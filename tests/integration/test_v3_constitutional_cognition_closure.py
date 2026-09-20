from datetime import datetime, timedelta, timezone

import pytest

from aios_core.communication import (
    CommunicationExperienceRequest,
    CommunicationExperienceService,
)
from aios_core.contracts.enums import PolicyClass, UserReaction
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.events import EventDimensionService, EventTransitionRequest, EventWriteRequest
from aios_core.ingest.conversation import ConversationIngestor, INTERACTION_DIMENSION
from aios_core.policy import (
    CognitivePolicyCreateRequest,
    CognitivePolicyRegistry,
    CognitivePolicyUpdateRequest,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.recommendation.topic_state import TopicStateService
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries import MultiScaleSummaryScheduler, SummaryScale, window_bounds


UTC = timezone.utc
NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def _world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    return store, index


def _conversation_fact(store, *, at=NOW):
    ingest = ConversationIngestor(store)
    commit = ingest.commit_turn(
        session_id="s-constitutional",
        turn_index=1,
        user_text="我们继续把 AIOS 的认知机制收口。",
        assistant_text="我会按世界证据继续推进。",
        occurred_at=at,
    )
    return (
        ObjectRef(object_id=commit.user_observation_id, revision=1),
        ObjectRef(object_id=commit.assistant_observation_id, revision=1),
    )


def test_policy_event_and_communication_experience_share_one_world(tmp_path):
    store, index = _world(tmp_path)
    user_ref, assistant_ref = _conversation_fact(store)
    index.rebuild()

    policies = CognitivePolicyRegistry(store=store, index=index)
    registered = policies.register(
        CognitivePolicyCreateRequest(
            policy_id="communication.detail_level",
            scope="per-user:user_1",
            policy_class=PolicyClass.COGNITIVE_POLICY,
            default_value="compact",
            current_value="compact",
            allowed_range_or_choices=["compact", "detailed"],
            mutable_by_ai=True,
            reason="register a bounded user-specific communication policy",
            evidence_refs=(user_ref,),
            changed_by="system_bootstrap",
            evaluation_window="7d",
        ),
        changed_at=NOW + timedelta(seconds=1),
    )
    assert registered.revision == 1

    updated = policies.update(
        CognitivePolicyUpdateRequest(
            policy_id="communication.detail_level",
            current_value="detailed",
            reason="direct user feedback shows more detail is currently useful",
            evidence_refs=(user_ref,),
            changed_by="resident_ai",
            evaluation_window="7d",
        ),
        changed_at=NOW + timedelta(seconds=2),
        actor_is_ai=True,
    )
    assert updated.revision == 2
    latest = policies.latest("communication.detail_level")
    assert latest is not None
    assert latest.current_value == "detailed"
    assert latest.previous_version == 1
    assert latest.rollback_pointer == 1

    rolled = policies.rollback(
        "communication.detail_level",
        1,
        reason="later evidence shows compact mode is preferable again",
        evidence_refs=(user_ref,),
        changed_by="resident_ai",
        changed_at=NOW + timedelta(seconds=3),
        actor_is_ai=True,
    )
    assert rolled.revision == 3
    latest = policies.latest("communication.detail_level")
    assert latest is not None
    assert latest.current_value == "compact"
    assert latest.previous_version == 2
    assert latest.rollback_pointer == 1
    assert len(policies.history("communication.detail_level")) == 3

    events = EventDimensionService(store=store, index=index)
    event = events.form_event(
        EventWriteRequest(
            title="AIOS 认知机制收口",
            interpretation="用户与 AI 正在集中完成认知体系剩余机制的工程闭环。",
            event_time=TemporalExtent.point(NOW),
            evidence_refs=(user_ref,),
            confidence=0.9,
        ),
        learned_at=NOW + timedelta(seconds=4),
    )
    assert event.revision == 1
    assert event.status == "candidate"

    revised = events.transition(
        EventTransitionRequest(
            event_ref=ObjectRef(object_id=event.event_id, revision=1),
            new_status="revised",
            reason="新增证据使事件描述更精确",
            evidence_refs=(user_ref,),
            replacement_interpretation="用户要求把所有已审出的认知机制缺口一次性完善。",
            confidence=0.96,
        ),
        changed_at=NOW + timedelta(seconds=5),
    )
    assert revised.new_revision == 2
    assert store.get_payload(event.event_id, revision=1)["event_status"] == "candidate"
    assert store.get_payload(event.event_id, revision=2)["event_status"] == "revised"

    communication = CommunicationExperienceService(store=store, index=index)
    with pytest.raises(ValueError, match="real user/world feedback"):
        communication.record(
            CommunicationExperienceRequest(
                scenario="project_execution",
                style="concise_progress",
                user_reaction=UserReaction.ACCEPTED,
                evidence_refs=(assistant_ref,),
            ),
            recorded_at=NOW + timedelta(seconds=6),
        )

    comm = communication.record(
        CommunicationExperienceRequest(
            scenario="project_execution",
            style="direct_execution",
            tone="concise",
            user_reaction=UserReaction.ACCEPTED,
            evidence_refs=(user_ref,),
            applicable_conditions={"project": "AIOS"},
        ),
        recorded_at=NOW + timedelta(seconds=7),
    )
    payload = store.get_payload(comm.experience_id)
    assert payload["object_type"] == "communication_experience"
    assert payload["metadata"]["dimension"] == "dim:ai_communication_experience"


def test_topic_state_uses_canonical_recent_turns_and_can_close_history_gate():
    service = TopicStateService()

    greeting = service.resolve(user_input="你好")
    assert greeting.topic is None
    assert greeting.gate_open is False
    assert greeting.history_may_help is False

    continued = service.resolve(
        user_input="那这个怎么实现？",
        recent_turns=(
            {
                "role": "user",
                "text": "我们现在讨论 AIOS 智能世界索引的下钻机制。",
            },
            {
                "role": "assistant",
                "text": "可以从世界锚点继续下钻。",
            },
        ),
    )
    assert continued.gate_open is True
    assert continued.continued_from_recent_turn is True
    assert "智能世界索引" in (continued.topic or "")
    assert continued.history_may_help is True


def test_multiscale_summary_scheduler_requires_model_text_and_skips_unchanged(tmp_path):
    store, index = _world(tmp_path)
    ingest = ConversationIngestor(store)
    day = NOW - timedelta(days=1)
    ingest.commit_turn(
        session_id="summary-day",
        turn_index=1,
        user_text="昨天完成了 Event 和 Policy 的架构讨论。",
        assistant_text="相关事实已经进入统一世界。",
        occurred_at=day,
    )
    index.rebuild()

    calls = []

    def summarize(prepared):
        calls.append(prepared)
        return "该维度在这个日窗口内完成了 Event 与 Policy 相关设计讨论。"

    scheduler = MultiScaleSummaryScheduler(
        store=store,
        index=index,
        summary_handler=summarize,
    )
    first = scheduler.run_due(
        now=NOW,
        scales=(SummaryScale.DAY,),
        dimensions=(INTERACTION_DIMENSION,),
        max_jobs=4,
    )
    assert len(first.commits) == 1
    assert len(calls) == 1
    summary = store.get_payload(first.commits[0].object_id)
    assert summary["content"].startswith("该维度")
    assert summary["granularity"] == "day"

    second = scheduler.run_due(
        now=NOW + timedelta(minutes=1),
        scales=(SummaryScale.DAY,),
        dimensions=(INTERACTION_DIMENSION,),
        max_jobs=4,
    )
    assert len(second.commits) == 0
    assert len(second.skipped_unchanged) == 1
    assert len(calls) == 1


def test_all_constitutional_summary_scales_have_stable_utc_windows():
    cases = {
        SummaryScale.DAY: (
            datetime(2026, 9, 20, 0, 0, tzinfo=UTC),
            datetime(2026, 9, 20, 23, 59, 59, 999999, tzinfo=UTC),
        ),
        SummaryScale.WEEK: (
            datetime(2026, 9, 14, 0, 0, tzinfo=UTC),
            datetime(2026, 9, 20, 23, 59, 59, 999999, tzinfo=UTC),
        ),
        SummaryScale.MONTH: (
            datetime(2026, 9, 1, 0, 0, tzinfo=UTC),
            datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=UTC),
        ),
        SummaryScale.QUARTER: (
            datetime(2026, 7, 1, 0, 0, tzinfo=UTC),
            datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=UTC),
        ),
        SummaryScale.HALF_YEAR: (
            datetime(2026, 7, 1, 0, 0, tzinfo=UTC),
            datetime(2026, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
        ),
        SummaryScale.YEAR: (
            datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
            datetime(2026, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
        ),
        SummaryScale.MULTI_YEAR_3Y: (
            datetime(2025, 1, 1, 0, 0, tzinfo=UTC),
            datetime(2027, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
        ),
        SummaryScale.MULTI_YEAR_5Y: (
            datetime(2025, 1, 1, 0, 0, tzinfo=UTC),
            datetime(2029, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
        ),
        SummaryScale.DECADE: (
            datetime(2020, 1, 1, 0, 0, tzinfo=UTC),
            datetime(2029, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
        ),
    }
    for scale, expected in cases.items():
        assert window_bounds(NOW, scale) == expected


def test_fused_runtime_exposes_and_executes_new_constitutional_capabilities(tmp_path):
    store, index = _world(tmp_path)

    calls_seen = []

    def model(snapshot):
        if not snapshot.capability_history:
            current_ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="form_event",
                        arguments={
                            "title": "用户要求完善全部认知缺口",
                            "interpretation": "用户明确要求继续施工而不是只做审查。",
                            "event_time": {
                                "start": NOW.isoformat(),
                                "end": NOW.isoformat(),
                                "precision": "second",
                            },
                            "evidence_refs": [current_ref],
                            "confidence": 0.95,
                        },
                    ),
                    CapabilityCall(
                        name="record_communication_experience",
                        arguments={
                            "scenario": "project_execution",
                            "style": "execute_then_report",
                            "tone": "concise",
                            "user_reaction": "accepted",
                            "evidence_refs": [current_ref],
                        },
                    ),
                    CapabilityCall(
                        name="update_cognitive_policy",
                        arguments={
                            "policy_id": "communication.detail_level",
                            "current_value": "detailed",
                            "reason": "current direct feedback requests full implementation detail",
                            "evidence_refs": [current_ref],
                            "evaluation_window": "7d",
                        },
                    ),
                )
            )
        calls_seen.extend(item.name for item in snapshot.capability_history)
        return ModelDirective(response="已按统一世界机制继续执行。")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        max_tool_rounds=3,
    )
    runtime.policies.register(
        CognitivePolicyCreateRequest(
            policy_id="communication.detail_level",
            scope="per-user:user_1",
            policy_class=PolicyClass.COGNITIVE_POLICY,
            default_value="compact",
            current_value="compact",
            allowed_range_or_choices=["compact", "detailed"],
            mutable_by_ai=True,
            reason="bootstrap bounded communication policy",
            changed_by="system_bootstrap",
            evaluation_window="7d",
        ),
        changed_at=NOW - timedelta(minutes=1),
    )

    result = runtime.run_turn(
        session_id="runtime-closure",
        turn_index=1,
        user_input="把审查出来的问题全部完善。",
        occurred_at=NOW,
    )
    assert result.runtime.response == "已按统一世界机制继续执行。"
    assert calls_seen == [
        "form_event",
        "record_communication_experience",
        "update_cognitive_policy",
    ]
    names = {item["name"] for item in runtime.registry.catalog()}
    for required in {
        "focus_entity",
        "search_timeline",
        "follow_relation",
        "compare_claims",
        "retrieve_original_observation",
        "expand_recall",
        "inspect_outcome",
        "form_event",
        "transition_event",
        "record_communication_experience",
        "read_cognitive_policies",
        "update_cognitive_policy",
        "rollback_cognitive_policy",
    }:
        assert required in names

    assert runtime.policies.latest("communication.detail_level").current_value == "detailed"
    assert store.list_payloads(object_type=None)
