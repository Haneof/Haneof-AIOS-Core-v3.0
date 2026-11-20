"""Regression tests for PM-WINDOW80-GAPS-G1G2-001.

G-1: ``narrative_segment`` / ``dimension_curve_point`` / ``tool_proposal``
text fields must be keyword-searchable through the world search index
(they were missing from the ``_TEXT_FIELDS`` whitelist, so their titles
and content only landed in an empty haystack).

G-2: a failure of the automatic per-turn experience write in
``FusedTurnRuntime._record_turn_experience`` must leave a trace (warning
log + failure counter) instead of vanishing in a bare ``except: pass``.
"""

from datetime import datetime, timezone
import logging

from aios_core.contracts.enums import (
    NarrativeSegmentStatus,
    SourceClass,
)
from aios_core.contracts.models import (
    DimensionCurvePoint,
    DimensionDefinition,
    NarrativeSegment,
    ObjectRef,
    ToolProposal,
)
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.tools.proposal_pipeline import ToolProposalStatus

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)


def _seed_g1_fixtures(store: SQLiteWorldStore):
    segment = NarrativeSegment(
        object_id="nsg_deep_space_probe",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        title="星河远航纪元",
        description="深空探测器研制阶段",
        segment_status=NarrativeSegmentStatus.SEALED,
    )
    dim = DimensionDefinition(
        object_id="dim_vitality",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        name="精力与身心负荷",
        description="用户生理疲劳度量",
        data_shape="scalar",
    )
    curve_pt = DimensionCurvePoint(
        object_id="dcp_vitality_drop",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        dimension_ref=ObjectRef(object_id=dim.object_id, revision=1),
        point_time=NOW,
        value=32.0,
        velocity=-6.5,
        acceleration=-1.2,
        anomaly_flag=True,
        anomaly_description="连续加班导致极度疲惫",
    )
    proposal = ToolProposal(
        object_id="tpr_auto_archive",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        status=ToolProposalStatus.DRAFT.value,
        capability_gap="缺少自动归档能力",
        use_cases=["过期对话自动归档"],
        current_limitations=["只能手动归档"],
        proposed_interface={"archive": {"turn_id": "string"}},
        expected_benefit="检索延迟降低",
        validation_plan="对照组验证归档效果",
    )
    op = OperationRequest(
        operation_name="test.seed_window80_gaps_g1",
        expected_world_revision=0,
        reason="seed fixtures for G-1 keyword search regression",
        idempotency_key="seed_window80_gaps_g1",
        source_class=SourceClass.USER,
    )
    store.commit([segment, dim, curve_pt, proposal], op)


def test_g1_keyword_search_finds_segment_curve_point_and_proposal(tmp_path):
    """G-1: the three Window80 product types are keyword-searchable."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    _seed_g1_fixtures(store)

    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    # NarrativeSegment: keyword from the title and from the description.
    page = index.co_search(["星河"])
    assert any(hit.object_id == "nsg_deep_space_probe" for hit in page.hits)
    page = index.co_search(["深空探测器"])
    assert any(hit.object_id == "nsg_deep_space_probe" for hit in page.hits)

    # DimensionCurvePoint: keyword from anomaly_description (its only text field).
    page = index.co_search(["疲惫"])
    assert any(hit.object_id == "dcp_vitality_drop" for hit in page.hits)

    # ToolProposal: keyword from capability_gap and from expected_benefit.
    page = index.co_search(["归档"])
    assert any(hit.object_id == "tpr_auto_archive" for hit in page.hits)
    page = index.co_search(["检索延迟"])
    assert any(hit.object_id == "tpr_auto_archive" for hit in page.hits)


class _FailingExperienceTracker:
    """Stand-in tracker whose write always fails (G-2 regression)."""

    def record_interaction_experience(self, **kwargs):
        raise RuntimeError("simulated experience write failure")


def test_g2_failed_experience_write_is_logged_and_counted(tmp_path, caplog):
    """G-2: a failed automatic experience write is observable, not swallowed."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    def model(snapshot):
        return ModelDirective(response="ok")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    assert runtime.experience_record_failures == 0

    runtime.experience_tracker = _FailingExperienceTracker()
    with caplog.at_level(logging.WARNING, logger="aios_core.runtime.turn_runtime"):
        # Must not raise: the turn itself still completes.
        runtime._record_turn_experience(
            user_input="好的",
            assistant_text="收到",
            user_obs_ref=ObjectRef(object_id="obs_test", revision=1),
            occurred_at=NOW,
        )

    assert runtime.experience_record_failures == 1
    assert "failed to record turn experience" in caplog.text
