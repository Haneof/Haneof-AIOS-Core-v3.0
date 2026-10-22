"""Several durable facts from one utterance must all persist.

One user sentence commonly carries three or four facts ("I'm Lao Wang, I build 23cm
bands, supply is stuck with the Dongguan supplier, drop the honorifics"). Persisting
them is the only way they survive context exhaustion, so a partial write is silent
memory loss: the model believes it recorded something it did not.

Root cause this locks down: evidence-set identity is content-addressed over
(subject, dimension, member refs, learned time). Two claims in the same turn about
the same dimension from the same evidence derive the *same* evidence-set id and the
*same* member dependency ids. The second write therefore attempted revision 1 on an
object that already existed and aborted the whole atomic bundle with VERSION_CONFLICT.
"""

from __future__ import annotations

from datetime import datetime, timezone

from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


def _seed(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs = Observation(
        object_id="obs_durable_facts_1",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="multi-claim-test",
        source_kind="chat",
        modality="text",
        value="我叫老王，做 23cm 柔性屏手环，供应链卡在东莞那家。别跟我用敬语。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    store.commit(
        [obs],
        OperationRequest(
            operation_name="test.seed",
            expected_world_revision=0,
            reason="seed durable facts",
            idempotency_key="multi-claim-seed",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, obs


def _request(content: str, obs: Observation, dimension: str) -> ClaimWriteRequest:
    return ClaimWriteRequest(
        content=content,
        evidence_refs=(ObjectRef(object_id=obs.object_id, revision=1),),
        confidence=0.9,
        dimension=dimension,
    )


def test_three_facts_in_one_dimension_all_persist(tmp_path):
    store, index, obs = _seed(tmp_path)
    service = CognitionWritebackService(store=store, index=index)

    receipts = [
        service.commit_claim(
            _request(content, obs, "dim:ai_user_understanding"),
            learned_at=NOW,
        )
        for content in (
            "用户叫老王",
            "用户做 23cm 柔性屏手环",
            "供应链卡在东莞那家供应商",
        )
    ]

    assert len({receipt.claim_id for receipt in receipts}) == 3
    for receipt in receipts:
        claim = store.get_payload(receipt.claim_id)
        assert claim["content"] in (
            "用户叫老王",
            "用户做 23cm 柔性屏手环",
            "供应链卡在东莞那家供应商",
        )
    # The shared evidence set is reused, not re-created, so all three claims point
    # at the same support object.
    assert len({receipt.evidence_set_id for receipt in receipts}) == 1
    evidence = store.get_payload(receipts[0].evidence_set_id)
    assert evidence["revision"] == 1
    assert evidence["member_refs"] == [{"object_id": obs.object_id, "revision": 1}]


def test_facts_across_dimensions_persist_independently(tmp_path):
    store, index, obs = _seed(tmp_path)
    service = CognitionWritebackService(store=store, index=index)

    user_receipt = service.commit_claim(
        _request("用户叫老王", obs, "dim:ai_user_understanding"),
        learned_at=NOW,
    )
    rel_receipt = service.commit_claim(
        _request("用户要求不用敬语", obs, "dim:ai_relationship"),
        learned_at=NOW,
    )

    assert user_receipt.evidence_set_id != rel_receipt.evidence_set_id
    assert store.get_payload(user_receipt.claim_id)["metadata"]["dimension"] == (
        "dim:ai_user_understanding"
    )
    assert store.get_payload(rel_receipt.claim_id)["metadata"]["dimension"] == "dim:ai_relationship"


def test_repeated_identical_claim_does_not_duplicate_world_revisions(tmp_path):
    """An exact retry must stay a retry, not mint a second revision of everything."""

    store, index, obs = _seed(tmp_path)
    service = CognitionWritebackService(store=store, index=index)

    first = service.commit_claim(
        _request("用户叫老王", obs, "dim:ai_user_understanding"),
        learned_at=NOW,
    )
    revision_after_first = store.current_world_revision()

    second = service.commit_claim(
        _request("用户叫老王", obs, "dim:ai_user_understanding"),
        learned_at=NOW,
    )

    assert second.claim_id == first.claim_id
    assert second.reused_existing is True
    assert store.current_world_revision() == revision_after_first
