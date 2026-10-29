"""Arm A — the REAL mechanical cleaning path (aios_core.ingest.RealityIngestService).

Nothing here is simulated: records go through the production ingest service into a
real SQLiteWorldStore. Whatever survives is what the current system would actually
keep. Text records are expected to pass through untouched; only the numeric stream
gets mechanical compression.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aios_core.contracts.enums import SourceClass
from aios_core.ingest import (
    MechanicalSeriesPolicy,
    NumericSample,
    RealityIngestService,
    RealityRecord,
    SourceAdapterSpec,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore

from sim_day import RECORDS

ADAPTERS: dict[str, SourceAdapterSpec] = {
    "dim:mic_audio": SourceAdapterSpec(
        adapter_id="wearable.mic.v1", source_kind="mic_transcript",
        dimension="dim:mic_audio", source_class=SourceClass.USER,
        default_modality="transcript",
    ),
    "dim:payment": SourceAdapterSpec(
        adapter_id="phone.payment.v1", source_kind="payment",
        dimension="dim:payment", source_class=SourceClass.USER,
        default_modality="structured_record",
    ),
    "dim:order": SourceAdapterSpec(
        adapter_id="phone.order.v1", source_kind="order",
        dimension="dim:order", source_class=SourceClass.USER,
        default_modality="structured_record",
    ),
    "dim:calendar": SourceAdapterSpec(
        adapter_id="phone.calendar.v1", source_kind="calendar",
        dimension="dim:calendar", source_class=SourceClass.USER,
        default_modality="structured_record",
    ),
    "dim:note": SourceAdapterSpec(
        adapter_id="phone.note.v1", source_kind="note",
        dimension="dim:note", source_class=SourceClass.USER,
        default_modality="text",
    ),
    "dim:camera_visual": SourceAdapterSpec(
        adapter_id="glass.camera.v1", source_kind="camera",
        dimension="dim:camera_visual", source_class=SourceClass.SENSOR,
        default_modality="caption",
    ),
    "dim:app_usage": SourceAdapterSpec(
        adapter_id="phone.appusage.v1", source_kind="app_event",
        dimension="dim:app_usage", source_class=SourceClass.USER,
        default_modality="notification",
    ),
    "dim:external_chat": SourceAdapterSpec(
        adapter_id="phone.chat.v1", source_kind="chat",
        dimension="dim:external_chat", source_class=SourceClass.USER,
        default_modality="message",
    ),
    "dim:heart_rate": SourceAdapterSpec(
        adapter_id="wearable.hr.v1", source_kind="heart_rate",
        dimension="dim:heart_rate", source_class=SourceClass.SENSOR,
        default_modality="numeric",
    ),
}


def build_heart_rate_samples() -> list[NumericSample]:
    """1000 samples across the day: baseline ~70, with a real spike at 15:41
    (the moment the user said the dizziness was severe)."""
    samples: list[NumericSample] = []
    base = datetime(2026, 10, 28, 0, 0, tzinfo=timezone.utc)
    for i in range(1000):
        minute = (i * 1440) // 1000
        second = ((i * 86400) // 1000) % 60
        t = base + timedelta(minutes=minute, seconds=second)
        value = 70.0 + ((i % 7) - 3) * 1.5          # 稳定在 ~65-76
        if 15 * 60 + 35 <= minute <= 15 * 60 + 50:  # 头晕时段
            value = 128.0 + ((i % 5) - 2) * 2.0     # 明显飙升
        samples.append(
            NumericSample(
                external_record_id=f"hr-{i:04d}",
                occurred_at=t,
                value=round(float(value), 1),
                source_locator=f"sensor://hr/{i:04d}",
            )
        )
    return samples


def run(db_path: Path) -> dict:
    store = SQLiteWorldStore(db_path)
    index = WorldSearchIndex(db_path, store=store)
    index.rebuild()
    service = RealityIngestService(store=store, index=index)

    kept: list[str] = []
    dropped: list[str] = []
    failures: list[tuple[str, str]] = []

    for rec in RECORDS:
        if rec["kind"] == "numeric":
            continue
        spec = ADAPTERS[rec["dim"]]
        try:
            service.ingest_record(
                spec,
                RealityRecord(
                    external_record_id=rec["id"],
                    occurred_at=rec["t"],
                    received_at=rec["t"],
                    value=rec["text"],
                    source_locator=f"adapter://{spec.adapter_id}/{rec['id']}",
                ),
            )
            kept.append(rec["id"])
        except Exception as exc:  # noqa: BLE001 - report, do not swallow silently
            dropped.append(rec["id"])
            failures.append((rec["id"], f"{type(exc).__name__}: {exc}"))

    numeric_note = ""
    try:
        receipt = service.ingest_numeric_series(
            ADAPTERS["dim:heart_rate"],
            series_id="hr-2026-10-28",
            samples=build_heart_rate_samples(),
            policy=MechanicalSeriesPolicy(
                tolerance=3.0, change_threshold=15.0, max_gap_seconds=300.0
            ),
            unit="bpm",
            received_at=datetime(2026, 10, 28, 23, 59, tzinfo=timezone.utc),
        )
        numeric_note = (
            f"1000 采样 → {len(receipt.segment_observation_ids)} 段 + "
            f"{len(receipt.change_observation_ids)} 个变化事件"
        )
        kept.append("hr_series")
    except Exception as exc:  # noqa: BLE001
        dropped.append("hr_series")
        failures.append(("hr_series", f"{type(exc).__name__}: {exc}"))

    total_objects = len(store.list_object_ids()) if hasattr(store, "list_object_ids") else None
    return {
        "arm": "mechanical",
        "kept": kept,
        "dropped": dropped,
        "failures": failures,
        "numeric_note": numeric_note,
        "total_objects": total_objects,
    }


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        result = run(Path(tmp) / "world.db")
    print("机制清洗结果")
    print(f"  保留 {len(result['kept'])} 条 / 共 {len(RECORDS)} 条")
    print(f"  丢弃 {result['dropped']}")
    print(f"  数值流: {result['numeric_note']}")
    for fid, err in result["failures"]:
        print(f"  [入库失败] {fid}: {err[:120]}")
