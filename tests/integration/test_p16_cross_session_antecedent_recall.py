from datetime import datetime, timedelta, timezone

from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.recommendation.topic_state import TopicStateService
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 3, 8, 21, 0, tzinfo=timezone.utc)
# T33 regression file intentionally exercises the real FusedTurnRuntime gate.


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

    assert result.recommendation.reason == "topic_matched_history_with_antecedent_candidates"
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


def test_self_contained_demonstrative_does_not_open_cross_session_recall(tmp_path):
    """Case A: a locally specified current preference must not pull old history."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    ingest = ConversationIngestor(store)
    ingest.commit_turn(
        session_id="old-1",
        turn_index=1,
        user_text="我以前比较过红色和绿色的包装。",
        assistant_text="可以以后再比较。",
        occurred_at=NOW - timedelta(days=30),
    )
    ingest.commit_turn(
        session_id="old-2",
        turn_index=1,
        user_text="开店前我还讨论过咖啡机清洁。",
        assistant_text="记录过这个旧话题。",
        occurred_at=NOW - timedelta(days=20),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        topic = snapshot.cockpit["task_context"]["topic_state"]
        assert topic["antecedent_recall_needed"] is False
        assert topic["history_may_help"] is False
        assert snapshot.cockpit["memory_cards"] == ()
        return ModelDirective(response="已按你当前明确表达的偏好处理。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="new",
        turn_index=1,
        user_input="我喜欢这个颜色：深蓝色。请把它作为当前偏好记录。",
        occurred_at=NOW,
    )

    assert result.recommendation.cards == ()
    assert result.recommendation.reason == "current_topic_does_not_need_history"


def test_true_cross_session_ellipsis_exposes_candidates_without_binding_identity(tmp_path):
    """Case B: an explicitly historical elliptical follow-up may expose candidates."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    ingest = ConversationIngestor(store)
    prior = ingest.commit_turn(
        session_id="old",
        turn_index=1,
        user_text="上次我们在讨论西雅图出差前一晚要准备什么。",
        assistant_text="我列了一个准备清单。",
        occurred_at=NOW - timedelta(days=4),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        topic = snapshot.cockpit["task_context"]["topic_state"]
        assert topic["history_may_help"] is True
        assert topic["antecedent_recall_needed"] is True
        refs = {item["object_id"] for item in snapshot.cockpit["memory_cards"]}
        assert prior.user_observation_id in refs
        assert prior.assistant_observation_id not in refs
        return ModelDirective(response="我看到了历史候选，但仍由我判断你具体指哪一项。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="new",
        turn_index=1,
        user_input="上次那个继续。",
        occurred_at=NOW,
    )

    assert result.recommendation.cards
    assert all(
        card.match_reason in {
            "current_topic_index_overlap",
            "cross_session_antecedent_candidate",
        }
        for card in result.recommendation.cards
    )


def test_deictic_without_trustworthy_history_exposes_no_fake_antecedent(tmp_path):
    """Case C: the gate may open, but Core must not fabricate an antecedent."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        topic = snapshot.cockpit["task_context"]["topic_state"]
        assert topic["history_may_help"] is True
        assert topic["antecedent_recall_needed"] is True
        assert snapshot.cockpit["memory_cards"] == ()
        return ModelDirective(response="当前没有可信历史候选，我需要继续搜索或向用户确认。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="fresh",
        turn_index=1,
        user_input="那天后来怎么样了？",
        occurred_at=NOW,
    )

    assert result.recommendation.cards == ()


def test_same_session_continuation_uses_recent_turn_without_cross_session_fallback():
    """Same-session continuity remains distinct from cross-session antecedent recovery."""
    state = TopicStateService().resolve(
        user_input="那个继续。",
        recent_turns=(
            {"role": "user", "text": "我们先讨论预算上限。"},
            {"role": "assistant", "text": "可以。"},
        ),
    )

    assert state.continued_from_recent_turn is True
    assert state.antecedent_recall_needed is False
    assert state.history_may_help is True
    assert state.topic == "我们先讨论预算上限。"


def test_embedded_continuation_word_in_self_contained_request_does_not_open_history():
    state = TopicStateService().resolve(
        user_input="我准备继续学习 Python，请帮我整理今天的计划。",
        recent_turns=(),
    )

    assert state.continued_from_recent_turn is False
    assert state.antecedent_recall_needed is False
    assert state.history_may_help is False
