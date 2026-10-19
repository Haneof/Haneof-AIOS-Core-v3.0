from datetime import datetime, timezone
import pytest

from aios_core.contracts.models import ObjectRef
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.tools.proposal_pipeline import (
    ToolProposalPipeline,
    ToolProposalStatus,
)

NOW = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)


def test_draft_and_submit_tool_proposal(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    pipeline = ToolProposalPipeline(store=store)

    draft = pipeline.draft_proposal(
        capability_gap="需要支持跨周期的情绪衰减模式识别",
        use_cases=["每日复盘反思", "长周期心理健康看板预警"],
        current_limitations=["仅支持单日离散情绪点记录，缺乏衰减半衰期模型"],
        proposed_interface={
            "tool_name": "compute_emotion_decay",
            "parameters": {"half_life_days": 7.0, "decay_function": "exponential"},
        },
        expected_benefit="提升情绪预警准确率 40%",
        validation_plan="通过历史 30 天情绪样本回测验证衰减曲线拟合度",
        created_at=NOW,
    )

    assert draft.revision == 1
    assert draft.status == ToolProposalStatus.DRAFT
    assert "情绪衰减" in draft.capability_gap

    # Proposal exists in store
    p = pipeline.get_proposal(draft.proposal_id)
    assert p.revision == 1
    assert pipeline.get_proposal_status(draft.proposal_id) == ToolProposalStatus.DRAFT

    # Advance to SUBMITTED
    submitted = pipeline.submit_proposal(
        proposal_ref=ObjectRef(object_id=draft.proposal_id, revision=1),
        submitted_by="ai_cognition_engine",
        submitted_at=NOW,
    )
    assert submitted.revision == 2
    assert submitted.status == ToolProposalStatus.SUBMITTED

    # Check forward revision
    p_sub = pipeline.get_proposal(draft.proposal_id)
    assert p_sub.revision == 2
    assert p_sub.source_refs[0].revision == 1
    assert p_sub.metadata["supersedes_revision"] == 1
    assert pipeline.get_proposal_status(draft.proposal_id) == ToolProposalStatus.SUBMITTED


def test_review_approved_and_execute_lifecycle(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    pipeline = ToolProposalPipeline(store=store)

    draft = pipeline.draft_proposal(
        capability_gap="动态心率变异性(HRV)实时频谱分析缺失",
        use_cases=["深度冥想引导", "极端疲劳防御"],
        current_limitations=["底层驱动仅上报原始 SDNN 指标"],
        proposed_interface={"tool_name": "hrv_spectral_analyzer"},
        expected_benefit="提供高频(HF)与低频(LF)自律神经平衡指标",
        validation_plan="对比医用级心电传感器基准数据",
        created_at=NOW,
    )

    # Submit
    sub = pipeline.submit_proposal(
        proposal_ref=ObjectRef(object_id=draft.proposal_id, revision=draft.revision),
        submitted_at=NOW,
    )

    # Review -> APPROVED
    app = pipeline.review_proposal(
        proposal_ref=ObjectRef(object_id=sub.proposal_id, revision=sub.revision),
        decision=ToolProposalStatus.APPROVED,
        reviewer="chief_architect",
        review_comments="符合端侧 50ms 实时调度要求，计算负荷评估通过",
        reviewed_at=NOW,
    )
    assert app.revision == 3
    assert app.status == ToolProposalStatus.APPROVED

    # Execute
    exc = pipeline.execute_proposal(
        proposal_ref=ObjectRef(object_id=app.proposal_id, revision=app.revision),
        executor="runtime_kernel",
        execution_context={"mounted_version": "v1.0.0"},
        executed_at=NOW,
    )
    assert exc.revision == 4
    assert exc.status == ToolProposalStatus.EXECUTED

    # Retire
    ret = pipeline.retire_proposal(
        proposal_ref=ObjectRef(object_id=exc.proposal_id, revision=exc.revision),
        reason="已由更高级的多导联心电算法取代",
        retired_at=NOW,
    )
    assert ret.revision == 5
    assert ret.status == ToolProposalStatus.RETIRED

    final_p = pipeline.get_proposal(draft.proposal_id)
    assert final_p.revision == 5
    assert pipeline.get_proposal_status(draft.proposal_id) == ToolProposalStatus.RETIRED


def test_review_rejected_and_invalid_transition(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    pipeline = ToolProposalPipeline(store=store)

    draft = pipeline.draft_proposal(
        capability_gap="高危测试提案",
        use_cases=["测试危险越权操作"],
        current_limitations=["受安全沙箱约束"],
        proposed_interface={"tool_name": "raw_shell_exec"},
        expected_benefit="无限制控制端侧系统",
        validation_plan="手动测试",
        created_at=NOW,
    )

    # DRAFT cannot execute directly
    with pytest.raises(ValueError, match="Cannot execute proposal in status draft; must be approved"):
        pipeline.execute_proposal(
            proposal_ref=ObjectRef(object_id=draft.proposal_id, revision=draft.revision),
        )

    # Submit
    sub = pipeline.submit_proposal(
        proposal_ref=ObjectRef(object_id=draft.proposal_id, revision=draft.revision),
        submitted_at=NOW,
    )

    # Reject
    rej = pipeline.review_proposal(
        proposal_ref=ObjectRef(object_id=sub.proposal_id, revision=sub.revision),
        decision=ToolProposalStatus.REJECTED,
        reviewer="safety_guard",
        review_comments="严禁任何非沙箱化原始终端执行，违背宪法安全铁律",
        reviewed_at=NOW,
    )
    assert rej.status == ToolProposalStatus.REJECTED

    # Rejected cannot execute
    with pytest.raises(ValueError, match="Cannot execute proposal in status rejected; must be approved"):
        pipeline.execute_proposal(
            proposal_ref=ObjectRef(object_id=rej.proposal_id, revision=rej.revision),
        )


def test_native_strategy_propose_index_acceleration_tool(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    pipeline = ToolProposalPipeline(store=store)

    # Under threshold -> raises ValueError
    with pytest.raises(ValueError, match="Observed latency 45.0ms does not exceed threshold"):
        pipeline.propose_index_acceleration_tool(
            observed_latency_ms=45.0,
            latency_threshold_ms=100.0,
        )

    # Above threshold -> automatically drafted and submitted
    receipt = pipeline.propose_index_acceleration_tool(
        observed_latency_ms=280.5,
        latency_threshold_ms=100.0,
        target_index="world_search_index",
        created_at=NOW,
    )
    assert receipt.status == ToolProposalStatus.SUBMITTED
    assert receipt.revision == 2

    p = pipeline.get_proposal(receipt.proposal_id)
    assert "280.5ms" in p.capability_gap
    assert p.proposed_interface["action"] == "CREATE_COMPOSITE_INDEX"
    assert "object_type" in p.proposed_interface["index_columns"]
