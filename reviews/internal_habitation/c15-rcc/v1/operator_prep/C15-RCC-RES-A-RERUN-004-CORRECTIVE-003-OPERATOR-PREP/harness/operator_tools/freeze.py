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

TASK_ID = "C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP"
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
    manifest = build_manifest(harness_root)
    manifest["scope"] = str(harness_root.relative_to(operator_prep_root))
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
    freeze = {
        "task_id": TASK_ID,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "operator_prep_exact_head": head,
        "python": platform.python_version(),
        "harness_manifest_sha256": manifest["manifest_sha256"],
        "harness_file_count": manifest["file_count"],
        "gate_summary": summary.get("gates", {}),
        "gate_summary_status": summary.get("status"),
        "launch_packet_present": packet.exists(),
        "launch_packet_sha256": sha256_file(packet) if packet.exists() else None,
        "packet_audit_present": audit.exists(),
        "packet_audit_sha256": sha256_file(audit) if audit.exists() else None,
        "frozen_after_gates": True,
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
