#!/usr/bin/env python3
"""Frozen targeted probes for IA-OP-001/002/003 only.

This file is frozen before the first run against historical candidate #281.
Do not edit it after its SHA-256 is recorded in CORRECTIVE_PROBE_FREEZE.json.
The probe uses synthetic exchange data only and never initializes a Resident.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import re
import shutil
import sys
import tempfile
from typing import Any

BASELINE_COUNTS = {"A": 19, "B": 7, "C": 2, "D": 5}
CANDIDATE_COUNTS = {"A": 24, "B": 7, "C": 2, "D": 5}
EXPECTED_DISTRIBUTIONS = {
    "pydantic": "2.13.5",
    "pydantic-core": None,
    "typing-extensions": None,
    "annotated-types": None,
    "typing-inspection": None,
    "pytest": "8.4.2",
    "iniconfig": None,
    "packaging": None,
    "pluggy": None,
    "pygments": None,
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load candidate module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def c1_probe(package_root: pathlib.Path, core_source: pathlib.Path | None = None) -> dict[str, Any]:
    harness = package_root / "harness"
    if core_source is not None:
        sys.path.insert(0, str(core_source.resolve()))
    sys.path.insert(0, str(harness))
    try:
        from aios_exchange.bridge import ExchangeBridge, ExchangeContractError
        from aios_exchange.canonical import canonical_json_bytes
        from aios_exchange.responses import ResponsePublishError
    except Exception as exc:
        return {"status": "BLOCKED", "error": f"cannot import publisher: {type(exc).__name__}: {exc}"}

    def make_bridge(root: pathlib.Path, name: str):
        bridge = ExchangeBridge(root / name)
        request = bridge.publish_request(
            kind="model_directive",
            body={"synthetic_probe": "C1", "synthetic_subject": "operator_prep", "synthetic_round": 0},
        )
        payload = bridge.request_payload(request["request_id"])
        payload["request_sha256"] = request["request_sha256"]
        response = {
            "response_version": 1,
            "request_id": request["request_id"],
            "request_sha256": request["request_sha256"],
            "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
            "directive": {"capability_calls": [], "response": "SYNTHETIC C1", "silence": False},
        }
        blob = canonical_json_bytes(response) + b"\n"
        bridge.responses.publish_bytes(request_id=request["request_id"], response_bytes=blob)
        return bridge, request["request_id"], blob

    def expect_publish_failure(fn) -> bool:
        try:
            fn()
        except (ResponsePublishError, ExchangeContractError, OSError):
            return True
        except Exception:
            return True
        return False

    with tempfile.TemporaryDirectory(prefix="aios-c1-") as temp:
        root = pathlib.Path(temp)
        intact, intact_id, intact_blob = make_bridge(root, "intact")
        intact_result = intact.responses.publish_bytes(request_id=intact_id, response_bytes=intact_blob)

        tampered, tampered_id, tampered_blob = make_bridge(root, "tampered")
        tampered_path = tampered.responses.path_for(tampered_id)
        tampered_path.write_bytes(b'{"tampered":"on disk"}\n')
        tampered_fail_closed = expect_publish_failure(
            lambda: tampered.responses.publish_bytes(request_id=tampered_id, response_bytes=tampered_blob)
        )
        tampered_consume_fail_closed = expect_publish_failure(
            lambda: tampered.consume_response(tampered_id)
        )

        missing, missing_id, missing_blob = make_bridge(root, "missing")
        missing.responses.path_for(missing_id).unlink()
        missing_fail_closed = expect_publish_failure(
            lambda: missing.responses.publish_bytes(request_id=missing_id, response_bytes=missing_blob)
        )

        changed, changed_id, changed_blob = make_bridge(root, "changed")
        changed_input_rejected = expect_publish_failure(
            lambda: changed.responses.publish_bytes(request_id=changed_id, response_bytes=changed_blob + b" ")
        )

    blocker_red = not tampered_fail_closed or not missing_fail_closed
    all_green = (
        intact_result.get("idempotent_replay") is True
        and tampered_fail_closed
        and missing_fail_closed
        and changed_input_rejected
        and tampered_consume_fail_closed
    )
    return {
        "status": "RED" if blocker_red else ("GREEN" if all_green else "FAIL"),
        "expected": {
            "tampered_publish": "fail closed",
            "missing_publish": "fail closed",
            "intact_exact_replay": "idempotent_replay=true",
            "changed_replay": "fail closed",
            "tampered_consume": "fail closed",
        },
        "observed": {
            "tampered_publish_fail_closed": tampered_fail_closed,
            "missing_publish_fail_closed": missing_fail_closed,
            "intact_idempotent_replay": intact_result.get("idempotent_replay"),
            "changed_replay_fail_closed": changed_input_rejected,
            "tampered_consume_fail_closed": tampered_consume_fail_closed,
        },
    }


def _validate_lock(lock_path: pathlib.Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    wheels = lock.get("wheels")
    if not isinstance(wheels, list) or not wheels:
        raise ValueError("lock has no non-empty wheels array")
    required = {"project", "version", "filename", "sha256", "python_tag", "abi_tag", "platform_tag"}
    seen: set[str] = set()
    for wheel in wheels:
        if not isinstance(wheel, dict) or not required <= set(wheel):
            raise ValueError("wheel entry lacks required immutable artifact identity fields")
        if not re.fullmatch(r"[0-9a-f]{64}", str(wheel["sha256"])):
            raise ValueError("wheel entry has malformed SHA-256")
        filename = str(wheel["filename"])
        if not filename.endswith(".whl") or filename in seen:
            raise ValueError("wheel filename is invalid or duplicated")
        seen.add(filename)
    return lock, wheels


def c2_probe(package_root: pathlib.Path) -> dict[str, Any]:
    bootstrap = package_root / "bootstrap" / "bootstrap_runtime.sh"
    source = bootstrap.read_text(encoding="utf-8")
    lock_candidates = [
        package_root / "bootstrap" / "PYTHON_WHEEL_LOCK.json",
        package_root / "bootstrap" / "python_wheel_lock.json",
        package_root / "bootstrap" / "wheel-lock.json",
    ]
    lock_path = next((p for p in lock_candidates if p.is_file()), None)
    observations: dict[str, Any] = {
        "lock_present": lock_path is not None,
        "bootstrap_uses_pre_download_lock": False,
        "bootstrap_avoids_top_level_live_resolution": False,
        "install_is_offline_and_no_resolver": False,
        "wrong_bytes_rejected": False,
        "wrong_hash_rejected": False,
        "unexpected_wheel_rejected": False,
        "missing_wheel_rejected": False,
        "required_distributions": {},
        "lock_sha256": None,
        "lock_error": None,
    }
    if lock_path is None:
        observations["lock_error"] = "no candidate-controlled pre-download wheel lock"
        observations["status"] = "RED"
        return observations

    observations["lock_sha256"] = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    try:
        lock, wheels = _validate_lock(lock_path)
    except Exception as exc:
        observations["lock_error"] = f"{type(exc).__name__}: {exc}"
        observations["status"] = "RED"
        return observations

    projects = {str(w["project"]).lower().replace("_", "-"): str(w["version"]) for w in wheels}
    observations["required_distributions"] = projects
    required_projects_present = all(
        name in projects and (version is None or projects[name] == version)
        for name, version in EXPECTED_DISTRIBUTIONS.items()
    )
    calls_lock = "PYTHON_WHEEL_LOCK" in source or "python_wheel_lock" in source or "wheel-lock.json" in source
    no_top_level_resolver = not re.search(
        r"pip\s+download[^\n]*(?:pydantic|pytest)", source, flags=re.IGNORECASE
    )
    offline_no_resolver = bool(re.search(r"pip\s+install[^\n]*--no-index[^\n]*--no-deps", source))
    observations["bootstrap_uses_pre_download_lock"] = calls_lock and required_projects_present
    observations["bootstrap_avoids_top_level_live_resolution"] = no_top_level_resolver
    observations["install_is_offline_and_no_resolver"] = offline_no_resolver

    verifier_path = package_root / "bootstrap" / "wheel_lock.py"
    if verifier_path.is_file():
        try:
            verifier = load_module("corrective_candidate_wheel_lock", verifier_path)
            verify = getattr(verifier, "verify_wheelhouse")
            wheelhouse = package_root / "bootstrap" / ".probe-wheelhouse"
            if wheelhouse.exists():
                shutil.rmtree(wheelhouse)
            wheelhouse.mkdir(parents=True)
            with tempfile.TemporaryDirectory(prefix="aios-c2-_") as temp:
                temp_root = pathlib.Path(temp)
                test_lock = temp_root / "lock.json"
                wheel_dir = temp_root / "wheelhouse"
                wheel_dir.mkdir()
                # Synthetic artifacts exercise the verifier; project metadata is not installed.
                sample = dict(wheels[0])
                sample["filename"] = "probe-1.0-py3-none-any.whl"
                sample["project"] = "probe"
                sample["version"] = "1.0"
                sample["python_tag"] = "py3"
                sample["abi_tag"] = "none"
                sample["platform_tag"] = "any"
                sample["url"] = "https://files.pythonhosted.org/packages/probe-1.0-py3-none-any.whl"
                sample_bytes = b"synthetic-wheel-bytes"
                sample["sha256"] = sha256(sample_bytes)
                test_lock.write_text(json.dumps({"schema_version": 1, "target": lock.get("target", {}), "wheels": [sample]}))
                (wheel_dir / sample["filename"]).write_bytes(sample_bytes)
                verify(test_lock, wheel_dir)

                (wheel_dir / sample["filename"]).write_bytes(b"wrong bytes")
                try:
                    verify(test_lock, wheel_dir)
                except Exception:
                    observations["wrong_bytes_rejected"] = True

                (wheel_dir / sample["filename"]).write_bytes(sample_bytes)
                bad_lock = dict(sample)
                bad_lock["sha256"] = "0" * 64
                bad_lock_path = temp_root / "bad-lock.json"
                bad_lock_path.write_text(json.dumps({"schema_version": 1, "target": lock.get("target", {}), "wheels": [bad_lock]}))
                try:
                    verify(bad_lock_path, wheel_dir)
                except Exception:
                    observations["wrong_hash_rejected"] = True

                (wheel_dir / "unexpected-1.0-py3-none-any.whl").write_bytes(b"unexpected")
                try:
                    verify(test_lock, wheel_dir)
                except Exception:
                    observations["unexpected_wheel_rejected"] = True
                (wheel_dir / "unexpected-1.0-py3-none-any.whl").unlink()
                (wheel_dir / sample["filename"]).unlink()
                try:
                    verify(test_lock, wheel_dir)
                except Exception:
                    observations["missing_wheel_rejected"] = True
            observations["verifier_api_present"] = True
        except Exception as exc:
            observations["verifier_error"] = f"{type(exc).__name__}: {exc}"
            observations["verifier_api_present"] = False
    else:
        observations["verifier_api_present"] = False

    checks = [
        observations["bootstrap_uses_pre_download_lock"],
        observations["bootstrap_avoids_top_level_live_resolution"],
        observations["install_is_offline_and_no_resolver"],
        observations.get("verifier_api_present", False),
        observations["wrong_bytes_rejected"],
        observations["wrong_hash_rejected"],
        observations["unexpected_wheel_rejected"],
        observations["missing_wheel_rejected"],
    ]
    observations["status"] = "GREEN" if all(checks) else "RED"
    return observations


def c3_probe(package_root: pathlib.Path, mode: str) -> dict[str, Any]:
    expected_counts = BASELINE_COUNTS if mode == "historical" else CANDIDATE_COUNTS
    tool = package_root / "harness" / "operator_tools" / "gate_runner.py"
    module = load_module("corrective_candidate_gate_runner", tool)
    parser = getattr(module, "parse_collection_output", None)
    observations: dict[str, Any] = {"parser_api_present": callable(parser), "gates": {}, "negative_cases": {}}
    gates_dir = package_root / "evidence" / "gates"
    all_evidence_good = True
    for gate, expected_count in expected_counts.items():
        stem = f"gate_{gate.lower()}"
        collect_path = gates_dir / f"{stem}_tests.txt"
        result_path = gates_dir / f"{stem}_result.json"
        collect_text = collect_path.read_text(encoding="utf-8") if collect_path.exists() else ""
        node_ids = [line.strip() for line in collect_text.splitlines() if "::" in line.strip()]
        summary = re.search(r"(?m)^(\d+) tests? collected(?: in [^\n]+)?\s*$", collect_text)
        reported = int(summary.group(1)) if summary else None
        result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
        outcomes = result.get("outcomes", {})
        executed = sum(int(outcomes.get(k, 0)) for k in ("passed", "failed", "error", "skipped"))
        exact_ids = len(node_ids) == expected_count and reported == expected_count
        if callable(parser):
            try:
                parsed = parser(collect_text, "", 0)
                parsed_ids = parsed[0] if isinstance(parsed, tuple) else parsed
                exact_ids = exact_ids and list(parsed_ids) == node_ids
            except Exception as exc:
                exact_ids = False
                observations.setdefault("parser_errors", {})[gate] = f"{type(exc).__name__}: {exc}"
        gate_good = (
            exact_ids
            and result.get("test_count") == len(result.get("test_ids", []))
            and result.get("test_count") == expected_count
            and result.get("test_ids") == node_ids
            and executed == expected_count
            and result.get("returncode") == 0
        )
        all_evidence_good = all_evidence_good and gate_good
        observations["gates"][gate] = {
            "expected_count": expected_count,
            "parsed_node_count": len(node_ids),
            "reported_collected_total": reported,
            "result_test_count": result.get("test_count"),
            "result_id_count": len(result.get("test_ids", [])),
            "execution_total": executed,
            "collect_and_result_consistent": gate_good,
            "node_ids": node_ids,
        }

    if callable(parser):
        malformed = [
            ("malformed_collection", "not a pytest collection summary\n", "", 0),
            ("nonzero_returncode", "1 test collected\n", "collection failed\n", 1),
            ("empty_ids_nonempty_total", "2 tests collected\n", "", 0),
            ("count_mismatch", "x.py::test_one\n2 tests collected\n", "", 0),
        ]
        for name, stdout, stderr, code in malformed:
            try:
                parser(stdout, stderr, code)
                observations["negative_cases"][name] = "ACCEPTED"
            except Exception:
                observations["negative_cases"][name] = "BLOCKED"
        negative_good = all(value == "BLOCKED" for value in observations["negative_cases"].values())
    else:
        negative_good = False
        observations["negative_cases"] = {
            "malformed_collection": "NO_FAIL_CLOSED_PARSER",
            "nonzero_returncode": "NO_FAIL_CLOSED_PARSER",
            "empty_ids_nonempty_total": "NO_FAIL_CLOSED_PARSER",
            "count_mismatch": "NO_FAIL_CLOSED_PARSER",
        }
    observations["status"] = "GREEN" if all_evidence_good and negative_good else "RED"
    return observations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", required=True, type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--core-source", type=pathlib.Path)
    parser.add_argument("--mode", choices=("historical", "candidate"), default="candidate")
    args = parser.parse_args()
    root = args.candidate_root.resolve()
    report = {
        "candidate_root": str(root),
        "candidate_identity": {
            "head": "10901d467679b70437ae112747eab81f889fd5cb" if args.mode == "historical" else "candidate-pinned-in-report",
            "expected_historical_baseline": "10901d467679b70437ae112747eab81f889fd5cb",
        },
        "probe_mode": args.mode,
        "probes": {
            "C1_IA_OP_001": c1_probe(root, args.core_source),
            "C2_IA_OP_002": c2_probe(root),
            "C3_IA_OP_003": c3_probe(root, args.mode),
        },
    }
    report["status"] = "GREEN" if all(p.get("status") == "GREEN" for p in report["probes"].values()) else "RED"
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
