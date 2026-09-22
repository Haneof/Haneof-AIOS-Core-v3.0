import sqlite3

import pytest
from datetime import datetime, timedelta, timezone

from aios_core.ai_world import (
    AI_SELF_SUBJECT_ID,
    AIWorldClaimRequest,
    AIWorldCognitionService,
    AIWorldDomain,
)
from aios_core.contracts.enums import ClaimType, KnowledgeState, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService


NOW = datetime(2026, 9, 20, 13, 10, tzinfo=timezone.utc)


def _seed(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    facts = [
        Observation(
            object_id="obs_user_pref_p10",
            subject_id="user_1",
            occurred=TemporalExtent.point(NOW - timedelta(days=2)),
            learned_at=NOW - timedelta(days=2),
            recorded_at=NOW - timedelta(days=2),
            created_by="p10-test",
            source_kind="conversation",
            modality="text",
            value="我不喜欢你每次都问我该怎么设计，工程细节你自己判断。",
            metadata={"dimension": "dim:user_ai_interaction"},
        ),
        Observation(
            object_id="obs_ai_error_p10",
            subject_id="user_1",
            occurred=TemporalExtent.point(NOW - timedelta(days=1)),
            learned_at=NOW - timedelta(days=1),
            recorded_at=NOW - timedelta(days=1),
            created_by="p10-test",
            source_kind="conversation",
            modality="text",
            value="你刚才又把索引和推荐混到一起了。",
            metadata={"dimension": "dim:user_ai_interaction"},
        ),
    ]
    store.commit(
        facts,
        OperationRequest(
            operation_name="test.seed.p10",
            expected_world_revision=0,
            reason="seed P10 evidence",
            idempotency_key="p10-seed",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, facts


def test_all_ai_domains_share_one_world_store_without_second_ai_database(tmp_path):
    store, index, facts = _seed(tmp_path)
    service = AIWorldCognitionService(store=store, index=index)

    user = service.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.USER_UNDERSTANDING,
            statement="用户希望工程细节由AI自行判断，不要反复把架构问题抛回给用户。",
            evidence_refs=(ObjectRef(object_id=facts[0].object_id, revision=1),),
            confidence=0.94,
            scope_key="collaboration.engineering_autonomy",
        ),
        learned_at=NOW,
    )
    relationship = service.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.RELATIONSHIP,
            statement="当前协作关系要求AI承担更高的项目执行责任，而不是只做建议者。",
            evidence_refs=(ObjectRef(object_id=facts[0].object_id, revision=1),),
            confidence=0.82,
            scope_key="working_relationship",
        ),
        learned_at=NOW + timedelta(seconds=1),
    )
    self_claim = service.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.SELF,
            statement="我在这个项目中的角色需要包含持续执行、核验和断点续传，而不只是对话回答。",
            evidence_refs=(
                ObjectRef(object_id=user.claim.claim_id, revision=1),
                ObjectRef(object_id=relationship.claim.claim_id, revision=1),
            ),
            confidence=0.86,
            scope_key="project_role",
        ),
        learned_at=NOW + timedelta(seconds=2),
    )

    assert store.get_payload(user.claim.claim_id)["subject_id"] == "user_1"
    assert store.get_payload(relationship.claim.claim_id)["subject_id"] == "user_1"
    assert store.get_payload(self_claim.claim.claim_id)["subject_id"] == AI_SELF_SUBJECT_ID

    with sqlite3.connect(store.db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "runtime_ai_self_memory" not in tables
    assert "ai_user_understanding" not in tables
    assert "ai_relationship" not in tables


def test_cognitive_boundary_can_preserve_unknown_and_hypothesis(tmp_path):
    store, index, facts = _seed(tmp_path)
    service = AIWorldCognitionService(store=store, index=index)

    boundary = service.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.COGNITIVE_BOUNDARY,
            statement="目前不知道用户在没有明确反馈时是否偏好主动提醒，需要继续验证。",
            evidence_refs=(ObjectRef(object_id=facts[0].object_id, revision=1),),
            confidence=0.55,
            knowledge_state=KnowledgeState.UNKNOWN,
            claim_type=ClaimType.HYPOTHESIS,
            scope_key="proactive_reminder.preference",
        ),
        learned_at=NOW,
    )

    payload = store.get_payload(boundary.claim.claim_id)
    assert payload["knowledge_state"] == "unknown"
    assert payload["claim_type"] == "hypothesis"
    assert payload["metadata"]["ai_domain"] == "cognitive_boundary"


def test_calibration_can_record_real_correction_evidence(tmp_path):
    store, index, facts = _seed(tmp_path)
    service = AIWorldCognitionService(store=store, index=index)

    calibration = service.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.CALIBRATION,
            statement="我曾把智能索引与推荐机制混为一体，这类机制边界需要先核对现有法统再修改。",
            evidence_refs=(ObjectRef(object_id=facts[1].object_id, revision=1),),
            confidence=0.97,
            scope_key="architecture.boundary_errors",
            tags=("user_correction", "mechanism_boundary"),
        ),
        learned_at=NOW,
    )

    views = service.current(domains=[AIWorldDomain.CALIBRATION])
    assert len(views) == 1
    assert views[0].object_id == calibration.claim.claim_id
    assert views[0].tags == ("user_correction", "mechanism_boundary")


def test_ai_world_claim_reuses_p9_revision_chain(tmp_path):
    store, index, facts = _seed(tmp_path)
    service = AIWorldCognitionService(store=store, index=index)

    initial = service.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.USER_UNDERSTANDING,
            statement="用户偏好所有回答都非常详细。",
            evidence_refs=(ObjectRef(object_id=facts[0].object_id, revision=1),),
            confidence=0.45,
            scope_key="communication.detail_level",
        ),
        learned_at=NOW,
    )

    revised = service.revise(
        target_ref=ObjectRef(object_id=initial.claim.claim_id, revision=1),
        evidence_refs=(ObjectRef(object_id=facts[1].object_id, revision=1),),
        replacement_statement="用户更看重准确执行和必要细节，不要求所有回答都很长。",
        reason="新的直接反馈修正了此前过度概括的沟通偏好",
        confidence=0.88,
        changed_at=NOW + timedelta(seconds=1),
    )

    assert revised.new_revision == 2
    current = service.current(
        domains=[AIWorldDomain.USER_UNDERSTANDING],
        scope_key="communication.detail_level",
    )
    assert len(current) == 1
    assert current[0].revision == 2
    assert "不要求所有回答都很长" in current[0].statement
    assert store.get_payload(initial.claim.claim_id, revision=1)["content"] == "用户偏好所有回答都非常详细。"


def test_snapshot_contains_only_current_active_ai_world_claims(tmp_path):
    store, index, facts = _seed(tmp_path)
    service = AIWorldCognitionService(store=store, index=index)

    first = service.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.RELATIONSHIP,
            statement="当前关系是普通问答关系。",
            evidence_refs=(ObjectRef(object_id=facts[0].object_id, revision=1),),
            confidence=0.4,
            scope_key="working_relationship",
        ),
        learned_at=NOW,
    )
    service.revise(
        target_ref=ObjectRef(object_id=first.claim.claim_id, revision=1),
        evidence_refs=(ObjectRef(object_id=facts[0].object_id, revision=1),),
        replacement_statement="当前关系是长期项目协作关系。",
        reason="持续项目执行证据使关系理解发生变化",
        confidence=0.85,
        changed_at=NOW + timedelta(seconds=1),
    )

    snapshot = service.snapshot(per_domain=5)
    relation = snapshot["relationship"]
    assert len(relation) == 1
    assert relation[0]["revision"] == 2
    assert relation[0]["statement"] == "当前关系是长期项目协作关系。"


def test_all_p10_domains_are_typed_views_over_the_same_claim_engine(tmp_path):
    store, index, facts = _seed(tmp_path)
    service = AIWorldCognitionService(store=store, index=index)

    domains = [
        AIWorldDomain.USER_UNDERSTANDING,
        AIWorldDomain.RELATIONSHIP,
        AIWorldDomain.SELF,
        AIWorldDomain.INTENT,
        AIWorldDomain.STRATEGY,
        AIWorldDomain.COGNITIVE_BOUNDARY,
        AIWorldDomain.PERSONALITY,
        AIWorldDomain.CALIBRATION,
    ]
    for offset, domain in enumerate(domains):
        service.commit(
            AIWorldClaimRequest(
                domain=domain,
                statement=f"{domain.value} 的测试认知。",
                evidence_refs=(ObjectRef(object_id=facts[0].object_id, revision=1),),
                confidence=0.6 + offset * 0.01,
                scope_key=f"test.{domain.value}",
            ),
            learned_at=NOW + timedelta(seconds=offset),
        )

    snapshot = service.snapshot(per_domain=3)
    assert set(snapshot) == {domain.value for domain in AIWorldDomain}
    assert all(len(snapshot[domain.value]) == 1 for domain in domains)

    payloads = store.list_payloads()
    ai_claims = [
        item for item in payloads
        if item.get("object_type") == "claim"
        and (item.get("metadata") or {}).get("ai_world")
    ]
    assert len(ai_claims) == len(domains)
    assert {
        (item.get("metadata") or {}).get("dimension")
        for item in ai_claims
    } == {
        "dim:ai_user_understanding",
        "dim:ai_relationship",
        "dim:ai_self",
        "dim:ai_intent",
        "dim:ai_strategy",
        "dim:ai_cognitive_boundary",
        "dim:ai_personality",
        "dim:ai_calibration",
    }



def _seed_subject_isolation_world(tmp_path):
    db = tmp_path / "subject_isolation.db"
    store = SQLiteWorldStore(db)
    facts = {
        "user_A": Observation(
            object_id="obs_subject_isolation_a",
            subject_id="user_A",
            occurred=TemporalExtent.point(NOW - timedelta(days=2)),
            learned_at=NOW - timedelta(days=2),
            recorded_at=NOW - timedelta(days=2),
            created_by="c15-subject-isolation",
            source_kind="conversation",
            modality="text",
            value="User A evidence",
            metadata={"dimension": "dim:user_ai_interaction"},
        ),
        "user_B": Observation(
            object_id="obs_subject_isolation_b",
            subject_id="user_B",
            occurred=TemporalExtent.point(NOW - timedelta(days=1)),
            learned_at=NOW - timedelta(days=1),
            recorded_at=NOW - timedelta(days=1),
            created_by="c15-subject-isolation",
            source_kind="conversation",
            modality="text",
            value="User B evidence",
            metadata={"dimension": "dim:user_ai_interaction"},
        ),
    }
    store.commit(
        list(facts.values()),
        OperationRequest(
            operation_name="test.seed.c15.subject_isolation",
            expected_world_revision=0,
            reason="seed two-subject C15 isolation evidence",
            idempotency_key="c15-subject-isolation-seed",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, facts


def _commit_for_subject(service, *, domain, evidence, statement, scope_key, tags=()):
    return service.commit(
        AIWorldClaimRequest(
            domain=domain,
            statement=statement,
            evidence_refs=(ObjectRef(object_id=evidence.object_id, revision=1),),
            confidence=0.9,
            scope_key=scope_key,
            tags=tags,
        ),
        learned_at=NOW,
    )


def test_user_understanding_current_isolated_by_service_user(tmp_path):
    store, index, facts = _seed_subject_isolation_world(tmp_path)
    service_a = AIWorldCognitionService(store=store, index=index, user_id="user_A")
    service_b = AIWorldCognitionService(store=store, index=index, user_id="user_B")
    a = _commit_for_subject(
        service_a,
        domain=AIWorldDomain.USER_UNDERSTANDING,
        evidence=facts["user_A"],
        statement="User A prefers terse status reports.",
        scope_key="communication.style",
    )
    b = _commit_for_subject(
        service_b,
        domain=AIWorldDomain.USER_UNDERSTANDING,
        evidence=facts["user_B"],
        statement="User B prefers detailed status reports.",
        scope_key="communication.style",
    )

    current = service_b.current(domains=[AIWorldDomain.USER_UNDERSTANDING])

    assert {item.object_id for item in current} == {b.claim.claim_id}
    assert a.claim.claim_id not in {item.object_id for item in current}


def test_relationship_current_isolated_by_service_user(tmp_path):
    store, index, facts = _seed_subject_isolation_world(tmp_path)
    service_a = AIWorldCognitionService(store=store, index=index, user_id="user_A")
    service_b = AIWorldCognitionService(store=store, index=index, user_id="user_B")
    a = _commit_for_subject(
        service_a,
        domain=AIWorldDomain.RELATIONSHIP,
        evidence=facts["user_A"],
        statement="User A relationship cognition.",
        scope_key="relationship.current",
    )
    b = _commit_for_subject(
        service_b,
        domain=AIWorldDomain.RELATIONSHIP,
        evidence=facts["user_B"],
        statement="User B relationship cognition.",
        scope_key="relationship.current",
    )

    current = service_b.current(domains=[AIWorldDomain.RELATIONSHIP])

    assert {item.object_id for item in current} == {b.claim.claim_id}
    assert a.claim.claim_id not in {item.object_id for item in current}


def test_strategy_current_isolated_by_service_user(tmp_path):
    store, index, facts = _seed_subject_isolation_world(tmp_path)
    service_a = AIWorldCognitionService(store=store, index=index, user_id="user_A")
    service_b = AIWorldCognitionService(store=store, index=index, user_id="user_B")
    a = _commit_for_subject(
        service_a,
        domain=AIWorldDomain.STRATEGY,
        evidence=facts["user_A"],
        statement="User A strategy cognition.",
        scope_key="strategy.delivery",
    )
    b = _commit_for_subject(
        service_b,
        domain=AIWorldDomain.STRATEGY,
        evidence=facts["user_B"],
        statement="User B strategy cognition.",
        scope_key="strategy.delivery",
    )

    current = service_b.current(domains=[AIWorldDomain.STRATEGY])

    assert {item.object_id for item in current} == {b.claim.claim_id}
    assert a.claim.claim_id not in {item.object_id for item in current}


def test_core_context_does_not_cross_user_but_keeps_ai_self(tmp_path):
    store, index, facts = _seed_subject_isolation_world(tmp_path)
    service_a = AIWorldCognitionService(store=store, index=index, user_id="user_A")
    service_b = AIWorldCognitionService(store=store, index=index, user_id="user_B")
    user_claim = _commit_for_subject(
        service_a,
        domain=AIWorldDomain.USER_UNDERSTANDING,
        evidence=facts["user_A"],
        statement="User A core understanding.",
        scope_key="core.user",
        tags=("core_context",),
    )
    relationship_claim = _commit_for_subject(
        service_a,
        domain=AIWorldDomain.RELATIONSHIP,
        evidence=facts["user_A"],
        statement="User A core relationship.",
        scope_key="core.relationship",
        tags=("core_context",),
    )
    self_claim = _commit_for_subject(
        service_a,
        domain=AIWorldDomain.SELF,
        evidence=facts["user_A"],
        statement="Resident self cognition shared across users.",
        scope_key="core.self",
        tags=("core_context",),
    )

    context = service_b.core_context()
    flattened = {
        item["object_id"]
        for items in context.values()
        for item in items
    }

    assert user_claim.claim.claim_id not in flattened
    assert relationship_claim.claim.claim_id not in flattened
    assert self_claim.claim.claim_id in flattened



def test_core_context_filters_core_tag_before_domain_limit(tmp_path):
    store, index, facts = _seed(tmp_path)
    service = AIWorldCognitionService(store=store, index=index)

    core = service.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.USER_UNDERSTANDING,
            statement="用户长期要求 Resident 直接承担工程执行责任。",
            evidence_refs=(ObjectRef(object_id=facts[0].object_id, revision=1),),
            confidence=0.95,
            scope_key="collaboration.long_term_role",
            tags=("core_context",),
        ),
        learned_at=NOW,
    )

    for offset in range(1, 201):
        service.commit(
            AIWorldClaimRequest(
                domain=AIWorldDomain.USER_UNDERSTANDING,
                statement=f"普通非核心认知 {offset}",
                evidence_refs=(ObjectRef(object_id=facts[0].object_id, revision=1),),
                confidence=0.6,
                scope_key=f"ordinary.{offset}",
                tags=("ordinary",),
            ),
            learned_at=NOW + timedelta(seconds=offset),
        )

    context = service.core_context(per_domain=3)
    user_context = context["user_understanding"]

    assert [item["object_id"] for item in user_context] == [core.claim.claim_id]
    assert user_context[0]["scope_key"] == "collaboration.long_term_role"

def test_snapshot_does_not_cross_user_scoped_domains(tmp_path):
    store, index, facts = _seed_subject_isolation_world(tmp_path)
    service_a = AIWorldCognitionService(store=store, index=index, user_id="user_A")
    service_b = AIWorldCognitionService(store=store, index=index, user_id="user_B")
    a_claims = {
        _commit_for_subject(
            service_a,
            domain=domain,
            evidence=facts["user_A"],
            statement=f"User A {domain.value} cognition.",
            scope_key=f"scope.{domain.value}",
        ).claim.claim_id
        for domain in (
            AIWorldDomain.USER_UNDERSTANDING,
            AIWorldDomain.RELATIONSHIP,
            AIWorldDomain.STRATEGY,
        )
    }

    snapshot = service_b.snapshot()
    visible = {
        item["object_id"]
        for items in snapshot.values()
        for item in items
    }

    assert a_claims.isdisjoint(visible)


def test_self_continuity_preserved_across_user_services(tmp_path):
    store, index, facts = _seed_subject_isolation_world(tmp_path)
    service_a = AIWorldCognitionService(store=store, index=index, user_id="user_A")
    service_b = AIWorldCognitionService(store=store, index=index, user_id="user_B")
    self_claim = _commit_for_subject(
        service_a,
        domain=AIWorldDomain.SELF,
        evidence=facts["user_A"],
        statement="Resident durable self cognition.",
        scope_key="self.identity",
    )

    assert {item.object_id for item in service_a.current(domains=[AIWorldDomain.SELF])} == {
        self_claim.claim.claim_id
    }
    assert {item.object_id for item in service_b.current(domains=[AIWorldDomain.SELF])} == {
        self_claim.claim.claim_id
    }


def test_calibration_continuity_preserved_across_user_services(tmp_path):
    store, index, facts = _seed_subject_isolation_world(tmp_path)
    service_a = AIWorldCognitionService(store=store, index=index, user_id="user_A")
    service_b = AIWorldCognitionService(store=store, index=index, user_id="user_B")
    calibration = _commit_for_subject(
        service_a,
        domain=AIWorldDomain.CALIBRATION,
        evidence=facts["user_A"],
        statement="Resident durable calibration cognition.",
        scope_key="calibration.fact_state",
    )

    assert {item.object_id for item in service_a.current(domains=[AIWorldDomain.CALIBRATION])} == {
        calibration.claim.claim_id
    }
    assert {item.object_id for item in service_b.current(domains=[AIWorldDomain.CALIBRATION])} == {
        calibration.claim.claim_id
    }


def test_cross_user_typed_revise_is_rejected_for_user_scoped_domains(tmp_path):
    store, index, facts = _seed_subject_isolation_world(tmp_path)
    service_a = AIWorldCognitionService(store=store, index=index, user_id="user_A")
    service_b = AIWorldCognitionService(store=store, index=index, user_id="user_B")
    claims = [
        _commit_for_subject(
            service_a,
            domain=domain,
            evidence=facts["user_A"],
            statement=f"User A {domain.value} original.",
            scope_key=f"revise.{domain.value}",
        )
        for domain in (
            AIWorldDomain.USER_UNDERSTANDING,
            AIWorldDomain.RELATIONSHIP,
            AIWorldDomain.STRATEGY,
        )
    ]

    for receipt in claims:
        with pytest.raises(ValueError, match="subject"):
            service_b.revise(
                target_ref=ObjectRef(object_id=receipt.claim.claim_id, revision=1),
                evidence_refs=(ObjectRef(object_id=facts["user_B"].object_id, revision=1),),
                replacement_statement="Illegal cross-user replacement.",
                reason="must be rejected by typed facade subject authorization",
                confidence=0.8,
                changed_at=NOW + timedelta(seconds=1),
            )
        assert store.get_payload(receipt.claim.claim_id)["revision"] == 1


def test_cross_user_typed_retract_is_rejected_for_user_scoped_domains(tmp_path):
    store, index, facts = _seed_subject_isolation_world(tmp_path)
    service_a = AIWorldCognitionService(store=store, index=index, user_id="user_A")
    service_b = AIWorldCognitionService(store=store, index=index, user_id="user_B")
    claims = [
        _commit_for_subject(
            service_a,
            domain=domain,
            evidence=facts["user_A"],
            statement=f"User A {domain.value} original.",
            scope_key=f"retract.{domain.value}",
        )
        for domain in (
            AIWorldDomain.USER_UNDERSTANDING,
            AIWorldDomain.RELATIONSHIP,
            AIWorldDomain.STRATEGY,
        )
    ]

    for receipt in claims:
        with pytest.raises(ValueError, match="subject"):
            service_b.retract(
                target_ref=ObjectRef(object_id=receipt.claim.claim_id, revision=1),
                evidence_refs=(ObjectRef(object_id=facts["user_B"].object_id, revision=1),),
                reason="must be rejected by typed facade subject authorization",
                changed_at=NOW + timedelta(seconds=1),
            )
        assert store.get_payload(receipt.claim.claim_id)["revision"] == 1


@pytest.mark.parametrize("domain", [AIWorldDomain.SELF, AIWorldDomain.CALIBRATION])
def test_legitimate_ai_self_revision_still_works_across_current_user(tmp_path, domain):
    store, index, facts = _seed_subject_isolation_world(tmp_path)
    service_a = AIWorldCognitionService(store=store, index=index, user_id="user_A")
    service_b = AIWorldCognitionService(store=store, index=index, user_id="user_B")
    initial = _commit_for_subject(
        service_a,
        domain=domain,
        evidence=facts["user_A"],
        statement=f"Initial resident {domain.value}.",
        scope_key=f"resident.{domain.value}",
    )

    revised = service_b.revise(
        target_ref=ObjectRef(object_id=initial.claim.claim_id, revision=1),
        evidence_refs=(ObjectRef(object_id=facts["user_B"].object_id, revision=1),),
        replacement_statement=f"Revised resident {domain.value}.",
        reason="new current-user evidence updates valid AI-self cognition",
        confidence=0.92,
        changed_at=NOW + timedelta(seconds=1),
    )

    assert revised.new_revision == 2
    assert store.get_payload(initial.claim.claim_id)["subject_id"] == AI_SELF_SUBJECT_ID
    assert store.get_payload(initial.claim.claim_id)["revision"] == 2


@pytest.mark.parametrize(
    "metadata",
    [
        {"ai_world": False, "ai_domain": "user_understanding"},
        {"ai_world": True},
        {"ai_world": True, "ai_domain": "not_a_domain"},
    ],
)
@pytest.mark.parametrize("mode", ["revise", "retract"])
def test_typed_mutation_rejects_malformed_ai_world_metadata(tmp_path, metadata, mode):
    store, index, facts = _seed_subject_isolation_world(tmp_path)
    writer = CognitionWritebackService(
        store=store,
        index=index,
        subject_id="user_A",
        evidence_subject_ids=("user_A",),
    )
    malformed = writer.commit_claim(
        ClaimWriteRequest(
            content="Malformed typed facade target.",
            evidence_refs=(ObjectRef(object_id=facts["user_A"].object_id, revision=1),),
            confidence=0.8,
            dimension="dim:ai_user_understanding",
            claim_type=ClaimType.INFERENCE,
            knowledge_state=KnowledgeState.INFERRED,
            claimant_id="resident_ai",
            metadata=metadata,
        ),
        learned_at=NOW,
    )
    service_b = AIWorldCognitionService(store=store, index=index, user_id="user_B")
    target_ref = ObjectRef(object_id=malformed.claim_id, revision=1)
    evidence_refs = (ObjectRef(object_id=facts["user_B"].object_id, revision=1),)

    with pytest.raises(ValueError, match="AI-world"):
        if mode == "revise":
            service_b.revise(
                target_ref=target_ref,
                evidence_refs=evidence_refs,
                replacement_statement="Must not revise malformed typed target.",
                reason="fail closed on malformed metadata",
                changed_at=NOW + timedelta(seconds=1),
            )
        else:
            service_b.retract(
                target_ref=target_ref,
                evidence_refs=evidence_refs,
                reason="fail closed on malformed metadata",
                changed_at=NOW + timedelta(seconds=1),
            )
    assert store.get_payload(malformed.claim_id)["revision"] == 1
