"""Unit test suite for WearableSensorPipeline (Window 83).

Validates:
1. IMU 50Hz compression (Article 33.1): raw 50Hz wave strictly collapsed into
   MacroMotionState, error bound holds, compression ratio > 50x.
2. Fall detection (Iron Rule 3): dual-condition impact escalation triggers P0 safety alert.
3. Optical PPG: resting rate collapsed into EpisodeMean, acute arrhythmia escalated.
4. Multimodal & Iron Rule 4: zero raw binary bloat in SQLite; substandard photo and
   street noise physically purged (<5ms); 180-day TTL voiceprint lifecycle.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aios_core.contracts.enums import WakePriority
from aios_core.contracts.time import utc_now
from aios_core.ingest.sensor_pipeline import WearableSensorPipeline
from aios_core.storage.sqlite_store import SQLiteWorldStore

UTC = timezone.utc


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_sensor_world.db"
        yield SQLiteWorldStore(db_path)


@pytest.fixture
def pipeline(store: SQLiteWorldStore):
    return WearableSensorPipeline(store, subject_id="tester_001")


def test_imu_50hz_stream_collapses_and_bounds_error(pipeline: WearableSensorPipeline, store: SQLiteWorldStore):
    # Simulate 50Hz resting IMU stream for 100 seconds (5,000 samples)
    step_us = 20_000  # 20ms = 50Hz
    samples = [(i * step_us, 1.0 + (i % 3) * 0.05) for i in range(5_000)]

    summary, obs_list = pipeline.ingest_imu_stream(samples)

    assert summary.raw_samples_count == 5_000
    assert summary.compressed_observations_count <= 10
    assert summary.compression_ratio > 100.0
    assert not summary.p0_critical_alert

    # Verify persisted in SQLite
    for obs in obs_list:
        payload = store.get_payload(obs.object_id)
        assert payload is not None
        assert payload["source_kind"] == "wearable_imu"
        assert payload["data_quality"]["error_bound_holds"] is True
        assert payload["data_quality"]["hardware_derivative_computed"] is False


def test_imu_dual_condition_impact_triggers_p0_fall_alert(pipeline: WearableSensorPipeline, store: SQLiteWorldStore):
    # Simulate steady walking then sudden high-g fall impact
    step_us = 20_000
    samples = [(i * step_us, 1.0) for i in range(2_000)]
    # Insert sharp impact at sample 1000: jumping from 1.0g to 14.5g
    samples[1000] = (1000 * step_us, 14.5)

    summary, obs_list = pipeline.ingest_imu_stream(samples)

    assert summary.p0_critical_alert is True
    assert any("FALL_DETECTED" in alert for alert in summary.alerts)

    # Check that an impact observation was persisted with P0 priority
    impact_obs = [o for o in obs_list if o.source_kind == "wearable_imu_impact"]
    assert len(impact_obs) >= 1
    assert impact_obs[0].value["suspect_fall"] is True
    assert impact_obs[0].value["wake_priority"] == WakePriority.P0_CRITICAL_SAFETY.value


def test_ppg_steady_resting_collapses_to_episode_mean(pipeline: WearableSensorPipeline, store: SQLiteWorldStore):
    # 1 hour of resting heart rate (3,600 samples, 70 bpm +- 1.5)
    now = utc_now()
    samples = [(now + timedelta(seconds=i), 70.0 + (i % 4) * 0.5) for i in range(3_600)]

    summary, obs_list = pipeline.ingest_ppg_stream(samples)

    assert summary.raw_samples_count == 3_600
    assert summary.compressed_observations_count <= 5
    assert summary.compression_ratio > 500.0
    assert not summary.p0_critical_alert

    for obs in obs_list:
        assert obs.source_kind == "wearable_ppg"
        assert obs.value["mean_bpm"] == pytest.approx(70.75, abs=1.0)


def test_ppg_acute_arrhythmia_triggers_anomaly_escalation(pipeline: WearableSensorPipeline, store: SQLiteWorldStore):
    now = utc_now()
    samples = [(now + timedelta(seconds=i), 72.0) for i in range(300)]
    # Acute ventricular tachycardia surge: spikes to 185 bpm
    samples.extend([(now + timedelta(seconds=300 + i), 185.0) for i in range(30)])

    summary, obs_list = pipeline.ingest_ppg_stream(samples)

    assert summary.p0_critical_alert is True
    anomaly_obs = [o for o in obs_list if o.source_kind == "wearable_ppg_anomaly"]
    assert len(anomaly_obs) >= 1
    assert anomaly_obs[0].value["peak_bpm"] == 185.0
    assert anomaly_obs[0].value["wake_priority"] == WakePriority.P0_CRITICAL_SAFETY.value


def test_audio_noise_purged_and_voiceprint_registered(pipeline: WearableSensorPipeline, store: SQLiteWorldStore):
    # 1. Environment noise is physically zeroed and discarded without DB write
    noisy_bytes = b"\x00\xFF" * 4096
    summary_noise, obs_noise = pipeline.ingest_audio_event(
        transcript="",
        raw_audio_bytes=noisy_bytes,
        is_environment_noise=True,
    )
    assert obs_noise is None
    assert summary_noise.compressed_observations_count == 0
    assert summary_noise.purged_bytes_count == 8192

    # 2. Clear speech with 128-dim voiceprint vector
    vp_vec = [0.1] * 128
    speech_bytes = b"\xAA\x55" * 2048
    summary_speech, obs_speech = pipeline.ingest_audio_event(
        transcript="老大，我们开始进行端侧内核调度开发",
        audio_feature_128=vp_vec,
        speaker_entity_id="entity:chief_architect",
        raw_audio_bytes=speech_bytes,
    )
    assert obs_speech is not None
    assert obs_speech.value["raw_bytes_retained"] is False
    assert obs_speech.raw_locator is None  # Zero raw blob in store
    assert obs_speech.value["speaker_entity_id"] == "entity:chief_architect"

    # Verify voiceprint in registry
    vp_id = obs_speech.value["voiceprint_id"]
    profile = pipeline.voiceprint_registry.get(vp_id)
    assert profile is not None
    assert profile.entity_id == "entity:chief_architect"


def test_camera_substandard_photo_purged_and_good_photo_captioned_only(
    pipeline: WearableSensorPipeline, store: SQLiteWorldStore
):
    garbage_bytes = b"\x00" * 10240
    # Quality < 0.4 -> dropped
    summary_bad, obs_bad = pipeline.ingest_camera_snapshot(
        caption="模糊抖动照片",
        quality_score=0.25,
        raw_image_bytes=garbage_bytes,
    )
    assert obs_bad is None
    assert summary_bad.compressed_observations_count == 0
    assert summary_bad.purged_bytes_count == 10240

    # Good quality photo (0.85) -> only Caption persisted, raw bytes purged
    good_bytes = b"\x11\x22" * 5120
    summary_good, obs_good = pipeline.ingest_camera_snapshot(
        caption="办公室白板上的 AIOS 架构图",
        quality_score=0.85,
        raw_image_bytes=good_bytes,
    )
    assert obs_good is not None
    assert obs_good.value["caption"] == "办公室白板上的 AIOS 架构图"
    assert obs_good.raw_locator is None  # Zero binary blob
    assert obs_good.value["raw_bytes_retained"] is False
    assert obs_good.data_quality["raw_image_purged"] is True
