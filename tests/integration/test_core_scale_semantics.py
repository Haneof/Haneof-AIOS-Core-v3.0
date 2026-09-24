from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aios_core.ai_world import (
    AI_SELF_SUBJECT_ID,
    AIWorldClaimRequest,
    AIWorldCognitionService,
    AIWorldDomain,
)
from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import Dependency, Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.turn_runtime import _KnowledgeCutoffStoreView
from aios_core.storage.sqlite_store import SQLiteWorldStore


UTC = timezone.utc
T0 = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)
USER_SCOPED = {
    AIWorldDomain.USER_UNDERSTANDING,
    AIWorldDomain.RELATIONSHIP,
    AIWorldDomain.STRATEGY,
}


def _commit_fact(
    store: SQLiteWorldStore,
    *,
    object_id: str,
    subject_id: str,
    text: str,
    at: datetime,
) -> Observation:
    fact = Observation(
        object_id=object_id,
        subject_id=subject_id,
        occurred=TemporalExtent.point(at),
        learned_at=at,
        recorded_at=at,
        created_by="core-scale-semantics",
        source_kind="conversation",
        modality="text",
        value=text,
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    store.commit(
        [fact],
        OperationRequest(
            operation_name=f"test.core_scale.fact.{object_id}",
            expected_world_revision=store.current_world_revision(),
            reason="seed CORE-SCALE-001 semantic equivalence evidence",
            idempotency_key=f"core-scale-fact:{object_id}",
            source_class=SourceClass.USER,
        ),
    )
    return fact


def _commit_ai_claim(
    service: AIWorldCognitionService,
    *,
    domain: AIWorldDomain,
    fact: Observation,
    statement: str,
    at: datetime,
    scope: str,
    tags: tuple[str, ...] = (),
):
    return service.commit(
        AIWorldClaimRequest(
            domain=domain,
            statement=statement,
            evidence_refs=(ObjectRef(object_id=fact.object_id, revision=1),),
            confidence=0.9,
            scope_key=scope,
            tags=tags,
        ),
        learned_at=at,
    )


def _legacy_current_ids(
    store: SQLiteWorldStore,
    *,
    user_id: str,
    domains: tuple[AIWorldDomain, ...],
    cutoff: datetime | None = None,
    required_tags: tuple[str, ...] = (),
    limit: int = 100,
) -> list[tuple[str, int]]:
    allowed = set(domains)
    rows = store.list_payloads(
        object_type=ObjectType.CLAIM,
        knowledge_cutoff=cutoff,
    )
    selected: list[tuple[float, str, str, int]] = []
    required = frozenset(required_tags)
    for payload in rows:
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict) or not metadata.get("ai_world"):
            continue
        try:
            domain = AIWorldDomain(str(metadata.get("ai_domain")))
        except ValueError:
            continue
        if domain not in allowed:
            continue
        expected_subject = user_id if domain in USER_SCOPED else AI_SELF_SUBJECT_ID
        if str(payload.get("subject_id") or "") != expected_subject:
            continue
        if str(payload.get("status") or "active") != "active":
            continue
        tags = tuple(str(tag) for tag in metadata.get("tags") or ())
        if required and not required.issubset(tags):
            continue
        learned = datetime.fromisoformat(str(payload["learned_at"])).timestamp()
        selected.append(
            (
                -learned,
                domain.value,
                str(payload["object_id"]),
                int(payload["revision"]),
            )
        )
    selected.sort()
    return [(object_id, revision) for _, _, object_id, revision in selected[:limit]]


def _view_ids(items) -> list[tuple[str, int]]:
    return [(item.object_id, item.revision) for item in items]


def test_ai_world_streaming_preserves_legacy_cutoff_subject_revision_and_partition_semantics(
    tmp_path,
):
    store = SQLiteWorldStore(tmp_path / "world.sqlite")
    fact_a = _commit_fact(
        store,
        object_id="obs_scale_a",
        subject_id="user_A",
        text="A evidence",
        at=T0,
    )
    fact_b = _commit_fact(
        store,
        object_id="obs_scale_b",
        subject_id="user_B",
        text="B evidence",
        at=T0 + timedelta(seconds=1),
    )
    index = WorldSearchIndex(tmp_path / "index.sqlite", store=store)
    index.rebuild()

    service_a = AIWorldCognitionService(store=store, index=index, user_id="user_A")
    service_b = AIWorldCognitionService(store=store, index=index, user_id="user_B")

    a_user = _commit_ai_claim(
        service_a,
        domain=AIWorldDomain.USER_UNDERSTANDING,
        fact=fact_a,
        statement="A user understanding.",
        at=T0 + timedelta(minutes=1),
        scope="user.style",
        tags=("core_context",),
    )
    b_user = _commit_ai_claim(
        service_b,
        domain=AIWorldDomain.USER_UNDERSTANDING,
        fact=fact_b,
        statement="B user understanding v1.",
        at=T0 + timedelta(minutes=2),
        scope="user.style",
        tags=("core_context",),
    )
    b_relationship = _commit_ai_claim(
        service_b,
        domain=AIWorldDomain.RELATIONSHIP,
        fact=fact_b,
        statement="B relationship.",
        at=T0 + timedelta(minutes=3),
        scope="relationship",
        tags=("core_context",),
    )
    shared_self = _commit_ai_claim(
        service_a,
        domain=AIWorldDomain.SELF,
        fact=fact_a,
        statement="Shared resident self.",
        at=T0 + timedelta(minutes=4),
        scope="self.identity",
        tags=("core_context",),
    )
    _commit_ai_claim(
        service_b,
        domain=AIWorldDomain.CALIBRATION,
        fact=fact_b,
        statement="Shared resident calibration.",
        at=T0 + timedelta(minutes=5),
        scope="calibration",
    )
    cutoff = T0 + timedelta(minutes=6)

    revised = service_b.revise(
        target_ref=ObjectRef(object_id=b_user.claim.claim_id, revision=1),
        evidence_refs=(ObjectRef(object_id=fact_b.object_id, revision=1),),
        replacement_statement="B user understanding v2 after cutoff.",
        reason="post-cutoff revision for temporal equivalence",
        changed_at=cutoff + timedelta(minutes=1),
        confidence=0.95,
    )
    assert revised.new_revision == 2
    index.catch_up()

    current_b = service_b.current(
        domains=(AIWorldDomain.USER_UNDERSTANDING,),
        limit=20,
    )
    assert _view_ids(current_b) == _legacy_current_ids(
        store,
        user_id="user_B",
        domains=(AIWorldDomain.USER_UNDERSTANDING,),
        limit=20,
    )
    assert _view_ids(current_b) == [(b_user.claim.claim_id, 2)]
    assert a_user.claim.claim_id not in {item.object_id for item in current_b}

    cutoff_service = AIWorldCognitionService(
        store=_KnowledgeCutoffStoreView(store, cutoff),
        index=index,
        user_id="user_B",
    )
    cutoff_b = cutoff_service.current(
        domains=(AIWorldDomain.USER_UNDERSTANDING,),
        limit=20,
    )
    assert _view_ids(cutoff_b) == _legacy_current_ids(
        store,
        user_id="user_B",
        domains=(AIWorldDomain.USER_UNDERSTANDING,),
        cutoff=cutoff,
        limit=20,
    )
    assert _view_ids(cutoff_b) == [(b_user.claim.claim_id, 1)]

    expected_core = {
        domain.value: _legacy_current_ids(
            store,
            user_id="user_B",
            domains=(domain,),
            cutoff=cutoff,
            required_tags=("core_context",),
            limit=3,
        )
        for domain in (
            AIWorldDomain.USER_UNDERSTANDING,
            AIWorldDomain.RELATIONSHIP,
            AIWorldDomain.SELF,
        )
    }
    actual_core = cutoff_service.core_context(per_domain=3)
    actual_core_ids = {
        domain: [
            (str(item["object_id"]), int(item["revision"]))
            for item in items
        ]
        for domain, items in actual_core.items()
    }
    assert actual_core_ids == {key: value for key, value in expected_core.items() if value}
    assert (a_user.claim.claim_id, 1) not in actual_core_ids["user_understanding"]
    assert (b_relationship.claim.claim_id, 1) in actual_core_ids["relationship"]
    assert (shared_self.claim.claim_id, 1) in actual_core_ids["self"]

    snapshot = cutoff_service.snapshot(per_domain=10)
    for domain in AIWorldDomain:
        assert [
            (str(item["object_id"]), int(item["revision"]))
            for item in snapshot[domain.value]
        ] == _legacy_current_ids(
            store,
            user_id="user_B",
            domains=(domain,),
            cutoff=cutoff,
            limit=10,
        )


def test_batched_world_payload_lookup_matches_repeated_latest_reads(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.sqlite")
    fact = _commit_fact(
        store,
        object_id="obs_batch",
        subject_id="user_1",
        text="batch evidence",
        at=T0,
    )
    index = WorldSearchIndex(tmp_path / "index.sqlite", store=store)
    service = AIWorldCognitionService(store=store, index=index)
    claim = _commit_ai_claim(
        service,
        domain=AIWorldDomain.USER_UNDERSTANDING,
        fact=fact,
        statement="batch lookup v1 marker",
        at=T0 + timedelta(minutes=1),
        scope="batch",
    )
    cutoff = T0 + timedelta(minutes=2)
    service.revise(
        target_ref=ObjectRef(object_id=claim.claim.claim_id, revision=1),
        evidence_refs=(ObjectRef(object_id=fact.object_id, revision=1),),
        replacement_statement="batch lookup v2 marker",
        reason="batch lookup revision",
        changed_at=cutoff + timedelta(minutes=1),
        confidence=0.92,
    )

    ids = (fact.object_id, claim.claim.claim_id)
    current_batch = store.get_payloads_for_ids(ids)
    historical_batch = store.get_payloads_for_ids(ids, knowledge_cutoff=cutoff)

    for object_id in ids:
        assert current_batch[object_id] == store.get_payload(object_id)
        assert historical_batch[object_id] == store.get_payload(
            object_id,
            knowledge_cutoff=cutoff,
        )
    assert int(current_batch[claim.claim.claim_id]["revision"]) == 2
    assert int(historical_batch[claim.claim.claim_id]["revision"]) == 1


def test_recall_batching_preserves_current_historical_subject_and_inactive_semantics(
    tmp_path,
):
    store = SQLiteWorldStore(tmp_path / "world.sqlite")
    fact_a = _commit_fact(
        store,
        object_id="obs_recall_a",
        subject_id="user_A",
        text="recall evidence A",
        at=T0,
    )
    fact_b = _commit_fact(
        store,
        object_id="obs_recall_b",
        subject_id="user_B",
        text="recall evidence B",
        at=T0 + timedelta(seconds=1),
    )
    index = WorldSearchIndex(tmp_path / "index.sqlite", store=store)
    index.rebuild()
    service_a = AIWorldCognitionService(store=store, index=index, user_id="user_A")
    service_b = AIWorldCognitionService(store=store, index=index, user_id="user_B")

    a_claim = _commit_ai_claim(
        service_a,
        domain=AIWorldDomain.USER_UNDERSTANDING,
        fact=fact_a,
        statement="scale-marker A current",
        at=T0 + timedelta(minutes=1),
        scope="recall.a",
    )
    b_claim = _commit_ai_claim(
        service_b,
        domain=AIWorldDomain.USER_UNDERSTANDING,
        fact=fact_b,
        statement="scale-marker B revision one",
        at=T0 + timedelta(minutes=2),
        scope="recall.b",
    )
    inactive = _commit_ai_claim(
        service_b,
        domain=AIWorldDomain.RELATIONSHIP,
        fact=fact_b,
        statement="scale-marker B inactive candidate",
        at=T0 + timedelta(minutes=3),
        scope="recall.inactive",
    )
    cutoff = T0 + timedelta(minutes=4)

    service_b.revise(
        target_ref=ObjectRef(object_id=b_claim.claim.claim_id, revision=1),
        evidence_refs=(ObjectRef(object_id=fact_b.object_id, revision=1),),
        replacement_statement="scale-marker B revision two",
        reason="post-cutoff revision",
        changed_at=cutoff + timedelta(minutes=1),
        confidence=0.96,
    )
    service_b.retract(
        target_ref=ObjectRef(object_id=inactive.claim.claim_id, revision=1),
        evidence_refs=(ObjectRef(object_id=fact_b.object_id, revision=1),),
        reason="post-cutoff inactive revision",
        changed_at=cutoff + timedelta(minutes=2),
    )
    index.catch_up()

    current_page = index.recall_candidates(
        "scale-marker",
        subject="user_B",
        limit=20,
    )
    current_pairs = {(hit.object_id, hit.revision) for hit in current_page.hits}
    assert (b_claim.claim.claim_id, 2) in current_pairs
    assert (b_claim.claim.claim_id, 1) not in current_pairs
    assert a_claim.claim.claim_id not in {hit.object_id for hit in current_page.hits}
    assert inactive.claim.claim_id not in {hit.object_id for hit in current_page.hits}

    current_inactive = index.recall_candidates(
        "scale-marker",
        subject="user_B",
        include_inactive=True,
        limit=20,
    )
    assert (inactive.claim.claim_id, 2) in {
        (hit.object_id, hit.revision) for hit in current_inactive.hits
    }

    historical_page = index.recall_candidates(
        "scale-marker",
        subject="user_B",
        as_of=cutoff,
        limit=20,
    )
    historical_pairs = {(hit.object_id, hit.revision) for hit in historical_page.hits}
    assert (b_claim.claim.claim_id, 1) in historical_pairs
    assert (b_claim.claim.claim_id, 2) not in historical_pairs
    assert (inactive.claim.claim_id, 1) in historical_pairs
    assert a_claim.claim.claim_id not in {hit.object_id for hit in historical_page.hits}


def test_batched_world_lookup_preserves_evidence_and_dependency_visibility(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.sqlite")
    fact = _commit_fact(
        store,
        object_id="obs_batch_lineage",
        subject_id="user_1",
        text="batch lineage evidence",
        at=T0,
    )
    index = WorldSearchIndex(tmp_path / "index.sqlite", store=store)
    index.rebuild()
    service = AIWorldCognitionService(store=store, index=index)
    claim = _commit_ai_claim(
        service,
        domain=AIWorldDomain.USER_UNDERSTANDING,
        fact=fact,
        statement="batch-lineage claim",
        at=T0 + timedelta(minutes=1),
        scope="batch.lineage",
    )
    claim_ref = ObjectRef(object_id=claim.claim.claim_id, revision=1)
    claim_payload = store.get_payload(claim_ref.object_id, revision=1)
    support_refs = tuple(claim_payload.get("support_evidence_set_refs") or ())
    assert support_refs, "AI-world Claim must keep its pinned support EvidenceSet"

    dependency = Dependency(
        object_id="dep_batch_lineage",
        subject_id="user_1",
        occurred=TemporalExtent.point(T0 + timedelta(minutes=2)),
        learned_at=T0 + timedelta(minutes=2),
        recorded_at=T0 + timedelta(minutes=2),
        created_by="core-scale-semantics",
        dependent_ref=claim_ref,
        dependency_ref=ObjectRef(object_id=fact.object_id, revision=1),
        dependency_type="scale_semantic_equivalence",
    )
    store.commit(
        [dependency],
        OperationRequest(
            operation_name="test.core_scale.dependency_visibility",
            expected_world_revision=store.current_world_revision(),
            reason="prove batched retrieval preserves evidence/dependency payloads",
            idempotency_key="core-scale-dependency-visibility",
            source_class=SourceClass.AI_COGNITION,
        ),
    )

    evidence_id = str(support_refs[0]["object_id"])
    batch = store.get_payloads_for_ids(
        (claim_ref.object_id, evidence_id, dependency.object_id)
    )
    for object_id in (claim_ref.object_id, evidence_id, dependency.object_id):
        assert batch[object_id] == store.get_payload(object_id)

    assert batch[claim_ref.object_id]["support_evidence_set_refs"] == list(support_refs)
    assert batch[dependency.object_id]["dependent_ref"] == {
        "object_id": claim_ref.object_id,
        "revision": 1,
    }
    assert batch[dependency.object_id]["dependency_ref"] == {
        "object_id": fact.object_id,
        "revision": 1,
    }


def test_recall_batching_preserves_exact_limit_order_and_watermark_catchup(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.sqlite")
    index = WorldSearchIndex(tmp_path / "index.sqlite", store=store)

    observations = []
    for offset in range(5):
        at = T0 + timedelta(minutes=offset)
        observation = Observation(
            object_id=f"obs_scale_order_{offset}",
            subject_id="user_1",
            occurred=TemporalExtent.point(at),
            learned_at=at,
            recorded_at=at,
            created_by="core-scale-semantics",
            source_kind="conversation",
            modality="text",
            value=f"order-marker item {offset}",
            metadata={"dimension": "dim:scale_order"},
        )
        store.commit(
            [observation],
            OperationRequest(
                operation_name=f"test.core_scale.order.{offset}",
                expected_world_revision=store.current_world_revision(),
                reason="seed exact recall order and limit semantics",
                idempotency_key=f"core-scale-order:{offset}",
                source_class=SourceClass.USER,
            ),
        )
        observations.append(observation)
        if offset == 3:
            index.rebuild()

    assert index.watermark() < store.current_world_revision()
    page = index.recall_candidates(
        "order-marker",
        subject="user_1",
        dimension="dim:scale_order",
        object_types=("observation",),
        limit=3,
    )

    assert [hit.object_id for hit in page.hits] == [
        observations[4].object_id,
        observations[3].object_id,
        observations[2].object_id,
    ]
    assert [hit.revision for hit in page.hits] == [1, 1, 1]
    assert len(page.hits) == 3
    assert page.world_revision == store.current_world_revision()
    assert page.index_watermark == store.current_world_revision()
    assert page.lag == 0
