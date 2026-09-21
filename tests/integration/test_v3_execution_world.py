from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import (
    ClaimType,
    GoalSourceType,
    GoalStatus,
    KnowledgeState,
    SourceClass,
    TaskState,
    TaskType,
)
from aios_core.contracts.models import Claim, EvidenceSet, Observation, Outcome, Task
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import KnowledgeWindow, TemporalExtent
from aios_core.execution import (
    ActionOutcomeRequest,
    ActionProposalRequest,
    GoalCreateRequest,
    GoalTaskActionService,
    GoalTransitionRequest,
    TaskCreateRequest,
    TaskTransitionRequest,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 20, 14, 40, tzinfo=timezone.utc)


def _seed(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    intent = Observation(
        object_id="obs_user_goal_p12",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(days=1)),
        learned_at=NOW - timedelta(days=1),
        recorded_at=NOW - timedelta(days=1),
        created_by="p12-test",
        source_kind="conversation",
        modality="text",
        value="明天下午提醒我把项目周报发给团队。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    authorization = Observation(
        object_id="obs_user_auth_p12",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="p12-test",
        source_kind="conversation",
        modality="text",
        value="到时间后可以直接把我确认过的周报发到团队频道。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    store.commit(
        [intent, authorization],
        OperationRequest(
            operation_name="test.seed.p12",
            expected_world_revision=0,
            reason="seed P12 intent and authorization",
            idempotency_key="p12-seed",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, intent, authorization


def _active_goal_and_running_task(store, index, intent):
    service = GoalTaskActionService(store=store, index=index)
    goal = service.create_goal(
        GoalCreateRequest(
            source_type=GoalSourceType.USER_EXPLICIT,
            title="完成项目周报发送",
            description="在用户指定时间把确认后的周报发给团队。",
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
            confidence=0.99,
            success_criteria=("团队收到用户确认过的周报",),
        ),
        created_at=NOW,
    )
    goal_active = service.transition_goal(
        GoalTransitionRequest(
            goal_ref=ObjectRef(object_id=goal.goal_id, revision=1),
            new_status=GoalStatus.ACTIVE,
            reason="用户明确提出该目标。",
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(seconds=1),
    )
    task = service.create_task(
        TaskCreateRequest(
            title="发送已确认周报",
            task_type=TaskType.SCHEDULED,
            reason_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
            goal_ref=ObjectRef(
                object_id=goal.goal_id,
                revision=goal_active.revision,
            ),
            initial_state=TaskState.READY,
            priority=70,
        ),
        created_at=NOW + timedelta(seconds=2),
    )
    running = service.transition_task(
        TaskTransitionRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=1),
            new_state=TaskState.RUNNING,
            reason="开始准备执行周报发送任务。",
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(seconds=3),
    )
    return service, goal_active, running


def test_goal_and_task_are_forward_revised_world_objects(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service, goal, task = _active_goal_and_running_task(store, index, intent)

    assert store.get_payload(goal.goal_id, revision=1)["goal_status"] == "proposed"
    assert store.get_payload(goal.goal_id, revision=2)["goal_status"] == "active"
    assert store.get_payload(task.task_id, revision=1)["task_state"] == "ready"
    assert store.get_payload(task.task_id, revision=2)["task_state"] == "running"

    current_goal = service.current_goals()
    current_task = service.current_tasks()
    assert len(current_goal) == 1
    assert current_goal[0].revision == 2
    assert len(current_task) == 1
    assert current_task[0].revision == 2


def test_scheduler_wakes_due_task_without_inventing_new_goal(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service = GoalTaskActionService(store=store, index=index)
    task = service.create_task(
        TaskCreateRequest(
            title="明天下午提醒周报",
            task_type=TaskType.SCHEDULED,
            reason_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
            initial_state=TaskState.WAITING_TIME,
            next_wake_at=NOW + timedelta(hours=2),
            deadline=NOW + timedelta(hours=5),
            timezone_name="UTC",
        ),
        created_at=NOW,
    )

    assert service.wake_due_tasks(now=NOW + timedelta(hours=1)) == ()
    wakes = service.wake_due_tasks(now=NOW + timedelta(hours=2, seconds=1))
    assert len(wakes) == 1
    assert wakes[0].task_id == task.task_id
    assert wakes[0].new_state == "ready"
    assert store.get_payload(task.task_id, revision=1)["task_state"] == "waiting_time"
    assert store.get_payload(task.task_id)["task_state"] == "ready"
    assert store.get_payload(wakes[0].wake_id)["wake_source"] == "task_due"


def test_model_proposal_cannot_authorize_external_action_by_itself(tmp_path):
    store, index, intent, authorization = _seed(tmp_path)
    service, _, task = _active_goal_and_running_task(store, index, intent)

    action = service.propose_action(
        ActionProposalRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            action_type="send_team_message",
            payload={"channel": "team", "document": "weekly-report"},
            expected_outcome="团队频道收到已确认周报",
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        proposed_at=NOW + timedelta(seconds=4),
    )

    denied_calls = 0

    def deny(_action, _refs):
        nonlocal denied_calls
        denied_calls += 1
        return False

    with pytest.raises(PermissionError, match="authorization denied"):
        service.authorize_action(
            action_ref=ObjectRef(object_id=action.action_id, revision=1),
            authorization_refs=(
                ObjectRef(object_id=authorization.object_id, revision=1),
            ),
            authorized_by="platform_permission_gate",
            authorized_at=NOW + timedelta(seconds=5),
            authorizer=deny,
        )

    assert denied_calls == 1
    latest = store.get_payload(action.action_id)
    assert latest["revision"] == 1
    assert latest["action_status"] == "proposed"


def test_authorized_action_dispatch_and_real_outcome_close_task_loop(tmp_path):
    store, index, intent, authorization = _seed(tmp_path)
    service, _, task = _active_goal_and_running_task(store, index, intent)

    action = service.propose_action(
        ActionProposalRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            action_type="send_team_message",
            payload={"channel": "team", "document": "weekly-report"},
            expected_outcome="团队频道收到已确认周报",
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        proposed_at=NOW + timedelta(seconds=4),
    )

    envelope = service.authorize_action(
        action_ref=ObjectRef(object_id=action.action_id, revision=1),
        authorization_refs=(
            ObjectRef(object_id=authorization.object_id, revision=1),
        ),
        authorized_by="platform_permission_gate",
        authorized_at=NOW + timedelta(seconds=5),
        authorizer=lambda _action, refs: bool(refs),
    )

    assert envelope.revision == 2
    assert envelope.execution_id == action.execution_id
    assert store.get_payload(action.action_id)["action_status"] == "submitted"

    # The external platform performs the side effect outside AIOS Core using
    # execution_id as its idempotency key, then reports the actual result.
    outcome = service.record_outcome(
        ActionOutcomeRequest(
            action_ref=ObjectRef(object_id=action.action_id, revision=2),
            outcome_state="completed",
            payload={
                "provider_message_id": "msg-123",
                "delivery": "accepted",
            },
        ),
        recorded_at=NOW + timedelta(seconds=6),
    )

    assert store.get_payload(action.action_id, revision=1)["action_status"] == "proposed"
    assert store.get_payload(action.action_id, revision=2)["action_status"] == "submitted"
    assert store.get_payload(action.action_id, revision=3)["action_status"] == "completed"
    assert store.commit_source_class(envelope.world_revision) == SourceClass.PLATFORM.value
    assert store.commit_source_class(outcome.world_revision) == SourceClass.PLATFORM.value
    assert store.get_payload(outcome.outcome_id)["outcome_state"] == "completed"

    completed = service.transition_task(
        TaskTransitionRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            new_state=TaskState.COMPLETED,
            reason="外部平台确认团队频道已接收周报。",
            evidence_refs=(ObjectRef(object_id=outcome.outcome_id, revision=1),),
            execution_refs=(ObjectRef(object_id=action.action_id, revision=3),),
            outcome_refs=(ObjectRef(object_id=outcome.outcome_id, revision=1),),
        ),
        changed_at=NOW + timedelta(seconds=7),
    )
    assert completed.state == "completed"
    assert store.get_payload(task.task_id)["outcome_refs"] == [
        {"object_id": outcome.outcome_id, "revision": 1}
    ]


def test_submitted_action_cannot_be_dispatched_twice(tmp_path):
    store, index, intent, authorization = _seed(tmp_path)
    service, _, task = _active_goal_and_running_task(store, index, intent)
    action = service.propose_action(
        ActionProposalRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            action_type="send_team_message",
            payload={"channel": "team"},
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        proposed_at=NOW + timedelta(seconds=4),
    )
    service.authorize_action(
        action_ref=ObjectRef(object_id=action.action_id, revision=1),
        authorization_refs=(
            ObjectRef(object_id=authorization.object_id, revision=1),
        ),
        authorized_by="platform_permission_gate",
        authorized_at=NOW + timedelta(seconds=5),
        authorizer=lambda _action, _refs: True,
    )

    with pytest.raises(ValueError, match="not current"):
        service.authorize_action(
            action_ref=ObjectRef(object_id=action.action_id, revision=1),
            authorization_refs=(
                ObjectRef(object_id=authorization.object_id, revision=1),
            ),
            authorized_by="platform_permission_gate",
            authorized_at=NOW + timedelta(seconds=6),
            authorizer=lambda _action, _refs: True,
        )

    assert store.get_payload(action.action_id)["revision"] == 2
    assert store.get_payload(action.action_id)["action_status"] == "submitted"


def test_external_action_task_cannot_use_observation_to_bypass_outcome(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service, _, task = _active_goal_and_running_task(store, index, intent)

    request = TaskTransitionRequest(
        task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
        new_state=TaskState.COMPLETED,
        reason="不能只靠普通 Observation 宣布外部发送已经完成。",
        evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
    )
    with pytest.raises(ValueError, match="ACTION_OUTCOME.*real outcome_refs"):
        service.transition_task(
            request,
            changed_at=NOW + timedelta(seconds=8),
        )


def test_action_and_outcome_are_retrievable_world_anchors(tmp_path):
    store, index, intent, authorization = _seed(tmp_path)
    service, _, task = _active_goal_and_running_task(store, index, intent)

    action = service.propose_action(
        ActionProposalRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            action_type="send_team_message",
            payload={"channel": "team"},
            expected_outcome="团队频道收到确认周报",
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        proposed_at=NOW + timedelta(seconds=4),
    )
    service.authorize_action(
        action_ref=ObjectRef(object_id=action.action_id, revision=1),
        authorization_refs=(
            ObjectRef(object_id=authorization.object_id, revision=1),
        ),
        authorized_by="platform_permission_gate",
        authorized_at=NOW + timedelta(seconds=5),
        authorizer=lambda _action, _refs: True,
    )
    outcome = service.record_outcome(
        ActionOutcomeRequest(
            action_ref=ObjectRef(object_id=action.action_id, revision=2),
            outcome_state="completed",
            payload={"delivery": "accepted"},
        ),
        recorded_at=NOW + timedelta(seconds=6),
    )

    action_hits = index.recall_candidates(
        "团队频道收到确认周报",
        object_types=["action"],
    )
    assert action.action_id in {hit.object_id for hit in action_hits.hits}

    outcome_hits = index.recall_candidates(
        "completed",
        object_types=["outcome"],
    )
    assert outcome.outcome_id in {hit.object_id for hit in outcome_hits.hits}


def test_cancelled_parent_task_cannot_authorize_retry_or_restart(tmp_path):
    store, index, intent, authorization = _seed(tmp_path)
    service, _, task = _active_goal_and_running_task(store, index, intent)
    action = service.propose_action(
        ActionProposalRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            action_type="send_team_message",
            payload={"channel": "team", "document": "weekly-report"},
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        proposed_at=NOW + timedelta(seconds=4),
    )

    cancelled = service.transition_task(
        TaskTransitionRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            new_state=TaskState.CANCELLED,
            reason="用户撤销发送请求。",
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(seconds=5),
    )
    assert cancelled.state == "cancelled"
    assert store.get_payload(task.task_id)["task_state"] == "cancelled"
    cancelled_world_revision = cancelled.world_revision

    authorizer_calls = 0

    def allow(_action, _refs):
        nonlocal authorizer_calls
        authorizer_calls += 1
        return True

    restarted_store = SQLiteWorldStore(tmp_path / "world.db")
    restarted_service = GoalTaskActionService(store=restarted_store)

    for candidate in (service, restarted_service):
        with pytest.raises(ValueError):
            candidate.authorize_action(
                action_ref=ObjectRef(object_id=action.action_id, revision=1),
                authorization_refs=(
                    ObjectRef(object_id=authorization.object_id, revision=1),
                ),
                authorized_by="platform_permission_gate",
                authorized_at=NOW + timedelta(seconds=6),
                authorizer=allow,
            )

    # Task cancellation must forward-invalidate the pending proposal without
    # rewriting history. Retry/restart therefore fail before the authorizer is
    # consulted, while the original PROPOSED revision remains auditable.
    assert authorizer_calls == 0
    assert store.current_world_revision() == cancelled_world_revision
    assert store.get_payload(action.action_id, revision=1)["action_status"] == "proposed"
    latest_action = store.get_payload(action.action_id)
    assert latest_action["revision"] == 2
    assert latest_action["action_status"] == "cancelled"
    assert latest_action["status"] == "cancelled"


def test_restart_rejects_legacy_proposed_action_with_cancelled_parent(tmp_path):
    store, index, intent, authorization = _seed(tmp_path)
    service, _, task = _active_goal_and_running_task(store, index, intent)
    action = service.propose_action(
        ActionProposalRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            action_type="send_team_message",
            payload={"channel": "team"},
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        proposed_at=NOW + timedelta(seconds=4),
    )

    # Reconstruct the durable shape produced by pre-T34 Core: parent Task has
    # advanced to CANCELLED, but the pending Action still has only PROPOSED rev1.
    # This bypasses the new transition service only to model an existing World
    # written before forward invalidation existed.
    task_payload = store.get_payload(task.task_id)
    legacy_cancelled_task = Task.model_validate(
        {
            **task_payload,
            "revision": task.revision + 1,
            "occurred": TemporalExtent.point(NOW + timedelta(seconds=5)),
            "learned_at": NOW + timedelta(seconds=5),
            "recorded_at": NOW + timedelta(seconds=5),
            "task_state": TaskState.CANCELLED,
            "status": TaskState.CANCELLED.value,
        }
    )
    store.commit(
        [legacy_cancelled_task],
        OperationRequest(
            operation_name="test.seed.pre_t34_cancelled_parent",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed persisted pre-T34 cancelled Task with pending Action",
            idempotency_key="test-pre-t34-cancelled-parent",
            source_class=SourceClass.USER,
        ),
    )
    world_revision_before_retry = int(store.current_world_revision())
    assert store.get_payload(action.action_id)["action_status"] == "proposed"

    restarted_store = SQLiteWorldStore(tmp_path / "world.db")
    restarted_service = GoalTaskActionService(store=restarted_store)
    authorizer_calls = 0

    def allow(_action, _refs):
        nonlocal authorizer_calls
        authorizer_calls += 1
        return True

    with pytest.raises(ValueError, match="parent Task"):
        restarted_service.authorize_action(
            action_ref=ObjectRef(object_id=action.action_id, revision=1),
            authorization_refs=(
                ObjectRef(object_id=authorization.object_id, revision=1),
            ),
            authorized_by="platform_permission_gate",
            authorized_at=NOW + timedelta(seconds=6),
            authorizer=allow,
        )

    assert authorizer_calls == 0
    assert restarted_store.current_world_revision() == world_revision_before_retry
    assert restarted_store.get_payload(action.action_id, revision=1)["action_status"] == "proposed"
    assert restarted_store.get_payload(action.action_id)["revision"] == 1


def test_cancel_authorize_race_is_fail_closed(tmp_path):
    store, index, intent, authorization = _seed(tmp_path)
    service, _, task = _active_goal_and_running_task(store, index, intent)
    action = service.propose_action(
        ActionProposalRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            action_type="send_team_message",
            payload={"channel": "team"},
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        proposed_at=NOW + timedelta(seconds=4),
    )

    def allow_after_user_cancel(_action, _refs):
        service.transition_task(
            TaskTransitionRequest(
                task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
                new_state=TaskState.CANCELLED,
                reason="授权等待期间用户撤销发送请求。",
                evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
            ),
            changed_at=NOW + timedelta(seconds=5),
        )
        return True

    with pytest.raises(ValueError):
        service.authorize_action(
            action_ref=ObjectRef(object_id=action.action_id, revision=1),
            authorization_refs=(
                ObjectRef(object_id=authorization.object_id, revision=1),
            ),
            authorized_by="platform_permission_gate",
            authorized_at=NOW + timedelta(seconds=6),
            authorizer=allow_after_user_cancel,
        )

    assert store.get_payload(task.task_id)["task_state"] == "cancelled"
    assert store.get_payload(action.action_id, revision=1)["action_status"] == "proposed"
    assert store.get_payload(action.action_id)["action_status"] == "cancelled"


def _running_evidence_task(
    service,
    intent,
    *,
    title,
    task_type=TaskType.VERIFICATION,
    completion_condition=None,
    created_offset=20,
):
    task = service.create_task(
        TaskCreateRequest(
            title=title,
            task_type=task_type,
            reason_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
            initial_state=TaskState.READY,
            completion_condition=dict(completion_condition or {}),
        ),
        created_at=NOW + timedelta(seconds=created_offset),
    )
    return service.transition_task(
        TaskTransitionRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            new_state=TaskState.RUNNING,
            reason="开始执行非外部副作用任务。",
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(seconds=created_offset + 1),
    )


def _commit_observation(
    store,
    *,
    object_id,
    value,
    subject_id="user_1",
    created_by="p12-test:trusted-source",
    source_class=SourceClass.USER,
    metadata=None,
    offset=30,
):
    observation = Observation(
        object_id=object_id,
        subject_id=subject_id,
        occurred=TemporalExtent.point(NOW + timedelta(seconds=offset)),
        learned_at=NOW + timedelta(seconds=offset),
        recorded_at=NOW + timedelta(seconds=offset),
        created_by=created_by,
        source_kind="test",
        modality="text",
        value=value,
        metadata=dict(metadata or {}),
    )
    store.commit(
        [observation],
        OperationRequest(
            operation_name=f"test.seed.{object_id}",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed T35 durable completion evidence",
            idempotency_key=f"t35-seed:{object_id}",
            source_class=source_class,
        ),
    )
    return observation


def test_non_action_verification_task_completes_from_real_world_evidence(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service = GoalTaskActionService(store=store, index=index)
    task = _running_evidence_task(
        service,
        intent,
        title="验证上传文件已经通过校验",
        completion_condition={"mode": "WORLD_EVIDENCE"},
    )
    verified = _commit_observation(
        store,
        object_id="obs_t35_verified",
        value="deterministic validator: checksum and schema validation passed",
        source_class=SourceClass.PLATFORM,
    )

    completed = service.transition_task(
        TaskTransitionRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            new_state=TaskState.COMPLETED,
            reason="平台校验结果已作为 durable Observation 写入 World。",
            evidence_refs=(ObjectRef(object_id=verified.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(seconds=40),
    )

    latest = store.get_payload(task.task_id)
    assert completed.state == "completed"
    assert latest["outcome_refs"] == []
    assert latest["metadata"]["terminal_completion_mode"] == "world_evidence"
    assert latest["metadata"]["task_state_history"][-1]["evidence_refs"] == [
        {"object_id": verified.object_id, "revision": 1}
    ]


def test_legacy_verification_without_mode_uses_narrow_world_evidence_compatibility(
    tmp_path,
):
    store, index, intent, _ = _seed(tmp_path)
    service = GoalTaskActionService(store=store, index=index)
    task = _running_evidence_task(
        service,
        intent,
        title="核验现有 World 状态",
        completion_condition={},
    )
    verified = _commit_observation(
        store,
        object_id="obs_t35_legacy_verified",
        value="trusted verifier confirms the existing state",
        source_class=SourceClass.PLATFORM,
        offset=31,
    )

    completed = service.transition_task(
        TaskTransitionRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            new_state=TaskState.COMPLETED,
            reason="旧 verification Task 使用窄兼容规则。",
            evidence_refs=(ObjectRef(object_id=verified.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(seconds=41),
    )
    assert completed.state == "completed"
    assert store.get_payload(task.task_id)["metadata"]["terminal_completion_mode"] == (
        "world_evidence"
    )


def test_information_review_task_completes_from_supported_current_claim(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service = GoalTaskActionService(store=store, index=index)
    evidence = EvidenceSet(
        object_id="evs_t35_review",
        subject_id="user_1",
        learned_at=NOW + timedelta(seconds=32),
        recorded_at=NOW + timedelta(seconds=32),
        created_by="periodic_review:test",
        purpose="support review conclusion",
        knowledge_window=KnowledgeWindow(
            knowledge_cutoff=NOW + timedelta(seconds=32),
            world_revision=int(store.current_world_revision()),
        ),
        member_refs=[ObjectRef(object_id=intent.object_id, revision=1)],
        support_refs=[ObjectRef(object_id=intent.object_id, revision=1)],
        selection_method="pinned_test_evidence",
    )
    store.commit(
        [evidence],
        OperationRequest(
            operation_name="test.seed.t35.review_evidence",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed supported review evidence",
            idempotency_key="t35-review-evidence",
            source_class=SourceClass.AI_COGNITION,
        ),
    )
    claim = Claim(
        object_id="claim_t35_review",
        subject_id="user_1",
        learned_at=NOW + timedelta(seconds=33),
        recorded_at=NOW + timedelta(seconds=33),
        created_by="periodic_review:resident_ai",
        claimant_id="resident_ai",
        claim_type=ClaimType.INFERENCE,
        content="The reviewed evidence supports the requested internal conclusion.",
        asserted_at=NOW + timedelta(seconds=33),
        knowledge_state=KnowledgeState.INFERRED,
        confidence=0.9,
        support_evidence_set_refs=[
            ObjectRef(object_id=evidence.object_id, revision=1)
        ],
    )
    store.commit(
        [claim],
        OperationRequest(
            operation_name="test.seed.t35.review_claim",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed evidence-grounded review work product",
            idempotency_key="t35-review-claim",
            source_class=SourceClass.AI_COGNITION,
        ),
    )

    task = _running_evidence_task(
        service,
        intent,
        title="审查证据并形成可追溯结论",
        task_type=TaskType.MAINTENANCE,
        completion_condition={
            "mode": "world_evidence",
            "result_object_types": ["claim"],
        },
        created_offset=34,
    )
    completed = service.transition_task(
        TaskTransitionRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            new_state=TaskState.COMPLETED,
            reason="所需 evidence-grounded Claim 已形成。",
            evidence_refs=(ObjectRef(object_id=claim.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(seconds=42),
    )
    assert completed.state == "completed"
    assert store.get_payload(task.task_id)["outcome_refs"] == []


def test_assistant_raw_dialogue_cannot_complete_world_evidence_task(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service = GoalTaskActionService(store=store, index=index)
    assistant = _commit_observation(
        store,
        object_id="obs_t35_assistant_self_claim",
        value="I checked it and it is done.",
        created_by="conversation_ingest:assistant",
        source_class=SourceClass.AI_COGNITION,
        metadata={"role": "assistant"},
        offset=35,
    )
    task = _running_evidence_task(
        service,
        intent,
        title="验证真实状态",
        completion_condition={"mode": "world_evidence"},
        created_offset=36,
    )

    with pytest.raises(ValueError, match="assistant raw dialogue"):
        service.transition_task(
            TaskTransitionRequest(
                task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
                new_state=TaskState.COMPLETED,
                reason="模型自己的话不能成为完成事实。",
                evidence_refs=(ObjectRef(object_id=assistant.object_id, revision=1),),
            ),
            changed_at=NOW + timedelta(seconds=43),
        )


def test_synthetic_outcome_cannot_complete_external_action_task(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service, _, task = _active_goal_and_running_task(store, index, intent)
    action = service.propose_action(
        ActionProposalRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            action_type="send_team_message",
            payload={"channel": "team"},
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        proposed_at=NOW + timedelta(seconds=44),
    )
    synthetic = Outcome(
        object_id="outcome_t35_synthetic",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW + timedelta(seconds=45)),
        learned_at=NOW + timedelta(seconds=45),
        recorded_at=NOW + timedelta(seconds=45),
        created_by="test:synthetic_outcome",
        action_ref=ObjectRef(object_id=action.action_id, revision=1),
        outcome_state="completed",
        payload={"fake": True},
    )
    store.commit(
        [synthetic],
        OperationRequest(
            operation_name="test.seed.synthetic_outcome",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed synthetic outcome to prove T35 rejects it",
            idempotency_key="t35-synthetic-outcome",
            source_class=SourceClass.AI_COGNITION,
        ),
    )

    with pytest.raises(ValueError, match="synthetic Outcome"):
        service.transition_task(
            TaskTransitionRequest(
                task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
                new_state=TaskState.COMPLETED,
                reason="伪 Outcome 不得闭环外部任务。",
                evidence_refs=(
                    ObjectRef(object_id=synthetic.object_id, revision=1),
                ),
                execution_refs=(
                    ObjectRef(object_id=action.action_id, revision=1),
                ),
                outcome_refs=(
                    ObjectRef(object_id=synthetic.object_id, revision=1),
                ),
            ),
            changed_at=NOW + timedelta(seconds=46),
        )


def test_unsupported_claim_cannot_complete_task(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service = GoalTaskActionService(store=store, index=index)
    claim = Claim(
        object_id="claim_t35_unsupported",
        subject_id="user_1",
        learned_at=NOW + timedelta(seconds=47),
        recorded_at=NOW + timedelta(seconds=47),
        created_by="test:model_only_claim",
        claimant_id="resident_ai",
        claim_type=ClaimType.INFERENCE,
        content="Unsupported model conclusion.",
        asserted_at=NOW + timedelta(seconds=47),
        knowledge_state=KnowledgeState.INFERRED,
        confidence=0.6,
    )
    store.commit(
        [claim],
        OperationRequest(
            operation_name="test.seed.unsupported_claim",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed unsupported claim",
            idempotency_key="t35-unsupported-claim",
            source_class=SourceClass.AI_COGNITION,
        ),
    )
    task = _running_evidence_task(
        service,
        intent,
        title="形成有证据的结论",
        task_type=TaskType.MAINTENANCE,
        completion_condition={
            "mode": "world_evidence",
            "result_object_types": ["claim"],
        },
        created_offset=48,
    )

    with pytest.raises(ValueError, match="unsupported Claim"):
        service.transition_task(
            TaskTransitionRequest(
                task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
                new_state=TaskState.COMPLETED,
                reason="无支持证据的 Claim 不得完成任务。",
                evidence_refs=(ObjectRef(object_id=claim.object_id, revision=1),),
            ),
            changed_at=NOW + timedelta(seconds=49),
        )


def test_non_action_failed_requires_real_failure_evidence(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service = GoalTaskActionService(store=store, index=index)
    task = _running_evidence_task(
        service,
        intent,
        title="验证构件是否有效",
        completion_condition={"mode": "world_evidence"},
        created_offset=50,
    )
    failed_validation = _commit_observation(
        store,
        object_id="obs_t35_validation_failed",
        value="deterministic validator reports artifact invalid",
        source_class=SourceClass.PLATFORM,
        offset=51,
    )
    failed = service.transition_task(
        TaskTransitionRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            new_state=TaskState.FAILED,
            reason="明确的 deterministic validation failure 已持久化。",
            evidence_refs=(
                ObjectRef(object_id=failed_validation.object_id, revision=1),
            ),
        ),
        changed_at=NOW + timedelta(seconds=52),
    )
    assert failed.state == "failed"

    task2 = _running_evidence_task(
        service,
        intent,
        title="另一个验证任务",
        completion_condition={"mode": "world_evidence"},
        created_offset=53,
    )
    with pytest.raises(ValueError, match="not permitted"):
        service.transition_task(
            TaskTransitionRequest(
                task_ref=ObjectRef(object_id=task2.task_id, revision=task2.revision),
                new_state=TaskState.FAILED,
                reason="不能因为模型说失败就 FAILED。",
                evidence_refs=(
                    ObjectRef(object_id=task2.task_id, revision=task2.revision),
                ),
            ),
            changed_at=NOW + timedelta(seconds=54),
        )


def test_cross_subject_completion_evidence_is_rejected(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service = GoalTaskActionService(store=store, index=index)
    foreign = _commit_observation(
        store,
        object_id="obs_t35_other_subject",
        value="foreign subject verification",
        subject_id="user_2",
        offset=55,
    )
    task = _running_evidence_task(
        service,
        intent,
        title="同 subject 核验",
        completion_condition={"mode": "world_evidence"},
        created_offset=56,
    )
    with pytest.raises(ValueError, match="crosses the runtime subject scope"):
        service.transition_task(
            TaskTransitionRequest(
                task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
                new_state=TaskState.COMPLETED,
                reason="跨 subject 证据不得使用。",
                evidence_refs=(ObjectRef(object_id=foreign.object_id, revision=1),),
            ),
            changed_at=NOW + timedelta(seconds=57),
        )


def test_stale_retracted_and_historical_evidence_are_rejected(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service = GoalTaskActionService(store=store, index=index)
    evidence = _commit_observation(
        store,
        object_id="obs_t35_retracted",
        value="initial verification",
        offset=58,
    )
    retracted = Observation.model_validate(
        {
            **evidence.model_dump(mode="python", round_trip=True),
            "revision": 2,
            "learned_at": NOW + timedelta(seconds=59),
            "recorded_at": NOW + timedelta(seconds=59),
            "status": "retracted",
        }
    )
    store.commit(
        [retracted],
        OperationRequest(
            operation_name="test.retract.t35_evidence",
            expected_world_revision=int(store.current_world_revision()),
            reason="retract completion evidence",
            idempotency_key="t35-retract-evidence",
            source_class=SourceClass.USER,
        ),
    )

    old_ref_task = _running_evidence_task(
        service,
        intent,
        title="拒绝历史 evidence revision",
        completion_condition={"mode": "world_evidence"},
        created_offset=60,
    )
    with pytest.raises(ValueError, match="not current"):
        service.transition_task(
            TaskTransitionRequest(
                task_ref=ObjectRef(
                    object_id=old_ref_task.task_id,
                    revision=old_ref_task.revision,
                ),
                new_state=TaskState.COMPLETED,
                reason="旧 revision 已不是 current。",
                evidence_refs=(ObjectRef(object_id=evidence.object_id, revision=1),),
            ),
            changed_at=NOW + timedelta(seconds=61),
        )

    current_ref_task = _running_evidence_task(
        service,
        intent,
        title="拒绝 current retracted evidence",
        completion_condition={"mode": "world_evidence"},
        created_offset=62,
    )
    with pytest.raises(ValueError, match="inactive"):
        service.transition_task(
            TaskTransitionRequest(
                task_ref=ObjectRef(
                    object_id=current_ref_task.task_id,
                    revision=current_ref_task.revision,
                ),
                new_state=TaskState.COMPLETED,
                reason="retracted evidence 不能成为 completion truth。",
                evidence_refs=(ObjectRef(object_id=evidence.object_id, revision=2),),
            ),
            changed_at=NOW + timedelta(seconds=63),
        )


def test_terminal_completion_retry_is_idempotent_across_restart(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service = GoalTaskActionService(store=store, index=index)
    task = _running_evidence_task(
        service,
        intent,
        title="验证并允许幂等重试",
        completion_condition={"mode": "world_evidence"},
        created_offset=64,
    )
    verified = _commit_observation(
        store,
        object_id="obs_t35_retry_verified",
        value="trusted verification passed",
        source_class=SourceClass.PLATFORM,
        offset=65,
    )
    request = TaskTransitionRequest(
        task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
        new_state=TaskState.COMPLETED,
        reason="同一 terminal transition 可安全重试。",
        evidence_refs=(ObjectRef(object_id=verified.object_id, revision=1),),
    )
    first = service.transition_task(
        request,
        changed_at=NOW + timedelta(seconds=66),
    )
    revision_after_first = int(store.current_world_revision())
    second = service.transition_task(
        request,
        changed_at=NOW + timedelta(seconds=67),
    )
    assert int(store.current_world_revision()) == revision_after_first
    assert second.revision == first.revision

    restarted_store = SQLiteWorldStore(tmp_path / "world.db")
    restarted_service = GoalTaskActionService(store=restarted_store)
    third = restarted_service.transition_task(
        request,
        changed_at=NOW + timedelta(seconds=68),
    )
    assert int(restarted_store.current_world_revision()) == revision_after_first
    assert third.revision == first.revision


def test_terminal_transition_keeps_historical_task_revision_immutable(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service = GoalTaskActionService(store=store, index=index)
    task = _running_evidence_task(
        service,
        intent,
        title="验证历史 revision 不覆写",
        completion_condition={"mode": "world_evidence"},
        created_offset=69,
    )
    verified = _commit_observation(
        store,
        object_id="obs_t35_history_verified",
        value="trusted verification passed",
        source_class=SourceClass.PLATFORM,
        offset=70,
    )
    before = store.get_payload(task.task_id, revision=task.revision)
    completed = service.transition_task(
        TaskTransitionRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            new_state=TaskState.COMPLETED,
            reason="只追加新 revision。",
            evidence_refs=(ObjectRef(object_id=verified.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(seconds=71),
    )
    assert store.get_payload(task.task_id, revision=task.revision) == before
    assert store.get_payload(task.task_id, revision=completed.revision)[
        "task_state"
    ] == "completed"


def test_world_evidence_task_cannot_propose_action(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service = GoalTaskActionService(store=store, index=index)
    task = _running_evidence_task(
        service,
        intent,
        title="纯验证任务",
        completion_condition={"mode": "world_evidence"},
        created_offset=72,
    )
    with pytest.raises(ValueError, match="WORLD_EVIDENCE Task cannot propose"):
        service.propose_action(
            ActionProposalRequest(
                task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
                action_type="send_team_message",
                payload={"channel": "team"},
                evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
            ),
            proposed_at=NOW + timedelta(seconds=73),
        )
