"""Synthetic trusted external-return adapter used only by Core unit tests.

This module is a TEST FIXTURE. It is not a C15 transport, not a C15 operator
implementation, and it grants no production trust to any real handler. It stands
in for the one actor the new Core contract actually trusts: a provider/relay
adapter that was handed a one-shot return capability at dispatch time and then
observed the real external return *after* the Core process died.

Nothing here is imported by ``src/aios_core``. If a probe can be made to pass
only by changing this file, the probe is a harness bug, not a product result.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3
from typing import Callable

from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
)
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 9, 30, 6, tzinfo=timezone.utc)


class ProcessDeath(BaseException):
    """Escape the runtime's ordinary Exception-to-result conversion.

    Raising it from the model handler models the Core process dying at the
    dispatch await, i.e. after the outbound request crossed the provider
    boundary and before the trusted return callback could ever run.
    """


def world(db):
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def seed_anchor(store, *, key="late_return_anchor", object_id=None):
    anchor = Observation(
        object_id=object_id or f"late_return_anchor_{key}",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=2)),
        learned_at=NOW - timedelta(hours=2),
        recorded_at=NOW - timedelta(hours=2),
        created_by="test:late-trusted-return",
        source_kind="conversation",
        modality="text",
        value="A durable anchor for a late trusted external return",
        metadata={"dimension": "dim:late"},
    )
    store.commit(
        [anchor],
        OperationRequest(
            operation_name="test.late_trusted_return.seed",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed anchor",
            idempotency_key=f"late-return-anchor:{key}",
            source_class=SourceClass.USER,
        ),
    )
    return anchor


def trusted_directive(
    request_id: str,
    *,
    response: str = "late return applied exactly once",
    provider: str = "late-trusted-provider",
    model: str = "late-trusted-model",
):
    """One exact directive carrying a full provider/model/request identity."""

    return ModelDirective(
        response=response,
        capability_calls=(),
        usage=ModelUsage(
            input_tokens=7,
            output_tokens=3,
            total_tokens=10,
            provider=provider,
            model=model,
            request_id=request_id,
        ),
        provenance=ModelCallProvenance(
            provider=provider, model=model, request_id=request_id
        ),
    )


def anonymous_directive(*, response: str = "anonymous bytes"):
    """A directive with no provider identity: it can never become trusted."""

    return ModelDirective(response=response, capability_calls=(), usage=None, provenance=None)


class SyntheticExternalResponder:
    """A registered, authorized observer of one real external return.

    Implements the Core ``ExternalReturnObserver`` protocol. It is handed a
    one-shot, per-attempt return capability at dispatch time and keeps it across
    the Core process death, exactly like a real relay adapter that already put
    the token on the wire.
    """

    def __init__(self, *, wire: Callable[[str, object], None] | None = None) -> None:
        self.capabilities: dict[str, object] = {}
        self.wire = wire

    # -- Core ExternalReturnObserver protocol ---------------------------------
    def accept_return_capability(self, snapshot, capability) -> None:
        self.capabilities[capability.attempt_id] = capability
        if self.wire is not None:
            self.wire(capability.attempt_id, capability)

    # -- external side --------------------------------------------------------
    def finish_after_core_death(self, attempt_id: str, directive: ModelDirective) -> str:
        """Complete the exact external return and mint its proof.

        Runs *after* the Core process is gone, which is the whole point: the
        authenticity artifact is contemporaneous with the real external return
        and is produced by the authorized observer, not by a recovery caller.
        """

        capability = self.capabilities.get(attempt_id)
        if capability is None:
            raise AssertionError(
                "the registered external-return observer never received a "
                f"return capability for {attempt_id}"
            )
        return capability.prove_external_return(directive)


def dispatch_then_die(_snapshot):
    """Model handler that crosses the boundary and then kills the Core process."""

    raise ProcessDeath("core process died at the provider dispatch await")


def meters(runtime, *, subject_id: str = "user_1") -> list:
    return list(runtime.metering.list_model_calls(subject_id=subject_id))


def capability_rows(db) -> list[tuple]:
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        try:
            return [
                tuple(bool(value) if index == 7 else value
                      for index, value in enumerate(tuple(row)))
                for row in conn.execute(
                    "SELECT attempt_id, subject_id, work_kind, work_id, "
                    "model_round_index, outbound_request_fingerprint, relay_id, "
                    "(consumed_at IS NOT NULL) FROM background_model_return_capabilities "
                    "ORDER BY attempt_id"
                )
            ]
        except sqlite3.OperationalError:
            # The capability table does not exist on a Core that cannot issue one.
            return []
