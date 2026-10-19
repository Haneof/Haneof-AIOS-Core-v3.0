"""Wearable hardware sensor streaming pipeline for AIOS 3.0.

Constitutional Mandates:
1. Article 33.1: IMU strictly prohibited from dumping 50Hz raw points to database.
   Must use adaptive deadband compression (AdaptiveTemporalCompressor) to extract
   macro motion states (STATIC, SLEEP, WALK, RUN, VEHICLE, UNKNOWN).
2. Heart rate (PPG): Stable periods stored strictly as episode means;
   arrhythmia / sudden surges escalated to high-priority anomaly observations.
3. Fall detection: Dual-condition impact surge (magnitude + relative jump)
   escalated to WakePriority.P0_CRITICAL_SAFETY with sub-50ms bypass trigger.
4. Iron Rule 4 & Article 33.5: No raw binary bloat on edge. Substandard photos
   (<0.4 quality) and ambient audio noise physically purged (RawByteSink);
   only semantic Captions and structured features are persisted.
5. Voiceprint LSH (128-dim) with 180-day TTL tombstone state machine.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from aios_core.contracts.enums import ObjectType, WakePriority
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent, utc_now
from aios_core.ingest.multimodal_edge import (
    EdgeMultimodalCleaner,
    FEATURE_DIM,
    QualityGate,
    RawByteSink,
    VoiceprintLSHIndex,
    VoiceprintProfile,
    VoiceprintTTLRegistry,
    assess_image_quality,
)
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.tools.adaptive_temporal_compressor import (
    AdaptiveScalarCompressor,
    AdaptiveTemporalCompressor,
    ImpactWaveform,
    MacroMotionState,
)


@dataclass(frozen=True, slots=True)
class SensorIngestSummary:
    """Audit summary for a wearable sensor stream ingestion batch."""

    raw_samples_count: int
    compressed_observations_count: int
    compression_ratio: float
    p0_critical_alert: bool
    purged_bytes_count: int
    alerts: tuple[str, ...] = ()


class WearableSensorPipeline:
    """Stream purifier and fact synthesizer for 23cm wearable band hardware sensors."""

    def __init__(
        self,
        world_store: SQLiteWorldStore,
        *,
        subject_id: str = "user_default",
        imu_epsilon: float = 2.0,
        imu_curvature_budget: float = 4.0,
        voiceprint_ttl_days: int = 180,
    ) -> None:
        self._store = world_store
        self._subject_id = subject_id
        self._imu_compressor = AdaptiveTemporalCompressor(
            epsilon=imu_epsilon,
            curvature_budget=imu_curvature_budget,
            impact_magnitude=3.0,
            impact_jump=10.0,
        )
        self._hr_compressor = AdaptiveScalarCompressor(
            tolerance=4.0,
            spike_delta=30.0,
            min_episode_span_s=10.0,
            sample_interval_s=1.0,
        )
        self._byte_sink = RawByteSink()
        self._voiceprint_registry = VoiceprintTTLRegistry(ttl_days=voiceprint_ttl_days)
        self._voiceprint_index = VoiceprintLSHIndex(seed=20260918, lsh_planes=96)
        self._multimodal_cleaner = EdgeMultimodalCleaner(
            quality_gate=QualityGate(),
        )

    def _commit_observations(self, obs_list: Sequence[Observation], reason: str) -> None:
        if not obs_list:
            return
        rev = self._store.current_world_revision()
        op = OperationRequest(
            operation_id=f"op:sensor:{uuid.uuid4().hex[:12]}",
            operation_name="ingest_sensor_observations",
            arguments={"count": len(obs_list)},
            expected_world_revision=rev,
            reason=reason,
            idempotency_key=str(uuid.uuid4()),
            source_class="sensor",
        )
        self._store.commit(obs_list, op)

    @property
    def byte_sink(self) -> RawByteSink:
        return self._byte_sink

    @property
    def voiceprint_registry(self) -> VoiceprintTTLRegistry:
        return self._voiceprint_registry

    def ingest_imu_stream(
        self,
        samples: Sequence[tuple[int, float]],
        *,
        device: str = "band_imu_6axis",
    ) -> tuple[SensorIngestSummary, list[Observation]]:
        """Ingest raw 50Hz accelerometry stream without raw DB flooding.
        
        Extracts MacroMotionState and escalates dual-condition ImpactWaveform.
        """
        if not samples:
            return SensorIngestSummary(0, 0, 1.0, False, 0), []

        now = utc_now()
        first_t = samples[0][0]
        if isinstance(first_t, (int, float)) and not isinstance(first_t, datetime):
            dt_samples = [
                (now + timedelta(microseconds=int(ts)), float(val)) for ts, val in samples
            ]
        else:
            dt_samples = samples

        result = self._imu_compressor.compress(dt_samples)
        created_obs: list[Observation] = []
        alerts: list[str] = []
        is_p0 = False

        # 1. Macro Motion States
        for macro in result.macro_states:
            obs = Observation(
                object_id=f"obs:imu:macro:{uuid.uuid4().hex[:12]}",
                subject_id=self._subject_id,
                learned_at=now,
                recorded_at=now,
                created_by="pipeline:wearable_imu",
                source_kind="wearable_imu",
                modality="motion",
                value={
                    "motion_class": macro.motion_class,
                    "mean_g": macro.mean_g,
                    "rms_g": macro.rms_g,
                    "variance": macro.variance,
                    "sample_count": macro.sample_count,
                    "duration_s": macro.duration_s,
                },
                unit="g",
                data_quality={
                    "compression_ratio": macro.compression_ratio,
                    "error_bound_holds": result.error_bound_holds,
                    "hardware_derivative_computed": False,
                },
                occurred=TemporalExtent(start=macro.start_time, end=macro.end_time),
            )
            created_obs.append(obs)

        # 2. Impacts and Fall Detection
        for impact in result.impacts:
            if impact.suspect_fall:
                is_p0 = True
                alerts.append(f"FALL_DETECTED: peak_g={impact.peak_g:.2f}g")

            obs = Observation(
                object_id=f"obs:imu:impact:{uuid.uuid4().hex[:12]}",
                subject_id=self._subject_id,
                learned_at=now,
                recorded_at=now,
                created_by="pipeline:wearable_imu",
                source_kind="wearable_imu_impact",
                modality="motion_impact",
                value={
                    "peak_g": impact.peak_g,
                    "duration_s": impact.duration_s,
                    "sample_count": len(impact.samples),
                    "suspect_fall": impact.suspect_fall,
                    "wake_priority": WakePriority.P0_CRITICAL_SAFETY.value if impact.suspect_fall else WakePriority.P1_TIME_CRITICAL.value,
                },
                unit="g",
                data_quality={
                    "hardware_derivative_computed": False,
                    "max_samples_clamped": len(impact.samples) <= 32,
                },
                occurred=TemporalExtent(
                    start=impact.onset_time,
                    end=max(now, impact.onset_time + timedelta(seconds=max(0.1, impact.duration_s))),
                ),
            )
            created_obs.append(obs)

        self._commit_observations(created_obs, "IMU stream ingest")

        ratio = (len(samples) / len(created_obs)) if created_obs else 1.0
        summary = SensorIngestSummary(
            raw_samples_count=len(samples),
            compressed_observations_count=len(created_obs),
            compression_ratio=ratio,
            p0_critical_alert=is_p0,
            purged_bytes_count=0,
            alerts=tuple(alerts),
        )
        return summary, created_obs

    def ingest_ppg_stream(
        self,
        samples: Sequence[tuple[datetime, float]],
        *,
        device: str = "band_ppg_optical",
    ) -> tuple[SensorIngestSummary, list[Observation]]:
        """Ingest continuous heart rate optical PPG stream.
        
        Compresses steady periods to episode means; escalates arrhythmias.
        """
        if not samples:
            return SensorIngestSummary(0, 0, 1.0, False, 0), []

        result = self._hr_compressor.compress(samples)
        created_obs: list[Observation] = []
        alerts: list[str] = []
        is_p0 = False
        now = utc_now()

        # 1. Steady Episode Means
        for ep in result.episodes:
            obs = Observation(
                object_id=f"obs:ppg:mean:{uuid.uuid4().hex[:12]}",
                subject_id=self._subject_id,
                learned_at=now,
                recorded_at=now,
                created_by="pipeline:wearable_ppg",
                source_kind="wearable_ppg",
                modality="vital_hr",
                value={
                    "mean_bpm": ep.mean_value,
                    "min_bpm": ep.min_value,
                    "max_bpm": ep.max_value,
                    "sample_count": ep.sample_count,
                    "duration_s": ep.duration_s,
                },
                unit="bpm",
                data_quality={
                    "compression_type": "EPISODE_MEAN",
                    "steady_tolerance": 4.0,
                },
                occurred=TemporalExtent(start=ep.start_time, end=ep.end_time),
            )
            created_obs.append(obs)

        # 2. Anomalies (Arrhythmia, PVC, Tachycardia)
        for anomaly in result.anomalies:
            peak_bpm = anomaly.peak_value
            base_bpm = anomaly.baseline_value
            delta_bpm = peak_bpm - base_bpm
            if delta_bpm >= 45.0 or peak_bpm >= 170.0 or peak_bpm <= 40.0:
                is_p0 = True
                alerts.append(f"ACUTE_CARDIAC_ANOMALY: peak={peak_bpm}bpm delta={delta_bpm}bpm")

            obs = Observation(
                object_id=f"obs:ppg:anomaly:{uuid.uuid4().hex[:12]}",
                subject_id=self._subject_id,
                learned_at=now,
                recorded_at=now,
                created_by="pipeline:wearable_ppg",
                source_kind="wearable_ppg_anomaly",
                modality="vital_hr_anomaly",
                value={
                    "peak_bpm": peak_bpm,
                    "delta_bpm": delta_bpm,
                    "baseline_bpm": base_bpm,
                    "suspect_arrhythmia": True,
                    "wake_priority": WakePriority.P0_CRITICAL_SAFETY.value if is_p0 else WakePriority.P1_TIME_CRITICAL.value,
                },
                unit="bpm",
                data_quality={
                    "compression_type": "ANOMALY_ESCALATED",
                },
                occurred=TemporalExtent(
                    start=anomaly.onset_time,
                    end=max(now, anomaly.onset_time + timedelta(seconds=max(0.1, anomaly.duration_s))),
                ),
            )
            created_obs.append(obs)

        self._commit_observations(created_obs, "PPG stream ingest")

        ratio = (len(samples) / len(created_obs)) if created_obs else 1.0
        summary = SensorIngestSummary(
            raw_samples_count=len(samples),
            compressed_observations_count=len(created_obs),
            compression_ratio=ratio,
            p0_critical_alert=is_p0,
            purged_bytes_count=0,
            alerts=tuple(alerts),
        )
        return summary, created_obs

    def ingest_audio_event(
        self,
        *,
        transcript: str,
        audio_feature_128: Sequence[float] | None = None,
        speaker_entity_id: str | None = None,
        raw_audio_bytes: bytes | None = None,
        is_environment_noise: bool = False,
    ) -> tuple[SensorIngestSummary, Observation | None]:
        """Ingest mic audio event with Voiceprint LSH, 180d TTL, and Iron Rule 4 byte purging."""
        purged_bytes = 0
        if raw_audio_bytes:
            purged_bytes = len(raw_audio_bytes)
            # Iron Rule 4: Substandard/transient raw audio bytes physically zeroed & discarded
            self._byte_sink.purge(raw_audio_bytes)

        if is_environment_noise or not transcript.strip():
            # Street noise / chatter without intelligible content -> zero DB bloat
            return SensorIngestSummary(
                raw_samples_count=1,
                compressed_observations_count=0,
                compression_ratio=1.0,
                p0_critical_alert=False,
                purged_bytes_count=purged_bytes,
                alerts=("ENVIRONMENT_NOISE_PURGED",),
            ), None

        voiceprint_id = None
        now = utc_now()

        if audio_feature_128:
            candidates = self._voiceprint_index.candidate_search(audio_feature_128, k=1)
            if candidates and candidates[0][1] <= 15:
                voiceprint_id = candidates[0][0]
                self._voiceprint_registry.note_contact(voiceprint_id, now)
            else:
                voiceprint_id = f"vp:{uuid.uuid4().hex[:8]}"
                feat_hash = hashlib.sha256(
                    bytes(int(abs(x) * 1000) & 0xFF for x in audio_feature_128)
                ).hexdigest()[:16]
                profile = VoiceprintProfile(
                    voiceprint_id=voiceprint_id,
                    entity_id=speaker_entity_id,
                    feature_hash=feat_hash,
                    first_detected_at=now,
                    last_contact_at=now,
                )
                self._voiceprint_registry.register(profile)
                self._voiceprint_index.add(
                    voiceprint_id, audio_feature_128, speaker_entity_id
                )

        obs = Observation(
            object_id=f"obs:audio:{uuid.uuid4().hex[:12]}",
            subject_id=self._subject_id,
            learned_at=now,
            recorded_at=now,
            created_by="pipeline:wearable_audio",
            source_kind="wearable_mic",
            modality="audio_transcript",
            value={
                "transcript": transcript,
                "voiceprint_id": voiceprint_id,
                "speaker_entity_id": speaker_entity_id,
                "raw_bytes_retained": False,
            },
            raw_locator=None,  # Zero binary locator in durable world
            data_quality={
                "raw_purged": True,
                "purged_bytes": purged_bytes,
            },
            occurred=TemporalExtent(start=now, end=now),
        )
        self._commit_observations([obs], "Audio event ingest")

        summary = SensorIngestSummary(
            raw_samples_count=1,
            compressed_observations_count=1,
            compression_ratio=1.0,
            p0_critical_alert=False,
            purged_bytes_count=purged_bytes,
            alerts=(),
        )
        return summary, obs

    def ingest_camera_snapshot(
        self,
        *,
        caption: str,
        quality_score: float,
        raw_image_bytes: bytes | None = None,
    ) -> tuple[SensorIngestSummary, Observation | None]:
        """Ingest wearable camera snapshot with Article 33.5 quality gate and byte purge."""
        purged_bytes = 0
        if raw_image_bytes:
            purged_bytes = len(raw_image_bytes)
            self._byte_sink.purge(raw_image_bytes)

        # Quality Gate (< 0.4 discarded immediately per Constitution)
        if quality_score < 0.4 or not caption.strip():
            return SensorIngestSummary(
                raw_samples_count=1,
                compressed_observations_count=0,
                compression_ratio=1.0,
                p0_critical_alert=False,
                purged_bytes_count=purged_bytes,
                alerts=("POOR_IMAGE_QUALITY_PURGED",),
            ), None

        now = utc_now()
        obs = Observation(
            object_id=f"obs:image:{uuid.uuid4().hex[:12]}",
            subject_id=self._subject_id,
            learned_at=now,
            recorded_at=now,
            created_by="pipeline:wearable_camera",
            source_kind="wearable_camera",
            modality="image_caption",
            value={
                "caption": caption,
                "quality_score": quality_score,
                "raw_bytes_retained": False,
            },
            raw_locator=None,  # Iron Rule 4: never store raw binary images in SQLite
            data_quality={
                "quality_score": quality_score,
                "raw_image_purged": True,
                "purged_bytes": purged_bytes,
            },
            occurred=TemporalExtent(start=now, end=now),
        )
        self._commit_observations([obs], "Camera snapshot ingest")

        summary = SensorIngestSummary(
            raw_samples_count=1,
            compressed_observations_count=1,
            compression_ratio=1.0,
            p0_critical_alert=False,
            purged_bytes_count=purged_bytes,
            alerts=(),
        )
        return summary, obs
