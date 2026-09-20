from datetime import datetime, timedelta, timezone

from aios_core.contracts.enums import SourceClass, WakeSource
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import (
    MechanicalWakeHit,
    MechanicalWakeRouter,
    MechanicalWakeRoutingPolicy,
    WakeStep0Decision,
    WakeStep0Outcome,
)


NOW = datetime(2026, 9, 20, 17, 0, tzinfo=timezone.utc)


def _seed(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    observations = [
        Observation(
            object_id="obs_wake_route_1",
            subject_id="user_1",
            occurred=TemporalExtent.point(NOW),
            learned_at=NOW,
            recorded_at=NOW,
            created_by="p16-route-test",
            source_kind="sensor",
            modality="numeric_change",
            value={"from": 80, "to": 110},
            metadata={"dimension": "dim:heart_rate"},
        ),
        Observation(
            object_id="obs_wake_route_2",
            subject_id="user_1",
            occurred=TemporalExtent.point(NOW + timedelta(seconds=60)),
            learned_at=NOW + timedelta(seconds=60),
            recorded_at=NOW + timedelta(seconds=60),
            created_by="p16-route-test",
            source_kind="sensor",
            modality="numeric_change",
            value={"from": 110, "to": 118},
            metadata={"dimension": "dim:heart_rate"},
        ),
    ]
    store.commit(
        observations,
        OperationRequest(
            operation_name="test.seed.wake-routing",
            expected_world_revision=0,
            reason="seed deterministic mechanical evidence",
            idempotency_key="seed-wake-routing",
            source_class=SourceClass.SENSOR,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, observations


def test_mechanical_wake_hits_are_idempotent_and_merge_inside_window(tmp_path):
    store, index, observations = _seed(tmp_path)
    router = MechanicalWakeRouter(store=store, index=index)
    policy = MechanicalWakeRoutingPolicy(
        merge_window_seconds=300,
        cooldown_seconds=600,
    )
    first_hit = MechanicalWakeHit(
        hit_id="hr-rise-1",
        wake_source=WakeSource.MECHANICAL_CHANGE,
        rule_id="heart_rate.delta.registered.v1",
        occurred_at=NOW,
        evidence_refs=(ObjectRef(object_id=observations[0].object_id, revision=1),),
        priority=60,
        dedupe_key="heart_rate:continuous-rise",
        metadata={"mechanical_metric": "delta"},
    )
    first = router.route(first_hit, policy=policy)
    replay = router.route(first_hit, policy=policy)

    assert first.state == "new"
    assert first.revision == 1
    assert replay.idempotent_replay is True
    assert replay.wake_id == first.wake_id
    assert store.get_payload(first.wake_id)["hit_count"] == 1

    second = router.route(
        MechanicalWakeHit(
            hit_id="hr-rise-2",
            wake_source=WakeSource.MECHANICAL_CHANGE,
            rule_id="heart_rate.delta.registered.v1",
            occurred_at=NOW + timedelta(seconds=60),
            evidence_refs=(
                ObjectRef(object_id=observations[1].object_id, revision=1),
            ),
            priority=75,
            dedupe_key="heart_rate:continuous-rise",
            metadata={"mechanical_metric": "delta"},
        ),
        policy=policy,
    )
    merged = store.get_payload(first.wake_id)

    assert second.wake_id == first.wake_id
    assert second.merged is True
    assert second.revision == 2
    assert merged["hit_count"] == 2
    assert merged["priority"] == 75
    assert merged["first_hit_at"] == NOW.isoformat()
    assert merged["last_hit_at"] == (NOW + timedelta(seconds=60)).isoformat()
    assert len(merged["evidence_refs"]) == 2


def test_dispatch_does_not_rewrite_trigger_hit_time_and_cooldown_is_audited(tmp_path):
    store, index, observations = _seed(tmp_path)
    router = MechanicalWakeRouter(store=store, index=index)
    policy = MechanicalWakeRoutingPolicy(
        merge_window_seconds=300,
        cooldown_seconds=600,
    )
    first = router.route(
        MechanicalWakeHit(
            hit_id="mechanical-1",
            wake_source=WakeSource.MECHANICAL_CHANGE,
            rule_id="registered-rule",
            occurred_at=NOW,
            evidence_refs=(
                ObjectRef(object_id=observations[0].object_id, revision=1),
            ),
            priority=50,
            dedupe_key="same-context",
        ),
        policy=policy,
    )

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: ModelDirective(silence=True),
    )
    runtime.run_wake(
        wake_ref=ObjectRef(object_id=first.wake_id, revision=1),
        now=NOW + timedelta(seconds=120),
        step0_gate=lambda _wake, _now: WakeStep0Decision(
            outcome=WakeStep0Outcome.QUIET,
            audit={"channel": "background"},
        ),
    )
    completed = store.get_payload(first.wake_id)
    assert completed["wake_state"] == "completed"
    assert completed["last_hit_at"] == NOW.isoformat()
    assert completed["hit_count"] == 1

    suppressed = router.route(
        MechanicalWakeHit(
            hit_id="mechanical-2",
            wake_source=WakeSource.MECHANICAL_CHANGE,
            rule_id="registered-rule",
            occurred_at=NOW + timedelta(seconds=180),
            evidence_refs=(
                ObjectRef(object_id=observations[1].object_id, revision=1),
            ),
            priority=50,
            dedupe_key="same-context",
        ),
        policy=policy,
    )
    payload = store.get_payload(suppressed.wake_id)

    assert suppressed.suppressed is True
    assert suppressed.wake_id != first.wake_id
    assert payload["wake_state"] == "suppressed"
    assert payload["metadata"]["suppression"]["kind"] == "cooldown"
    assert payload["metadata"]["suppression"]["suppressed_by"]["object_id"] == first.wake_id


def test_finite_suppression_requires_scope_and_reactivation_contract(tmp_path):
    store, index, observations = _seed(tmp_path)
    router = MechanicalWakeRouter(store=store, index=index)
    policy = MechanicalWakeRoutingPolicy(
        suppress_until=NOW + timedelta(hours=1),
        suppression_reason="user-requested quiet window",
        suppression_scope="heart-rate informational wake",
        reactivation_condition="quiet window expires",
    )
    receipt = router.route(
        MechanicalWakeHit(
            hit_id="quiet-hit",
            wake_source=WakeSource.WATCH_MATCH,
            rule_id="registered-watch",
            occurred_at=NOW,
            evidence_refs=(
                ObjectRef(object_id=observations[0].object_id, revision=1),
            ),
            dedupe_key="watch:quiet-test",
        ),
        policy=policy,
    )
    payload = store.get_payload(receipt.wake_id)
    assert receipt.suppressed is True
    assert payload["metadata"]["suppression"]["scope"] == "heart-rate informational wake"
    assert payload["metadata"]["suppression"]["reactivation_condition"] == "quiet window expires"
