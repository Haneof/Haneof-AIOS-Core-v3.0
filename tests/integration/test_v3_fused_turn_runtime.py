from datetime import datetime, timedelta, timezone

from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
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


def test_model_can_request_all_dimensions_projection(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    objects = [
        Observation(
            object_id="obs_work_runtime",
            subject_id="user_1",
            occurred=TemporalExtent.point(NOW - timedelta(hours=4)),
            learned_at=NOW - timedelta(hours=4),
            recorded_at=NOW - timedelta(hours=4),
            created_by="runtime-test",
            source_kind="virtual_life",
            modality="text",
            value="项目今天持续加班。",
            metadata={"dimension": "dim:work"},
        ),
        Observation(
            object_id="obs_sleep_runtime",
            subject_id="user_1",
            occurred=TemporalExtent.point(NOW - timedelta(hours=2)),
            learned_at=NOW - timedelta(hours=2),
            recorded_at=NOW - timedelta(hours=2),
            created_by="runtime-test",
            source_kind="virtual_life",
            modality="text",
            value="昨晚入睡明显延后。",
            metadata={"dimension": "dim:sleep"},
        ),
    ]
    store.commit(
        objects,
        OperationRequest(
            operation_name="test.seed.multidim",
            expected_world_revision=0,
            reason="seed runtime projection",
            idempotency_key="seed-runtime-projection",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        if not snapshot.capability_history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="request_all_dimensions_projection",
                        arguments={
                            "dimensions": ["dim:work", "dim:sleep"],
                            "window_start": (NOW - timedelta(days=1)).isoformat(),
                            "window_end": NOW.isoformat(),
                        },
                    ),
                )
            )
        result = snapshot.capability_history[-1]
        assert result.ok is True
        assert [item["dimension"] for item in result.data["slices"]] == ["dim:work", "dim:sleep"]
        assert "causal_conclusion" not in result.data
        return ModelDirective(response="两个维度都出现了变化，但目前只能确认时间上同时出现，不能直接断言因果。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="current",
        turn_index=1,
        user_input="我今天整体状态有什么变化？",
        current_topic=None,
        occurred_at=NOW,
    )

    assert result.runtime.response.startswith("两个维度都出现了变化")
    assert result.runtime.capability_history[0].name == "request_all_dimensions_projection"


def test_model_can_search_then_write_evidence_grounded_claim(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    seed = ConversationIngestor(store)
    seed_result = seed.commit_turn(
        session_id="history",
        turn_index=1,
        user_text="我希望你以后先给我结论，再展开细节。",
        assistant_text="明白，这种反馈我会作为后续沟通依据。",
        occurred_at=NOW - timedelta(days=3),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        if not snapshot.capability_history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="search_world",
                        arguments={"query": "先给结论 展开细节", "limit": 5},
                    ),
                )
            )
        if len(snapshot.capability_history) == 1:
            search = snapshot.capability_history[-1]
            assert search.ok is True
            evidence = next(item for item in search.data if item["object_id"] == seed_result.user_observation_id)
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_claim",
                        arguments={
                            "content": "用户偏好先看到结论，再按需展开细节。",
                            "evidence_refs": [
                                {
                                    "object_id": evidence["object_id"],
                                    "revision": evidence["revision"],
                                }
                            ],
                            "confidence": 0.86,
                            "dimension": "dim:ai_user_understanding",
                        },
                    ),
                )
            )

        written = snapshot.capability_history[-1]
        assert written.ok is True
        assert written.data["claim_id"].startswith("clm_")
        return ModelDirective(response="我会按这个偏好来组织后续回答。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="current",
        turn_index=1,
        user_input="继续。",
        current_topic=None,
        occurred_at=NOW,
    )

    assert result.runtime.response == "我会按这个偏好来组织后续回答。"
    assert [item.name for item in result.runtime.capability_history] == ["search_world", "commit_claim"]

    claim_result = result.runtime.capability_history[-1].data
    claim = store.get_payload(claim_result["claim_id"])
    assert claim["object_type"] == "claim"
    assert claim["content"] == "用户偏好先看到结论，再按需展开细节。"
    assert claim["metadata"]["dimension"] == "dim:ai_user_understanding"
