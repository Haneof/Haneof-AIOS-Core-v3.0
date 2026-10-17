"""Read-only, allowlisted remote task runner for public GitHub Actions.

This gateway is NOT the formal Window69 security environment. It never invokes
Resident, Publisher, Core, signing tools, or user-provided shell commands.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from xml.etree import ElementTree as ET


REPO = "Haneof/Haneof-AIOS-Core-v3.0"
ROOT = Path(__file__).resolve().parents[2]
HEAD = "6fb725407569bc719c049587f67fe65e797eb734"
PARENT = "9d3b19b0e7bf090e5d472d9781b9156f73ea2088"
HEAD_BRANCH = "c15-rerun005-signed-ttyless-window66"
BASE = "reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005"
PACKET = BASE + "/RESIDENT_SAFE_LAUNCH_PACKET.json"
ARTIFACT = BASE + "/artifacts/resident-harness.tar.gz"
IDENTITY = BASE + "/harness/IDENTITY.json"
EXPECTED_PACKET = "023c7556de1bcd4d4b0caccb90b0fa65d0b8a9b783f41f30574dfbb12e8f6b34"
EXPECTED_ARTIFACT = "82aa3ff81d9492e0828934b5744adf4129fb6dc1361303a537379a603a319de3"
EXPECTED_IDENTITY = "364cc03617fcd782327b3307720baf5371839185b1b07b71476308af74c5a817"
TASKS = ("gateway-selftest", "pr370-source-boundary", "pr370-artifact-audit",
         "pr371-evidence-integrity", "r005-binding-ledger")
ALLOWED_EXACT = {PACKET}
ALLOWED_PREFIXES = (
    "reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66/",
    BASE + "/harness/",
    BASE + "/artifacts/",
)


class GateFailure(ValueError):
    """Unfulfilled public-only gate (not a security attack verdict)."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise GateFailure(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_git(*args: str) -> bytes:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, timeout=90, check=False
    )
    if proc.returncode:
        raise GateFailure(
            f"git {args[0]} exited {proc.returncode}; "
            + proc.stderr.decode("utf-8", errors="replace")[:350]
        )
    return proc.stdout


def verify_remote_and_fetch() -> dict:
    remote = run_git("remote", "get-url", "origin").decode().strip()
    expected = "https://github.com/" + REPO
    require(remote.rstrip("/").removesuffix(".git") == expected,
            "Git remote origin is not the approved public repository")
    ref = "refs/heads/" + HEAD_BRANCH
    actual = run_git("ls-remote", "--exit-code", "origin", ref).decode().strip()
    require(actual == HEAD + "\t" + ref,
            "PR370 branch no longer points at the frozen HEAD")
    run_git("fetch", "--no-tags", "origin", ref)
    require(run_git("rev-parse", "FETCH_HEAD").decode().strip() == HEAD,
            "fetched commit differs from approved HEAD")
    require(run_git("show", "-s", "--format=%P", HEAD).decode().strip() == PARENT,
            "frozen candidate's sole parent does not match")
    return {"repository": REPO, "candidate_head": HEAD, "sole_parent": PARENT}


def git_bytes(path: str, commit: str = HEAD) -> bytes:
    require(bool(re.fullmatch(r"[A-Za-z0-9_./-]+", path)) and ".." not in path.split("/"),
            "not an approved static repository path")
    data = run_git("show", commit + ":" + path)
    require(len(data) <= 4 * 1024 * 1024, "Git blob exceeds audit size bound")
    return data


def check_changed_paths(paths: list[str]) -> None:
    require(bool(paths) and len(paths) == len(set(paths)), "empty/duplicate change set")
    for path in paths:
        require(path in ALLOWED_EXACT or any(path.startswith(p) for p in ALLOWED_PREFIXES),
                "unapproved PR370 changed path: " + path)
    require(PACKET in paths and ARTIFACT in paths and IDENTITY in paths,
            "missing expected signed-Harness delivery members")


def audit_source_boundary() -> dict:
    meta = verify_remote_and_fetch()
    paths = run_git("diff", "--name-only", PARENT, HEAD).decode().splitlines()
    check_changed_paths(paths)
    return {**meta, "changed_file_count": len(paths),
            "forbidden_core_or_test_changes": 0,
            "source_boundary": "PASS"}


def audit_tar(raw: bytes, inventory: dict) -> dict:
    require(len(raw) <= 4 * 1024 * 1024, "archive exceeds audit limit")
    require(isinstance(inventory, dict) and len(inventory) == 22,
            "closed 22-member inventory required")
    require(all(isinstance(x, dict) for x in inventory.values()),
            "invalid archive inventory")
    observed = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
            members = archive.getmembers()
            require(len(members) == len(inventory), "archive member count mismatch")
            for entry in members:
                name = entry.name
                path = PurePosixPath(name)
                require(
                    name in inventory
                    and name.startswith("harness/")
                    and not path.is_absolute()
                    and all(part not in ("", ".", "..") for part in name.split("/")),
                    "unapproved archive member path"
                )
                require(name not in observed, "duplicate archive member")
                pin = inventory[name]
                require(entry.isreg() and not entry.linkname and not entry.pax_headers,
                        "archive contains link or non-regular member")
                require(entry.mode == pin["mode"] == 0o644
                        and entry.uid == entry.gid == entry.mtime == 0
                        and entry.size == pin["size"]
                        and 0 <= entry.size <= 4 * 1024 * 1024,
                        "archive member metadata mismatch")
                stream = archive.extractfile(entry)
                require(stream is not None, "archive member has no readable content")
                data = stream.read(4 * 1024 * 1024 + 1)
                require(len(data) == entry.size and digest(data) == pin["sha256"],
                        "archive member SHA256 mismatch")
                observed[name] = digest(data)
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise GateFailure("invalid archive: " + type(exc).__name__) from exc
    require(set(observed) == set(inventory), "archive closed member set mismatch")
    require(observed["harness/IDENTITY.json"] == EXPECTED_IDENTITY,
            "archive Harness identity differs from pinned manifest")
    return {"member_count": len(observed), "identity_sha256": EXPECTED_IDENTITY}


def audit_artifact() -> dict:
    meta = verify_remote_and_fetch()
    raw_packet = git_bytes(PACKET)
    raw_artifact = git_bytes(ARTIFACT)
    raw_identity = git_bytes(IDENTITY)
    require(digest(raw_packet) == EXPECTED_PACKET, "packet SHA256 mismatch")
    require(digest(raw_artifact) == EXPECTED_ARTIFACT, "artifact SHA256 mismatch")
    require(digest(raw_identity) == EXPECTED_IDENTITY, "manifest SHA256 mismatch")
    packet = json.loads(raw_packet)
    require(packet.get("real_resident_use_authorized") is False
            and packet.get("access_class") == "TEST_ONLY/MECHANICAL",
            "unsafe launch packet status")
    grant_spec = packet.get("signed_test_response", {})
    require(grant_spec.get("purpose") == "aios.r005.test.response.sign.v1",
            "wrong test-response purpose")
    package = packet["cross_sandbox_harness_materialization"]
    require(package.get("artifact_sha256") == EXPECTED_ARTIFACT,
            "packet and archive mismatch")
    require(packet.get("runtime_module_identity", {}).get("manifest_sha256")
            == EXPECTED_IDENTITY, "packet and manifest mismatch")
    members = audit_tar(raw_artifact, package["member_identity"])
    return {**meta, **members, "packet_sha256": EXPECTED_PACKET,
            "artifact_sha256": EXPECTED_ARTIFACT,
            "real_resident_use_authorized": False,
            "audit_scope": "STATIC_PUBLIC_BYTES_ONLY_NO_EXECUTION"}



def window67_audit_module():
    """Load only reviewed sibling validator under isolated Python -I."""
    path = ROOT / "tools" / "agent_gateway" / "window67_audit.py"
    spec = importlib.util.spec_from_file_location("aios_window67_public_evidence", path)
    require(spec is not None and spec.loader is not None, "missing trusted evidence validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_window67_evidence_ref(module) -> dict:
    """Read pinned Git commit identity, never select arbitrary Issue-supplied refs."""
    verify_remote_and_fetch()
    ref = "refs/heads/" + module.WINDOW67_BRANCH
    actual = run_git("ls-remote", "--exit-code", "origin", ref).decode().strip()
    require(actual == module.WINDOW67_HEAD + "\t" + ref,
            "Window67 independent-evidence branch head moved")
    run_git("fetch", "--no-tags", "origin", ref)
    require(run_git("rev-parse", "FETCH_HEAD").decode().strip()
            == module.WINDOW67_HEAD, "evidence fetch identity differs")
    require(run_git("show", "-s", "--format=%T",
                    module.WINDOW67_HEAD).decode().strip()
            == module.WINDOW67_TREE, "evidence Git tree identity differs")
    return {
        "engineering_candidate": HEAD,
        "frozen_window67_head": module.WINDOW67_HEAD,
        "frozen_window67_tree": module.WINDOW67_TREE,
    }


def verified_window67_ledger_bytes(module) -> tuple:
    base = module.WINDOW67_BASE + "/"
    raw_manifest = git_bytes(base + "SHA256.json", module.WINDOW67_HEAD)
    inventory = module.validate_manifest(raw_manifest)
    path = "WINDOW67_TEST_RESULTS.json"
    data = git_bytes(base + path, module.WINDOW67_HEAD)
    require(len(data) == inventory[path]["size"]
            and digest(data) == inventory[path]["sha256"],
            "Window67 formal result bytes differ from pinned evidence inventory")
    return inventory, data


def audit_window67_evidence() -> dict:
    module = window67_audit_module()
    refs = verify_window67_evidence_ref(module)
    manifest, _ = verified_window67_ledger_bytes(module)
    prefix = module.WINDOW67_BASE + "/"
    tracked = run_git(
        "ls-tree", "-r", "--name-only", module.WINDOW67_HEAD,
        "--", module.WINDOW67_BASE
    ).decode("utf-8").splitlines()
    inspected = module.verify_manifest_members(
        manifest, tracked,
        lambda name: git_bytes(prefix + name, module.WINDOW67_HEAD),
    )
    return {**refs, **inspected,
            "scope": "STATIC_PUBLIC_EVIDENCE_HASHES_NOT_FORMAL_SECURITY"}


def audit_binding_ledger() -> dict:
    module = window67_audit_module()
    refs = verify_window67_evidence_ref(module)
    _, record = verified_window67_ledger_bytes(module)
    engineer = git_bytes(
        "reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66/DEVELOPMENT_STATUS.json"
    )
    status = module.json_object_no_duplicates(record)
    author = module.json_object_no_duplicates(engineer)
    result = module.validate_binding_ledger(status, author, HEAD)
    return {**refs, **result,
            "scope": "FROZEN_HISTORICAL_REGRESSIONS_NO_TEST_REEXECUTION"}


def selftest() -> dict:
    require(TASKS == ("gateway-selftest", "pr370-source-boundary",
                      "pr370-artifact-audit", "pr371-evidence-integrity",
                      "r005-binding-ledger"), "unexpected task list")
    require(len({HEAD, PARENT}) == 2 and len(HEAD) == 40, "invalid commit pins")
    require(all(len(x) == 64 for x in
                (EXPECTED_ARTIFACT, EXPECTED_PACKET, EXPECTED_IDENTITY)),
            "invalid immutable SHA256 pins")
    require(all(x.startswith(("pr370-", "pr371-", "r005-"))
                or x == "gateway-selftest" for x in TASKS),
            "unexpected task type")
    return {"allowlisted_tasks": list(TASKS),
            "security_scope": "NO_SECRETS_NO_EXEC_NO_REAL_RESIDENT"}


def write_evidence(task: str, status: str, detail: dict, error: str | None) -> None:
    destination = ROOT / "gateway-evidence" / task
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    result = {
        "schema": "aios.agent.gateway.result.v0.1",
        "task": task, "status": status,
        "classification": "NON_FORMAL_PUBLIC_CI_EVIDENCE",
        "candidate": HEAD,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "github_run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "details": detail,
        "error": error,
        "window69_formal_validation": "NOT_PERFORMED",
        "real_resident_started": False,
        "merge_authorized": False,
    }
    result_path = destination / "result.json"
    result_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    testsuite = ET.Element("testsuite", name="AIOS_Agent_Gateway_v0.1",
                           tests="1", failures=str(status != "PASS"),
                           errors="0", skipped="0")
    test = ET.SubElement(testsuite, "testcase", name=task, classname="gateway")
    if status != "PASS":
        ET.SubElement(test, "failure", message="read-only gate failed").text = error or ""
    junit_path = destination / "junit.xml"
    ET.ElementTree(testsuite).write(junit_path, encoding="utf-8",
                                    xml_declaration=True)
    index = {
        "result.json": digest(result_path.read_bytes()),
        "junit.xml": digest(junit_path.read_bytes()),
    }
    (destination / "SHA256.json").write_text(json.dumps(index, indent=2) + "\n",
                                              encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, choices=TASKS)
    args = parser.parse_args(argv)
    detail: dict = {}
    error: str | None = None
    try:
        if args.task == "gateway-selftest":
            detail = selftest()
        elif args.task == "pr370-source-boundary":
            detail = audit_source_boundary()
        elif args.task == "pr370-artifact-audit":
            detail = audit_artifact()
        elif args.task == "pr371-evidence-integrity":
            detail = audit_window67_evidence()
        elif args.task == "r005-binding-ledger":
            detail = audit_binding_ledger()
        else:
            raise GateFailure("task not allowlisted")
        status = "PASS"
    except (GateFailure, subprocess.TimeoutExpired, KeyError, ValueError, TypeError,
            json.JSONDecodeError) as exc:
        status = "FAIL"
        error = f"{type(exc).__name__}: {str(exc)[:700]}"
    write_evidence(args.task, status, detail, error)
    print(json.dumps({"task": args.task, "status": status,
                      "classification": "NON_FORMAL_PUBLIC_CI_EVIDENCE",
                      "error": error}, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
