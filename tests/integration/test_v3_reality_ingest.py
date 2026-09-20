from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import ErrorCode, ObjectType, SourceClass
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
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError


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



def test_structured_identity_hash_prevents_delimiter_boundary_collision(tmp_path):
    store, _, service = _world(tmp_path)
    first_spec = SourceAdapterSpec(
        adapter_id="a|b",
        source_kind="note",
        dimension="dim:notes",
        source_class=SourceClass.USER,
        default_modality="text",
    )
    second_spec = SourceAdapterSpec(
        adapter_id="a",
        source_kind="note",
        dimension="dim:notes",
        source_class=SourceClass.USER,
        default_modality="text",
    )

    first = service.ingest_record(
        first_spec,
        RealityRecord(
            external_record_id="c",
            occurred_at=NOW,
            received_at=NOW,
            value="first",
        ),
    )
    second = service.ingest_record(
        second_spec,
        RealityRecord(
            external_record_id="b|c",
            occurred_at=NOW,
            received_at=NOW,
            value="second",
        ),
    )

    assert first.observation_id != second.observation_id
    assert len(store.list_payloads(object_type=ObjectType.OBSERVATION)) == 2


def test_identity_text_is_canonicalized_and_subjects_are_isolated(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    spec = SourceAdapterSpec(
        adapter_id="  notes.v1  ",
        source_kind="  note  ",
        dimension="  dim:notes  ",
        source_class=SourceClass.USER,
        schema_version="  1  ",
        default_modality="  text  ",
    )
    record = RealityRecord(
        external_record_id="  note-1  ",
        external_revision="  7  ",
        occurred_at=NOW,
        received_at=NOW,
        value="买牛奶",
    )

    assert spec.adapter_id == "notes.v1"
    assert spec.dimension == "dim:notes"
    assert record.external_record_id == "note-1"
    assert record.external_revision == "7"

    user_one = RealityIngestService(store=store, subject_id=" user_1 ")
    user_two = RealityIngestService(store=store, subject_id="user_2")

    one = user_one.ingest_record(spec, record)
    one_retry = user_one.ingest_record(
        spec,
        record.model_copy(
            update={
                "external_record_id": "note-1",
                "external_revision": "7",
            }
        ),
    )
    two = user_two.ingest_record(spec, record)

    assert one_retry.observation_id == one.observation_id
    assert one_retry.reused_existing is True
    assert two.observation_id != one.observation_id
    assert store.get_payload(one.observation_id)["subject_id"] == "user_1"
    assert store.get_payload(two.observation_id)["subject_id"] == "user_2"


def test_same_source_revision_cannot_silently_change_adapter_semantics(tmp_path):
    store, _, service = _world(tmp_path)
    base = SourceAdapterSpec(
        adapter_id="notes.v1",
        source_kind="note",
        dimension="dim:notes",
        source_class=SourceClass.USER,
        default_modality="text",
    )
    record = RealityRecord(
        external_record_id="note-1",
        external_revision="3",
        occurred_at=NOW,
        received_at=NOW,
        value="same source payload",
        source_locator="content://notes/note-1",
    )
    service.ingest_record(base, record)

    rerouted = base.model_copy(update={"dimension": "dim:relationship"})
    with pytest.raises(ValueError, match="adapter semantics"):
        service.ingest_record(rerouted, record)

    reclassified = base.model_copy(update={"source_class": SourceClass.SENSOR})
    with pytest.raises(ValueError, match="adapter semantics"):
        service.ingest_record(reclassified, record)


def test_generic_reality_record_preserves_time_interval(tmp_path):
    store, _, service = _world(tmp_path)
    calendar = SourceAdapterSpec(
        adapter_id="calendar.v1",
        source_kind="calendar_event",
        dimension="dim:calendar",
        source_class=SourceClass.USER,
        default_modality="structured_record",
    )
    end = NOW + timedelta(hours=2)

    receipt = service.ingest_record(
        calendar,
        RealityRecord(
            external_record_id="meeting-1",
            occurred_at=NOW,
            occurred_end_at=end,
            received_at=NOW - timedelta(minutes=1),
            value={"title": "project review"},
        ),
    )
    payload = store.get_payload(receipt.observation_id)

    assert payload["occurred"]["start"].startswith(NOW.isoformat().replace("+00:00", ""))
    assert payload["occurred"]["end"].startswith(end.isoformat().replace("+00:00", ""))
    assert payload["metadata"]["occurred_end_at_original"] == end.isoformat()


def test_non_not_found_storage_failure_is_not_misclassified_as_missing(
    tmp_path,
    monkeypatch,
):
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
        value="x",
    )

    def broken_get_payload(*args, **kwargs):
        raise StoreError(
            ErrorCode.STORAGE_FAILURE,
            "simulated corrupt payload",
            context={"reason": "test_corruption"},
        )

    monkeypatch.setattr(store, "get_payload", broken_get_payload)
    with pytest.raises(StoreError) as exc_info:
        service.ingest_record(spec, record)
    assert exc_info.value.code == ErrorCode.STORAGE_FAILURE


def test_retry_through_commit_path_is_idempotent_under_race_window(
    tmp_path,
    monkeypatch,
):
    store, _, service = _world(tmp_path)
    spec = SourceAdapterSpec(
        adapter_id="notes.v1",
        source_kind="note",
        dimension="dim:notes",
        source_class=SourceClass.USER,
        default_modality="text",
    )
    record = RealityRecord(
        external_record_id="note-race",
        occurred_at=NOW,
        received_at=NOW,
        value="same logical request",
    )

    first = service.ingest_record(spec, record)
    first_revision = store.current_world_revision()

    monkeypatch.setattr(service, "_get_payload_if_exists", lambda object_id: None)
    replay = service.ingest_record(spec, record)

    assert replay.observation_id == first.observation_id
    assert replay.reused_existing is True
    assert store.current_world_revision() == first_revision


def test_numeric_series_rejects_mutated_content_under_same_series_identity(tmp_path):
    store, _, service = _world(tmp_path)
    spec = SourceAdapterSpec(
        adapter_id="sensor.hr.v1",
        source_kind="heart_rate",
        dimension="dim:heart_rate",
        source_class=SourceClass.SENSOR,
        default_modality="numeric",
    )
    samples = [
        NumericSample(
            external_record_id="hr-1",
            occurred_at=NOW,
            value=70.0,
        ),
        NumericSample(
            external_record_id="hr-2",
            occurred_at=NOW + timedelta(seconds=30),
            value=71.0,
        ),
    ]
    policy = MechanicalSeriesPolicy(
        tolerance=10.0,
        change_threshold=20.0,
        max_gap_seconds=60.0,
    )
    service.ingest_numeric_series(
        spec,
        series_id="window-1",
        samples=samples,
        policy=policy,
        unit="bpm",
        received_at=NOW + timedelta(minutes=1),
    )

    mutated = [
        samples[0],
        samples[1].model_copy(update={"value": 72.0}),
    ]
    with pytest.raises(ValueError, match="numeric series identity conflict"):
        service.ingest_numeric_series(
            spec,
            series_id="window-1",
            samples=mutated,
            policy=policy,
            unit="bpm",
            received_at=NOW + timedelta(minutes=2),
        )

    with pytest.raises(ValueError, match="numeric series identity conflict"):
        service.ingest_numeric_series(
            spec,
            series_id="window-1",
            samples=samples,
            policy=policy.model_copy(update={"tolerance": 11.0}),
            unit="bpm",
            received_at=NOW + timedelta(minutes=2),
        )


def test_numeric_contract_rejects_non_finite_values():
    with pytest.raises(ValueError):
        NumericSample(
            external_record_id="bad",
            occurred_at=NOW,
            value=float("nan"),
        )
    with pytest.raises(ValueError):
        MechanicalSeriesPolicy(
            tolerance=float("inf"),
            change_threshold=1.0,
            max_gap_seconds=60.0,
        )


def test_public_ingest_boundary_revalidates_model_copy_mutations(tmp_path):
    _, _, service = _world(tmp_path)
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
        value="合法文本",
    )

    dirty_spec = spec.model_copy(
        update={"source_class": SourceClass.AI_COGNITION}
    )
    with pytest.raises(ValueError, match="USER or SENSOR"):
        service.ingest_record(dirty_spec, record)

    dirty_record = record.model_copy(update={"value": b"raw-bytes"})
    with pytest.raises(ValueError, match="raw binary payloads"):
        service.ingest_record(spec, dirty_record)

    sensor = SourceAdapterSpec(
        adapter_id="sensor.hr.v1",
        source_kind="heart_rate",
        dimension="dim:heart_rate",
        source_class=SourceClass.SENSOR,
        default_modality="numeric",
    )
    samples = (
        NumericSample(
            external_record_id="hr-1",
            occurred_at=NOW,
            value=70.0,
        ),
        NumericSample(
            external_record_id="hr-2",
            occurred_at=NOW + timedelta(seconds=10),
            value=71.0,
        ),
    )
    dirty_policy = MechanicalSeriesPolicy(
        tolerance=2.0,
        change_threshold=10.0,
        max_gap_seconds=60.0,
    ).model_copy(update={"change_threshold": 0.0})
    with pytest.raises(ValueError):
        service.ingest_numeric_series(
            sensor,
            series_id="dirty-policy-window",
            samples=samples,
            policy=dirty_policy,
            unit="bpm",
            received_at=NOW + timedelta(minutes=1),
        )


def test_numeric_change_is_not_fabricated_across_unobserved_gap(tmp_path):
    store, _, service = _world(tmp_path)
    spec = SourceAdapterSpec(
        adapter_id="sensor.temperature.v1",
        source_kind="temperature",
        dimension="dim:temperature",
        source_class=SourceClass.SENSOR,
        default_modality="numeric",
    )
    samples = (
        NumericSample(
            external_record_id="temp-1",
            occurred_at=NOW,
            value=20.0,
            source_locator="sensor://temperature/temp-1",
        ),
        NumericSample(
            external_record_id="temp-2",
            occurred_at=NOW + timedelta(minutes=30),
            value=35.0,
            source_locator="sensor://temperature/temp-2",
        ),
    )

    receipt = service.ingest_numeric_series(
        spec,
        series_id="gap-window",
        samples=samples,
        policy=MechanicalSeriesPolicy(
            tolerance=1.0,
            change_threshold=5.0,
            max_gap_seconds=60.0,
        ),
        unit="C",
        received_at=NOW + timedelta(minutes=31),
    )

    assert len(receipt.segment_observation_ids) == 2
    assert receipt.change_observation_ids == ()

    first_segment = store.get_payload(receipt.segment_observation_ids[0])
    second_segment = store.get_payload(receipt.segment_observation_ids[1])
    assert first_segment["metadata"]["source_record_range"] == {
        "first": "temp-1",
        "last": "temp-1",
        "count": 1,
    }
    assert second_segment["metadata"]["source_record_range"] == {
        "first": "temp-2",
        "last": "temp-2",
        "count": 1,
    }
    assert first_segment["metadata"]["source_locator_range"] == {
        "first": "sensor://temperature/temp-1",
        "last": "sensor://temperature/temp-1",
    }
    assert second_segment["metadata"]["source_locator_range"] == {
        "first": "sensor://temperature/temp-2",
        "last": "sensor://temperature/temp-2",
    }


def test_failure_audit_identity_preserves_external_revision_and_adapter_semantics(tmp_path):
    store, _, service = _world(tmp_path)
    spec_v1 = SourceAdapterSpec(
        adapter_id="calendar.v1",
        source_kind="calendar_event",
        dimension="dim:calendar",
        source_class=SourceClass.USER,
        schema_version="1",
        default_modality="structured_record",
    )
    spec_v2 = spec_v1.model_copy(update={"schema_version": "2"})

    first = service.ingest_mapping(
        spec_v1,
        {
            "external_record_id": "event-1",
            "external_revision": "1",
            "occurred_at": NOW,
            "value": b"invalid-binary",
            "source_locator": "content://calendar/event-1",
        },
        failure_time=NOW,
    )
    second = service.ingest_mapping(
        spec_v1,
        {
            "external_record_id": "event-1",
            "external_revision": "2",
            "occurred_at": NOW,
            "value": b"invalid-binary",
            "source_locator": "content://calendar/event-1",
        },
        failure_time=NOW + timedelta(seconds=1),
    )
    third = service.ingest_mapping(
        spec_v2,
        {
            "external_record_id": "event-1",
            "external_revision": "2",
            "occurred_at": NOW,
            "value": b"invalid-binary",
            "source_locator": "content://calendar/event-1",
        },
        failure_time=NOW + timedelta(seconds=2),
    )

    assert len({
        first.audit_observation_id,
        second.audit_observation_id,
        third.audit_observation_id,
    }) == 3

    p1 = store.get_payload(first.audit_observation_id)
    p2 = store.get_payload(second.audit_observation_id)
    p3 = store.get_payload(third.audit_observation_id)
    assert p1["value"]["external_revision"] == "1"
    assert p2["value"]["external_revision"] == "2"
    assert p3["metadata"]["source_schema_version"] == "2"
    assert p3["metadata"]["failure_digest"]


def test_nested_binary_in_model_value_is_rejected_without_recursive_crash(tmp_path):
    from pydantic import BaseModel

    class WrappedPayload(BaseModel):
        blob: bytes

    _, _, service = _world(tmp_path)
    spec = SourceAdapterSpec(
        adapter_id="wrapped.v1",
        source_kind="wrapped",
        dimension="dim:wrapped",
        source_class=SourceClass.USER,
        default_modality="structured",
    )

    with pytest.raises(ValueError, match="raw binary payloads"):
        service.ingest_record(
            spec,
            RealityRecord(
                external_record_id="wrapped-1",
                occurred_at=NOW,
                received_at=NOW,
                value=WrappedPayload(blob=b"abc"),
            ),
        )

    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(ValueError):
        service.ingest_record(
            spec,
            RealityRecord(
                external_record_id="cycle-1",
                occurred_at=NOW,
                received_at=NOW,
                value=cyclic,
            ),
        )


def test_large_numeric_segment_keeps_compact_source_provenance(tmp_path):
    store, _, service = _world(tmp_path)
    spec = SourceAdapterSpec(
        adapter_id="sensor.steps.v1",
        source_kind="step_counter",
        dimension="dim:steps",
        source_class=SourceClass.SENSOR,
        default_modality="numeric",
    )
    samples = tuple(
        NumericSample(
            external_record_id=f"step-{i:04d}",
            occurred_at=NOW + timedelta(seconds=i),
            value=1000.0 + (i % 2),
            source_locator=f"sensor://steps/{i:04d}",
        )
        for i in range(1000)
    )

    receipt = service.ingest_numeric_series(
        spec,
        series_id="steps-window-large",
        samples=samples,
        policy=MechanicalSeriesPolicy(
            tolerance=2.0,
            change_threshold=100.0,
            max_gap_seconds=2.0,
        ),
        unit="count",
        received_at=NOW + timedelta(minutes=30),
    )

    assert len(receipt.segment_observation_ids) == 1
    payload = store.get_payload(receipt.segment_observation_ids[0])
    metadata = payload["metadata"]
    assert metadata["source_record_range"] == {
        "first": "step-0000",
        "last": "step-0999",
        "count": 1000,
    }
    assert "source_record_ids" not in metadata
    assert "source_locators" not in metadata
    assert metadata["source_record_ids_digest"]


# Experimental proxy: ensures the already-registered P13 PR gate executes the
# frozen self-resident blind replay in this non-production validation branch.
def test_experimental_self_resident_blind_replay_proxy(tmp_path):
    import importlib.util
    from pathlib import Path

    module_path = (
        Path(__file__).resolve().parents[1]
        / "experimental"
        / "test_p16_self_resident_blind_replay.py"
    )
    spec = importlib.util.spec_from_file_location(
        "p16_self_resident_blind_replay_exp",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.test_frozen_self_resident_blind_replay_reaches_real_world_and_exposes_wake_gap(
        tmp_path
    )
