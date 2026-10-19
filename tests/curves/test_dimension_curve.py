from datetime import datetime, timedelta, timezone
import pytest

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import (
    DimensionDefinition,
    ObjectRef,
    Observation,
)
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.curves.dimension_curve import DimensionCurveTracker
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)


def _seed_dim(store: SQLiteWorldStore, dim_id: str = "dim_energy") -> DimensionDefinition:
    dim = DimensionDefinition(
        object_id=dim_id,
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test",
        name="精力与认知负荷",
        description="用户精力水平与负荷度量",
        data_shape="scalar",
    )
    op = OperationRequest(
        operation_name="test.seed_dim",
        expected_world_revision=0,
        reason="seed dimension for curve testing",
        idempotency_key=f"seed_{dim_id}",
        source_class=SourceClass.USER,
    )
    store.commit([dim], op)
    return dim


def test_record_single_and_sequential_curve_points(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    dim = _seed_dim(store)
    tracker = DimensionCurveTracker(store=store)

    dim_ref = ObjectRef(object_id=dim.object_id, revision=1)

    # Point 1: Day 0
    r1 = tracker.record_point(
        dimension_ref=dim_ref,
        point_time=NOW,
        value=10.0,
        granularity="day",
    )
    assert r1.value == 10.0
    assert r1.velocity is None
    assert r1.acceleration is None

    # Point 2: Day 1 (+2.0 in 1 day => velocity = 2.0)
    r2 = tracker.record_point(
        dimension_ref=dim_ref,
        point_time=NOW + timedelta(days=1),
        value=12.0,
        granularity="day",
    )
    assert r2.value == 12.0
    assert pytest.approx(r2.velocity, rel=1e-3) == 2.0
    assert r2.acceleration is None

    # Point 3: Day 2 (+3.0 in 1 day => velocity = 3.0, acceleration = 3.0 - 2.0 = 1.0)
    r3 = tracker.record_point(
        dimension_ref=dim_ref,
        point_time=NOW + timedelta(days=2),
        value=15.0,
        granularity="day",
    )
    assert r3.value == 15.0
    assert pytest.approx(r3.velocity, rel=1e-3) == 3.0
    assert pytest.approx(r3.acceleration, rel=1e-3) == 1.0

    points = tracker.query_points(dim.object_id, ascending=True)
    assert len(points) == 3
    assert points[0].value == 10.0
    assert points[1].value == 12.0
    assert points[2].value == 15.0


def test_constitution_ch7_art23_forbids_raw_sensor_derivatives(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    tracker = DimensionCurveTracker(store=store)

    # Seed a raw sensor observation
    obs = Observation(
        object_id="obs_heart_rate_raw",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="sensor_driver",
        source_kind="heart_rate_sensor",
        modality="ppg",
        value=78,
        unit="bpm",
    )
    op = OperationRequest(
        operation_name="test.seed_obs",
        expected_world_revision=0,
        reason="seed raw sensor observation",
        idempotency_key="seed_obs_1",
        source_class=SourceClass.SENSOR,
    )
    store.commit([obs], op)

    # Attempt to calculate cognitive derivatives on raw sensor observation
    obs_ref = ObjectRef(object_id=obs.object_id, revision=1)
    with pytest.raises(ValueError, match="Constitution Ch.7 Art.23 violation: derivatives strictly forbidden on raw sensor layer"):
        tracker.record_point(
            dimension_ref=obs_ref,
            point_time=NOW + timedelta(days=1),
            value=82.0,
        )


def test_detect_inflection_points(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    dim = _seed_dim(store, dim_id="dim_productivity")
    tracker = DimensionCurveTracker(store=store)
    dim_ref = ObjectRef(object_id=dim.object_id, revision=1)

    # Ascending then descending trajectory (creates a local PEAK)
    # Day 0: 5.0
    tracker.record_point(dimension_ref=dim_ref, point_time=NOW, value=5.0)
    # Day 1: 10.0 (vel = +5.0)
    tracker.record_point(dimension_ref=dim_ref, point_time=NOW + timedelta(days=1), value=10.0)
    # Day 2: 12.0 (vel = +2.0)
    tracker.record_point(dimension_ref=dim_ref, point_time=NOW + timedelta(days=2), value=12.0)
    # Day 3: 8.0 (vel = -4.0) -> switches from +2.0 to -4.0 => PEAK at Day 2
    tracker.record_point(dimension_ref=dim_ref, point_time=NOW + timedelta(days=3), value=8.0)
    # Day 4: 4.0 (vel = -4.0)
    tracker.record_point(dimension_ref=dim_ref, point_time=NOW + timedelta(days=4), value=4.0)

    inflections = tracker.detect_inflection_points(dim.object_id, curvature_threshold=0.5)
    assert len(inflections) >= 1
    peaks = [inf for inf in inflections if inf.inflection_type == "PEAK"]
    assert len(peaks) == 1
    assert peaks[0].value == 12.0
    assert "trajectory shifting downward" in peaks[0].description


def test_detect_burnout_risk(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    dim = _seed_dim(store, dim_id="dim_vitality")
    tracker = DimensionCurveTracker(store=store)
    dim_ref = ObjectRef(object_id=dim.object_id, revision=1)

    # 4 consecutive days of steep drop
    tracker.record_point(dimension_ref=dim_ref, point_time=NOW, value=100.0)
    tracker.record_point(dimension_ref=dim_ref, point_time=NOW + timedelta(days=1), value=80.0)
    tracker.record_point(dimension_ref=dim_ref, point_time=NOW + timedelta(days=2), value=60.0)
    tracker.record_point(dimension_ref=dim_ref, point_time=NOW + timedelta(days=3), value=35.0)

    burnout = tracker.detect_burnout_risk(dim.object_id, consecutive_declines=3, velocity_threshold=-5.0)
    assert burnout["burnout_detected"] is True
    assert burnout["severity"] in {"HIGH", "CRITICAL"}
    assert "consecutive declining periods" in burnout["reason"]
    assert "proactive" in burnout["suggested_action"]


def test_anomaly_detection_with_description_requirement(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    dim = _seed_dim(store, dim_id="dim_focus")
    tracker = DimensionCurveTracker(store=store)
    dim_ref = ObjectRef(object_id=dim.object_id, revision=1)

    # Anomaly flagged manually with description works
    r = tracker.record_point(
        dimension_ref=dim_ref,
        point_time=NOW,
        value=50.0,
        anomaly_flag=True,
        anomaly_description="Sudden drop due to severe migraine",
    )
    assert r.anomaly_flag is True

    # Pinned revision required on dimension_ref
    unpinned_ref = ObjectRef(object_id=dim.object_id)
    with pytest.raises(ValueError, match="dimension_ref requires pinned ObjectRef revision"):
        tracker.record_point(
            dimension_ref=unpinned_ref,
            point_time=NOW + timedelta(days=1),
            value=55.0,
        )
