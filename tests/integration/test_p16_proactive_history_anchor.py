from datetime import datetime, timedelta, timezone

from aios_core.ai_world import AIWorldClaimRequest, AIWorldCognitionService, AIWorldDomain
from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 4, 25, 20, 0, tzinfo=timezone.utc)


def _commit_observation(
    store: SQLiteWorldStore,
    *,
    object_id: str,
    value: object,
    occurred_at: datetime,
    source_kind: str,
    dimension: str,
) -> Observation:
    observation = Observation(
        object_id=object_id,
        subject_id="user_1",
        occurred=TemporalExtent.point(occurred_at),
        learned_at=occurred_at,
        recorded_at=occurred_at,
        created_by="p16-history-gate-regression",
        source_kind=source_kind,
        modality="text",
        value=value,
        metadata={"dimension": dimension},
    )
    store.commit(
        [observation],
        OperationRequest(
            operation_name=f"test.seed.{object_id}",
            expected_world_revision=store.current_world_revision(),
            reason="seed proactive history gate regression",
            idempotency_key=f"seed-{object_id}",
            source_class=SourceClass.USER,
        ),
    )
    return observation


def test_auto_topic_gate_opens_from_current_claim_overlap_without_history_cue(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    evidence = _commit_observation(
        store,
        object_id="obs_schedule_change",
        value="计划变了，接下来两个月每周六上午固定开项目会，之前周六上午学习的安排不再适用了。",
        occurred_at=NOW - timedelta(days=13),
        source_kind="conversation",
        dimension="dim:user_ai_interaction",
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    cognition = AIWorldCognitionService(store=store, index=index, user_id="user_1")
    receipt = cognition.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.USER_UNDERSTANDING,
            statement=(
                "用户通常周末不工作；但接下来两个月每周六上午固定开项目会，"
                "因此此前周六上午通常留给学习的安排在这段期间不再适用。"
            ),
            evidence_refs=(ObjectRef(object_id=evidence.object_id, revision=1),),
            confidence=0.97,
            scope_key="weekly_routine",
        ),
        learned_at=NOW - timedelta(days=12),
    )
    index.catch_up()

    def model(snapshot):
        topic_state = snapshot.cockpit["task_context"]["topic_state"]
        assert topic_state["history_may_help"] is True
        assert "indexed_current_world_anchor" in topic_state["reason"]
        cards = snapshot.cockpit["memory_cards"]
        assert any(
            card["object_id"] == receipt.claim.claim_id
            and card["revision"] == 1
            for card in cards
        )
        return ModelDirective(response="周六上午已有固定项目会，学习应另找连续时段。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="s3",
        turn_index=1,
        user_input="如果这周想安排一次两小时的学习，什么时候更合适？",
        occurred_at=NOW,
    )

    assert result.recommendation.cards
    assert result.context.task_context["topic_state"]["history_may_help"] is True


def test_auto_topic_gate_does_not_reopen_from_old_conversation_overlap_alone(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    seed = ConversationIngestor(store)
    seed.commit_turn(
        session_id="old-chat",
        turn_index=1,
        user_text="我最近在研究学习方法和学习效率。",
        assistant_text="可以从复盘和间隔练习开始。",
        occurred_at=NOW - timedelta(days=20),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        topic_state = snapshot.cockpit["task_context"]["topic_state"]
        assert topic_state["history_may_help"] is False
        assert topic_state["reason"].endswith("history_not_needed")
        assert snapshot.cockpit["memory_cards"] == ()
        return ModelDirective(response="可以先明确目标，再选具体学习方法。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="new-chat",
        turn_index=1,
        user_input="学习方法应该怎么选？",
        occurred_at=NOW,
    )

    assert result.recommendation.cards == ()


def test_auto_topic_gate_can_open_from_non_conversation_world_observation(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    calendar = _commit_observation(
        store,
        object_id="obs_calendar_project_meeting",
        value="周六上午项目周会，固定占用上午时段。",
        occurred_at=NOW - timedelta(days=5),
        source_kind="calendar",
        dimension="dim:calendar",
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        topic_state = snapshot.cockpit["task_context"]["topic_state"]
        assert topic_state["history_may_help"] is True
        assert "indexed_external_observation_anchor" in topic_state["reason"]
        assert any(
            card["object_id"] == calendar.object_id
            for card in snapshot.cockpit["memory_cards"]
        )
        return ModelDirective(response="周六上午已有日历占用。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="calendar-query",
        turn_index=1,
        user_input="周六上午项目周会要避开吗？",
        occurred_at=NOW,
    )

    assert result.recommendation.cards
