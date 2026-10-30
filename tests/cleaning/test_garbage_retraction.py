"""端到端验证：二次门禁 confirm → 认知层 retract（真实删除）。

链路：入库原始记录（作证据）→ commit 一条 Claim → 门禁 confirm 删除 → retract →
断言 Claim 状态变为 retracted。受 PM-CLEANING-AB-EXPERIMENT-001 授权。
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from aios_core.cleaning import GarbageRetractionService, current_claim_ref  # noqa: E402
from aios_core.contracts.enums import SourceClass  # noqa: E402
from aios_core.contracts.refs import ObjectRef  # noqa: E402
from aios_core.ingest import RealityIngestService, RealityRecord, SourceAdapterSpec  # noqa: E402
from aios_core.query.search import WorldSearchIndex  # noqa: E402
from aios_core.storage.sqlite_store import SQLiteWorldStore  # noqa: E402
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService  # noqa: E402

SUBJECT = "user_1"
WHEN = datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)


def _fresh() -> tuple[SQLiteWorldStore, WorldSearchIndex]:
    db = Path(__file__).resolve().parent / f"_tmp_clean_{id(object())}.db"
    if db.exists():
        db.unlink()
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _ingest_record(store, index, value: str) -> ObjectRef:
    svc = RealityIngestService(store=store, index=index, subject_id=SUBJECT)
    spec = SourceAdapterSpec(
        adapter_id="test.note.v1", source_kind="note", dimension="dim:note",
        source_class=SourceClass.USER, default_modality="text",
    )
    rec = RealityRecord(
        external_record_id="rec_garbage_1", occurred_at=WHEN, received_at=WHEN,
        value=value, source_locator="adapter://test.note.v1/rec_garbage_1",
    )
    receipt = svc.ingest_record(spec, rec)
    return ObjectRef(object_id=receipt.observation_id, revision=1)


def test_confirmed_garbage_is_retracted():
    store, index = _fresh()
    record_ref = _ingest_record(store, index, "这是一条商城广告推送，无长期价值")
    wb = CognitionWritebackService(store=store, index=index, subject_id=SUBJECT)
    claim = wb.commit_claim(
        ClaimWriteRequest(
            content="用户收到了一条商城广告",
            evidence_refs=(record_ref,), confidence=1.0, dimension="dim:note",
        ),
        learned_at=WHEN,
    )
    claim_ref = ObjectRef(object_id=claim.claim_id, revision=1)

    # 二次门禁 confirm 删除，理由来自真实模型调用（此处以常量模拟）
    rs = GarbageRetractionService(store=store, index=index, subject_id=SUBJECT)
    receipt = rs.retract(
        claim_ref=claim_ref, record_ref=record_ref,
        reason="二次门禁确认：商城广告，无价值噪声", changed_at=datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc),
    )
    assert receipt.mode == "retract"
    assert receipt.new_revision == 2

    payload = store.get_payload(claim.claim_id)
    assert payload["status"] == "retracted", payload["status"]
    # 原始记录仍保留（宪法：ingest 层不删）
    assert store.get_payload(record_ref.object_id) is not None

    claim_ref2 = current_claim_ref(store, claim.claim_id)
    assert claim_ref2.revision == 2


def test_retract_is_idempotent_on_already_retracted():
    store, index = _fresh()
    record_ref = _ingest_record(store, index, "又一条广告")
    wb = CognitionWritebackService(store=store, index=index, subject_id=SUBJECT)
    claim = wb.commit_claim(
        ClaimWriteRequest(content="广告", evidence_refs=(record_ref,),
                           confidence=1.0, dimension="dim:note"),
        learned_at=WHEN,
    )
    claim_ref = ObjectRef(object_id=claim.claim_id, revision=1)
    rs = GarbageRetractionService(store=store, index=index, subject_id=SUBJECT)
    rs.retract(claim_ref=claim_ref, record_ref=record_ref,
               reason="门禁确认广告", changed_at=datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc))
    # 第二次 retract 必须被服务拒绝（前向不可变）
    from aios_core.revision.service import ClaimRevisionRequest, CognitionRevisionService
    bad = CognitionRevisionService(store=store, index=index, subject_id=SUBJECT)
    raised = False
    try:
        bad.apply(
            ClaimRevisionRequest(target_ref=ObjectRef(object_id=claim.claim_id, revision=2),
                                 mode="retract", reason="重复", evidence_refs=(record_ref,)),
            changed_at=datetime(2026, 10, 30, 13, 0, tzinfo=timezone.utc),
        )
    except ValueError:
        raised = True
    assert raised, "已 retract 的 Claim 不应被二次 retract"
