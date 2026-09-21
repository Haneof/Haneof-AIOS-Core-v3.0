from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aios_core.ai_world import AIWorldDomain
from aios_core.contracts.enums import (
    ActionStatus,
    AttentionClass,
    MaintenanceClass,
    ObjectType,
    SourceClass,
    SummaryStatus,
    WakeSource,
)
from aios_core.contracts.models import Action, Dependency, Observation, Outcome, Summary
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent, TimePrecision
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.review import OperationExperienceRequest, PeriodicReviewService
from aios_core.runtime.capabilities import (
    CapabilityCall,
    CapabilityKind,
    CapabilitySpec,
)
from aios_core.runtime.cognitive_runtime import (
    CognitiveRuntime,
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
    RuntimeSnapshot,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries import CognitiveDerivationScheduler, DerivedLineageClass
from aios_core.wake import AttentionSchedulingPolicy, WakeSignalRequest
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService


UTC = timezone.utc
NOW = datetime(2026, 9, 21, 9, 30, tzinfo=UTC)


def _commit(store, objects, *, source_class: SourceClass, tag: str) -> None:
    store.commit(
        list(objects),
        OperationRequest(
            operation_name=f"test.c14.runtime.{tag}",
            expected_world_revision=int(store.current_world_revision()),
            reason=f"seed C14 runtime {tag}",
            idempotency_key=f"test-c14-runtime:{tag}:{store.current_world_revision()}",
            source_class=source_class,
            maintenance_class=(
                MaintenanceClass.SUMMARY_REBUILD
                if source_class is SourceClass.MAINTENANCE
                else None
            ),
        ),
    )


def _world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _observation(
    store: SQLiteWorldStore,
    object_id: str,
    *,
    value: str,
    dimension: str,
    subject_id: str = "user_1",
    source_class: SourceClass = SourceClass.USER,
    at: datetime = NOW,
) -> ObjectRef:
    obs = Observation(
        object_id=object_id,
        subject_id=subject_id,
        occurred=TemporalExtent.point(at),
        learned_at=at,
        recorded_at=at,
        created_by="test:c14-runtime",
        source_kind="conversation" if source_class is SourceClass.USER else "sensor",
        modality="text",
        value=value,
        metadata={"dimension": dimension, "role": "user"} if source_class is SourceClass.USER else {"dimension": dimension},
    )
    _commit(store, [obs], source_class=source_class, tag=f"obs:{object_id}")
    return ObjectRef(object_id=object_id, revision=1)


def _summary(
    store: SQLiteWorldStore,
    object_id: str,
    source_refs: tuple[ObjectRef, ...],
    *,
    dimension: str,
    at: datetime = NOW + timedelta(minutes=10),
    granularity: str = "day",
) -> ObjectRef:
    summary = Summary(
        object_id=object_id,
        subject_id="user_1",
        occurred=TemporalExtent(
            start=NOW,
            end=NOW + timedelta(hours=1),
            precision=TimePrecision.DAY,
        ),
        learned_at=at,
        recorded_at=at,
        source_refs=[
            SourceRef(object_id=ref.object_id, revision=ref.revision)
            for ref in source_refs
        ],
        created_by="test:c14-runtime:summary",
        summary_time=TemporalExtent(
            start=NOW,
            end=NOW + timedelta(hours=1),
            precision=TimePrecision.DAY,
        ),
        granularity=granularity,
        content="opaque temporal description; never parse this for cognition",
        source_world_revision=int(store.current_world_revision()),
        coverage={
            "dimension": dimension,
            "source_count": len(source_refs),
            "truncated": False,
        },
        summary_status=SummaryStatus.CURRENT,
        metadata={
            "dimension": dimension,
            "summary_kind": "single_dimension_temporal",
        },
    )
    deps = [
        Dependency(
            object_id=f"dep_{object_id}_{ref.object_id}_{ref.revision}",
            subject_id="user_1",
            learned_at=at,
            recorded_at=at,
            created_by="test:c14-runtime:summary",
            dependent_ref=ObjectRef(object_id=object_id, revision=1),
            dependency_ref=ref,
            dependency_type="summary_uses_source",
        )
        for ref in source_refs
    ]
    _commit(
        store,
        [summary, *deps],
        source_class=SourceClass.MAINTENANCE,
        tag=f"summary:{object_id}",
    )
    return ObjectRef(object_id=object_id, revision=1)


def _schedule(store, index, summary_ref: ObjectRef):
    scheduler = CognitiveDerivationScheduler(store=store, index=index)
    result = scheduler.ensure(summary_ref)
    assert result.eligible is True
    assert result.wake is not None
    return result


def _manual_wake(store, index, summary_ref: ObjectRef):
    scheduler = CognitiveDerivationScheduler(store=store, index=index)
    lineage = scheduler.derive_lineage(summary_ref)
    payload = store.get_payload(summary_ref.object_id, revision=summary_ref.revision)
    dimension = (payload.get("metadata") or {}).get("dimension")
    return scheduler.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.COGNITIVE_DERIVATION,
            rule_id=CognitiveDerivationScheduler.RULE_ID,
            observed_at=NOW + timedelta(minutes=20),
            evidence_refs=(summary_ref,),
            priority=50,
            dedupe_key=f"c14:test-runtime:{summary_ref.object_id}:{summary_ref.revision}",
            cooldown_seconds=0,
            attention_class=AttentionClass.BACKGROUND,
            metadata={
                "trigger_kind": "dimension_summary_cognitive_derivation",
                "summary_ref": summary_ref.model_dump(mode="json"),
                "summary_dimension": dimension,
                "granularity": payload.get("granularity"),
                "summary_window": payload.get("summary_time"),
                "derived_lineage": lineage.audit_payload(),
                "semantic_conclusions": False,
                "routing_only": True,
            },
        )
    )


def _usage(snapshot):
    return {
        "usage": ModelUsage(
            total_tokens=12,
            input_tokens=8,
            output_tokens=4,
            provider="test-provider",
            model="resident-test-model",
            request_id=f"c14-runtime-round-{snapshot.round_index}",
        ),
        "provenance": ModelCallProvenance(
            provider="test-provider",
            model="resident-test-model",
            request_id=f"c14-runtime-round-{snapshot.round_index}",
        ),
    }


def test_derivation_cockpit_uses_same_resident_runtime_metering_and_suppresses_background_delivery(tmp_path):
    store, index = _world(tmp_path)
    leaf = _observation(
        store,
        "obs_c14_cockpit",
        value="用户明确说今天把训练时间改到晚上。",
        dimension="dim:schedule",
    )
    summary_ref = _summary(
        store,
        "sum_c14_cockpit",
        (leaf,),
        dimension="dim:schedule",
    )
    scheduled = _schedule(store, index, summary_ref)

    seen = {}

    def model(snapshot):
        seen["snapshot"] = snapshot
        assert snapshot.wake_reason == WakeSource.COGNITIVE_DERIVATION.value
        c14 = snapshot.cockpit["task_context"]["cognitive_derivation"]
        assert c14["summary_ref"] == summary_ref.model_dump(mode="json")
        assert c14["summary_revision"] == 1
        assert c14["summary_dimension"] == "dim:schedule"
        assert c14["granularity"] == "day"
        assert c14["summary_window"]["start"] is not None
        assert c14["scheduler_derived_lineage"]["classification"] == "REALITY"
        assert c14["runtime_derived_lineage"]["grounding_leaf_refs"] == [
            leaf.model_dump(mode="json")
        ]
        assert c14["summary_is_semantic_conclusion"] is False
        assert c14["summary_is_sufficient_evidence_by_itself"] is False
        assert c14["silence_is_valid_success"] is True
        for capability in (
            "search_world",
            "inspect_world_object",
            "search_timeline",
            "compare_claims",
            "expand_recall",
            "request_all_dimensions_projection",
            "commit_claim",
            "commit_ai_world_claim",
            "revise_claim",
            "retract_claim",
        ):
            assert capability in c14["capability_names"]
        return ModelDirective(
            response="后台已完成检查，但不应直接投放用户。",
            **_usage(snapshot),
        )

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    assert sum(
        isinstance(value, CognitiveRuntime)
        for value in vars(runtime).values()
    ) == 1
    assert runtime.cognitive_runtime.model_handler is model

    result = runtime.run_wake(
        wake_ref=ObjectRef(
            object_id=scheduled.wake.wake_id,
            revision=scheduled.wake.revision,
        ),
        now=NOW + timedelta(minutes=30),
    )

    assert result.runtime is not None
    assert result.runtime.response is not None
    assert result.delivery_response is None
    assert result.delivery_suppressed is True
    assert result.wake.state == "completed"
    calls = runtime.metering.list_model_calls(
        subject_id="user_1",
        wake_id=scheduled.wake.wake_id,
    )
    assert len(calls) == 1
    assert calls[0].execution_class == "background"
    assert calls[0].wake_reason == WakeSource.COGNITIVE_DERIVATION.value
    assert calls[0].total_tokens == 12
    assert not any(
        item.get("object_type") == "metering_record"
        for item in store.list_payloads()
    )


def test_grounded_claim_can_drill_down_and_search_cross_dimension_before_commit(tmp_path):
    store, index = _world(tmp_path)
    leaf_a = _observation(
        store,
        "obs_c14_a",
        value="用户说周三晚上去跑步。",
        dimension="dim:activity",
    )
    leaf_b = _observation(
        store,
        "obs_c14_b",
        value="日历记录周三晚上已有固定课程。",
        dimension="dim:calendar",
        source_class=SourceClass.PLATFORM,
        at=NOW + timedelta(minutes=1),
    )
    summary_ref = _summary(
        store,
        "sum_c14_a",
        (leaf_a,),
        dimension="dim:activity",
    )
    scheduled = _schedule(store, index, summary_ref)
    index.catch_up()

    def model(snapshot):
        history = snapshot.capability_history
        if len(history) == 0:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="inspect_world_object",
                        arguments={
                            "object_id": summary_ref.object_id,
                            "revision": summary_ref.revision,
                        },
                    ),
                )
            )
        if len(history) == 1:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="inspect_world_object",
                        arguments={
                            "object_id": leaf_a.object_id,
                            "revision": leaf_a.revision,
                        },
                    ),
                )
            )
        if len(history) == 2:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="search_world",
                        arguments={"query": "固定课程", "limit": 10},
                    ),
                )
            )
        if len(history) == 3:
            assert history[-1].ok is True
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_claim",
                        arguments={
                            "content": "周三晚间安排存在需要后续协调的并行事实。",
                            "evidence_refs": [
                                leaf_a.model_dump(mode="json"),
                                leaf_b.model_dump(mode="json"),
                            ],
                            "confidence": 0.82,
                            "dimension": "dim:planning_cognition",
                        },
                    ),
                )
            )
        assert [item.name for item in history] == [
            "inspect_world_object",
            "inspect_world_object",
            "search_world",
            "commit_claim",
        ]
        assert history[-1].ok is True
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        max_tool_rounds=4,
    )
    result = runtime.run_wake(
        wake_ref=ObjectRef(
            object_id=scheduled.wake.wake_id,
            revision=scheduled.wake.revision,
        ),
        now=NOW + timedelta(minutes=30),
    )
    assert result.runtime is not None and result.runtime.silenced is True
    claims = store.list_payloads(object_type=ObjectType.CLAIM)
    assert any(
        item.get("content") == "周三晚间安排存在需要后续协调的并行事实。"
        for item in claims
    )


@pytest.mark.parametrize("mode", ["revise", "retract"])
def test_derivation_revision_and_retraction_require_and_accept_new_grounding(tmp_path, mode):
    store, index = _world(tmp_path)
    old_leaf = _observation(
        store,
        "obs_c14_old",
        value="用户曾说每天喝茶。",
        dimension="dim:preference",
    )
    old_claim = CognitionWritebackService(store=store, index=index).commit_claim(
        ClaimWriteRequest(
            content="用户当前每天喝茶。",
            evidence_refs=(old_leaf,),
            confidence=0.8,
            dimension="dim:user_understanding",
        ),
        learned_at=NOW + timedelta(minutes=2),
    )
    new_leaf = _observation(
        store,
        "obs_c14_new",
        value="用户现在明确说已经不喝茶了。",
        dimension="dim:preference",
        at=NOW + timedelta(minutes=5),
    )
    summary_ref = _summary(
        store,
        f"sum_c14_{mode}",
        (new_leaf,),
        dimension="dim:preference",
        at=NOW + timedelta(minutes=10),
    )
    scheduled = _schedule(store, index, summary_ref)

    def model(snapshot):
        if not snapshot.capability_history:
            arguments = {
                "target_ref": {
                    "object_id": old_claim.claim_id,
                    "revision": 1,
                },
                "reason": "新的明确用户事实改变了旧认知。",
                "evidence_refs": [new_leaf.model_dump(mode="json")],
            }
            if mode == "revise":
                arguments["replacement_content"] = "用户当前明确表示已经不喝茶。"
                call_name = "revise_claim"
            else:
                call_name = "retract_claim"
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(name=call_name, arguments=arguments),
                )
            )
        assert snapshot.capability_history[-1].ok is True
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_wake(
        wake_ref=ObjectRef(
            object_id=scheduled.wake.wake_id,
            revision=scheduled.wake.revision,
        ),
        now=NOW + timedelta(minutes=30),
    )
    assert result.runtime is not None and result.runtime.silenced is True
    latest = store.get_payload(old_claim.claim_id)
    assert latest["revision"] == 2
    if mode == "revise":
        assert latest["content"] == "用户当前明确表示已经不喝茶。"
        assert latest["status"] == "active"
    else:
        assert latest["status"] == "retracted"


def test_old_ai_claim_via_summary_cannot_self_ground_new_claim(tmp_path):
    store, index = _world(tmp_path)
    leaf = _observation(
        store,
        "obs_c14_old_fact",
        value="用户曾经明确说过更喜欢安静的工作环境。",
        dimension="dim:conversation",
    )
    old_claim = CognitionWritebackService(store=store, index=index).commit_claim(
        ClaimWriteRequest(
            content="用户曾表达过对安静工作环境的偏好。",
            evidence_refs=(leaf,),
            confidence=0.8,
            dimension="dim:user_understanding",
        ),
        learned_at=NOW + timedelta(minutes=2),
    )
    summary_ref = _summary(
        store,
        "sum_c14_ai_recursion",
        (ObjectRef(object_id=old_claim.claim_id, revision=1),),
        dimension="dim:ai_user_understanding",
    )
    scheduled = _schedule(store, index, summary_ref)
    assert scheduled.lineage.classification is DerivedLineageClass.MIXED
    assert scheduled.lineage.grounding_leaf_refs == ()

    before_claims = len(store.list_payloads(object_type=ObjectType.CLAIM))

    def model(snapshot):
        if not snapshot.capability_history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_claim",
                        arguments={
                            "content": "把旧 AI Claim 再总结一遍不能生成新的自证认知。",
                            "evidence_refs": [summary_ref.model_dump(mode="json")],
                            "confidence": 0.9,
                            "dimension": "dim:user_understanding",
                        },
                    ),
                )
            )
        failed = snapshot.capability_history[-1]
        assert failed.ok is False
        assert failed.error_code == "CAPABILITY_EXECUTION_ERROR"
        assert "leaf-grounded evidence closure rejected" in failed.error_message
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_wake(
        wake_ref=ObjectRef(
            object_id=scheduled.wake.wake_id,
            revision=scheduled.wake.revision,
        ),
        now=NOW + timedelta(minutes=30),
    )
    assert result.runtime is not None and result.runtime.silenced is True
    assert len(store.list_payloads(object_type=ObjectType.CLAIM)) == before_claims


def test_t28_assistant_only_summary_is_rejected_but_user_leaf_can_ground_cognition(tmp_path):
    store, index = _world(tmp_path)
    turn = ConversationIngestor(store).commit_turn(
        session_id="c14-t28",
        turn_index=1,
        user_text="我明确说我喜欢 X。",
        assistant_text="我来重复：你喜欢 X。",
        occurred_at=NOW,
    )
    user_ref = ObjectRef(object_id=turn.user_observation_id, revision=1)
    assistant_ref = ObjectRef(object_id=turn.assistant_observation_id, revision=1)

    assistant_summary = _summary(
        store,
        "sum_c14_assistant_only",
        (assistant_ref,),
        dimension="dim:user_ai_interaction",
    )
    scheduler = CognitiveDerivationScheduler(store=store, index=index)
    assistant_route = scheduler.ensure(assistant_summary)
    assert assistant_route.eligible is False
    assert assistant_route.lineage.classification is DerivedLineageClass.AI_COGNITION_ONLY
    manual = _manual_wake(store, index, assistant_summary)

    def assistant_model(snapshot):
        if not snapshot.capability_history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_ai_world_claim",
                        arguments={
                            "domain": AIWorldDomain.USER_UNDERSTANDING.value,
                            "statement": "用户喜欢 X。",
                            "evidence_refs": [assistant_summary.model_dump(mode="json")],
                            "confidence": 0.95,
                        },
                    ),
                )
            )
        assert snapshot.capability_history[-1].ok is False
        assert "leaf-grounded evidence closure rejected" in (
            snapshot.capability_history[-1].error_message
        )
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=assistant_model)
    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=manual.wake_id, revision=manual.revision),
        now=NOW + timedelta(minutes=30),
    )
    assert result.runtime is not None and result.runtime.silenced is True
    assert runtime.ai_world.current(domains=[AIWorldDomain.USER_UNDERSTANDING]) == ()

    user_summary = _summary(
        store,
        "sum_c14_user_only",
        (user_ref,),
        dimension="dim:user_ai_interaction",
        at=NOW + timedelta(minutes=40),
    )
    user_route = _schedule(store, index, user_summary)

    def user_model(snapshot):
        history = snapshot.capability_history
        if len(history) == 0:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="inspect_world_object",
                        arguments={
                            "object_id": user_summary.object_id,
                            "revision": user_summary.revision,
                        },
                    ),
                )
            )
        if len(history) == 1:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="inspect_world_object",
                        arguments={
                            "object_id": user_ref.object_id,
                            "revision": user_ref.revision,
                        },
                    ),
                )
            )
        if len(history) == 2:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_ai_world_claim",
                        arguments={
                            "domain": AIWorldDomain.USER_UNDERSTANDING.value,
                            "statement": "用户明确表达过喜欢 X。",
                            "evidence_refs": [user_ref.model_dump(mode="json")],
                            "confidence": 0.95,
                        },
                    ),
                )
            )
        assert history[-1].ok is True
        return ModelDirective(silence=True)

    runtime2 = FusedTurnRuntime(store=store, index=index, model_handler=user_model)
    result2 = runtime2.run_wake(
        wake_ref=ObjectRef(
            object_id=user_route.wake.wake_id,
            revision=user_route.wake.revision,
        ),
        now=NOW + timedelta(minutes=50),
    )
    assert result2.runtime is not None and result2.runtime.silenced is True
    current = runtime2.ai_world.current(domains=[AIWorldDomain.USER_UNDERSTANDING])
    assert len(current) == 1
    assert current[0].statement == "用户明确表达过喜欢 X。"


@pytest.mark.parametrize("case", ["missing", "cross_subject"])
def test_derivation_grounding_missing_unknown_and_cross_subject_fail_closed(tmp_path, case):
    store, index = _world(tmp_path)
    leaf = _observation(
        store,
        "obs_c14_valid_anchor",
        value="有效的本用户事实。",
        dimension="dim:test",
    )
    summary_ref = _summary(
        store,
        f"sum_c14_fail_closed_{case}",
        (leaf,),
        dimension="dim:test",
    )
    scheduled = _schedule(store, index, summary_ref)

    if case == "missing":
        bad_ref = ObjectRef(object_id="missing_c14_evidence", revision=1)
    else:
        bad_ref = _observation(
            store,
            "obs_c14_foreign",
            value="另一个用户的事实。",
            dimension="dim:test",
            subject_id="user_2",
            at=NOW + timedelta(minutes=2),
        )

    def model(snapshot):
        if not snapshot.capability_history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_claim",
                        arguments={
                            "content": "这条认知不得越过闭包边界。",
                            "evidence_refs": [bad_ref.model_dump(mode="json")],
                            "confidence": 0.8,
                            "dimension": "dim:test_cognition",
                        },
                    ),
                )
            )
        failed = snapshot.capability_history[-1]
        assert failed.ok is False
        assert "leaf-grounded evidence closure rejected" in failed.error_message
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    before_claims = len(store.list_payloads(object_type=ObjectType.CLAIM))
    result = runtime.run_wake(
        wake_ref=ObjectRef(
            object_id=scheduled.wake.wake_id,
            revision=scheduled.wake.revision,
        ),
        now=NOW + timedelta(minutes=30),
    )
    assert result.runtime is not None and result.runtime.silenced is True
    assert len(store.list_payloads(object_type=ObjectType.CLAIM)) == before_claims


def test_strategy_cognition_can_close_through_real_operation_outcome_case(tmp_path):
    store, index = _world(tmp_path)
    observation = Observation(
        object_id="obs_c14_outcome_request",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test:c14-runtime",
        source_kind="conversation",
        modality="text",
        value="把确认后的周报发给团队。",
        metadata={"dimension": "dim:user_ai_interaction", "role": "user"},
    )
    action = Action(
        object_id="action_c14_real",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW + timedelta(minutes=1)),
        learned_at=NOW + timedelta(minutes=1),
        recorded_at=NOW + timedelta(minutes=1),
        created_by="test:c14-runtime",
        execution_id="exec-c14-real",
        action_type="send_team_message",
        action_status=ActionStatus.COMPLETED,
        payload={"channel": "team"},
        expected_outcome="团队收到消息",
    )
    outcome = Outcome(
        object_id="outcome_c14_real",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW + timedelta(minutes=2)),
        learned_at=NOW + timedelta(minutes=2),
        recorded_at=NOW + timedelta(minutes=2),
        created_by="test:c14-runtime",
        action_ref=ObjectRef(object_id=action.object_id, revision=1),
        outcome_state="completed",
        payload={"delivery": "accepted"},
        evidence_refs=[ObjectRef(object_id=observation.object_id, revision=1)],
    )
    _commit(
        store,
        [observation, action, outcome],
        source_class=SourceClass.PLATFORM,
        tag="real-outcome",
    )
    index.catch_up()

    experience = PeriodicReviewService(store=store, index=index).commit_operation_experience(
        OperationExperienceRequest(
            problem_type="external_delivery",
            method_path=("propose", "authorize", "wait_for_outcome"),
            result_summary="真实平台 Outcome 确认投放完成。",
            positive_case_refs=(ObjectRef(object_id=outcome.object_id, revision=1),),
        ),
        learned_at=NOW + timedelta(minutes=3),
    )
    exp_ref = ObjectRef(object_id=experience.experience_id, revision=experience.revision)
    summary_ref = _summary(
        store,
        "sum_c14_strategy_case",
        (exp_ref,),
        dimension="dim:ai_strategy",
        at=NOW + timedelta(minutes=10),
    )
    scheduled = _schedule(store, index, summary_ref)
    assert scheduled.lineage.classification is DerivedLineageClass.MIXED
    assert ObjectRef(object_id=outcome.object_id, revision=1) in (
        scheduled.lineage.grounding_leaf_refs
    )

    def model(snapshot):
        if not snapshot.capability_history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_ai_world_claim",
                        arguments={
                            "domain": AIWorldDomain.STRATEGY.value,
                            "statement": "外部动作应以真实 Outcome 作为已完成判断依据。",
                            "evidence_refs": [summary_ref.model_dump(mode="json")],
                            "confidence": 0.9,
                            "scope_key": "external_action.outcome_grounding",
                        },
                    ),
                )
            )
        assert snapshot.capability_history[-1].ok is True
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_wake(
        wake_ref=ObjectRef(
            object_id=scheduled.wake.wake_id,
            revision=scheduled.wake.revision,
        ),
        now=NOW + timedelta(minutes=30),
    )
    assert result.runtime is not None and result.runtime.silenced is True
    strategy = runtime.ai_world.current(domains=[AIWorldDomain.STRATEGY])
    assert any(
        item.statement == "外部动作应以真实 Outcome 作为已完成判断依据。"
        for item in strategy
    )


def test_silence_completes_wake_without_semantic_write(tmp_path):
    store, index = _world(tmp_path)
    leaf = _observation(
        store,
        "obs_c14_silence",
        value="今天的记录没有形成新的长期认知。",
        dimension="dim:daily",
    )
    summary_ref = _summary(
        store,
        "sum_c14_silence",
        (leaf,),
        dimension="dim:daily",
    )
    scheduled = _schedule(store, index, summary_ref)
    before = {
        object_type: len(store.list_payloads(object_type=object_type))
        for object_type in (
            ObjectType.CLAIM,
            ObjectType.OPERATION_EXPERIENCE,
            ObjectType.OUTCOME,
        )
    }

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: ModelDirective(silence=True),
    )
    result = runtime.run_wake(
        wake_ref=ObjectRef(
            object_id=scheduled.wake.wake_id,
            revision=scheduled.wake.revision,
        ),
        now=NOW + timedelta(minutes=30),
    )
    assert result.runtime is not None
    assert result.runtime.silenced is True
    assert result.runtime.capability_history == ()
    assert result.delivery_response is None
    assert result.wake.state == "completed"
    after = {
        object_type: len(store.list_payloads(object_type=object_type))
        for object_type in before
    }
    assert after == before


C14_ALLOWED_SIDE_EFFECTS = frozenset(
    {
        "commit_claim",
        "commit_ai_world_claim",
        "revise_claim",
        "retract_claim",
    }
)

C14_DENIED_SIDE_EFFECTS = (
    "propose_entity",
    "revise_entity",
    "upsert_relation",
    "propose_dimension",
    "transition_dimension",
    "propose_goal",
    "transition_goal",
    "create_task",
    "transition_task",
    "create_attention_watch",
    "propose_action",
    "form_event",
    "transition_event",
    "commit_operation_experience",
    "record_communication_experience",
    "propose_cognitive_policy",
    "update_cognitive_policy",
    "rollback_cognitive_policy",
)


def _authorization_snapshot(runtime: FusedTurnRuntime, wake_source: WakeSource) -> RuntimeSnapshot:
    return RuntimeSnapshot(
        user_input="authorization probe",
        wake_reason=wake_source.value,
        cockpit={},
        capability_catalog=tuple(runtime.registry.catalog()),
        capability_history=(),
        round_index=0,
        remaining_tool_rounds=1,
    )


def test_derivation_side_effect_authorization_is_explicit_default_deny(tmp_path):
    store, index = _world(tmp_path)
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: ModelDirective(silence=True),
    )
    snapshot = _authorization_snapshot(runtime, WakeSource.COGNITIVE_DERIVATION)

    registered_side_effects = {
        item["name"]
        for item in runtime.registry.catalog()
        if item["side_effecting"]
    }
    assert C14_ALLOWED_SIDE_EFFECTS <= registered_side_effects

    for name in registered_side_effects:
        spec = runtime.registry.get_spec(name)
        allowed = runtime._authorize_side_effect(
            spec,
            CapabilityCall(name=name),
            snapshot,
        )
        assert allowed is (name in C14_ALLOWED_SIDE_EFFECTS)

    future_side_effect = CapabilitySpec(
        name="future_side_effect_escape_probe",
        description="Future side-effect capability used to prove C14 default deny.",
        kind=CapabilityKind.WRITE,
    )
    assert future_side_effect.side_effecting is True
    assert runtime._authorize_side_effect(
        future_side_effect,
        CapabilityCall(name=future_side_effect.name),
        snapshot,
    ) is False

    for item in runtime.registry.catalog():
        if item["side_effecting"]:
            continue
        spec = runtime.registry.get_spec(item["name"])
        assert runtime._authorize_side_effect(
            spec,
            CapabilityCall(name=spec.name),
            snapshot,
        ) is True


@pytest.mark.parametrize("capability_name", C14_DENIED_SIDE_EFFECTS)
def test_derivation_denies_non_cognition_side_effects_before_world_write(
    tmp_path,
    capability_name,
):
    store, index = _world(tmp_path)
    leaf = _observation(
        store,
        f"obs_c14_deny_{capability_name}",
        value="用于验证 C14 side-effect 授权边界的真实用户事实。",
        dimension="dim:c14_authorization",
    )
    summary_ref = _summary(
        store,
        f"sum_c14_deny_{capability_name}",
        (leaf,),
        dimension="dim:c14_authorization",
    )
    scheduled = _schedule(store, index, summary_ref)
    observed = {}

    def model(snapshot):
        history = snapshot.capability_history
        if not history:
            observed["world_revision_before_denied_call"] = int(
                store.current_world_revision()
            )
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(name=capability_name, arguments={}),
                )
            )
        denied = history[-1]
        assert denied.name == capability_name
        assert denied.ok is False
        assert denied.error_code == "CAPABILITY_NOT_AUTHORIZED"
        assert int(store.current_world_revision()) == observed[
            "world_revision_before_denied_call"
        ]
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_wake(
        wake_ref=ObjectRef(
            object_id=scheduled.wake.wake_id,
            revision=scheduled.wake.revision,
        ),
        now=NOW + timedelta(minutes=30),
    )
    assert result.runtime is not None and result.runtime.silenced is True
    assert result.runtime.capability_history[-1].error_code == "CAPABILITY_NOT_AUTHORIZED"


@pytest.mark.parametrize(
    "capability_name",
    (
        "propose_entity",
        "revise_entity",
        "upsert_relation",
        "propose_dimension",
        "transition_dimension",
        "propose_goal",
        "transition_goal",
        "create_task",
        "transition_task",
        "create_attention_watch",
        "propose_action",
        "form_event",
        "transition_event",
    ),
)
def test_user_interaction_keeps_existing_side_effect_authorization(
    tmp_path,
    capability_name,
):
    store, index = _world(tmp_path)
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: ModelDirective(silence=True),
    )
    snapshot = _authorization_snapshot(runtime, WakeSource.USER_INTERACTION)
    spec = runtime.registry.get_spec(capability_name)
    assert runtime._authorize_side_effect(
        spec,
        CapabilityCall(name=capability_name),
        snapshot,
    ) is True


@pytest.mark.parametrize(
    "capability_name",
    (
        "commit_operation_experience",
        "commit_claim",
        "commit_ai_world_claim",
        "revise_claim",
        "retract_claim",
        "propose_cognitive_policy",
        "update_cognitive_policy",
        "rollback_cognitive_policy",
    ),
)
def test_periodic_review_keeps_existing_side_effect_authorization(
    tmp_path,
    capability_name,
):
    store, index = _world(tmp_path)
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: ModelDirective(silence=True),
    )
    snapshot = _authorization_snapshot(runtime, WakeSource.PERIODIC_REVIEW)
    spec = runtime.registry.get_spec(capability_name)
    assert runtime._authorize_side_effect(
        spec,
        CapabilityCall(name=capability_name),
        snapshot,
    ) is True


def test_loop_repro_twelve_sibling_derivations_coalesce_without_losing_contract(
    tmp_path,
):
    store, index = _world(tmp_path)
    scheduled = []
    summary_refs = []
    for offset in range(12):
        leaf = _observation(
            store,
            f"obs_c14_loop_burst_{offset}",
            value=f"mechanical sibling fact {offset}",
            dimension=f"dim:loop:{offset}",
            at=NOW + timedelta(seconds=offset),
        )
        summary_ref = _summary(
            store,
            f"sum_c14_loop_burst_{offset}",
            (leaf,),
            dimension=f"dim:loop:{offset}",
            at=NOW + timedelta(minutes=10, seconds=offset),
        )
        summary_refs.append(summary_ref)
        scheduled.append(_schedule(store, index, summary_ref))

    seen = {"model_calls": 0}

    def model(snapshot):
        seen["model_calls"] += 1
        assert snapshot.wake_reason == WakeSource.COGNITIVE_DERIVATION.value
        bundle = snapshot.cockpit["task_context"]["cognitive_derivation_bundle"]
        assert bundle["member_count"] == 12
        assert {
            (item["summary_ref"]["object_id"], item["summary_ref"]["revision"])
            for item in bundle["members"]
        } == {(ref.object_id, ref.revision) for ref in summary_refs}
        assert {
            (item["wake_ref"]["object_id"], item["wake_ref"]["revision"])
            for item in bundle["members"]
        } == {
            (item.wake.wake_id, item.wake.revision)
            for item in scheduled
        }
        return ModelDirective(silence=True, **_usage(snapshot))

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        attention_scheduling_policy=AttentionSchedulingPolicy(
            background_batch_window_seconds=60,
            background_bundle_max_wakes=16,
        ),
    )
    result = runtime.run_wake(
        wake_ref=ObjectRef(
            object_id=scheduled[0].wake.wake_id,
            revision=scheduled[0].wake.revision,
        ),
        now=NOW + timedelta(minutes=30),
    )

    assert seen["model_calls"] == 1
    bundle_payload = store.get_payload(result.wake_ref.object_id)
    assert bundle_payload["wake_source"] == WakeSource.ATTENTION_BUNDLE.value
    assert bundle_payload["metadata"]["attention_bundle"]["member_count"] == 12
    assert result.wake.state == "completed"
    assert result.delivery_response is None
    for item in scheduled:
        assert runtime.wake_bus.current_wake(item.wake.wake_id).wake_state.value == "merged"

    calls = runtime.metering.list_model_calls(
        subject_id="user_1",
        wake_id=result.wake_ref.object_id,
    )
    assert len(calls) == 1
    assert calls[0].wake_reason == WakeSource.COGNITIVE_DERIVATION.value


def test_loop_repro_direct_c14_attention_bundle_preserves_effective_execution_reason(
    tmp_path,
):
    store, index = _world(tmp_path)
    scheduled = []
    for offset in range(2):
        leaf = _observation(
            store,
            f"obs_c14_loop_contract_{offset}",
            value=f"contract sibling {offset}",
            dimension=f"dim:contract:{offset}",
            at=NOW + timedelta(seconds=offset),
        )
        summary_ref = _summary(
            store,
            f"sum_c14_loop_contract_{offset}",
            (leaf,),
            dimension=f"dim:contract:{offset}",
            at=NOW + timedelta(minutes=10, seconds=offset),
        )
        scheduled.append(_schedule(store, index, summary_ref))

    observed = {}

    def model(snapshot):
        observed["wake_reason"] = snapshot.wake_reason
        assert snapshot.wake_reason == WakeSource.COGNITIVE_DERIVATION.value
        assert snapshot.cockpit["task_context"]["cognitive_derivation_bundle"]["member_count"] == 2
        return ModelDirective(silence=True, **_usage(snapshot))

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    bundled = runtime.attention_router.bundle_pending(
        now=NOW + timedelta(minutes=30),
        window_seconds=60,
        max_wakes=16,
        anchor_wake_id=scheduled[0].wake.wake_id,
    )
    assert bundled is not None and bundled.member_count == 2

    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=bundled.wake_id, revision=bundled.revision),
        now=NOW + timedelta(minutes=30),
    )
    assert observed["wake_reason"] == WakeSource.COGNITIVE_DERIVATION.value
    assert result.wake.state == "completed"


def test_loop_repro_tool_round_budget_exhaustion_keeps_c14_wake_resumable(
    tmp_path,
):
    store, index = _world(tmp_path)
    leaf = _observation(
        store,
        "obs_c14_loop_tool_budget",
        value="budget recovery fact",
        dimension="dim:budget",
    )
    summary_ref = _summary(
        store,
        "sum_c14_loop_tool_budget",
        (leaf,),
        dimension="dim:budget",
    )
    scheduled = _schedule(store, index, summary_ref)

    def model(snapshot):
        return ModelDirective(
            capability_calls=(
                CapabilityCall(
                    name="search_world",
                    arguments={"query": "budget recovery fact", "limit": 1},
                ),
            ),
            **_usage(snapshot),
        )

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        max_tool_rounds=0,
    )
    result = runtime.run_wake(
        wake_ref=ObjectRef(
            object_id=scheduled.wake.wake_id,
            revision=scheduled.wake.revision,
        ),
        now=NOW + timedelta(minutes=30),
    )

    assert result.runtime is not None
    assert result.runtime.termination_reason == "tool_round_budget_exhausted"
    assert result.wake.state == "queued"
    assert runtime.wake_bus.current_wake(
        scheduled.wake.wake_id
    ).wake_state.value == "queued"
