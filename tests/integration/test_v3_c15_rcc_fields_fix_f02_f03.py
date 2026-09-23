"""F-02/F-03 remediation tests for C15-RCC-COGNITION-FIELDS-001.

F-02: retract mode must reject valid_time/unknown_items/counter_evidence_refs (Scheme A)
      and must not create orphan EvidenceSet; Dependency must be consistent.
F-03: AIWorldClaimRequest must reject blank unknown_items.
"""

from datetime import datetime, timedelta, timezone

import pytest

from aios_core.ai_world import (
    AI_SELF_SUBJECT_ID,
    AIWorldClaimRequest,
    AIWorldDomain,
)
from aios_core.contracts.enums import ObjectType
from aios_core.contracts.models import TemporalExtent
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TimePrecision
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.revision.service import ClaimRevisionRequest, CognitionRevisionService
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService

NOW = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)


def test_ai_world_claim_request_rejects_blank_unknown_items():
    """F-03: AIWorldClaimRequest must reject blank unknown_items entries."""
    with pytest.raises(ValueError, match="unknown_items"):
        AIWorldClaimRequest(
            domain=AIWorldDomain.USER_UNDERSTANDING,
            statement="测试语句",
            evidence_refs=(ObjectRef(object_id="obs_dummy", revision=1),),
            confidence=0.8,
            unknown_items=("有效", " ", "  "),
        )
    with pytest.raises(ValueError, match="unknown_items"):
        AIWorldClaimRequest(
            domain=AIWorldDomain.USER_UNDERSTANDING,
            statement="测试语句",
            evidence_refs=(ObjectRef(object_id="obs_dummy", revision=1),),
            confidence=0.8,
            unknown_items=("",),
        )
    with pytest.raises(ValueError, match="unknown_items"):
        AIWorldClaimRequest(
            domain=AIWorldDomain.USER_UNDERSTANDING,
            statement="测试语句",
            evidence_refs=(ObjectRef(object_id="obs_dummy", revision=1),),
            confidence=0.8,
            unknown_items=("   ",),
        )
    # Valid non-blank should pass
    req = AIWorldClaimRequest(
        domain=AIWorldDomain.USER_UNDERSTANDING,
        statement="测试语句",
        evidence_refs=(ObjectRef(object_id="obs_dummy", revision=1),),
        confidence=0.8,
        unknown_items=("其他场景未知", "后续待观察"),
    )
    assert req.unknown_items == ("其他场景未知", "后续待观察")
    # Empty should still be allowed (UNKNOWN legal - empty means no explicit unknown)
    req2 = AIWorldClaimRequest(
        domain=AIWorldDomain.USER_UNDERSTANDING,
        statement="测试语句",
        evidence_refs=(ObjectRef(object_id="obs_dummy", revision=1),),
        confidence=0.8,
        unknown_items=(),
    )
    assert req2.unknown_items == ()


def test_claim_revision_request_retract_rejects_temporal_and_counter_fields():
    """F-02 Scheme A: retract must not carry valid_time/unknown_items/counter_evidence_refs."""
    valid_ext = TemporalExtent(
        start=NOW - timedelta(days=1),
        end=NOW + timedelta(days=1),
        precision=TimePrecision.DAY,
    )
    base_kwargs = dict(
        target_ref=ObjectRef(object_id="clm_dummy", revision=1),
        mode="retract",
        reason="测试 retract 拒绝",
        evidence_refs=(ObjectRef(object_id="obs_dummy", revision=1),),
    )
    with pytest.raises(ValueError, match="retract must not carry valid_time"):
        ClaimRevisionRequest(**base_kwargs, valid_time=valid_ext)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="retract must not carry unknown_items"):
        ClaimRevisionRequest(**base_kwargs, unknown_items=("某项",))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="retract must not carry counter_evidence_refs"):
        ClaimRevisionRequest(
            **base_kwargs,
            counter_evidence_refs=(ObjectRef(object_id="obs_dummy2", revision=1),),  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="retract must not carry replacement_content"):
        ClaimRevisionRequest(**base_kwargs, replacement_content="不应出现的内容")  # type: ignore[arg-type]
    # Valid retract without those fields should succeed
    req = ClaimRevisionRequest(**base_kwargs)
    assert req.mode == "retract"
    assert req.valid_time is None
    assert req.unknown_items is None
    assert req.counter_evidence_refs == ()


def test_retract_without_counter_creates_no_orphan_and_dependency_consistent(tmp_path):
    """F-02: retract creates exactly one counter evidence set via evidence_refs, no orphan, Dependency consistent."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    seed = ConversationIngestor(store)
    turn1 = seed.commit_turn(
        session_id="sess1",
        turn_index=1,
        user_text="用户偏好短回复的观察",
        assistant_text="收到",
        occurred_at=NOW - timedelta(days=2),
    )
    turn2 = seed.commit_turn(
        session_id="sess2",
        turn_index=1,
        user_text="提供反证的闲聊长回复观察",
        assistant_text="详细展开...",
        occurred_at=NOW - timedelta(days=1),
    )
    writer = CognitionWritebackService(
        store=store,
        subject_id="user_1",
        evidence_subject_ids=("user_1", AI_SELF_SUBJECT_ID),
    )
    receipt = writer.commit_claim(
        ClaimWriteRequest(
            content="用户偏好短回复",
            evidence_refs=(ObjectRef(object_id=turn1.user_observation_id, revision=1),),
            confidence=0.8,
            dimension="dim:test",
        ),
        learned_at=NOW,
    )
    claim_id = receipt.claim_id
    before_evss = list(store.list_payloads(object_type=ObjectType.EVIDENCE_SET))

    revisor = CognitionRevisionService(
        store=store,
        subject_id="user_1",
        evidence_subject_ids=("user_1", AI_SELF_SUBJECT_ID),
    )
    rev_receipt = revisor.apply(
        ClaimRevisionRequest(
            target_ref=ObjectRef(object_id=claim_id, revision=1),
            mode="retract",
            reason="后续反证表明原偏好结论需撤回",
            evidence_refs=(ObjectRef(object_id=turn2.user_observation_id, revision=1),),
        ),
        changed_at=NOW + timedelta(hours=2),
    )
    assert rev_receipt.new_revision == 2
    assert rev_receipt.mode == "retract"

    payload_v2 = store.get_payload(claim_id, revision=2)
    assert payload_v2["status"] == "retracted"
    assert payload_v2["knowledge_state"] == "conflict"
    counter_refs = payload_v2.get("counter_evidence_set_refs") or []
    assert len(counter_refs) == 1
    retract_ev_set_ref = counter_refs[0]
    if isinstance(retract_ev_set_ref, dict):
        retract_ev_set_id = retract_ev_set_ref["object_id"]
    else:
        retract_ev_set_id = getattr(retract_ev_set_ref, "object_id", "")
    assert retract_ev_set_id == rev_receipt.evidence_set_id

    evs_payload = store.get_payload(retract_ev_set_id, revision=1)
    assert evs_payload["object_type"] == ObjectType.EVIDENCE_SET.value
    collected = evs_payload.get("counter_refs") or evs_payload.get("member_refs") or []
    found = any(
        (r.get("object_id") if isinstance(r, dict) else getattr(r, "object_id", "")) == turn2.user_observation_id
        for r in collected
    )
    assert found, "retract EvidenceSet should contain the counter observation"

    deps_after = list(store.list_payloads(object_type=ObjectType.DEPENDENCY))
    claim_dep_found = False
    evs_dep_found = False
    for dep in deps_after:
        dep_ref = dep.get("dependent_ref") or {}
        d_depend = dep_ref.get("object_id") if isinstance(dep_ref, dict) else ""
        ref = dep.get("dependency_ref") or {}
        r_id = ref.get("object_id") if isinstance(ref, dict) else ""
        if d_depend == claim_id and r_id == retract_ev_set_id:
            claim_dep_found = True
        if d_depend == retract_ev_set_id and r_id == turn2.user_observation_id:
            evs_dep_found = True
    assert claim_dep_found, "missing Dependency: Claim -> retract EvidenceSet"
    assert evs_dep_found, "missing Dependency: EvidenceSet -> source observation"

    after_evss = list(store.list_payloads(object_type=ObjectType.EVIDENCE_SET))
    assert len(after_evss) == len(before_evss) + 1, "retract should create exactly one new EvidenceSet, no orphan"
    for ev in after_evss:
        if "evs_revision_counter" in ev["object_id"]:
            pytest.fail("retract should not create evs_revision_counter orphan")

    # Verify retract rejected when trying to carry counter_evidence_refs via service (validation)
    with pytest.raises(ValueError, match="retract must not carry counter_evidence_refs"):
        revisor.apply(
            ClaimRevisionRequest(
                target_ref=ObjectRef(object_id=claim_id, revision=2),
                mode="retract",
                reason="二次撤回",
                evidence_refs=(ObjectRef(object_id=turn1.user_observation_id, revision=1),),
                counter_evidence_refs=(ObjectRef(object_id=turn2.user_observation_id, revision=1),),
            ),
            changed_at=NOW + timedelta(hours=3),
        )


def test_retract_rejects_valid_time_and_unknown_items_via_service(tmp_path):
    """Additional coverage: service layer also rejects via model validation."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    seed = ConversationIngestor(store)
    turn1 = seed.commit_turn(
        session_id="sess1",
        turn_index=1,
        user_text="事实1",
        assistant_text="回复1",
        occurred_at=NOW - timedelta(days=2),
    )
    writer = CognitionWritebackService(
        store=store,
        subject_id="user_1",
        evidence_subject_ids=("user_1", AI_SELF_SUBJECT_ID),
    )
    receipt = writer.commit_claim(
        ClaimWriteRequest(
            content="待撤回结论",
            evidence_refs=(ObjectRef(object_id=turn1.user_observation_id, revision=1),),
            confidence=0.8,
            dimension="dim:test",
        ),
        learned_at=NOW,
    )
    revisor = CognitionRevisionService(
        store=store,
        subject_id="user_1",
        evidence_subject_ids=("user_1", AI_SELF_SUBJECT_ID),
    )
    valid_ext = TemporalExtent(
        start=NOW - timedelta(days=1),
        end=NOW + timedelta(days=1),
        precision=TimePrecision.DAY,
    )
    with pytest.raises(ValueError, match="retract must not carry valid_time"):
        revisor.apply(
            ClaimRevisionRequest(
                target_ref=ObjectRef(object_id=receipt.claim_id, revision=1),
                mode="retract",
                reason="尝试携带 valid_time",
                evidence_refs=(ObjectRef(object_id=turn1.user_observation_id, revision=1),),
                valid_time=valid_ext,
            ),
            changed_at=NOW + timedelta(hours=1),
        )
    with pytest.raises(ValueError, match="retract must not carry unknown_items"):
        revisor.apply(
            ClaimRevisionRequest(
                target_ref=ObjectRef(object_id=receipt.claim_id, revision=1),
                mode="retract",
                reason="尝试携带 unknown_items",
                evidence_refs=(ObjectRef(object_id=turn1.user_observation_id, revision=1),),
                unknown_items=("不应携带",),
            ),
            changed_at=NOW + timedelta(hours=1),
        )
