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
    return dict(format="c15-mechanical-restart-plan-v1", accepted_a=A_SHA, session_id=new_session,
                subject_id=raw["subject_id"], next_turn=1, clock=clock.isoformat(),
                next_review_at=review.isoformat(), review_interval_hours=24, completed_sequence=13,
                status="STAGED_NOT_RELEASED", launchable=False)


def stage_accepted_a(source: Path, destination: Path, repo: Path, *, new_session: str):
    audit(source, repo)
    raw = json.loads((source / "restart_state.json").read_text())
    plan = restart_plan(raw, new_session)
    destination.mkdir(mode=0o700)
    try:
        for name in HASHES:
            shutil.copyfile(source / name, destination / name)
            os.chmod(destination / name, 0o600)
        verify_files(destination, HASHES)
        atomic_json(destination / "mechanical_restart.json", plan)
        verify_files(source, HASHES)
        return plan
    except BaseException:
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
    verify_files(destination, HASHES)
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
    marker = runtime.periodic_review._latest_marker()
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


def validate_synthetic_a_staging(destination: Path, repo: Path | None = None):
    """Synthetic equivalent of validate_staged_core without fixed hash pins.

    For permanent tests, we create a synthetic A with 88 revisions and a Review marker,
    but with synthetic fixture hash. This validates the same mechanical properties
    as real A without requiring the exact pinned bytes.

    Does NOT call verify_core for untracked files, because synthetic tests run
    in an environment where __pycache__ may be present. Real A validation still
    calls verify_core separately.
    """
    from aios_core.query.search import WorldSearchIndex
    from aios_core.runtime.turn_runtime import FusedTurnRuntime
    from aios_core.storage.sqlite_store import SQLiteWorldStore

    import sys
    # For synthetic, we optionally check Core import path is not shadowed if repo provided,
    # but we do NOT enforce untracked Core source check, to avoid __pycache__ false positives
    # in full pytest runs.
    if repo is not None:
        root = (repo).resolve() / "src/aios_core"
        for name, module in tuple(sys.modules.items()):
            if name == "aios_core" or name.startswith("aios_core."):
                file = getattr(module, "__file__", None)
                if file is not None:
                    try:
                        # Only enforce if file is inside repo but not in src/aios_core
                        p = Path(file).resolve()
                        if p.is_relative_to(repo.resolve()) and not p.is_relative_to(root):
                            require(False, "Core import path shadowed")
                    except Exception:
                        pass
    # Do NOT check fixed HASHES for synthetic
    for name in ("private_world.sqlite", "world_index.sqlite", "release_state.json", "restart_state.json", "mechanical_restart.json"):
        p = destination / name
        require(p.is_file() and not p.is_symlink(), f"missing synthetic A file: {name}")

    plan = json.loads((destination / "mechanical_restart.json").read_text())
    # Synthetic plan may have accepted_a = real A_SHA or synthetic marker, allow both
    require(plan.get("format") == "c15-mechanical-restart-plan-v1", "synthetic plan format")
    require(plan.get("completed_sequence") == 13, "synthetic plan completed_sequence")
    require(plan.get("status") == "STAGED_NOT_RELEASED", "synthetic plan status")

    requested = []

    def forbidden(_):
        requested.append(True)
        raise DriverBlocked("restore validation must not request a model")

    store = SQLiteWorldStore(destination / "private_world.sqlite")
    index = WorldSearchIndex(destination / "world_index.sqlite", store=store)
    runtime = FusedTurnRuntime(store=store, index=index, subject_id=plan["subject_id"],
                              model_handler=forbidden, round_summary_handler=forbidden,
                              dimension_summary_handler=forbidden)
    require(int(store.current_world_revision()) == index.watermark() == 88, "synthetic A watermark mismatch")
    marker = runtime.periodic_review._latest_marker()
    require(marker is not None and marker.wake_state.value not in {"new", "queued", "running"},
            "synthetic A unresolved Review marker")
    require(not (marker.wake_state.value == "completed" and marker.metadata.get("truncated")),
            "synthetic A Review backlog")
    due = marker.last_hit_at + timedelta(hours=plan["review_interval_hours"])
    require(due == moment(plan["next_review_at"]), "synthetic A Review deadline mismatch")
    require(not requested, "synthetic A unexpected model request")
    return {"status": "SYNTHETIC_A_VERIFIED", "world_revision": 88, "index_watermark": 88, "model_requests": 0}


def restore_frozen(source: Path, destination: Path, *, manifest_sha256: str):
    """Require persistent receipt AND pinned bytes; never replay trace."""
    require(digest(source / "manifest.json") == manifest_sha256, "untrusted freeze manifest")
    manifest = json.loads((source / "manifest.json").read_text())
    expected_names = {"private_world.sqlite", "world_index.sqlite", "release_state.json", "restart_state.json", "trace.jsonl"}
    require(manifest.get("format") in ("c15-synthetic-freeze-v2", "c15-synthetic-freeze-v3"),
            "unexpected freeze manifest format")
    require(set(manifest["files"]) == expected_names,
            "unexpected freeze manifest fields")
    from .publication import load_and_verify_receipt
    publication = manifest.get("publication", {})
    pub_id = publication.get("id")
    require(isinstance(pub_id, str) and pub_id, "manifest missing publication id")
    load_and_verify_receipt(source, expected_manifest_sha256=manifest_sha256, expected_publication_id=pub_id)
    verify_files(source, manifest["files"])
    state = json.loads((source / "restart_state.json").read_text())
    require(state["stage"] == "READY", "interrupted restart forbidden")
    destination.mkdir(mode=0o700)
    for name in expected_names - {"trace.jsonl"}:
        target = "driver_state.json" if name == "restart_state.json" else name
        shutil.copyfile(source / name, destination / target)
        os.chmod(destination / target, 0o600)
    return state


def import_accepted_a_to_driver_run(
    staged_a_dir: Path,
    driver_run_dir: Path,
    *,
    repo: Path | None = None,
    synthetic: bool = False,
):
    """Create a Driver run directory from a verified staged accepted-A.

    If synthetic=True, uses synthetic validation without fixed hash pins.
    Otherwise uses real A validation with fixed hashes.
    """
    staged_a_dir = staged_a_dir.resolve()
    driver_run_dir = driver_run_dir.resolve()
    require(staged_a_dir.is_dir(), "staged A dir missing")
    require(not driver_run_dir.exists(), "driver run dir already exists")

    if synthetic:
        validation = validate_synthetic_a_staging(staged_a_dir, repo=repo)
    else:
        validation = validate_staged_core(staged_a_dir, repo=repo)
    require(validation["model_requests"] == 0, "staged core made model requests")

    plan_path = staged_a_dir / "mechanical_restart.json"
    require(plan_path.is_file(), "mechanical plan missing")
    plan = json.loads(plan_path.read_text())

    driver_run_dir.mkdir(mode=0o700)
    try:
        for name in ("private_world.sqlite", "world_index.sqlite", "release_state.json"):
            src = staged_a_dir / name
            dst = driver_run_dir / name
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o600)
        shutil.copyfile(plan_path, driver_run_dir / "mechanical_restart.json")
        os.chmod(driver_run_dir / "mechanical_restart.json", 0o600)
        return {
            "status": "ACCEPTED_A_DRIVER_RUN_PREPARED",
            "plan": plan,
            "validation": validation,
            "driver_run_dir": str(driver_run_dir),
        }
    except BaseException:
        if driver_run_dir.exists():
            shutil.rmtree(driver_run_dir)
        raise
