# P16 Internal Model Habitation Review Protocol

> Status: ACTIVE
> Scope: internal large-model habitation / red-team discovery
> Authority: `main` is implementation truth; this protocol does not amend constitutional semantics.
> Intake: GitHub Issue #30 — `P16 Internal Model Habitation Review Queue`

## 1. Mission

You are an **independent internal Resident Reviewer**, not a feature developer.

Your task is to actually inhabit and operate the current AIOS Core over a long synthetic life, use your own model cognition rather than benchmark-specific scripts, and discover:

- reproducible bugs;
- mechanism gaps;
- long-horizon cognition failures;
- memory / recall errors;
- Summary misuse;
- false or self-reinforcing cognition;
- revision / retraction failures;
- Entity / Relation errors;
- Dimension creation / lifecycle errors;
- Goal / Task / Action / Outcome failures;
- Wake / Periodic Review / CognitivePolicy failures;
- authorization / side-effect boundary errors;
- subject-isolation problems;
- restart / continuity problems;
- storage / indexing / scheduling / token-cost bottlenecks;
- concrete optimization opportunities.

The purpose is **discovery**, not to prove the system correct.

Do not declare P16 PASS or P17 READY.

## 2. Hard requirement: one reviewer, one different life

Every reviewer MUST create and run a life that is materially different from other reviewers.

This is **千人千面**, not one fixture with names replaced.

Do not copy another reviewer's persona, event sequence, relationship graph, goals, habits, communication style, or failure pattern.

Before freezing your first report, do **not** read other Arena reviewer reports. This preserves independent coverage and reduces groupthink.

A reviewer's life should vary across multiple dimensions, for example:

- daily rhythm and availability;
- work / study pattern;
- family and social network shape;
- interests and long-term projects;
- spending and order behavior;
- calendar and commitment style;
- communication brevity / verbosity / ambiguity;
- device / app / sensor usage pattern;
- travel or location-change frequency;
- recurring routines and exceptions;
- interruptions, noise and irrelevant events;
- relationship changes;
- goals that appear, evolve, conflict or are abandoned;
- delayed corrections and contradictory evidence;
- preferences that are stable, temporary, or revised.

Do not use political ideology or other sensitive traits as a steering mechanism for reviewer conclusions.

## 3. Hard requirement: minimum one full simulated year

Each review run MUST cover at least:

- **365 consecutive simulated days**;
- **12 month boundaries**;
- at least **365 observable life events** in aggregate;
- at least **240 user-AI interaction turns** in aggregate;
- at least **12 multi-turn long conversations** of 20+ turns each;
- at least **60 non-conversation reality inputs** from app/platform/device/sensor-style sources;
- at least **12 Goal/Task lifecycle opportunities**;
- at least **6 Action/Outcome opportunities**, including success, failure, cancellation or unavailable execution paths;
- at least **12 Periodic Review opportunities**;
- multiple day/week/month Summary windows;
- at least **6 delayed-truth or correction events** that can challenge earlier cognition;
- at least **12 ambiguous / deictic / cross-session references**;
- at least **6 deliberate noise bursts or irrelevant-event clusters**;
- at least **4 runtime restart / resume points**;
- at least **1 secondary decoy subject** for isolation probes.

A reviewer MAY exceed these numbers.

A run with sparse timestamps stretched across one year but only a handful of events is invalid.

## 4. Life must evolve

The synthetic person must not remain static for 365 days.

Across the year, introduce naturally spaced changes such as:

- new and completed goals;
- abandoned plans;
- recurring habits that later change;
- relationship changes;
- corrections to earlier statements;
- old events referenced months later;
- conflicting evidence from different times or sources;
- mistaken assumptions that should later be revised;
- preference changes based on explicit feedback;
- failed actions followed by later retry or strategy change;
- periods with little interaction and later resumption;
- long-session context pressure;
- old claims becoming stale after new evidence.

Do not pre-write a single “correct personality” or expected causal story for the Resident.

## 5. Use the real AIOS mechanisms

Exercise current Core paths rather than replacing cognition with a helper script.

Where applicable, use:

- WorldStore;
- WorldSearchIndex / recall;
- FusedTurnRuntime / CognitiveRuntime;
- long-context continuity and drill-down;
- multi-scale Summary;
- Claim / EvidenceSet / Dependency;
- revision / retraction;
- Entity / Relation;
- Event lifecycle;
- Dimension lifecycle;
- Goal / Task / Action / Outcome;
- Wake;
- Periodic Review;
- OperationExperience / CommunicationExperience;
- CognitivePolicy;
- restart / resume behavior.

A deterministic helper may generate timestamps, ids, bulk synthetic inputs, load, or scheduling.

A deterministic helper MUST NOT decide:

- what the user “really means”;
- which memory is semantically relevant;
- causal interpretation;
- user personality;
- relationship meaning;
- what new Dimension should exist;
- what Claim should be believed;
- what cognition is “correct”.

Those remain model decisions and review judgments.

## 6. Anti-cheat / independence rules

Do not:

- put expected answers into Resident-visible input;
- let the Resident read hidden oracle / judge notes;
- add benchmark-specific Core logic;
- hard-code a target Claim, Dimension, causal chain, personality or response;
- count string matching as cognition success;
- replace actual Resident reasoning with a pseudo-LLM;
- modify Core code to make your own scenario pass;
- reuse another reviewer's report as your own finding.

Internal runs are discovery evidence.

They count as formal P16 exit evidence only if they separately satisfy the provider-backed provenance, fresh-private-World, equal visible fingerprint, hidden-oracle isolation and raw-artifact requirements in `governance/P16_CONVERGENCE_CONTROL_2026-09-20.md`.

## 7. Required adversarial coverage

During the year, actively probe at least these classes:

1. relevant old memory should be found;
2. irrelevant old memory should stay out;
3. cross-session ellipsis / “that thing / that day / continue”;
4. long-session summary then exact raw drill-down;
5. old Claim contradicted months later;
6. stale cognition must not remain current;
7. assistant self-echo must not become user evidence;
8. Summary must not silently become source-of-truth;
9. false or weak Claim must not self-reinforce through Review;
10. CommunicationExperience must come from real feedback;
11. OperationExperience must require real Outcome;
12. learned CognitivePolicy must influence later cognition without becoming an unconstrained hard boundary;
13. Entity / Relation changes over time;
14. Event lifecycle transitions;
15. Dimension creation / merge / retire without dimension spam;
16. Task due → Wake → Resident continuation;
17. queued / suppressed / repeated Wake behavior;
18. failed / cancelled / unavailable Action path;
19. external side-effect authorization must remain outside the Resident;
20. restart after long inactivity;
21. same-world resume after runtime restart;
22. subject-isolation probes using the decoy subject;
23. late-arriving historical data and Summary rebuild/stale behavior;
24. noisy periods with many irrelevant events;
25. token / latency / index / storage growth pressure.

Do not turn this list into 25 fixed-answer questions. Embed them naturally into the year-long life.

## 8. What to submit

Do NOT fix Core on your review branch.

Submit evidence and diagnosis only.

Create:

`reviews/internal_habitation/<your-branch-or-reviewer-id>.md`

The report MUST contain:

- reviewer/model identity if available;
- base `main` SHA actually tested;
- review branch;
- simulated start and end dates;
- total simulated days;
- event / conversation / action / review counts;
- persona/life fingerprint or seed;
- which AIOS mechanisms were exercised;
- exact reproducible findings;
- evidence paths / object ids / revisions / timestamps where available;
- expected mechanism vs observed mechanism;
- severity: BLOCKER / HIGH / MEDIUM / LOW / OPTIMIZATION;
- whether the finding is confirmed, suspected, or not reproducible;
- minimal reproduction instructions;
- suggested mechanism-level direction, if any;
- explicit list of things tested that did **not** fail.

For every finding, distinguish:

- **bug** — implementation violates an intended invariant;
- **mechanism gap** — architecture lacks a needed general mechanism;
- **optimization** — system is correct but inefficient / noisy / costly;
- **model behavior** — resident made a poor judgment but Core behaved as designed;
- **test artifact** — scenario / harness caused the issue;
- **insufficient evidence** — plausible but not proven.

## 9. Submission routing

Commit the report and optional non-Core evidence artifacts to your own review branch.

Do not merge Core changes.

Then add one short comment to Issue #30 containing:

- branch name;
- tested `main` SHA;
- report path;
- number of BLOCKER / HIGH / MEDIUM / LOW / OPTIMIZATION findings;
- whether the 365-day minimum was completed.

Do not open competing implementation PRs unless the project lead later assigns a specific confirmed finding for repair.

## 10. Central triage rule

All reviewer findings are hypotheses until independently triaged against current `main`.

The project lead / chief reviewer will:

1. deduplicate overlapping reports;
2. reject stale or non-reproducible findings;
3. distinguish model mistakes from Core defects;
4. compare findings against constitution and current runtime semantics;
5. prioritize confirmed general-mechanism defects;
6. implement fixes from the latest `main` on dedicated repair branches;
7. add regressions;
8. merge only after the relevant gates pass;
9. update Issue #30 with disposition.

Reviewer count is not a vote.

Ten reports repeating the same unsupported claim do not outweigh one reproducible counterexample.

## 11. Completion condition for one internal reviewer

Your assignment is complete only when:

- at least 365 simulated days are finished;
- the density requirements above are met;
- the life is materially unique;
- you actually exercised the AIOS mechanisms rather than only reading source;
- findings have reproducible evidence;
- your report is committed to your branch;
- Issue #30 contains the intake comment.

If no bugs are found, submit the same report with the coverage evidence and state that no reproducible defect was found in your run.

The goal is not to manufacture findings. The goal is to expose real ones.
