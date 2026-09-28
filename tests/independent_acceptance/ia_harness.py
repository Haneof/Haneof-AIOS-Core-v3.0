"""Reviewer-owned shared harness for Independent Acceptance rev1.

Nothing here imports candidate test helpers at run time except the frozen
recovery module's *seed* builders, which are re-derived locally so that a
candidate change to its own tests cannot silently relax a reviewer probe.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import ModelCallProvenance, ModelDirective, ModelUsage
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 9, 28, 6, tzinfo=timezone.utc)
LATER = NOW + timedelta(minutes=1)
ANCHOR = "ia_anchor"


class ProcessDeath(BaseException):
    """Escape the capability registry's Exception -> CapabilityResult conversion."""


def world(db):
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def new_runtime(db, handler):
    store, index = world(db)
    return FusedTurnRuntime(store=store, index=index, model_handler=handler)


def directive(round_index, *, call=None, text="finished once"):
    rid = f"ia-provider-request-{round_index}"
    return ModelDirective(
        response=text if call is None else None,
        capability_calls=() if call is None else (call,),
        usage=ModelUsage(
            input_tokens=4, output_tokens=2, total_tokens=6,
            provider="ia-provider", model="ia-model", request_id=rid,
        ),
        provenance=ModelCallProvenance(
            provider="ia-provider", model="ia-model", request_id=rid,
        ),
    )


def seed_anchor(store):
    anchor = Observation(
        object_id=ANCHOR, subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=2)),
        learned_at=NOW - timedelta(hours=2), recorded_at=NOW - timedelta(hours=2),
        created_by="ia:seed", source_kind="conversation", modality="text",
        value="IA durable anchor", metadata={"dimension": "dim:ia"},
    )
    store.commit([anchor], OperationRequest(
        operation_name="ia.seed",
        expected_world_revision=int(store.current_world_revision()),
        reason="seed", idempotency_key="ia-anchor", source_class=SourceClass.USER,
    ))


def ref(object_id=ANCHOR, revision=1):
    return {"object_id": object_id, "revision": revision}


def payloads(store, object_type, predicate=None):
    rows = store.list_payloads(object_type=object_type, subject_id="user_1")
    return [p for p in rows if predicate is None or predicate(p)]


def q(db, sql, args=()):
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def op_rows(db):
    return q(db, "SELECT operation_id, operation_name, idempotency_key, "
                 "expected_world_revision, status, result_world_revision FROM operations")


def idem_rows(db):
    return q(db, "SELECT idempotency_key, operation_id, world_revision FROM idempotency_records")


def handoff_rows(db):
    return q(db, "SELECT * FROM background_model_return_handoffs")


def receipt_rows(db):
    return q(db, "SELECT * FROM background_model_response_receipts")


def staged_rows(db):
    return q(db, "SELECT * FROM background_model_responses")


def attempt_rows(db):
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        try:
            rows = [dict(r) for r in conn.execute(
                "SELECT * FROM background_model_attempts").fetchall()]
        except sqlite3.OperationalError:
            return []
    rows.sort(key=lambda r: (str(r.get("admitted_at")), str(r.get("model_round_index")),
                             str(r.get("attempt_id"))))
    return rows


def meter_rows(db):
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM metering_records").fetchall()]
        except sqlite3.OperationalError:
            return []


def cap(call_name, call_id, arguments):
    """Build a CapabilityCall without colliding with capability argument names."""
    return CapabilityCall(name=call_name, call_id=call_id, arguments=dict(arguments))
