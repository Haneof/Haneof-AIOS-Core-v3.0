from datetime import datetime, timedelta, timezone

from aios_core.ingest.conversation import ConversationIngestor, INTERACTION_DIMENSION
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries.dimension_summary import DimensionSummaryService


DAY = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)


def _seed(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    ingest = ConversationIngestor(store)
    ingest.commit_turn(
        session_id="s1",
        turn_index=1,
        user_text="智能索引和推荐机制要分开。",
        assistant_text="索引作为公共能力。",
        occurred_at=DAY + timedelta(hours=9),
    )
    ingest.commit_turn(
        session_id="s1",
        turn_index=2,
        user_text="ALL_DIMENSIONS只负责跨维观察。",
        assistant_text="因果结论交给AI形成Claim。",
        occurred_at=DAY + timedelta(hours=10),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, ingest


def test_single_dimension_summary_is_durable_and_searchable(tmp_path):
    store, index, _ = _seed(tmp_path)
    service = DimensionSummaryService(store=store, index=index)

    prepared = service.prepare(
        dimension=INTERACTION_DIMENSION,
        granularity="day",
        window_start=DAY,
        window_end=DAY + timedelta(days=1) - timedelta(microseconds=1),
    )
    assert len(prepared.sources) == 4
    assert all(source.metadata["dimension"] == INTERACTION_DIMENSION for source in prepared.sources)

    result = service.commit(
        prepared,
        content="今天围绕智能索引、推荐机制和ALL_DIMENSIONS边界进行了设计讨论。",
        generated_at=DAY + timedelta(hours=23),
    )
    assert result.revision == 1

    payload = store.get_payload(result.object_id)
    assert payload["content"].startswith("今天围绕智能索引")
    assert payload["metadata"]["dimension"] == INTERACTION_DIMENSION
    assert len(payload["source_refs"]) == 4

    page = index.recall_candidates("ALL_DIMENSIONS")
    assert result.object_id in {hit.object_id for hit in page.hits}


def test_new_world_data_creates_forward_summary_revision(tmp_path):
    store, index, ingest = _seed(tmp_path)
    service = DimensionSummaryService(store=store, index=index)

    first_input = service.prepare(
        dimension=INTERACTION_DIMENSION,
        granularity="day",
        window_start=DAY,
        window_end=DAY + timedelta(days=1) - timedelta(microseconds=1),
    )
    first = service.commit(
        first_input,
        content="上午完成了索引与推荐的边界讨论。",
        generated_at=DAY + timedelta(hours=12),
    )

    ingest.commit_turn(
        session_id="s1",
        turn_index=3,
        user_text="晚上继续讨论模型上下文中控。",
        assistant_text="先跑通最小闭环。",
        occurred_at=DAY + timedelta(hours=18),
    )
    index.catch_up()

    second_input = service.prepare(
        dimension=INTERACTION_DIMENSION,
        granularity="day",
        window_start=DAY,
        window_end=DAY + timedelta(days=1) - timedelta(microseconds=1),
    )
    second = service.commit(
        second_input,
        content="当天先讨论索引与推荐，晚上继续推进模型上下文中控和最小闭环。",
        generated_at=DAY + timedelta(hours=23),
    )

    assert first.object_id == second.object_id
    assert first.revision == 1
    assert second.revision == 2
    assert store.get_payload(first.object_id, revision=1)["content"].startswith("上午")
    assert store.get_payload(second.object_id, revision=2)["content"].startswith("当天")
