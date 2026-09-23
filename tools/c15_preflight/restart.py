"""Mechanical restart staging, never restoration of prior model decisions.

A restore test initializes Core services on a NEW COPY with a callback that
raises on any model request. This is not a Resident run or a B release.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import timedelta
from pathlib import Path

from .audit import A_SHA, HASHES, RESTART_KEYS, audit, digest, require, verify_files
from .driver import DriverBlocked, atomic_json, moment


def restart_plan(raw, new_session: str):
    require(set(raw) == RESTART_KEYS, "unreviewed restart fields")
    require(isinstance(new_session, str) and bool(new_session.strip()) and new_session == new_session.strip(),
            "new session must be canonical nonblank text")
    require(new_session != raw["session_id"], "cannot reuse A session")
    require(raw["restart_state_format"] == "c15-rcc-resident-a-restart-state-v1", "restart format")
    for key in ("conversation_turn_index", "review_interval_hours", "final_world_revision", "final_index_watermark",
                "done_at_cursor", "release_state_next_sequence"):
        require(type(raw[key]) is int and raw[key] > 0, f"invalid restart integer: {key}")
    require(raw["subject_id"] == "user_1", "restart subject mismatch")
    clock, review = moment(raw["final_virtual_clock"]), moment(raw["next_periodic_review_at"])
    require(review > clock, "invalid next Review deadline")
    require(raw["review_interval_hours"] == 24, "unapproved Review cadence")
    require(raw["done_at_cursor"] == 13 and raw["release_state_next_sequence"] == 14, "restart cursor mismatch")
    require(raw["final_world_revision"] == raw["final_index_watermark"] == 88, "restart watermark")
    # Intentionally omit note/process_ended/session transcript/old turn index.
    return dict(format="c15-mechanical-restart-plan-v1", accepted_a=A_SHA, session_id=new_session,
                subject_id=raw["subject_id"], next_turn=1, clock=clock.isoformat(),
                next_review_at=review.isoformat(), review_interval_hours=24, completed_sequence=13,
                status="STAGED_NOT_RELEASED", launchable=False)


def stage_accepted_a(source: Path, destination: Path, repo: Path, *, new_session: str):
    audit(source, repo)
    raw = json.loads((source / "restart_state.json").read_text())
    plan = restart_plan(raw, new_session)
    destination.mkdir(mode=0o700)  # Exclusive; never replace A or an existing run.
    try:
        for name in HASHES:
            shutil.copyfile(source / name, destination / name)
            os.chmod(destination / name, 0o600)
        verify_files(destination, HASHES)
        atomic_json(destination / "mechanical_restart.json", plan)
        verify_files(source, HASHES)
        return plan
    except BaseException:
        # Partial stage is not a valid run. Do not silently remove audit evidence.
        atomic_json(destination / "STAGING_FAILED.json", {"status": "BLOCKED"})
        raise


def validate_staged_core(destination: Path, repo: Path | None = None):
    from aios_core.query.search import WorldSearchIndex
    from aios_core.runtime.turn_runtime import FusedTurnRuntime
    from aios_core.storage.sqlite_store import SQLiteWorldStore

    from .audit import verify_core
    import sys
    root = (repo or Path.cwd()).resolve() / "src/aios_core"
    verify_core(root.parents[1])
    for name, module in tuple(sys.modules.items()):
        if name == "aios_core" or name.startswith("aios_core."):
            file = getattr(module, "__file__", None)
            require(file is not None and Path(file).resolve().is_relative_to(root), "Core import path shadowed")
    verify_files(destination, HASHES)  # Must be exact before ANY service initialization.
    plan = json.loads((destination / "mechanical_restart.json").read_text())
    expected = restart_plan(json.loads((destination / "restart_state.json").read_text()), plan["session_id"])
    require(plan == expected, "restart plan was edited")
    requested = []

    def forbidden(_):
        requested.append(True)
        raise DriverBlocked("restore validation must not request a model")

    store = SQLiteWorldStore(destination / "private_world.sqlite")
    index = WorldSearchIndex(destination / "world_index.sqlite", store=store)
    runtime = FusedTurnRuntime(store=store, index=index, subject_id=plan["subject_id"],
                              model_handler=forbidden, round_summary_handler=forbidden,
                              dimension_summary_handler=forbidden)
    require(int(store.current_world_revision()) == index.watermark() == 88, "Core restore changed watermarks")
    # Frozen Core's durable marker, not the operator's guess, supplies Review truth.
    marker = runtime.periodic_review._latest_marker()
    # Core also treats SUPPRESSED as a terminal scheduling marker (not semantic
    # success). Do not invent a completed-review requirement or Claim quota.
    require(marker is not None and marker.wake_state.value not in {"new", "queued", "running"},
            "unresolved/absent durable Review marker")
    require(not (marker.wake_state.value == "completed" and marker.metadata.get("truncated")),
            "Review backlog requires separate recovery review")
    due = marker.last_hit_at + timedelta(hours=plan["review_interval_hours"])
    require(due == moment(plan["next_review_at"]), "restart Review deadline disagrees with durable Core")
    require(not requested, "unexpected model request")
    return {"status": "COPY_SERVICE_RESTORE_VERIFIED_NOT_RELEASED", "world_revision": 88,
            "index_watermark": 88, "model_requests": 0, "review_deadline_matches_core": True,
            "limitations": ["no due work executed", "no real B release", "fresh session authorization pending"]}


def restore_frozen(source: Path, destination: Path, *, manifest_sha256: str, confirmation=None):
    """Require live publication confirmation AND pinned bytes; never replay trace.

    A dead controller/missing receipt or uncertain publication has no automatic
    recovery path here, even if the package's mechanical checkpoint says READY.
    """
    require(digest(source / "manifest.json") == manifest_sha256, "untrusted freeze manifest")
    manifest = json.loads((source / "manifest.json").read_text())
    expected_names = {"private_world.sqlite", "world_index.sqlite", "release_state.json", "restart_state.json", "trace.jsonl"}
    require(manifest.get("format") == "c15-synthetic-freeze-v2" and set(manifest["files"]) == expected_names,
            "unexpected freeze manifest fields")
    from .publication import require_confirmation
    publication = manifest.get("publication", {})
    require(publication.get("status") == "VALIDATED_NOT_CONFIRMED", "unexpected publication state")
    require_confirmation(confirmation, manifest_sha256=manifest_sha256,
                         publication_id=publication.get("id"))
    verify_files(source, manifest["files"])
    state = json.loads((source / "restart_state.json").read_text())
    require(state["stage"] == "READY", "interrupted restart forbidden")
    destination.mkdir(mode=0o700)
    for name in expected_names - {"trace.jsonl"}:
        target = "driver_state.json" if name == "restart_state.json" else name
        shutil.copyfile(source / name, destination / target)
        os.chmod(destination / target, 0o600)
    return state  # New callback/Trace must be supplied, not recovered from old trace.
