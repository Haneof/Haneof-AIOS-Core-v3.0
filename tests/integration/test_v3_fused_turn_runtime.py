from datetime import datetime, timedelta, timezone

from aios_core.ai_world import AIWorldClaimRequest, AIWorldCognitionService, AIWorldDomain
from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.dimensions import DimensionProposalRequest, DimensionRegistryService
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective, ModelUsage
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
    assert result.conversation_commit.user_world_revision == 2
    assert result.conversation_commit.assistant_world_revision == 3
    assert result.conversation_commit.world_revision == 3

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


def test_resident_model_can_check_existing_dimensions_then_propose_candidate(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    evidence = Observation(
        object_id="obs_dimension_runtime",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(days=1)),
        learned_at=NOW - timedelta(days=1),
        recorded_at=NOW - timedelta(days=1),
        created_by="dimension-runtime-test",
        source_kind="virtual_life",
        modality="text",
        value="最近多次学习任务中，用户独立解决复杂问题的能力在变化。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    store.commit(
        [evidence],
        OperationRequest(
            operation_name="test.seed.dimension.runtime",
            expected_world_revision=0,
            reason="seed dimension proposal evidence",
            idempotency_key="seed-dimension-runtime",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        history = snapshot.capability_history
        if not history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="list_dimensions",
                        arguments={"include_terminal": False},
                    ),
                )
            )
        if len(history) == 1:
            assert history[-1].ok is True
            assert history[-1].data == []
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="search_world",
                        arguments={"query": "学习任务 独立解决 复杂问题", "limit": 5},
                    ),
                )
            )
        if len(history) == 2:
            search = history[-1]
            assert search.ok is True
            source = next(
                item for item in search.data
                if item["object_id"] == evidence.object_id
            )
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="propose_dimension",
                        arguments={
                            "dimension_key": "dim:learning_ability",
                            "name": "学习能力",
                            "description": "长期观察用户独立解决学习任务的能力变化。",
                            "data_shape": "evidence_grounded_cognition_over_time",
                            "evidence_refs": [
                                {
                                    "object_id": source["object_id"],
                                    "revision": source["revision"],
                                }
                            ],
                            "why_existing_dimensions_are_insufficient": "现有事实维度记录单次学习事件，但没有持续能力观察轴。",
                            "continuity_rationale": "后续学习事件和结果可持续更新该观察轴。",
                            "user_value_rationale": "有助于调整教学难度和帮助方式。",
                            "maintenance_cost_rationale": "只记录有证据的变化和总结，不复制原始学习事实。",
                            "confidence": 0.72,
                        },
                    ),
                )
            )

        proposed = history[-1]
        assert proposed.ok is True
        assert proposed.data["lifecycle"] == "candidate"
        return ModelDirective(response="我已把它作为候选观察轴登记，先通过真实运行继续验证。")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        max_tool_rounds=4,
    )
    result = runtime.run_turn(
        session_id="current",
        turn_index=1,
        user_input="你觉得长期学习能力值得单独观察吗？",
        current_topic=None,
        occurred_at=NOW,
    )

    assert [
        item.name for item in result.runtime.capability_history
    ] == ["list_dimensions", "search_world", "propose_dimension"]
    definitions = store.list_payloads()
    dynamic = [
        item for item in definitions
        if item.get("object_type") == "dimension_definition"
        and (item.get("metadata") or {}).get("dimension_key") == "dim:learning_ability"
    ]
    assert len(dynamic) == 1
    assert dynamic[0]["lifecycle"] == "candidate"


def test_resident_model_can_move_candidate_dimension_into_trial(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    evidence = Observation(
        object_id="obs_dimension_transition_runtime",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(days=5)),
        learned_at=NOW - timedelta(days=5),
        recorded_at=NOW - timedelta(days=5),
        created_by="dimension-transition-runtime-test",
        source_kind="virtual_life",
        modality="text",
        value="连续学习记录显示值得继续观察能力变化。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    store.commit(
        [evidence],
        OperationRequest(
            operation_name="test.seed.dimension.transition.runtime",
            expected_world_revision=0,
            reason="seed transition evidence",
            idempotency_key="seed-dimension-transition-runtime",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    registry = DimensionRegistryService(store=store, index=index)
    candidate = registry.propose(
        DimensionProposalRequest(
            dimension_key="dim:learning_ability",
            name="学习能力",
            description="持续观察学习能力变化。",
            data_shape="evidence_grounded_cognition_over_time",
            evidence_refs=(ObjectRef(object_id=evidence.object_id, revision=1),),
            why_existing_dimensions_are_insufficient="现有事实轴不足以连续表达能力变化。",
            continuity_rationale="后续学习结果可以持续更新。",
            user_value_rationale="可用于调整教学支持。",
            maintenance_cost_rationale="只保留能力变化Claim和Summary。",
            confidence=0.7,
        ),
        proposed_at=NOW - timedelta(days=4),
    )

    def model(snapshot):
        history = snapshot.capability_history
        if not history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="list_dimensions",
                        arguments={"include_terminal": False},
                    ),
                )
            )
        if len(history) == 1:
            dimensions = history[-1].data
            current = next(
                item for item in dimensions
                if item["object_id"] == candidate.dimension_id
            )
            assert current["lifecycle"] == "candidate"
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="transition_dimension",
                        arguments={
                            "dimension_ref": {
                                "object_id": candidate.dimension_id,
                                "revision": 1,
                            },
                            "new_lifecycle": "trial",
                            "reason": "AI决定让该观察轴进入真实运行试用，而不是直接判定为有效。",
                            "evidence_refs": [
                                {
                                    "object_id": evidence.object_id,
                                    "revision": 1,
                                }
                            ],
                        },
                    ),
                )
            )
        transitioned = history[-1]
        assert transitioned.ok is True
        assert transitioned.data["new_lifecycle"] == "trial"
        return ModelDirective(response="先进入试用，继续通过后续真实生活数据验证。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="current",
        turn_index=1,
        user_input="这个新维度现在应该怎么办？",
        current_topic=None,
        occurred_at=NOW,
    )

    assert [
        item.name for item in result.runtime.capability_history
    ] == ["list_dimensions", "transition_dimension"]
    assert store.get_payload(candidate.dimension_id)["lifecycle"] == "trial"


def test_current_user_input_can_ground_same_turn_goal_task_and_action_proposal(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        catalog_names = {item["name"] for item in snapshot.cockpit["capability_catalog"]}
        assert "propose_action" in catalog_names
        assert "authorize_action" not in catalog_names
        assert "record_outcome" not in catalog_names

        current_ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
        history = snapshot.capability_history

        if not history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="propose_goal",
                        arguments={
                            "source_type": "user_explicit",
                            "title": "发送项目周报",
                            "description": "按用户本轮要求把确认后的项目周报发送给团队。",
                            "evidence_refs": [current_ref],
                            "confidence": 0.99,
                            "success_criteria": ["团队收到确认后的项目周报"],
                        },
                    ),
                )
            )

        if len(history) == 1:
            goal = history[-1].data
            assert goal["status"] == "proposed"
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="transition_goal",
                        arguments={
                            "goal_ref": {
                                "object_id": goal["goal_id"],
                                "revision": goal["revision"],
                            },
                            "new_status": "active",
                            "reason": "用户在当前会话明确提出该目标。",
                            "evidence_refs": [current_ref],
                        },
                    ),
                )
            )

        if len(history) == 2:
            goal = history[-1].data
            assert goal["status"] == "active"
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="create_task",
                        arguments={
                            "title": "发送确认后的项目周报",
                            "task_type": "immediate",
                            "reason_refs": [current_ref],
                            "goal_ref": {
                                "object_id": goal["goal_id"],
                                "revision": goal["revision"],
                            },
                            "initial_state": "ready",
                            "priority": 80,
                        },
                    ),
                )
            )

        if len(history) == 3:
            task = history[-1].data
            assert task["state"] == "ready"
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="transition_task",
                        arguments={
                            "task_ref": {
                                "object_id": task["task_id"],
                                "revision": task["revision"],
                            },
                            "new_state": "running",
                            "reason": "开始准备执行用户明确要求的发送任务。",
                            "evidence_refs": [current_ref],
                        },
                    ),
                )
            )

        if len(history) == 4:
            task = history[-1].data
            assert task["state"] == "running"
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="propose_action",
                        arguments={
                            "task_ref": {
                                "object_id": task["task_id"],
                                "revision": task["revision"],
                            },
                            "action_type": "send_team_message",
                            "payload": {
                                "channel": "team",
                                "document": "weekly-report",
                            },
                            "expected_outcome": "团队收到确认后的项目周报",
                            "evidence_refs": [current_ref],
                        },
                    ),
                )
            )

        action = history[-1].data
        assert action["revision"] == 1
        assert store.get_payload(action["action_id"])["action_status"] == "proposed"
        return ModelDirective(
            response="发送动作已经形成提案，等待独立授权层批准后才能真正执行。"
        )

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        max_tool_rounds=8,
    )
    result = runtime.run_turn(
        session_id="same-turn-p12",
        turn_index=1,
        user_input="把我确认后的项目周报发给团队。",
        current_topic="项目周报",
        occurred_at=NOW,
    )

    assert [
        item.name for item in result.runtime.capability_history
    ] == [
        "propose_goal",
        "transition_goal",
        "create_task",
        "transition_task",
        "propose_action",
    ]
    current_user_ref = result.context.task_context["current_user_observation_ref"]
    user_payload = store.get_payload(
        current_user_ref["object_id"],
        revision=current_user_ref["revision"],
    )
    assert user_payload["value"] == "把我确认后的项目周报发给团队。"

    actions = [
        item
        for item in store.list_payloads()
        if item.get("object_type") == "action"
    ]
    assert len(actions) == 1
    assert actions[0]["action_status"] == "proposed"
    assert actions[0]["metadata"]["authorization_required"] is True



def test_user_interaction_model_call_is_metered_outside_world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda snapshot: ModelDirective(
            response="收到。",
            usage=ModelUsage(
                input_tokens=13,
                output_tokens=2,
                total_tokens=15,
                provider="openai",
                model="test-model",
                request_id="resp_user_meter",
            ),
        ),
    )
    result = runtime.run_turn(
        session_id="meter-session",
        turn_index=1,
        user_input="测试计量。",
        current_topic=None,
        occurred_at=NOW,
    )

    rows = runtime.metering.list_model_calls(subject_id="user_1")
    assert len(rows) == 1
    assert rows[0].execution_class == "user_interaction"
    assert rows[0].session_id == "meter-session"
    assert rows[0].wake_id is None
    assert rows[0].total_tokens == 15
    assert rows[0].provider_request_id == "resp_user_meter"

    # The model call is metered between user-ingest and assistant writeback without
    # creating an extra world commit of its own.
    assert rows[0].world_revision == result.conversation_commit.user_world_revision
    assert result.conversation_commit.assistant_world_revision == (
        result.conversation_commit.user_world_revision + 1
    )
