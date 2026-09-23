"""Resident-AI Event Dimension writeback over the unified world.

An Event is a revisable observation axis formed by the resident model from pinned
world evidence. The deterministic service never decides that an event happened; it
only validates provenance, identity and legal forward lifecycle transitions.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import EventStatus, SourceClass
from aios_core.contracts.models import Dependency, EventAnchor, EvidenceCoverage, EvidenceSet
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import KnowledgeWindow, TemporalExtent, as_utc
from aios_core.revision.propagation import plan_invalidation
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore

EVENT_DIMENSION = "dim:events"

_EVENT_TRANSITIONS: dict[EventStatus, frozenset[EventStatus]] = {
    EventStatus.CANDIDATE: frozenset({
        EventStatus.ACTIVE,
        EventStatus.REVISED,
        EventStatus.REJECTED,
        EventStatus.MERGED,
        EventStatus.SPLIT,
    }),
    EventStatus.ACTIVE: frozenset({
        EventStatus.RESOLVED,
        EventStatus.REVISED,
        EventStatus.REJECTED,
        EventStatus.MERGED,
        EventStatus.SPLIT,
    }),
    EventStatus.REVISED: frozenset({
        EventStatus.ACTIVE,
        EventStatus.RESOLVED,
        EventStatus.REVISED,
        EventStatus.REJECTED,
        EventStatus.MERGED,
        EventStatus.SPLIT,
    }),
    # A resolved/rejected interpretation may be reopened only through an explicit
    # REVISED revision carrying new evidence; terminal structural operations stay terminal.
    EventStatus.RESOLVED: frozenset({EventStatus.REVISED}),
    EventStatus.REJECTED: frozenset({EventStatus.REVISED}),
    EventStatus.MERGED: frozenset(),
    EventStatus.SPLIT: frozenset(),
}


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _require_pinned(refs: Sequence[ObjectRef], label: str) -> None:
    for ref in refs:
        if ref.revision is None:
            raise ValueError(f"{label} must pin exact revisions")


class EventWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1)
    interpretation: str = Field(min_length=1)
    event_time: TemporalExtent
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    participant_refs: tuple[ObjectRef, ...] = ()
    primary_claim_refs: tuple[ObjectRef, ...] = ()
    confidence: float = Field(ge=0.0, le=1.0)
    dimension: str = EVENT_DIMENSION

    @model_validator(mode="after")
    def validate_request(self) -> "EventWriteRequest":
        if not self.title.strip() or not self.interpretation.strip():
            raise ValueError("event title/interpretation must not be blank")
        if not self.dimension.strip().startswith("dim:"):
            raise ValueError("event dimension must be explicit and start with 'dim:'")
        _require_pinned(
            (*self.evidence_refs, *self.participant_refs, *self.primary_claim_refs),
            "event references",
        )
        return self


class EventTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_ref: ObjectRef
    new_status: EventStatus
    reason: str = Field(min_length=1)
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    replacement_title: str | None = None
    replacement_interpretation: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    related_event_refs: tuple[ObjectRef, ...] = ()

    @model_validator(mode="after")
    def validate_request(self) -> "EventTransitionRequest":
        _require_pinned((self.event_ref, *self.evidence_refs, *self.related_event_refs), "event transition refs")
        if not self.reason.strip():
            raise ValueError("event transition reason must not be blank")
        if self.new_status is EventStatus.MERGED and len(self.related_event_refs) != 1:
            raise ValueError("MERGED event transition requires exactly one target event ref")
        if self.new_status is EventStatus.SPLIT and not self.related_event_refs:
            raise ValueError("SPLIT event transition requires split child event refs")
        if self.new_status is EventStatus.REVISED:
            if not (self.replacement_title or "").strip() and not (self.replacement_interpretation or "").strip():
                raise ValueError("REVISED event requires replacement title or interpretation")
        return self


@dataclass(frozen=True, slots=True)
class EventWriteReceipt:
    event_id: str
    revision: int
    status: str
    evidence_set_id: str
    world_revision: int


@dataclass(frozen=True, slots=True)
class EventTransitionReceipt:
    event_id: str
    previous_revision: int
    new_revision: int
    previous_status: str
    new_status: str
    evidence_set_id: str
    world_revision: int


class EventDimensionService:
    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex | None = None,
        subject_id: str = "user_1",
        propagation_subject_ids: Sequence[str] | None = None,
    ) -> None:
        self.store = store
        self.index = index
        self.subject_id = subject_id
        self.propagation_subject_ids = tuple(dict.fromkeys((subject_id, *(propagation_subject_ids or ()))))

    def _validate_refs(self, refs: Sequence[ObjectRef]) -> None:
        _require_pinned(refs, "event refs")
        for ref in refs:
            payload = self.store.get_payload(ref.object_id, revision=ref.revision)
            ref_subject = str(payload.get("subject_id") or "")
            if ref_subject != self.subject_id:
                raise ValueError(
                    "event reference crosses the runtime subject scope: "
                    f"{ref.object_id}@{ref.revision} belongs to {ref_subject!r}"
                )

    def _evidence(
        self,
        *,
        event_id: str,
        revision: int,
        refs: Sequence[ObjectRef],
        learned_at: datetime,
        dimension: str,
        purpose: str,
    ) -> EvidenceSet:
        eid = _stable_id(
            "evs_event", event_id, revision,
            tuple((r.object_id, r.revision) for r in refs), learned_at.isoformat(),
        )
        return EvidenceSet(
            object_id=eid,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(learned_at),
            learned_at=learned_at,
            recorded_at=learned_at,
            source_refs=[SourceRef(object_id=r.object_id, revision=r.revision) for r in refs],
            created_by="event_dimension:evidence",
            purpose=purpose,
            knowledge_window=KnowledgeWindow(
                knowledge_cutoff=learned_at,
                world_revision=int(self.store.current_world_revision()),
            ),
            member_refs=list(refs),
            support_refs=list(refs),
            selection_method="resident_model_selected_event_evidence",
            coverage=EvidenceCoverage(
                expected_count=len(refs),
                observed_count=len(refs),
                coverage_ratio=1.0,
            ),
            metadata={"dimension": dimension, "event_id": event_id},
        )

    def _deps(
        self,
        *,
        event_ref: ObjectRef,
        evidence: EvidenceSet,
        source_refs: Sequence[ObjectRef],
        at: datetime,
    ) -> list[Dependency]:
        ev_ref = ObjectRef(object_id=evidence.object_id, revision=1)
        deps = [
            Dependency(
                object_id=_stable_id("dep", event_ref.object_id, event_ref.revision, evidence.object_id, 1),
                subject_id=self.subject_id,
                learned_at=at,
                recorded_at=at,
                created_by="event_dimension:dependency",
                dependent_ref=event_ref,
                dependency_ref=ev_ref,
                dependency_type="event_uses_evidence_set",
            )
        ]
        for ref in source_refs:
            deps.append(
                Dependency(
                    object_id=_stable_id("dep", evidence.object_id, 1, ref.object_id, ref.revision),
                    subject_id=self.subject_id,
                    learned_at=at,
                    recorded_at=at,
                    created_by="event_dimension:dependency",
                    dependent_ref=ev_ref,
                    dependency_ref=ref,
                    dependency_type="event_evidence_set_contains_source",
                )
            )
        return deps

    def form_event(self, request: EventWriteRequest, *, learned_at: datetime) -> EventWriteReceipt:
        learned = as_utc(learned_at, "learned_at")
        refs = tuple(dict.fromkeys((*request.evidence_refs, *request.primary_claim_refs)))
        self._validate_refs((*refs, *request.participant_refs))
        event_id = _stable_id(
            "event", self.subject_id, request.dimension.strip(), request.title.strip(),
            request.event_time.model_dump(mode="json"),
            tuple((r.object_id, r.revision) for r in refs),
        )
        evidence = self._evidence(
            event_id=event_id,
            revision=1,
            refs=refs,
            learned_at=learned,
            dimension=request.dimension.strip(),
            purpose=f"support resident event {request.title.strip()}",
        )
        evidence_ref = ObjectRef(object_id=evidence.object_id, revision=1)
        event = EventAnchor(
            object_id=event_id,
            subject_id=self.subject_id,
            revision=1,
            occurred=request.event_time,
            learned_at=learned,
            recorded_at=learned,
            source_refs=[SourceRef(object_id=r.object_id, revision=r.revision) for r in refs],
            created_by="event_dimension:resident_ai",
            title=request.title.strip(),
            interpretation=request.interpretation.strip(),
            event_status=EventStatus.CANDIDATE,
            event_time=request.event_time,
            participant_refs=list(request.participant_refs),
            primary_claim_refs=list(request.primary_claim_refs),
            evidence_set_refs=[evidence_ref],
            support_evidence_set_refs=[evidence_ref],
            confidence=request.confidence,
            metadata={"dimension": request.dimension.strip()},
        )
        event_ref = ObjectRef(object_id=event_id, revision=1)
        objects = [evidence, event, *self._deps(event_ref=event_ref, evidence=evidence, source_refs=refs, at=learned)]
        result = self.store.commit(
            objects,
            OperationRequest(
                operation_name="event.form",
                arguments={"event_id": event_id, "title": event.title, "dimension": request.dimension},
                expected_world_revision=int(self.store.current_world_revision()),
                reason="resident AI formed evidence-grounded Event candidate",
                idempotency_key=f"event-form:{event_id}:1",
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        if self.index is not None:
            self.index.catch_up()
        return EventWriteReceipt(event_id, 1, event.event_status.value, evidence.object_id, result.world_revision)

    def transition(self, request: EventTransitionRequest, *, changed_at: datetime) -> EventTransitionReceipt:
        changed = as_utc(changed_at, "changed_at")
        expected_world_revision = int(self.store.current_world_revision())
        payload = self.store.get_payload(request.event_ref.object_id, revision=request.event_ref.revision)
        latest = self.store.get_payload(request.event_ref.object_id)
        if int(latest["revision"]) != int(request.event_ref.revision or 0):
            raise ValueError("only the current Event revision may transition")
        current = EventAnchor.model_validate(payload)
        if current.subject_id != self.subject_id:
            raise ValueError("event transition target crosses the runtime subject scope")
        allowed = _EVENT_TRANSITIONS.get(current.event_status, frozenset())
        if request.new_status not in allowed:
            raise ValueError(
                "illegal Event transition: "
                f"{current.event_status.value}->{request.new_status.value}"
            )
        self._validate_refs((*request.evidence_refs, *request.related_event_refs))
        new_revision = current.revision + 1
        dimension = str(current.metadata.get("dimension") or EVENT_DIMENSION)
        evidence = self._evidence(
            event_id=current.object_id,
            revision=new_revision,
            refs=request.evidence_refs,
            learned_at=changed,
            dimension=dimension,
            purpose=f"support event transition {current.object_id}@{current.revision}->{request.new_status.value}",
        )
        evidence_ref = ObjectRef(object_id=evidence.object_id, revision=1)
        data = current.model_dump(mode="python", round_trip=True)
        data.update({
            "revision": new_revision,
            "occurred": current.event_time,
            "learned_at": changed,
            "recorded_at": changed,
            "source_refs": [SourceRef(object_id=r.object_id, revision=r.revision) for r in request.evidence_refs],
            "event_status": request.new_status,
            "evidence_set_refs": [*current.evidence_set_refs, evidence_ref],
            "support_evidence_set_refs": [*current.support_evidence_set_refs, evidence_ref],
            "confidence": current.confidence if request.confidence is None else request.confidence,
            "revision_reason": request.reason.strip(),
            "status": request.new_status.value if request.new_status in {EventStatus.RESOLVED, EventStatus.REJECTED, EventStatus.MERGED, EventStatus.SPLIT} else "active",
        })
        if request.replacement_title is not None and request.replacement_title.strip():
            data["title"] = request.replacement_title.strip()
        if request.replacement_interpretation is not None and request.replacement_interpretation.strip():
            data["interpretation"] = request.replacement_interpretation.strip()
        if request.new_status is EventStatus.REVISED:
            data["supersedes_refs"] = [ObjectRef(object_id=current.object_id, revision=current.revision)]
        if request.new_status is EventStatus.MERGED:
            data["merged_into_ref"] = request.related_event_refs[0]
        if request.new_status is EventStatus.SPLIT:
            data["split_child_refs"] = list(request.related_event_refs)
        new_event = EventAnchor.model_validate(data)
        new_ref = ObjectRef(object_id=new_event.object_id, revision=new_revision)
        deps = self._deps(event_ref=new_ref, evidence=evidence, source_refs=request.evidence_refs, at=changed)
        for ref in request.related_event_refs:
            deps.append(
                Dependency(
                    object_id=_stable_id("dep", new_event.object_id, new_revision, ref.object_id, ref.revision, request.new_status.value),
                    subject_id=self.subject_id,
                    learned_at=changed,
                    recorded_at=changed,
                    created_by="event_dimension:dependency",
                    dependent_ref=new_ref,
                    dependency_ref=ref,
                    dependency_type=f"event_{request.new_status.value}_related_event",
                )
            )
        invalidation = plan_invalidation(
            self.store, changed_ref=request.event_ref, changed_at=changed,
            reason=f"Event {current.object_id}@{current.revision} transitioned to {request.new_status.value}: {request.reason.strip()}",
            subject_ids=self.propagation_subject_ids,
        )
        result = self.store.commit(
            [evidence, new_event, *deps, *invalidation.objects],
            OperationRequest(
                operation_name="event.transition",
                arguments={
                    "event_id": current.object_id,
                    "from": current.event_status.value,
                    "to": request.new_status.value,
                },
                expected_world_revision=expected_world_revision,
                reason=request.reason.strip(),
                idempotency_key=f"event-transition:{current.object_id}:{new_revision}:{request.new_status.value}",
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        if self.index is not None:
            self.index.catch_up()
        return EventTransitionReceipt(
            event_id=current.object_id,
            previous_revision=current.revision,
            new_revision=new_revision,
            previous_status=current.event_status.value,
            new_status=request.new_status.value,
            evidence_set_id=evidence.object_id,
            world_revision=result.world_revision,
        )
