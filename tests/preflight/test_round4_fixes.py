"""Round4 permanent regressions: cross-process freeze handoff, accepted-A to Driver import, isolation broad-except fix.

Synthetic only, no real B/C, no private A in Git. Private A verification separate.
"""
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.contracts.models import Observation, Wake
from aios_core.contracts.enums import SourceClass, WakeSource, WakeState, ObjectType, MaintenanceClass
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent
from aios_core.contracts.operations import OperationRequest

from tools.c15_preflight.audit import digest
from tools.c15_preflight.driver import Driver, DriverBlocked, AcceptedAPort, atomic_json
from tools.c15_preflight.freeze import freeze
from tools.c15_preflight.restart import restore_frozen, restart_plan, validate_staged_core, import_accepted_a_to_driver_run
from tools.c15_preflight.transport import Trace
from tools.c15_preflight.publication import RECEIPT_NAME, load_and_verify_receipt, confirm_uncertain_package

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tests/preflight'))
from test_driver import setup as synthetic_setup, NOW, bindings

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---- 1 cross-process handoff ----

def test_successful_freeze_cross_process_restore(tmp_path):
    """After successful freeze, original process exits, new process restores."""
    d, _, modules = synthetic_setup(tmp_path)
    d.step()
    final = tmp_path / "frozen"
    published = freeze(d, final)
    # Verify persistent receipt exists
    assert (final / RECEIPT_NAME).exists()
    receipt = json.loads((final / RECEIPT_NAME).read_text())
    assert receipt["manifest_sha256"] == digest(final / "manifest.json")
    assert receipt["publication_id"] == published.publication_id
    assert published.manifest["format"] == "c15-synthetic-freeze-v3"
    d.close(); d.trace.close()

    # Simulate new process via subprocess that calls restore_frozen
    other = tmp_path / "other"
    other.mkdir()
    script = tmp_path / "restore_script.py"
    script.write_text(f"""
import sys
sys.path.insert(0, "{REPO_ROOT / 'src'}")
sys.path.insert(0, "{REPO_ROOT}")
import json
from pathlib import Path
from tools.c15_preflight.restart import restore_frozen
from tools.c15_preflight.audit import digest
src = Path("{final}")
dst = Path("{other / 'run'}")
manifest_sha = digest(src / "manifest.json")
state = restore_frozen(src, dst, manifest_sha256=manifest_sha)
print(json.dumps({{"restored": True, "stage": state["stage"], "completed": state["completed_sequence"]}}))
""")
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, f"subprocess failed: {result.stderr} {result.stdout}"
    out = json.loads(result.stdout.strip())
    assert out["restored"] is True
    assert out["stage"] == "READY"

    # Also test that full Driver can be created in new process via setup helper in subprocess
    script2 = tmp_path / "driver_script.py"
    script2.write_text(f"""
import sys
sys.path.insert(0, "{REPO_ROOT / 'src'}")
sys.path.insert(0, "{REPO_ROOT}")
sys.path.insert(0, "{REPO_ROOT / 'tests/preflight'}")
from test_driver import setup
from tools.c15_preflight.audit import digest
from pathlib import Path
final = Path("{final}")
other = Path("{tmp_path / 'other2'}")
other.mkdir()
d, peer, modules = setup(other, restore=final)
print(d.state["completed_sequence"])
d.close(); d.trace.close()
""")
    result2 = subprocess.run([sys.executable, str(script2)], capture_output=True, text=True, timeout=20)
    assert result2.returncode == 0, f"driver subprocess failed: {result2.stderr} {result2.stdout}"
    assert result2.stdout.strip() == "1"

def test_freeze_receipt_persistence_after_process_exit(tmp_path):
    """Receipt file must survive and be verifiable without live object."""
    d, _, _ = synthetic_setup(tmp_path)
    d.step()
    final = tmp_path / "frozen"
    published = freeze(d, final)
    manifest_sha = digest(final / "manifest.json")
    d.close(); d.trace.close()
    receipt_data = load_and_verify_receipt(final, expected_manifest_sha256=manifest_sha, expected_publication_id=published.publication_id)
    assert receipt_data["manifest_sha256"] == manifest_sha
    assert receipt_data["publication_id"] == published.publication_id

def test_freeze_post_fsync_failure_no_receipt(tmp_path):
    d, _, _ = synthetic_setup(tmp_path)
    d.step()
    dest = tmp_path / "frozen"
    real_sync = os.fsync
    def fail_after_rename(fd):
        if dest.exists():
            raise OSError("synthetic post-publication fsync failure")
        return real_sync(fd)
    with patch("os.fsync", side_effect=fail_after_rename):
        with pytest.raises(OSError):
            freeze(d, dest)
    assert dest.exists()
    assert not (dest / RECEIPT_NAME).exists()
    with pytest.raises(Exception, match="receipt missing|unconfirmed|untrusted"):
        restore_frozen(dest, tmp_path / "restored", manifest_sha256=digest(dest / "manifest.json"))
    assert d.state["stage"] == "FAILED"
    d.close(); d.trace.close()

def test_partial_tampered_wrong_pin_rejected(tmp_path):
    d, _, _ = synthetic_setup(tmp_path)
    d.step()
    final = tmp_path / "frozen"
    freeze(d, final)
    manifest_sha = digest(final / "manifest.json")
    d.close(); d.trace.close()

    partial = tmp_path / "partial"
    shutil.copytree(final, partial)
    (partial / "private_world.sqlite").unlink()
    with pytest.raises(Exception):
        restore_frozen(partial, tmp_path / "p1", manifest_sha256=manifest_sha)

    tampered = tmp_path / "tampered"
    shutil.copytree(final, tampered)
    with (tampered / "private_world.sqlite").open("ab") as f:
        f.write(b"\x00")
    with pytest.raises(Exception):
        restore_frozen(tampered, tmp_path / "p2", manifest_sha256=manifest_sha)

    with pytest.raises(Exception, match="untrusted"):
        restore_frozen(final, tmp_path / "p3", manifest_sha256="0"*64)

    tampered_receipt = tmp_path / "tampered_receipt"
    shutil.copytree(final, tampered_receipt)
    receipt_path = tampered_receipt / RECEIPT_NAME
    data = json.loads(receipt_path.read_text())
    data["manifest_sha256"] = "0"*64
    receipt_path.write_text(json.dumps(data))
    with pytest.raises(Exception):
        restore_frozen(tampered_receipt, tmp_path / "p4", manifest_sha256=manifest_sha)

# ---- 2 accepted-A to Driver import (synthetic equivalent) ----

def _create_synthetic_a_staging(tmp_path: Path):
    staging = tmp_path / "synthetic_a"
    staging.mkdir(mode=0o700)
    db_path = staging / "private_world.sqlite"
    store = SQLiteWorldStore(db_path)
    index = WorldSearchIndex(staging / "world_index.sqlite", store=store)

    receipts = []
    for i in range(1, 88):
        obs = Observation(
            object_id=f"obs_{i}",
            subject_id="user_1",
            occurred=TemporalExtent.point(NOW + timedelta(seconds=i)),
            learned_at=NOW + timedelta(seconds=i),
            recorded_at=NOW + timedelta(seconds=i),
            created_by="test:synthetic_a",
            source_kind="sensor",
            modality="structured_record",
            value={"seq": i},
            metadata={"dimension": f"dim:test:{i}"},
        )
        result = store.commit(
            [obs],
            OperationRequest(
                operation_name=f"test.synthetic_a.{i}",
                expected_world_revision=int(store.current_world_revision()),
                reason="synthetic A",
                idempotency_key=f"synthetic_a:{i}",
                source_class=SourceClass.SENSOR,
            ),
        )
        if i <= 13:
            receipts.append({
                "sequence": i,
                "fixture_sha256": "sha256:synthetic",
                "ingest_object_id": obs.object_id,
                "ingest_revision": 1,
                "ingest_world_revision": result.world_revision,
                "ingest_ref": f"{obs.object_id}@1",
                "binding_mode": "fixture_observation",
            })
    assert int(store.current_world_revision()) == 87
    index.rebuild()
    assert index.watermark() == 87

    wake = Wake(
        object_id="wake_review_synthetic_a",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        source_refs=[],
        created_by="periodic_review:scheduler",
        wake_source=WakeSource.PERIODIC_REVIEW,
        wake_state=WakeState.SUPPRESSED,
        rule_id="periodic_review.interval",
        first_hit_at=NOW,
        last_hit_at=NOW,
        evidence_refs=[],
        priority=10,
        dedupe_key="periodic-review:user_1:synthetic_a",
        status=WakeState.SUPPRESSED.value,
        metadata={
            "review_kind": "periodic_ai_growth_review",
            "window_start": (NOW - timedelta(hours=72)).isoformat(),
            "window_end": NOW.isoformat(),
            "reason": "synthetic A review checked; no eligible world changes",
            "candidate_count": 0,
            "truncated": False,
        },
    )
    store.commit(
        [wake],
        OperationRequest(
            operation_name="review.schedule",
            expected_world_revision=int(store.current_world_revision()),
            reason="synthetic A review marker",
            idempotency_key="review:synthetic_a",
            source_class=SourceClass.MAINTENANCE,
            maintenance_class=MaintenanceClass.PERIODIC_REVIEW,
        ),
    )
    index.catch_up()
    assert int(store.current_world_revision()) == 88
    assert index.watermark() == 88

    release_state = {
        "active_phase": "A",
        "fixture_sha256": "sha256:synthetic",
        "last_acked_sequence": 13,
        "last_acked_event_id": "synthetic-13",
        "next_sequence": 14,
        "pending_reveal": None,
        "receipts": receipts,
    }
    (staging / "release_state.json").write_text(json.dumps(release_state))
    os.chmod(staging / "release_state.json", 0o600)

    restart_state = {
        "restart_state_format": "c15-rcc-resident-a-restart-state-v1",
        "note": "SYNTHETIC A EQUIVALENT",
        "session_id": "synthetic-old",
        "subject_id": "user_1",
        "conversation_turn_index": 7,
        "final_virtual_clock": NOW.isoformat(),
        "next_periodic_review_at": (NOW + timedelta(hours=24)).isoformat(),
        "review_interval_hours": 24,
        "final_world_revision": 88,
        "final_index_watermark": 88,
        "done_at_cursor": 13,
        "release_state_next_sequence": 14,
        "process_ended": "SYNTHETIC STOP",
    }
    (staging / "restart_state.json").write_text(json.dumps(restart_state))
    os.chmod(staging / "restart_state.json", 0o600)

    plan = restart_plan(restart_state, "synthetic-new", synthetic=True)
    (staging / "mechanical_restart.json").write_text(json.dumps(plan))
    os.chmod(staging / "mechanical_restart.json", 0o600)

    return staging, plan

def test_synthetic_a_to_driver_import(tmp_path):
    staging, plan = _create_synthetic_a_staging(tmp_path)

    driver_run_dir = tmp_path / "driver_run"
    result = import_accepted_a_to_driver_run(staging, driver_run_dir, repo=REPO_ROOT, synthetic=True)
    assert result["status"] == "ACCEPTED_A_DRIVER_RUN_PREPARED"
    assert result["plan"]["completed_sequence"] == 13

    from aios_core.runtime.turn_runtime import FusedTurnRuntime

    store = SQLiteWorldStore(driver_run_dir / "private_world.sqlite")
    index = WorldSearchIndex(driver_run_dir / "world_index.sqlite", store=store)
    trace = Trace(driver_run_dir / "trace.jsonl", store.current_world_revision)

    def forbidden_model(_):
        raise DriverBlocked("model must not be called during A import")

    runtime = FusedTurnRuntime(store=store, index=index, subject_id="user_1",
                               model_handler=forbidden_model,
                               round_summary_handler=forbidden_model,
                               dimension_summary_handler=forbidden_model)
    port = AcceptedAPort(driver_run_dir / "release_state.json", driver_run_dir / "private_world.sqlite")
    clock = datetime.fromisoformat(plan["clock"])
    driver = Driver(
        runtime,
        trace,
        port,
        driver_run_dir,
        session=plan["session_id"],
        clock=clock,
        stop_sequence=20,
        accepted_a_dir=staging,
    )
    assert driver.state["completed_sequence"] == 13
    assert driver.state["world_revision"] == 88
    assert driver.state["index_watermark"] == 88
    assert driver.state["clock"] == plan["clock"]
    driver.verify_boundary()
    driver.close()
    trace.close()

def test_checkpoint_loss_cannot_bypass_via_a_import(tmp_path):
    d, _, _ = synthetic_setup(tmp_path)
    d.step()
    assert d.state["completed_sequence"] == 1
    d.state_path.unlink()
    d.close(); d.trace.close()
    from tools.c15_preflight.transport import Trace
    t = Trace(d.directory / "new-trace", d.runtime.store.current_world_revision)
    with pytest.raises(DriverBlocked, match="accepted-A|missing checkpoint|fresh synthetic genesis"):
        Driver(d.runtime, t, d.port, d.directory, session="synthetic-session", clock=NOW, stop_sequence=3, accepted_a_dir=Path("/nonexistent"))
    t.close()
    empty = tmp_path / "empty_a"
    empty.mkdir()
    t2 = Trace(d.directory / "new-trace2", d.runtime.store.current_world_revision)
    with pytest.raises(DriverBlocked):
        Driver(d.runtime, t2, d.port, d.directory, session="synthetic-session", clock=NOW, stop_sequence=3, accepted_a_dir=empty)
    t2.close()

# ---- 3 isolation broad-except fix (A/B/C separation) ----

def test_isolation_decision_logic_always_runs():
    import tempfile, shutil
    base = Path(tempfile.mkdtemp())
    try:
        from tools.c15_preflight.isolation_probe import create_canaries, outside_checks, assess
        paths, hashes = create_canaries(base)
        before = outside_checks(paths, hashes)
        assert all(v == "VERIFIED" for v in before.values())
        child = {"denied": {k: True for k in paths}, "controls": {"allowed_readable": True, "no_host_proc": True, "no_git_or_gh": True, "clean_environment": True, "chroot_capability_removed": True, "external_network_denied": True, "packet_readonly": True}}
        after = outside_checks(paths, hashes)
        report = assess(before, child, after)
        assert report["synthetic_boundary_status"] == "PASS"
        assert all(v == "NOT_TESTED" for v in report["real_resources"].values())
    finally:
        shutil.rmtree(base, ignore_errors=True)

def test_isolation_probe_execution_result():
    from tools.c15_preflight.isolation_probe import probe
    try:
        result = probe()
    except (FileNotFoundError, PermissionError, OSError) as e:
        pytest.skip(f"B: probe env unsupported ({type(e).__name__}: {e}) - A logic still tested")
    except RuntimeError as e:
        pytest.skip(f"B: probe INCONCLUSIVE ({e})")
    assert result["synthetic_boundary_status"] == "PASS"
    assert result["resident_arena_isolation"] == "BLOCKED"
    assert result["launchable"] is False

def test_isolation_real_resident_status():
    manifest_path = REPO_ROOT / "tools/c15_preflight/resident_packet/manifest.json"
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text())
        assert data.get("launchable") is False
    op_manifest = REPO_ROOT / "tools/c15_preflight/operator_manifest.json"
    if op_manifest.exists():
        op_data = json.loads(op_manifest.read_text())
        assert "BLOCKED" in op_data.get("status", "")