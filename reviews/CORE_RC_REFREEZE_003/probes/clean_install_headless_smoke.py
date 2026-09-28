#!/usr/bin/env python3
"""Fresh-wheel headless lifecycle smoke for CORE-RC-REFREEZE-003.

This is release evidence only. It uses the package's deterministic mechanical
adapter, invokes the installed console script as separate processes, and never
uses a real model/provider or a Resident fixture.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


def invoke(cli: str, label: str, args: list[str], *, safe_recovery: bool = False) -> dict[str, Any]:
    env = os.environ.copy()
    for name in ("AIOS_WORLD_PATH", "AIOS_INDEX_PATH", "AIOS_LOCK_PATH", "AIOS_MODEL_HANDLER"):
        env.pop(name, None)
    completed = subprocess.run(
        [cli, *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    print(f"--- {label}: exit={completed.returncode} ---")
    print(completed.stdout.rstrip())
    if completed.stderr:
        print("STDERR:")
        print(completed.stderr.rstrip())
    if completed.returncode != 0:
        raise RuntimeError(f"{label} exited {completed.returncode}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} did not emit one JSON result") from exc
    if safe_recovery and result.get("status") != "recovery_status":
        raise AssertionError(f"safe recovery-status path returned {result!r}")
    return result


def main() -> int:
    cli = sys.argv[1] if len(sys.argv) > 1 else "aios-core-headless"
    cli_path = Path(cli).resolve()
    if not cli_path.exists():
        raise SystemExit(f"installed entrypoint not found: {cli}")

    with tempfile.TemporaryDirectory(prefix="aios-rc-refreeze-003-headless-") as raw:
        root = Path(raw)
        world = root / "disposable-world.sqlite"
        index = root / "disposable-index.sqlite"
        common = [
            "--world",
            str(world),
            "--index",
            str(index),
            "--model-handler",
            "aios_core.headless.testing:deterministic_model_handler",
        ]

        initial = invoke(str(cli_path), "initial clean start", [*common, "status"])
        assert initial["status"] == "ready"
        assert initial["world_revision"] == 0
        assert initial["index_watermark"] == 0

        turn = invoke(
            str(cli_path),
            "deterministic mechanical turn",
            [
                *common,
                "turn",
                "--session",
                "rc-refreeze-003-clean-install",
                "--turn-index",
                "1",
                "--text",
                "mechanical RC release smoke",
                "--at",
                "2026-09-28T12:00:00Z",
            ],
        )
        assert turn["status"] == "turn_completed"
        assert turn["response"] == "HEADLESS_MECHANICAL_OK"
        assert turn["summary_error"] is None

        # A new OS process proves the canonical World and projection reopen cleanly.
        restarted = invoke(str(cli_path), "fresh-process stop/restart", [*common, "status"])
        assert restarted["world_path"] == str(world)
        assert restarted["index_path"] == str(index)
        assert restarted["world_revision"] == turn["world_revision"]
        assert restarted["world_revision"] > 0
        assert restarted["index_watermark"] == restarted["world_revision"]
        assert restarted["index_lag"] == 0
        assert restarted["writer_lease_held"] is True

        # This path is intentionally invoked with no provider/model-handler option.
        safe = invoke(
            str(cli_path),
            "provider-free safe recovery-status",
            ["--world", str(world), "--index", str(index), "recovery-status"],
            safe_recovery=True,
        )
        assert safe["world_revision"] == restarted["world_revision"]
        assert safe["index_status"] == "ready"
        assert safe["index_watermark"] == restarted["world_revision"]
        assert safe["index_lag"] == 0

        # One more process start after the recovery-only path proves clean close/reopen.
        closed = invoke(str(cli_path), "clean close and final reopen", [*common, "status"])
        assert closed["world_revision"] == restarted["world_revision"]
        assert closed["index_watermark"] == closed["world_revision"]
        assert world.is_file() and index.is_file()

        result = {
            "status": "HEADLESS_CLEAN_INSTALL_PASS",
            "adapter": "aios_core.headless.testing:deterministic_model_handler",
            "real_provider_used": False,
            "resident_fixture_used": False,
            "world_path": "disposable-world.sqlite",
            "index_path": "disposable-index.sqlite",
            "initial_world_revision": initial["world_revision"],
            "final_world_revision": closed["world_revision"],
            "final_index_watermark": closed["index_watermark"],
            "restart_continuity": True,
            "safe_recovery_status": safe["status"],
            "clean_close_reopen": True,
            "separate_cli_processes": 5,
        }
        print("RESULT=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
