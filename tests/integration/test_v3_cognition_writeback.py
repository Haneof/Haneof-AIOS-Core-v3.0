from datetime import datetime, timezone

import pytest

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService


NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def _seed(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs = Observation(
        object_id="obs_user_feedback_1",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="writeback-test",
        source_kind="chat",
        modality="text",
        value="我更喜欢你先给结论，再展开细节。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    store.commit(
        [obs],
        OperationRequest(
            operation_name="test.seed",
            expected_world_revision=0,
            reason="seed evidence",
            idempotency_key="writeback-seed",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, obs


def test_claim_writeback_is_evidence_grounded_and_atomic(tmp_path):
    store, index, obs = _seed(tmp_path)
    service = CognitionWritebackService(store=store, index=index)

    receipt = service.commit_claim(
        ClaimWriteRequest(
            content="用户偏好先看到结论，再按需展开细节。",
            evidence_refs=(ObjectRef(object_id=obs.object_id, revision=1),),
            confidence=0.82,
            dimension="dim:ai_user_understanding",
        ),
        learned_at=NOW,
    )

    assert receipt.world_revision == 2
    claim = store.get_payload(receipt.claim_id)
    evidence = store.get_payload(receipt.evidence_set_id)
    assert claim["object_type"] == ObjectType.CLAIM.value
    assert claim["metadata"]["writeback_kind"] == "revisable_cognition"
    assert claim["support_evidence_set_refs"][0]["object_id"] == receipt.evidence_set_id
    assert evidence["member_refs"] == [{"object_id": obs.object_id, "revision": 1}]
    assert len(receipt.dependency_ids) == 2
    assert all(store.get_payload(dep_id)["object_type"] == ObjectType.DEPENDENCY.value for dep_id in receipt.dependency_ids)

    original = store.get_payload(obs.object_id)
    assert original["value"] == "我更喜欢你先给结论，再展开细节。"

    page = index.recall_candidates("先看到结论")
    assert receipt.claim_id in {hit.object_id for hit in page.hits}


def test_exact_claim_retry_reuses_existing_bundle(tmp_path):
    store, index, obs = _seed(tmp_path)
    service = CognitionWritebackService(store=store, index=index)
    request = ClaimWriteRequest(
        content="用户偏好先看到结论。",
        evidence_refs=(ObjectRef(object_id=obs.object_id, revision=1),),
        confidence=0.8,
        dimension="dim:ai_user_understanding",
    )
    first = service.commit_claim(request, learned_at=NOW)
    retry = service.commit_claim(request, learned_at=NOW)

    assert first.claim_id == retry.claim_id
    assert retry.reused_existing is True
    assert store.current_world_revision() == first.world_revision


def test_unpinned_or_missing_evidence_is_rejected(tmp_path):
    store, index, _ = _seed(tmp_path)
    service = CognitionWritebackService(store=store, index=index)

    with pytest.raises(ValueError):
        ClaimWriteRequest(
            content="不能无证据写认知。",
            evidence_refs=(ObjectRef(object_id="obs_user_feedback_1"),),
            confidence=0.5,
            dimension="dim:ai_user_understanding",
        )

    with pytest.raises(Exception):
        service.commit_claim(
            ClaimWriteRequest(
                content="不存在的证据不能写认知。",
                evidence_refs=(ObjectRef(object_id="obs_missing", revision=1),),
                confidence=0.5,
                dimension="dim:ai_user_understanding",
            ),
            learned_at=NOW,
        )
