from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import (
    GoalSourceType,
    GoalStatus,
    SourceClass,
    TaskState,
    TaskType,
)
from aios_core.contracts.models import Observation, Task
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
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


def test_task_cannot_claim_completion_without_outcome(tmp_path):
    store, index, intent, _ = _seed(tmp_path)
    service, _, task = _active_goal_and_running_task(store, index, intent)

    with pytest.raises(ValueError, match="requires outcome_refs"):
        TaskTransitionRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=task.revision),
            new_state=TaskState.COMPLETED,
            reason="不能只靠模型口头宣布完成。",
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
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