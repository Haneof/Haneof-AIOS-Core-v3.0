"""Constitutional C09 Wake Bus for AIOS v3.0.

The bus is deliberately mechanical. It may decide that a registered signal is worth
waking the resident model, merge repeated hits, apply cooldown/suppression, and move
Wake objects through their lifecycle. It must not infer user emotion, intent,
relationships, life events, or any other high-level meaning.

Semantic interpretation belongs to the resident CognitiveRuntime after dispatch.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import (
    MaintenanceClass,
    ObjectType,
    SourceClass,
    WakeSource,
    WakeState,
)
from aios_core.contracts.models import Wake
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore


Step0State = Literal["ok", "quiet", "hard_block"]


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


class WakeSignalRequest(BaseModel):
    """A deterministic trigger hit that may become a durable Wake.

    The request carries routing facts only. It intentionally has no field such as
    "meaning", "emotion", "user_intent", or "diagnosis".
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    wake_source: WakeSource
    rule_id: str = Field(min_length=1)
    observed_at: datetime
    evidence_refs: tuple[ObjectRef, ...] = ()
    priority: int = Field(default=50, ge=0, le=100)
    dedupe_key: str = Field(min_length=1)
    cooldown_seconds: int = Field(default=0, ge=0)
    metadata: Mapping[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_signal(self) -> "WakeSignalRequest":
        as_utc(self.observed_at, "observed_at")
        if not self.rule_id.strip():
            raise ValueError("rule_id must not be blank")
        if not self.dedupe_key.strip():
            raise ValueError("dedupe_key must not be blank")
        if any(ref.revision is None for ref in self.evidence_refs):
            raise ValueError("evidence_refs must pin exact revisions")
        return self


class Step0GateInput(BaseModel):
    """Deterministic pre-cognition gate inputs.

    The gate does not decide semantic importance. It only carries already-known
    physical/runtime facts such as availability, channel legality, budget, and
    whether a mandatory safety action has happened before model invocation.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    convenience_allowed: bool = True
    channel_allowed: bool = True
    budget_available: bool = True
    hard_blocked: bool = False
    safety_action_complete: bool = True
    reasons: tuple[str, ...] = ()


class Step0GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Step0State
    model_allowed: bool
    delivery_allowed: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WakeSignalReceipt:
    wake_id: str
    revision: int
    state: str
    world_revision: int
    merged: bool = False
    suppressed: bool = False


@dataclass(frozen=True, slots=True)
class WakeStateReceipt:
    wake_id: str
    revision: int
    state: str
    world_revision: int


class WakeBus:
    """Mechanical Wake creation, merge/cooldown, and lifecycle service."""

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

    def _validate_refs(self, refs: tuple[ObjectRef, ...]) -> None:
        for ref in refs:
            if ref.revision is None:
                raise ValueError("Wake evidence refs must pin exact revisions")
            self.store.get_payload(ref.object_id, revision=ref.revision)

    def _current_wakes(self) -> tuple[Wake, ...]:
        return tuple(
            Wake.model_validate(payload)
            for payload in self.store.list_payloads(
                object_type=ObjectType.WAKE,
                subject_id=self.subject_id,
            )
        )

    def current_wake(self, wake_id: str) -> Wake:
        wake = Wake.model_validate(self.store.get_payload(wake_id))
        if wake.subject_id != self.subject_id:
            raise ValueError("Wake belongs to another subject")
        return wake

    def pending_wakes(self) -> tuple[Wake, ...]:
        pending = [
            wake
            for wake in self._current_wakes()
            if wake.wake_state in {WakeState.NEW, WakeState.QUEUED}
        ]
        pending.sort(
            key=lambda wake: (
                -wake.priority,
                as_utc(wake.first_hit_at, "first_hit_at"),
                wake.object_id,
            )
        )
        return tuple(pending)

    @staticmethod
    def evaluate_step0(
        wake: Wake,
        gate: Step0GateInput | None = None,
    ) -> Step0GateResult:
        value = gate or Step0GateInput()
        reasons = [item.strip() for item in value.reasons if item.strip()]
        model_allowed = True
        delivery_allowed = True
        state: Step0State = "ok"

        if wake.wake_source is WakeSource.SAFETY and not value.safety_action_complete:
            state = "hard_block"
            model_allowed = False
            delivery_allowed = False
            reasons.append("required_pre_model_safety_action_not_complete")

        if value.hard_blocked:
            state = "hard_block"
            delivery_allowed = False
            reasons.append("mechanical_hard_block")

        if not value.channel_allowed:
            state = "hard_block"
            delivery_allowed = False
            reasons.append("delivery_channel_not_allowed")

        if not value.budget_available:
            state = "hard_block"
            model_allowed = False
            delivery_allowed = False
            reasons.append("model_budget_unavailable")
        elif state == "ok" and not value.convenience_allowed:
            state = "quiet"
            delivery_allowed = False
            reasons.append("user_context_not_convenient_for_delivery")

        return Step0GateResult(
            state=state,
            model_allowed=model_allowed,
            delivery_allowed=delivery_allowed,
            reasons=tuple(dict.fromkeys(reasons)),
        )

    def emit(self, request: WakeSignalRequest) -> WakeSignalReceipt:
        """Create or mechanically merge one registered trigger hit."""

        moment = as_utc(request.observed_at, "observed_at")
        refs = tuple(request.evidence_refs)
        self._validate_refs(refs)

        same_key = [
            wake
            for wake in self._current_wakes()
            if wake.dedupe_key == request.dedupe_key
        ]
        same_key.sort(key=lambda wake: as_utc(wake.last_hit_at, "last_hit_at"))
        latest = same_key[-1] if same_key else None

        # A queued/new Wake represents the same continuous pending situation. Merge
        # hits into that one durable object rather than flooding the resident model.
        if latest is not None and latest.wake_state in {
            WakeState.NEW,
            WakeState.QUEUED,
        }:
            last = as_utc(latest.last_hit_at, "last_hit_at")
            if moment < last:
                raise ValueError("out-of-order Wake hit for existing dedupe_key")

            merged_refs = list(latest.evidence_refs)
            for ref in refs:
                if ref not in merged_refs:
                    merged_refs.append(ref)

            revision = latest.revision + 1
            metadata = dict(latest.metadata)
            metadata.update(dict(request.metadata))
            metadata["last_merge_at"] = moment.isoformat()
            metadata["merged_hit_count"] = latest.hit_count + 1

            merged = Wake.model_validate(
                {
                    **latest.model_dump(mode="python", round_trip=True),
                    "revision": revision,
                    "occurred": TemporalExtent.point(moment),
                    "learned_at": moment,
                    "recorded_at": moment,
                    "last_hit_at": moment,
                    "hit_count": latest.hit_count + 1,
                    "priority": max(latest.priority, request.priority),
                    "evidence_refs": merged_refs,
                    "source_refs": [
                        SourceRef(object_id=ref.object_id, revision=ref.revision)
                        for ref in merged_refs
                    ],
                    "metadata": metadata,
                }
            )
            result = self.store.commit(
                [merged],
                OperationRequest(
                    operation_name="wake.signal.merge",
                    arguments={
                        "wake_id": latest.object_id,
                        "revision": revision,
                        "dedupe_key": request.dedupe_key,
                    },
                    expected_world_revision=int(self.store.current_world_revision()),
                    reason="merge repeated deterministic Wake trigger",
                    idempotency_key=f"wake-merge:{latest.object_id}:{revision}",
                    source_class=SourceClass.MAINTENANCE,
                    maintenance_class=MaintenanceClass.WAKE_SCHEDULER,
                ),
            )
            self._catch_up()
            return WakeSignalReceipt(
                wake_id=merged.object_id,
                revision=revision,
                state=merged.wake_state.value,
                world_revision=result.world_revision,
                merged=True,
            )

        # Cooldown is an engineering scheduling rule. It suppresses another model
        # invocation, but it does not claim anything about what the signal means.
        if (
            latest is not None
            and request.cooldown_seconds > 0
            and latest.wake_state
            in {
                WakeState.COMPLETED,
                WakeState.SUPPRESSED,
                WakeState.CANCELLED,
            }
        ):
            elapsed = moment - as_utc(latest.last_hit_at, "last_hit_at")
            if elapsed < timedelta(seconds=request.cooldown_seconds):
                wake_id = _stable_id(
                    "wake_suppressed",
                    self.subject_id,
                    request.wake_source.value,
                    request.rule_id,
                    request.dedupe_key,
                    moment.isoformat(),
                )
                suppressed = Wake(
                    object_id=wake_id,
                    subject_id=self.subject_id,
                    occurred=TemporalExtent.point(moment),
                    learned_at=moment,
                    recorded_at=moment,
                    source_refs=[
                        SourceRef(object_id=ref.object_id, revision=ref.revision)
                        for ref in refs
                    ],
                    created_by="wake_bus:cooldown",
                    wake_source=request.wake_source,
                    wake_state=WakeState.SUPPRESSED,
                    rule_id=request.rule_id.strip(),
                    first_hit_at=moment,
                    last_hit_at=moment,
                    hit_count=1,
                    evidence_refs=list(refs),
                    priority=request.priority,
                    dedupe_key=request.dedupe_key.strip(),
                    status=WakeState.SUPPRESSED.value,
                    metadata={
                        **dict(request.metadata),
                        "suppression_reason": "cooldown",
                        "cooldown_seconds": request.cooldown_seconds,
                        "previous_wake_ref": {
                            "object_id": latest.object_id,
                            "revision": latest.revision,
                        },
                    },
                )
                result = self.store.commit(
                    [suppressed],
                    OperationRequest(
                        operation_name="wake.signal.suppress_cooldown",
                        arguments={
                            "wake_id": wake_id,
                            "dedupe_key": request.dedupe_key,
                        },
                        expected_world_revision=int(self.store.current_world_revision()),
                        reason="suppress repeated Wake during deterministic cooldown",
                        idempotency_key=f"wake-suppress:{wake_id}",
                        source_class=SourceClass.MAINTENANCE,
                        maintenance_class=MaintenanceClass.WAKE_SCHEDULER,
                    ),
                )
                self._catch_up()
                return WakeSignalReceipt(
                    wake_id=wake_id,
                    revision=1,
                    state=WakeState.SUPPRESSED.value,
                    world_revision=result.world_revision,
                    suppressed=True,
                )

        wake_id = _stable_id(
            "wake",
            self.subject_id,
            request.wake_source.value,
            request.rule_id,
            request.dedupe_key,
            moment.isoformat(),
        )
        wake = Wake(
            object_id=wake_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(moment),
            learned_at=moment,
            recorded_at=moment,
            source_refs=[
                SourceRef(object_id=ref.object_id, revision=ref.revision)
                for ref in refs
            ],
            created_by="wake_bus:trigger",
            wake_source=request.wake_source,
            wake_state=WakeState.NEW,
            rule_id=request.rule_id.strip(),
            first_hit_at=moment,
            last_hit_at=moment,
            hit_count=1,
            evidence_refs=list(refs),
            priority=request.priority,
            dedupe_key=request.dedupe_key.strip(),
            status=WakeState.NEW.value,
            metadata=dict(request.metadata),
        )
        result = self.store.commit(
            [wake],
            OperationRequest(
                operation_name="wake.signal.create",
                arguments={
                    "wake_id": wake_id,
                    "wake_source": request.wake_source.value,
                    "rule_id": request.rule_id,
                    "dedupe_key": request.dedupe_key,
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="registered deterministic trigger requested Resident attention",
                idempotency_key=f"wake-create:{wake_id}",
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.WAKE_SCHEDULER,
            ),
        )
        self._catch_up()
        return WakeSignalReceipt(
            wake_id=wake_id,
            revision=1,
            state=WakeState.NEW.value,
            world_revision=result.world_revision,
        )

    def claim(
        self,
        wake_id: str,
        *,
        started_at: datetime,
    ) -> WakeStateReceipt:
        moment = as_utc(started_at, "started_at")
        wake = self.current_wake(wake_id)

        if wake.wake_state is WakeState.RUNNING:
            return WakeStateReceipt(
                wake_id=wake.object_id,
                revision=wake.revision,
                state=wake.wake_state.value,
                world_revision=int(self.store.current_world_revision()),
            )
        if wake.wake_state not in {WakeState.NEW, WakeState.QUEUED}:
            raise ValueError("only NEW/QUEUED Wake may be claimed")

        revision = wake.revision + 1
        metadata = dict(wake.metadata)
        metadata["started_at"] = moment.isoformat()
        running = Wake.model_validate(
            {
                **wake.model_dump(mode="python", round_trip=True),
                "revision": revision,
                "occurred": TemporalExtent.point(moment),
                "learned_at": moment,
                "recorded_at": moment,
                "wake_state": WakeState.RUNNING,
                "status": WakeState.RUNNING.value,
                "metadata": metadata,
            }
        )
        result = self.store.commit(
            [running],
            OperationRequest(
                operation_name="wake.dispatch.claim",
                arguments={"wake_id": wake.object_id, "revision": revision},
                expected_world_revision=int(self.store.current_world_revision()),
                reason="claim Wake for Resident CognitiveRuntime dispatch",
                idempotency_key=f"wake-claim:{wake.object_id}:{revision}",
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.WAKE_SCHEDULER,
            ),
        )
        self._catch_up()
        return WakeStateReceipt(
            wake_id=running.object_id,
            revision=revision,
            state=WakeState.RUNNING.value,
            world_revision=result.world_revision,
        )

    def _finish(
        self,
        wake_id: str,
        *,
        finished_at: datetime,
        target_state: WakeState,
        metadata_update: Mapping[str, Any],
        reason: str,
    ) -> WakeStateReceipt:
        moment = as_utc(finished_at, "finished_at")
        wake = self.current_wake(wake_id)

        if wake.wake_state is target_state:
            return WakeStateReceipt(
                wake_id=wake.object_id,
                revision=wake.revision,
                state=wake.wake_state.value,
                world_revision=int(self.store.current_world_revision()),
            )
        if wake.wake_state not in {
            WakeState.NEW,
            WakeState.QUEUED,
            WakeState.RUNNING,
        }:
            raise ValueError("Wake is already terminal")

        revision = wake.revision + 1
        metadata = dict(wake.metadata)
        metadata.update(dict(metadata_update))
        terminal = Wake.model_validate(
            {
                **wake.model_dump(mode="python", round_trip=True),
                "revision": revision,
                "occurred": TemporalExtent.point(moment),
                "learned_at": moment,
                "recorded_at": moment,
                "wake_state": target_state,
                "status": target_state.value,
                "metadata": metadata,
            }
        )
        result = self.store.commit(
            [terminal],
            OperationRequest(
                operation_name=f"wake.dispatch.{target_state.value}",
                arguments={"wake_id": wake.object_id, "revision": revision},
                expected_world_revision=int(self.store.current_world_revision()),
                reason=reason,
                idempotency_key=(
                    f"wake-finish:{wake.object_id}:{revision}:{target_state.value}"
                ),
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.WAKE_SCHEDULER,
            ),
        )
        self._catch_up()
        return WakeStateReceipt(
            wake_id=terminal.object_id,
            revision=revision,
            state=target_state.value,
            world_revision=result.world_revision,
        )

    def complete(
        self,
        wake_id: str,
        *,
        completed_at: datetime,
        termination_reason: str,
        model_rounds: int,
        capability_names: tuple[str, ...] = (),
        delivery_allowed: bool,
        step0_state: Step0State,
    ) -> WakeStateReceipt:
        return self._finish(
            wake_id,
            finished_at=completed_at,
            target_state=WakeState.COMPLETED,
            metadata_update={
                "completed_at": as_utc(completed_at, "completed_at").isoformat(),
                "termination_reason": termination_reason,
                "model_rounds": int(model_rounds),
                "capability_names": list(capability_names),
                "delivery_allowed": bool(delivery_allowed),
                "step0_state": step0_state,
            },
            reason="complete Resident Wake dispatch",
        )

    def suppress(
        self,
        wake_id: str,
        *,
        suppressed_at: datetime,
        step0: Step0GateResult,
    ) -> WakeStateReceipt:
        return self._finish(
            wake_id,
            finished_at=suppressed_at,
            target_state=WakeState.SUPPRESSED,
            metadata_update={
                "suppressed_at": as_utc(
                    suppressed_at,
                    "suppressed_at",
                ).isoformat(),
                "suppression_reason": "step0_model_block",
                "step0_state": step0.state,
                "step0_reasons": list(step0.reasons),
            },
            reason="Step-0 blocked Resident model dispatch",
        )
