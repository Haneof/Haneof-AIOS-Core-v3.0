from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile

from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2027, 1, 12, 16, 30, tzinfo=timezone.utc)
SUBJECT = "structured-search-repro"

with tempfile.TemporaryDirectory() as td:
    db = Path(td) / "world.sqlite"
    store = SQLiteWorldStore(db)

    structured = Observation(
        object_id="obs_structured_invoice",
        subject_id=SUBJECT,
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="review-repro",
        source_kind="invoice",
        modality="structured_record",
        value={
            "vendor": "North Mill",
            "item": "bread flour",
            "unit_price": 1.38,
            "currency": "USD",
        },
        metadata={"dimension": "dim:invoice"},
    )
    text = Observation(
        object_id="obs_text_invoice",
        subject_id=SUBJECT,
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="review-repro",
        source_kind="note",
        modality="text",
        value="North Mill bread flour old invoice price was 1.38 USD/kg.",
        metadata={"dimension": "dim:note"},
    )
    store.commit(
        [structured, text],
        OperationRequest(
            operation_name="review.seed.structured.search",
            expected_world_revision=0,
            reason="review-only structured search reproduction",
            idempotency_key="structured-search-seed",
            source_class=SourceClass.USER,
        ),
    )

    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    by_vendor = index.recall_candidates("North Mill", subject=SUBJECT, limit=20)
    by_price = index.recall_candidates("1.38", subject=SUBJECT, limit=20)

    vendor_ids = {hit.object_id for hit in by_vendor.hits}
    price_ids = {hit.object_id for hit in by_price.hits}

    print("REPRO_RESULT=STRUCTURED_OBSERVATION_VALUE_NOT_SEARCHABLE")
    print("VENDOR_HITS=" + ",".join(sorted(vendor_ids)))
    print("PRICE_HITS=" + ",".join(sorted(price_ids)))

    import sqlite3
    con = sqlite3.connect(db)
    row = con.execute(
        "SELECT haystack, excerpt FROM search_doc WHERE object_id=? AND revision=1",
        (structured.object_id,),
    ).fetchone()
    print(f"STRUCTURED_HAYSTACK={row[0]!r}")
    print(f"STRUCTURED_EXCERPT={row[1]!r}")

    assert text.object_id in vendor_ids
    assert text.object_id in price_ids
    assert structured.object_id not in vendor_ids
    assert structured.object_id not in price_ids
    assert row == ("", "")
