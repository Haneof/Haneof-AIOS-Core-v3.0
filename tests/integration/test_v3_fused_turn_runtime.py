from datetime import datetime, timedelta, timezone

from aios_core.ai_world import AIWorldClaimRequest, AIWorldCognitionService, AIWorldDomain
from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService


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


def test_model_can_revise_claim_and_propagate_current_view(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)

    old_obs = Observation(
        object_id="obs_old_preference_runtime",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(days=20)),
        learned_at=NOW - timedelta(days=20),
        recorded_at=NOW - timedelta(days=20),
        created_by="runtime-revision-test",
        source_kind="conversation",
        modality="text",
        value="我最近每天都喝茶。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    correction = Observation(
        object_id="obs_new_preference_runtime",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="runtime-revision-test",
        source_kind="conversation",
        modality="text",
        value="现在已经改成每天喝咖啡了。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    store.commit(
        [old_obs, correction],
        OperationRequest(
            operation_name="test.seed.revision.runtime",
            expected_world_revision=0,
            reason="seed revision runtime",
            idempotency_key="seed-revision-runtime",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    writeback = CognitionWritebackService(store=store, index=index)
    old_claim = writeback.commit_claim(
        ClaimWriteRequest(
            content="用户当前偏好每天喝茶。",
            evidence_refs=(ObjectRef(object_id=old_obs.object_id, revision=1),),
            confidence=0.8,
            dimension="dim:ai_user_understanding",
        ),
        learned_at=NOW - timedelta(days=19),
    )

    def model(snapshot):
        if not snapshot.capability_history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="revise_claim",
                        arguments={
                            "target_ref": {
                                "object_id": old_claim.claim_id,
                                "revision": 1,
                            },
                            "reason": "用户明确更新了当前饮品习惯",
                            "evidence_refs": [
                                {
                                    "object_id": correction.object_id,
                                    "revision": 1,
                                }
                            ],
                            "replacement_content": "用户当前偏好每天喝咖啡。",
                            "confidence": 0.92,
                        },
                    ),
                )
            )
        revised = snapshot.capability_history[-1]
        assert revised.ok is True
        assert revised.data["new_revision"] == 2
        return ModelDirective(response="我已按你现在的习惯更新理解。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="current",
        turn_index=1,
        user_input="对，之前喝茶，现在改喝咖啡了。",
        current_topic=None,
        occurred_at=NOW,
    )

    assert result.runtime.capability_history[0].name == "revise_claim"
    assert store.get_payload(old_claim.claim_id, revision=1)["content"] == "用户当前偏好每天喝茶。"
    assert store.get_payload(old_claim.claim_id)["content"] == "用户当前偏好每天喝咖啡。"

    current_old = index.recall_candidates("喝茶", object_types=["claim"])
    assert old_claim.claim_id not in {hit.object_id for hit in current_old.hits}

    current_new = index.recall_candidates("每天喝咖啡", object_types=["claim"])
    assert old_claim.claim_id in {hit.object_id for hit in current_new.hits}


def test_resident_model_can_build_and_read_user_understanding_in_unified_ai_world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    seed = ConversationIngestor(store)
    evidence_turn = seed.commit_turn(
        session_id="history",
        turn_index=1,
        user_text="工程细节你自己判断，不要每一步都反过来问我。",
        assistant_text="收到。",
        occurred_at=NOW - timedelta(days=2),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        history = snapshot.capability_history
        if not history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="search_world",
                        arguments={"query": "工程细节 自己判断", "limit": 5},
                    ),
                )
            )
        if len(history) == 1:
            search = history[-1]
            assert search.ok is True
            evidence = next(
                item for item in search.data
                if item["object_id"] == evidence_turn.user_observation_id
            )
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_ai_world_claim",
                        arguments={
                            "domain": "user_understanding",
                            "statement": "用户希望工程细节由AI自行判断，不要把每个实现选择重新抛回给用户。",
                            "evidence_refs": [
                                {
                                    "object_id": evidence["object_id"],
                                    "revision": evidence["revision"],
                                }
                            ],
                            "confidence": 0.95,
                            "scope_key": "collaboration.engineering_autonomy",
                            "tags": ["direct_feedback"],
                        },
                    ),
                )
            )
        if len(history) == 2:
            written = history[-1]
            assert written.ok is True
            assert written.data["domain"] == "user_understanding"
            assert written.data["dimension"] == "dim:ai_user_understanding"
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="read_ai_world",
                        arguments={
                            "domains": ["user_understanding"],
                            "scope_key": "collaboration.engineering_autonomy",
                        },
                    ),
                )
            )

        current = history[-1]
        assert current.ok is True
        assert len(current.data) == 1
        assert "工程细节由AI自行判断" in current.data[0]["statement"]
        return ModelDirective(response="我会直接推进工程实现，只有真正缺少产品目标时才向你确认。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="current",
        turn_index=1,
        user_input="继续AIOS。",
        current_topic=None,
        occurred_at=NOW,
    )

    assert [
        item.name for item in result.runtime.capability_history
    ] == ["search_world", "commit_ai_world_claim", "read_ai_world"]
    assert result.runtime.response.startswith("我会直接推进工程实现")

    claims = store.list_payloads()
    ai_claims = [
        item for item in claims
        if item.get("object_type") == "claim"
        and (item.get("metadata") or {}).get("ai_domain") == "user_understanding"
    ]
    assert len(ai_claims) == 1
    assert ai_claims[0]["metadata"]["scope_key"] == "collaboration.engineering_autonomy"


def test_new_session_loads_only_explicit_core_ai_world_context(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    facts = [
        Observation(
            object_id="obs_core_context_role",
            subject_id="user_1",
            occurred=TemporalExtent.point(NOW - timedelta(days=4)),
            learned_at=NOW - timedelta(days=4),
            recorded_at=NOW - timedelta(days=4),
            created_by="core-context-test",
            source_kind="conversation",
            modality="text",
            value="这个项目你要持续执行，不只是给建议。",
            metadata={"dimension": "dim:user_ai_interaction"},
        ),
        Observation(
            object_id="obs_non_core_preference",
            subject_id="user_1",
            occurred=TemporalExtent.point(NOW - timedelta(days=3)),
            learned_at=NOW - timedelta(days=3),
            recorded_at=NOW - timedelta(days=3),
            created_by="core-context-test",
            source_kind="conversation",
            modality="text",
            value="我今天比较喜欢短一点的回复。",
            metadata={"dimension": "dim:user_ai_interaction"},
        ),
    ]
    store.commit(
        facts,
        OperationRequest(
            operation_name="test.seed.core_context",
            expected_world_revision=0,
            reason="seed core continuity context",
            idempotency_key="seed-core-context",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    ai_world = AIWorldCognitionService(store=store, index=index)

    ai_world.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.SELF,
            statement="我在这个长期项目中的角色包含持续执行、核验和断点续传。",
            evidence_refs=(ObjectRef(object_id=facts[0].object_id, revision=1),),
            confidence=0.95,
            scope_key="project_role",
            tags=("core_context",),
        ),
        learned_at=NOW - timedelta(days=2),
    )
    ai_world.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.USER_UNDERSTANDING,
            statement="用户今天偏好较短回复。",
            evidence_refs=(ObjectRef(object_id=facts[1].object_id, revision=1),),
            confidence=0.7,
            scope_key="communication.detail_level",
        ),
        learned_at=NOW - timedelta(days=1),
    )

    def model(snapshot):
        continuity = snapshot.cockpit["ai_identity"]
        assert "self" in continuity
        assert continuity["self"][0]["scope_key"] == "project_role"
        assert "user_understanding" not in continuity
        return ModelDirective(response="继续当前项目主线。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="brand-new-session",
        turn_index=1,
        user_input="继续。",
        current_topic=None,
        occurred_at=NOW,
    )

    assert result.runtime.response == "继续当前项目主线。"
