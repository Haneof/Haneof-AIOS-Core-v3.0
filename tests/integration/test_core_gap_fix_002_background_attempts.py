from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import ObjectType, SourceClass, WakeSource
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import WakeSignalRequest


NOW = datetime(2026, 9, 24, 6, 0, tzinfo=timezone.utc)


def _world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _seed_review_fact(store: SQLiteWorldStore) -> None:
    fact = Observation(
        object_id="obs_gap_fix_002_review_fact",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=1)),
        learned_at=NOW - timedelta(hours=1),
        recorded_at=NOW - timedelta(hours=1),
        created_by="test:core-gap-fix-002",
        source_kind="conversation",
        modality="text",
        value="A durable fact eligible for periodic review.",
        metadata={"dimension": "dim:test"},
    )
    store.commit(
        [fact],
        OperationRequest(
            operation_name="test.core_gap_fix_002.seed_review_fact",
            expected_world_revision=0,
            reason="seed periodic review fact",
            idempotency_key="core-gap-fix-002:seed-review-fact",
            source_class=SourceClass.USER,
        ),
    )


def test_before_fix_running_wake_can_blindly_reinvoke_provider_after_ambiguous_failure(tmp_path):
    store, index = _world(tmp_path)
    calls = []

    def ambiguous_provider(snapshot):
        calls.append(("first", snapshot.round_index))
        raise TimeoutError("provider may already have accepted the request")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=ambiguous_provider,
    )
    signal = runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id="core-gap-fix-002.wake",
            observed_at=NOW,
            dedupe_key="core-gap-fix-002:wake",
        )
    )

    with pytest.raises(TimeoutError, match="may already have accepted"):
        runtime.run_wake(
            wake_ref=ObjectRef(object_id=signal.wake_id, revision=signal.revision),
            now=NOW,
        )
    assert runtime.wake_bus.current_wake(signal.wake_id).wake_state.value == "running"

    reopened = SQLiteWorldStore(tmp_path / "world.db")
    reopened_index = WorldSearchIndex(tmp_path / "world.db", store=reopened)
    reopened_index.rebuild()

    def retrying_provider(snapshot):
        calls.append(("restart", snapshot.round_index))
        return ModelDirective(silence=True)

    restarted = FusedTurnRuntime(
        store=reopened,
        index=reopened_index,
        model_handler=retrying_provider,
    )
    restarted.run_wake(
        wake_ref=ObjectRef(object_id=signal.wake_id, revision=signal.revision),
        now=NOW + timedelta(minutes=5),
    )

    # Correct recovery must refuse the blind second provider invocation.
    assert calls == [("first", 0)]


def test_before_fix_running_periodic_review_can_blindly_reinvoke_provider_after_ambiguous_failure(tmp_path):
    store, index = _world(tmp_path)
    _seed_review_fact(store)
    index.catch_up()
    calls = []

    def ambiguous_provider(snapshot):
        calls.append(("first", snapshot.round_index))
        raise TimeoutError("review provider may already have accepted the request")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=ambiguous_provider,
    )
    with pytest.raises(TimeoutError, match="may already have accepted"):
        runtime.run_periodic_review(now=NOW)

    running = [
        payload
        for payload in store.list_payloads(object_type=ObjectType.WAKE, subject_id="user_1")
        if payload.get("wake_state") == "running"
        and (payload.get("metadata") or {}).get("review_kind") == "periodic_review"
    ]
    assert len(running) == 1

    reopened = SQLiteWorldStore(tmp_path / "world.db")
    reopened_index = WorldSearchIndex(tmp_path / "world.db", store=reopened)
    reopened_index.rebuild()

    def retrying_provider(snapshot):
        calls.append(("restart", snapshot.round_index))
        return ModelDirective(silence=True)

    restarted = FusedTurnRuntime(
        store=reopened,
        index=reopened_index,
        model_handler=retrying_provider,
    )
    restarted.run_periodic_review(now=NOW + timedelta(minutes=5))

    # Correct recovery must refuse the blind second provider invocation.
    assert calls == [("first", 0)]
