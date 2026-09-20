from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import DimensionLifecycle, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.dimensions import (
    DimensionProposalRequest,
    DimensionRegistryService,
    DimensionTransitionRequest,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 20, 13, 20, tzinfo=timezone.utc)


def _seed(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs = Observation(
        object_id="obs_learning_pattern",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(days=1)),
        learned_at=NOW - timedelta(days=1),
        recorded_at=NOW - timedelta(days=1),
        created_by="p11-test",
        source_kind="conversation",
        modality="text",
        value="这段时间学习任务越来越复杂，用户能独立解决的问题明显增加。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    store.commit(
        [obs],
        OperationRequest(
            operation_name="test.seed.p11",
            expected_world_revision=0,
            reason="seed dimension evidence",
            idempotency_key="p11-seed",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, obs


def _request(obs):
    return DimensionProposalRequest(
        dimension_key="dim:learning_ability",
        name="学习能力",
        description="持续观察用户在不同学习任务中的独立解决能力变化。",
        data_shape="time_series_of_evidence_grounded_cognition",
        evidence_refs=(ObjectRef(object_id=obs.object_id, revision=1),),
        why_existing_dimensions_are_insufficient="现有聊天事实只记录发生了什么，不能持续表达能力变化这条观察轴。",
        continuity_rationale="该能力可以随长期学习事件持续更新，而不是一次性事件。",
        user_value_rationale="可以帮助AI判断教学难度和需要提供的支持程度。",
        maintenance_cost_rationale="只记录有证据的能力变化和周期总结，不复制原始学习数据。",
        confidence=0.74,
        update_method="AI基于学习事件、结果和反馈形成可修正Claim",
        expected_value="提高长期教学与帮助的个性化程度",
    )


def test_single_evidence_can_enter_candidate_without_legacy_semantic_thresholds(tmp_path):
    store, index, obs = _seed(tmp_path)
    service = DimensionRegistryService(store=store, index=index)

    receipt = service.propose(_request(obs), proposed_at=NOW)

    definition = store.get_payload(receipt.dimension_id)
    assert definition["lifecycle"] == "candidate"
    assert definition["metadata"]["dimension_key"] == "dim:learning_ability"
    assert definition["metadata"]["proposal"]["confidence"] == 0.74
    assert len(definition["source_refs"]) == 1

    # P11 intentionally has no 2-domain / 3-day / 30-day / 70% promotion gate.
    # The system records the AI proposal; semantic worth is evaluated through real use.
    assert receipt.lifecycle == "candidate"


def test_duplicate_dimension_key_is_rejected_deterministically(tmp_path):
    store, index, obs = _seed(tmp_path)
    service = DimensionRegistryService(store=store, index=index)
    service.propose(_request(obs), proposed_at=NOW)

    with pytest.raises(ValueError, match="already exists"):
        service.propose(_request(obs), proposed_at=NOW + timedelta(seconds=1))


def test_lifecycle_is_evidence_backed_but_not_semantically_hardcoded(tmp_path):
    store, index, obs = _seed(tmp_path)
    service = DimensionRegistryService(store=store, index=index)
    proposed = service.propose(_request(obs), proposed_at=NOW)

    trial = service.transition(
        DimensionTransitionRequest(
            dimension_ref=ObjectRef(object_id=proposed.dimension_id, revision=1),
            new_lifecycle=DimensionLifecycle.TRIAL,
            reason="AI认为该观察轴值得进入真实运行试用。",
            evidence_refs=(ObjectRef(object_id=obs.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(days=1),
    )
    active = service.transition(
        DimensionTransitionRequest(
            dimension_ref=ObjectRef(object_id=proposed.dimension_id, revision=2),
            new_lifecycle=DimensionLifecycle.ACTIVE,
            reason="试用期间持续产生可解释的新观察，AI决定正式保留。",
            evidence_refs=(ObjectRef(object_id=obs.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(days=2),
    )

    assert trial.previous_lifecycle == "candidate"
    assert trial.new_lifecycle == "trial"
    assert active.new_lifecycle == "active"

    assert store.get_payload(proposed.dimension_id, revision=1)["lifecycle"] == "candidate"
    assert store.get_payload(proposed.dimension_id, revision=2)["lifecycle"] == "trial"
    assert store.get_payload(proposed.dimension_id, revision=3)["lifecycle"] == "active"


def test_illegal_backward_transition_is_rejected(tmp_path):
    store, index, obs = _seed(tmp_path)
    service = DimensionRegistryService(store=store, index=index)
    proposed = service.propose(_request(obs), proposed_at=NOW)
    service.transition(
        DimensionTransitionRequest(
            dimension_ref=ObjectRef(object_id=proposed.dimension_id, revision=1),
            new_lifecycle=DimensionLifecycle.TRIAL,
            reason="进入试用。",
            evidence_refs=(ObjectRef(object_id=obs.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(hours=1),
    )
    service.transition(
        DimensionTransitionRequest(
            dimension_ref=ObjectRef(object_id=proposed.dimension_id, revision=2),
            new_lifecycle=DimensionLifecycle.ACTIVE,
            reason="AI决定正式保留。",
            evidence_refs=(ObjectRef(object_id=obs.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(hours=2),
    )

    with pytest.raises(ValueError, match="illegal dimension lifecycle transition"):
        service.transition(
            DimensionTransitionRequest(
                dimension_ref=ObjectRef(object_id=proposed.dimension_id, revision=3),
                new_lifecycle=DimensionLifecycle.CANDIDATE,
                reason="不允许倒退成候选。",
                evidence_refs=(ObjectRef(object_id=obs.object_id, revision=1),),
            ),
            changed_at=NOW + timedelta(hours=3),
        )


def test_archive_preserves_all_previous_dimension_revisions(tmp_path):
    store, index, obs = _seed(tmp_path)
    service = DimensionRegistryService(store=store, index=index)
    proposed = service.propose(_request(obs), proposed_at=NOW)
    service.transition(
        DimensionTransitionRequest(
            dimension_ref=ObjectRef(object_id=proposed.dimension_id, revision=1),
            new_lifecycle=DimensionLifecycle.TRIAL,
            reason="试用。",
            evidence_refs=(ObjectRef(object_id=obs.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(days=1),
    )
    service.transition(
        DimensionTransitionRequest(
            dimension_ref=ObjectRef(object_id=proposed.dimension_id, revision=2),
            new_lifecycle=DimensionLifecycle.ACTIVE,
            reason="正式激活。",
            evidence_refs=(ObjectRef(object_id=obs.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(days=2),
    )
    archived = service.transition(
        DimensionTransitionRequest(
            dimension_ref=ObjectRef(object_id=proposed.dimension_id, revision=3),
            new_lifecycle=DimensionLifecycle.ARCHIVED,
            reason="长期观察后AI认为该维度已无继续维护价值。",
            evidence_refs=(ObjectRef(object_id=obs.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(days=100),
    )

    assert archived.new_lifecycle == "archived"
    assert store.get_payload(proposed.dimension_id, revision=1)["lifecycle"] == "candidate"
    assert store.get_payload(proposed.dimension_id, revision=3)["lifecycle"] == "active"
    assert store.get_payload(proposed.dimension_id, revision=4)["lifecycle"] == "archived"
