# C14-LOOP-001 Independent PM Acceptance Review

> Date: 2026-09-21  
> Verdict: **PASS**  
> Reviewed main: `511df9941e12a281fe8260840bd8a1fd936664b6`  
> Candidate: `f48c3c9cfa8a24fa2e0e0220d7fe20bcda1be34d`  
> PR: #65  
> Squash merge: `a385f7b3fcc71982aae0611a382502c9a37ba71e`

## 1. Independent verification scope

PM independently re-read the merged implementation rather than relying on the task report.

Verified:

- current Task Board state;
- PR #65 and exact candidate;
- all 14 required workflow runs and their `head_sha`;
- completion evidence;
- candidate/merge/main blob equivalence for changed Core files and C14 tests;
- post-merge changes are governance/evidence only;
- C14 AttentionBundle contract preservation;
- runtime-incomplete lifecycle and restart recovery;
- partial Claim retry idempotency;
- C13/background budget treatment of unfinished provider calls;
- self-excitation boundary for old AI cognition;
- mixed lineage with genuinely new reality;
- reconcile support-graph scale fix;
- fresh-runtime durable cognition retrieval.

## 2. Workflow verification

All 14 reported workflows completed SUCCESS on exact candidate:

`f48c3c9cfa8a24fa2e0e0220d7fe20bcda1be34d`.

This includes the C14 LOOP/SCHED/RUNTIME workflows and the required P16 convergence, constitutional cognition closure, P15, P14, P12, C09, Fused Runtime, Dimension Summary, P11, P10 and P9 regressions.

The C14 LOOP aggregate jobs also completed SUCCESS for:

- targeted loop;
- runtime/wake/attention/budget;
- cognition/AI-world;
- summary/index/P12;
- P15/C13/P14/T28;
- P16 habitation harness;
- full P16 convergence.

## 3. C14 bundle contract

The implementation reuses the existing AttentionRouter/AttentionBundle rather than adding another queue.

Bundle membership is mechanically partitioned by execution contract.

For C14:

- only COGNITIVE_DERIVATION members are bundled together;
- every member Wake revision is pinned;
- every member Summary revision is recoverable from its pinned Wake;
- runtime validates bundle membership before restoring effective wake source to `COGNITIVE_DERIVATION`;
- cognition-only side-effect allowlist remains binding;
- leaf-grounding remains binding;
- user delivery remains suppressed;
- ordinary broader-write background Wakes are not mixed into the C14 bundle.

No contract laundering blocker remains.

## 4. Runtime-incomplete lifecycle

For effective C14 work, only semantic terminal outcomes close the opportunity.

Runtime/model/tool/capability budget exhaustion is persisted as durable QUEUED runtime-incomplete work.

Independent review verified:

- unfinished bundle survives SQLite reopen;
- member Wake/Summary refs survive restart;
- runtime-incomplete individual work is excluded from creation of a new bundle;
- a partial successful Claim remains durable;
- retry of the same grounded Claim remains idempotent;
- stable first-start write time preserves semantic write identity across retry.

This closes the prior false-COMPLETED and partial-rebundle identity-reset risks.

## 5. Budget / Metering

C13 MeteringLedger remains the provider-call/token source of truth.

The PM specifically checked the same-Wake retry case:

`BackgroundBudgetGate.evaluate()` excludes the current Wake from the general world scan, then explicitly adds its queued runtime-incomplete historical usage back through `_queued_runtime_incomplete_usage()`.

Therefore unfinished provider spend:

- counts against other background Wakes;
- also counts against the same unfinished Wake's own retry budget;
- remains visible after eventual completion through all MeteringLedger rows.

No free-retry budget bypass was found.

## 6. Self-excitation and provenance

The shared provenance walker now distinguishes full lineage from direct grounding lineage.

An old AI Claim may have historical reality support and therefore produce a MIXED full lineage, but if the only route to that old reality passes through the prior AI semantic assertion, the Summary has no qualifying direct `grounding_leaf_refs` for immediate C14 scheduling.

Result:

`old AI Claim -> AI Summary -> immediate C14 Wake`

is blocked.

A Summary containing both old AI cognition and a genuinely new direct reality/user leaf remains eligible.

This is based on durable provenance structure, not Claim text, keywords, counts or semantic scoring.

## 7. Reconcile scale

`CognitiveDerivationScheduler.reconcile()` now builds the support Dependency graph once per reconciliation pass and reuses it.

The targeted regression verifies one support-graph build across 200 Summary candidates.

No second provenance database or semantic index was introduced.

## 8. New-runtime retrieval

A deterministic engineering proof confirms that after:

- durable cognition write;
- original runtime disposal;
- SQLite World reopen;
- new WorldSearchIndex;
- new FusedTurnRuntime;
- fresh session with no prior dialogue injection;

the exact cognition revision is recovered via normal AIOS capabilities:

`read_ai_world -> search_world -> inspect_world_object`.

This proves persistence/retrieval plumbing only.

It does **not** satisfy the semantic behavior requirement reserved for `C14-RES-001`.

## 9. PM decision

`C14-LOOP-001 = PASS`.

No further Core blocker was found in the LOOP acceptance scope.

`C14-RES-001` may proceed.

C14 is **not** closed. The next task must use a real Resident model and must prove semantic behavior rather than deterministic mechanism:

1. genuine cross-dimensional positive cognition;
2. matched negative silence/no unsupported cognition;
3. contradiction leading to evidence-grounded revision/retraction/retention;
4. original model session/runtime termination;
5. fresh runtime/session restoring only durable AIOS state;
6. prior cognition materially participating in a later independent decision;
7. later Outcome/new evidence feeding cognition again.

Pseudo-LLM, Python semantic answer generation, keyword rules, precomputed expected cognition, or using chat-window memory as Resident memory invalidates the evidence.
