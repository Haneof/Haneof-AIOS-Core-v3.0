"""Freeze tooling: harness manifest, SHA256SUMS, freeze manifest.

Operator tooling. Produces the mechanical freeze artifacts for the
operator-prep evidence package.

Usage:
    python operator_tools/freeze.py manifest --operator-prep-root <root>
    python operator_tools/freeze.py sha256sums --operator-prep-root <root>
    python operator_tools/freeze.py freeze --operator-prep-root <root> [--head <sha>]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import platform
import sys
from typing import Any

TASK_ID = "C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003"
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
FREEZE_EXCLUDE_NAMES = {"SHA256SUMS"}


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: pathlib.Path, *, relative_to: pathlib.Path) -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def build_manifest(root: pathlib.Path) -> dict[str, Any]:
    files = []
    for path in iter_files(root, relative_to=root):
        relative = path.relative_to(root).as_posix()
        files.append({"path": relative, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest = {
        "task_id": TASK_ID,
        "root": root.name,
        "file_count": len(files),
        "files": files,
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return manifest


def write_manifest(operator_prep_root: pathlib.Path) -> dict[str, Any]:
    harness_root = operator_prep_root / "harness"
    harness_manifest = build_manifest(harness_root)
    bootstrap_root = operator_prep_root / "bootstrap"
    bootstrap_paths = [
        bootstrap_root / "bootstrap_runtime.sh",
        bootstrap_root / "PYTHON_WHEEL_LOCK.json",
        bootstrap_root / "wheel_lock.py",
    ]
    bootstrap_files = [
        {
            "path": path.relative_to(operator_prep_root).as_posix(),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in bootstrap_paths
    ]
    harness_files = [
        {**entry, "path": f"harness/{entry['path']}"}
        for entry in harness_manifest["files"]
    ]
    all_files = sorted(harness_files + bootstrap_files, key=lambda item: item["path"])
    manifest = {
        "task_id": TASK_ID,
        "root": operator_prep_root.name,
        "scope": "harness + bootstrap + pre-frozen Python wheel trust root",
        "harness_file_count": harness_manifest["file_count"],
        "bootstrap_file_count": len(bootstrap_files),
        "file_count": len(all_files),
        "files": all_files,
        "bootstrap_sha256": sha256_file(bootstrap_paths[0]),
        "wheel_lock_sha256": sha256_file(bootstrap_paths[1]),
        "wheel_lock_verifier_sha256": sha256_file(bootstrap_paths[2]),
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(all_files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    evidence = operator_prep_root / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    path = evidence / "harness_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def write_sha256sums(operator_prep_root: pathlib.Path) -> pathlib.Path:
    evidence = operator_prep_root / "evidence"
    files = [
        path
        for path in iter_files(operator_prep_root, relative_to=operator_prep_root)
        if path.name not in FREEZE_EXCLUDE_NAMES
    ]
    lines = []
    for path in files:
        relative = path.relative_to(operator_prep_root).as_posix()
        lines.append(f"{sha256_file(path)}  {relative}")
    target = evidence / "SHA256SUMS"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def write_freeze_manifest(operator_prep_root: pathlib.Path, head: str | None) -> dict[str, Any]:
    evidence = operator_prep_root / "evidence"
    gates = evidence / "gates" / "gate_summary.json"
    summary = json.loads(gates.read_text()) if gates.exists() else {}
    packet = operator_prep_root / "RESIDENT_SAFE_LAUNCH_PACKET.json"
    audit = evidence / "resident_safe_packet_audit.json"
    manifest = json.loads((evidence / "harness_manifest.json").read_text())
    wheel_lock = operator_prep_root / "bootstrap" / "PYTHON_WHEEL_LOCK.json"
    bootstrap = operator_prep_root / "bootstrap" / "bootstrap_runtime.sh"
    wheel_verification = evidence / "wheel_lock_verification.json"
    clean_bootstrap = evidence / "clean_bootstrap_manifest.json"
    green_probe = evidence / "corrective_candidate_green.json"
    c10_c11_green = evidence / "c10_c11_candidate_green.json"
    concurrency = evidence / "concurrency_integration.json"
    durability = evidence / "durability_fault_evidence.json"
    gate_results = {}
    for gate in "abcd":
        result_path = evidence / "gates" / f"gate_{gate}_result.json"
        payload = json.loads(result_path.read_text()) if result_path.exists() else {}
        gate_results[gate.upper()] = {
            "status": payload.get("status"),
            "result_sha256": sha256_file(result_path) if result_path.exists() else None,
            "test_count": payload.get("test_count"),
            "test_ids_count": len(payload.get("test_ids", [])),
            "execution_total": payload.get("execution_total"),
        }
    freeze = {
        "task_id": TASK_ID,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "operator_prep_exact_head": head,
        "python": platform.python_version(),
        "harness_manifest_sha256": manifest["manifest_sha256"],
        "harness_file_count": manifest["harness_file_count"],
        "bootstrap_sha256": sha256_file(bootstrap),
        "wheel_lock_sha256": sha256_file(wheel_lock),
        "wheel_lock_verification_sha256": sha256_file(wheel_verification) if wheel_verification.exists() else None,
        "clean_bootstrap_evidence_sha256": sha256_file(clean_bootstrap) if clean_bootstrap.exists() else None,
        "c1_c3_regression_sha256": sha256_file(evidence / "c1_c3_regression.json"),
        "c4_c9_regression_sha256": sha256_file(green_probe) if green_probe.exists() else None,
        "c10_c11_candidate_green_sha256": sha256_file(c10_c11_green) if c10_c11_green.exists() else None,
        "concurrency_integration_sha256": sha256_file(concurrency) if concurrency.exists() else None,
        "durability_fault_evidence_sha256": sha256_file(durability) if durability.exists() else None,
        "c10_c11_baseline_red_sha256": sha256_file(operator_prep_root.parent.parent / "operator_prep_corrective_003/raw/baseline/BASELINE_RED.json") if (operator_prep_root.parent.parent / "operator_prep_corrective_003/raw/baseline/BASELINE_RED.json").exists() else None,
        "corrective_candidate_green_sha256": sha256_file(green_probe) if green_probe.exists() else None,
        "gate_results": gate_results,
        "gate_summary": summary.get("gates", {}),
        "gate_summary_status": summary.get("status"),
        "launch_packet_present": packet.exists(),
        "launch_packet_sha256": sha256_file(packet) if packet.exists() else None,
        "packet_audit_present": audit.exists(),
        "packet_audit_sha256": sha256_file(audit) if audit.exists() else None,
        "frozen_after_gates": True,
        "freeze_coverage": "SHA256SUMS enumerates every package file including this freeze manifest, except SHA256SUMS itself",
        "mutation_policy": (
            "after this freeze the bootstrap, harness, tests, gate raw outputs, "
            "environment record, manifest and packet are immutable; any change "
            "requires a new operator-prep window"
        ),
    }
    path = evidence / "FREEZE_MANIFEST.json"
    path.write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")
    return freeze


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["manifest", "sha256sums", "freeze"])
    parser.add_argument("--operator-prep-root", required=True)
    parser.add_argument("--head", default=None)
    args = parser.parse_args()
    root = pathlib.Path(args.operator_prep_root).resolve()
    if args.stage == "manifest":
        print(json.dumps(write_manifest(root), indent=2))
    elif args.stage == "sha256sums":
        print(write_sha256sums(root))
    else:
        print(json.dumps(write_freeze_manifest(root, args.head), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
