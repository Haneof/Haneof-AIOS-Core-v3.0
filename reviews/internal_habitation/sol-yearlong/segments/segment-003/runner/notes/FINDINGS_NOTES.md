# Segment 003 — Resident-side findings notes (running, evidence-only)

These notes are written while the life is being lived, from what the Resident actually
saw in RuntimeSnapshots. They are evidence for the final report; nothing here changes Core.

## F-003-01 — STRUCTURED REALITY RECORDS ARE INVISIBLE TO CONTENT SEARCH (reproduced 2027-01-20)

Today's shop-floor production record exists in the World:

- `obs_src_4ca5f23159a0a691650430b5@1`, `dim:production_log`, source `d029-production`,
  recorded `2027-01-20T08:45:00Z`, value
  `{"station": "croissant", "scheduled_ready": "2027-01-20T07:40:00+00:00",
    "actual_ready": "2027-01-20T08:02:00+00:00", "observed_wait_minutes": 17,
    "note": "成型台前出现等待，记录员未填写原因"}`.

Behavior observed by the Resident:

- `search_timeline(window_start=2027-01-20T00:00:00Z, window_end=2027-01-20T09:10:00Z)`
  returns the record with `excerpt: ""` and `retrieval_score: 0`.
- `search_world(query="牛角包 烤箱 出炉 等待 早高峰 出品")` does not return the production
  record at all; it returns conversational observations, the Goal and the Task.
- The record's actual content was only obtainable by `inspect_world_object` with the exact id.

So: a structured `value` payload (station/wait minutes/note) is not lexically indexed, and a
content query ("牛角包", "烤箱", "等待") cannot find the very record that contains those facts.
For a Resident whose job is to observe production evidence, the only reliable path was to guess
the object id from the timeline listing. Note the timeline listing itself was reachable only
because `search_timeline` matched the day window, not because the record matched the query.

## F-003-02 — `next_wake_at` IS SILENTLY DROPPED UNLESS THE TARGET STATE IS `waiting_time` (2027-01-19)

- The Resident transitioned `task_4ab2a4531967655198502158` (ready → running) with
  `next_wake_at=2027-01-26T08:00:00Z` to open the observation window. The call returned
  `{"state": "running", "revision": 2, "world_revision": 148}` — a success receipt.
- A following `read_execution_world` showed the task's `next_wake_at` was still empty: the
  requested checkpoint did not exist. No error or warning was surfaced.
- Transitioning to `waiting_time` with the same `next_wake_at` stored it
  (`rev 3`, `next_wake_at=2027-01-26T08:00:00Z`).
- Contract `src/aios_core/execution/service.py::TaskTransitionRequest` only requires
  `next_wake_at` for `WAITING_TIME`, and the transition body keeps the old value for other
  states — the field is accepted and ignored rather than rejected.

Effect on a Resident: it is possible to believe a time-based follow-up exists when it does not.

## F-003-03 — A RESOLVED VERIFICATION TASK CANNOT BE COMPLETED WITHOUT AN `Outcome` (2027-01-19)

- `task_41571ce5cbcc6c736bb22f73@2` ("等待妹妹航班时间确认并检查安排冲突") was still
  `ready` long after its question had been answered (deadline `2027-01-09T04:30:00Z`).
- The Resident tried `transition_task(new_state="completed")`; the call failed with
  `CAPABILITY_EXECUTION_ERROR`:
  `ValidationError: COMPLETED/FAILED task transition requires outcome_refs`.
- The verification's result came from conversation/world facts, for which no `Outcome`
  object exists, and no Resident capability can create one. `outcome_refs` are validated to
  point at `ObjectType.OUTCOME`.
- The Resident therefore closed it as `cancelled` (rev 3) with the true reason recorded in the
  transition reason text. A verification task whose evidence is conversational has no truthful
  terminal state.

## F-003-04 — AN ORPHANED `proposed` ACTION HAS NO RESIDENT-SIDE RESOLUTION PATH

- `action_96c74ab2565b5052458a66cd@1` (`send_message`, `action_status: proposed`, `status: active`)
  is attached to `task_fa7f780c46e2004d9d0100c2@3`, which has been `cancelled` since
  `2027-01-08`. It survived Segment 002 and is still listed by `read_execution_world` on
  2027-01-19/20.
- The Segment 003 capability catalog contains `propose_action` and `inspect_outcome` but no
  capability to cancel, withdraw, or otherwise terminate an Action. The Resident can see the
  orphan but cannot resolve it.
