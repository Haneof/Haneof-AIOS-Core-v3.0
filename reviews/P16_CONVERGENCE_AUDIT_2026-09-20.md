# AIOS v3.0 P16 Convergence Audit — 2026-09-20

> Role: project-level convergence / correctness audit
> Audited branch: `main`
> Last verified functional anchor before governance-only commits: `1fc7b9f5c69b01f01dac8097efd29973bc4dbf4c`
> Governing baseline: `docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md`
> Construction control: `governance/P16_CONVERGENCE_CONTROL_2026-09-20.md`

## Executive result

The AIOS v3.0 mainline is not globally stalled. P0-P15 are integrated and the P16 deterministic habitation harness is structurally usable.

However, **P16 must not be declared cognition-complete or advance to P17 yet**.

The audit found four correctness gaps around P15 review/experience semantics and several P16 evidence gaps. One quarantined red-team branch contains useful hardening ideas that are not yet in main; it must be mined selectively, never wholesale-merged.

## Confirmed strengths

1. Unified WorldStore + rebuildable WorldSearchIndex remain the shared substrate.
2. Conversation raw facts enter the world before resident inference.
3. Continuity summaries remain indexes and pin raw dialogue; they are not Claims.
4. C09 registered mechanical trigger -> durable Wake -> Step-0 -> same CognitiveRuntime is implemented.
5. Periodic Review uses the same resident CognitiveRuntime and does not fabricate Conversation observations.
6. Habitation resident/oracle file separation, fresh private candidate worlds, public fingerprinting, final virtual horizon and future-sample leak checks are present.
7. Current deterministic Gates are green, but they prove mechanics rather than real-model cognition.

## Blocking / high-severity findings

### A1 — BLOCKER — OperationExperience does not enforce “real result” evidence in main

Main `PeriodicReviewService.commit_operation_experience()` only verifies that referenced objects exist. It does **not** enforce:

- same `subject_id`;
- allowed real-case object types;
- rejection of Claim-as-result evidence;
- positive/negative ref disjointness.

This allows a model-authored Claim to be cited as the “real case” for an OperationExperience, which can then support a strategy Claim. That creates a self-reinforcement path contrary to the evidence/outcome boundary.

The quarantined branch `hardening/p15-review-growth-redteam-20260920` contains a useful candidate rule: only Observation / Outcome / CommunicationExperience may serve as operation-case evidence, plus subject isolation.

**Required action:** re-implement this hardening from current main and add regression tests. Do not merge the old branch wholesale.

### A2 — BLOCKER — Periodic Review candidate truncation can permanently skip evidence

Main `_collect_candidates()` keeps only the newest `max_candidates`. After the review completes, the next window starts at the previous review's `last_hit_at`.

If a review window contains more candidates than the configured cap, older candidates dropped by truncation are never revisited: the cursor advances past them.

This means important world evidence can be permanently absent from periodic cognition.

The quarantined red-team branch contains a backlog/paging concept that tracks reviewed refs within a fixed window and drains truncated pages.

**Required action:** implement deterministic backlog paging with exact reviewed-ref accounting and a regression that proves >max_candidates cannot lose evidence.

### A3 — BLOCKER — Budget exhaustion is recorded as a completed review

`CognitiveRuntime` correctly returns termination reasons such as:

- `tool_round_budget_exhausted`;
- `capability_call_budget_exhausted`.

But main `FusedTurnRuntime.run_periodic_review()` unconditionally calls `complete_review()`, and `complete_review()` moves the Wake to `COMPLETED` regardless of termination reason.

A review can therefore be marked finished even though the resident model ran out of execution budget before finishing its work.

The quarantined red-team branch contains the correct direction: leave such a Wake resumable/RUNNING rather than falsely complete it.

**Required action:** define terminal-success vs resumable-exhaustion semantics and test process restart after exhaustion.

### A4 — HIGH — OperationExperience identity is under-specified

Main stable identity currently hashes roughly:

- subject;
- problem type;
- method path;
- combined case refs.

It omits:

- result summary;
- applicability;
- cost;
- misses;
- experience state;
- positive vs negative polarity separation.

Distinct experiences can therefore alias to the same object/idempotency identity, especially if the same case refs and method path are reinterpreted.

The quarantined red-team branch includes a better canonical identity shape.

**Required action:** canonicalize the full immutable experience content and keep positive/negative ref lists distinct in identity.

### A5 — BLOCKER FOR P16 EXIT — No provider-backed resident integration exists

Current `ModelHandler` is only a callable boundary. The project currently has no provider-backed implementation, provider dependencies, or committed runner for GPT/Claude/Gemini-style residents.

Therefore no current Gate proves long-horizon AI cognition quality.

**Required action:** provider-backed ModelHandler + RoundSummaryHandler, deterministic configuration capture, error/retry semantics, and raw run artifacts.

### A6 — HIGH — P16 does not yet prove restart/model-handoff continuity

`CurrentCoreHabitationTarget` is created fresh by default and keeps:

- virtual clock;
- next review time;
- per-session turn counters

in process memory.

The current harness has no durable resume/handoff protocol that reconstructs these values from an existing World. Yet the project completion definition requires continuity across restart/model replacement.

**Required action:** add a restart/handoff scenario that reopens the same World, reconstructs scheduling/session state, swaps model handler if required, and continues without duplicate turn identities or missed due work.

### A7 — HIGH — Evaluator contract is a schema, not yet an independent evaluator

`evaluation.py` validates evaluator-supplied findings, but it does not derive findings from the sealed oracle. A caller can construct arbitrary pass/fail findings as long as event IDs are valid.

Oracle fixtures also do not currently expose one uniform validated criterion schema; e.g. some contain `criteria`, while `learning_independence_v1` uses latent truth/event annotations without the same field.

**Required action:** define a versioned evaluator contract and implement evaluator-only logic that maps oracle criteria + run artifacts to evidence-backed findings. Preserve room for model-based qualitative evaluation, but record evaluator model/version/config as provenance.

### A8 — MEDIUM — Candidate model identity can be mislabeled

`HabitationRunner.run_models()` trusts the mapping key `model_id`; the target's internally configured model identity is not contractually checked against it.

With real providers this can produce an artifact labeled as model A while the target actually invokes model B.

**Required action:** expose/verifiably bind candidate identity/provenance at the target contract boundary.

### A9 — MEDIUM — P16 workflow trigger surface is too narrow

The P16 workflow currently triggers mainly on `tests/habitation/**` and P16 docs/workflow paths. Changes to runtime/review/wake/ingest code can materially alter habitation behavior without necessarily running the P16 harness in that workflow.

**Required action:** add relevant Core paths or a release-level aggregate Gate before P16/P17 transitions.

## Quarantined branch disposition after audit

### `hardening/p15-review-growth-redteam-20260920`

**SALVAGE REQUIRED, DO NOT MERGE.**

Useful concepts observed:

- real-case type and subject validation;
- positive/negative disjointness;
- fuller OperationExperience identity;
- review backlog paging;
- resumable semantics for budget exhaustion.

These must be ported selectively onto current main with new tests.

### `p15/periodic-review-growth-20260920`

**TEST-MINING ONLY.**

It represents an older competing P15 design. Some tests express useful invariants, but the implementation shape is superseded by main. Never merge it wholesale.

### `p16/habitation-integration-20260920`

**ARCHIVE / REFERENCE ONLY.**

It contains older C09/P16 structure (including superseded wake module layout). Current main has the accepted C09 service and merged P16 harness. Do not revive this branch.

## Required execution order

Use the single active branch `p16/provider-backed-habitation-20260920`.

1. Recover A1-A4 as current-main hardening + regression tests.
2. Run P15 + C09 + P16 deterministic aggregate regression.
3. Implement A5 provider-backed resident + summary handlers and provenance.
4. Implement A6 restart/model-handoff scenario.
5. Implement A7 evaluator-only contract/runner.
6. Fix A8 identity binding and A9 aggregate workflow.
7. Run multiple real models independently on identical resident-visible lives.
8. Red-team artifacts for memory misuse, unsupported cognition, revision failure, summary misuse, meaningless dimension creation, and self-reinforcing experience.
9. Only then consider P16 PASS and P17 entry.

## Gate decision

**P16: CONTINUE / NOT PASS**

The mechanical foundation is strong enough to continue. The evidence is not strong enough to claim real long-term cognition or Core release readiness.
