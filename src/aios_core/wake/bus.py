"""Article-82 mechanical Wake routing for AIOS v3.0.

The router is deliberately non-semantic. A registered mechanical detector supplies
an explicit hit, rule id, evidence refs and dedupe key. The router may then perform
only deterministic scheduling work: idempotency, merge-window dedupe, cooldown and
finite suppression. It never infers emotion, intent, relationship meaning or event
semantics from observations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from aios_core.contracts.enums import (
    MaintenanceClass,
    ObjectType,
    SourceClass,
    WakeSource,
    WakeState,
)
from aios_core.contracts.models import Dependency, Wake
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore


MECHANICAL_WAKE_SOURCES: frozenset[WakeSource] = frozenset(
    {
        WakeSource.MECHANICAL_CHANGE,
        WakeSource.KEYWORD_ENTITY,
        WakeSource.NO_UPDATE,
        WakeSource.WATCH_MATCH,
    }
)


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _hit_digest(hit: "MechanicalWakeHit") -> str:
    raw = canonical_json_dumps(
        {
            "hit_id": hit.hit_id,
            "wake_source": hit.wake_source.value,
            "rule_id": hit.rule_id,
            "occurred_at": hit.occurred_at.isoformat(),
            "evidence_refs": [
                {"object_id": ref.object_id, "revision": ref.revision}
                for ref in hit.evidence_refs
            ],
            "priority": hit.priority,
            "dedupe_key": hit.dedupe_key,
            "metadata": hit.metadata,
        }
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class MechanicalWakeRoutingPolicy(BaseModel):
    """Deterministic scheduling parameters, never cognitive meaning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    merge_window_seconds: FiniteFloat = Field(default=300.0, ge=0.0)
    cooldown_seconds: FiniteFloat = Field(default=0.0, ge=0.0)
    suppress_until: datetime | None = None
    suppression_reason: str | None = None
    suppression_scope: str | None = None
    reactivation_condition: str | None = None

    @model_validator(mode="after")
    def validate_policy(self) -> "MechanicalWakeRoutingPolicy":
        if self.suppress_until is not None:
            as_utc(self.suppress_until, "suppress_until")
            fields = (
                self.suppression_reason,
                self.suppression_scope,
                self.reactivation_condition,
            )
            if any(value is None or not str(value).strip() for value in fields):
                raise ValueError(
                    "finite suppression requires reason, scope and reactivation_condition"
                )
        return self


class MechanicalWakeHit(BaseModel):
    """One already-detected mechanical trigger hit.

    The caller owns detection. This contract prevents the Wake router from quietly
    becoming a second semantic brain.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    hit_id: str = Field(min_length=1)
    wake_source: WakeSource
    rule_id: str = Field(min_length=1)
    occurred_at: datetime
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    priority: int = Field(default=50, ge=0, le=100)
    dedupe_key: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_hit(self) -> "MechanicalWakeHit":
        if self.wake_source not in MECHANICAL_WAKE_SOURCES:
            raise ValueError("mechanical router accepts only registered mechanical sources")
        as_utc(self.occurred_at, "occurred_at")
        if not self.hit_id.strip() or not self.rule_id.strip() or not self.dedupe_key.strip():
            raise ValueError("hit_id/rule_id/dedupe_key must not be blank")
        if any(ref.revision is None for ref in self.evidence_refs):
            raise ValueError("mechanical wake evidence refs must pin exact revisions")
        return self


@dataclass(frozen=True, slots=True)
class WakeRoutingReceipt:
    wake_id: str
    revision: int
    state: str
    world_revision: int
    merged: bool = False
    suppressed: bool = False
    idempotent_replay: bool = False


class MechanicalWakeRouter:
    """Deterministic Article-82 Wake creation/merge/cooldown service."""

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

    def _current_wakes(self) -> tuple[Wake, ...]:
        wakes = [
            Wake.model_validate(payload)
            for payload in self.store.list_payloads(
                object_type=ObjectType.WAKE,
                subject_id=self.subject_id,
            )
        ]
        wakes.sort(
            key=lambda item: (
                as_utc(item.last_hit_at, "last_hit_at"),
                item.object_id,
            )
        )
        return tuple(wakes)

    @staticmethod
    def _hit_digests(wake: Wake) -> dict[str, str]:
        raw = wake.metadata.get("mechanical_hit_digests", {})
        if not isinstance(raw, Mapping):
            return {}
        return {str(key): str(value) for key, value in raw.items()}

    def _idempotent_receipt(
        self,
        *,
        hit: MechanicalWakeHit,
        digest: str,
        wakes: tuple[Wake, ...],
    ) -> WakeRoutingReceipt | None:
        for wake in reversed(wakes):
            digests = self._hit_digests(wake)
            if hit.hit_id not in digests:
                continue
            if digests[hit.hit_id] != digest:
                raise ValueError(
                    "mechanical hit identity conflict: same hit_id has different payload"
                )
            return WakeRoutingReceipt(
                wake_id=wake.object_id,
                revision=wake.revision,
                state=wake.wake_state.value,
                world_revision=int(self.store.current_world_revision()),
                merged=bool(wake.metadata.get("mechanical_merged", False)),
                suppressed=wake.wake_state is WakeState.SUPPRESSED,
                idempotent_replay=True,
            )
        return None

    @staticmethod
    def _matching_wakes(
        wakes: tuple[Wake, ...],
        hit: MechanicalWakeHit,
    ) -> list[Wake]:
        return [
            wake
            for wake in wakes
            if wake.wake_source is hit.wake_source
            and wake.dedupe_key == hit.dedupe_key
        ]

    @staticmethod
    def _source_refs(refs: tuple[ObjectRef, ...]) -> list[SourceRef]:
        return [
            SourceRef(object_id=ref.object_id, revision=ref.revision)
            for ref in refs
        ]

    @staticmethod
    def _merge_refs(
        existing: tuple[ObjectRef, ...] | list[ObjectRef],
        incoming: tuple[ObjectRef, ...],
    ) -> list[ObjectRef]:
        merged: list[ObjectRef] = list(existing)
        seen = {(ref.object_id, ref.revision) for ref in merged}
        for ref in incoming:
            key = (ref.object_id, ref.revision)
            if key not in seen:
                merged.append(ref)
                seen.add(key)
        return merged

    def _dependencies(
        self,
        *,
        wake: Wake,
    ) -> list[Dependency]:
        wake_ref = ObjectRef(object_id=wake.object_id, revision=wake.revision)
        return [
            Dependency(
                object_id=_stable_id(
                    "dep_wake_trigger",
                    wake.object_id,
                    wake.revision,
                    ref.object_id,
                    ref.revision,
                ),
                subject_id=self.subject_id,
                learned_at=wake.recorded_at,
                recorded_at=wake.recorded_at,
                created_by="wake_router:dependency",
                dependent_ref=wake_ref,
                dependency_ref=ref,
                dependency_type="wake_triggered_by",
            )
            for ref in wake.evidence_refs
        ]

    def _commit(
        self,
        *,
        wake: Wake,
        operation_name: str,
        reason: str,
        hit: MechanicalWakeHit,
    ) -> WakeRoutingReceipt:
        result = self.store.commit(
            [wake, *self._dependencies(wake=wake)],
            OperationRequest(
                operation_name=operation_name,
                arguments={
                    "wake_id": wake.object_id,
                    "revision": wake.revision,
                    "wake_source": wake.wake_source.value,
                    "rule_id": wake.rule_id,
                    "hit_id": hit.hit_id,
                    "dedupe_key": wake.dedupe_key,
                    "state": wake.wake_state.value,
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason=reason,
                idempotency_key=(
                    f"{operation_name}:{wake.object_id}:{wake.revision}:{hit.hit_id}"
                ),
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.WAKE_ROUTING,
            ),
        )
        self._catch_up()
        return WakeRoutingReceipt(
            wake_id=wake.object_id,
            revision=wake.revision,
            state=wake.wake_state.value,
            world_revision=result.world_revision,
            merged=bool(wake.metadata.get("mechanical_merged", False)),
            suppressed=wake.wake_state is WakeState.SUPPRESSED,
        )

    def route(
        self,
        hit: MechanicalWakeHit,
        *,
        policy: MechanicalWakeRoutingPolicy | None = None,
    ) -> WakeRoutingReceipt:
        hit = MechanicalWakeHit.model_validate(
            hit.model_dump(mode="python", round_trip=True)
        )
        policy = policy or MechanicalWakeRoutingPolicy()
        policy = MechanicalWakeRoutingPolicy.model_validate(
            policy.model_dump(mode="python", round_trip=True)
        )
        moment = as_utc(hit.occurred_at, "occurred_at")
        digest = _hit_digest(hit)
        wakes = self._current_wakes()

        replay = self._idempotent_receipt(
            hit=hit,
            digest=digest,
            wakes=wakes,
        )
        if replay is not None:
            return replay

        matches = self._matching_wakes(wakes, hit)
        latest = matches[-1] if matches else None
        if latest is not None and moment < as_utc(latest.last_hit_at, "last_hit_at"):
            raise ValueError("mechanical hit time cannot move backward within dedupe context")

        # Finite registered suppression is deterministic and fully audited.
        if (
            policy.suppress_until is not None
            and moment < as_utc(policy.suppress_until, "suppress_until")
        ):
            return self._create_new(
                hit=hit,
                policy=policy,
                state=WakeState.SUPPRESSED,
                suppression={
                    "kind": "registered_finite_suppression",
                    "reason": policy.suppression_reason,
                    "scope": policy.suppression_scope,
                    "until": as_utc(
                        policy.suppress_until,
                        "suppress_until",
                    ).isoformat(),
                    "reactivation_condition": policy.reactivation_condition,
                },
            )

        # Pending hits in one continuous mechanical context become one Wake.
        if latest is not None and latest.wake_state in {
            WakeState.NEW,
            WakeState.QUEUED,
        }:
            gap = moment - as_utc(latest.last_hit_at, "last_hit_at")
            if gap <= timedelta(seconds=float(policy.merge_window_seconds)):
                return self._merge(
                    current=latest,
                    hit=hit,
                    policy=policy,
                    digest=digest,
                )

        # A completed Wake may establish a mechanical cooldown. We preserve the
        # suppressed attempt as its own auditable Wake rather than dropping evidence.
        completed = next(
            (
                wake
                for wake in reversed(matches)
                if wake.wake_state is WakeState.COMPLETED
            ),
            None,
        )
        if completed is not None and float(policy.cooldown_seconds) > 0.0:
            gap = moment - as_utc(completed.last_hit_at, "last_hit_at")
            if gap < timedelta(seconds=float(policy.cooldown_seconds)):
                return self._create_new(
                    hit=hit,
                    policy=policy,
                    state=WakeState.SUPPRESSED,
                    suppression={
                        "kind": "cooldown",
                        "suppressed_by": {
                            "object_id": completed.object_id,
                            "revision": completed.revision,
                        },
                        "cooldown_seconds": float(policy.cooldown_seconds),
                    },
                )

        return self._create_new(
            hit=hit,
            policy=policy,
            state=WakeState.NEW,
            suppression=None,
        )

    def _base_metadata(
        self,
        *,
        hit: MechanicalWakeHit,
        policy: MechanicalWakeRoutingPolicy,
        digest: str,
    ) -> dict[str, Any]:
        return {
            "mechanical_router": True,
            "mechanical_hit_ids": [hit.hit_id],
            "mechanical_hit_digests": {hit.hit_id: digest},
            "latest_hit_metadata": dict(hit.metadata),
            "routing_policy": {
                "merge_window_seconds": float(policy.merge_window_seconds),
                "cooldown_seconds": float(policy.cooldown_seconds),
            },
        }

    def _create_new(
        self,
        *,
        hit: MechanicalWakeHit,
        policy: MechanicalWakeRoutingPolicy,
        state: WakeState,
        suppression: Mapping[str, Any] | None,
    ) -> WakeRoutingReceipt:
        moment = as_utc(hit.occurred_at, "occurred_at")
        digest = _hit_digest(hit)
        wake_id = _stable_id(
            "wake_mechanical",
            self.subject_id,
            hit.wake_source.value,
            hit.rule_id,
            hit.dedupe_key,
            hit.hit_id,
        )
        metadata = self._base_metadata(
            hit=hit,
            policy=policy,
            digest=digest,
        )
        if suppression is not None:
            metadata["suppression"] = dict(suppression)
        wake = Wake(
            object_id=wake_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(moment),
            learned_at=moment,
            recorded_at=moment,
            source_refs=self._source_refs(hit.evidence_refs),
            created_by="wake_router:mechanical",
            wake_source=hit.wake_source,
            wake_state=state,
            rule_id=hit.rule_id,
            first_hit_at=moment,
            last_hit_at=moment,
            hit_count=1,
            evidence_refs=list(hit.evidence_refs),
            priority=hit.priority,
            dedupe_key=hit.dedupe_key,
            status=state.value,
            metadata=metadata,
        )
        return self._commit(
            wake=wake,
            operation_name="wake.route.create",
            reason=(
                "record mechanically detected wake hit"
                if state is WakeState.NEW
                else "record mechanically suppressed wake hit"
            ),
            hit=hit,
        )

    def _merge(
        self,
        *,
        current: Wake,
        hit: MechanicalWakeHit,
        policy: MechanicalWakeRoutingPolicy,
        digest: str,
    ) -> WakeRoutingReceipt:
        moment = as_utc(hit.occurred_at, "occurred_at")
        evidence = self._merge_refs(tuple(current.evidence_refs), hit.evidence_refs)
        metadata = dict(current.metadata)
        hit_ids = list(metadata.get("mechanical_hit_ids", []))
        hit_ids.append(hit.hit_id)
        digests = self._hit_digests(current)
        digests[hit.hit_id] = digest
        metadata.update(
            {
                "mechanical_hit_ids": hit_ids,
                "mechanical_hit_digests": digests,
                "latest_hit_metadata": dict(hit.metadata),
                "mechanical_merged": True,
                "routing_policy": {
                    "merge_window_seconds": float(policy.merge_window_seconds),
                    "cooldown_seconds": float(policy.cooldown_seconds),
                },
            }
        )
        merged = Wake.model_validate(
            {
                **current.model_dump(mode="python", round_trip=True),
                "revision": current.revision + 1,
                "occurred": TemporalExtent.point(moment),
                "learned_at": moment,
                "recorded_at": moment,
                "source_refs": self._source_refs(tuple(evidence)),
                "last_hit_at": moment,
                "hit_count": current.hit_count + 1,
                "evidence_refs": evidence,
                "priority": max(current.priority, hit.priority),
                "metadata": metadata,
            }
        )
        return self._commit(
            wake=merged,
            operation_name="wake.route.merge",
            reason="merge repeated mechanical hit into pending Wake",
            hit=hit,
        )
