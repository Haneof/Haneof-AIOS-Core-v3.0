"""Integration tests for C15-RCC-COGNITION-FIELDS-001.

Validates the full exposure of:
- valid_time (bounded temporal scope)
- unknown_items (explicit uncertainty boundary)
- counter_evidence_refs (counter-evidence tracking)
- counter_evidence_summary (in read_ai_world, snapshot, and core_context)
"""

from datetime import datetime, timedelta, timezone

from aios_core.ai_world import (
    AI_SELF_SUBJECT_ID,
    AIWorldClaimRequest,
    AIWorldCognitionService,
    AIWorldDomain,
)
from aios_core.contracts.models import TemporalExtent
from aios_core.contracts.time import TimePrecision
from aios_core.contracts.refs import ObjectRef
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.revision.service import ClaimRevisionRequest, CognitionRevisionService
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService


NOW = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)


def test_turn_runtime_commit_ai_world_claim_with_valid_time_and_unknowns(tmp_path):
    """Test commit_ai_world_claim and read_ai_world with bounded sprint valid_time and unknown_items."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    seed = ConversationIngestor(store)
    sprint_turn = seed.commit_turn(
        session_id="sprint_sess",
        turn_index=1,
        user_text="现在是项目冲刺期，回复尽量短，挑重点说即可。",
        assistant_text="收到，冲刺期间保持极简短回复。",
        occurred_at=NOW - timedelta(days=2),
    )
    weekend_turn = seed.commit_turn(
        session_id="weekend_sess",
        turn_index=1,
        user_text="今天周六闲聊一下，你详细展开讲讲手环柔性屏在弯折受力时的热力学模拟过程？",
        assistant_text="没问题，我们从柔性铰链力学模型和热耗散方程开始详细拆解...",
        occurred_at=NOW - timedelta(days=1),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    sprint_start = NOW - timedelta(days=7)
    sprint_end = NOW + timedelta(days=7)
    sprint_valid_time = TemporalExtent(
        start=sprint_start,
        end=sprint_end,
        precision=TimePrecision.DAY,
    )

    call_states: list[str] = []

    def model(snapshot):
        history = snapshot.capability_history
        if snapshot.user_input == "记录我的回复偏好":
            if not history:
                call_states.append("step1_search")
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="search_world",
                            arguments={"query": "冲刺期 短回复"},
                        ),
                    )
                )
            if len(history) == 1:
                call_states.append("step2_commit")
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="commit_ai_world_claim",
                            arguments={
                                "domain": "user_understanding",
                                "statement": "在最近项目冲刺期间，用户更偏好短回复。",
                                "evidence_refs": [
                                    {
                                        "object_id": sprint_turn.user_observation_id,
                                        "revision": 1,
                                    }
                                ],
                                "confidence": 0.9,
                                "scope_key": "communication.verbosity_preference",
                                "tags": ["core_context", "preference"],
                                "valid_time": sprint_valid_time.model_dump(mode="json"),
                                "unknown_items": ["其他场景未知"],
                            },
                        ),
                    )
                )
            if len(history) == 2:
                call_states.append("step3_read")
                assert history[-1].ok is True
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="read_ai_world",
                            arguments={
                                "domains": ["user_understanding"],
                                "scope_key": "communication.verbosity_preference",
                            },
                        ),
                    )
                )

            call_states.append("step4_respond")
            read_result = history[-1]
            assert read_result.ok is True
            items = read_result.data
            assert len(items) == 1
            claim_view = items[0]

            # Verify bounded cognition fields in read_ai_world
            assert claim_view["statement"] == "在最近项目冲刺期间，用户更偏好短回复。"
            assert claim_view["unknown_items"] == ["其他场景未知"]
            assert claim_view["valid_time"]["start"] is not None
            assert claim_view["valid_time"]["end"] is not None
            assert claim_view["valid_time"]["unknown"] is False
            assert claim_view["counter_evidence_summary"]["count"] == 0
            assert claim_view["counter_evidence_summary"]["counter_refs"] == []

            return ModelDirective(response="已认知：冲刺期间偏好短回复，其他场景保持观察。")

        # Second turn: revise
        if not history:
            call_states.append("step1_read_for_target")
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="read_ai_world",
                        arguments={
                            "domains": ["user_understanding"],
                            "scope_key": "communication.verbosity_preference",
                        },
                    ),
                )
            )
        if len(history) == 1:
            call_states.append("step2_revise")
            read_item = history[-1].data[0]
            target_ref = {"object_id": read_item["object_id"], "revision": read_item["revision"]}
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="revise_claim",
                        arguments={
                            "target_ref": target_ref,
                            "reason": "周六闲聊时用户要求详细展开讨论，反例证明偏好仅限于冲刺工作场景",
                            "evidence_refs": [
                                {
                                    "object_id": sprint_turn.user_observation_id,
                                    "revision": 1,
                                }
                            ],
                            "replacement_content": "在最近项目冲刺期间，用户偏好短回复；但非工作闲聊与深度探讨时更倾向详细回复。",
                            "confidence": 0.92,
                            "valid_time": sprint_valid_time.model_dump(mode="json"),
                            "unknown_items": ["复杂架构研讨场景偏好待观察"],
                            "counter_evidence_refs": [
                                {
                                    "object_id": weekend_turn.user_observation_id,
                                    "revision": 1,
                                }
                            ],
                        },
                    ),
                )
            )
        if len(history) == 2:
            call_states.append("step3_verify_read")
            assert history[-1].ok is True
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="read_ai_world",
                        arguments={
                            "domains": ["user_understanding"],
                            "scope_key": "communication.verbosity_preference",
                        },
                    ),
                )
            )

        call_states.append("step4_respond_revised")
        revised_view = history[-1].data[0]
        assert revised_view["revision"] == 2
        assert "非工作闲聊与深度探讨时更倾向详细回复" in revised_view["statement"]
        assert revised_view["unknown_items"] == ["复杂架构研讨场景偏好待观察"]
        # Verify counter_evidence_summary reflects the counter evidence!
        ces = revised_view["counter_evidence_summary"]
        assert ces["count"] == 1
        assert len(ces["counter_refs"]) == 1
        assert ces["counter_refs"][0]["object_id"] == weekend_turn.user_observation_id
        assert ces["counter_refs"][0]["revision"] == 1
        assert len(ces["counter_evidence_set_refs"]) == 1

        return ModelDirective(response="已修正回复偏好认知：冲刺期间简短，闲聊深度展开。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="turn_session",
        turn_index=1,
        user_input="记录我的回复偏好",
        current_topic="偏好设定",
        occurred_at=NOW,
    )

    assert result.runtime.termination_reason == "responded"
    assert call_states == ["step1_search", "step2_commit", "step3_read", "step4_respond"]

    # Now run second turn
    call_states.clear()
    result2 = runtime.run_turn(
        session_id="turn_session",
        turn_index=2,
        user_input="修正之前的偏好结论",
        current_topic="偏好设定",
        occurred_at=NOW + timedelta(hours=1),
    )

    assert result2.runtime.termination_reason == "responded"
    assert call_states == [
        "step1_read_for_target",
        "step2_revise",
        "step3_verify_read",
        "step4_respond_revised",
    ]


def test_ai_world_direct_service_full_lifecycle(tmp_path):
    """Test AIWorldCognitionService direct commit, revise, and current view inspection."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    seed = ConversationIngestor(store)
    turn1 = seed.commit_turn(
        session_id="sess1",
        turn_index=1,
        user_text="平时不要啰嗦，挑重点说。",
        assistant_text="收到。",
        occurred_at=NOW - timedelta(days=3),
    )
    turn2 = seed.commit_turn(
        session_id="sess2",
        turn_index=1,
        user_text="请展开长篇分析这个架构方案的前因后果。",
        assistant_text="好的，详细分析如下...",
        occurred_at=NOW - timedelta(days=1),
    )

    service = AIWorldCognitionService(store=store, user_id="user_1")
    sprint_extent = TemporalExtent(
        start=NOW - timedelta(days=5),
        end=NOW + timedelta(days=5),
        precision=TimePrecision.DAY,
    )

    # 1. Commit initial claim with valid_time, unknown_items, counter_evidence_refs
    receipt = service.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.USER_UNDERSTANDING,
            statement="日常任务中偏好极简重点回复",
            evidence_refs=(ObjectRef(object_id=turn1.user_observation_id, revision=1),),
            confidence=0.85,
            scope_key="pref.brevity",
            tags=("core_context", "preference"),
            valid_time=sprint_extent,
            unknown_items=("长篇架构方案设计场景未知",),
            counter_evidence_refs=(),
        ),
        learned_at=NOW,
    )
    assert receipt.claim.claim_id.startswith("clm_")

    # Verify current view
    views = service.current(domains=[AIWorldDomain.USER_UNDERSTANDING], scope_key="pref.brevity")
    assert len(views) == 1
    v = views[0]
    assert v.statement == "日常任务中偏好极简重点回复"
    assert v.valid_time.start == sprint_extent.start
    assert v.valid_time.end == sprint_extent.end
    assert v.unknown_items == ("长篇架构方案设计场景未知",)
    assert v.counter_evidence_summary == {
        "count": 0,
        "counter_evidence_set_refs": [],
        "counter_refs": [],
    }

    # Verify core_context snapshot contains the new fields
    core = service.core_context()
    assert "user_understanding" in core
    core_item = core["user_understanding"][0]
    assert core_item["statement"] == "日常任务中偏好极简重点回复"
    assert "valid_time" in core_item
    assert core_item["unknown_items"] == ["长篇架构方案设计场景未知"]
    assert core_item["counter_evidence_summary"]["count"] == 0

    # 2. Revise claim adding counter_evidence_refs
    rev_receipt = service.revise(
        target_ref=ObjectRef(object_id=receipt.claim.claim_id, revision=1),
        evidence_refs=[ObjectRef(object_id=turn1.user_observation_id, revision=1)],
        replacement_statement="日常任务偏好重点回复，但在技术方案设计时要求展开详尽分析",
        reason="观察到技术方案设计时的反例",
        changed_at=NOW + timedelta(hours=2),
        confidence=0.9,
        valid_time=sprint_extent,
        unknown_items=("紧急故障排查场景未知",),
        counter_evidence_refs=[ObjectRef(object_id=turn2.user_observation_id, revision=1)],
    )
    assert rev_receipt.new_revision == 2

    # Verify updated current view
    views2 = service.current(domains=[AIWorldDomain.USER_UNDERSTANDING], scope_key="pref.brevity")
    assert len(views2) == 1
    v2 = views2[0]
    assert v2.revision == 2
    assert "日常任务偏好重点回复" in v2.statement
    assert v2.unknown_items == ("紧急故障排查场景未知",)
    assert v2.counter_evidence_summary["count"] == 1
    assert v2.counter_evidence_summary["counter_refs"] == [
        {"object_id": turn2.user_observation_id, "revision": 1}
    ]
    assert len(v2.counter_evidence_summary["counter_evidence_set_refs"]) == 1


def test_writeback_and_revision_preserves_temporal_and_uncertainty(tmp_path):
    """Test lower-level CognitionWritebackService and CognitionRevisionService field preservation."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    seed = ConversationIngestor(store)
    turn1 = seed.commit_turn(
        session_id="sess1",
        turn_index=1,
        user_text="测试事实1",
        assistant_text="回复1",
        occurred_at=NOW - timedelta(days=2),
    )
    turn2 = seed.commit_turn(
        session_id="sess2",
        turn_index=1,
        user_text="测试事实2（反例）",
        assistant_text="回复2",
        occurred_at=NOW - timedelta(days=1),
    )

    writer = CognitionWritebackService(
        store=store,
        subject_id="user_1",
        evidence_subject_ids=("user_1", AI_SELF_SUBJECT_ID),
    )
    valid_ext = TemporalExtent(
        start=NOW - timedelta(days=10),
        end=NOW,
        precision=TimePrecision.DAY,
    )
    write_receipt = writer.commit_claim(
        ClaimWriteRequest(
            content="初始测试结论",
            evidence_refs=(ObjectRef(object_id=turn1.user_observation_id, revision=1),),
            confidence=0.8,
            dimension="dim:test",
            valid_time=valid_ext,
            unknown_items=("未知项A", "未知项B"),
            counter_evidence_refs=(ObjectRef(object_id=turn2.user_observation_id, revision=1),),
        ),
        learned_at=NOW,
    )

    payload = store.get_payload(write_receipt.claim_id, revision=1)
    assert payload["valid_time"]["start"] is not None
    assert payload["valid_time"]["end"] is not None
    assert payload["unknown_items"] == ["未知项A", "未知项B"]
    assert len(payload["counter_evidence_set_refs"]) == 1

    # Revise without supplying valid_time or unknown_items: should preserve old claim's fields!
    revisor = CognitionRevisionService(
        store=store,
        subject_id="user_1",
        evidence_subject_ids=("user_1", AI_SELF_SUBJECT_ID),
    )
    rev_receipt = revisor.apply(
        ClaimRevisionRequest(
            target_ref=ObjectRef(object_id=write_receipt.claim_id, revision=1),
            mode="revise",
            reason="微调内容，保留时间和未知项",
            evidence_refs=(ObjectRef(object_id=turn1.user_observation_id, revision=1),),
            replacement_content="微调后的测试结论",
        ),
        changed_at=NOW + timedelta(hours=1),
    )

    payload_v2 = store.get_payload(write_receipt.claim_id, revision=rev_receipt.new_revision)
    assert payload_v2["content"] == "微调后的测试结论"
    # Preserved from v1!
    assert payload_v2["valid_time"]["start"] is not None
    assert payload_v2["valid_time"]["end"] is not None
    assert payload_v2["unknown_items"] == ["未知项A", "未知项B"]
    assert len(payload_v2["counter_evidence_set_refs"]) == 1
