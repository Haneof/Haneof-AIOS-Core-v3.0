from datetime import datetime, timedelta, timezone

from aios_core.contracts.enums import SourceClass, WakeSource
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.ingest import RealityRecord, SourceAdapterSpec
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def test_resident_creates_attention_watch_and_new_reality_fact_wakes_it(tmp_path):
    store, index = _world(tmp_path)

    def model(snapshot):
        if snapshot.wake_reason == "user_interaction":
            history = snapshot.capability_history
            if not history:
                current_ref = snapshot.cockpit["task_context"][
                    "current_user_observation_ref"
                ]
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="create_attention_watch",
                            arguments={
                                "title": "关注明显心率变化",
                                "dimensions": ["dim:heart_rate"],
                                "reason_refs": [current_ref],
                                "source_kind": "heart_rate",
                                "modality": "numeric_change",
                                "numeric": {
                                    "operator": "gte",
                                    "threshold": 100,
                                    "path": ["current"],
                                },
                                "priority": 70,
                                "cooldown_seconds": 300,
                            },
                        ),
                    )
                )
            created = history[-1]
            assert created.ok is True
            assert created.data["state"] == "waiting_evidence"
            return ModelDirective(response="我会关注后续明确的心率变化。")

        assert snapshot.wake_reason == "watch_match"
        wake = snapshot.cockpit["task_context"]["wake"]
        assert wake["wake_source"] == "watch_match"
        assert len(wake["evidence_refs"]) == 2
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    result = runtime.run_turn(
        session_id="attention-watch",
        turn_index=1,
        user_input="如果接下来心率明显升高，你再关注一下。",
        current_topic=None,
        occurred_at=NOW,
    )
    assert result.runtime.response == "我会关注后续明确的心率变化。"
    watches = runtime.attention_watches.current()
    assert len(watches) == 1
    assert watches[0].task_type.value == "observation"
    assert watches[0].task_state.value == "waiting_evidence"
    assert watches[0].completion_condition["kind"] == "attention_watch_v1"

    adapter = SourceAdapterSpec(
        adapter_id="sensor.hr.attention",
        source_kind="heart_rate",
        dimension="dim:heart_rate",
        source_class=SourceClass.SENSOR,
        default_modality="numeric_change",
    )
    receipt = runtime.reality_ingest.ingest_record(
        adapter,
        RealityRecord(
            external_record_id="hr-change-1",
            occurred_at=NOW + timedelta(minutes=5),
            received_at=NOW + timedelta(minutes=5),
            value={"previous": 82, "current": 112},
            modality="numeric_change",
        ),
    )
    assert receipt.reused_existing is False

    pending = runtime.wake_bus.pending_wakes()
    assert len(pending) == 1
    assert pending[0].wake_source is WakeSource.WATCH_MATCH
    assert pending[0].metadata["trigger_kind"] == "resident_attention_watch"

    dispatched = runtime.run_wake(
        wake_ref=ObjectRef(
            object_id=pending[0].object_id,
            revision=pending[0].revision,
        ),
        now=NOW + timedelta(minutes=5, seconds=1),
    )
    assert dispatched.runtime is not None
    assert dispatched.runtime.silenced is True
    assert dispatched.wake.state == "completed"


def test_attention_watch_does_not_turn_mechanical_match_into_semantic_meaning(tmp_path):
    store, index = _world(tmp_path)
    evidence = Observation(
        object_id="obs_attention_reason",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="attention-test",
        source_kind="user_note",
        modality="text",
        value="关注工作流里的明确状态变化。",
        metadata={"dimension": "dim:work"},
    )
    store.commit(
        [evidence],
        OperationRequest(
            operation_name="test.seed.attention.reason",
            expected_world_revision=0,
            reason="seed attention watch reason",
            idempotency_key="seed-attention-reason",
            source_class=SourceClass.USER,
        ),
    )
    index.catch_up()

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda snapshot: ModelDirective(silence=True),
    )
    runtime.attention_watches.create(
        __import__(
            "aios_core.wake", fromlist=["AttentionWatchRequest"]
        ).AttentionWatchRequest(
            title="工作状态标记",
            dimensions=("dim:work",),
            reason_refs=(ObjectRef(object_id=evidence.object_id, revision=1),),
            metadata_equals={"state_changed": True},
            priority=40,
        ),
        created_at=NOW,
    )

    adapter = SourceAdapterSpec(
        adapter_id="work.state",
        source_kind="work_system",
        dimension="dim:work",
        source_class=SourceClass.USER,
        default_modality="structured_record",
    )
    runtime.reality_ingest.ingest_record(
        adapter,
        RealityRecord(
            external_record_id="work-change",
            occurred_at=NOW + timedelta(minutes=1),
            received_at=NOW + timedelta(minutes=1),
            value={"status": "blocked"},
            provenance={},
        ).model_copy(
            update={"provenance": {},}
        ),
    )

    # The record above lacks the explicit metadata marker and must not wake the model.
    assert runtime.wake_bus.pending_wakes() == ()


def test_attention_router_batches_burst_into_one_resident_invocation(tmp_path):
    store, index = _world(tmp_path)
    evidence = Observation(
        object_id="obs_router_reason",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="attention-router-test",
        source_kind="user_note",
        modality="text",
        value="同时关注工作和睡眠的机械变化。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    store.commit(
        [evidence],
        OperationRequest(
            operation_name="test.seed.router.reason",
            expected_world_revision=0,
            reason="seed router reason",
            idempotency_key="seed-router-reason",
            source_class=SourceClass.USER,
        ),
    )
    index.catch_up()

    model_calls = 0

    def model(snapshot):
        nonlocal model_calls
        model_calls += 1
        assert snapshot.wake_reason == "attention_bundle"
        wake = snapshot.cockpit["task_context"]["wake"]
        bundle = wake["attention_bundle"]
        assert bundle["member_count"] == 2
        sources = {item["wake_source"] for item in bundle["members"]}
        assert sources == {"watch_match"}
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )

    from aios_core.wake import AttentionWatchRequest

    for title, dimension, source in (
        ("关注工作变化", "dim:work", "work_system"),
        ("关注睡眠变化", "dim:sleep", "sleep_sensor"),
    ):
        runtime.attention_watches.create(
            AttentionWatchRequest(
                title=title,
                dimensions=(dimension,),
                reason_refs=(ObjectRef(object_id=evidence.object_id, revision=1),),
                source_kind=source,
                priority=50,
            ),
            created_at=NOW,
        )

    for adapter_id, source_kind, dimension, external_id in (
        ("work.adapter", "work_system", "dim:work", "work-1"),
        ("sleep.adapter", "sleep_sensor", "dim:sleep", "sleep-1"),
    ):
        runtime.reality_ingest.ingest_record(
            SourceAdapterSpec(
                adapter_id=adapter_id,
                source_kind=source_kind,
                dimension=dimension,
                source_class=SourceClass.USER,
                default_modality="structured_record",
            ),
            RealityRecord(
                external_record_id=external_id,
                occurred_at=NOW + timedelta(minutes=2),
                received_at=NOW + timedelta(minutes=2),
                value={"changed": True},
            ),
        )

    pending = runtime.wake_bus.pending_wakes()
    assert len(pending) == 2
    first = pending[0]

    dispatched = runtime.run_wake(
        wake_ref=ObjectRef(
            object_id=first.object_id,
            revision=first.revision,
        ),
        now=NOW + timedelta(minutes=2, seconds=10),
    )

    assert model_calls == 1
    assert dispatched.runtime is not None
    assert dispatched.runtime.silenced is True
    assert dispatched.wake.state == "completed"
    assert dispatched.context is not None
    assert (
        dispatched.context.task_context["wake"]["wake_source"]
        == "attention_bundle"
    )

    current_wakes = {
        item.object_id: item
        for item in runtime.wake_bus._current_wakes()
    }
    merged = [
        current_wakes[item.object_id].wake_state.value
        for item in pending
    ]
    assert merged == ["merged", "merged"]


def test_safety_wake_is_never_batched_with_attention_burst(tmp_path):
    store, index = _world(tmp_path)
    reason = Observation(
        object_id="obs_safety_router_reason",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="attention-router-test",
        source_kind="system",
        modality="marker",
        value={"marker": True},
        metadata={"dimension": "dim:test"},
    )
    store.commit(
        [reason],
        OperationRequest(
            operation_name="test.seed.router.safety",
            expected_world_revision=0,
            reason="seed router safety evidence",
            idempotency_key="seed-router-safety",
            source_class=SourceClass.USER,
        ),
    )
    index.catch_up()

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda snapshot: ModelDirective(silence=True),
    )
    ref = ObjectRef(object_id=reason.object_id, revision=1)
    safety = runtime.wake_bus.emit(
        __import__(
            "aios_core.wake", fromlist=["WakeSignalRequest"]
        ).WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id="safety.direct",
            observed_at=NOW + timedelta(seconds=1),
            evidence_refs=(ref,),
            dedupe_key="safety-direct",
            priority=100,
        )
    )
    runtime.wake_bus.emit(
        __import__(
            "aios_core.wake", fromlist=["WakeSignalRequest"]
        ).WakeSignalRequest(
            wake_source=WakeSource.WATCH_MATCH,
            rule_id="watch.other",
            observed_at=NOW + timedelta(seconds=1),
            evidence_refs=(ref,),
            dedupe_key="watch-other",
            priority=40,
        )
    )

    bundle = runtime.attention_router.bundle_pending(
        now=NOW + timedelta(seconds=2),
        window_seconds=60,
    )
    assert bundle is None
    assert runtime.wake_bus.current_wake(safety.wake_id).wake_state.value == "new"
