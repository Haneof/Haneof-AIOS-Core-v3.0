"""数据清洗删除执行层（二次 AI 审核门禁的落地）。

本包把「第一遍标注 → 护栏 → 第二遍删除门禁」确认出的垃圾，真正执行删除。
删除走认知层 `CognitionRevisionService.revise(mode="retract")`，符合宪法第六/十条：
AI 不得静默删原文（ingest 层冻结），删除须带 pinned 证据、可前向追溯。

受 `PM-CLEANING-AB-EXPERIMENT-001` 授权（governance/baseline.json 已登记）。
"""
from .pipeline import GarbageRetractionService, current_claim_ref

__all__ = ["GarbageRetractionService", "current_claim_ref"]
