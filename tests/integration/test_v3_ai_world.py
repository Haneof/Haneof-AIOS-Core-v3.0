import sqlite3
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
