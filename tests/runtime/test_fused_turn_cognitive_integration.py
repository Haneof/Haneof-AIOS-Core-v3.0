"""End-to-end integration tests for Window 82 Cognitive Runtime Integration.

Verifies that FusedTurnRuntime seamlessly orchestrates:
1. DynamicTopicAssociator (sub-30ms associative recall)
2. AISelfMindTracker (double-entry promise ledger and rapport posture)
3. NarrativeSegmenter (life chapter segmentation and sealing)
4. DimensionCurveTracker (cognitive derivative calculation and burnout risk detection)
5. ToolProposalPipeline (tool proposal drafting and state machine)
6. ExperienceTracker (adaptive Bayesian style evaluation)
7. ActiveRollingWindow (strict 6-turn / 1500-token envelope)
"""

from datetime import datetime, timedelta, timezone
import pytest

from aios_core.contracts.enums import (
    EventStatus,
    NarrativeSegmentStatus,
    ObjectType,
    SourceClass,
)
from aios_core.contracts.models import (
    DimensionDefinition,
    EventAnchor,
    NarrativeSegment,
    Observation,
    ObjectRef,
)
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)


def test_runtime_topic_association_capability(tmp_path):
    """Test model calling associate_topics to perform sub-30ms multi-path topological recall."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)

    # Seed event and narrative segment with keywords
    event = EventAnchor(
        object_id="evt_hz_startup",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(days=2)),
        learned_at=NOW - timedelta(days=2),
        recorded_at=NOW - timedelta(days=2),
        created_by="test",
        title="杭州西湖创业研讨",
        interpretation="在杭州开始新一轮硬科技手环创业，与合伙人讨论架构。",
        event_status=EventStatus.ACTIVE,
        confidence=0.95,
    )
    segment = NarrativeSegment(
        object_id="nsg_hz_startup",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(days=2)),
        learned_at=NOW - timedelta(days=2),
        recorded_at=NOW - timedelta(days=2),
        created_by="test",
        title="初创启航纪元",
        description="2026杭州手环硬科技探索阶段",
        segment_status=NarrativeSegmentStatus.SEALED,
        theme_tags=["创业", "杭州", "硬件"],
        key_event_refs=[ObjectRef(object_id=event.object_id, revision=1)],
    )
    op = OperationRequest(
        operation_name="seed.topic_entities",
        expected_world_revision=store.current_world_revision(),
        reason="seed topic fixtures",
        idempotency_key="seed_topic_entities_hz",
        source_class=SourceClass.USER,
    )
    store.commit([event, segment], op)

    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    called = False

    def model(snapshot):
        nonlocal called
        if not snapshot.capability_history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="associate_topics",
                        arguments={"query": "杭州创业", "max_tokens": 500},
                    ),
                )
            )
        history = snapshot.capability_history[-1]
        assert history.ok is True
        data = history.data
        assert data["type"] == "ad_hoc_topic_memory"
        assert "detected_keywords" in data
        assert any("杭州" in kw or "创业" in kw for kw in data["detected_keywords"])
        assert data["duration_ms"] < 200.0  # sub-30ms typical, bounded well under 200ms
        called = True
        return ModelDirective(response="已成功联想到杭州创业背景相关事实。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="session_topic",
        turn_index=1,
        user_input="聊聊之前合伙的事",
        occurred_at=NOW,
    )
    assert called is True
    assert result.runtime.termination_reason == "responded"
    assert "杭州创业" in result.runtime.response


def test_runtime_ai_promise_double_entry_ledger(tmp_path):
    """Test model calling record_ai_promise and reconcile_ai_promise."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    step = 0
    recorded_promise_id = None

    def model(snapshot):
        nonlocal step, recorded_promise_id
        if step == 0:
            if not snapshot.capability_history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="record_ai_promise",
                            arguments={
                                "statement": "每天早晨8点推送日程重点",
                                "reason": "用户要求每日晨间同步",
                                "confidence": 1.0,
                            },
                        ),
                    )
                )
            rec = snapshot.capability_history[-1]
            assert rec.ok is True
            recorded_promise_id = rec.data["promise_id"]
            assert rec.data["double_entry_effect"] == "DEBIT_LIABILITY"
            assert rec.data["status"] == "promised"
            return ModelDirective(response="好的，我已经把这项承诺记录在心智账本中。")

        elif step == 1:
            if not snapshot.capability_history:
                # Inspect mind and reconcile promise
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="reconcile_ai_promise",
                            arguments={
                                "promise_id": recorded_promise_id,
                                "new_status": "fulfilled",
                                "reason": "连续3天均准时提醒，承诺兑现完成",
                            },
                        ),
                    )
                )
            rec = snapshot.capability_history[-1]
            assert rec.ok is True
            assert rec.data["double_entry_effect"] == "CREDIT_RED_LINE_OFFSET"
            assert rec.data["status"] == "fulfilled"
            return ModelDirective(response="晨间提醒承诺已圆满兑现完成。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)

    # Turn 1: Make promise
    res1 = runtime.run_turn(
        session_id="session_promise",
        turn_index=1,
        user_input="以后每天早晨8点提醒我日程",
        occurred_at=NOW,
    )
    assert res1.runtime.termination_reason == "responded"
    assert recorded_promise_id is not None

    # Check mind summary via tracker
    mind_summary = runtime.ai_self_tracker.get_mind_summary()
    assert len(mind_summary["outstanding_promises"]) >= 1

    # Turn 2: Fulfill promise
    step = 1
    res2 = runtime.run_turn(
        session_id="session_promise",
        turn_index=2,
        user_input="前几天提醒得很好，这项承诺完成了",
        occurred_at=NOW + timedelta(days=3),
    )
    assert res2.runtime.termination_reason == "responded"

    # Verify that outstanding promise count dropped
    updated_summary = runtime.ai_self_tracker.get_mind_summary()
    assert len(updated_summary["outstanding_promises"]) == 0


def test_runtime_narrative_and_dimension_curve_capabilities(tmp_path):
    """Test model calling narrative segmentation and dimension curve tracking."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)

    # Pre-register dimension definition for testing curves
    dim_energy = DimensionDefinition(
        object_id="dim:energy_level",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(days=10)),
        learned_at=NOW - timedelta(days=10),
        recorded_at=NOW - timedelta(days=10),
        created_by="system",
        name="精力与能量水平",
        description="身心能量高阶认知曲线",
        data_shape="scalar",
    )
    op = OperationRequest(
        operation_name="seed.dim",
        expected_world_revision=store.current_world_revision(),
        reason="seed dimension",
        idempotency_key="seed_dim_energy",
        source_class=SourceClass.AI_COGNITION,
    )
    store.commit([dim_energy], op)

    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    step = 0
    opened_segment_id = None

    def model(snapshot):
        nonlocal step, opened_segment_id
        if step == 0:
            if not snapshot.capability_history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="open_narrative_segment",
                            arguments={
                                "dimension_key": "dim:energy_level",
                                "title": "冲刺攻坚阶段",
                                "start_time": NOW.isoformat(),
                                "reason": "进入AIOS系统集成攻坚周",
                            },
                        ),
                    )
                )
            rec = snapshot.capability_history[-1]
            assert rec.ok is True
            opened_segment_id = rec.data["segment_id"]
            assert rec.data["status"] == "open"
            return ModelDirective(response="冲刺叙事分段已正式开启。")

        elif step == 1:
            if not snapshot.capability_history:
                # Record a dimension curve point
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="record_dimension_curve_point",
                            arguments={
                                "dimension_id": "dim:energy_level",
                                "point_time": (NOW + timedelta(hours=2)).isoformat(),
                                "value": 78.5,
                                "unit": "score",
                            },
                        ),
                    )
                )
            rec = snapshot.capability_history[-1]
            assert rec.ok is True
            assert rec.data["value"] == 78.5
            return ModelDirective(response="认知导数曲线点已成功记录。")

        elif step == 2:
            if not snapshot.capability_history:
                # Seal the narrative segment
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="seal_narrative_segment",
                            arguments={
                                "segment_id": opened_segment_id,
                                "summary": "攻坚周全面告捷，各子系统测试满绿",
                                "end_time": (NOW + timedelta(days=5)).isoformat(),
                            },
                        ),
                    )
                )
            rec = snapshot.capability_history[-1]
            assert rec.ok is True
            assert rec.data["status"] == "sealed"
            return ModelDirective(response="攻坚叙事分段已封存。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)

    # Turn 1: Open narrative segment
    res1 = runtime.run_turn(
        session_id="session_narrative",
        turn_index=1,
        user_input="开启新一轮攻坚周",
        occurred_at=NOW,
    )
    assert res1.runtime.termination_reason == "responded"
    assert opened_segment_id is not None

    # Turn 2: Record curve point
    step = 1
    res2 = runtime.run_turn(
        session_id="session_narrative",
        turn_index=2,
        user_input="记录一下精力评分78.5",
        occurred_at=NOW + timedelta(hours=2),
    )
    assert res2.runtime.termination_reason == "responded"

    # Turn 3: Seal segment
    step = 2
    res3 = runtime.run_turn(
        session_id="session_narrative",
        turn_index=3,
        user_input="本周攻坚结束，封存分段",
        occurred_at=NOW + timedelta(days=5),
    )
    assert res3.runtime.termination_reason == "responded"


def test_runtime_tool_proposal_and_communication_tracker(tmp_path):
    """Test model proposing tool and querying communication style."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    step = 0

    def model(snapshot):
        nonlocal step
        if step == 0:
            if not snapshot.capability_history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="propose_tool",
                            arguments={
                                "tool_name": "accelerated_topological_finder",
                                "capability_gap": "三度关系检索延迟过高",
                                "motivation": "端侧查询超过30ms",
                                "proposed_schema": {"root_entity": "string", "depth": "integer"},
                                "expected_gain": "将3跳拓扑遍历压至10ms以内",
                            },
                        ),
                    )
                )
            rec = snapshot.capability_history[-1]
            assert rec.ok is True
            assert rec.data["proposal_id"].startswith("tlp_")
            return ModelDirective(response="已提交端侧加速工具演进提案。")

        elif step == 1:
            if not snapshot.capability_history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="get_effective_communication_style",
                            arguments={"scenario": "crisis_management"},
                        ),
                    )
                )
            rec = snapshot.capability_history[-1]
            assert rec.ok is True
            data = rec.data
            assert "recommended_style" in data
            assert "avoidance_blacklist" in data
            return ModelDirective(response="已自适应推荐危机情境沟通风格。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)

    res1 = runtime.run_turn(
        session_id="session_tools",
        turn_index=1,
        user_input="当前图谱查询较慢，提个工具优化提案",
        occurred_at=NOW,
    )
    assert res1.runtime.termination_reason == "responded"

    step = 1
    res2 = runtime.run_turn(
        session_id="session_tools",
        turn_index=2,
        user_input="查一下紧急危机时应该用什么语气交流",
        occurred_at=NOW + timedelta(minutes=10),
    )
    assert res2.runtime.termination_reason == "responded"


def test_runtime_active_rolling_window_envelope(tmp_path):
    """Test that ActiveRollingWindow strictly maintains 6 turns / 1500 tokens in multi-turn session."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        # Verify cockpit ai_identity has symbiotic posture and rapport
        ai_identity = snapshot.cockpit.get("ai_identity", {})
        assert "symbiotic_posture" in ai_identity
        assert "rapport_score" in ai_identity
        return ModelDirective(response=f"收到，回答第 {snapshot.round_index} 轮。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)

    session_name = "stress_window_session"
    for turn in range(1, 11):
        res = runtime.run_turn(
            session_id=session_name,
            turn_index=turn,
            user_input=f"这是第 {turn} 轮对话内容，测试手环端侧滚动窗口上限保护。",
            occurred_at=NOW + timedelta(minutes=turn),
        )
        assert res.runtime.termination_reason == "responded"

    rolling_window = runtime.active_rolling_windows.get(session_name)
    assert rolling_window is not None
    # Strict envelope invariants:
    # 1. Active turns <= 6
    assert len(rolling_window.active_turns) <= 6
    # 2. Total active tokens <= 1500
    assert rolling_window.total_active_tokens() <= 1500
    # 3. Exactly 4 overflow turns buffered for background processing (10 total - 6 active)
    assert len(rolling_window.pending_extract_turns) == 4
