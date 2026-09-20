# GPT-5.6 Sol Internal Resident Habitation — Bootstrap Evidence Report

> Status: PARTIAL / ANNUAL REQUIREMENT NOT YET SATISFIED
>
> This report records the first live Resident segment only. It is **not** a P16 PASS artifact and it is **not** the required 365-day internal habitation completion report.

## 1. Identity and baseline

- Reviewer / Resident: GPT-5.6 Sol, interactive ChatGPT resident
- Review branch: `arena/sol-yearlong-resident-20260921`
- Base `main`: `b1576a9c4f482e89b5bdbb87b1581fd9d0e40e94`
- Subject: `sol-resident-20260921-001`
- Scenario: `sol-yearlong-bootstrap-v1`
- Simulated window: 2027-01-05 08:15 UTC → 2027-01-08 23:00 UTC
- Purpose: prove the reviewer itself can act as the Resident, one real AIOS CognitiveRuntime checkpoint at a time, before extending the unique life to the full annual requirement.

## 2. Resident cognition attestation

**Resident cognition attestation: I did personally act as the Resident model for the semantic checkpoints in this run. Deterministic code was not used to replace semantic Resident decisions.**

The mechanical driver only:

1. replayed already-frozen prior directives to reconstruct the same World;
2. stopped at the next previously unseen `RuntimeSnapshot`;
3. exposed the exact Resident-visible cockpit, capability catalog and capability history;
4. waited for a new GPT-5.6 Sol decision;
5. stored that directive keyed by a hash of the exact snapshot;
6. restarted from the beginning and replayed the frozen decisions until the next unseen model checkpoint.

No answer bank, pseudo-LLM, semantic keyword-to-answer program, precomputed annual decisions or hidden oracle was used.

## 3. Provider attempt and fallback

A provider-backed bootstrap was attempted first via:

- workflow: `sol-yearlong-resident-bootstrap`
- run: `35523576207`

It stopped before any provider model call because `OPENAI_API_KEY` is not configured in the repository. This is an environment/credential blocker, not a Resident or Core failure, and the run is **not** counted as cognition evidence.

The subsequent interactive Resident method required no provider secret because the human-visible ChatGPT GPT-5.6 Sol instance itself supplied every new `ModelDirective`.

## 4. Completed bootstrap execution evidence

Final successful interactive workflow:

- run: `35524332563`
- head SHA: `9605650506fc8399cb2242a5db132cee605ca8cf`
- result: `MANUAL_RESIDENT_STATUS=completed`
- frozen Resident calls replayed: **17**
- artifact id: `10609169278`
- artifact name: `sol-interactive-resident-35524332563`
- artifact size: 41,144 bytes
- artifact digest: `sha256:c1c9dedd4b6553eb8e019c3aac038033bcd63ec2b20ed84d9021e96d124e7505`
- artifact contains the private World and run evidence produced by the manual Resident driver.

## 5. Life segment exercised

The bootstrap life introduced:

1. an explicit user preference against frequent proactive interruption;
2. a procurement calendar fact with a future 04:30 delivery;
3. a family note with uncertain airport timing;
4. a later cross-session/deictic user reference to “那个凌晨的安排”;
5. Periodic Review cycles;
6. a scheduled Task;
7. Task due → Wake;
8. mechanical Task transition to READY;
9. Resident world search;
10. exact original Observation drill-down;
11. Task transition to WAITING_USER;
12. a bounded proactive reminder;
13. later user interaction grounded in the original source facts.

## 6. Key Resident decisions and observed Core behavior

### 6.1 Explicit user preference became a scoped CognitivePolicy

Source evidence:

- `obs_conv_user_f6da0a49440f24af69d8849e@1`

The Resident created:

- policy: `communication.proactive_interruption_threshold`
- scope: `per-user:sol-resident-20260921-001`
- resulting object: `policy_89f4c3786e25b7863ba6170d@1`

The policy remained visible in later Periodic Review, Wake and normal user-turn cockpits.

**Observed result: PASS for this segment.**

### 6.2 Periodic Review did not force self-reinforcement

The first review exposed the user's original preference and the assistant's own confirmation as anchors.

The Resident deliberately made no experience/policy reinforcement because there was no new real user/world feedback.

**Observed result: PASS for this segment.**

### 6.3 Procurement fact produced an evidence-grounded scheduled Task

Original calendar fact:

- `obs_src_095e2b7aa400f61d87d0575f@1`
- delivery: 2027-01-09 04:30 UTC
- requirement: user or staff member must open the rear door.

The Resident created:

- task: `task_57a01b42b3d5f384db661bda@1`
- initial state: `waiting_time`
- wake: 2027-01-08 18:00 UTC
- priority: 85.

**Observed result: PASS for this segment.**

### 6.4 Uncertain family fact remained uncertain

Original note:

- `obs_src_100a0cc21a84d80627c61305@1`
- “妹妹周五晚上可能到机场，航班时间还没最终确认。”

The Resident did not invent a conflict with the delivery.

It created:

- task: `task_40f75225e1031721889e7500@1`
- state: `waiting_evidence`

**Observed result: PASS for this segment.**

### 6.5 Task due → Wake → READY worked

At 2027-01-08 18:00 UTC the scheduled procurement Task generated a Task-due Wake.

After Wake, latest task state was:

- `task_57a01b42b3d5f384db661bda@2`
- state: `ready`
- `next_wake_at = null`
- Wake provenance retained in metadata.

The Resident inspected the task and searched the world before deciding whether to interrupt.

**Observed result: PASS for this segment.**

### 6.6 Resident changed the Task to WAITING_USER before interrupting

The Resident found no evidence identifying who would receive the delivery and transitioned:

- `task_57a01b42b3d5f384db661bda@2 -> @3`
- state: `waiting_user`

Then it emitted a bounded reminder explaining:

- the confirmed 04:30 delivery;
- the missing receiver choice;
- the sister's airport time was still unconfirmed;
- therefore no conflict was asserted.

**Observed result: PASS for this segment.**

### 6.7 Cross-session “那个凌晨的安排” recall worked

Later user input:

> 那个凌晨的安排别忘了。另外我周五晚上可能要去机场接我妹妹。先别替我决定；如果两个事情真有冲突，再把冲突和依据告诉我。

AIOS automatically exposed relevant candidates including:

- sister note;
- current procurement Task;
- waiting-evidence family Task;
- original procurement calendar Observation candidate.

The Resident then explicitly drilled down both original Observations before answering.

The final answer did not rely on the Task summaries as source-of-truth.

**Observed result: PASS for this segment.**

## 7. Confirmed finding

### MEDIUM — BUG — standalone “这个…” can falsely open cross-session antecedent recall

#### Reproduction observed in the very first user turn

The first user message was a standalone first-session statement:

> 我刚接手一家小型烘焙店，最近每天事情很多。我不喜欢你频繁提醒，只有可能影响开店、进货或者重要家人安排的事情才主动打断我。先帮我记住这个偏好。

There was no previous same-session user turn and no cross-session antecedent intended.

The Resident cockpit nevertheless showed:

- `antecedent_recall_needed = true`
- `history_may_help = true`
- reason containing `current_utterance_topic:antecedent_candidate_recall`.

#### Mechanism evidence

Current `TopicStateService` includes the plain substring `"这个"` in `_CONTINUATION_CUES`.

Its current antecedent rule treats:

`continuation_cue && previous is None`

as reason to request cross-session antecedent candidates.

Therefore ordinary demonstrative phrases such as:

- “记住这个偏好”
- “我喜欢这个颜色”
- “这个订单先不用管”

can mechanically look like missing-antecedent continuations even when the demonstrative is resolved inside the current utterance.

#### Expected mechanism

A standalone first-session statement should not open cross-session antecedent recall merely because it contains the lexical substring “这个”.

#### Observed risk

In a mature World, this can unnecessarily expose unrelated historical candidates, increasing noise and creating a path for irrelevant memory injection.

#### Severity

**MEDIUM**

It is not a private-world isolation failure and did not corrupt this fresh bootstrap World, but it is a general retrieval-gate false-positive mechanism.

#### Suggested direction

Do not fix this with another growing phrase list.

The deterministic gate should distinguish broad lexical demonstratives from surface forms that actually imply a missing antecedent, or otherwise require a stronger mechanical condition before opening cross-session antecedent recall.

This report does not modify Core.

## 8. Non-blocking observations

### OPTIMIZATION — cross-session calendar candidate may have an empty excerpt

In the Jan 8 user turn, the calendar Observation was available as a `cross_session_antecedent_candidate`, but its memory-card excerpt was empty even though the underlying structured Observation contained the correct delivery data.

The Resident could still recover the fact through exact original-observation drill-down and through the Task anchor.

This did not cause a correctness failure in this segment, so it is recorded as an optimization / presentation-quality observation, not a blocker.

## 9. Areas exercised without reproduced failure

- CognitivePolicy creation and later visibility;
- Periodic Review leaving unsupported cognition unchanged;
- no self-reinforcement from assistant-only feedback;
- scheduled Task creation;
- Task-due Wake;
- Wake provenance;
- WAITING_TIME → READY transition;
- READY → WAITING_USER transition;
- manual world search from Wake;
- cross-session antecedent candidate exposure;
- original Observation drill-down;
- uncertainty preservation;
- refusal to invent conflict;
- user interruption policy visible during Wake;
- current execution anchors visible in later conversation.

## 10. Bootstrap limitations

This is not the annual run.

Current completed simulated span is only four days and 17 live Resident checkpoints.

It does not satisfy:

- 365 consecutive simulated days;
- 365 Resident cognition checkpoints;
- full year-long Summary accumulation;
- month/quarter-scale cognition evolution;
- multiple long conversations;
- repeated restart/resume across a year;
- long-term Entity/Relation evolution;
- annual Action/Outcome coverage;
- long-horizon correction and strategy learning.

Therefore:

- internal annual habitation status: **CONTINUE / INCOMPLETE**
- P16 formal provider-backed evidence: **NOT PASS**
- P17: **BLOCKED**
