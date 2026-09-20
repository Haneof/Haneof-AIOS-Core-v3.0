from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.errors import AIOSProtocolError
from aios_core.ingest.external import ExternalFactIngestor
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 20, 6, 45, tzinfo=timezone.utc)


def test_user_digital_fact_is_source_bound_and_dimension_explicit(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    ingest = ExternalFactIngestor(store, source_class=SourceClass.USER)

    result = ingest.commit_fact(
        source_system="android.calendar",
        source_record_id="event-42",
        dimension="dim:calendar",
        source_kind="calendar_event",
        modality="structured",
        value={"title": "Project review", "calendar_id": "work"},
        occurred_at=NOW + timedelta(days=2),
        learned_at=NOW,
        raw_locator="android-calendar://event/42",
        ingest_mode="historical",
        source_schema_version="calendar-v1",
        metadata={"account_scope": "primary"},
    )

    assert result.world_revision == 1
    payloads = store.list_payloads(object_type=ObjectType.OBSERVATION)
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["object_id"] == result.observation_id
    assert payload["source_kind"] == "calendar_event"
    assert payload["raw_locator"] == "android-calendar://event/42"
    assert payload["metadata"]["dimension"] == "dim:calendar"
    assert payload["metadata"]["source_system"] == "android.calendar"
    assert payload["metadata"]["source_record_id"] == "event-42"
    assert payload["metadata"]["ingest_mode"] == "historical"
    assert payload["metadata"]["source_schema_version"] == "calendar-v1"
    assert payload["metadata"]["account_scope"] == "primary"

    # Calendar data may describe a future event learned now. Acquisition must not
    # rewrite that fact just to force occurred_at <= learned_at.
    assert payload["occurred"]["start"] > payload["learned_at"]


def test_exact_retry_replays_but_mutated_source_identity_conflicts(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    ingest = ExternalFactIngestor(store, source_class=SourceClass.SENSOR)

    kwargs = dict(
        source_system="wearable.ppg",
        source_record_id="sample-window-7",
        dimension="dim:heart_rate",
        source_kind="heart_rate_window",
        modality="scalar",
        value={"mean_bpm": 76.2, "sample_count": 120},
        unit="bpm",
        occurred_at=NOW,
        learned_at=NOW,
        data_quality={"coverage_ratio": 0.99},
    )

    first = ingest.commit_fact(**kwargs)
    replay = ingest.commit_fact(**kwargs)

    assert first.world_revision == replay.world_revision == 1
    assert replay.idempotent_replay is True

    with pytest.raises(AIOSProtocolError):
        ingest.commit_fact(
            **{
                **kwargs,
                "value": {"mean_bpm": 101.0, "sample_count": 120},
            }
        )


def test_adapter_cannot_overwrite_reserved_provenance_metadata(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    ingest = ExternalFactIngestor(store)

    with pytest.raises(ValueError, match="reserved provenance"):
        ingest.commit_fact(
            source_system="notes.app",
            source_record_id="note-9",
            dimension="dim:notes",
            source_kind="note",
            modality="text",
            value="remember the appointment",
            occurred_at=NOW,
            learned_at=NOW,
            metadata={"dimension": "dim:relationship"},
        )


def test_external_ingest_rejects_cognition_and_privileged_source_classes(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")

    for source_class in (
        SourceClass.AI_COGNITION,
        SourceClass.MAINTENANCE,
        SourceClass.SAFETY,
    ):
        with pytest.raises(ValueError, match="USER or SENSOR"):
            ExternalFactIngestor(store, source_class=source_class)


def test_blank_source_identity_and_unknown_ingest_mode_are_rejected(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    ingest = ExternalFactIngestor(store)

    with pytest.raises(ValueError, match="source_record_id"):
        ingest.commit_fact(
            source_system="notes.app",
            source_record_id="   ",
            dimension="dim:notes",
            source_kind="note",
            modality="text",
            value="x",
            occurred_at=NOW,
            learned_at=NOW,
        )

    with pytest.raises(ValueError, match="ingest_mode"):
        ingest.commit_fact(
            source_system="notes.app",
            source_record_id="note-1",
            dimension="dim:notes",
            source_kind="note",
            modality="text",
            value="x",
            occurred_at=NOW,
            learned_at=NOW,
            ingest_mode="magic",
        )
