from datetime import datetime, timezone

from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.recommendation.proactive import ProactiveMemoryRecommender
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)


def test_assistant_interpretation_cannot_self_reinforce_as_p16_proactive_memory(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    ingest = ConversationIngestor(store)
    prior = ingest.commit_turn(
        session_id="prior",
        turn_index=1,
        user_text="今天第一次跟朋友试了下攀岩，鞋是临时租的。",
        assistant_text="你可能已经把攀岩当成固定爱好了。",
        occurred_at=NOW,
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    # Audit/search access to the raw assistant turn remains intact.
    raw = index.recall_candidates("固定爱好")
    assert any(hit.object_id == prior.assistant_observation_id for hit in raw.hits)

    recommender = ProactiveMemoryRecommender(index=index, store=store)

    # The assistant's own interpretation is not independent personalization evidence.
    assistant_only = recommender.recommend(current_topic="固定爱好")
    assert assistant_only.cards == ()

    # The user's actual raw dialogue remains eligible.
    user_history = recommender.recommend(current_topic="第一次跟朋友试了下攀岩")
    assert any(card.object_id == prior.user_observation_id for card in user_history.cards)
