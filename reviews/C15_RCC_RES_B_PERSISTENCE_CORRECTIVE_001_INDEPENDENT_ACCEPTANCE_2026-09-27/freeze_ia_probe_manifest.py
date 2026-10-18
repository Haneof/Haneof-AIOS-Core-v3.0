#!/usr/bin/env python3
"""Freeze the Independent Acceptance probe manifest BEFORE first execution.

Ordering is mechanical:
  1. hash every probe file (SHA-256)
  2. pytest --collect-only  -> probe_enumeration.txt + collect_only.txt
  3. write PROBE_MANIFEST.json + PROBE_MANIFEST.sha256
The execution job verifies the frozen manifest hash before running anything.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE_FILES = ["ia_probes.py", "ia_child.py"]
CANDIDATE = "63ca592359c7e3fd71d6cc4ba349949e4f0b80e3"
STAGE_B = "15c75ac3e97c57a5fa1f3085c282a852994d9acf"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    repo = Path(os.environ.get("IA_CANDIDATE_REPO", Path.cwd())).resolve()
    files = {}
    for name in PROBE_FILES:
        p = HERE / name
        files[name] = sha256_bytes(p.read_bytes())

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(repo / "src"), str(repo)])
    env["IA_CANDIDATE_REPO"] = str(repo)

    collect = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-o", "addopts=", "-p", "no:cacheprovider",
         "--timeout=600", str(HERE / "ia_probes.py")],
        cwd=str(HERE), env=env, capture_output=True, text=True, timeout=1800,
    )
    (HERE / "collect_only.txt").write_text(
        f"returncode={collect.returncode}\n--- stdout ---\n{collect.stdout}\n"
        f"--- stderr ---\n{collect.stderr}\n")
    if collect.returncode != 0 or "::" not in collect.stdout:
        print("COLLECT-ONLY FAILED -- full output follows", flush=True)
        print(collect.stdout, flush=True)
        print(collect.stderr, flush=True)
        return 1

    enum_lines = [l for l in collect.stdout.splitlines()
                  if "::" in l and not l.startswith(" ")]
    (HERE / "probe_enumeration.txt").write_text("\n".join(enum_lines) + "\n")

    groups: dict[str, int] = {}
    for l in enum_lines:
        g = l.split("[")[0].split("::")[0]
        key = "GROUP_A" if "groupA" in l else (
            "GROUP_B" if "groupB" in l else (
                "GROUP_C" if "groupC" in l else (
                    "GROUP_D" if "groupD" in l else (
                        "GROUP_E" if "groupE" in l else "GROUP_F"))))
        groups[key] = groups.get(key, 0) + 1

    manifest = {
        "manifest_version": "ia-probe-manifest-v1",
        "task": "C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE",
        "tested_exact_candidate": CANDIDATE,
        "canonical_stage_b_commit": STAGE_B,
        "author": "Independent Persistence Corrective Acceptance Reviewer",
        "frozen_before_first_execution": True,
        "probe_file_sha256": files,
        "probe_count": len(enum_lines),
        "probes_by_group": dict(sorted(groups.items())),
        "enumeration": enum_lines,
        "enumeration_sha256": sha256_bytes((HERE / "probe_enumeration.txt").read_bytes()),
        "collect_only_sha256": sha256_bytes((HERE / "collect_only.txt").read_bytes()),
    }
    raw = json.dumps(manifest, indent=2, sort_keys=True).encode()
    (HERE / "PROBE_MANIFEST.json").write_bytes(raw)
    (HERE / "PROBE_MANIFEST.sha256").write_text(
        f"{sha256_bytes(raw)}  PROBE_MANIFEST.json\n")
    print(f"frozen {len(enum_lines)} probes: {groups}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
