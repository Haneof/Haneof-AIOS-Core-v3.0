from datetime import datetime, timezone

import pytest

from aios_core.contracts.enums import ObjectType
from aios_core.errors import AIOSProtocolError
from aios_core.ingest.conversation import ConversationIngestor, INTERACTION_DIMENSION
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def test_turn_is_atomic_unified_world_fact_and_searchable(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    ingest = ConversationIngestor(store, subject_id="user_1")

    result = ingest.commit_turn(
        session_id="session-1",
        turn_index=1,
        user_text="我们继续讨论智能世界索引",
        assistant_text="好，先把索引底座跑通。",
        occurred_at=NOW,
    )

    assert result.world_revision == 1
    payloads = store.list_payloads(object_type=ObjectType.OBSERVATION)
    assert len(payloads) == 2
    assert {p["metadata"]["role"] for p in payloads} == {"user", "assistant"}
    assert {p["metadata"]["dimension"] for p in payloads} == {INTERACTION_DIMENSION}
    assert all(p["metadata"]["session_id"] == "session-1" for p in payloads)

    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    page = index.co_search(["世界", "索引"])
    assert page.status == "ok"
    assert result.user_observation_id in {hit.object_id for hit in page.hits}


def test_exact_retry_is_idempotent_but_changed_text_conflicts(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    ingest = ConversationIngestor(store)

    first = ingest.commit_turn(
        session_id="s1",
        turn_index=1,
        user_text="昨天说到哪里了",
        assistant_text="我们说到索引和推荐要分开。",
        occurred_at=NOW,
    )
    replay = ingest.commit_turn(
        session_id="s1",
        turn_index=1,
        user_text="昨天说到哪里了",
        assistant_text="我们说到索引和推荐要分开。",
        occurred_at=NOW,
    )
    assert first.world_revision == replay.world_revision == 1
    assert replay.idempotent_replay is True

    with pytest.raises(AIOSProtocolError):
        ingest.commit_turn(
            session_id="s1",
            turn_index=1,
            user_text="昨天说到哪里了",
            assistant_text="被篡改的不同回答",
            occurred_at=NOW,
        )
