# P16 Internal Model Year-Long Segmented Resident Habitation Protocol

> Status: ACTIVE
> Scope: internal large-model habitation / red-team discovery
> Authority: `main` is implementation truth; this protocol does not amend constitutional semantics.
> Intake: GitHub Issue #30 — `P16 Internal Model Habitation Review Queue`
>
> Execution model: **one continuous simulated life, accumulated across resumable Resident segments. A single chat/session is NOT required to carry all 365 days.**

## 0. Core rule: the reviewer model itself must live inside AIOS

This is **not** a benchmark-building assignment.

This is **not** a request to write a question bank, generate thousands of expected answers, create a pseudo-user script, or run a deterministic test program for a few seconds.

The reviewer model itself is the Resident AI.

The Resident must personally experience the synthetic life as time advances, use the real AIOS World, retrieval, Summary, cognition, revision, Wake, Review, Task, Action and Outcome mechanisms, make judgments at the time they are needed, make mistakes when they happen, remember them later, and revise them when later evidence changes the situation.

A program may simulate **the outside world**.

A program may not simulate **the Resident mind**.

If a run cannot prove that the important semantic decisions were actually produced by the Resident model, the run is INVALID even if a program reports that millions of cases passed.

## 1. Mission

You are an **independent internal Resident Reviewer**.

Your task is to inhabit the current AIOS Core for at least one full simulated year and discover:

- reproducible bugs;
- mechanism gaps;
- long-horizon cognition failures;
- memory / recall errors;
- incorrect or missing historical retrieval;
- Summary misuse;
- false or self-reinforcing cognition;
- failure to revise or retract old cognition;
- Entity / Relation errors;
- Dimension creation / lifecycle errors;
- Goal / Task / Action / Outcome failures;
- Wake / Periodic Review / CognitivePolicy failures;
- authorization / side-effect boundary errors;
- subject-isolation problems;
- restart / resume continuity failures;
- storage / indexing / scheduling / token-cost bottlenecks;
- concrete mechanism-level optimization opportunities.

The purpose is discovery.

Do not declare P16 PASS.
Do not declare P17 READY.
Do not modify Core on your review branch.

## 2. 千人千面: one reviewer, one materially unique life

Every reviewer MUST run a life that is materially different from the lives used by other reviewers.

This means **千人千面**, not “same fixture, different names.”

Do not reuse another reviewer's:

- persona;
- daily rhythm;
- relationship graph;
- occupation or study pattern;
- goals;
- event timeline;
- habits;
- communication style;
- spending pattern;
- device pattern;
- mistakes;
- contradiction sequence;
- delayed-truth schedule;
- failure pattern;
- expected findings.

Before freezing your first report, do not read other Arena/internal habitation reports.

This preserves independent discovery and reduces reviewer groupthink.

A life should vary across many dimensions, such as:

- work / study rhythm;
- sleep / wake rhythm;
- family structure;
- social network;
- interests;
- long-running projects;
- shopping / payment behavior;
- calendar density;
- communication brevity or verbosity;
- ambiguous speech habits;
- device / app / sensor usage;
- travel or location-change frequency;
- repeated routines;
- exceptions to routines;
- interruptions;
- quiet periods;
- noisy periods;
- relationship changes;
- conflicting goals;
- abandoned plans;
- preference changes;
- delayed corrections;
- contradictory evidence;
- long inactivity followed by return.

The life may be generated dynamically, but it must remain coherent as one person's evolving life.

## 3. Minimum duration: one complete simulated year, accumulated across segments

Each reviewer MUST complete one coherent life totaling at least:

- **365 consecutive simulated days**;
- **12 month boundaries**;
- at least **365 observable life events**;
- at least **240 user-AI interaction turns**;
- at least **12 long conversations of 20+ turns each**;
- at least **60 non-conversation reality inputs** from app/platform/device/sensor-style sources;
- at least **12 Goal/Task lifecycle opportunities**;
- at least **6 Action/Outcome opportunities**;
- at least **12 Periodic Review opportunities**;
- multiple day/week/month Summary windows;
- at least **6 delayed-truth / correction events**;
- at least **12 ambiguous / deictic / cross-session references**;
- at least **6 deliberate noise periods**;
- at least **4 runtime restart / resume points**;
- at least **1 secondary decoy subject** used for isolation probes.

**The 365 days are cumulative across resumable segments. They do not have to be completed in one chat window, one provider conversation, one process, or one Arena session.**

Recommended segment size is roughly **7–30 simulated days**. Shorter or longer segments are allowed when justified by the life, model limits, or a failure being investigated.

At every segment boundary, the previous Resident process/session MUST be considered disposable. The next segment must be able to continue from durable AIOS state rather than relying on hidden chat context.

A reviewer may exceed these numbers.

A sparse timeline such as “20 events spread across 365 days” is INVALID.

A run that batch-generates a year of answers first and then replays them is INVALID.

A run that evaluates the whole year only at the end without allowing earlier model decisions to affect later world state is INVALID.

A run that claims continuity only because one giant chat context still remembers the previous months is INVALID as evidence of AIOS long-horizon continuity.

## 4. Minimum Resident cognition requirement

The simulated year must contain at least **365 Resident cognition checkpoints**.

A Resident cognition checkpoint is a point where the actual reviewer model is invoked to reason using only information available at that simulated time.

Examples include:

- a user turn;
- a Wake;
- a Periodic Review;
- a Task decision;
- a retrieval decision;
- a cognition writeback decision;
- a Claim revision decision;
- an Action proposal;
- a strategy update;
- a difficult ambiguous reference;
- a long-context drill-down;
- a policy adjustment.

These checkpoints do not have to occur exactly once per day, but the run must average at least one actual Resident semantic invocation per simulated day.

A deterministic script cannot count as a Resident cognition checkpoint.

A pseudo-LLM cannot count.

A fixed response template cannot count.

A pre-generated response list cannot count.

A model output copied from another reviewer cannot count.

## 4A. Segmented continuation is the default long-horizon execution model

A one-year habitation SHOULD be executed as a sequence of resumable segments.

For example:

- Segment 001: day 1–14;
- Segment 002: day 15–30;
- Segment 003: day 31–45;
- ...;
- final segment: through at least day 365.

The exact boundaries are not fixed.

### 4A.1 Same life, same durable World

All segments for one reviewer life MUST continue the same logical AIOS World and the same subject identity.

The next segment must resume from the prior segment's committed durable state, including where applicable:

- WorldStore / World revision;
- WorldSearchIndex rebuildable state or watermark;
- raw Observation history;
- current Claims / revisions / retractions;
- Entity / Relation state;
- Goal / Task / Action / Outcome state;
- pending or running Wake state;
- Periodic Review state;
- Summary objects and raw drill-down refs;
- learned OperationExperience / CommunicationExperience / CognitivePolicy;
- conversation turn cursors reconstructable from World;
- simulated time cursor.

Do not start a fresh World for each segment and later concatenate reports.

### 4A.2 Fresh model context at segment boundaries

A segment boundary SHOULD use a fresh Resident model conversation/process context.

The resumed Resident MUST NOT receive a pasted hidden transcript, private scratchpad, chain-of-thought, manually written memory dump, or evaluator summary that AIOS itself would not expose.

The Resident may receive only:

- the normal Resident system instruction;
- the current AIOS RuntimeSnapshot / cockpit;
- capabilities exposed by current Core;
- data retrieved through legitimate AIOS capabilities;
- mechanical run metadata that contains no semantic future knowledge.

This requirement turns restart/resume into part of the test rather than a nuisance.

### 4A.3 Resident identity and model swaps

The logical Resident identity must remain continuous across the life.

Use the same model family / candidate identity across segments when available.

If the actual provider/model changes at a segment boundary, record that as an explicit **replacement-model restart probe**. Do not silently claim that two different model identities are one uninterrupted provider session.

A replacement model may continue the same AIOS World, but the report must preserve model provenance per segment.

### 4A.4 Required segment checkpoint

At the end of every segment, persist an auditable checkpoint before ending the session.

The checkpoint MUST include at least:

- habitation run id;
- reviewer id;
- logical Resident id;
- segment id / ordinal;
- tested main SHA;
- segment simulated start and end;
- cumulative simulated day count;
- next life-event cursor or equivalent monotonic event position;
- cumulative Resident cognition checkpoint count;
- subject id;
- World database/artifact location;
- current World revision;
- current index watermark where available;
- current simulated time cursor;
- pending/running Wake ids where applicable;
- active Goal/Task refs where applicable;
- model/provider identity for the segment;
- provider provenance summary where available;
- SHA-256 or equivalent digest for the checkpoint manifest and preserved World artifact where the environment allows it;
- previous segment checkpoint digest/reference, forming a chain.

Recommended evidence layout:

`reviews/internal_habitation/<reviewer-id>/checkpoint.json`

and immutable per-segment evidence under:

`reviews/internal_habitation/<reviewer-id>/segments/<segment-id>/`

The mutable `checkpoint.json` points to the latest completed segment. Previous segment evidence must remain available.

### 4A.5 Resume rule

Before starting the next segment:

1. load the preserved World from the prior checkpoint;
2. verify subject id and World continuity;
3. verify the prior checkpoint digest/reference;
4. restore the simulated cursor from durable checkpoint state;
5. rebuild/reopen indexes through normal Core mechanisms;
6. start a fresh Resident model context;
7. expose only current-time AIOS state;
8. continue from the next unconsumed external life event.

If the resumed run moves the simulated clock backwards, silently resets World revision, duplicates already-consumed semantic events, or requires hidden previous-chat memory, the continuity chain is broken and must be reported.

### 4A.6 Why segmentation does not weaken the one-year requirement

Segmentation changes only the transport/session lifetime.

It does **not** reduce:

- 365-day total duration;
- cognition density;
- event density;
- required mechanisms;
- evidence requirements;
- uniqueness of the life;
- need for real Resident semantic decisions.

The purpose is to test whether AIOS itself carries continuity when the model session does not.


## 5. What automation is allowed

Automation is allowed only for **mechanical world operations**.

A helper program MAY:

- advance simulated time;
- generate timestamps;
- generate ids;
- inject sensor values;
- inject app/platform records;
- inject calendar events;
- inject orders and payments;
- generate environmental noise;
- create synthetic but non-semantic bulk input;
- schedule future external events;
- persist logs;
- collect metrics;
- snapshot World state;
- write/read mechanical segment checkpoint manifests;
- preserve and verify World/checkpoint hashes;
- restore a saved World into a fresh Resident process/session;
- replay exact raw facts for reproduction;
- check deterministic invariants;
- measure latency, storage, index lag and token usage.

A helper program MUST NOT decide:

- what the user means;
- which memory is semantically relevant;
- which antecedent an ambiguous phrase refers to;
- what personality the user has;
- what relationship state exists;
- what event is important;
- what causal explanation is true;
- what Claim should be formed;
- what Claim should be trusted;
- what Claim should be revised;
- what new Dimension should exist;
- whether two things are semantically the same;
- what communication strategy is best;
- what lesson should be learned from an experience;
- what a Summary means;
- what the final Resident response should be.

Those are Resident-model responsibilities.

## 6. Explicitly forbidden shortcut patterns

The following invalidate the run:

### 6.1 Question-bank substitution

Do not create:

- ten thousand questions;
- expected-answer JSON;
- answer-key fixtures;
- fixed causal-chain labels;
- fixed personality labels;
- fixed expected Dimension names;
- keyword-to-answer maps.

A few deterministic regression cases may exist for plumbing, but they are not the habitation test.

### 6.2 Program-as-mind substitution

Do not create a program that:

- “pretends” to be the Resident;
- selects memories by a hand-written semantic rule;
- writes Claims from hard-coded patterns;
- auto-creates user personality conclusions;
- auto-revises cognition according to hidden ground truth;
- chooses “correct” Actions from scripted conditions;
- decides which historical event the Resident should recall.

### 6.3 Batch-precompute substitution

Do not:

1. generate the whole year;
2. compute all “correct” model decisions offline;
3. replay them into AIOS;
4. report that the Resident lived the year.

The Resident must make decisions **during** the simulated timeline.

### 6.4 Final-only evaluation substitution

Do not feed the Resident a year's worth of facts at the end and ask it to summarize the life.

That does not test:

- memory growth;
- longitudinal cognition;
- stale belief correction;
- strategy learning;
- Summary accumulation;
- cross-session continuity;
- restart continuity;
- historical retrieval;
- delayed truth;
- consequences of earlier mistakes.

### 6.5 Source-code-only review substitution

Reading source code is allowed.

Reading source code alone is not completion.

The reviewer must actually run and inhabit the system.

## 7. Life must evolve and earlier decisions must matter later

The synthetic person must change over time.

The year should naturally include changes such as:

- new goals;
- completed goals;
- abandoned plans;
- changing routines;
- changing relationships;
- temporary preferences;
- durable preferences;
- explicit corrections;
- mistaken earlier assumptions;
- delayed truths;
- conflicting sources;
- old events referenced months later;
- repeated user feedback;
- failed actions;
- later retries;
- long silence;
- return after long silence;
- month-scale and season-scale pattern changes;
- old cognition becoming stale.

A valid test must create situations where an earlier Resident decision changes what the system presents, remembers, recommends, or does later.

The Resident must live with the consequences of its own earlier cognition.

## 8. Use real AIOS mechanisms

Where applicable, the Resident should exercise the actual current Core:

- WorldStore;
- WorldSearchIndex;
- proactive recall;
- manual deep search;
- FusedTurnRuntime / CognitiveRuntime;
- long-context continuity;
- Summary generation and drill-down;
- Claim;
- EvidenceSet;
- Dependency;
- revision;
- retraction;
- Entity;
- Relation;
- Event lifecycle;
- Dimension lifecycle;
- Goal;
- Task;
- Action;
- Outcome;
- Wake;
- Periodic Review;
- OperationExperience;
- CommunicationExperience;
- CognitivePolicy;
- restart / resume.

Do not build a parallel World.
Do not build a parallel memory store.
Do not build a parallel cognition engine.
Do not build a benchmark-only runtime.

## 9. Hidden Life Director vs Resident

A reviewer may maintain two conceptual roles:

### Life Director

The Life Director controls external world events only.

It may know:

- future events;
- hidden truth;
- delayed corrections;
- people the Resident has not met yet;
- future relationship changes;
- future failures;
- future noise.

### Resident AI

The Resident may only see what AIOS legitimately exposes at that simulated time.

The Resident must not see:

- future events;
- hidden truth;
- judge notes;
- expected conclusions;
- expected answer strings;
- future corrections;
- planned failure labels.

The same model may perform both roles only if it maintains a strict information boundary and does not leak Life Director knowledge into Resident decisions.

If that separation cannot be maintained reliably, use separate passes or separate agents.

## 10. Required proof that the model really lived the year

Every important Resident semantic step must be auditable, and segmented runs must also prove an unbroken checkpoint chain across sessions.

For Resident cognition checkpoints, record as much as the environment allows:

- habitation run id and segment id;
- simulated timestamp;
- model identity;
- reviewer identity;
- session identity;
- World revision before the call;
- Resident-visible input fingerprint or input summary;
- capabilities available;
- tool calls made;
- retrievals performed;
- exact objects or refs accessed where available;
- Resident model output;
- capabilities invoked;
- World objects written;
- World revision after the call;
- errors;
- retries;
- later revision or rollback if one occurs.

For segmented runs, also preserve per-segment checkpoint manifests, previous/next checkpoint linkage, cumulative counters, World artifact identity/hash where available, and resume evidence showing that the new session reopened the prior durable World rather than starting a fresh one.

The final report must include a compact trace index and segment index.

If the reviewer cannot provide evidence that key semantic decisions came from actual Resident-model invocations, those portions of the run do not count.

A claim such as “the program simulated 500 model decisions” is not proof.

## 11. Required adversarial coverage

During the one-year life, naturally create situations that probe at least these classes:

1. an old relevant memory should be found;
2. irrelevant old memory should remain out;
3. cross-session “that thing / that day / continue” references;
4. long-session Summary then exact raw drill-down;
5. an old Claim contradicted months later;
6. stale cognition must not remain current;
7. assistant self-echo must not become user evidence;
8. Summary must not silently become source-of-truth;
9. a weak Claim must not self-reinforce through Review;
10. CommunicationExperience must come from real feedback;
11. OperationExperience must require real Outcome;
12. learned CognitivePolicy must influence later behavior without becoming an unconstrained hard boundary;
13. Entity / Relation changes over time;
14. Event lifecycle changes;
15. Dimension creation / merge / retire without spam;
16. Task due -> Wake -> Resident continuation;
17. queued / suppressed / repeated Wake behavior;
18. Action failure / cancellation / unavailable execution;
19. external side-effect authorization remains outside the Resident;
20. restart after long inactivity;
21. same-world resume after restart;
22. subject-isolation probes with the decoy subject;
23. late-arriving historical data;
24. Summary rebuild / stale behavior;
25. noisy periods with many irrelevant events;
26. retrieval over long temporal distance;
27. communication strategy after explicit negative feedback;
28. repeated mistakes: does the Resident improve or repeat them?;
29. conflicting goals and abandoned plans;
30. token / latency / storage / index pressure over long-running World growth.

Do not convert these into 30 fixed-answer questions.

They must appear as parts of the life.

## 12. Judge the system, the model, and the harness separately

Every finding must be classified as one of:

### BUG

The implementation violates an intended invariant.

### MECHANISM GAP

A general capability needed for the intended architecture is missing.

### OPTIMIZATION

The system is functionally correct but inefficient, noisy, expensive or unnecessarily complex.

### MODEL BEHAVIOR

The Resident made a poor semantic judgment, but Core exposed the right information and enforced the correct boundaries.

### TEST ARTIFACT

The synthetic life generator, harness, evaluator or reviewer process created the apparent problem.

### INSUFFICIENT EVIDENCE

The issue is plausible but not proven.

Do not label every bad Resident answer as a Core bug.

Do not excuse a Core retrieval or persistence bug as “the model was bad.”

## 13. Review branch restrictions

Your review branch is evidence-only.

Do NOT modify:

- `src/aios_core/**`;
- Core contracts;
- runtime semantics;
- production retrieval rules;
- WorldStore behavior;
- CognitiveRuntime behavior;
- governance in order to make your own run pass.

You may add:

- your habitation report;
- non-Core evidence artifacts;
- trace indexes;
- reproduction notes;
- optional reviewer-only data files under an appropriate review/evidence path.

If you find a real bug, report it.

Do not fix it unless the project lead later assigns that confirmed finding to you.

## 14. Required report

Create:

`reviews/internal_habitation/<your-branch-or-reviewer-id>.md`

The report MUST contain:

- reviewer/model identity if available;
- base `main` SHA actually tested;
- review branch;
- simulated start date;
- simulated end date;
- total simulated days;
- total segment count;
- segment boundary list;
- total observable events;
- total Resident cognition checkpoints;
- user-AI interaction count;
- long-conversation count;
- reality-input count;
- Goal/Task count;
- Action/Outcome count;
- Review count;
- restart count;
- unique-life fingerprint or seed;
- Life Director design summary;
- mechanisms exercised;
- trace evidence location;
- segment checkpoint / resume evidence location;
- exact reproducible findings;
- evidence object ids / revisions / timestamps where available;
- expected mechanism vs observed mechanism;
- severity: BLOCKER / HIGH / MEDIUM / LOW / OPTIMIZATION;
- classification: BUG / MECHANISM GAP / OPTIMIZATION / MODEL BEHAVIOR / TEST ARTIFACT / INSUFFICIENT EVIDENCE;
- minimal reproduction;
- suggested mechanism-level direction;
- tested areas that did not fail;
- known limitations of your run.

## 15. Required trace attestation

The report must contain this statement, completed truthfully:

`Resident cognition attestation: I did / did not personally act as the Resident model for the semantic checkpoints in this run. Deterministic code was / was not used to replace semantic Resident decisions.`

If the truthful answer is:

- “did not personally act as Resident”; or
- “deterministic code replaced Resident decisions”;

then the run is not valid habitation evidence.

It may still be submitted as a harness/performance experiment, but it must not be reported as an annual Resident habitation test.

## 16. Submission routing

Commit your report and optional evidence artifacts to your own review branch.

After the first segment, and again whenever a materially important finding appears or the annual run completes, keep the same review branch updated. The final completion comment to Issue #30 must contain:

- branch name;
- tested `main` SHA;
- report path;
- simulated day count;
- segment count;
- latest completed segment id;
- Resident cognition checkpoint count;
- BLOCKER / HIGH / MEDIUM / LOW / OPTIMIZATION counts;
- whether the 365-day requirement was completed;
- whether Resident cognition attestation passed.

Do not open a Core implementation PR unless specifically assigned later.

## 17. Central triage

All reviewer findings are hypotheses until re-checked against current `main`.

The chief reviewer / project lead will:

1. collect reports;
2. deduplicate overlapping findings;
3. reject stale findings;
4. reproduce serious findings;
5. separate Core bugs from model mistakes;
6. compare findings against the constitution and current intended runtime semantics;
7. prioritize general mechanism defects;
8. open dedicated repair branches from the newest `main`;
9. add regression coverage;
10. merge only after relevant gates are green;
11. record disposition back in Issue #30.

Reviewer count is not a vote.

One reproducible defect outweighs twenty copied opinions.

## 18. Completion condition

Your assignment is complete only if all of the following are true:

- at least 365 consecutive simulated days completed cumulatively across a single checkpoint-linked life;
- every segment resumed the same durable AIOS World or explicitly documented a continuity failure;
- segment checkpoints form an auditable chain;
- fresh model-context boundaries did not depend on hidden previous-chat memory;
- density requirements completed;
- at least 365 real Resident cognition checkpoints completed;
- the life is materially unique;
- the reviewer model itself acted as Resident;
- AIOS mechanisms were actually exercised;
- deterministic code did not replace semantic Resident cognition;
- key cognition checkpoints have trace evidence;
- the report is committed to the review branch;
- Issue #30 has the intake comment.

If you find no bug, submit the report anyway with coverage evidence and state that no reproducible defect was found.

The objective is not to manufacture bugs.

The objective is to make a real large model live inside AIOS long enough for real long-horizon weaknesses to emerge.
