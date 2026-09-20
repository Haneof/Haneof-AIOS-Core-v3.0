"""Durable Wake -> resident-runtime dispatch for AIOS v3.0.

This module is intentionally mechanical. It claims and completes durable Wake
objects, records the deterministic Step-0 gate result, and exposes the exact trigger
refs to the resident runtime. It does not decide what the Wake means or what the AI
should do about it.

Specialized paths remain specialized:
- USER_INTERACTION is handled by the conversation turn runtime.
- PERIODIC_REVIEW is handled by P15 review orchestration.
- SAFETY requires the dedicated hardware-first safety path.

The generic resident dispatcher is for ordinary durable world Wakes such as
TASK_DUE, WATCH_MATCH, RECOVERY and registered mechanical triggers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Callable, Mapping

from aios_core.contracts.enums import (
    MaintenanceClass,
    ObjectType,
    SourceClass,
    WakeSource,
    WakeState,
)
from aios_core.contracts.models import Wake
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore


class WakeStep0Outcome(StrEnum):
    """ADJ-001 deterministic pre-model gate outcome."""

    OK = "ok"
    QUIET = "quiet"
    HARD_BLOCK = "hard_block"


@dataclass(frozen=True, slots=True)
class WakeStep0Decision:
    """Auditable result of the deterministic Step-0 gate.

    The gate itself lives at the platform/device boundary because clock, calendar,
    driving, sleep, DND, channel and safety state are external inputs. Core requires
    an explicit result rather than silently assuming that outward delivery is legal.
    """

    outcome: WakeStep0Outcome
    audit: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, WakeStep0Outcome):
            object.__setattr__(self, "outcome", WakeStep0Outcome(str(self.outcome)))
        if not isinstance(self.audit, Mapping):
            raise ValueError("step0 audit must be a mapping")

    @property
    def delivery_allowed(self) -> bool:
        return self.outcome is WakeStep0Outcome.OK

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "delivery_allowed": self.delivery_allowed,
            "audit": dict(self.audit),
        }


WakeStep0Gate = Callable[[Wake, datetime], WakeStep0Decision]


@dataclass(frozen=True, slots=True)
class WakeDispatchRequest:
    subject_id: str
    wake_ref: ObjectRef
    wake_source: WakeSource
    rule_id: str | None
    priority: int
    evidence_refs: tuple[ObjectRef, ...]
    step0: WakeStep0Decision


@dataclass(frozen=True, slots=True)
class WakeDispatchReceipt:
    wake_id: str
    revision: int
    state: str
    world_revision: int


GENERIC_RESIDENT_WAKE_SOURCES: frozenset[WakeSource] = frozenset(
    {
        WakeSource.MECHANICAL_CHANGE,
        WakeSource.KEYWORD_ENTITY,
        WakeSource.NO_UPDATE,
        WakeSource.TASK_DUE,
        WakeSource.WATCH_MATCH,
        WakeSource.RECOVERY,
    }
)


class WakeDispatchService:
    """Claim/complete ordinary durable Wakes without performing cognition."""

    _DISPATCH_KIND = "generic_resident_wake"

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex | None = None,
        subject_id: str = "user_1",
    ) -> None:
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must not be blank")
        self.store = store
        self.index = index
        self.subject_id = subject_id.strip()

    def _catch_up(self) -> None:
        if self.index is not None:
            self.index.catch_up()

    def resolve(self, wake_ref: ObjectRef) -> Wake:
        if wake_ref.revision is None:
            raise ValueError("wake_ref must pin an exact revision")
        payload = self.store.get_payload(
            wake_ref.object_id,
            revision=wake_ref.revision,
        )
        wake = Wake.model_validate(payload)
        if wake.subject_id != self.subject_id:
            raise ValueError("wake belongs to another subject")
        return wake

    def latest(self, wake_id: str) -> Wake:
        wake = Wake.model_validate(self.store.get_payload(str(wake_id)))
        if wake.subject_id != self.subject_id:
            raise ValueError("wake belongs to another subject")
        return wake

    @staticmethod
    def _step0_from_wake(wake: Wake) -> WakeStep0Decision:
        raw = wake.metadata.get("dispatch_step0")
        if not isinstance(raw, Mapping):
            raise ValueError("RUNNING wake is missing dispatch Step-0 audit")
        audit = raw.get("audit")
        return WakeStep0Decision(
            outcome=WakeStep0Outcome(str(raw.get("outcome"))),
            audit=(dict(audit) if isinstance(audit, Mapping) else {}),
        )

    @staticmethod
    def _request(wake: Wake, step0: WakeStep0Decision) -> WakeDispatchRequest:
        return WakeDispatchRequest(
            subject_id=wake.subject_id,
            wake_ref=ObjectRef(object_id=wake.object_id, revision=wake.revision),
            wake_source=wake.wake_source,
            rule_id=wake.rule_id,
            priority=wake.priority,
            evidence_refs=tuple(wake.evidence_refs),
            step0=step0,
        )

    def claim(
        self,
        wake_ref: ObjectRef,
        *,
        started_at: datetime,
        step0_gate: WakeStep0Gate,
    ) -> WakeDispatchRequest:
        """Atomically claim a NEW wake, or resume the same RUNNING dispatch.

        The Step-0 gate is evaluated exactly once when NEW -> RUNNING. Crash resume
        reuses the recorded result, so a retry cannot silently change the historical
        delivery gate after model execution may already have started.
        """

        if not callable(step0_gate):
            raise TypeError("step0_gate must be callable")
        started = as_utc(started_at, "started_at")
        pinned = self.resolve(wake_ref)
        latest = self.latest(pinned.object_id)

        if latest.wake_state is WakeState.RUNNING:
            if latest.metadata.get("dispatch_kind") != self._DISPATCH_KIND:
                raise ValueError("wake is RUNNING under a specialized dispatcher")
            return self._request(latest, self._step0_from_wake(latest))

        if latest.revision != pinned.revision:
            raise ValueError("wake_ref is no longer current")
        if latest.wake_state is not WakeState.NEW:
            raise ValueError("only NEW or resumable RUNNING wake may be dispatched")

        decision = step0_gate(latest, started)
        if not isinstance(decision, WakeStep0Decision):
            raise TypeError("step0_gate must return WakeStep0Decision")

        metadata = dict(latest.metadata)
        metadata.update(
            {
                "dispatch_kind": self._DISPATCH_KIND,
                "dispatch_started_at": started.isoformat(),
                "dispatch_step0": decision.as_dict(),
            }
        )
        running = Wake.model_validate(
            {
                **latest.model_dump(mode="python", round_trip=True),
                "revision": latest.revision + 1,
                "occurred": TemporalExtent.point(started),
                "learned_at": started,
                "recorded_at": started,
                "wake_state": WakeState.RUNNING,
                "last_hit_at": latest.last_hit_at,
                "status": WakeState.RUNNING.value,
                "metadata": metadata,
            }
        )
        result = self.store.commit(
            [running],
            OperationRequest(
                operation_name="wake.dispatch.begin",
                arguments={
                    "wake_id": running.object_id,
                    "revision": running.revision,
                    "wake_source": running.wake_source.value,
                    "step0": decision.as_dict(),
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="claim durable wake for resident-model execution",
                idempotency_key=(
                    f"wake-dispatch-begin:{running.object_id}:{running.revision}"
                ),
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.WAKE_DISPATCH,
            ),
        )
        self._catch_up()
        _ = result
        return self._request(running, decision)

    def complete(
        self,
        request: WakeDispatchRequest,
        *,
        completed_at: datetime,
        termination_reason: str,
        model_rounds: int,
        capability_names: tuple[str, ...] = (),
    ) -> WakeDispatchReceipt:
        if request.subject_id != self.subject_id:
            raise ValueError("wake request belongs to another subject")
        completed_at = as_utc(completed_at, "completed_at")
        running = self.resolve(request.wake_ref)
        latest = self.latest(running.object_id)

        if (
            latest.wake_state is WakeState.COMPLETED
            and latest.metadata.get("dispatch_kind") == self._DISPATCH_KIND
        ):
            return WakeDispatchReceipt(
                wake_id=latest.object_id,
                revision=latest.revision,
                state=latest.wake_state.value,
                world_revision=int(self.store.current_world_revision()),
            )

        if latest.revision != running.revision:
            raise ValueError("wake is no longer current")
        if running.wake_state is not WakeState.RUNNING:
            raise ValueError("only RUNNING wake may complete generic dispatch")
        if running.metadata.get("dispatch_kind") != self._DISPATCH_KIND:
            raise ValueError("wake is RUNNING under a specialized dispatcher")

        metadata = dict(running.metadata)
        metadata.update(
            {
                "dispatch_completed_at": completed_at.isoformat(),
                "termination_reason": str(termination_reason),
                "model_rounds": int(model_rounds),
                "capability_names": list(capability_names),
            }
        )
        completed = Wake.model_validate(
            {
                **running.model_dump(mode="python", round_trip=True),
                "revision": running.revision + 1,
                "occurred": TemporalExtent.point(completed_at),
                "learned_at": completed_at,
                "recorded_at": completed_at,
                "wake_state": WakeState.COMPLETED,
                "last_hit_at": running.last_hit_at,
                "status": WakeState.COMPLETED.value,
                "metadata": metadata,
            }
        )
        result = self.store.commit(
            [completed],
            OperationRequest(
                operation_name="wake.dispatch.complete",
                arguments={
                    "wake_id": completed.object_id,
                    "revision": completed.revision,
                    "termination_reason": str(termination_reason),
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="record completion of resident-model wake execution",
                idempotency_key=(
                    f"wake-dispatch-complete:{completed.object_id}:{completed.revision}"
                ),
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.WAKE_DISPATCH,
            ),
        )
        self._catch_up()
        return WakeDispatchReceipt(
            wake_id=completed.object_id,
            revision=completed.revision,
            state=completed.wake_state.value,
            world_revision=result.world_revision,
        )
