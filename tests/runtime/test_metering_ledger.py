from datetime import datetime, timedelta, timezone

import pytest

from aios_core.runtime.cognitive_runtime import ModelCallProvenance, ModelUsage
from aios_core.runtime.metering import ModelMeteringLedger
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def test_metering_write_does_not_advance_world_revision_or_create_world_object(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    ledger = ModelMeteringLedger(store)
    before = int(store.current_world_revision())

    record = ledger.record_model_call(
        subject_id="user_1",
        world_revision=before,
        recorded_at=NOW,
        execution_class="user_interaction",
        session_id="session_1",
        wake_reason="user_interaction",
        model_round_index=0,
        usage=ModelUsage(
            input_tokens=11,
            output_tokens=4,
            total_tokens=15,
            provider="openai",
            model="test-model",
            request_id="resp_meter_1",
        ),
    )

    assert int(store.current_world_revision()) == before
    assert store.list_payloads(subject_id="user_1") == []
    assert record.total_tokens == 15

    rows = ledger.list_model_calls(subject_id="user_1")
    assert rows == (record,)


def test_provider_request_id_makes_metering_replay_idempotent(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    ledger = ModelMeteringLedger(store)
    usage = ModelUsage(
        input_tokens=7,
        output_tokens=3,
        total_tokens=10,
        provider="anthropic",
        model="test-claude",
        request_id="msg_meter_same_response",
    )

    first = ledger.record_model_call(
        subject_id="user_1",
        world_revision=0,
        recorded_at=NOW,
        execution_class="background",
        wake_id="wake_1",
        wake_reason="watch_match",
        model_round_index=0,
        usage=usage,
    )
    second = ledger.record_model_call(
        subject_id="user_1",
        world_revision=0,
        recorded_at=NOW,
        execution_class="background",
        wake_id="wake_1",
        wake_reason="watch_match",
        model_round_index=0,
        usage=usage,
    )

    assert first.record_id == second.record_id
    assert len(ledger.list_model_calls(subject_id="user_1")) == 1


def test_missing_provider_usage_records_unknown_call_without_fake_zero_tokens(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    ledger = ModelMeteringLedger(store)
    provenance = ModelCallProvenance(
        provider="openai",
        model="test-model",
        request_id="resp_unknown_usage",
    )

    first = ledger.record_model_call(
        subject_id="user_1",
        world_revision=0,
        recorded_at=NOW,
        execution_class="background",
        wake_id="wake_unknown_usage",
        wake_reason="watch_match",
        model_round_index=0,
        usage=None,
        provenance=provenance,
    )
    second = ledger.record_model_call(
        subject_id="user_1",
        world_revision=9,
        recorded_at=NOW + timedelta(minutes=5),
        execution_class="background",
        wake_id="wake_unknown_usage",
        wake_reason="watch_match",
        model_round_index=0,
        usage=None,
        provenance=provenance,
    )

    assert first.record_id == second.record_id
    assert second.recorded_at == NOW
    assert first.provider == "openai"
    assert first.model == "test-model"
    assert first.provider_request_id == "resp_unknown_usage"
    assert first.usage_complete is False
    assert first.input_tokens is None
    assert first.output_tokens is None
    assert first.total_tokens is None
    assert len(ledger.list_model_calls(subject_id="user_1")) == 1


def test_same_provider_response_id_replay_conflict_fails_closed(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    ledger = ModelMeteringLedger(store)
    usage = ModelUsage(
        input_tokens=7,
        output_tokens=3,
        total_tokens=10,
        provider="anthropic",
        model="test-claude",
        request_id="msg_conflict",
    )
    ledger.record_model_call(
        subject_id="user_1",
        world_revision=0,
        recorded_at=NOW,
        execution_class="background",
        wake_id="wake_1",
        wake_reason="watch_match",
        model_round_index=0,
        usage=usage,
    )

    with pytest.raises(RuntimeError, match="metering replay conflicts"):
        ledger.record_model_call(
            subject_id="user_1",
            world_revision=1,
            recorded_at=NOW + timedelta(minutes=1),
            execution_class="periodic_review",
            wake_id="wake_other",
            wake_reason="periodic_review",
            model_round_index=0,
            usage=usage,
        )
