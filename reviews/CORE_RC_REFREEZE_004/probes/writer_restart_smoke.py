#!/usr/bin/env python3
"""CORE-RC-REFREEZE-004 §11 writer / restart / no-duplicate-effect proof.

Runs only against the exact frozen software worktree supplied in
AIOS_RC_TARGET_ROOT.  Proves canonical same-World writer exclusion, that lock
overrides are validation-only and cannot create a second writer, that stale
diagnostic lock metadata cannot block a legal restart, that a clean stop /
restart preserves World and projection continuity, and that re-submitting the
same turn after restart is an effect-free idempotent replay (no provider
redispatch, no duplicate meter, no duplicate effect).
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import aios_core
from aios_core.headless.core import (
    HeadlessConfig,
    HeadlessCore,
    HeadlessConfigurationError,
    HeadlessWriterBusy,
)
from aios_core.headless.testing import deterministic_model_handler
from aios_core.runtime import TurnAlreadyCompleted


def _assert_target_import() -> Path:
    raw_target = os.environ.get("AIOS_RC_TARGET_ROOT")
    if not raw_target:
        raise RuntimeError("AIOS_RC_TARGET_ROOT must identify the exact software worktree")
    target = Path(raw_target).resolve()
    module_path = Path(aios_core.__file__).resolve()
    if target not in module_path.parents:
        raise RuntimeError(
            f"wrong aios_core import: {module_path}; expected below exact target {target}"
        )
    return target


TARGET = _assert_target_import()
NOW = datetime(2026, 10, 4, 9, 0, tzinfo=timezone.utc)

_SUBPROCESS_PROBE = """
import json, sys
from pathlib import Path
from aios_core.headless.core import HeadlessConfig, HeadlessCore, HeadlessWriterBusy
world, index = sys.argv[1], sys.argv[2]
try:
    HeadlessCore(
        config=HeadlessConfig(world_path=Path(world), index_path=Path(index)),
        model_handler=lambda snapshot: None,
    ).start()
except HeadlessWriterBusy as exc:
    print(json.dumps({"result": "WRITER_BUSY", "detail": str(exc)}))
else:
    print(json.dumps({"result": "SECOND_WRITER_STARTED"}))
"""


def main() -> int:
    report: dict[str, Any] = {
        "status": "WRITER_RESTART_FAILED",
        "target_root": str(TARGET),
        "aios_core_import": str(Path(aios_core.__file__).resolve()),
        "real_provider_used": False,
        "resident_fixture_used": False,
    }
    checks: dict[str, Any] = {}

    with tempfile.TemporaryDirectory(prefix="aios-rc004-writer-") as raw:
        root = Path(raw)
        world = root / "world.sqlite"
        index = root / "index.sqlite"
        canonical_lock = Path(str(world) + ".writer.lock")

        core1 = HeadlessCore(
            config=HeadlessConfig(world_path=world, index_path=index),
            model_handler=deterministic_model_handler,
        ).start()
        status1 = core1.status()
        checks["first_writer_lease_held"] = status1["writer_lease_held"] is True

        # 1. a second writer for the same canonical World is refused in-process
        second = HeadlessCore(
            config=HeadlessConfig(world_path=world, index_path=index),
            model_handler=deterministic_model_handler,
        )
        try:
            second.start()
        except HeadlessWriterBusy:
            checks["second_writer_refused_in_process"] = True
        else:
            checks["second_writer_refused_in_process"] = False
            second.stop()

        # 2. a second writer in a fresh OS process is refused by the same lease
        completed = subprocess.run(
            [sys.executable, "-c", _SUBPROCESS_PROBE, str(world), str(index)],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(TARGET / "src")},
            check=False,
        )
        checks["second_writer_refused_fresh_process"] = (
            completed.returncode == 0 and "WRITER_BUSY" in completed.stdout
        )
        checks["second_writer_process_stdout"] = completed.stdout.strip()

        # 3. a lock override is validation-only and cannot select a second lease
        try:
            HeadlessConfig(
                world_path=world, index_path=index, lock_path=str(root / "override.lock")
            )
        except HeadlessConfigurationError:
            checks["lock_override_refused"] = True
        else:
            checks["lock_override_refused"] = False

        # 4. stale diagnostic metadata cannot be used to decide World state
        canonical_lock.write_text(
            json.dumps(
                {
                    "kind": "aios-headless-writer-lease-v1",
                    "pid": 999999,
                    "host": "stale-host",
                    "world_lock_path": str(canonical_lock),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        checks["stale_metadata_written_while_held"] = canonical_lock.exists()

        # 5. one ordinary turn, then clean stop / restart
        first = core1.submit_user_turn(
            session_id="rc004-writer",
            turn_index=1,
            user_input="writer restart continuity",
            occurred_at=NOW,
        )
        revision_after_turn = core1.status()["world_revision"]
        checks["turn_completed"] = first.runtime.response is not None
        checks["revision_after_turn"] = revision_after_turn
        core1.stop()
        checks["lease_released_on_stop"] = core1._lease.held is False

        # canonical lock file with stale metadata exists, but no OS lease is held,
        # so a fresh writer must start (metadata is diagnostic only)
        restarted = HeadlessCore(
            config=HeadlessConfig(world_path=world, index_path=index),
            model_handler=deterministic_model_handler,
        ).start()
        status2 = restarted.status()
        checks["restart_after_stale_metadata"] = status2["status"] == "ready"
        checks["restart_world_revision_preserved"] = (
            status2["world_revision"] == revision_after_turn
        )
        checks["restart_index_watermark_matches"] = (
            status2["index_watermark"] == status2["world_revision"]
        )
        checks["restart_index_lag_zero"] = status2["index_lag"] == 0

        # 6. the same turn re-submitted after restart is an effect-free replay
        meters_before = len(restarted.runtime.metering.list_model_calls(subject_id="user_1"))
        replay_error = None
        try:
            restarted.submit_user_turn(
                session_id="rc004-writer",
                turn_index=1,
                user_input="writer restart continuity",
                occurred_at=NOW,
            )
        except TurnAlreadyCompleted as exc:
            replay_error = type(exc).__name__
        meters_after = len(restarted.runtime.metering.list_model_calls(subject_id="user_1"))
        checks["completed_turn_replay_refused"] = replay_error == "TurnAlreadyCompleted"
        checks["replay_revision_unchanged"] = (
            restarted.status()["world_revision"] == revision_after_turn
        )
        checks["replay_meters_unchanged"] = meters_before == meters_after
        checks["meters_after_restart"] = meters_after
        restarted.stop()

        all_ok = (
            checks["first_writer_lease_held"]
            and checks["second_writer_refused_in_process"]
            and checks["second_writer_refused_fresh_process"]
            and checks["lock_override_refused"]
            and checks["turn_completed"]
            and checks["lease_released_on_stop"]
            and checks["restart_after_stale_metadata"]
            and checks["restart_world_revision_preserved"]
            and checks["restart_index_watermark_matches"]
            and checks["restart_index_lag_zero"]
            and checks["completed_turn_replay_refused"]
            and checks["replay_revision_unchanged"]
            and checks["replay_meters_unchanged"]
        )
        report["checks"] = checks
        report["status"] = "WRITER_RESTART_PASS" if all_ok else "WRITER_RESTART_FAILED"
        print("RESULT=" + json.dumps(report, sort_keys=True))
        return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
