"""Test-only path helpers (no semantics, no fixture access)."""

from __future__ import annotations

import os
import pathlib
import tempfile

HARNESS_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE_ROOT = HARNESS_ROOT / "aios_exchange"


def repo_root() -> pathlib.Path:
    configured = os.environ.get("AIOS_REPO_ROOT")
    if configured:
        return pathlib.Path(configured)
    return HARNESS_ROOT.parents[4]


def core_source_path() -> pathlib.Path:
    configured = os.environ.get("AIOS_FROZEN_CORE_SOURCE")
    if configured:
        return pathlib.Path(configured)
    return repo_root() / "src" / "aios_core" / "runtime" / "turn_runtime.py"


def evidence_dir(name: str) -> pathlib.Path:
    configured = os.environ.get("AIOS_GATE_EVIDENCE_DIR")
    base = pathlib.Path(configured) if configured else pathlib.Path(tempfile.mkdtemp(prefix="aios-gate-"))
    target = base / name
    target.mkdir(parents=True, exist_ok=True)
    return target
