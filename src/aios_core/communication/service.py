"""Evidence-grounded communication experience in the unified AIOS world.

The service records what communication happened and how reality/user feedback reacted.
It never ranks styles or chooses a future speaking style; that judgment remains with the
resident model and, when promoted into an adaptive strategy, the CognitivePolicy layer.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import ObjectType, SourceClass, UserReaction
from aios_core.contracts.models import CommunicationExperience, Dependency
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore

COMMUNICATION_EXPERIENCE_DIMENSION = "dim:ai_communication_experience"


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


class CommunicationExperienceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario: str = Field(min_length=1)
    style: str = Field(min_length=1)
    tone: str | None = None
    user_reaction: UserReaction
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    action_ref: ObjectRef | None = None
    applicable_conditions: dict[str, Any] = Field(default_factory=dict)
    counterexample_refs: tuple[ObjectRef, ...] = ()

    @model_validator(mode="after")
    def validate_request(self) -> "CommunicationExperienceRequest":
        refs = (*self.evidence_refs, *self.counterexample_refs)
        if self.action_ref is not None:
            refs = (*refs, self.action_ref)
        for ref in refs:
            if ref.revision is None:
                raise ValueError("communication experience refs must pin exact revisions")
        return self


@dataclass(frozen=True, slots=True)
class CommunicationExperienceReceipt:
    experience_id: str
    revision: int
    world_revision: int


class CommunicationExperienceService:
    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex | None = None,
        subject_id: str = "user_1",
    ) -> None:
        self.store = store
        self.index = index
        self.subject_id = subject_id

    def _validate_real_feedback(self, refs: Sequence[ObjectRef]) -> None:
        saw_real_feedback = False
        for ref in refs:
            payload = self.store.get_payload(ref.object_id, revision=ref.revision)
            object_type = str(payload.get("object_type") or "")
            if object_type not in {ObjectType.OBSERVATION.value, ObjectType.OUTCOME.value}:
                continue
            if object_type == ObjectType.OBSERVATION.value:
                metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
                role = str(metadata.get("role") or "").strip().lower()
                created_by = str(payload.get("created_by") or "").strip().lower()
                if role == "assistant" or created_by == "conversation_ingest:assistant":
                    continue
            saw_real_feedback = True
        if not saw_real_feedback:
            raise ValueError(
                "communication experience requires real user/world feedback evidence "
                "(Observation or Outcome); assistant output alone is not feedback"
            )

    def record(
        self,
        request: CommunicationExperienceRequest,
        *,
        recorded_at: datetime,
    ) -> CommunicationExperienceReceipt:
        recorded = as_utc(recorded_at, "recorded_at")
        all_refs = tuple(dict.fromkeys((*request.evidence_refs, *request.counterexample_refs)))
        self._validate_real_feedback(request.evidence_refs)
        if request.action_ref is not None:
            self.store.get_payload(request.action_ref.object_id, revision=request.action_ref.revision)
        for ref in all_refs:
            self.store.get_payload(ref.object_id, revision=ref.revision)

        experience_id = _stable_id(
            "commexp", self.subject_id, request.scenario.strip(), request.style.strip(),
            request.user_reaction.value,
            tuple((r.object_id, r.revision) for r in request.evidence_refs),
            recorded.isoformat(),
        )
        experience = CommunicationExperience(
            object_id=experience_id,
            subject_id=self.subject_id,
            revision=1,
            occurred=TemporalExtent.point(recorded),
            learned_at=recorded,
            recorded_at=recorded,
            source_refs=[SourceRef(object_id=r.object_id, revision=r.revision) for r in all_refs],
            created_by="communication_experience:resident_ai",
            scenario=request.scenario.strip(),
            style=request.style.strip(),
            tone=(request.tone.strip() if request.tone is not None and request.tone.strip() else None),
            user_reaction=request.user_reaction,
            action_ref=request.action_ref,
            applicable_conditions=dict(request.applicable_conditions),
            counterexample_refs=list(request.counterexample_refs),
            metadata={
                "dimension": COMMUNICATION_EXPERIENCE_DIMENSION,
                "evidence_refs": [r.model_dump(mode="json") for r in request.evidence_refs],
            },
        )
        exp_ref = ObjectRef(object_id=experience_id, revision=1)
        deps: list[Dependency] = []
        for ref in all_refs:
            deps.append(
                Dependency(
                    object_id=_stable_id("dep", experience_id, 1, ref.object_id, ref.revision),
                    subject_id=self.subject_id,
                    learned_at=recorded,
                    recorded_at=recorded,
                    created_by="communication_experience:dependency",
                    dependent_ref=exp_ref,
                    dependency_ref=ref,
                    dependency_type=(
                        "communication_experience_counterexample"
                        if ref in request.counterexample_refs
                        else "communication_experience_feedback_evidence"
                    ),
                )
            )
        if request.action_ref is not None:
            deps.append(
                Dependency(
                    object_id=_stable_id("dep", experience_id, 1, request.action_ref.object_id, request.action_ref.revision, "action"),
                    subject_id=self.subject_id,
                    learned_at=recorded,
                    recorded_at=recorded,
                    created_by="communication_experience:dependency",
                    dependent_ref=exp_ref,
                    dependency_ref=request.action_ref,
                    dependency_type="communication_experience_follows_action",
                )
            )
        result = self.store.commit(
            [experience, *deps],
            OperationRequest(
                operation_name="communication_experience.record",
                arguments={
                    "experience_id": experience_id,
                    "scenario": experience.scenario,
                    "style": experience.style,
                    "user_reaction": experience.user_reaction.value,
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="record evidence-grounded communication experience",
                idempotency_key=f"communication-experience:{experience_id}",
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        if self.index is not None:
            self.index.catch_up()
        return CommunicationExperienceReceipt(experience_id, 1, result.world_revision)

    def current(self, *, scenario: str | None = None, limit: int = 100) -> tuple[CommunicationExperience, ...]:
        items = [
            CommunicationExperience.model_validate(payload)
            for payload in self.store.list_payloads(
                object_type=ObjectType.COMMUNICATION_EXPERIENCE,
                subject_id=self.subject_id,
            )
        ]
        if scenario is not None:
            clean = scenario.strip()
            items = [item for item in items if item.scenario == clean]
        items.sort(key=lambda item: (-item.recorded_at.timestamp(), item.object_id))
        return tuple(items[: max(0, int(limit))])
