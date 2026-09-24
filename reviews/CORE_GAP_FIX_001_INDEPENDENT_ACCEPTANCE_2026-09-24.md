# CORE-GAP-FIX-001 Independent Acceptance — 2026-09-24

## Verdict

**ACCEPTANCE_FAIL**

PR #145 exact candidate `b5a50435b3f9048bf94d88e9625b9e5bc2b83f42` closes the originally reproduced search / exact-inspect / AI-world / resumed C14 / resumed Periodic Review cases covered by its tests, and its exact-head CI is green. However, independent path inspection found one remaining model-visible temporal leak in resumed C14: `runtime_derived_lineage` is recomputed through the current, uncut `CognitionEvidencePolicy` store. A support `Dependency` learned only at T2 can therefore add a T2 leaf reference to the cockpit of an execution whose original cognition/write time is T1.

Because CG-001 requires **all** model-visible world/cognition paths to obey the same historical read cut, this is a blocking temporal-integrity defect. The exact candidate must not be handed to PM for integration.

## Review identity and pinned state

- Role: Independent Core Runtime / Temporal Integrity Acceptance Reviewer.
- Review-time live `main`: `a424cb9dee37d5fb20d85f4ba03f2bb2f83863a7`.
- Reviewed PR: #145 — `CORE-GAP-FIX-001: enforce runtime temporal read cut`.
- Reviewed exact head: `b5a50435b3f9048bf94d88e9625b9e5bc2b83f42`.
- PR #145 at review: OPEN, UNMERGED, non-draft, exact head unchanged; REST recomputation reported `mergeable=true`, `mergeable_state=clean`.
- Governance gate: `CORE-GAP-FIX-001 = GATE / REVIEW_READY`.
- PR #157 / CORE-GAP-FIX-003 at start and pre-report recheck: OPEN, UNMERGED, exact head `81d626820cfa31e4f3f1aba0e892eb48cb11e46c`. Serialization rebase rule was therefore not triggered during the acceptance review.
- FIX-002 integration receipt confirms #143 exact `c5382a1653b66654df23d0938d9d19a80a12619c` was accepted and integrated as `3d980fadf6beefcdd02ff4367ba834a5b013d871`.

## Required governance inputs

Read from review-time `main`:

1. `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
2. `AIOS_v3.0_CURRENT_CHECKPOINT.md`
3. `PROJECT_MASTER_MAP.md`
4. `reviews/CORE_GAP_AUDIT_001_2026-09-24.md`
5. `governance/prompts/CORE_GAP_FIX_001_2026-09-24.md`
6. `governance/prompts/CORE_GAP_FIX_001_RESUME_AFTER_FIX_002_2026-09-24.md`
7. `governance/AIOS_CORE_S2_POST_FIX002_PARALLELISM_RULING_2026-09-24.md`
8. `governance/CORE_GAP_FIX_002_INTEGRATION_RECEIPT_2026-09-24.md`

The governing requirement is unchanged: a resumed execution whose original cognition/write time is T1 must see World **as known at T1**, not current T2 state, across every model-visible path.

## Before-fix reproduction

Reproduction-only SHA:

`a9a089a65414f9ba3a4b3dd6721edc3f05773834`

Raw GitHub Actions logs were independently re-read.

| Surface | Run / job | Raw result | Independent finding |
|---|---|---|---|
| fused-turn-runtime | 35961012015 / 107509381835 | 28 passed / 2 failed | T2 late fact visible in T1 historical search; missing/corrupt `learned_at` exact inspect did not fail closed |
| P15 Periodic Review | 35961012024 / 107509381909 | 103 passed / 3 failed | resumed T1 review saw `obs_cg001_review_t2_late`, plus fused failures |
| C14 Runtime | 35961012033 / 107509382050 | failed targeted CG-001 case | resumed T1 C14 saw `obs_cg001_c14_t2_late` |
| P16 full | 35961012003 / 107509381746 | failed | same CG-001 failures reproduced in full repository regression |

**Before-fix verdict: CG-001 = REPRODUCED.**

## Exact changed-file scope

PR #145 changes exactly eight files.

Core:

1. `src/aios_core/context/continuity.py`
2. `src/aios_core/projections/all_dimensions.py`
3. `src/aios_core/query/search.py`
4. `src/aios_core/recommendation/proactive.py`
5. `src/aios_core/runtime/turn_runtime.py`

Tests:

6. `tests/integration/test_v3_c14_cognitive_derivation_runtime.py`
7. `tests/integration/test_v3_fused_turn_runtime.py`
8. `tests/integration/test_v3_periodic_review.py`

No governance, review, operator, fixture, Resident evidence, UI, or hardware files are modified.

No FIX-003 user-turn retry/reconciliation state-machine files are modified. Filtering the `turn_runtime.py` patch for user-turn retry / reconciliation / `IN_DOUBT` / attempt / metering / budget terms found no changed FIX-003 state-machine line; the only matching temporal state line was the relocation/use of `runtime_first_started_at`.

## Temporal model implemented by the candidate

The candidate introduces a read-only `_KnowledgeCutoffStoreView` that forces `knowledge_cutoff=Tcut` into `get_payload` and `list_payloads`. Runtime helper readers for AI-world cognition, conversation continuity, cognitive policies, ALL_DIMENSIONS projection, exact scoped payloads, relations, dimensions, execution world, attention watches, timeline/entity recall, and recommendation are routed through the cut or pass `as_of=Tcut` into `WorldSearchIndex`.

`SQLiteWorldStore.get_payload(object_id, revision=None, knowledge_cutoff=Tcut)` selects the newest revision with `learned_at <= Tcut`. This is the correct primitive for “latest knowable revision”, not “take current latest then filter”.

`WorldSearchIndex` historical paths similarly use `_payload_at_cutoff` / `_known_at_cutoff` and compare the candidate row to the selected historical revision. Current-view tombstones/latest filtering is not incorrectly reused for historical views.

## Resumed entrypoint ordering

### C14 / run_wake

The candidate derives `active_write_time` from the durable original `runtime_first_started_at` / `started_at` before building semantic cockpit state. AI-world core context, AI-world snapshot, cognitive policy context, and world map are explicitly built with that T1 value before the model runs.

`_active_turn_time` itself is assigned after `ContextController.assemble`, but the reviewed cockpit builders named above do **not** first read current T2 cognition: they receive T1 explicitly. Once model capability execution begins, `_active_turn_time=T1` constrains search/inspect/recall capabilities.

### Periodic Review

The same pattern is used with the original review `started_at`: `review_write_time` is resolved before AI-world, policy, and world-map cockpit construction; model capability execution is then run with `_active_turn_time=review_write_time`.

This ordering is correct for the paths that were converted to cutoff-aware readers. The blocker below is a separate pre-model C14 cockpit read that was not converted.

## Read-cut coverage review

| Model-visible path | Verdict | Basis |
|---|---|---|
| `search_world` | PASS | `recall_candidates(..., as_of=_active_turn_time)` |
| exact inspect / scoped payload | PASS | cutoff store floating read selects latest knowable revision; explicit future rev fails unavailable/closed |
| AI-world current cognition | PASS | cutoff `AIWorldCognitionService` |
| cognitive policy context | PASS | cutoff `CognitivePolicyRegistry` |
| World map | PASS | `dimension_directory(as_of=Tcut)` + dimension definitions at `knowledge_cutoff=Tcut` |
| execution Goals / Tasks / Actions | PASS | cutoff store lists |
| dimensions | PASS | cutoff store lists |
| attention watches | PASS | cutoff TASK list plus watch predicate filtering |
| Relation follow | PASS | cutoff RELATION list |
| timeline recall | PASS | `search_mind(..., as_of=Tcut)` |
| entity recall | PASS | `search_by_entity(..., as_of=Tcut)` |
| conversation summaries / drill-down | PASS | cutoff continuity reader; search also passes `as_of` |
| proactive memory recommendation | PASS | historical recall/recent candidates plus cutoff store |
| ALL_DIMENSIONS projection | PASS | projection built on cutoff store plus `as_of` |
| C14 `runtime_derived_lineage` | **FAIL** | uses current uncut `CognitionEvidencePolicy._support_dependencies()` and uncut exact traversal |

Therefore the required “all model-visible paths obey one Tcut” condition is **not** satisfied.

## Search AS_KNOWN

**PASS for the reviewed search paths.**

- T1-known facts remain visible.
- T2-only facts are removed by `as_of`.
- Historical row selection is checked against the revision returned by the historical payload lookup, so a later current revision does not erase an earlier knowable revision.
- Missing/blank/malformed `learned_at` fails closed in historical search selection.
- Candidate current-time control test shows a current fact remains visible.

## Exact historical revision selection

**PASS.**

Independent revision-ladder path probe:

- object rev0 learned at T0
- rev1 learned at T1
- rev2 learned at T2
- historical cut = T1.5

`SQLiteWorldStore.get_payload(..., revision=None, knowledge_cutoff=T1.5)` orders eligible revisions descending after `learned_at <= T1.5`; therefore rev1 is selected. `_scoped_payload` uses that floating cutoff lookup for inspect, and historical search uses the same selected historical payload to admit only its matching index revision.

The candidate's exact-head fused test independently exercises the two-revision form of the same invariant and confirms historical AI-world/search/floating inspect returns rev1 rather than current rev2 or nothing.

## Missing / corrupt learned_at

**PASS for search, inspect, recommendation/projection entry paths reviewed.**

- exact historical inspect raises `ValueError` on missing/corrupt `learned_at`;
- `WorldSearchIndex._known_at_cutoff` / `_payload_at_cutoff` fail closed;
- recommendation and projection consume the same cutoff-aware candidate selection and a cutoff store.

Current-time execution does not silently treat malformed timestamps as known-before-cut; current normal objects with valid current `learned_at` remain visible.

## Current-time control

**PASS.**

Ordinary user turns use the turn's `occurred_at` as their current read/write cut. The candidate test `test_cg001_current_time_control_keeps_current_fact_visible` confirms a fact learned at the current turn remains visible through both search and exact inspect. The implementation does not force ordinary turns onto an older historical snapshot.

## AI-world cognition temporal behavior

**PASS for AI-world Claim revision selection.**

The exact-head fused regression creates an earlier cognition revision and a later corrected revision, then verifies the historical T1 runtime sees the earlier revision in:

- cockpit AI identity,
- `search_world`,
- `read_ai_world`,
- floating `inspect_world_object`.

This protects User Understanding / Relationship / Calibration / Strategy records routed through the AI-world reader. It does not cover the independent C14 lineage leak described below.

## Adversarial probes

### Probe A — revision ladder

**PASS.**

T0 rev0 / T1 rev1 / T2 rev2 with cut T1.5 selects rev1 through the store cutoff primitive and preserves that revision through inspect/search selection.

### Probe B — mixed cockpit

**PASS for the named mixed cockpit surfaces.**

With User Understanding at T1, Strategy at T2, Relation at T1, and Summary at T2, the reviewed readers behave as follows at historical T1:

- AI-world User Understanding: visible;
- AI-world Strategy T2-only record: excluded;
- T1 Relation: visible through cutoff relation list;
- T2 Summary: excluded by cutoff continuity/search.

### Probe C — malformed timestamp

**PASS.**

Malformed/missing `learned_at` is not treated as known-before-cut in index selection and exact inspect fails closed. Current valid semantics remain unaffected.

### Additional Probe D — late C14 support dependency

**FAIL — blocking.**

This probe targets a model-visible path not covered by the candidate's added tests.

1. At T1, persist Summary `S@1` with valid T1 grounding and start a C14 execution so its durable original runtime start is T1.
2. Let the C14 execution remain resumable.
3. At T2, persist a new reality fact `L@1` with `learned_at=T2`.
4. At T2, persist a valid `Dependency` `D@1` with:
   - `dependency_type="summary_uses_source"`
   - `dependent_ref=S@1`
   - `dependency_ref=L@1`
   - `learned_at=T2`.
5. Resume C14 at T2. The execution's semantic read/write cut is still T1.
6. `run_wake` computes `runtime_lineage = self.cognitive_derivation.derive_lineage(summary_ref)`.
7. `CognitiveDerivationScheduler.derive_lineage` delegates to the shared `CognitionEvidencePolicy`.
8. `CognitionEvidencePolicy._support_dependencies()` calls the uncut current `self.store.list_payloads(object_type=DEPENDENCY)`, so T2 dependency `D@1` is included.
9. `_walk` then follows `L@1` through the uncut store. No `learned_at <= T1` check is applied on this path.
10. `DerivedLineageView.audit_payload()` exposes leaf and grounding-leaf ObjectRefs.
11. `run_wake` places that payload into model-visible `task_context["cognitive_derivation"]["runtime_derived_lineage"]` (and analogously for C14 bundle members).

**Expected:** T2 dependency and T2-only leaf must be absent from the resumed T1 cockpit.

**Actual:** the current dependency graph can inject the T2-only leaf ref into the T1 cockpit and can also change lineage classification / grounding state.

This is a future-information leak before model execution. Even if later write validation rejects citing the T2 ref directly, the model has already observed future world structure and can change its T1-authored cognition accordingly.

## Blocking defect

### CORE-GAP-FIX-001-ACCEPT-BLOCKER-001 — C14_RUNTIME_DERIVED_LINEAGE_NOT_CUTOFF

- **Reproduction:** Probe D above.
- **Expected:** every C14 model-visible lineage computation for a resumed T1 execution is derived from World dependencies and exact refs knowable at T1 only.
- **Actual:** `runtime_derived_lineage` traverses the current dependency graph and can include a T2 dependency / T2 fact ref.
- **Affected read path:** `run_wake` → `CognitiveDerivationScheduler.derive_lineage` → `CognitionEvidencePolicy.derive_lineage_for_refs` → `_support_dependencies` / `_walk` → `audit_payload` → C14 cockpit `runtime_derived_lineage`.
- **Temporal integrity impact:** a T1 execution can observe T2 world structure/evidence and then make a T1 cognition decision, violating `World AS KNOWN AT T1`.
- **Minimal corrective scope:** make C14 runtime lineage derivation cutoff-aware at `active_write_time`, for both direct C14 Wake and C14 bundle. Either construct a read-only `CognitionEvidencePolicy` / derivation reader over the cutoff store or add an explicit knowledge cutoff to lineage derivation so both Dependency enumeration and exact object traversal fail closed beyond Tcut. Add a regression that inserts a T2 `summary_uses_source` dependency and T2 leaf against a T1 Summary, then resumes at T1 and asserts neither appears in `runtime_derived_lineage`. Do not alter FIX-002 attempt identity/state/reconciliation/metering/budget/lifecycle/completion or FIX-003 user-turn recovery.

**Blocker count: 1.**

## FIX-002 compatibility

**PASS on the reviewed FIX-002 surfaces.**

PR #145 does not change `background_attempt.py`, `turn_execution.py`, or the FIX-002 state-machine implementation. The `turn_runtime.py` changes are temporal read/cockpit changes and original-start ordering only.

The exact-head C09 Wake and P15 suites are green, and no diff was found that changes:

- background attempt ID,
- admitted / dispatching / in_doubt semantics,
- reconciliation,
- metering,
- budget,
- Wake lifecycle,
- Review lifecycle,
- completion semantics.

The acceptance failure is therefore not a FIX-002 regression.

## FIX-003 scope isolation

**PASS.**

PR #145 does not implement user-turn retry authorization, user-turn attempt reconciliation, or completion recovery state-machine work owned by PR #157. No FIX-003 scope crossover was found.

## Exact-head CI verification

All 17 workflows attached to exact head `b5a50435b3f9048bf94d88e9625b9e5bc2b83f42` were independently enumerated and reported `completed / success`.

Key raw-log checks:

| Gate | Run / job | Exact-head evidence |
|---|---|---|
| fused-turn-runtime | 35969980537 / 107537166335 | synthetic PR checkout contains `b5a50435...`; Python 3.12.14; pytest 8.4.2; pydantic 2.13.5; 31 passed |
| P15 | 35969980601 / 107537166742 | exact-head checkout; 107 passed |
| C14 runtime | 35969980421 / 107537166134 | exact-head checkout; 84 pass progress markers, 0 fail/skip/xfail |
| C14 loop | 35969980339 / 107537165827 | exact-head checkout; 84 pass progress markers, 0 fail/skip/xfail |
| P10 AI-world | 35969980407 / 107537166234 | exact-head checkout; 69 passed |
| memory recommendation | 35969980517 / 107537166289 | exact-head checkout; 18 passed |
| world-index | 35969980325 / 107537165768 | exact-head checkout; 12 passed |
| all-dimensions | 35969980450 / 107537166216 | exact-head checkout; 4 passed |
| constitutional cognition closure | 35969980457 / 107537166157 | exact-head checkout; 91 passed; habitation subgate 92 passed |
| P16 full regression | 35969980349 / 107537165993 | exact-head checkout; `pytest -q`; Python 3.12.14; pytest 8.4.2; pydantic 2.13.5; 649 pass progress markers, 0 fail/skip/xfail; job SUCCESS |

The other exact-head workflows were also inspected at the job/step level and completed successfully without skipped test steps or swallowed job failures.

**CI verdict: 17/17 SUCCESS.**

## Full regression

P16:

- run `35969980349`
- job `107537165993`
- command: `pytest -q`
- environment: Python 3.12.14 / pytest 8.4.2 / pydantic 2.13.5
- independent raw-log progress count: 649 pass markers, 0 fail markers, 0 skip markers, 0 xfail markers
- GitHub job conclusion: SUCCESS

**Full regression verdict: PASS.**

This does not override the independent path blocker because the late-dependency C14 lineage adversarial case is absent from the current test matrix.

## Current-main compatibility

The exact candidate includes code through `ddc26aa3e705fad1ed193a6ba6146128aa2a805c`.

Independent compare `ddc26aa... → a424cb9...` reports four commits ahead and only these changed paths:

- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`

No `src/**` file changed. Therefore the review-time main advance is governance-only and does not invalidate the code-level candidate analysis.

PR #145 REST state was re-read as `mergeable=true`, `mergeable_state=clean`; `rebaseable=false` by itself is not treated as a content conflict.

## Historical Resident evidence

No historical A/B/C Resident evidence file is changed by PR #145. The 17 exact-head workflow set contains Core/test gates, not a Resident run, and no evidence hash-swap was found in the changed-file scope.

Because the candidate changes Core temporal semantics, historical Resident evidence remains historical only. Formal C15 evidence must be generated by fresh A/B/C after the eventual RC freeze.

## Serialization status

PR #157 remained OPEN / UNMERGED at the last pre-report check, so the mandatory FIX-003-first rebase/revalidation branch was not triggered for this review.

If #157 integrates before a corrected FIX-001 candidate is accepted, the governing serialization ruling still requires the corrected FIX-001 branch to rebase/merge the new live main, rerun targeted/full gates, and undergo acceptance on its new exact head.

## Final decision

- Before-state reproduced: **YES**
- Search read cut: **PASS**
- Exact historical revision selection: **PASS**
- AI-world / relation / timeline / entity / continuity / recommendation / projection cut: **PASS**
- Missing/corrupt `learned_at` fail-closed behavior: **PASS**
- Current-time control: **PASS**
- FIX-002 compatibility: **PASS**
- FIX-003 scope isolation: **PASS**
- 17/17 exact-head workflows: **PASS**
- P16 full regression: **PASS**
- C14 runtime-derived lineage temporal cut: **FAIL**
- Blocker count: **1**
- Final verdict: **ACCEPTANCE_FAIL**

PR #145 exact candidate is **not independently accepted for PM integration**.
