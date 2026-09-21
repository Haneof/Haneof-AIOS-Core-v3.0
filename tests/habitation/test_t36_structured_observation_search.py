from __future__ import annotations

from datetime import datetime, timezone

from aios_core.contracts import (
    ObjectType,
    Observation,
    OperationRequest,
    SourceClass,
    TemporalExtent,
    new_object_id,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.storage import SQLiteWorldStore


NOW = datetime(2026, 12, 18, 12, 0, tzinfo=timezone.utc)


def test_t36_habitation_invoice_is_recallable_without_rewriting_world_fact(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    observation_id = new_object_id(ObjectType.OBSERVATION)
    value = {
        "vendor": "North Mill",
        "item": "bread flour",
        "unit_price": 1.38,
        "paid": False,
    }
    observation = Observation(
        object_id=observation_id,
        subject_id="resident-1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="habitation.t36.regression",
        source_kind="invoice",
        modality="structured",
        value=value,
    )
    store.commit(
        [observation],
        OperationRequest(
            operation_name="habitation.invoice.ingest",
            expected_world_revision=store.current_world_revision(),
            reason="T36 structured reality fact regression",
            idempotency_key="t36-habitation-invoice",
            source_class=SourceClass.PLATFORM,
        ),
    )

    durable_before = store.get_payload(observation_id)
    index = WorldSearchIndex(store.db_path, store=store)
    assert index.rebuild() == 1

    vendor_hits = index.recall_candidates("North Mill", subject="resident-1")
    price_hits = index.recall_candidates("1.38", subject="resident-1")

    assert observation_id in {hit.object_id for hit in vendor_hits.hits}
    assert observation_id in {hit.object_id for hit in price_hits.hits}
    assert store.get_payload(observation_id) == durable_before
    assert store.get_payload(observation_id)["value"] == value
