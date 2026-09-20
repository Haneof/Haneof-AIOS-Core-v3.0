from datetime import datetime, timedelta, timezone

from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.recommendation.proactive import ProactiveMemoryRecommender
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def _system(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    ingest = ConversationIngestor(store)
    ingest.commit_turn(
        session_id="old-session",
        turn_index=1,
        user_text="智能索引和推荐机制一定要分开。",
        assistant_text="索引是公共能力，推荐只是调用方。",
        occurred_at=NOW - timedelta(days=10),
    )
    ingest.commit_turn(
        session_id="other-session",
        turn_index=1,
        user_text="妈妈生日准备买一个保温杯。",
        assistant_text="记录一下这个计划。",
        occurred_at=NOW - timedelta(days=8),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def test_no_topic_means_zero_historical_injection(tmp_path):
    store, index = _system(tmp_path)
    recommender = ProactiveMemoryRecommender(index=index, store=store)
    bundle = recommender.recommend(current_topic=None)

    assert bundle.topic_gate_open is False
    assert bundle.cards == ()
    assert bundle.reason == "no_current_topic"


def test_topic_proactively_recalls_related_history(tmp_path):
    store, index = _system(tmp_path)
    recommender = ProactiveMemoryRecommender(index=index, store=store)
    bundle = recommender.recommend(current_topic="智能索引")

    assert bundle.topic_gate_open is True
    assert bundle.cards
    assert any("索引" in card.excerpt for card in bundle.cards)
    assert all("生日" not in card.excerpt for card in bundle.cards)


def test_unrelated_topic_returns_empty_bundle(tmp_path):
    store, index = _system(tmp_path)
    recommender = ProactiveMemoryRecommender(index=index, store=store)
    bundle = recommender.recommend(current_topic="天气预报")

    assert bundle.topic_gate_open is True
    assert bundle.cards == ()
    assert bundle.reason == "topic_has_no_matching_history"


def test_current_session_can_be_excluded_from_history_recommendation(tmp_path):
    store, index = _system(tmp_path)
    recommender = ProactiveMemoryRecommender(index=index, store=store)
    bundle = recommender.recommend(
        current_topic="智能索引",
        exclude_session_id="old-session",
    )

    assert bundle.cards == ()
