"""DimensionCurveTracker: Higher-order cognitive derivative engine and curve tracker.

Fulfills Constitution Chapter 7 Article 23:
- Tracks temporal trajectories of cognitive dimensions across day/week/month/quarter granularities.
- Atomically computes first derivative (velocity) and second derivative (acceleration).
- Strictly enforces Ch.7 Art.23: Derivatives are NEVER computed on raw sensor observations;
  only on high-order cognitive dimensions.
- Detects cognitive trajectory inflection points (peaks, troughs, acceleration flips) and burnout risks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import math
from typing import Sequence

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import DimensionCurvePoint, ObjectRef
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.storage.sqlite_store import SQLiteWorldStore


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256(
        "|".join(str(part) for part in parts).encode("utf-8")
    ).hexdigest()[:24]
    return f"{prefix}_{digest}"


@dataclass(frozen=True, slots=True)
class DimensionCurvePointReceipt:
    point_id: str
    revision: int
    dimension_id: str
    point_time: datetime
    value: float
    velocity: float | None
    acceleration: float | None
    anomaly_flag: bool
    world_revision: int


@dataclass(frozen=True, slots=True)
class InflectionEvent:
    dimension_id: str
    point_id: str
    point_time: datetime
    inflection_type: str  # "PEAK", "TROUGH", "ACCELERATION_FLIP"
    value: float
    velocity_before: float
    velocity_after: float
    description: str


class DimensionCurveTracker:
    """Tracks cognitive dimension curves and computes higher-order cognitive derivatives."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        subject_id: str = "user_1",
    ) -> None:
        self.store = store
        self.subject_id = subject_id

    def _validate_dimension_ref(self, ref: ObjectRef) -> dict:
        """Validate referenced dimension exists and adheres to Constitution Ch.7 Art.23."""
        if ref.revision is None or ref.revision < 1:
            raise ValueError("dimension_ref requires pinned ObjectRef revision >= 1")
        payload = self.store.get_payload(ref.object_id, revision=ref.revision)
        if str(payload.get("subject_id") or "") != self.subject_id:
            raise ValueError(f"{ref.object_id} crosses runtime subject scope")

        obj_type = str(payload.get("object_type") or "")
        # Constitution Chapter 7 Article 23: strictly forbid raw sensor data as derivative basis
        if obj_type in {
            ObjectType.OBSERVATION.value,
            "observation",
            "raw_sensor",
            "sensor_frame",
        }:
            raise ValueError(
                "Constitution Ch.7 Art.23 violation: derivatives strictly forbidden on raw sensor layer"
            )
        return payload

    def query_points(
        self,
        dimension_id: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        ascending: bool = True,
        limit: int = 500,
    ) -> list[DimensionCurvePoint]:
        """Query curve points for a given cognitive dimension."""
        payloads = self.store.list_payloads(
            object_type=ObjectType.DIMENSION_CURVE_POINT,
            subject_id=self.subject_id,
        )
        points: list[DimensionCurvePoint] = []
        for payload in payloads:
            dim_ref = payload.get("dimension_ref") or {}
            if str(dim_ref.get("object_id") or "") != dimension_id:
                continue
            if payload.get("deleted_at") is not None:
                continue
            point = DimensionCurvePoint.model_validate(payload)
            if start_time is not None and point.point_time < start_time:
                continue
            if end_time is not None and point.point_time > end_time:
                continue
            points.append(point)

        points.sort(key=lambda p: p.point_time, reverse=not ascending)
        return points[:limit]

    def record_point(
        self,
        *,
        dimension_ref: ObjectRef,
        point_time: datetime,
        value: float,
        confidence: float = 0.5,
        granularity: str = "day",
        source_summary_ref: ObjectRef | None = None,
        source_evidence_set_ref: ObjectRef | None = None,
        anomaly_flag: bool = False,
        anomaly_description: str | None = None,
        created_by: str = "ai_cognition",
        recorded_at: datetime | None = None,
    ) -> DimensionCurvePointReceipt:
        """Atomically record a cognitive curve point and calculate its velocity and acceleration."""
        pt = as_utc(point_time, "point_time")

        dim_payload = self._validate_dimension_ref(dimension_ref)

        if source_summary_ref is not None:
            if source_summary_ref.revision is None or source_summary_ref.revision < 1:
                raise ValueError("source_summary_ref requires pinned revision")
            self.store.get_payload(source_summary_ref.object_id, revision=source_summary_ref.revision)

        if source_evidence_set_ref is not None:
            if source_evidence_set_ref.revision is None or source_evidence_set_ref.revision < 1:
                raise ValueError("source_evidence_set_ref requires pinned revision")
            self.store.get_payload(source_evidence_set_ref.object_id, revision=source_evidence_set_ref.revision)

        # Historical points for calculating derivatives
        existing_points = self.query_points(dimension_ref.object_id, ascending=True)

        prev_point: DimensionCurvePoint | None = None
        for p in reversed(existing_points):
            if p.point_time < pt:
                prev_point = p
                break

        unit_seconds = 86400.0 if granularity == "day" else 3600.0 if granularity == "hour" else 1.0

        computed_velocity: float | None = None
        computed_acceleration: float | None = None

        if prev_point is not None:
            dt_seconds = (pt - prev_point.point_time).total_seconds()
            if dt_seconds > 0:
                dt_units = dt_seconds / unit_seconds
                computed_velocity = (float(value) - prev_point.value) / dt_units
                if prev_point.velocity is not None:
                    computed_acceleration = (computed_velocity - prev_point.velocity) / dt_units

        # Anomaly detection heuristic if not manually flagged
        final_anomaly_flag = anomaly_flag
        final_anomaly_desc = anomaly_description

        if not final_anomaly_flag and existing_points:
            values = [p.value for p in existing_points]
            mean_val = sum(values) / len(values)
            variance = sum((v - mean_val) ** 2 for v in values) / len(values)
            std_dev = math.sqrt(variance)
            if std_dev > 1e-4 and abs(float(value) - mean_val) > 3.0 * std_dev:
                final_anomaly_flag = True
                final_anomaly_desc = f"Value {value:.2f} deviates >3 sigma from historical mean {mean_val:.2f}"
            elif computed_velocity is not None and abs(computed_velocity) > 5.0:
                final_anomaly_flag = True
                final_anomaly_desc = f"Velocity magnitude {computed_velocity:.2f} exceeds rapid-change limit"

        if final_anomaly_flag and not (final_anomaly_desc or "").strip():
            final_anomaly_desc = "Cognitive derivative anomaly detected by tracker"

        # Invariant: learned_at >= dimension's learned_at for temporal cutoff check
        dim_learned_str = str(dim_payload.get("learned_at") or "")
        learned_dt = pt
        if dim_learned_str:
            try:
                dim_learned = datetime.fromisoformat(dim_learned_str.replace("Z", "+00:00"))
                if learned_dt < dim_learned:
                    learned_dt = dim_learned
            except Exception:
                pass

        if recorded_at is not None:
            rec = as_utc(recorded_at, "recorded_at")
            if rec < learned_dt:
                rec = learned_dt
        else:
            now_utc = datetime.now(timezone.utc)
            rec = max(pt, learned_dt, now_utc)

        point_id = _stable_id("dcp", dimension_ref.object_id, pt.isoformat(), granularity)

        curve_point = DimensionCurvePoint(
            object_id=point_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(pt),
            learned_at=learned_dt,
            recorded_at=rec,
            created_by=created_by,
            dimension_ref=dimension_ref,
            point_time=pt,
            value=float(value),
            velocity=computed_velocity,
            acceleration=computed_acceleration,
            confidence=confidence,
            source_summary_ref=source_summary_ref,
            source_evidence_set_ref=source_evidence_set_ref,
            anomaly_flag=final_anomaly_flag,
            anomaly_description=final_anomaly_desc,
            granularity=granularity,
        )

        expected_rev = self.store.current_world_revision()
        op = OperationRequest(
            operation_name="curves.record_point",
            expected_world_revision=expected_rev,
            reason=f"Record curve point for dimension {dimension_ref.object_id}",
            idempotency_key=f"record_point_{point_id}_{expected_rev}",
            source_class=SourceClass.AI_COGNITION,
        )
        commit_res = self.store.commit([curve_point], op)

        return DimensionCurvePointReceipt(
            point_id=point_id,
            revision=1,
            dimension_id=dimension_ref.object_id,
            point_time=pt,
            value=float(value),
            velocity=computed_velocity,
            acceleration=computed_acceleration,
            anomaly_flag=final_anomaly_flag,
            world_revision=commit_res.world_revision,
        )

    def detect_inflection_points(
        self,
        dimension_id: str,
        *,
        min_points: int = 3,
        curvature_threshold: float = 0.3,
    ) -> list[InflectionEvent]:
        """Detect trajectory inflection points (peaks, troughs, rapid acceleration flips)."""
        points = self.query_points(dimension_id, ascending=True)
        if len(points) < min_points:
            return []

        inflections: list[InflectionEvent] = []

        for i in range(1, len(points) - 1):
            p_prev = points[i - 1]
            p_curr = points[i]
            p_next = points[i + 1]

            if p_curr.velocity is None or p_next.velocity is None:
                continue

            v_prev = p_curr.velocity
            v_next = p_next.velocity

            # Peak: velocity was positive, becomes negative
            if v_prev > curvature_threshold and v_next < -curvature_threshold:
                inflections.append(
                    InflectionEvent(
                        dimension_id=dimension_id,
                        point_id=p_curr.object_id,
                        point_time=p_curr.point_time,
                        inflection_type="PEAK",
                        value=p_curr.value,
                        velocity_before=v_prev,
                        velocity_after=v_next,
                        description=f"Local peak reached at value {p_curr.value:.2f}; trajectory shifting downward",
                    )
                )
            # Trough: velocity was negative, becomes positive
            elif v_prev < -curvature_threshold and v_next > curvature_threshold:
                inflections.append(
                    InflectionEvent(
                        dimension_id=dimension_id,
                        point_id=p_curr.object_id,
                        point_time=p_curr.point_time,
                        inflection_type="TROUGH",
                        value=p_curr.value,
                        velocity_before=v_prev,
                        velocity_after=v_next,
                        description=f"Local trough reached at value {p_curr.value:.2f}; trajectory recovering upward",
                    )
                )
            # Acceleration flip: sudden large sign flip in acceleration
            elif (
                p_curr.acceleration is not None
                and p_next.acceleration is not None
                and (p_curr.acceleration * p_next.acceleration < 0)
                and abs(p_next.acceleration - p_curr.acceleration) > (curvature_threshold * 2.0)
            ):
                inflections.append(
                    InflectionEvent(
                        dimension_id=dimension_id,
                        point_id=p_curr.object_id,
                        point_time=p_curr.point_time,
                        inflection_type="ACCELERATION_FLIP",
                        value=p_curr.value,
                        velocity_before=v_prev,
                        velocity_after=v_next,
                        description=f"Acceleration flip observed (acc={p_curr.acceleration:.2f} -> {p_next.acceleration:.2f})",
                    )
                )

        return inflections

    def detect_burnout_risk(
        self,
        dimension_id: str,
        *,
        consecutive_declines: int = 3,
        velocity_threshold: float = -0.2,
    ) -> dict:
        """Evaluate cognitive health and energetic exhaustion (Burnout) risk."""
        points = self.query_points(dimension_id, ascending=True)
        if len(points) < consecutive_declines:
            return {
                "burnout_detected": False,
                "dimension_id": dimension_id,
                "severity": "LOW",
                "reason": "Insufficient points for burnout trend analysis",
                "consecutive_declines": 0,
            }

        recent = points[-consecutive_declines:]
        negative_count = 0
        steep_drop_count = 0

        for pt in recent:
            if pt.velocity is not None:
                if pt.velocity < 0:
                    negative_count += 1
                if pt.velocity <= velocity_threshold:
                    steep_drop_count += 1

        is_burnout = negative_count >= consecutive_declines
        if is_burnout:
            severity = "CRITICAL" if steep_drop_count >= (consecutive_declines - 1) else "HIGH"
            reason = (
                f"Cognitive dimension {dimension_id} exhibited {negative_count} consecutive declining periods "
                f"with steep negative velocity (threshold {velocity_threshold})"
            )
            suggested_action = "Trigger proactive stress-relief prompt and throttle proactive interruptions."
        else:
            severity = "LOW"
            reason = "Cognitive trajectory within normal resilience bounds"
            suggested_action = "Maintain regular monitoring schedule"

        return {
            "burnout_detected": is_burnout,
            "dimension_id": dimension_id,
            "severity": severity,
            "reason": reason,
            "consecutive_declines": negative_count,
            "suggested_action": suggested_action,
        }
