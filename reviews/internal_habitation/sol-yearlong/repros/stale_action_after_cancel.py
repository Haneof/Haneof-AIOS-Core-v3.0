from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from aios_core.contracts.enums import SourceClass, TaskState, TaskType
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.execution import (
    ActionProposalRequest,
    GoalTaskActionService,
    TaskCreateRequest,
    TaskTransitionRequest,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2027, 1, 8, 22, 5, tzinfo=timezone.utc)


def commit_observation(store, observation, key):
    store.commit(
        [observation],
        OperationRequest(
            operation_name="review.seed.cancelled_action",
            expected_world_revision=int(store.current_world_revision()),
            reason="review-only deterministic mechanism reproduction",
            idempotency_key=key,
            source_class=SourceClass.USER,
        ),
    )


with tempfile.TemporaryDirectory() as td:
    db = Path(td) / "world.sqlite"
    store = SQLiteWorldStore(db)

    intent = Observation(
        object_id="obs_intent_cancel_repro",
        subject_id="user_cancel_repro",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="review-repro",
        source_kind="conversation",
        modality="text",
        value="Send the message; I authorize it.",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    commit_observation(store, intent, "seed-intent")

    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    service = GoalTaskActionService(
        store=store,
        index=index,
        subject_id="user_cancel_repro",
    )

    task = service.create_task(
        TaskCreateRequest(
            title="Send user-approved message",
            task_type=TaskType.IMMEDIATE,
            reason_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
            initial_state=TaskState.READY,
        ),
        created_at=NOW,
    )
    running = service.transition_task(
        TaskTransitionRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=1),
            new_state=TaskState.RUNNING,
            reason="Prepare the requested send.",
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        changed_at=NOW + timedelta(seconds=1),
    )
    action = service.propose_action(
        ActionProposalRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=running.revision),
            action_type="send_message",
            payload={"recipient": "staff", "message": "hello"},
            expected_outcome="message sent",
            evidence_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        ),
        proposed_at=NOW + timedelta(seconds=2),
    )

    cancel_time = NOW + timedelta(minutes=20)
    cancellation = Observation(
        object_id="obs_cancel_cancel_repro",
        subject_id="user_cancel_repro",
        occurred=TemporalExtent.point(cancel_time),
        learned_at=cancel_time,
        recorded_at=cancel_time,
        created_by="review-repro",
        source_kind="conversation",
        modality="text",
        value="Do not send it. I withdraw the request.",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    commit_observation(store, cancellation, "seed-cancel")

    cancelled = service.transition_task(
        TaskTransitionRequest(
            task_ref=ObjectRef(object_id=task.task_id, revision=running.revision),
            new_state=TaskState.CANCELLED,
            reason="User explicitly withdrew the action request.",
            evidence_refs=(ObjectRef(object_id=cancellation.object_id, revision=1),),
            next_step="Do not send the proposed action.",
        ),
        changed_at=cancel_time,
    )

    before = store.get_payload(action.action_id)
    assert cancelled.state == "cancelled"
    assert before["action_status"] == "proposed"

    envelope = service.authorize_action(
        action_ref=ObjectRef(object_id=action.action_id, revision=1),
        authorization_refs=(ObjectRef(object_id=intent.object_id, revision=1),),
        authorized_by="trusted-platform-test",
        authorized_at=cancel_time + timedelta(seconds=1),
        authorizer=lambda _action, _refs: True,
    )

    after = store.get_payload(action.action_id)
    print("REPRO_RESULT=STALE_ACTION_AUTHORIZED")
    print(f"PARENT_TASK_STATE={store.get_payload(task.task_id)['task_state']}")
    print(f"ACTION_BEFORE={before['action_status']}")
    print(f"ACTION_AFTER={after['action_status']}")
    print(f"DISPATCH_REVISION={envelope.revision}")
    print(f"EXECUTION_ID={envelope.execution_id}")

    assert store.get_payload(task.task_id)["task_state"] == "cancelled"
    assert after["action_status"] == "submitted"
