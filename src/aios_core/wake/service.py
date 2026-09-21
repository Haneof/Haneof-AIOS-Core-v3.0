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
    AttentionClass,
    MaintenanceClass,
    ObjectType,
    SourceClass,
    WakeSource,
    WakeState,
)
from aios_core.contracts.models import Observation, Wake
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore


Step0State = Literal["ok", "quiet", "background", "review_queue", "hard_block"]


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
    attention_class: AttentionClass | None = None
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


_OBSERVATION_WAKE_SOURCES = frozenset(
    {
        WakeSource.MECHANICAL_CHANGE,
        WakeSource.KEYWORD_ENTITY,
        WakeSource.WATCH_MATCH,
        WakeSource.RECOVERY,
    }
)


class ObservationWakeRule(BaseModel):
    """Registered deterministic mapping from an Observation marker to a Wake signal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str = Field(min_length=1)
    wake_source: WakeSource
    source_kind: str | None = None
    modality: str | None = None
    metadata_equals: Mapping[str, Any] = Field(default_factory=dict)
    dedupe_metadata_keys: tuple[str, ...] = ()
    priority: int = Field(default=50, ge=0, le=100)
    cooldown_seconds: int = Field(default=0, ge=0)
    attention_class: AttentionClass | None = None
    enabled: bool = True

    @model_validator(mode="after")
    def validate_rule(self) -> "ObservationWakeRule":
        if not self.rule_id.strip():
            raise ValueError("rule_id must not be blank")
        if self.wake_source not in _OBSERVATION_WAKE_SOURCES:
            raise ValueError(
                "ObservationWakeRule supports only registered indirect observation wake sources"
            )
        if self.source_kind is not None and not self.source_kind.strip():
            raise ValueError("source_kind must not be blank")
        if self.modality is not None and not self.modality.strip():
            raise ValueError("modality must not be blank")
        for key in (*self.metadata_equals.keys(), *self.dedupe_metadata_keys):
            if not isinstance(key, str) or not key.strip():
                raise ValueError("metadata rule keys must be non-blank strings")
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
    cognition_allowed: bool = True
    external_action_allowed: bool = True
    user_delivery_allowed: bool = True
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


class ObservationTriggerService:
    """Evaluate registered mechanical Observation rules without semantic inference."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        wake_bus: "WakeBus",
        subject_id: str = "user_1",
    ) -> None:
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must not be blank")
        self.store = store
        self.wake_bus = wake_bus
        self.subject_id = subject_id.strip()

    @staticmethod
    def _matches(observation: Observation, rule: ObservationWakeRule) -> bool:
        if not rule.enabled:
            return False
        if rule.source_kind is not None and observation.source_kind != rule.source_kind:
            return False
        if rule.modality is not None and observation.modality != rule.modality:
            return False
        for key, expected in rule.metadata_equals.items():
            if observation.metadata.get(key) != expected:
                return False
        return True

    def evaluate_observation(
        self,
        observation_ref: ObjectRef,
        *,
        rules: tuple[ObservationWakeRule, ...],
    ) -> tuple[WakeSignalReceipt, ...]:
        """Turn only explicitly matched deterministic markers into Wake signals."""

        if observation_ref.revision is None:
            raise ValueError("observation_ref must pin an exact revision")
        payload = self.store.get_payload(
            observation_ref.object_id,
            revision=observation_ref.revision,
        )
        if payload.get("object_type") != ObjectType.OBSERVATION.value:
            raise ValueError("observation_ref must point to an Observation")
        observation = Observation.model_validate(payload)
        if observation.subject_id != self.subject_id:
            raise ValueError("Observation belongs to another subject")

        receipts: list[WakeSignalReceipt] = []
        for rule in rules:
            if not self._matches(observation, rule):
                continue

            dedupe_values: dict[str, Any] = {}
            for key in rule.dedupe_metadata_keys:
                if key not in observation.metadata:
                    raise ValueError(
                        f"dedupe metadata key missing from Observation: {key}"
                    )
                dedupe_values[key] = observation.metadata[key]

            # Wake time is when AIOS evaluated/recorded the fact, not when the
            # underlying real-world event originally occurred. Historical imports
            # must not fabricate Wakes in the past.
            observed_at = observation.recorded_at
            dedupe_key = _stable_id(
                "observation_wake_scope",
                self.subject_id,
                rule.rule_id,
                observation.source_kind,
                dedupe_values,
            )
            receipts.append(
                self.wake_bus.emit(
                    WakeSignalRequest(
                        wake_source=rule.wake_source,
                        rule_id=rule.rule_id,
                        observed_at=observed_at,
                        evidence_refs=(observation_ref,),
                        priority=rule.priority,
                        dedupe_key=dedupe_key,
                        cooldown_seconds=rule.cooldown_seconds,
                        attention_class=rule.attention_class,
                        metadata={
                            "trigger_kind": "registered_observation_rule",
                            "trigger_rule_id": rule.rule_id,
                            "trigger_observation_ref": observation_ref.model_dump(
                                mode="json"
                            ),
                        },
                    )
                )
            )
        return tuple(receipts)


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
            payload = self.store.get_payload(ref.object_id, revision=ref.revision)
            ref_subject = str(payload.get("subject_id") or "")
            if ref_subject != self.subject_id:
                raise ValueError(
                    "Wake evidence crosses the runtime subject scope: "
                    f"{ref.object_id}@{ref.revision} belongs to {ref_subject!r}"
                )

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
    def default_attention_class(
        wake_source: WakeSource,
        *,
        priority: int = 50,
    ) -> AttentionClass:
        """Mechanical default routing; never a semantic importance judgment."""

        if wake_source in {WakeSource.SAFETY, WakeSource.USER_INTERACTION}:
            return AttentionClass.INTERRUPT
        if wake_source is WakeSource.PERIODIC_REVIEW:
            return AttentionClass.REVIEW_QUEUE
        if wake_source is WakeSource.TASK_DUE and int(priority) >= 80:
            return AttentionClass.INTERRUPT
        return AttentionClass.BACKGROUND

    @classmethod
    def attention_class_for_wake(cls, wake: Wake) -> AttentionClass:
        raw = wake.metadata.get("attention_class")
        if raw is not None:
            try:
                return AttentionClass(str(raw))
            except ValueError:
                pass
        return cls.default_attention_class(
            wake.wake_source,
            priority=wake.priority,
        )

    @classmethod
    def evaluate_step0(
        cls,
        wake: Wake,
        gate: Step0GateInput | None = None,
    ) -> Step0GateResult:
        value = gate or Step0GateInput()
        reasons = [item.strip() for item in value.reasons if item.strip()]
        attention_class = cls.attention_class_for_wake(wake)

        model_allowed = attention_class is not AttentionClass.REVIEW_QUEUE
        action_allowed = bool(value.external_action_allowed)
        delivery_allowed = (
            attention_class is AttentionClass.INTERRUPT
            and bool(value.user_delivery_allowed)
        )

        if attention_class is AttentionClass.REVIEW_QUEUE:
            state: Step0State = "review_queue"
            action_allowed = False
            delivery_allowed = False
            reasons.append("queued_for_periodic_review")
        elif attention_class is AttentionClass.BACKGROUND:
            state = "background"
            delivery_allowed = False
            reasons.append("background_attention_no_user_interrupt")
        else:
            state = "ok"

        if wake.wake_source is WakeSource.SAFETY and not value.safety_action_complete:
            state = "hard_block"
            model_allowed = False
            action_allowed = False
            delivery_allowed = False
            reasons.append("required_pre_model_safety_action_not_complete")

        if value.hard_blocked:
            state = "hard_block"
            action_allowed = False
            delivery_allowed = False
            reasons.append("mechanical_hard_block")

        if not value.channel_allowed:
            delivery_allowed = False
            reasons.append("delivery_channel_not_allowed")
            if state == "ok":
                state = "quiet"

        if not value.cognition_allowed:
            state = "hard_block"
            model_allowed = False
            action_allowed = False
            delivery_allowed = False
            reasons.append("cognition_not_allowed")

        if not value.budget_available:
            state = "hard_block"
            model_allowed = False
            action_allowed = False
            delivery_allowed = False
            reasons.append("model_budget_unavailable")
        elif not value.convenience_allowed:
            delivery_allowed = False
            reasons.append("user_context_not_convenient_for_delivery")
            if state == "ok":
                state = "quiet"

        if not value.user_delivery_allowed:
            delivery_allowed = False
            reasons.append("user_delivery_not_allowed")
            if state == "ok":
                state = "quiet"

        if not value.external_action_allowed:
            action_allowed = False
            reasons.append("external_action_not_allowed")

        return Step0GateResult(
            state=state,
            model_allowed=model_allowed,
            action_allowed=action_allowed,
            delivery_allowed=delivery_allowed,
            reasons=tuple(dict.fromkeys(reasons)),
        )

    def emit(self, request: WakeSignalRequest) -> WakeSignalReceipt:
        """Create or mechanically merge one registered trigger hit."""

        moment = as_utc(request.observed_at, "observed_at")
        refs = tuple(request.evidence_refs)
        self._validate_refs(refs)

        signal_id = _stable_id(
            "wake_signal",
            self.subject_id,
            request.wake_source.value,
            request.rule_id,
            request.dedupe_key,
            moment.isoformat(),
            [
                {"object_id": ref.object_id, "revision": ref.revision}
                for ref in refs
            ],
            request.priority,
            (
                request.attention_class.value
                if request.attention_class is not None
                else None
            ),
            dict(request.metadata),
        )

        same_scope = [
            wake
            for wake in self._current_wakes()
            if wake.dedupe_key == request.dedupe_key
            and wake.wake_source is request.wake_source
            and wake.rule_id == request.rule_id
        ]
        same_scope.sort(key=lambda wake: as_utc(wake.last_hit_at, "last_hit_at"))
        latest = same_scope[-1] if same_scope else None

        # Exact signal retry is idempotent even if later Wakes in the same scope
        # already exist. Search the full scope history rather than only the newest
        # Wake so a delayed retry cannot become a fresh hit.
        for prior in reversed(same_scope):
            prior_signal_ids = tuple(
                str(item)
                for item in (prior.metadata.get("signal_ids") or ())
            )
            if signal_id in prior_signal_ids:
                return WakeSignalReceipt(
                    wake_id=prior.object_id,
                    revision=prior.revision,
                    state=prior.wake_state.value,
                    world_revision=int(self.store.current_world_revision()),
                )

        if latest is not None and moment < as_utc(
            latest.last_hit_at,
            "last_hit_at",
        ):
            raise ValueError("out-of-order Wake hit for existing trigger scope")

        # A queued/new Wake represents the same continuous pending situation. Merge
        # hits into that one durable object rather than flooding the resident model.
        if latest is not None and latest.wake_state in {
            WakeState.NEW,
            WakeState.QUEUED,
        }:
            last = as_utc(latest.last_hit_at, "last_hit_at")

            merged_refs = list(latest.evidence_refs)
            for ref in refs:
                if ref not in merged_refs:
                    merged_refs.append(ref)

            revision = latest.revision + 1
            metadata = dict(latest.metadata)
            metadata.update(dict(request.metadata))
            existing_class = self.attention_class_for_wake(latest)
            incoming_class = (
                request.attention_class
                or self.default_attention_class(
                    request.wake_source,
                    priority=request.priority,
                )
            )
            rank = {
                AttentionClass.REVIEW_QUEUE: 0,
                AttentionClass.BACKGROUND: 1,
                AttentionClass.INTERRUPT: 2,
            }
            effective_class = (
                incoming_class
                if rank[incoming_class] > rank[existing_class]
                else existing_class
            )
            metadata["attention_class"] = effective_class.value
            metadata["last_merge_at"] = moment.isoformat()
            metadata["merged_hit_count"] = latest.hit_count + 1
            metadata["signal_ids"] = [
                *tuple(str(item) for item in (latest.metadata.get("signal_ids") or ())),
                signal_id,
            ]

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
                        "attention_class": (
                            request.attention_class
                            or self.default_attention_class(
                                request.wake_source,
                                priority=request.priority,
                            )
                        ).value,
                        "signal_ids": [signal_id],
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
            metadata={
                **dict(request.metadata),
                "attention_class": (
                    request.attention_class
                    or self.default_attention_class(
                        request.wake_source,
                        priority=request.priority,
                    )
                ).value,
                "signal_ids": [signal_id],
            },
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

    def defer(
        self,
        wake_id: str,
        *,
        deferred_at: datetime,
        step0: Step0GateResult,
    ) -> WakeStateReceipt:
        """Keep a Wake pending when Step-0 cannot safely invoke the model yet."""

        moment = as_utc(deferred_at, "deferred_at")
        wake = self.current_wake(wake_id)
        if wake.wake_state is WakeState.QUEUED:
            return WakeStateReceipt(
                wake_id=wake.object_id,
                revision=wake.revision,
                state=wake.wake_state.value,
                world_revision=int(self.store.current_world_revision()),
            )
        if wake.wake_state is not WakeState.NEW:
            raise ValueError("only NEW Wake may be deferred")

        revision = wake.revision + 1
        metadata = dict(wake.metadata)
        metadata.update(
            {
                "deferred_at": moment.isoformat(),
                "step0_state": step0.state,
                "step0_reasons": list(step0.reasons),
            }
        )
        queued = Wake.model_validate(
            {
                **wake.model_dump(mode="python", round_trip=True),
                "revision": revision,
                "occurred": TemporalExtent.point(moment),
                "learned_at": moment,
                "recorded_at": moment,
                "wake_state": WakeState.QUEUED,
                "status": WakeState.QUEUED.value,
                "metadata": metadata,
            }
        )
        result = self.store.commit(
            [queued],
            OperationRequest(
                operation_name="wake.dispatch.defer",
                arguments={"wake_id": wake.object_id, "revision": revision},
                expected_world_revision=int(self.store.current_world_revision()),
                reason="Step-0 deferred Resident model invocation",
                idempotency_key=f"wake-defer:{wake.object_id}:{revision}",
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.WAKE_SCHEDULER,
            ),
        )
        self._catch_up()
        return WakeStateReceipt(
            wake_id=queued.object_id,
            revision=revision,
            state=WakeState.QUEUED.value,
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
