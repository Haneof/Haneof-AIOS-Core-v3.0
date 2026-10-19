"""Comprehensive adversarial audit verification suite (Remediating DEF-001, DEF-002, DEF-003).

Directly validates fixes for external PM audit findings:
1. DEF-003: ActiveRollingWindow durable slide-out persistence & restart recovery
2. DEF-002: Closed-loop Bayesian communication adaptation on every turn
3. DEF-001: ToolProposalPipeline authorization enforcement & safety metadata
"""

from datetime import datetime, timedelta, timezone
import pytest

from aios_core.contracts.enums import ObjectType, SourceClass, UserReaction
from aios_core.contracts.models import ObjectRef
from aios_core.context.active_window import ActiveRollingWindow
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.tools.proposal_pipeline import ToolProposalPipeline, ToolProposalStatus


NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)


def test_overflow_turns_persist_across_restarts(tmp_path):
    """DEF-003: Overflow turns that slide out must be durably stored in SQLite and recovered on restart."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)

    # Initialize window with max 3 active turns
    session_id = "restart_test_session"
    window = ActiveRollingWindow(
        max_active_turns=3,
        max_token_budget=1500,
        session_id=session_id,
        store=store,
    )

    # Record 5 turns: turns 1 and 2 will slide out
    for i in range(1, 6):
        user_ref = ObjectRef(object_id=f"obs_user_{i}", revision=1)
        asst_ref = ObjectRef(object_id=f"obs_asst_{i}", revision=1)
        window.record_turn(
            turn_index=i,
            user_text=f"用户输入第 {i} 轮内容",
            user_observation_ref=user_ref,
            assistant_text=f"助手回复第 {i} 轮内容",
            assistant_observation_ref=asst_ref,
            occurred_at=NOW + timedelta(minutes=i),
        )

    assert len(window.active_turns) == 3
    assert len(window.pending_extract_turns) == 2
    assert [t.turn_index for t in window.pending_extract_turns] == [1, 2]

    # --- SIMULATE WEARABLE CRASH & RESTART ---
    restarted_window = ActiveRollingWindow(
        max_active_turns=3,
        max_token_budget=1500,
        session_id=session_id,
        store=store,
    )

    # Slid-out turns must be completely recovered from SQLite table active_window_overflow_staging
    assert len(restarted_window.pending_extract_turns) == 2
    recovered = restarted_window.pending_extract_turns
    assert recovered[0].turn_index == 1
    assert recovered[0].user_text == "用户输入第 1 轮内容"
    assert recovered[0].assistant_text == "助手回复第 1 轮内容"
    assert recovered[0].user_observation_ref.object_id == "obs_user_1"

    assert recovered[1].turn_index == 2
    assert recovered[1].user_text == "用户输入第 2 轮内容"
    assert recovered[1].assistant_text == "助手回复第 2 轮内容"

    # Acknowledge extraction and verify durable update
    acked = restarted_window.ack_extracted([1, 2])
    assert acked == 2
    assert len(restarted_window.pending_extract_turns) == 0

    # Verify that in a fresh reload after ack, nothing remains pending
    fresh_window = ActiveRollingWindow(
        max_active_turns=3,
        max_token_budget=1500,
        session_id=session_id,
        store=store,
    )
    assert len(fresh_window.pending_extract_turns) == 0


def test_communication_experience_updates_automatically_in_turns(tmp_path):
    """DEF-002: FusedTurnRuntime must automatically evaluate and record communication experiences across turns."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    turn_count = 0

    def model(snapshot):
        nonlocal turn_count
        turn_count += 1
        if turn_count == 1:
            return ModelDirective(response="今天杭州天气晴朗，气温22度。")
        elif turn_count == 2:
            return ModelDirective(response="收到，已切换为精简直言模式。")
        return ModelDirective(response="好的。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    session_id = "comm_test_session"

    # Turn 1: Normal friendly question -> triggers automatic ACCEPTED feedback
    res1 = runtime.run_turn(
        session_id=session_id,
        turn_index=1,
        user_input="今天天气怎么样？",
        occurred_at=NOW,
    )
    assert res1.runtime.termination_reason == "responded"

    stats_1 = runtime.experience_tracker.get_style_stats("daily_chat")
    assert len(stats_1) >= 1
    concise_stat = next((s for s in stats_1 if s.style == "concise"), None)
    assert concise_stat is not None
    assert concise_stat.accepted_count >= 1
    assert concise_stat.resisted_count == 0

    # Turn 2: User explicitly expresses resistance ("太啰嗦了，别废话，挑重点讲")
    res2 = runtime.run_turn(
        session_id=session_id,
        turn_index=2,
        user_input="太啰嗦了，别废话，挑重点讲！",
        occurred_at=NOW + timedelta(minutes=1),
    )
    assert res2.runtime.termination_reason == "responded"

    # Verify that RESISTED reaction was automatically recorded
    stats_2 = runtime.experience_tracker.get_style_stats("daily_chat")
    concise_stat_2 = next(s for s in stats_2 if s.style == "concise")
    assert concise_stat_2.resisted_count >= 1

    # Verify Bayesian effective style computation incorporates this resistance
    effective = runtime.experience_tracker.get_effective_style("daily_chat")
    assert effective.sample_count >= 2


def test_tool_proposal_authorization_and_safety_boundary(tmp_path):
    """DEF-001: ToolProposal execution must require explicit authorization and embed safety metadata."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    pipeline = ToolProposalPipeline(store=store, subject_id="user_1")

    # 1. Draft proposal
    draft = pipeline.draft_proposal(
        capability_gap="需要对心率波形进行自回归预测",
        use_cases=["提前5分钟预警心律失常"],
        current_limitations=["只有瞬时心率检测"],
        proposed_interface={"input": "heart_rate_array", "output": "arrhythmia_risk_score"},
        expected_benefit="提升P0急救预警窗口",
        validation_plan="用历史1000条早搏数据做F1评估",
        created_at=NOW,
    )
    prop_ref = ObjectRef(object_id=draft.proposal_id, revision=draft.revision)

    # 2. Cannot execute unapproved proposal
    with pytest.raises(ValueError, match="Cannot execute proposal in status draft; must be approved"):
        pipeline.execute_proposal(proposal_ref=prop_ref, executor="runtime_kernel")

    # 3. Submit proposal
    submitted = pipeline.submit_proposal(
        proposal_ref=prop_ref,
        submitted_by="ai_cognition",
        submitted_at=NOW + timedelta(minutes=2),
    )
    submitted_ref = ObjectRef(object_id=submitted.proposal_id, revision=submitted.revision)

    # 4. Review and approve proposal
    approved = pipeline.review_proposal(
        proposal_ref=submitted_ref,
        decision=ToolProposalStatus.APPROVED,
        reviewer="chief_architect",
        review_comments="架构合宪，准许在沙箱中接入",
        risk_level="MEDIUM",
        reviewed_at=NOW + timedelta(minutes=5),
    )
    approved_ref = ObjectRef(object_id=approved.proposal_id, revision=approved.revision)

    # 4. Unauthorized executor must be strictly rejected
    with pytest.raises(PermissionError, match="Unauthorized executor 'malicious_agent'"):
        pipeline.execute_proposal(
            proposal_ref=approved_ref,
            executor="malicious_agent",
        )

    # 5. Authorized executor succeeds and metadata explicitly clarifies safety boundary
    executed = pipeline.execute_proposal(
        proposal_ref=approved_ref,
        executor="runtime_kernel",
        execution_context={"mounted_capability": "predict_arrhythmia_risk"},
        executed_at=NOW + timedelta(minutes=10),
    )
    assert executed.status == ToolProposalStatus.EXECUTED

    # Inspect stored payload
    payload = store.get_payload(executed.proposal_id, revision=executed.revision)
    meta = payload["metadata"]
    assert meta["executor"] == "runtime_kernel"
    assert meta["execution_safety"] == "METADATA_RECORD_ONLY_NO_ARBITRARY_CODE_EXECUTION"
    assert meta["is_code_sandboxed"] is False
    assert meta["requires_formal_operator_release"] is True
