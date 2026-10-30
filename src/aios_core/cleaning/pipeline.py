"""二次 AI 审核门禁的删除执行层。

流程（见 `experiments/cleaning_ab`）：第一遍 AI 标注 keep/drop → 确定性护栏强制保留
白名单 → 第二遍 AI 删除门禁对 drop 候选二次认知（confirm/cancel + 理由）。
本模块负责最后一步：当门禁 `confirm` 一条原始记录为垃圾，把它在认知层对应的
Claim **真实 retract**（带证据，前向不可变、可审计），而不是在 ingest 层静默删原文。

设计要点：
- 原始 RealityRecord 始终保留（canonical source，宪法冻结 ingest 层删除）；被 retract
  的是认知层从中抽取的 Claim，下游 summary/context 不再把它当已确立真理。
- 纯噪声若认知层从未抽 Claim，则无 Claim 可 retract——它本身不进认知，无需删除。
- 删除是唯一不可逆动作，因此必须且仅由第二遍门禁（最保守的一遍）的 `confirm` 触发。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from aios_core.contracts.refs import ObjectRef
from aios_core.query.search import WorldSearchIndex
from aios_core.revision.service import ClaimRevisionRequest, CognitionRevisionService
from aios_core.storage.sqlite_store import SQLiteWorldStore


class GarbageRetractionService:
    """对二次门禁 confirm 的垃圾，执行认知层 retract（带证据）。"""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex | None = None,
        subject_id: str = "user_1",
    ) -> None:
        self._revision = CognitionRevisionService(
            store=store, index=index, subject_id=subject_id
        )

    def retract(
        self,
        *,
        claim_ref: ObjectRef,
        record_ref: ObjectRef,
        reason: str,
        changed_at: datetime,
    ) -> Any:
        """把一条经二次门禁 confirm 的垃圾对应的 Claim retract（不可逆）。

        claim_ref：要 retract 的 Claim 精确引用（必须 pin 当前 revision）。
        record_ref：原始记录的精确引用，作为 retract 的证据（counter evidence）。
        reason：第二遍门禁给出的删除理由（来自真实模型调用，可追溯）。
        """
        request = ClaimRevisionRequest(
            target_ref=claim_ref,
            mode="retract",
            reason=reason,
            evidence_refs=(record_ref,),
        )
        return self._revision.apply(request, changed_at=changed_at)


def current_claim_ref(store: SQLiteWorldStore, claim_id: str) -> ObjectRef:
    """返回某 Claim 的当前 revision 引用（retract 必须 pin 当前 revision）。"""
    payload = store.get_payload(claim_id)
    return ObjectRef(object_id=claim_id, revision=int(payload.get("revision") or 1))
