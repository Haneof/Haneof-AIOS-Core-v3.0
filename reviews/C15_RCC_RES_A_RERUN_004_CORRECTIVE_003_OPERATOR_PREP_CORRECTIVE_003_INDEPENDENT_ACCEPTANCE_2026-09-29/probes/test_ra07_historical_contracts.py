"""RA-07: independent re-attack of historical #283/#284 guarantees.

C1 response replay integrity; C2 wheel trust root; C4 recovery binding;
C5 operational ledger integrity; C6 frozen RC identity; C7 exact runtime pins;
C8 clean-room startup boundary.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

from conftest import assert_linear, run_worker

REPO_ROOT = pathlib.Path(os.environ.get("AIOS_REVIEW_REPO_ROOT", "/home/user/ia_review/rc"))
PACKAGE_ROOT = pathlib.Path(
    os.environ.get(
        "AIOS_REVIEW_PACKAGE_ROOT",
        "/home/user/ia_review/h2/reviews/internal_habitation/c15-rcc/v1/operator_prep/"
        "C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP",
    )
)
RUNTIME_ROOT = pathlib.Path(
    os.environ.get("AIOS_REVIEW_RUNTIME_ROOT", "/home/user/ia_review/runtime")
)


# ---------------------------------------------------------------------------
# C1: published response replay integrity
# ---------------------------------------------------------------------------
def _seed_published_response(exchange, marker="c1"):
    seed, _ = run_worker("publish", root=exchange, marker=f"{marker}-seed")
    request_id = seed["receipt"]["request_id"]
    published, _ = run_worker(
        "publish-response", root=exchange, request_id=request_id, marker=f"{marker}-response"
    )
    assert published["ok"], published
    return request_id, published["receipt"]


def test_c1_tampered_published_response_fails_closed(tmp_path, exchange):
    from aios_exchange.bridge import ExchangeBridge

    request_id, receipt = _seed_published_response(exchange, "c1-tamper")
    path = exchange / "responses" / f"{request_id}.json"
    payload = json.loads(path.read_bytes())
    payload["directive"]["response"] = "reviewer-tampered-response"
    path.write_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode() + b"\n")

    bridge = ExchangeBridge(exchange)
    for operation in (
        lambda: bridge.responses.publish_object(
            request_id=request_id,
            response={
                "response_version": 1,
                "request_id": request_id,
                "request_sha256": bridge.request_sha256(request_id),
                "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
                "directive": {"capability_calls": [], "response": "replay-attempt", "silence": False},
            },
        ),
        lambda: bridge.responses.published_bytes(request_id),
        lambda: bridge.consume_response(request_id),
    ):
        try:
            operation()
            raise AssertionError("tampered published response was accepted")
        except AssertionError:
            raise
        except Exception:
            pass


def test_c1_missing_published_response_fails_closed(tmp_path, exchange):
    from aios_exchange.bridge import ExchangeBridge

    request_id, receipt = _seed_published_response(exchange, "c1-missing")
    (exchange / "responses" / f"{request_id}.json").unlink()
    bridge = ExchangeBridge(exchange)
    for operation in (
        lambda: bridge.responses.published_bytes(request_id),
        lambda: bridge.consume_response(request_id),
        lambda: bridge.responses.publish_object(
            request_id=request_id,
            response={
                "response_version": 1,
                "request_id": request_id,
                "request_sha256": bridge.request_sha256(request_id),
                "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
                "directive": {"capability_calls": [], "response": "replay", "silence": False},
            },
        ),
    ):
        try:
            operation()
            raise AssertionError("missing published response was accepted")
        except AssertionError:
            raise
        except Exception:
            pass


def test_c1_intact_replay_is_idempotent(tmp_path, exchange):
    from aios_exchange.bridge import ExchangeBridge

    request_id, receipt = _seed_published_response(exchange, "c1-intact")
    bridge = ExchangeBridge(exchange)
    raw = bridge.responses.published_bytes(request_id)
    import hashlib

    assert hashlib.sha256(raw).hexdigest() == receipt["response_sha256"]
    replay = bridge.responses.publish_object(
        request_id=request_id,
        response=json.loads(raw),
    )
    assert replay["idempotent_replay"] is True
    rows = assert_linear(exchange)
    assert len([r for r in rows if r["event"] == "response_published"]) == 1


# ---------------------------------------------------------------------------
# C2: pre-download wheel trust root
# ---------------------------------------------------------------------------
def _wheel_verify(wheelhouse: pathlib.Path):
    verifier = PACKAGE_ROOT / "bootstrap" / "wheel_lock.py"
    lock = PACKAGE_ROOT / "bootstrap" / "PYTHON_WHEEL_LOCK.json"
    return subprocess.run(
        [sys.executable, str(verifier), "verify", "--lock", str(lock), "--wheelhouse", str(wheelhouse)],
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_c2_wheel_trust_root_closed_set(tmp_path):
    # pre-download frozen SHA verification must pass on the qualified closure
    qualified = RUNTIME_ROOT / "runtime" / "3.12.14" / "wheelhouse"
    assert qualified.is_dir(), f"qualified wheelhouse missing: {qualified}"
    assert _wheel_verify(qualified).returncode == 0, "qualified closure failed verification"

    # wrong bytes FAIL
    wrong = tmp_path / "wrong"
    shutil.copytree(qualified, wrong)
    victim = sorted(wrong.glob("*.whl"))[0]
    data = bytearray(victim.read_bytes())
    data[len(data) // 2] ^= 0xFF
    victim.write_bytes(bytes(data))
    assert _wheel_verify(wrong).returncode != 0, "corrupted wheel accepted"

    # missing wheel FAIL
    missing = tmp_path / "missing"
    shutil.copytree(qualified, missing)
    sorted(missing.glob("*.whl"))[0].unlink()
    assert _wheel_verify(missing).returncode != 0, "missing wheel accepted"

    # extra/unlocked wheel FAIL
    extra = tmp_path / "extra"
    shutil.copytree(qualified, extra)
    (extra / "unlocked_package-0.0.1-py3-none-any.whl").write_bytes(b"not a wheel")
    assert _wheel_verify(extra).returncode != 0, "extra unlocked wheel accepted"


def test_c2_install_uses_no_index_no_resolver():
    script = (PACKAGE_ROOT / "bootstrap" / "bootstrap_runtime.sh").read_text()
    assert "--no-index" in script, "bootstrap does not forbid a live index"
    assert "--no-deps" in script, "bootstrap does not forbid dependency re-resolution"
    assert "--require-hashes" in script or "sha256sum" in script


# ---------------------------------------------------------------------------
# C4: recovery request <-> RuntimeSnapshot exact binding
# ---------------------------------------------------------------------------
def test_c4_recovery_snapshot_mismatch_fails_closed(tmp_path, exchange):
    from aios_exchange.runner import ExternalSessionConfig, ExternalSessionModelHandler

    published, _ = run_worker("publish", root=exchange, marker="c4-original-snapshot")
    assert published["ok"], published
    handler = ExternalSessionModelHandler(
        ExternalSessionConfig(exchange, response_timeout_s=5, poll_interval_s=0.01)
    )
    try:
        handler(_snapshot_for("c4-different-snapshot"))
        raise AssertionError("recovery accepted a different snapshot")
    except AssertionError:
        raise
    except Exception as exc:
        assert "binding" in str(exc).lower() or "snapshot" in str(exc).lower(), exc


def _snapshot_for(marker: str):
    from aios_core.runtime.cognitive_runtime import RuntimeSnapshot

    return RuntimeSnapshot(
        user_input=marker,
        wake_reason="reviewer-synthetic",
        cockpit={"reviewer": True},
        capability_catalog=(),
        capability_history=(),
        round_index=0,
        remaining_tool_rounds=1,
    )


# ---------------------------------------------------------------------------
# C5: operational ledger integrity
# ---------------------------------------------------------------------------
def _valid_ledger_rows(exchange):
    for marker in ("c5-a", "c5-b"):
        run_worker("publish", root=exchange, marker=marker)
    from aios_exchange.ledger import ExchangeLedger

    ledger = ExchangeLedger(exchange / "ledger.jsonl")
    rows = ledger.read_records()
    assert rows
    return rows


def _expect_corrupt(exchange, mutate):
    from aios_exchange.ledger import ExchangeLedger, LedgerError

    path = exchange / "ledger.jsonl"
    rows = json.loads(json.dumps(_valid_ledger_rows(exchange)))
    lines = [json.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows]
    lines = mutate(lines)
    path.write_bytes(("\n".join(lines) + "\n").encode())
    ledger = ExchangeLedger(path)
    failed = False
    try:
        ledger.read_records()
    except LedgerError:
        failed = True
    assert failed, "corrupted ledger was accepted"
    assert ledger.verify_chain()["ok"] is False


def test_c5_interior_mutation_detected(tmp_path, exchange):
    def mutate(lines):
        row = json.loads(lines[0])
        row["wall_clock"] = "2020-01-01T00:00:00.000000Z"
        lines[0] = json.dumps(row, sort_keys=True, separators=(",", ":"))
        return lines

    _expect_corrupt(exchange, mutate)


def test_c5_interior_deletion_detected(tmp_path, exchange):
    _expect_corrupt(exchange, lambda lines: lines[1:])


def test_c5_duplicate_event_detected(tmp_path, exchange):
    _expect_corrupt(exchange, lambda lines: [lines[0], lines[0]] + lines[1:])


def test_c5_sequence_corruption_detected(tmp_path, exchange):
    def mutate(lines):
        row = json.loads(lines[1])
        row["seq"] = 99
        lines[1] = json.dumps(row, sort_keys=True, separators=(",", ":"))
        return lines

    _expect_corrupt(exchange, mutate)


def test_c5_digest_discontinuity_detected(tmp_path, exchange):
    def mutate(lines):
        row = json.loads(lines[1])
        row["prev_sha256"] = "f" * 64
        lines[1] = json.dumps(row, sort_keys=True, separators=(",", ":"))
        return lines

    _expect_corrupt(exchange, mutate)


def test_c5_illegal_event_order_detected(tmp_path, exchange):
    def mutate(lines):
        row = json.loads(lines[0])
        row["event"] = "response_consumed"
        row["record_sha256"] = _rehash(row)
        lines[0] = json.dumps(row, sort_keys=True, separators=(",", ":"))
        return lines

    _expect_corrupt(exchange, mutate)


def _rehash(row):
    import hashlib

    sys.path.insert(0, str(PACKAGE_ROOT / "harness"))
    from aios_exchange.canonical import canonical_json_bytes

    body = {k: v for k, v in row.items() if k != "record_sha256"}
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


# ---------------------------------------------------------------------------
# C6: frozen RC identity / C7: exact runtime pins / C8: clean-room boundary
# ---------------------------------------------------------------------------
def test_c6_frozen_rc_identity_checks(tmp_path):
    tool = PACKAGE_ROOT / "harness" / "operator_tools" / "rc_identity.py"
    ok = subprocess.run(
        [sys.executable, str(tool), "--repo-root", str(REPO_ROOT)],
        capture_output=True, text=True, timeout=300,
    )
    assert ok.returncode == 0, ok.stdout[-2000:] + ok.stderr[-1000:]

    # missing git metadata -> BLOCKED
    no_git = tmp_path / "no-git"
    shutil.copytree(REPO_ROOT / "src", no_git / "src")
    shutil.copytree(REPO_ROOT / "tests", no_git / "tests")
    blocked = subprocess.run(
        [sys.executable, str(tool), "--repo-root", str(no_git)],
        capture_output=True, text=True, timeout=300,
    )
    assert blocked.returncode != 0, "missing git metadata was accepted"

    # Core working-tree mutation -> BLOCKED
    mutated = tmp_path / "mutated"
    shutil.copytree(REPO_ROOT, mutated, symlinks=True)
    core_file = mutated / "src" / "aios_core" / "runtime" / "turn_runtime.py"
    core_file.write_bytes(core_file.read_bytes() + b"\n# reviewer mutation\n")
    blocked = subprocess.run(
        [sys.executable, str(tool), "--repo-root", str(mutated)],
        capture_output=True, text=True, timeout=300,
    )
    assert blocked.returncode != 0, "mutated Core working tree was accepted"

    # foreign repo without the frozen objects -> BLOCKED
    foreign = tmp_path / "foreign"
    subprocess.run(["git", "init", "-q", str(foreign)], check=True)
    blocked = subprocess.run(
        [sys.executable, str(tool), "--repo-root", str(foreign)],
        capture_output=True, text=True, timeout=300,
    )
    assert blocked.returncode != 0, "foreign repository was accepted"


def test_c7_exact_runtime_pins():
    import sqlite3
    import ssl

    import pydantic
    import pytest

    assert sys.version.split()[0] == "3.12.14", sys.version
    assert pydantic.VERSION == "2.13.5", pydantic.VERSION
    assert pytest.__version__ == "8.4.2", pytest.__version__
    assert sqlite3.sqlite_version == "3.45.1", sqlite3.sqlite_version
    assert ssl.OPENSSL_VERSION.startswith("OpenSSL 3.0.13"), ssl.OPENSSL_VERSION

    import aios_core

    core_file = pathlib.Path(aios_core.__file__).resolve()
    assert str(core_file).startswith(str(REPO_ROOT.resolve())), (
        f"foreign import path: {core_file}"
    )
    assert "site-packages" not in str(core_file), f"Core imported from site-packages: {core_file}"


def test_c8_clean_room_startup_boundary():
    packet = json.loads((PACKAGE_ROOT / "RESIDENT_SAFE_LAUNCH_PACKET.json").read_text())
    inputs = packet["allowed_startup_inputs"]
    assert len(inputs) == 4, f"startup input set is not exactly four: {inputs}"
    assert packet["status"] == "PREP_REVIEW_READY", packet["status"]
    assert packet["status"] != "READY_FOR_RESIDENT"
    assert not any("fixture" in str(item).lower() for item in inputs)
    assert not any("evaluator" in str(item).lower() for item in inputs)

    # the run package must not reach test/synthetic/evaluator modules
    run_package = PACKAGE_ROOT / "harness" / "aios_exchange"
    forbidden = ("tests.synthetic", "deterministic_resident", "crash_worker", "fixture", "evaluator")
    for path in sorted(run_package.rglob("*.py")):
        text = path.read_text()
        for token in forbidden:
            assert token not in text, f"{path} references {token!r}"
