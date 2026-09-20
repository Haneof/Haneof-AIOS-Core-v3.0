from datetime import datetime, timedelta, timezone

from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 3, 8, 21, 0, tzinfo=timezone.utc)


def _observation(
    *,
    object_id: str,
    value: object,
    at: datetime,
    source_kind: str = "calendar",
    dimension: str = "dim:calendar",
) -> Observation:
    return Observation(
        object_id=object_id,
        subject_id="user_1",
        occurred=TemporalExtent.point(at),
        learned_at=at,
        recorded_at=at,
        created_by="p16-antecedent-regression",
        source_kind=source_kind,
        modality="text",
        value=value,
        metadata={"dimension": dimension},
    )


def _commit(store: SQLiteWorldStore, observation: Observation) -> None:
    store.commit(
        [observation],
        OperationRequest(
            operation_name=f"test.seed.{observation.object_id}",
            expected_world_revision=store.current_world_revision(),
            reason="seed antecedent recall regression",
            idempotency_key=f"seed-{observation.object_id}",
            source_class=SourceClass.USER,
        ),
    )


def test_cross_session_deictic_followup_gets_bounded_antecedent_candidates(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    ingest = ConversationIngestor(store)
    prior = ingest.commit_turn(
        session_id="s1",
        turn_index=1,
        user_text="下周三我要去西雅图出差，早上8点的航班。",
        assistant_text="记下了：下周三早上8点飞西雅图出差。",
        occurred_at=NOW - timedelta(days=7),
    )
    calendar = _observation(
        object_id="obs_calendar_seattle",
        value={"start": "2026-03-11T08:00:00-08:00", "title": "Seattle trip"},
        at=NOW - timedelta(days=6),
    )
    _commit(store, calendar)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        topic = snapshot.cockpit["task_context"]["topic_state"]
        assert topic["history_may_help"] is True
        assert topic["antecedent_recall_needed"] is True
        assert "antecedent_candidate_recall" in topic["reason"]

        cards = snapshot.cockpit["memory_cards"]
        refs = {(item["object_id"], item["revision"]) for item in cards}
        assert (calendar.object_id, 1) in refs
        assert (prior.user_observation_id, 1) in refs
        assert (prior.assistant_observation_id, 1) not in refs
        assert len(cards) <= 5
        assert any(
            item["match_reason"] == "cross_session_antecedent_candidate"
            for item in cards
        )
        return ModelDirective(response="我先按之前那趟行程继续判断。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="s2",
        turn_index=1,
        user_input="那天早上我大概几点出门比较合适？",
        occurred_at=NOW,
    )

    assert result.recommendation.reason == "cross_session_antecedent_candidates"
    assert result.runtime.capability_history == ()


def test_deictic_recall_preserves_ambiguity_instead_of_selecting_one_event(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    trip = _observation(
        object_id="obs_trip",
        value={"title": "Seattle trip", "start": "2026-03-11T08:00:00-08:00"},
        at=NOW - timedelta(days=2),
    )
    dentist = _observation(
        object_id="obs_dentist",
        value={"title": "Dentist appointment", "start": "2026-03-12T10:00:00-08:00"},
        at=NOW - timedelta(days=1),
    )
    _commit(store, trip)
    _commit(store, dentist)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        cards = snapshot.cockpit["memory_cards"]
        refs = {item["object_id"] for item in cards}
        assert trip.object_id in refs
        assert dentist.object_id in refs
        return ModelDirective(
            response="我这里有不止一个近期安排；需要先确认你指的是哪一个。"
        )

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="fresh",
        turn_index=1,
        user_input="那天我要提前多久出门？",
        occurred_at=NOW,
    )

    assert len(result.recommendation.cards) >= 2


def test_concrete_new_session_question_does_not_receive_unrelated_recent_chat(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    ingest = ConversationIngestor(store)
    ingest.commit_turn(
        session_id="old",
        turn_index=1,
        user_text="我准备研究咖啡机。",
        assistant_text="可以先比较预算和清洁成本。",
        occurred_at=NOW - timedelta(days=1),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        topic = snapshot.cockpit["task_context"]["topic_state"]
        assert topic["antecedent_recall_needed"] is False
        assert topic["history_may_help"] is False
        assert snapshot.cockpit["memory_cards"] == ()
        return ModelDirective(response="可以先按重要性和截止时间排序。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="new",
        turn_index=1,
        user_input="给我一个通用的时间管理方法。",
        occurred_at=NOW,
    )

    assert result.recommendation.cards == ()


def test_new_session_bare_continue_exposes_candidates_without_pretending_resolution(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    ingest = ConversationIngestor(store)
    prior = ingest.commit_turn(
        session_id="old",
        turn_index=1,
        user_text="AIOS 的记忆推荐要和公共索引分开。",
        assistant_text="收到。",
        occurred_at=NOW - timedelta(hours=6),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        topic = snapshot.cockpit["task_context"]["topic_state"]
        assert topic["antecedent_recall_needed"] is True
        refs = {item["object_id"] for item in snapshot.cockpit["memory_cards"]}
        assert prior.user_observation_id in refs
        assert prior.assistant_observation_id not in refs
        return ModelDirective(response="我看到了上一段候选上下文，继续前先由我判断关联。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="new",
        turn_index=1,
        user_input="继续。",
        occurred_at=NOW,
    )

    assert result.recommendation.cards
