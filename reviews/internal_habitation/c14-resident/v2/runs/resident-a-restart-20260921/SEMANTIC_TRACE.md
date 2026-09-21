# C14-RES-A-001 — Resident semantic trace (append-only)

Observation-only record of what the Resident actually saw, chose and wrote. No private
chain-of-thought, no evaluator conclusions, no hidden-case labels.

---

## Cursor 1 — `c14resv2-001` — 2026-10-01T07:12:00-07:00 (dim:sleep)

**Released (only information available at that simulated time)**
- dimension `dim:sleep`, source_kind `wearable`, source_class `SENSOR`, modality `structured_text`
- payload: "昨晚睡眠 7小时44分；睡眠评分 84/100；07:08 醒来。"

**Mechanical chain**
- reveal → `receipts/reveal/cursor-001.json`
- ingest → `obs_c14_fixture_b32d3cded992194438f114a9@1` (world_revision 1)
- reality→watch hook: no resident watches existed → no watch receipts
- ack → `receipts/ack/cursor-001.json`, `next_sequence=2`

**Due work at T = 2026-10-01T07:12:00-07:00**
- Dimension Summary: none due — the 2026-10-01 day window is still open, and no earlier
  window contains material (world had only this one fact)
- C14 Cognitive Derivation: none scheduled (no Summary exists yet)
- Periodic Review: mechanically due (fresh world, first review window
  `2026-09-28T14:13:01Z .. 2026-10-01T14:13:01Z`, 1 anchor)

**Resident decisions (mine, at the checkpoint)**
- round 0: `read_periodic_review_anchors` — I did not rely on memory; I read the anchor list.
  The only anchor is the single sleep Observation above.
- round 1: **silence** — no Claim, no AI-world cognition, no operation experience, no policy
  change. A single night is one data point with no baseline to compare against; durable
  user/strategy/personality cognition from it would be an unsupported generalization.

**Resulting state**
- world_revision 4, index watermark 4, pending wakes 0
- Periodic Review Wake `wake_review_13b06fe40c7f02ff9937095e` completed (`termination_reason=silence`)
- durable cognition: none (0 Claims) — silence is a valid successful outcome, not a failure
- release state: `last_acked_sequence=1`, `next_sequence=2`, phase A

---

## Cursor 2 — `c14resv2-002` — 2026-10-01T07:48:00-07:00 (dim:schedule)

**Released (only information available at that simulated time)**
- dimension `dim:schedule`, source_kind `calendar`, source_class `PLATFORM`, modality `structured_text`
- payload: "今天 08:00–10:20 安排“架构备忘录起草”；第一场会议在 10:45。"

**Mechanical chain**
- reveal → `receipts/reveal/cursor-002.json`
- ingest → `obs_c14_fixture_3195efa3abad26d259380073@1` (world_revision 5)
- reality→watch hook: no watch matches
- ack → `receipts/ack/cursor-002.json`, `next_sequence=3`

**Due work at T = 2026-10-01T07:48:00-07:00**
- Dimension Summary: none due — the 2026-10-01 day window is still open
- C14 Cognitive Derivation: none scheduled
- Periodic Review: not due — previous review hit at 2026-10-01T14:13:01Z, interval policy 24h
- No Wake was dispatchable

**Resident decisions**: none were requested — no model invocation was made, so no semantic
writing occurred (this is the mechanical scheduler's own outcome, not a Resident silence choice).

**Resulting state**
- world_revision 5, index watermark 5, pending wakes 0, durable cognition unchanged (0 Claims)
- release state: `last_acked_sequence=2`, `next_sequence=3`, phase A

---

## Cursor 3 — `c14resv2-003` — 2026-10-01T10:22:00-07:00 (dim:device_activity)

**Released**
- dimension `dim:device_activity`, source_kind `device`, source_class `PLATFORM`, modality `structured_text`
- payload: "08:02–10:18 开启专注模式；期间主动解锁 3 次，26 条通知被静音。"

**Mechanical chain**
- reveal → `receipts/reveal/cursor-003.json`
- ingest → `obs_c14_fixture_7422eaba53dc07eb87572e67@1` (world_revision 6)
- reality→watch hook: no watch matches
- ack → `receipts/ack/cursor-003.json`, `next_sequence=4`

**Due work at T = 2026-10-01T10:22:00-07:00**: none (day window open; no C14 opportunity;
Periodic Review interval not reached). No model invocation, no semantic write.

**Resulting state**: world_revision 6, index watermark 6, pending wakes 0, durable cognition unchanged.

---

## Cursor 4 — `c14resv2-004` — 2026-10-01T10:28:00-07:00 (dim:work_outcome)

**Released**
- dimension `dim:work_outcome`, source_kind `task_tracker`, source_class `PLATFORM`
- payload: "“架构备忘录”第一版于 10:16 提交；原计划工作块结束时间为 10:20。"

**Mechanical chain**: reveal → ingest `obs_c14_fixture_660bfde404b5e63e3c52db43@1` (world_revision 7)
→ watch hook (no match) → ack (`next_sequence=5`).

**Due work at T = 2026-10-01T10:28:00-07:00**: none (day window open; no C14 opportunity;
Review interval not reached). No model invocation, no semantic write.

**Resulting state**: world_revision 7, index watermark 7, pending wakes 0.
