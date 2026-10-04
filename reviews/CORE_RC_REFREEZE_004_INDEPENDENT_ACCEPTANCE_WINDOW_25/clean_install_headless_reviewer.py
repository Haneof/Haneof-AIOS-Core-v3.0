#!/usr/bin/env python3
"""Window 25 reviewer-owned clean-wheel/headless lifecycle probe."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


def run_json(cli: Path, label: str, args: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    for key in ("AIOS_WORLD_PATH", "AIOS_INDEX_PATH", "AIOS_LOCK_PATH", "AIOS_MODEL_HANDLER"):
        env.pop(key, None)
    completed = subprocess.run(
        [str(cli), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    print(f"{label}: exit={completed.returncode}")
    print(completed.stdout.rstrip())
    if completed.stderr:
        print("stderr=" + completed.stderr.rstrip())
    assert completed.returncode == 0, (label, completed.returncode)
    return json.loads(completed.stdout)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: probe.py CLEAN_PYTHON INSTALLED_CLI")
    # Do not resolve the venv interpreter symlink: invoking its target directly
    # would discard the venv prefix and therefore test the wrong environment.
    clean_python = Path(sys.argv[1]).absolute()
    cli = Path(sys.argv[2]).resolve()
    assert clean_python.is_file()
    assert cli.is_file()

    identity = subprocess.check_output(
        [str(clean_python), "-c", "import aios_core; print(aios_core.__file__)"],
        text=True,
    ).strip()
    print("aios_core.__file__=" + identity)
    assert "site-packages" in identity

    with tempfile.TemporaryDirectory(prefix="rc004-window25-clean-") as raw:
        root = Path(raw)
        world = root / "world.sqlite"
        index = root / "index.sqlite"
        common = [
            "--world", str(world),
            "--index", str(index),
            "--model-handler", "aios_core.headless.testing:deterministic_model_handler",
        ]

        initial = run_json(cli, "initial", [*common, "status"])
        assert initial["status"] == "ready"
        assert initial["world_revision"] == initial["index_watermark"] == 0

        turn = run_json(
            cli,
            "turn",
            [
                *common,
                "turn",
                "--session", "window25-clean-install",
                "--turn-index", "1",
                "--text", "reviewer controlled mechanical turn",
                "--at", "2026-10-04T18:00:00Z",
            ],
        )
        assert turn["status"] == "turn_completed"
        assert turn["response"] == "HEADLESS_MECHANICAL_OK"
        assert turn["summary_error"] is None

        restarted = run_json(cli, "fresh-process-restart", [*common, "status"])
        assert restarted["world_path"] == str(world)
        assert restarted["index_path"] == str(index)
        assert restarted["world_revision"] == turn["world_revision"] > 0
        assert restarted["index_watermark"] == restarted["world_revision"]
        assert restarted["index_lag"] == 0

        safe = run_json(
            cli,
            "provider-free-recovery-status",
            ["--world", str(world), "--index", str(index), "recovery-status"],
        )
        assert safe["status"] == "recovery_status"
        assert safe["world_revision"] == restarted["world_revision"]
        assert safe["index_status"] == "ready"
        assert safe["index_watermark"] == restarted["world_revision"]

        final = run_json(cli, "clean-close-reopen", [*common, "status"])
        assert final["world_revision"] == restarted["world_revision"]
        assert final["index_watermark"] == final["world_revision"]
        assert world.is_file() and index.is_file()

    print("WINDOW25_CLEAN_INSTALL_HEADLESS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
