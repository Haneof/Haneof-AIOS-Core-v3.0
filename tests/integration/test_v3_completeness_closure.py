from datetime import datetime, timedelta, timezone

import pytest

from aios_core.ai_world import AIWorldClaimRequest, AIWorldCognitionService, AIWorldDomain
from aios_core.contracts.enums import (
    EventStatus,
    ObjectType,
    PolicyClass,
)
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
from aios_core.review import PeriodicReviewService
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries import MultiScaleSummaryScheduler, SummaryScale
from aios_core.world_graph import (
    EntityProposalRequest,
    EntityRelationService,
    EntityRevisionRequest,
    RelationUpsertRequest,
)
from aios_core.writeback.cognition import (
    ClaimWriteRequest,
    CognitionWritebackService,
    _stable_id as cognition_stable_id,
)


UTC = timezone.utc
NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def _world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    return store, index


def _user_fact(store, *, subject="user_1", text="真实用户反馈", at=NOW):
    ingest = ConversationIngestor(store, subject_id=subject)
    commit = ingest.commit_turn(
        session_id=f"s-{subject}",
        turn_index=1,
        user_text=text,
        assistant_text="assistant reply",
        occurred_at=at,
    )
    return (
        ObjectRef(object_id=commit.user_observation_id, revision=1),
        ObjectRef(object_id=commit.assistant_observation_id, revision=1),
    )


def test_subject_scoped_search_and_cognition_block_cross_user_refs(tmp_path):
    store, index = _world(tmp_path)
    user1_ref, _ = _user_fact(
        store,
        subject="user_1",
        text="sharedsecret user one",
        at=NOW,
    )
    user2_ref, _ = _user_fact(
        store,
        subject="user_2",
        text="sharedsecret user two",
        at=NOW + timedelta(seconds=1),
    )
    index.rebuild()

    page = index.search_mind(keywords=("sharedsecret",), subject="user_1", limit=20)
    assert page.hits
    assert {hit.subject_id for hit in page.hits} == {"user_1"}

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: ModelDirective(response="ok"),
        subject_id="user_1",
    )
    with pytest.raises(ValueError, match="subject scope"):
        runtime._inspect_world_object(user2_ref.object_id, revision=1)
    assert runtime._inspect_world_object(user1_ref.object_id, revision=1)["subject_id"] == "user_1"

    writer = CognitionWritebackService(
        store=store,
        index=index,
        subject_id="user_1",
    )
    with pytest.raises(ValueError, match="subject scope"):
        writer.commit_claim(
            ClaimWriteRequest(
                content="must not cross users",
                evidence_refs=(user2_ref,),
                confidence=0.5,
                dimension="dim:test",
            ),
            learned_at=NOW + timedelta(minutes=1),
        )

    # AI-self cognition is a distinct subject inside the same private user world and
    # is explicitly allowed to ground itself in this user's evidence.
    ai_world = AIWorldCognitionService(
        store=store,
        index=index,
        user_id="user_1",
    )
    receipt = ai_world.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.SELF,
            statement="I should verify before assuming.",
            evidence_refs=(user1_ref,),
            confidence=0.8,
        ),
        learned_at=NOW + timedelta(minutes=2),
    )
    assert receipt.subject_id == "ai_agent_self"


def test_structured_stable_identity_has_no_delimiter_boundary_alias():
    assert cognition_stable_id("x", "a|b", "c") != cognition_stable_id(
        "x", "a", "b|c"
    )


def test_ai_policy_requires_real_result_evidence_and_becomes_due(tmp_path):
    store, index = _world(tmp_path)
    user_ref, assistant_ref = _user_fact(store)
    index.rebuild()
    policies = CognitivePolicyRegistry(store=store, index=index)

    registered = policies.register(
        CognitivePolicyCreateRequest(
            policy_id="communication.detail_level",
            scope="per-user:user_1",
            policy_class=PolicyClass.COGNITIVE_POLICY,
            default_value="compact",
            current_value="detailed",
            allowed_range_or_choices=["compact", "detailed"],
            mutable_by_ai=True,
            reason="direct user feedback requested detail",
            evidence_refs=(user_ref,),
            changed_by="resident_ai",
            evaluation_window="1d",
        ),
        changed_at=NOW + timedelta(minutes=1),
        actor_is_ai=True,
    )
    assert registered.revision == 1
    assert policies.effective_value("communication.detail_level") == "detailed"
    assert policies.due_for_evaluation(now=NOW + timedelta(hours=23)) == ()
    assert len(policies.due_for_evaluation(now=NOW + timedelta(days=2))) == 1

    with pytest.raises(ValueError, match="assistant-generated"):
        policies.update(
            CognitivePolicyUpdateRequest(
                policy_id="communication.detail_level",
                current_value="compact",
                reason="assistant self-approval must not train policy",
                evidence_refs=(assistant_ref,),
            ),
            changed_at=NOW + timedelta(hours=2),
            actor_is_ai=True,
        )

    claim = CognitionWritebackService(
        store=store,
        index=index,
        subject_id="user_1",
    ).commit_claim(
        ClaimWriteRequest(
            content="I think detailed replies work better",
            evidence_refs=(user_ref,),
            confidence=0.7,
            dimension="dim:ai_strategy",
        ),
        learned_at=NOW + timedelta(hours=3),
    )
    with pytest.raises(ValueError, match="real-result evidence"):
        policies.update(
            CognitivePolicyUpdateRequest(
                policy_id="communication.detail_level",
                current_value="compact",
                reason="a Claim cannot recursively justify policy learning",
                evidence_refs=(ObjectRef(object_id=claim.claim_id, revision=1),),
            ),
            changed_at=NOW + timedelta(hours=4),
            actor_is_ai=True,
        )

    review = PeriodicReviewService(store=store, index=index)
    prepared = review.prepare_due_review(now=NOW + timedelta(days=2))
    assert prepared is not None
    assert any(
        anchor.object_type == ObjectType.COGNITIVE_POLICY.value
        for anchor in prepared.anchors
    )


def test_runtime_consumes_active_policy_values(tmp_path):
    store, index = _world(tmp_path)
    ingest = ConversationIngestor(store)
    for i, text in enumerate(
        ("之前我们讨论智能索引。", "之前我们讨论索引推荐。"),
        start=1,
    ):
        ingest.commit_turn(
            session_id=f"old-{i}",
            turn_index=1,
            user_text=text,
            assistant_text="old answer",
            occurred_at=NOW - timedelta(days=10 - i),
        )
    index.rebuild()

    def model(_snapshot):
        return ModelDirective(response="ok")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    runtime.policies.register(
        CognitivePolicyCreateRequest(
            policy_id="memory.recommendation_limit",
            scope="per-user:user_1",
            policy_class=PolicyClass.COGNITIVE_POLICY,
            default_value=5,
            current_value=1,
            allowed_range_or_choices={"min": 1, "max": 20},
            mutable_by_ai=True,
            reason="bounded system bootstrap for test",
            changed_by="system_bootstrap",
            evaluation_window="7d",
        ),
        changed_at=NOW - timedelta(days=1),
    )
    runtime.policies.register(
        CognitivePolicyCreateRequest(
            policy_id="communication.detail_level",
            scope="per-user:user_1",
            policy_class=PolicyClass.COGNITIVE_POLICY,
            default_value="compact",
            current_value="detailed",
            allowed_range_or_choices=["compact", "detailed"],
            mutable_by_ai=True,
            reason="bounded system bootstrap for test",
            changed_by="system_bootstrap",
            evaluation_window="7d",
        ),
        changed_at=NOW - timedelta(days=1),
    )

    result = runtime.run_turn(
        session_id="new-session",
        turn_index=1,
        user_input="继续之前的智能索引讨论。",
        occurred_at=NOW,
    )
    assert len(result.recommendation.cards) <= 1
    cockpit = result.context.as_cockpit()
    policy_context = cockpit["task_context"]["cognitive_policy_context"]
    assert policy_context["memory.recommendation_limit"] == 1
    assert policy_context["communication.detail_level"] == "detailed"


def test_topic_presence_alone_does_not_authorize_history_injection():
    state = TopicStateService().resolve(user_input="天空为什么是蓝色？")
    assert state.gate_open is True
    assert state.history_may_help is False

    historical = TopicStateService().resolve(user_input="继续我们昨天的索引讨论。")
    assert historical.history_may_help is True


def test_exact_entity_anchor_can_open_history_without_keyword_guessing(tmp_path):
    store, index = _world(tmp_path)
    user_ref, _ = _user_fact(store, text="小王的生日是十月三日。")
    index.rebuild()

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: ModelDirective(response="ok"),
    )
    runtime.world_graph.propose_entity(
        EntityProposalRequest(
            entity_key="entity:person:xiao_wang_topic",
            entity_kind="person",
            canonical_name="小王",
            evidence_refs=(user_ref,),
        ),
        proposed_at=NOW + timedelta(minutes=1),
    )

    signal, reason = runtime._structured_topic_history_signal("小王生日是哪天？")
    assert signal is True
    assert reason == "explicit_entity_anchor"

    state = runtime.topic_state.resolve(
        user_input="小王生日是哪天？",
        structured_history_signal=signal,
        structured_signal_reason=reason,
    )
    assert state.history_may_help is True
    assert "explicit_entity_anchor" in state.reason


def test_summary_scheduler_drains_missed_windows_and_reopens_late_data(tmp_path):
    store, index = _world(tmp_path)
    ingest = ConversationIngestor(store)
    day1 = NOW - timedelta(days=4)
    day3 = NOW - timedelta(days=2)
    ingest.commit_turn(
        session_id="d1",
        turn_index=1,
        user_text="day one fact",
        assistant_text="day one answer",
        occurred_at=day1,
    )
    ingest.commit_turn(
        session_id="d3",
        turn_index=1,
        user_text="day three fact",
        assistant_text="day three answer",
        occurred_at=day3,
    )
    index.rebuild()

    calls = []

    def summarize(prepared):
        calls.append((prepared.window_start, len(prepared.sources)))
        return f"summary with {len(prepared.sources)} sources"

    scheduler = MultiScaleSummaryScheduler(
        store=store,
        index=index,
        summary_handler=summarize,
    )
    first = scheduler.run_due(
        now=NOW,
        scales=(SummaryScale.DAY,),
        dimensions=(INTERACTION_DIMENSION,),
    )
    assert len(first.commits) == 2
    assert len(calls) == 2

    second = scheduler.run_due(
        now=NOW + timedelta(minutes=1),
        scales=(SummaryScale.DAY,),
        dimensions=(INTERACTION_DIMENSION,),
    )
    assert len(second.commits) == 0
    assert len(second.skipped_unchanged) >= 2

    # A late fact recorded into the already summarized day reopens only that source
    # identity and produces a forward Summary revision instead of silently staying stale.
    ingest.commit_turn(
        session_id="late",
        turn_index=1,
        user_text="late fact for old day",
        assistant_text="late answer",
        occurred_at=day1 + timedelta(hours=1),
        recorded_at=NOW + timedelta(minutes=2),
    )
    index.catch_up()
    third = scheduler.run_due(
        now=NOW + timedelta(minutes=3),
        scales=(SummaryScale.DAY,),
        dimensions=(INTERACTION_DIMENSION,),
    )
    assert any(item.revision == 2 for item in third.commits)


def test_summary_source_cap_fails_closed_instead_of_publishing_partial_current(tmp_path):
    store, index = _world(tmp_path)
    ingest = ConversationIngestor(store)
    ingest.commit_turn(
        session_id="dense",
        turn_index=1,
        user_text="one",
        assistant_text="two",
        occurred_at=NOW - timedelta(days=1),
    )
    index.rebuild()

    scheduler = MultiScaleSummaryScheduler(
        store=store,
        index=index,
        summary_handler=lambda _prepared: "must not be called for truncated input",
        max_source_objects=1,
    )
    result = scheduler.run_due(
        now=NOW,
        scales=(SummaryScale.DAY,),
        dimensions=(INTERACTION_DIMENSION,),
    )
    assert result.truncated is True
    assert result.commits == ()


def test_late_overflow_marks_existing_summary_stale(tmp_path):
    store, index = _world(tmp_path)
    ingest = ConversationIngestor(store)
    old_day = NOW - timedelta(days=1)
    ingest.commit_turn(
        session_id="dense-first",
        turn_index=1,
        user_text="first user fact",
        assistant_text="first assistant fact",
        occurred_at=old_day,
    )
    index.rebuild()

    scheduler = MultiScaleSummaryScheduler(
        store=store,
        index=index,
        summary_handler=lambda prepared: f"complete {len(prepared.sources)}",
        max_source_objects=2,
    )
    first = scheduler.run_due(
        now=NOW,
        scales=(SummaryScale.DAY,),
        dimensions=(INTERACTION_DIMENSION,),
    )
    assert len(first.commits) == 1
    first_summary = store.get_payload(first.commits[0].object_id)
    assert first_summary["summary_status"] == "current"

    ingest.commit_turn(
        session_id="dense-late",
        turn_index=1,
        user_text="late user fact",
        assistant_text="late assistant fact",
        occurred_at=old_day + timedelta(hours=1),
        recorded_at=NOW + timedelta(minutes=1),
    )
    index.catch_up()

    second = scheduler.run_due(
        now=NOW + timedelta(minutes=2),
        scales=(SummaryScale.DAY,),
        dimensions=(INTERACTION_DIMENSION,),
    )
    assert second.truncated is True
    latest = store.get_payload(first.commits[0].object_id)
    assert latest["revision"] == 2
    assert latest["summary_status"] == "stale"
    assert latest["metadata"]["stale_due_to_incomplete_source_window"] is True


def test_event_transition_matrix_blocks_terminal_backjump(tmp_path):
    store, index = _world(tmp_path)
    user_ref, _ = _user_fact(store)
    index.rebuild()
    events = EventDimensionService(store=store, index=index)
    event = events.form_event(
        EventWriteRequest(
            title="Candidate",
            interpretation="candidate event",
            event_time=TemporalExtent.point(NOW),
            evidence_refs=(user_ref,),
            confidence=0.8,
        ),
        learned_at=NOW + timedelta(minutes=1),
    )
    rejected = events.transition(
        EventTransitionRequest(
            event_ref=ObjectRef(object_id=event.event_id, revision=1),
            new_status=EventStatus.REJECTED,
            reason="evidence no longer supports event",
            evidence_refs=(user_ref,),
        ),
        changed_at=NOW + timedelta(minutes=2),
    )
    assert rejected.new_status == EventStatus.REJECTED.value

    with pytest.raises(ValueError, match="illegal Event transition"):
        events.transition(
            EventTransitionRequest(
                event_ref=ObjectRef(object_id=event.event_id, revision=2),
                new_status=EventStatus.ACTIVE,
                reason="terminal backjump should fail",
                evidence_refs=(user_ref,),
            ),
            changed_at=NOW + timedelta(minutes=3),
        )


def test_resident_entity_relation_graph_is_durable_and_searchable(tmp_path):
    store, index = _world(tmp_path)
    user_ref, _ = _user_fact(store, text="我今天和小王一起讨论项目。")
    index.rebuild()
    graph = EntityRelationService(store=store, index=index)

    user_entity = graph.propose_entity(
        EntityProposalRequest(
            entity_key="entity:user:self",
            entity_kind="person",
            canonical_name="用户",
            aliases=("我",),
            evidence_refs=(user_ref,),
        ),
        proposed_at=NOW + timedelta(minutes=1),
    )
    xiao_wang = graph.propose_entity(
        EntityProposalRequest(
            entity_key="entity:person:xiao_wang",
            entity_kind="person",
            canonical_name="小王",
            aliases=("王同事",),
            evidence_refs=(user_ref,),
        ),
        proposed_at=NOW + timedelta(minutes=2),
    )
    relation = graph.upsert_relation(
        RelationUpsertRequest(
            left_ref=ObjectRef(object_id=user_entity.entity_id, revision=1),
            relation_type="works_with",
            right_ref=ObjectRef(object_id=xiao_wang.entity_id, revision=1),
            valid_time=TemporalExtent.point(NOW),
            evidence_refs=(user_ref,),
            confidence=0.9,
            reason="direct conversation evidence",
        ),
        changed_at=NOW + timedelta(minutes=3),
    )
    assert store.get_payload(relation.relation_id)["object_type"] == "relation"

    page = index.search_by_entity(
        xiao_wang.entity_id,
        subject="user_1",
        limit=20,
    )
    assert any(hit.object_id == relation.relation_id for hit in page.hits)

    revised = graph.revise_entity(
        EntityRevisionRequest(
            entity_ref=ObjectRef(object_id=xiao_wang.entity_id, revision=1),
            reason="learned an additional alias",
            evidence_refs=(user_ref,),
            aliases=("王同事", "小王老师"),
        ),
        changed_at=NOW + timedelta(minutes=4),
    )
    assert revised.revision == 2
    assert store.get_payload(xiao_wang.entity_id)["aliases"] == ["王同事", "小王老师"]
