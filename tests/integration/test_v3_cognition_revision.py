from datetime import datetime, timedelta, timezone

from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.revision.service import (
    ClaimRevisionRequest,
    CognitionRevisionService,
    STATUS_RETRACTED,
    STATUS_REVIEW_REQUIRED,
)
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries.dimension_summary import DimensionSummaryService
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService


NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def _observation(oid: str, text: str, when: datetime) -> Observation:
    return Observation(
        object_id=oid,
        subject_id="user_1",
        occurred=TemporalExtent.point(when),
        learned_at=when,
        recorded_at=when,
        created_by="revision-test",
        source_kind="conversation",
        modality="text",
        value=text,
        metadata={"dimension": "dim:user_ai_interaction"},
    )


def _seed_world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    first = _observation("obs_pref_1", "我每天都喝茶。", NOW - timedelta(days=10))
    correction = _observation(
        "obs_pref_correction",
        "之前那段时间是喝茶，现在已经改成每天喝咖啡了。",
        NOW,
    )
    store.commit(
        [first, correction],
        OperationRequest(
            operation_name="test.seed",
            expected_world_revision=0,
            reason="seed old and correcting facts",
            idempotency_key="revision-seed",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    writeback = CognitionWritebackService(store=store, index=index)

    a = writeback.commit_claim(
        ClaimWriteRequest(
            content="用户当前偏好每天喝茶。",
            evidence_refs=(ObjectRef(object_id=first.object_id, revision=1),),
            confidence=0.8,
            dimension="dim:ai_user_understanding",
        ),
        learned_at=NOW - timedelta(days=9),
    )
    # C15-RCC-EVIDENCE-POLICY-001: a dependent Claim may still build on an earlier
    # Claim, but the earlier Claim can no longer be the *only* support. The real
    # Observation is pinned alongside it so the lineage still closes on a reality
    # leaf. The Claim -> Claim dependency edge under test here is unchanged, so the
    # revision/propagation semantics these tests cover are preserved exactly.
    b = writeback.commit_claim(
        ClaimWriteRequest(
            content="用户的饮品习惯目前以茶为主。",
            evidence_refs=(
                ObjectRef(object_id=a.claim_id, revision=1),
                ObjectRef(object_id=first.object_id, revision=1),
            ),
            confidence=0.72,
            dimension="dim:ai_user_understanding",
        ),
        learned_at=NOW - timedelta(days=8),
    )
    return store, index, first, correction, a, b


def test_revise_claim_preserves_history_and_marks_dependents_review_required(tmp_path):
    store, index, first, correction, a, b = _seed_world(tmp_path)
    service = CognitionRevisionService(store=store, index=index)

    receipt = service.apply(
        ClaimRevisionRequest(
            target_ref=ObjectRef(object_id=a.claim_id, revision=1),
            mode="revise",
            reason="用户提供了更新后的当前饮品习惯",
            evidence_refs=(ObjectRef(object_id=correction.object_id, revision=1),),
            replacement_content="用户当前偏好每天喝咖啡。",
            confidence=0.9,
        ),
        changed_at=NOW,
    )

    old_claim = store.get_payload(a.claim_id, revision=1)
    current_claim = store.get_payload(a.claim_id)
    dependent_claim = store.get_payload(b.claim_id)

    assert old_claim["content"] == "用户当前偏好每天喝茶。"
    assert old_claim["revision"] == 1
    assert current_claim["revision"] == 2
    assert current_claim["content"] == "用户当前偏好每天喝咖啡。"
    assert current_claim["status"] == "active"

    assert dependent_claim["revision"] == 2
    assert dependent_claim["status"] == STATUS_REVIEW_REQUIRED
    assert {
        "object_id": a.claim_id,
        "revision": 1,
    } in dependent_claim["metadata"]["stale_due_to_refs"]
    assert (b.claim_id, 1) in receipt.stale_refs

    # Raw reality never gets rewritten by cognition correction.
    assert store.get_payload(first.object_id)["value"] == "我每天都喝茶。"
    assert store.get_payload(correction.object_id)["value"].endswith("每天喝咖啡了。")

    current_tea = index.recall_candidates(
        "喝茶",
        object_types=["claim"],
    )
    assert a.claim_id not in {hit.object_id for hit in current_tea.hits}
    assert b.claim_id not in {hit.object_id for hit in current_tea.hits}

    current_coffee = index.recall_candidates(
        "喝咖啡",
        object_types=["claim"],
    )
    assert a.claim_id in {hit.object_id for hit in current_coffee.hits}

    historical = store.get_payload(a.claim_id, revision=1)
    assert historical["content"] == "用户当前偏好每天喝茶。"


def test_retract_claim_creates_forward_tombstone_semantics_without_deleting_history(tmp_path):
    store, index, _, correction, a, b = _seed_world(tmp_path)
    service = CognitionRevisionService(store=store, index=index)

    receipt = service.apply(
        ClaimRevisionRequest(
            target_ref=ObjectRef(object_id=a.claim_id, revision=1),
            mode="retract",
            reason="旧理解不再可作为当前结论",
            evidence_refs=(ObjectRef(object_id=correction.object_id, revision=1),),
        ),
        changed_at=NOW,
    )

    assert store.get_payload(a.claim_id, revision=1)["status"] == "active"
    latest = store.get_payload(a.claim_id)
    assert latest["revision"] == 2
    assert latest["status"] == STATUS_RETRACTED
    assert latest["knowledge_state"] == "conflict"
    assert store.get_payload(b.claim_id)["status"] == STATUS_REVIEW_REQUIRED
    assert receipt.mode == "retract"


def test_already_advanced_dependent_is_not_overwritten_by_old_dependency_propagation(tmp_path):
    store, index, _, correction, a, b = _seed_world(tmp_path)
    # Simulate the dependent already having been reviewed before upstream correction.
    current_b = store.get_payload(b.claim_id)
    from aios_core.contracts.models import Claim

    reviewed_b = Claim.model_validate(
        {
            **current_b,
            "revision": 2,
            "content": "用户饮品习惯正在变化，暂不下定论。",
            "confidence": 0.4,
            "learned_at": NOW - timedelta(days=1),
            "recorded_at": NOW - timedelta(days=1),
            "asserted_at": NOW - timedelta(days=1),
        }
    )
    store.commit(
        [reviewed_b],
        OperationRequest(
            operation_name="test.advance_dependent",
            expected_world_revision=store.current_world_revision(),
            reason="dependent already reviewed",
            idempotency_key="advance-dependent",
            source_class=SourceClass.AI_COGNITION,
        ),
    )
    index.catch_up()

    service = CognitionRevisionService(store=store, index=index)
    receipt = service.apply(
        ClaimRevisionRequest(
            target_ref=ObjectRef(object_id=a.claim_id, revision=1),
            mode="revise",
            reason="新证据更新旧理解",
            evidence_refs=(ObjectRef(object_id=correction.object_id, revision=1),),
            replacement_content="用户当前偏好每天喝咖啡。",
        ),
        changed_at=NOW,
    )

    assert store.get_payload(b.claim_id)["revision"] == 2
    assert store.get_payload(b.claim_id)["content"] == "用户饮品习惯正在变化，暂不下定论。"
    assert (b.claim_id, 1) in receipt.skipped_already_advanced_refs


def test_stale_dependent_can_be_re_evaluated_into_new_active_revision(tmp_path):
    store, index, _, correction, a, b = _seed_world(tmp_path)
    service = CognitionRevisionService(store=store, index=index)

    first = service.apply(
        ClaimRevisionRequest(
            target_ref=ObjectRef(object_id=a.claim_id, revision=1),
            mode="revise",
            reason="用户更新了当前饮品习惯",
            evidence_refs=(ObjectRef(object_id=correction.object_id, revision=1),),
            replacement_content="用户当前偏好每天喝咖啡。",
            confidence=0.9,
        ),
        changed_at=NOW,
    )
    assert store.get_payload(b.claim_id)["status"] == STATUS_REVIEW_REQUIRED

    second = service.apply(
        ClaimRevisionRequest(
            target_ref=ObjectRef(object_id=b.claim_id, revision=2),
            mode="revise",
            reason="上游用户偏好已更新，重新评估饮品习惯结论",
            # Re-evaluating a stale dependent still cites the revised upstream Claim,
            # pinned alongside the real correcting Observation so the revision
            # lineage closes on a reality leaf (C15-RCC-EVIDENCE-POLICY-001).
            evidence_refs=(
                ObjectRef(object_id=a.claim_id, revision=2),
                ObjectRef(object_id=correction.object_id, revision=1),
            ),
            replacement_content="用户的当前饮品习惯以咖啡为主。",
            confidence=0.84,
        ),
        changed_at=NOW + timedelta(seconds=1),
    )

    latest_b = store.get_payload(b.claim_id)
    assert latest_b["revision"] == 3
    assert latest_b["status"] == "active"
    assert latest_b["content"] == "用户的当前饮品习惯以咖啡为主。"
    assert second.previous_revision == 2
    assert second.new_revision == 3

    current_tea = index.recall_candidates("以茶", object_types=["claim"])
    assert b.claim_id not in {hit.object_id for hit in current_tea.hits}

    current_coffee = index.recall_candidates("以咖啡为主", object_types=["claim"])
    assert b.claim_id in {hit.object_id for hit in current_coffee.hits}


def test_claim_revision_stales_dependent_summary_then_summary_can_rebuild(tmp_path):
    store, index, _, correction, a, _ = _seed_world(tmp_path)

    summaries = DimensionSummaryService(store=store, index=index)
    window_start = NOW - timedelta(days=10)
    window_end = NOW - timedelta(days=7)

    prepared = summaries.prepare(
        dimension="dim:ai_user_understanding",
        granularity="week",
        window_start=window_start,
        window_end=window_end,
    )
    assert any(item.object_id == a.claim_id for item in prepared.sources)

    first_summary = summaries.commit(
        prepared,
        content="这一阶段AI理解为：用户当前饮品偏好以茶为主。",
        generated_at=NOW - timedelta(days=7),
    )
    assert store.get_payload(first_summary.object_id)["summary_status"] == "current"

    revision = CognitionRevisionService(store=store, index=index)
    revision.apply(
        ClaimRevisionRequest(
            target_ref=ObjectRef(object_id=a.claim_id, revision=1),
            mode="revise",
            reason="用户明确更新当前饮品习惯",
            evidence_refs=(ObjectRef(object_id=correction.object_id, revision=1),),
            replacement_content="用户当前偏好每天喝咖啡。",
            confidence=0.9,
        ),
        changed_at=NOW,
    )

    stale_summary = store.get_payload(first_summary.object_id)
    assert stale_summary["revision"] == 2
    assert stale_summary["summary_status"] == "stale"
    assert stale_summary["status"] == STATUS_REVIEW_REQUIRED

    current_old_summary = index.recall_candidates(
        "饮品偏好以茶",
        object_types=["summary"],
    )
    assert first_summary.object_id not in {hit.object_id for hit in current_old_summary.hits}

    rebuilt_input = summaries.prepare(
        dimension="dim:ai_user_understanding",
        granularity="week",
        window_start=window_start,
        window_end=window_end,
    )
    rebuilt = summaries.commit(
        rebuilt_input,
        content="这一阶段AI更新理解为：用户当前饮品偏好已经改为咖啡。",
        generated_at=NOW + timedelta(seconds=2),
    )
    latest = store.get_payload(first_summary.object_id)
    assert rebuilt.revision == 3
    assert latest["summary_status"] == "current"
    assert latest["status"] == "active"
    assert "咖啡" in latest["content"]
