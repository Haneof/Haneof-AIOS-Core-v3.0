from datetime import datetime, timedelta, timezone
import pytest

from aios_core.contracts.enums import (
    ClaimType,
    EventStatus,
    KnowledgeState,
    NarrativeSegmentStatus,
    ObjectType,
    SourceClass,
)
from aios_core.contracts.models import (
    Claim,
    DimensionDefinition,
    EventAnchor,
    ObjectRef,
)
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.narrative.segmenter import NarrativeSegmenter
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)


def _seed_fixtures(store: SQLiteWorldStore):
    dim = DimensionDefinition(
        object_id="dim_career",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        name="职场与事业发展",
        description="用户职业成长与项目经历",
        data_shape="text",
    )
    event1 = EventAnchor(
        object_id="evt_job_offer",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        title="收到新 Offer",
        interpretation="获得心仪岗位的录用意向",
        event_status=EventStatus.ACTIVE,
        confidence=0.95,
    )
    event2 = EventAnchor(
        object_id="evt_team_onboarding",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW + timedelta(days=5)),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        title="入职新团队",
        interpretation="完成新部门手续入职",
        event_status=EventStatus.ACTIVE,
        confidence=0.95,
    )
    claim = Claim(
        object_id="clm_skill_python",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        claimant_id="user_1",
        claim_type=ClaimType.FACT,
        content="精通 Python 核心架构",
        asserted_at=NOW,
        knowledge_state=KnowledgeState.REPORTED,
        confidence=0.9,
    )

    op = OperationRequest(
        operation_name="test.seed",
        expected_world_revision=0,
        reason="seed test fixtures",
        idempotency_key="seed-1",
        source_class=SourceClass.USER,
    )
    store.commit([dim, event1, event2, claim], op)
    return dim, event1, event2, claim


def test_open_narrative_segment(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    dim, event1, _, claim = _seed_fixtures(store)
    segmenter = NarrativeSegmenter(store=store)

    receipt = segmenter.open_segment(
        title="春季跳槽与入职期",
        description="记录从面试拿 offer 到顺利入职的完整阶段",
        dimension_refs=[ObjectRef(object_id=dim.object_id, revision=1)],
        key_event_refs=[ObjectRef(object_id=event1.object_id, revision=1)],
        key_claim_refs=[ObjectRef(object_id=claim.object_id, revision=1)],
        theme_tags=["跳槽", "职业转型"],
        coherence_score=0.6,
        created_at=NOW,
    )

    assert receipt.revision == 1
    assert receipt.status == NarrativeSegmentStatus.OPEN

    seg = segmenter.get_segment(receipt.segment_id)
    assert seg.title == "春季跳槽与入职期"
    assert seg.segment_status == NarrativeSegmentStatus.OPEN
    assert len(seg.key_event_refs) == 1
    assert len(seg.key_claim_refs) == 1


def test_attach_event_and_claim_forward_revisions(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    dim, event1, event2, claim = _seed_fixtures(store)
    segmenter = NarrativeSegmenter(store=store)

    r1 = segmenter.open_segment(
        title="职业转折纪元",
        dimension_refs=[ObjectRef(object_id=dim.object_id, revision=1)],
        created_at=NOW,
    )

    # Attach event2
    r2 = segmenter.attach_event(
        segment_ref=ObjectRef(object_id=r1.segment_id, revision=r1.revision),
        event_ref=ObjectRef(object_id=event2.object_id, revision=1),
        attached_at=NOW + timedelta(hours=1),
    )
    assert r2.revision == 2
    assert r2.status == NarrativeSegmentStatus.OPEN

    # Idempotent re-attachment
    r2_dup = segmenter.attach_event(
        segment_ref=ObjectRef(object_id=r2.segment_id, revision=r2.revision),
        event_ref=ObjectRef(object_id=event2.object_id, revision=1),
        attached_at=NOW + timedelta(hours=2),
    )
    assert r2_dup.revision == 2

    # Attach claim
    r3 = segmenter.attach_claim(
        segment_ref=ObjectRef(object_id=r2.segment_id, revision=r2.revision),
        claim_ref=ObjectRef(object_id=claim.object_id, revision=1),
        attached_at=NOW + timedelta(hours=3),
    )
    assert r3.revision == 3

    seg = segmenter.get_segment(r1.segment_id)
    assert len(seg.key_event_refs) == 1
    assert len(seg.key_claim_refs) == 1
    assert seg.supersedes_ref == ObjectRef(object_id=r1.segment_id, revision=2)


def test_seal_segment_lifecycle(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    dim, event1, event2, _ = _seed_fixtures(store)
    segmenter = NarrativeSegmenter(store=store)

    r1 = segmenter.open_segment(
        title="试用期历程",
        dimension_refs=[ObjectRef(object_id=dim.object_id, revision=1)],
        key_event_refs=[ObjectRef(object_id=event1.object_id, revision=1)],
        created_at=NOW,
    )

    # Seal the segment
    r_sealed = segmenter.seal_segment(
        segment_ref=ObjectRef(object_id=r1.segment_id, revision=r1.revision),
        reason="试用期结束，全票转正",
        sealed_at=NOW + timedelta(days=90),
    )
    assert r_sealed.revision == 2
    assert r_sealed.status == NarrativeSegmentStatus.SEALED

    # Cannot attach to sealed segment
    with pytest.raises(ValueError, match="cannot attach event to NarrativeSegment in status sealed"):
        segmenter.attach_event(
            segment_ref=ObjectRef(object_id=r_sealed.segment_id, revision=r_sealed.revision),
            event_ref=ObjectRef(object_id=event2.object_id, revision=1),
        )


def test_merge_segments(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    dim, event1, event2, _ = _seed_fixtures(store)
    segmenter = NarrativeSegmenter(store=store)

    s1 = segmenter.open_segment(
        title="投简历与初试阶段",
        dimension_refs=[ObjectRef(object_id=dim.object_id, revision=1)],
        key_event_refs=[ObjectRef(object_id=event1.object_id, revision=1)],
        theme_tags=["求职", "面试"],
        created_at=NOW,
    )
    s2 = segmenter.open_segment(
        title="终面与薪酬洽谈阶段",
        dimension_refs=[ObjectRef(object_id=dim.object_id, revision=1)],
        key_event_refs=[ObjectRef(object_id=event2.object_id, revision=1)],
        theme_tags=["求职", "Offer"],
        created_at=NOW + timedelta(days=10),
    )

    r_merged = segmenter.merge_segments(
        source_segment_refs=[
            ObjectRef(object_id=s1.segment_id, revision=s1.revision),
            ObjectRef(object_id=s2.segment_id, revision=s2.revision),
        ],
        target_title="2026 春季整体求职战役",
        target_description="合并两段细分子阶段为宏观求职篇章",
        merged_at=NOW + timedelta(days=15),
    )

    assert r_merged.status == NarrativeSegmentStatus.OPEN
    target = segmenter.get_segment(r_merged.segment_id)
    assert target.title == "2026 春季整体求职战役"
    assert len(target.key_event_refs) == 2
    assert "面试" in target.theme_tags
    assert "Offer" in target.theme_tags

    # Old segments forward-revised to MERGED
    old1 = segmenter.get_segment(s1.segment_id)
    assert old1.segment_status == NarrativeSegmentStatus.MERGED
    assert old1.merged_into_ref == ObjectRef(object_id=r_merged.segment_id, revision=1)

    old2 = segmenter.get_segment(s2.segment_id)
    assert old2.segment_status == NarrativeSegmentStatus.MERGED
    assert old2.merged_into_ref == ObjectRef(object_id=r_merged.segment_id, revision=1)


def test_suggest_segment_closure(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    dim, _, _, _ = _seed_fixtures(store)
    segmenter = NarrativeSegmenter(store=store)

    extent = TemporalExtent(start=NOW, end=NOW + timedelta(days=40))
    s = segmenter.open_segment(
        title="超期长项目",
        segment_time=extent,
        dimension_refs=[ObjectRef(object_id=dim.object_id, revision=1)],
        created_at=NOW,
    )

    should_close, reason = segmenter.suggest_segment_closure(s.segment_id, max_time_span_days=30)
    assert should_close is True
    assert "exceeded closure threshold" in reason
