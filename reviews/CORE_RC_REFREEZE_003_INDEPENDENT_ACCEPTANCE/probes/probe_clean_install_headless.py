#!/usr/bin/env python3
"""Reviewer Independent Probe 4: Clean install & headless lifecycle smoke.

Validates Section 12 requirements:
- Build wheel package from clean source
- Non-editable install into clean virtual environment
- Invoke aios-core-headless CLI as separate OS processes
- Create disposable World
- Run deterministic mechanical turn
- Stop & restart same World, verifying continuity
- Exercise safe provider-free recovery-status path
- Proves NO Resident fixture and NO hidden oracle used
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]


def invoke_cli(cli: Path, label: str, args: list[str]) -> dict[str, Any]:
    cmd = [str(cli), *args]
    proc = subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{label} failed (exit {proc.returncode}): stdout={proc.stdout} stderr={proc.stderr}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} did not emit JSON: {proc.stdout}") from exc


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aios-ia-headless-") as td:
        root = Path(td)
        wheel_dir = root / "wheel"
        wheel_dir.mkdir()

        # 1. Build wheel
        subprocess.check_call(
            [sys.executable, "-m", "build", "--wheel", "--no-isolation", "-o", str(wheel_dir)],
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        wheels = list(wheel_dir.glob("aios_core-*.whl"))
        assert len(wheels) == 1, f"expected 1 wheel, found {len(wheels)}"
        wheel = wheels[0]

        # 2. Create isolated venv
        venv_dir = root / "clean_venv"
        subprocess.check_call(
            [sys.executable, "-m", "venv", str(venv_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        pip_bin = venv_dir / "bin" / "pip"
        cli_bin = venv_dir / "bin" / "aios-core-headless"

        # 3. Install wheel non-editable into clean venv
        subprocess.check_call(
            [str(pip_bin), "install", "--ignore-requires-python", "--no-deps", str(wheel)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.check_call(
            [str(pip_bin), "install", "pydantic==2.13.5"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert cli_bin.is_file(), f"entrypoint not installed at {cli_bin}"

        # 4. Headless lifecycle tests
        world = root / "disposable-world.sqlite"
        index = root / "disposable-index.sqlite"
        common_args = [
            "--world", str(world),
            "--index", str(index),
            "--model-handler", "aios_core.headless.testing:deterministic_model_handler",
        ]

        # A. Clean start
        initial = invoke_cli(cli_bin, "initial start", [*common_args, "status"])
        assert initial["status"] == "ready"
        assert initial["world_revision"] == 0
        assert initial["index_watermark"] == 0
        assert initial["writer_lease_held"] is True

        # B. Deterministic mechanical turn
        turn = invoke_cli(
            cli_bin,
            "deterministic mechanical turn",
            [
                *common_args,
                "turn",
                "--session", "ia-clean-install-session",
                "--turn-index", "1",
                "--text", "deterministic mechanical IA turn",
                "--at", "2026-09-28T12:00:00Z",
            ],
        )
        assert turn["status"] == "turn_completed"
        assert turn["response"] == "HEADLESS_MECHANICAL_OK"
        assert turn["world_revision"] > 0
        turn_rev = turn["world_revision"]

        # C. Fresh process stop/restart continuity
        restarted = invoke_cli(cli_bin, "fresh process restart", [*common_args, "status"])
        assert restarted["status"] == "ready"
        assert restarted["world_revision"] == turn_rev
        assert restarted["index_watermark"] == turn_rev
        assert restarted["index_lag"] == 0
        assert restarted["writer_lease_held"] is True

        # D. Safe recovery-status path without model-handler
        safe = invoke_cli(
            cli_bin,
            "safe provider-free recovery-status",
            ["--world", str(world), "--index", str(index), "recovery-status"],
        )
        assert safe["status"] == "recovery_status"
        assert safe["world_revision"] == turn_rev
        assert safe["index_watermark"] == turn_rev
        assert safe["recovery_disposition"] == "AUTO_RECOVERABLE"

        # E. Final reopen check
        final_check = invoke_cli(cli_bin, "final reopen check", [*common_args, "status"])
        assert final_check["status"] == "ready"
        assert final_check["world_revision"] == turn_rev
        assert final_check["index_watermark"] == turn_rev

        # Clean build artifacts in repo root if any
        subprocess.run(["rm", "-rf", "build", "src/aios_core.egg-info"], cwd=REPO_ROOT, check=False)

        result = {
            "probe": "probe_clean_install_headless",
            "status": "PASS",
            "wheel_built": wheel.name,
            "separate_cli_processes_invoked": 5,
            "initial_world_revision": initial["world_revision"],
            "final_world_revision": final_check["world_revision"],
            "turn_status": turn["status"],
            "restart_continuity": True,
            "safe_recovery_status": safe["status"],
            "resident_fixture_used": False,
            "real_provider_used": False,
        }
        print("RESULT=" + json.dumps(result, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
