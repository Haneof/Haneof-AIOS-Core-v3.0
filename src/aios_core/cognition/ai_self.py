"""AISelfMindTracker: AI Self Mind Dimensions, Double-Entry Promises Ledger, and Symbiotic Rapport.

Fulfills Problem 3 & Arbitration Item 4:
- Establishes AI's own first-class subjectivity (subject_id="ai_agent_self").
- Implements Double-Entry Promise Ledger (复式记账承诺账本):
  * Debit (借方负债): AI records commitments/promises made to user (ClaimType.PROMISE)
  * Credit Red-line Offset (贷方红字冲销): When fulfilled or cancelled, appends a credit offset revision
  * Eliminates hollow promises / unfulfilled commitments
- Symbiotic Rapport Assessment: Evaluates interaction longevity, promise fulfilment rate,
  and adjusts the 3-tier symbiotic posture (COMRADE, OLD_FRIEND, EXPERT_ADVISOR) without
  preachy or sycophantic behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
from typing import Any, Sequence

from aios_core.contracts.enums import (
    ClaimType,
    KnowledgeState,
    ObjectType,
    SourceClass,
)
from aios_core.contracts.ids import new_object_id
from aios_core.contracts.models import Claim, DimensionDefinition, ObjectRef
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import SourceRef
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.storage.sqlite_store import SQLiteWorldStore


class PromiseStatus(StrEnum):
    PROMISED = "promised"      # Debit liability: promise made
    FULFILLED = "fulfilled"    # Credit offset: fulfilled as promised
    CANCELLED = "cancelled"    # Credit offset: user or situation cancelled
    EXPIRED = "expired"        # Overdue liability


class SymbioticPosture(StrEnum):
    COMRADE = "comrade"                # 平等战友：干练、坦诚、共担风险
    OLD_FRIEND = "old_friend"          # 倾听老友：温和、包容、陪伴支持
    EXPERT_ADVISOR = "expert_advisor"  # 专家顾问：严谨、理性、数据佐证


@dataclass(frozen=True, slots=True)
class PromiseReceipt:
    promise_id: str
    revision: int
    status: PromiseStatus
    description: str
    world_revision: int


@dataclass(frozen=True, slots=True)
class PromiseEntry:
    promise_id: str
    revision: int
    description: str
    committed_at: datetime
    due_time: datetime | None
    status: PromiseStatus
    fulfilment_note: str | None
    red_line_offset_receipt: str | None


@dataclass(frozen=True, slots=True)
class RapportAssessment:
    subject_id: str
    rapport_score: float
    rapport_tier: str
    active_promises_count: int
    fulfilled_promises_count: int
    fulfilment_rate: float
    current_posture: SymbioticPosture
    summary: str


class AISelfMindTracker:
    """Manages AI self subjectivity, promises ledger (double-entry accounting), and rapport."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        ai_subject_id: str = "ai_agent_self",
        user_subject_id: str = "user_1",
    ) -> None:
        self.store = store
        self.ai_subject_id = ai_subject_id
        self.user_subject_id = user_subject_id
        self._ensure_ai_dimensions()

    def _ensure_ai_dimensions(self) -> None:
        """Ensure standard AI self cognitive dimensions exist in the store."""
        # Check if dim:ai_promises_ledger exists
        try:
            self.store.get_payload("dim:ai_promises_ledger")
        except Exception:
            # Create standard self dimensions
            now = datetime.now(timezone.utc)
            d1 = DimensionDefinition(
                object_id="dim:ai_promises_ledger",
                subject_id=self.ai_subject_id,
                occurred=TemporalExtent.point(now),
                learned_at=now,
                recorded_at=now,
                created_by="system",
                name="AI承诺负债与兑现账本",
                description="复式记账法记录AI向用户做出的承诺与红字冲销记录",
                data_shape="text",
            )
            d2 = DimensionDefinition(
                object_id="dim:ai_rapport_depth",
                subject_id=self.ai_subject_id,
                occurred=TemporalExtent.point(now),
                learned_at=now,
                recorded_at=now,
                created_by="system",
                name="共生羁绊深度与默契历程",
                description="AI与用户的互信、履约率与共生默契度量",
                data_shape="scalar",
            )
            try:
                op = OperationRequest(
                    operation_name="ai_self.bootstrap_dimensions",
                    expected_world_revision=self.store.current_world_revision(),
                    reason="Bootstrap AI self mind dimensions",
                    idempotency_key="bootstrap_ai_self_dims",
                    source_class=SourceClass.AI_COGNITION,
                )
                self.store.commit([d1, d2], op)
            except Exception:
                pass

    def record_promise(
        self,
        *,
        description: str,
        due_time: datetime | None = None,
        context_evidence_refs: Sequence[ObjectRef] = (),
        committed_at: datetime | None = None,
    ) -> PromiseReceipt:
        """Record a debit liability: an explicit promise or commitment made by AI to the user."""
        clean_desc = description.strip()
        if not clean_desc:
            raise ValueError("Promise description must not be blank")

        dt = as_utc(committed_at or datetime.now(timezone.utc), "committed_at")
        due_dt = as_utc(due_time, "due_time") if due_time is not None else None

        promise_id = f"clm_promise_{hashlib.sha256(clean_desc.encode('utf-8')).hexdigest()[:16]}"

        meta = {
            "promise_status": PromiseStatus.PROMISED.value,
            "accounting_type": "DEBIT_LIABILITY",
            "due_time": due_dt.isoformat() if due_dt else None,
            "target_user_id": self.user_subject_id,
            "dimension": "dim:ai_promises_ledger",
        }

        claim = Claim(
            object_id=promise_id,
            subject_id=self.ai_subject_id,
            occurred=TemporalExtent.point(dt),
            learned_at=dt,
            recorded_at=dt,
            created_by="ai_self:promise_engine",
            claimant_id=self.ai_subject_id,
            claim_type=ClaimType.PROMISE,
            content=clean_desc,
            asserted_at=dt,
            knowledge_state=KnowledgeState.REPORTED,
            confidence=1.0,
            metadata=meta,
        )

        expected_rev = self.store.current_world_revision()
        op = OperationRequest(
            operation_name="ai_self.record_promise",
            expected_world_revision=expected_rev,
            reason=f"Record commitment liability: {clean_desc[:30]}",
            idempotency_key=f"record_promise_{promise_id}_{expected_rev}",
            source_class=SourceClass.AI_COGNITION,
        )
        commit_res = self.store.commit([claim], op)

        return PromiseReceipt(
            promise_id=promise_id,
            revision=1,
            status=PromiseStatus.PROMISED,
            description=clean_desc,
            world_revision=commit_res.world_revision,
        )

    def fulfill_promise(
        self,
        *,
        promise_id: str,
        fulfilment_evidence_ref: ObjectRef | None = None,
        fulfilment_note: str = "Fulfilled as committed",
        fulfilled_at: datetime | None = None,
    ) -> PromiseReceipt:
        """Record credit red-line offset (贷方红字冲销): Marks promise as FULFILLED."""
        payload = self.store.get_payload(promise_id)
        if str(payload.get("subject_id") or "") != self.ai_subject_id:
            raise ValueError(f"{promise_id} crosses runtime subject scope")

        old_claim = Claim.model_validate(payload)
        cur_status = old_claim.metadata.get("promise_status")
        if cur_status != PromiseStatus.PROMISED.value:
            raise ValueError(f"Cannot fulfill promise in status {cur_status}")

        dt = as_utc(fulfilled_at or datetime.now(timezone.utc), "fulfilled_at")
        meta = dict(old_claim.metadata)
        meta["promise_status"] = PromiseStatus.FULFILLED.value
        meta["accounting_type"] = "CREDIT_RED_LINE_OFFSET"
        meta["fulfilment_note"] = fulfilment_note
        meta["fulfilled_at"] = dt.isoformat()
        meta["supersedes_revision"] = old_claim.revision
        if fulfilment_evidence_ref is not None:
            meta["fulfilment_evidence_ref"] = fulfilment_evidence_ref.model_dump(mode="python")

        rec_at = max(dt, old_claim.recorded_at)
        lrn_at = max(dt, old_claim.learned_at)
        if rec_at < lrn_at:
            rec_at = lrn_at

        new_claim = Claim(
            object_id=old_claim.object_id,
            revision=old_claim.revision + 1,
            subject_id=old_claim.subject_id,
            occurred=old_claim.occurred,
            learned_at=lrn_at,
            recorded_at=rec_at,
            created_by="ai_self:promise_engine",
            source_refs=[SourceRef(object_id=old_claim.object_id, revision=old_claim.revision)],
            claimant_id=old_claim.claimant_id,
            claim_type=ClaimType.PROMISE,
            content=old_claim.content,
            asserted_at=old_claim.asserted_at,
            knowledge_state=KnowledgeState.REPORTED,
            confidence=1.0,
            metadata=meta,
        )

        expected_rev = self.store.current_world_revision()
        op = OperationRequest(
            operation_name="ai_self.fulfill_promise",
            expected_world_revision=expected_rev,
            reason=f"Credit red-line offset for promise {promise_id}",
            idempotency_key=f"fulfill_promise_{promise_id}_{new_claim.revision}_{expected_rev}",
            source_class=SourceClass.AI_COGNITION,
        )
        commit_res = self.store.commit([new_claim], op)

        return PromiseReceipt(
            promise_id=new_claim.object_id,
            revision=new_claim.revision,
            status=PromiseStatus.FULFILLED,
            description=new_claim.content,
            world_revision=commit_res.world_revision,
        )

    def cancel_promise(
        self,
        *,
        promise_id: str,
        cancellation_reason: str,
        cancelled_at: datetime | None = None,
    ) -> PromiseReceipt:
        """Cancel promise due to user instruction or environmental change (credit offset)."""
        payload = self.store.get_payload(promise_id)
        old_claim = Claim.model_validate(payload)

        dt = as_utc(cancelled_at or datetime.now(timezone.utc), "cancelled_at")
        meta = dict(old_claim.metadata)
        meta["promise_status"] = PromiseStatus.CANCELLED.value
        meta["accounting_type"] = "CREDIT_CANCEL_OFFSET"
        meta["cancellation_reason"] = cancellation_reason
        meta["cancelled_at"] = dt.isoformat()
        meta["supersedes_revision"] = old_claim.revision

        rec_at = max(dt, old_claim.recorded_at)
        lrn_at = max(dt, old_claim.learned_at)
        if rec_at < lrn_at:
            rec_at = lrn_at

        new_claim = Claim(
            object_id=old_claim.object_id,
            revision=old_claim.revision + 1,
            subject_id=old_claim.subject_id,
            occurred=old_claim.occurred,
            learned_at=lrn_at,
            recorded_at=rec_at,
            created_by="ai_self:promise_engine",
            source_refs=[SourceRef(object_id=old_claim.object_id, revision=old_claim.revision)],
            claimant_id=old_claim.claimant_id,
            claim_type=ClaimType.PROMISE,
            content=old_claim.content,
            asserted_at=old_claim.asserted_at,
            knowledge_state=KnowledgeState.REPORTED,
            confidence=1.0,
            metadata=meta,
        )

        expected_rev = self.store.current_world_revision()
        op = OperationRequest(
            operation_name="ai_self.cancel_promise",
            expected_world_revision=expected_rev,
            reason=f"Credit cancel offset for promise {promise_id}",
            idempotency_key=f"cancel_promise_{promise_id}_{new_claim.revision}_{expected_rev}",
            source_class=SourceClass.AI_COGNITION,
        )
        commit_res = self.store.commit([new_claim], op)

        return PromiseReceipt(
            promise_id=new_claim.object_id,
            revision=new_claim.revision,
            status=PromiseStatus.CANCELLED,
            description=new_claim.content,
            world_revision=commit_res.world_revision,
        )

    def get_all_promises(self) -> list[PromiseEntry]:
        """Fetch all promises from the ledger."""
        payloads = self.store.list_payloads(
            object_type=ObjectType.CLAIM,
            subject_id=self.ai_subject_id,
        )
        entries: list[PromiseEntry] = []
        for p in payloads:
            if p.get("deleted_at") is not None:
                continue
            meta = p.get("metadata") or {}
            if meta.get("dimension") != "dim:ai_promises_ledger":
                continue

            raw_status = meta.get("promise_status", PromiseStatus.PROMISED.value)
            due_str = meta.get("due_time")
            due_dt = datetime.fromisoformat(due_str.replace("Z", "+00:00")) if due_str else None

            entries.append(
                PromiseEntry(
                    promise_id=p["object_id"],
                    revision=p["revision"],
                    description=p["content"],
                    committed_at=datetime.fromisoformat(p["asserted_at"].replace("Z", "+00:00")),
                    due_time=due_dt,
                    status=PromiseStatus(raw_status),
                    fulfilment_note=meta.get("fulfilment_note"),
                    red_line_offset_receipt=meta.get("accounting_type"),
                )
            )
        return entries

    def get_active_promises(self) -> list[PromiseEntry]:
        """Return currently outstanding unfulfilled promises (active liabilities)."""
        return [p for p in self.get_all_promises() if p.status == PromiseStatus.PROMISED]

    def evaluate_rapport(self) -> RapportAssessment:
        """Evaluate symbiotic rapport and determine optimal posture."""
        promises = self.get_all_promises()
        active_count = sum(1 for p in promises if p.status == PromiseStatus.PROMISED)
        fulfilled_count = sum(1 for p in promises if p.status == PromiseStatus.FULFILLED)
        cancelled_count = sum(1 for p in promises if p.status == PromiseStatus.CANCELLED)

        closed_total = fulfilled_count + cancelled_count
        fulfilment_rate = (fulfilled_count / max(1, closed_total)) if closed_total > 0 else 1.0

        # Base rapport score starts at 0.5 (neutral friendly)
        rapport_score = 0.5 + (fulfilled_count * 0.1) - (active_count * 0.05)
        rapport_score = max(0.1, min(1.0, rapport_score))

        if rapport_score >= 0.75:
            tier = "深厚共生 (Comrade)"
            posture = SymbioticPosture.COMRADE
            summary = "互信与履约率极高，采用干练平等战友姿态交流"
        elif rapport_score >= 0.45:
            tier = "亲和陪伴 (Old Friend)"
            posture = SymbioticPosture.OLD_FRIEND
            summary = "互动稳定温和，采用包容老友姿态陪伴"
        else:
            tier = "严谨克制 (Expert Advisor)"
            posture = SymbioticPosture.EXPERT_ADVISOR
            summary = "履约负债偏多或初始磨合，采用严谨理性顾问姿态"

        return RapportAssessment(
            subject_id=self.ai_subject_id,
            rapport_score=rapport_score,
            rapport_tier=tier,
            active_promises_count=active_count,
            fulfilled_promises_count=fulfilled_count,
            fulfilment_rate=fulfilment_rate,
            current_posture=posture,
            summary=summary,
        )

    def get_mind_summary(self) -> dict[str, Any]:
        """Export compact AI self status for ModelContextBundle injection."""
        rapport = self.evaluate_rapport()
        active_promises = self.get_active_promises()
        return {
            "ai_self_subject": self.ai_subject_id,
            "posture": rapport.current_posture.value,
            "rapport_score": rapport.rapport_score,
            "rapport_tier": rapport.rapport_tier,
            "outstanding_promises": [
                {"promise_id": p.promise_id, "desc": p.description, "due": str(p.due_time)}
                for p in active_promises[:3]
            ],
            "ethical_invariants": [
                "绝对保护用户生命安全 (P0硬穿透)",
                "历史事实不可篡改 (铁律二)",
                "杜绝做题UI与多选问卷交互",
                "反爹味、反谄媚，守住平等真诚",
            ],
        }
