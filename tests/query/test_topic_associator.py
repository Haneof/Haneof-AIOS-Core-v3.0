from datetime import datetime, timezone
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
    DimensionCurvePoint,
    DimensionDefinition,
    EventAnchor,
    NarrativeSegment,
    ObjectRef,
)
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.query.topic_associator import DynamicTopicAssociator
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)


def _seed_fixtures(store: SQLiteWorldStore):
    event = EventAnchor(
        object_id="evt_hangzhou_startup",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        title="杭州西湖创业研讨",
        interpretation="与合伙人探讨AI手环原型方案",
        event_status=EventStatus.ACTIVE,
        confidence=0.95,
    )
    segment = NarrativeSegment(
        object_id="nsg_early_startup",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        title="初创启航纪元",
        description="2023至2024早期软硬件探索阶段",
        segment_status=NarrativeSegmentStatus.SEALED,
        theme_tags=["创业", "杭州", "硬件"],
        key_event_refs=[ObjectRef(object_id=event.object_id, revision=1)],
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
        anomaly_description="连续3天极度疲惫，身心处于崩溃边缘",
    )
    claim = Claim(
        object_id="clm_philosophy",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        claimant_id="user_1",
        claim_type=ClaimType.PREFERENCE,
        content="崇尚技术共生与极简主义生活哲学",
        asserted_at=NOW,
        knowledge_state=KnowledgeState.REPORTED,
        confidence=0.9,
    )

    op = OperationRequest(
        operation_name="test.seed_topic_fixtures",
        expected_world_revision=0,
        reason="seed fixtures for topic associator",
        idempotency_key="seed_topic_1",
        source_class=SourceClass.USER,
    )
    store.commit([event, segment, dim, curve_pt, claim], op)


def test_associate_past_unpredictable_event(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    _seed_fixtures(store)

    associator = DynamicTopicAssociator(store=store)

    # Spontaneous unpredictable topic about past events
    card = associator.associate_topic("你还记得当年在杭州聊的那个创业项目吗？")

    assert "创业" in card.detected_keywords or "杭州" in card.detected_keywords
    assert len(card.matched_segments) >= 1
    assert card.matched_segments[0]["title"] == "初创启航纪元"

    assert len(card.matched_events) >= 1
    assert card.matched_events[0]["title"] == "杭州西湖创业研讨"

    assert "初创启航纪元" in card.context_text
    assert "杭州西湖创业研讨" in card.context_text
    assert card.duration_ms < 50.0  # Ultra-fast execution


def test_associate_cognitive_stress_topic(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    _seed_fixtures(store)

    associator = DynamicTopicAssociator(store=store)

    # Spontaneous physiological complaint
    card = associator.associate_topic("最近工作好多，身体感觉特别疲惫，压力很大")

    assert len(card.cognitive_trends) >= 1
    assert card.cognitive_trends[0]["anomaly_flag"] is True
    assert "崩溃边缘" in card.cognitive_trends[0]["anomaly_description"]
    assert "身心处于崩溃边缘" in card.context_text


def test_token_budget_bound(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    _seed_fixtures(store)

    associator = DynamicTopicAssociator(store=store)

    # Bounded budget of 20 tokens
    card = associator.associate_topic(
        "当年在杭州聊的创业项目，还有我的极简主义生活哲学",
        max_tokens=20,
    )
    assert card.estimated_tokens <= 25
    assert "... (已依据Token预算上限紧凑裁剪)" in card.context_text
