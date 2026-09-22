# C15-RCC Resident A Repair Decision — 2026-09-22

> Task: `C15-RCC-RES-A-REPAIR-DECISION-001`
>
> Role: Independent Resident Evidence Repair Decision Reviewer / C15 Governance PM
>
> Scope: decision only. No Core modification, no historical backfill, no Resident rerun, no Resident B run, no semantic evaluation.
>
> Final decision: **PATH A = REJECTED** / **PATH B = REQUIRED**

## 1. Reviewed main

Live reviewed `main`:

`4fbfe16ea0c500fcd30f049f0a4b6d662dbe624a`

At review start:

- `C15-RCC-RES-A-REPAIR-DECISION-001 = READY`;
- `C15-RCC-WAKE-DELIVERY-FIX-001 = DONE`;
- `C15-RCC-RES-A-001 = BLOCKED`;
- `C15-RCC-RES-B-001 = BLOCKED`.

The fixed Wake-delivery Core is already merged through PR #104.

## 2. Fixed Core anchor

- Core merge: `fd9ba5de329abb025f52de76f1ab658cdafb4897`
- Exact final Core implementation commit:
  `41f2a5da2153c55b137741fdd71983eea2a011f7`
- Completion evidence:
  `reviews/C15_RCC_WAKE_DELIVERY_FIX_001_COMPLETION_EVIDENCE_2026-09-22.md`

Relevant fixed semantics:

- real user-delivered non-conversation Wake output becomes one durable assistant-only `dim:user_ai_interaction` Observation;
- no USER Observation is fabricated;
- logical delivery identity is deterministic from subject + logical Wake id + `wake_user_delivery`;
- first exact RUNNING Wake ref remains immutable provenance;
- delivery time is the actual user-delivery execution time;
- delivery is searchable and available to later Runtime/summary/review mechanisms.

## 3. Fixed diagnostic evidence

Only the following pre-fix Resident A evidence was treated as diagnostic input:

- PR #101
- exact head:
  `bfbfa059e2ac616326eecdfe3ffa7a927bdc7ce2`

PR #101 was confirmed OPEN and UNMERGED at that exact head.

Required disposition throughout this decision:

> **OPEN / UNMERGED / PINNED / IMMUTABLE**

No file in PR #101 was modified.

## 4. Cursor 9 execution provenance

Diagnostic artifact:

`reviews/internal_habitation/c15-rcc/v1/runs/resident-a-20260922/cursor_lifecycle/cursor_0009_runtime.json`

Verified:

- logical Wake: `wake_3df17e4ced76971ebbf90c05`
- Resident-visible/runtime execution Wake ref:
  `wake_3df17e4ced76971ebbf90c05@2`
- wake source: `watch_match`
- attention class: `interrupt`
- Step0 delivery allowed: `true`
- runtime termination: `responded`
- user-facing delivery response: non-empty
- final completed Wake:
  `wake_3df17e4ced76971ebbf90c05@3`
- delivery execution time:
  `2026-11-04T22:17:00Z`

Therefore the only correct fixed-Core historical provenance would be the RUNNING execution ref:

`wake_3df17e4ced76971ebbf90c05@2`

The completed `@3` ref is not a substitute for original execution provenance.

Fixed-Core deterministic delivery Observation identity for this logical Wake is:

`obs_wake_ai_2f90e34a8f88bd517552bfcf@1`

## 5. Cursor 11 execution provenance

Diagnostic artifact:

`cursor_lifecycle/cursor_0011_runtime.json`

Verified:

- logical Wake: `wake_c9ebc3c1cf7b2a3f1b9b953a`
- Resident-visible/runtime execution Wake ref:
  `wake_c9ebc3c1cf7b2a3f1b9b953a@2`
- wake source: `watch_match`
- attention class: `interrupt`
- Step0 delivery allowed: `true`
- runtime termination: `responded`
- user-facing delivery response: non-empty
- final completed Wake:
  `wake_c9ebc3c1cf7b2a3f1b9b953a@3`
- delivery execution time:
  `2026-11-04T23:02:00Z`

Therefore the correct historical provenance would be:

`wake_c9ebc3c1cf7b2a3f1b9b953a@2`

Fixed-Core deterministic delivery Observation identity:

`obs_wake_ai_dee8e0cd2712ed78f3bf05da@1`

## 6. Mechanical scratch counterfactual procedure

No model was run.

No canonical PR #101 bytes were modified.

The counterfactual was computed mechanically from:

1. the immutable PR #101 `sum0011.json` request;
2. the two immutable cursor runtime artifacts;
3. the exact fixed-Core `ConversationIngestor.commit_assistant_delivery(...)` identity/provenance rules;
4. the exact current `DimensionSummaryService.prepare(...)` source-selection rules.

For the scratch calculation, the two missing fixed-Core delivery Observations were instantiated with:

- exact original assistant text;
- subject `user_1`;
- `role=assistant`;
- `dimension=dim:user_ai_interaction`;
- `source_kind=user_ai_interaction`;
- original user-delivery times `22:17Z` and `23:02Z`;
- correct RUNNING provenance refs `@2`;
- deterministic fixed-Core object ids shown above.

Then the exact day-summary selector was applied mechanically:

- subject = `user_1`;
- dimension = `dim:user_ai_interaction`;
- time range = `2026-11-04T00:00:00Z` through `2026-11-04T23:59:59.999999Z`;
- ordinary Observation objects are eligible;
- results are ordered by occurred time, then object id.

No semantic text was synthesized for the corrected summary.

## 7. Original `sum0011` source set

Artifact:

`summary_requests/sum0011.json`

Verified:

- kind = `dimension_summary`
- dimension = `dim:user_ai_interaction`
- granularity = `day`
- window = `2026-11-04T00:00:00Z` → `2026-11-04T23:59:59.999999Z`
- executed during Phase A freeze processing at cursor 13
- Resident-authored semantic summary was produced
- original source count = **6**

Exact original refs, in summary order:

1. `obs_conv_ai_fff46dab8642ef4767cc1458@1` — 21:42Z assistant
2. `obs_conv_user_24843998506b575cc3f98915@1` — 21:42Z user
3. `obs_conv_ai_718dc834318477eb0dbff23f@1` — 22:24Z assistant
4. `obs_conv_user_1b929906e9a92dce0e19ef96@1` — 22:24Z user
5. `obs_conv_ai_b9e2ed5d3583b8456b40b6fb@1` — 23:07Z assistant
6. `obs_conv_user_498b81effac90ab9381a2533@1` — 23:07Z user

The Resident therefore summarized a six-source history.

## 8. Corrected-world `sum0011` source set

Both fixed-Core Wake-delivery facts are ordinary `dim:user_ai_interaction` Observations and both occurred inside the same day-summary window.

Mechanical corrected source count = **8**.

Exact corrected refs, in selector order:

1. `obs_conv_ai_fff46dab8642ef4767cc1458@1` — 21:42Z
2. `obs_conv_user_24843998506b575cc3f98915@1` — 21:42Z
3. `obs_wake_ai_2f90e34a8f88bd517552bfcf@1` — 22:17Z — cursor 9 delivered Wake output
4. `obs_conv_ai_718dc834318477eb0dbff23f@1` — 22:24Z
5. `obs_conv_user_1b929906e9a92dce0e19ef96@1` — 22:24Z
6. `obs_wake_ai_dee8e0cd2712ed78f3bf05da@1` — 23:02Z — cursor 11 delivered Wake output
7. `obs_conv_ai_b9e2ed5d3583b8456b40b6fb@1` — 23:07Z
8. `obs_conv_user_498b81effac90ab9381a2533@1` — 23:07Z

Therefore:

> **original source set = 6**
>
> **corrected-world source set = 8**

This conclusion follows directly from fixed-Core persistence semantics plus the deterministic summary selector. It does not depend on a semantic interpretation of either message.

## 9. Downstream model-visible differences

The source-set difference is not isolated.

### 9.1 Resident-authored summary input is different

At cursor 13 the original Resident received a six-source `DimensionSummaryInput` and authored the content of:

`sum_bbd1e5bef32dcaf8f73ccf20@1`

Current Core persists a dimension Summary with exact `source_refs` and creates dependencies for every prepared source.

Under the corrected history, the same summary window would reach the Resident with eight sources, including both proactive assistant deliveries.

The old semantic summary text cannot be mechanically declared equal to the text that the Resident would have authored from the eight-source request.

Using the old six-source semantic output after adding two source facts would therefore preserve a semantic result produced from an incomplete history.

### 9.2 Summary lineage / cognitive-derivation opportunity changes

The original cursor-13 cognition reconciliation sees:

`sum_bbd1e5bef32dcaf8f73ccf20@1`

with six interaction leaf refs and schedules a Cognitive Derivation Wake from that summary.

A corrected summary would have eight source refs/dependencies and a model-authored content generated from a different request.

Therefore the summary object provenance and the cognitive-derivation input lineage are not historically equivalent.

No prediction about what cognition the Resident would form is needed. The model-visible input already differs.

### 9.3 Periodic Review anchors also change mechanically

Cursor 13 performed a real Periodic Review with window:

`2026-11-04T21:30:00Z` → `2026-11-06T19:10:00Z`

The original request contains:

- 18 total anchors;
- 9 Observation anchors.

The Periodic Review scheduler mechanically includes reviewable Observations whose `recorded_at` is inside the window, with an Observation per-type limit of 20 and total limit of 80.

Both fixed Wake-delivery Observations:

- are Observation objects;
- are recorded at 22:17Z / 23:02Z;
- fall inside that review window;
- do not hit the per-type or total limit.

Therefore the corrected review request necessarily contains at least the two additional exact refs:

- `obs_wake_ai_2f90e34a8f88bd517552bfcf@1`
- `obs_wake_ai_dee8e0cd2712ed78f3bf05da@1`

Mechanically:

- Observation anchors: **9 → 11**
- total anchors: **18 → 20**

The review Wake identity itself is computed from the selected anchor refs, so its deterministic identity would also differ.

Thus an actual Resident-visible Periodic Review input in Phase A is different even before considering any possible summary-content difference.

### 9.4 Search / projection universe changes

The two fixed delivery Observations are searchable durable interaction facts.

Consequently a corrected World also changes the legal candidate universe for:

- explicit World search;
- interaction-dimension timeline/search;
- all-dimensions projection including `dim:user_ai_interaction`;
- future summary selection.

The assistant-dialogue anti-self-proof policy does not erase these interaction facts from the World or from dimension summarization/review input.

## 10. Historical-equivalence verdict

Strict historical equivalence is **not provable and is mechanically disproven**.

The corrected Core would have changed actual Phase A Resident-visible inputs before freeze:

1. `sum0011` day-summary sources: 6 → 8;
2. that model-authored Summary's source refs/dependency graph;
3. its downstream cognitive-derivation input lineage/opportunity;
4. cursor-13 Periodic Review anchors: 18 → 20 total, 9 → 11 Observations;
5. deterministic review Wake identity;
6. legal search/projection universe.

Additionally, had the two interaction commits existed at their historical execution points, later World revision numbers would also be shifted relative to the pre-fix run.

A post-hoc repair cannot retroactively recreate the Resident semantic execution that should have occurred from those changed inputs.

## 11. Path A verdict

> **PATH A = REJECTED**

Reason:

> Corrected Core would have changed the Resident-visible `dim:user_ai_interaction` day-summary source set during Phase A itself. Therefore post-hoc persistence cannot reproduce the semantic execution that should have occurred. A purely mechanical repair would preserve old semantic outputs from an incomplete input history and is not historical-equivalent.

The fact that the two missing Observations can be deterministically constructed is necessary but not sufficient for Path A.

The stricter no-source-set-change / no-Runtime-input-change requirement fails.

No `C15-RCC-RES-A-HISTORICAL-REPAIR-001` task is authorized.

## 12. Path B verdict

> **PATH B = REQUIRED**

A new Resident A run must execute the same frozen Phase A fixture on the fixed Core from:

- a fresh private World;
- a fresh Resident session/window;
- no old Resident A transcript;
- no PR #101 semantic decisions;
- no copied old Claims;
- no requirement to reproduce old answers/cognition.

The new Resident may legitimately form different cognition, use different capabilities, choose silence, or assign different confidence. The purpose is to execute the same sealed reality against the corrected durable-world mechanics.

## 13. Next task decision

Create:

`C15-RCC-RES-A-RERUN-001 = READY`

Purpose:

> On the fixed Core, execute the frozen C15 Phase A fixture cursor 1..13 from a fresh private World with a new real Resident A window.

Keep:

- `C15-RCC-RES-A-001 = BLOCKED / SUPERSEDED`;
- `C15-RCC-RES-B-001 = BLOCKED`;
- `C15-RCC-RES-C-001 = BLOCKED`;
- `C15-RCC-EVAL-001 = BLOCKED`;
- `C15-RCC-CLOSE-001 = BLOCKED`.

Resident B remains prohibited until the new Resident A evidence is independently accepted.

## 14. PR #101 final disposition

PR #101 remains permanently valuable as:

> **PRE-FIX DIAGNOSTIC / SUPERSEDED RESIDENT A RUN**

It proves that a real Resident habitation run exposed a durable Wake-delivery persistence defect.

It must remain:

- OPEN;
- UNMERGED;
- PINNED;
- exact head unchanged:
  `bfbfa059e2ac616326eecdfe3ffa7a927bdc7ce2`.

It is no longer an RCC canonical A World candidate.

## 15. No-mutation statement

This decision window:

- modified no `src/aios_core/**`;
- modified no fixture;
- modified no PR #101 evidence;
- performed no historical backfill;
- created no repaired private World artifact;
- ran no Resident A;
- ran no Resident B;
- wrote no cognition;
- performed no R1–R9 semantic evaluation.

Only governance decision artifacts are eligible for merge.
