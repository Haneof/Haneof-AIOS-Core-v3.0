# AIOS v3.0 Second-Pass Code Completeness Closure

Date: 2026-09-20

Source audit:

- `reviews/AIOS_V3_CODE_COMPLETENESS_REAUDIT_2026-09-20.md`
- audit commit: `5a2f569040ab0160923cbd805b2ebcdeaeb3b65b`

Closure PR:

- PR #21: `core: close second-pass code completeness blockers`
- accepted head: `029d8f6849cdb08e2c784cd3bded0b025d1e03e6`
- squash merge: `9d9fb9d82ef42b631d032c488617316c5a2a244c`

## Closure verdict

The second-pass code blockers are closed at the deterministic / code-completeness level.

This does **not** constitute P16 cognition quality PASS. Real provider-backed habitation evidence is still required.

## Closed BLOCKER 1 — private-world subject isolation

Implemented:

- `WorldSearchIndex.search_mind(..., subject=...)`
- timeline / entity / ALL_DIMENSIONS / DimensionSummary reads are subject scoped
- retrospective annotations inherit the subject of their target instead of hard-coded `user_1`
- direct Runtime object-id reads use a private-world scope
- continuity summary drill-down validates source subject
- Claim / Revision / Dimension / Execution / Event / CommunicationExperience / CognitivePolicy / Entity / Relation write paths validate reference scope
- AI-self cognition keeps an explicit user + AI-self evidence exception inside the same private world

The implementation intentionally does **not** use a naive “all refs must have identical subject_id” rule, because AI self-cognition is a distinct subject by design.

## Closed BLOCKER 2 — CognitivePolicy operational loop

Implemented:

- resident capability to propose an AI-mutable `CognitivePolicy`
- AI policy registration/update/rollback requires pinned real-result evidence
- AI Claim cannot directly train its own policy
- assistant-generated conversation Observation cannot count as policy result evidence
- policy evidence is subject scoped
- bounded `evaluation_window` is parsed to a durable evaluation due time
- due policies are routed into Periodic Review
- Runtime consumes effective policy values; current concrete consumers include:
  - `memory.recommendation_limit`
  - `communication.detail_level` in model-facing task context
- policy rollback remains forward-only and historical versions remain visible

This closes the “versioned ledger only” gap without moving semantic policy judgment into deterministic code.

## Closed BLOCKER 3 — multi-scale Summary live scheduling

Implemented:

- P16 Current-Core wires a dimension summary handler
- provider-backed summary handler distinguishes conversation summary from dimension summary and uses a constitution-safe single-dimension prompt
- habitation virtual time runs `run_due_dimension_summaries()`
- closed windows are derived from durable world material, so process downtime cannot permanently skip old windows
- late-arriving facts reopen the appropriate historical window when source identity changes
- terminal Dimension lifecycle states are excluded from active summary maintenance
- truncated source windows are never published as CURRENT
- when a previously CURRENT summary later becomes incomplete because of source overflow, it is forward-marked STALE

## Closed HIGH — Topic / Need-History

Removed the mechanical `len(topic) >= 4` history rule.

History prefetch now opens from:

- explicit historical cues
- canonical continuation state
- explicit trusted topic hints
- exact durable world anchors such as an Entity / Event / Goal / Task mention

A generic topical question no longer automatically receives personal history merely because it has enough characters.

## Closed HIGH — Entity / Relation production loop

Added resident-facing, evidence-grounded world graph writeback:

- propose Entity
- revise Entity
- upsert Relation
- pinned evidence
- subject isolation
- forward Entity revision
- durable Dependency provenance
- Relation lexical indexing and relation traversal

The resident model supplies identity and relationship meaning; deterministic Core does not infer them.

## Closed HIGH — stable identity encoding

Claim / Revision / Dimension / Execution / Summary identity construction was moved away from delimiter-joined strings to canonical structured JSON hashing, matching the collision-safe pattern already used elsewhere.

Regression covers delimiter-boundary collision.

## Closed HIGH — fail-closed durable reads

Removed broad exception swallowing from the audited truth paths.

Durable store failure is no longer silently converted into:

- “object missing”
- “annotation-only object”
- “memory not found”
- “nothing to recommend”

Projection-only exceptions are retained only for explicitly projection-owned annotation objects.

## Closed HIGH — Event lifecycle

Added an explicit Event state transition matrix.

Terminal structural states do not silently jump back to ACTIVE. Reopening of resolved/rejected interpretation requires an explicit REVISED revision with evidence.

## P16 coverage expansion

Added sealed fixture:

- `tests/habitation/fixtures/cognition_system_closure_v1.manifest.json`

It contains a longer multi-thread synthetic life covering:

- Entity / Relation continuity
- Event revision
- real communication feedback
- policy adaptation / authorization boundary
- project + relationship separation
- dynamic learning thread
- temporary family routine that later ends
- long-horizon cross-dimensional review
- explicit anti-causality / uncertainty requirement

Resident stream and hidden oracle remain physically separated.

## Regression evidence

Accepted PR head:

`029d8f6849cdb08e2c784cd3bded0b025d1e03e6`

All 20 triggered workflows completed with `success`, including:

- `constitutional-cognition-closure`
- `p16-convergence-gate` / full-core regression
- `p16-habitation-harness`
- `p15-periodic-review`
- `c09-wake-dispatch`
- `fused-turn-runtime`
- `world-index`
- `memory-recommendation`
- `dimension-summary`
- `all-dimensions-projection`
- `cognition-writeback`
- `cognition-revision`
- P9 / P10 / P11 / P12 gates
- P14 long-context

The new second-order regression suite is also pinned into the constitutional cognition closure workflow.

## Current project verdict

- Architecture direction: **PASS**
- Core spine: **STRONG**
- PR #20 first-order closure: **VALID**
- PR #21 second-order code completeness closure: **PASS**
- deterministic code completeness for the audited findings: **PASS**
- P16 cognition quality: **NOT PASS YET**
- P17: **BLOCKED until P16 real-model evidence exists**

## Remaining project-level blocker

The remaining blocker is now again external evidence, not another known Core code gap:

> produce at least two real provider/model independent habitation runs on the same sealed life, with identical resident-visible fingerprint, durable world/run provenance, separate hidden-oracle evaluation, offline comparison, and red-team review of actual cognition behavior.

Deterministic tests prove mechanics, isolation, provenance and runtime wiring. They do not prove that real resident models will form stable, evidence-grounded long-term cognition.
