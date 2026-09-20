from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.ingest import (
    AUDIT_DIMENSION,
    MechanicalSeriesPolicy,
    MediaDescriptorRecord,
    NumericSample,
    RealityIngestService,
    RealityRecord,
    SourceAdapterSpec,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 20, 15, 0, tzinfo=timezone.utc)


def _world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, RealityIngestService(store=store, index=index)


def test_payment_and_order_remain_independent_source_dimensions(tmp_path):
    store, index, service = _world(tmp_path)
    payment = SourceAdapterSpec(
        adapter_id="android.payment.v1",
        source_kind="payment",
        dimension="dim:payment",
        source_class=SourceClass.USER,
        default_modality="structured_record",
    )
    order = SourceAdapterSpec(
        adapter_id="android.order.v1",
        source_kind="order",
        dimension="dim:order",
        source_class=SourceClass.USER,
        default_modality="structured_record",
    )

    p = service.ingest_record(
        payment,
        RealityRecord(
            external_record_id="pay-1001",
            occurred_at=datetime(
                2026, 9, 20, 8, 0, tzinfo=timezone(timedelta(hours=8))
            ),
            received_at=NOW,
            value={"amount": 38.5, "currency": "CNY", "merchant": "coffee-shop"},
            source_locator="content://wallet/payments/pay-1001",
            provenance={"provider": "wallet"},
        ),
    )
    o = service.ingest_record(
        order,
        RealityRecord(
            external_record_id="order-5001",
            occurred_at=datetime(
                2026, 9, 20, 8, 0, tzinfo=timezone(timedelta(hours=8))
            ),
            received_at=NOW,
            value={"item": "coffee", "quantity": 1},
            source_locator="content://shopping/orders/order-5001",
            provenance={"provider": "shopping-app"},
        ),
    )

    pp = store.get_payload(p.observation_id)
    op = store.get_payload(o.observation_id)

    assert pp["metadata"]["dimension"] == "dim:payment"
    assert op["metadata"]["dimension"] == "dim:order"
    assert pp["source_kind"] == "payment"
    assert op["source_kind"] == "order"
    assert pp["occurred"]["start"].startswith("2026-09-20T00:00:00")
    assert pp["raw_locator"] == "content://wallet/payments/pay-1001"

    objects = store.list_payloads()
    assert not any(item["object_type"] == "claim" for item in objects)
    assert not any(item["object_type"] == "relation" for item in objects)

    pay_hits = index.recall_candidates(
        "pay-1001",
        dimension="dim:payment",
        object_types=["observation"],
    )
    # Structured facts are not forced through a semantic text projection.
    assert pay_hits.status == "ok"


def test_exact_source_retry_reuses_fact_but_mutated_identity_conflicts(tmp_path):
    store, _, service = _world(tmp_path)
    spec = SourceAdapterSpec(
        adapter_id="notes.v1",
        source_kind="note",
        dimension="dim:notes",
        source_class=SourceClass.USER,
        default_modality="text",
    )
    record = RealityRecord(
        external_record_id="note-1",
        occurred_at=NOW,
        received_at=NOW,
        value="买牛奶",
        source_locator="content://notes/note-1",
    )

    first = service.ingest_record(spec, record)
    second = service.ingest_record(spec, record)

    assert second.observation_id == first.observation_id
    assert second.reused_existing is True
    assert store.current_world_revision() == first.world_revision

    with pytest.raises(ValueError, match="identity conflict"):
        service.ingest_record(
            spec,
            record.model_copy(update={"value": "买咖啡"}),
        )


def test_media_descriptor_persists_text_not_raw_binary(tmp_path):
    store, index, service = _world(tmp_path)
    camera = SourceAdapterSpec(
        adapter_id="camera.caption.v1",
        source_kind="camera",
        dimension="dim:camera_visual",
        source_class=SourceClass.SENSOR,
        default_modality="image_caption",
    )

    receipt = service.ingest_media_descriptor(
        camera,
        MediaDescriptorRecord(
            external_record_id="photo-1",
            occurred_at=NOW,
            received_at=NOW,
            descriptor="桌上有一台打开的笔记本电脑和一杯水。",
            descriptor_kind="image_caption",
            source_locator="media://camera/photo-1",
            provenance={"caption_model": "upstream-vision"},
            object_facts=("笔记本电脑可见", "水杯可见"),
        ),
    )
    payload = store.get_payload(receipt.observation_id)

    assert payload["modality"] == "image_caption"
    assert "笔记本电脑" in payload["value"]
    assert payload["metadata"]["provenance"]["raw_media_retained"] is False
    assert "raw_bytes" not in payload

    hits = index.recall_candidates(
        "笔记本电脑",
        object_types=["observation"],
    )
    assert receipt.observation_id in {hit.object_id for hit in hits.hits}


def test_invalid_binary_record_creates_auditable_ingest_failure(tmp_path):
    store, _, service = _world(tmp_path)
    camera = SourceAdapterSpec(
        adapter_id="camera.raw.v1",
        source_kind="camera",
        dimension="dim:camera_visual",
        source_class=SourceClass.SENSOR,
        default_modality="image",
    )

    receipt = service.ingest_mapping(
        camera,
        {
            "external_record_id": "raw-photo-1",
            "occurred_at": NOW,
            "received_at": NOW,
            "value": b"not-allowed-as-long-term-world-fact",
            "source_locator": "media://camera/raw-photo-1",
        },
        failure_time=NOW,
    )
    audit = store.get_payload(receipt.audit_observation_id)

    assert audit["source_kind"] == "ingest_audit"
    assert audit["metadata"]["dimension"] == AUDIT_DIMENSION
    assert audit["value"]["external_record_id"] == "raw-photo-1"
    assert audit["metadata"]["mechanical_ingest_failure"] is True


def test_numeric_series_is_mechanically_compressed_and_preserves_changes(tmp_path):
    store, _, service = _world(tmp_path)
    hr = SourceAdapterSpec(
        adapter_id="sensor.heart_rate.v1",
        source_kind="heart_rate",
        dimension="dim:heart_rate",
        source_class=SourceClass.SENSOR,
        default_modality="numeric",
    )
    values = [100, 101, 100, 115, 120, 80, 81, 80]
    samples = [
        NumericSample(
            external_record_id=f"hr-{i}",
            occurred_at=NOW + timedelta(minutes=i),
            value=float(value),
            source_locator=f"sensor://heart_rate/hr-{i}",
        )
        for i, value in enumerate(values)
    ]

    receipt = service.ingest_numeric_series(
        hr,
        series_id="hr-session-1",
        samples=samples,
        policy=MechanicalSeriesPolicy(
            tolerance=3.0,
            change_threshold=10.0,
            max_gap_seconds=120.0,
        ),
        unit="bpm",
        received_at=NOW + timedelta(minutes=10),
    )

    assert receipt.input_sample_count == len(samples)
    assert len(receipt.segment_observation_ids) < len(samples)
    assert len(receipt.change_observation_ids) == 2

    segments = [
        store.get_payload(object_id)
        for object_id in receipt.segment_observation_ids
    ]
    changes = [
        store.get_payload(object_id)
        for object_id in receipt.change_observation_ids
    ]
    assert all(item["object_type"] == "observation" for item in segments + changes)
    assert all(
        item["metadata"]["dimension"] == "dim:heart_rate"
        for item in segments + changes
    )
    assert all(
        item["metadata"].get("mechanical_threshold_event") is True
        for item in changes
    )
    assert not any(
        item["object_type"] == ObjectType.CLAIM.value
        for item in store.list_payloads()
    )

    retry = service.ingest_numeric_series(
        hr,
        series_id="hr-session-1",
        samples=samples,
        policy=MechanicalSeriesPolicy(
            tolerance=3.0,
            change_threshold=10.0,
            max_gap_seconds=120.0,
        ),
        unit="bpm",
        received_at=NOW + timedelta(minutes=10),
    )
    assert retry.reused_existing_count == (
        len(receipt.segment_observation_ids)
        + len(receipt.change_observation_ids)
    )


def test_adapter_requires_explicit_source_dimension_and_nonsemantic_source_class():
    with pytest.raises(ValueError, match="start with 'dim:'"):
        SourceAdapterSpec(
            adapter_id="bad",
            source_kind="payment",
            dimension="finance",
            source_class=SourceClass.USER,
            default_modality="structured",
        )

    with pytest.raises(ValueError, match="USER or SENSOR"):
        SourceAdapterSpec(
            adapter_id="bad-ai",
            source_kind="payment",
            dimension="dim:payment",
            source_class=SourceClass.AI_COGNITION,
            default_modality="structured",
        )
