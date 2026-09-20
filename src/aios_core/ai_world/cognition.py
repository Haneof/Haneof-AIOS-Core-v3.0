"""Unified AI-world cognition views for AIOS v3.0.

AI User Understanding, Relationship, Self, Intent, Strategy, Cognitive Boundary,
Personality and Calibration are not separate databases. They are typed views over
the same durable Claim/Evidence/Dependency/Revision world machinery.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import ClaimType, KnowledgeState, ObjectType
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.revision.service import (
    ClaimRevisionReceipt,
    ClaimRevisionRequest,
    CognitionRevisionService,
)
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.writeback.cognition import (
    ClaimWriteReceipt,
    ClaimWriteRequest,
    CognitionWritebackService,
)


AI_SELF_SUBJECT_ID = "ai_agent_self"


class AIWorldDomain(StrEnum):
    USER_UNDERSTANDING = "user_understanding"
    RELATIONSHIP = "relationship"
    SELF = "self"
    INTENT = "intent"
    STRATEGY = "strategy"
    COGNITIVE_BOUNDARY = "cognitive_boundary"
    PERSONALITY = "personality"
    CALIBRATION = "calibration"


DOMAIN_DIMENSIONS: Mapping[AIWorldDomain, str] = {
    AIWorldDomain.USER_UNDERSTANDING: "dim:ai_user_understanding",
    AIWorldDomain.RELATIONSHIP: "dim:ai_relationship",
    AIWorldDomain.SELF: "dim:ai_self",
    AIWorldDomain.INTENT: "dim:ai_intent",
    AIWorldDomain.STRATEGY: "dim:ai_strategy",
    AIWorldDomain.COGNITIVE_BOUNDARY: "dim:ai_cognitive_boundary",
    AIWorldDomain.PERSONALITY: "dim:ai_personality",
    AIWorldDomain.CALIBRATION: "dim:ai_calibration",
}

_USER_SCOPED_DOMAINS = {
    AIWorldDomain.USER_UNDERSTANDING,
    AIWorldDomain.RELATIONSHIP,
    AIWorldDomain.STRATEGY,
}


class AIWorldClaimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    domain: AIWorldDomain
    statement: str = Field(min_length=1)
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    knowledge_state: KnowledgeState = KnowledgeState.INFERRED
    claim_type: ClaimType = ClaimType.INFERENCE
    scope_key: str | None = None
    tags: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_request(self) -> "AIWorldClaimRequest":
        if not self.statement.strip():
            raise ValueError("statement must not be blank")
        if self.scope_key is not None and not self.scope_key.strip():
            raise ValueError("scope_key must not be blank")
        if any(not tag.strip() for tag in self.tags):
            raise ValueError("tags must not contain blank values")
        for ref in self.evidence_refs:
            if ref.revision is None:
                raise ValueError("AI-world cognition requires pinned evidence revisions")
        return self


class AIWorldClaimView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    domain: AIWorldDomain
    dimension: str
    object_id: str
    revision: int = Field(ge=1)
    subject_id: str
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)
    knowledge_state: KnowledgeState
    claim_type: ClaimType
    learned_at: datetime
    scope_key: str | None = None
    tags: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_time(self) -> "AIWorldClaimView":
        as_utc(self.learned_at, "learned_at")
        return self


@dataclass(frozen=True, slots=True)
class AIWorldWriteReceipt:
    domain: AIWorldDomain
    dimension: str
    subject_id: str
    claim: ClaimWriteReceipt


class AIWorldCognitionService:
    """Thin typed facade over the unified cognition writeback/revision machinery."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex | None = None,
        user_id: str = "user_1",
        ai_subject_id: str = AI_SELF_SUBJECT_ID,
    ) -> None:
        self.store = store
        self.index = index
        self.user_id = user_id
        self.ai_subject_id = ai_subject_id

    def _subject_for(self, domain: AIWorldDomain) -> str:
        return self.user_id if domain in _USER_SCOPED_DOMAINS else self.ai_subject_id

    def commit(
        self,
        request: AIWorldClaimRequest,
        *,
        learned_at: datetime,
    ) -> AIWorldWriteReceipt:
        domain = AIWorldDomain(request.domain)
        dimension = DOMAIN_DIMENSIONS[domain]
        subject_id = self._subject_for(domain)
        writer = CognitionWritebackService(
            store=self.store,
            index=self.index,
            subject_id=subject_id,
            evidence_subject_ids=(self.user_id, self.ai_subject_id),
        )
        metadata: dict[str, Any] = {
            "ai_domain": domain.value,
            "ai_world": True,
        }
        if request.scope_key is not None:
            metadata["scope_key"] = request.scope_key.strip()
        if request.tags:
            metadata["tags"] = list(dict.fromkeys(tag.strip() for tag in request.tags))

        receipt = writer.commit_claim(
            ClaimWriteRequest(
                content=request.statement.strip(),
                evidence_refs=request.evidence_refs,
                confidence=request.confidence,
                dimension=dimension,
                claim_type=request.claim_type,
                knowledge_state=request.knowledge_state,
                claimant_id="resident_ai",
                metadata=metadata,
            ),
            learned_at=learned_at,
        )
        return AIWorldWriteReceipt(
            domain=domain,
            dimension=dimension,
            subject_id=subject_id,
            claim=receipt,
        )

    def current(
        self,
        *,
        domains: Sequence[AIWorldDomain] | None = None,
        scope_key: str | None = None,
        limit: int = 100,
    ) -> tuple[AIWorldClaimView, ...]:
        allowed = (
            {AIWorldDomain(item) for item in domains}
            if domains is not None
            else set(AIWorldDomain)
        )
        clean_scope = None if scope_key is None else scope_key.strip()
        if scope_key is not None and not clean_scope:
            raise ValueError("scope_key must not be blank")

        views: list[AIWorldClaimView] = []
        for payload in self.store.list_payloads(object_type=ObjectType.CLAIM):
            metadata = payload.get("metadata")
            if not isinstance(metadata, dict) or not metadata.get("ai_world"):
                continue
            try:
                domain = AIWorldDomain(str(metadata.get("ai_domain")))
            except ValueError:
                continue
            if domain not in allowed:
                continue
            if str(payload.get("status") or "active") != "active":
                continue
            if clean_scope is not None and metadata.get("scope_key") != clean_scope:
                continue

            views.append(
                AIWorldClaimView(
                    domain=domain,
                    dimension=DOMAIN_DIMENSIONS[domain],
                    object_id=str(payload["object_id"]),
                    revision=int(payload["revision"]),
                    subject_id=str(payload["subject_id"]),
                    statement=str(payload.get("content") or ""),
                    confidence=float(payload.get("confidence") or 0.0),
                    knowledge_state=KnowledgeState(str(payload["knowledge_state"])),
                    claim_type=ClaimType(str(payload["claim_type"])),
                    learned_at=datetime.fromisoformat(str(payload["learned_at"])),
                    scope_key=(
                        str(metadata["scope_key"])
                        if metadata.get("scope_key") is not None
                        else None
                    ),
                    tags=tuple(str(tag) for tag in metadata.get("tags") or ()),
                )
            )

        views.sort(
            key=lambda item: (
                -item.learned_at.timestamp(),
                item.domain.value,
                item.object_id,
            )
        )
        return tuple(views[: max(0, int(limit))])

    def core_context(
        self,
        *,
        per_domain: int = 3,
    ) -> dict[str, list[dict[str, Any]]]:
        """Return only explicitly tagged identity/relationship continuity cognition.

        New sessions must not preload the user's entire AI-world profile. Claims enter
        this compact continuity view only when their durable tags contain
        the core_context marker.
        """
        if per_domain < 1:
            raise ValueError("per_domain must be >= 1")

        result: dict[str, list[dict[str, Any]]] = {}
        for domain in (
            AIWorldDomain.USER_UNDERSTANDING,
            AIWorldDomain.RELATIONSHIP,
            AIWorldDomain.SELF,
        ):
            selected = [
                item
                for item in self.current(domains=[domain], limit=200)
                if "core_context" in item.tags
            ][:per_domain]
            if selected:
                result[domain.value] = [
                    item.model_dump(mode="json")
                    for item in selected
                ]
        return result

    def snapshot(
        self,
        *,
        per_domain: int = 10,
    ) -> dict[str, list[dict[str, Any]]]:
        if per_domain < 1:
            raise ValueError("per_domain must be >= 1")
        snapshot: dict[str, list[dict[str, Any]]] = {}
        for domain in AIWorldDomain:
            items = self.current(domains=[domain], limit=per_domain)
            snapshot[domain.value] = [
                item.model_dump(mode="json")
                for item in items
            ]
        return snapshot

    def revise(
        self,
        *,
        target_ref: ObjectRef,
        evidence_refs: Sequence[ObjectRef],
        replacement_statement: str,
        reason: str,
        changed_at: datetime,
        confidence: float | None = None,
    ) -> ClaimRevisionReceipt:
        payload = self.store.get_payload(
            target_ref.object_id,
            revision=target_ref.revision,
        )
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict) or not metadata.get("ai_world"):
            raise ValueError("target_ref is not an AI-world cognition Claim")
        service = CognitionRevisionService(
            store=self.store,
            index=self.index,
            subject_id=str(payload["subject_id"]),
            evidence_subject_ids=(self.user_id, self.ai_subject_id),
        )
        return service.apply(
            ClaimRevisionRequest(
                target_ref=target_ref,
                mode="revise",
                reason=reason,
                evidence_refs=tuple(evidence_refs),
                replacement_content=replacement_statement,
                confidence=confidence,
            ),
            changed_at=changed_at,
        )

    def retract(
        self,
        *,
        target_ref: ObjectRef,
        evidence_refs: Sequence[ObjectRef],
        reason: str,
        changed_at: datetime,
    ) -> ClaimRevisionReceipt:
        payload = self.store.get_payload(
            target_ref.object_id,
            revision=target_ref.revision,
        )
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict) or not metadata.get("ai_world"):
            raise ValueError("target_ref is not an AI-world cognition Claim")
        service = CognitionRevisionService(
            store=self.store,
            index=self.index,
            subject_id=str(payload["subject_id"]),
        )
        return service.apply(
            ClaimRevisionRequest(
                target_ref=target_ref,
                mode="retract",
                reason=reason,
                evidence_refs=tuple(evidence_refs),
            ),
            changed_at=changed_at,
        )
