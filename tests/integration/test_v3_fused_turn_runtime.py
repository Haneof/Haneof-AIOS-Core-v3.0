from datetime import datetime, timedelta, timezone

from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def test_vertical_slice_proactively_remembers_then_writes_new_turn(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    seed = ConversationIngestor(store)
    seed.commit_turn(
        session_id="history",
        turn_index=1,
        user_text="智能索引和智能推荐一定要分开。",
        assistant_text="索引是公共能力，推荐机制调用索引。",
        occurred_at=NOW - timedelta(days=5),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        cards = snapshot.cockpit["memory_cards"]
        assert cards
        assert any("索引" in card["excerpt"] for card in cards)
        return ModelDirective(response="接着之前的方案：索引继续作为公共能力。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="current",
        turn_index=1,
        user_input="继续这个方案",
        current_topic="智能索引",
        occurred_at=NOW,
    )

    assert result.runtime.termination_reason == "responded"
    assert result.recommendation.cards
    assert result.conversation_commit.world_revision == 2

    page = index.recall_candidates("继续这个方案")
    assert any(hit.object_id == result.conversation_commit.user_observation_id for hit in page.hits)


def test_model_can_ignore_empty_prefetch_and_deep_search(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    seed = ConversationIngestor(store)
    seed.commit_turn(
        session_id="history",
        turn_index=1,
        user_text="妈妈生日准备买保温杯，预算三百元。",
        assistant_text="记下了。",
        occurred_at=NOW - timedelta(days=30),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        if not snapshot.capability_history:
            assert snapshot.cockpit["memory_cards"] == ()
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="search_world",
                        arguments={"query": "妈妈生日保温杯", "limit": 5},
                    ),
                )
            )
        search_result = snapshot.capability_history[-1]
        assert search_result.ok is True
        assert any("预算三百元" in item["excerpt"] for item in search_result.data)
        return ModelDirective(response="之前的记录里预算是三百元。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="current",
        turn_index=1,
        user_input="妈妈生日那个保温杯预算是多少？",
        current_topic=None,
        occurred_at=NOW,
    )

    assert result.recommendation.cards == ()
    assert len(result.runtime.capability_history) == 1
    assert result.runtime.response == "之前的记录里预算是三百元。"
