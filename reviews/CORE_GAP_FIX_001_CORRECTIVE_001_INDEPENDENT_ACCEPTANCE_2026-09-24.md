# CORE-GAP-FIX-001-CORRECTIVE-001 Independent Acceptance — 2026-09-24

## Verdict

**ACCEPTANCE_PASS**

PR #145 corrected exact candidate `a56f113ace3c5e01af3acb724468bc2e0fbd4e98` is independently accepted for PM integration, subject to the serialization state recorded below.

The historical blocker `CORE-GAP-FIX-001-ACCEPT-BLOCKER-001 — C14_RUNTIME_DERIVED_LINEAGE_NOT_CUTOFF` is closed on this exact head. The corrective preserves the already accepted FIX-001 temporal-read surfaces, does not regress FIX-002 background recovery semantics, does not cross into FIX-003 user-turn recovery ownership, and has green exact-head targeted/full regression evidence.

**Blocker count: 0.**

## Review identity and pinned state

- Role: Independent Core Runtime / Temporal Integrity Corrective Acceptance Reviewer.
- Review-time live `main`: `5532772a4bebbe36eb545e690b3b0efe834260b9`.
- Reviewed PR: #145 — `CORE-GAP-FIX-001: enforce runtime temporal read cut`.
- Reviewed exact corrective head: `a56f113ace3c5e01af3acb724468bc2e0fbd4e98`.
- PR #145 at final pre-report recheck: OPEN, UNMERGED, non-draft / ready for review, head unchanged; mergeability recomputation reported mergeable.
- Governance gate: `CORE-GAP-FIX-001-CORRECTIVE-001 = GATE / REVIEW_READY`.
- Historical failed head remains `b5a50435b3f9048bf94d88e9625b9e5bc2b83f42`; historical report remains `reviews/CORE_GAP_FIX_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md` with verdict `ACCEPTANCE_FAIL`.
- PR #157 at start and final pre-report recheck: OPEN / UNMERGED, corrective head `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`. The FIX-003-first rebase rule was therefore not triggered during this review.

## Required governance inputs

Read from review-time `main`:

1. `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
2. `AIOS_v3.0_CURRENT_CHECKPOINT.md`
3. `governance/AIOS_CORE_S2_POST_FIX002_PARALLELISM_RULING_2026-09-24.md`
4. `governance/prompts/CORE_GAP_FIX_001_CORRECTIVE_001_2026-09-24.md`
5. `reviews/CORE_GAP_FIX_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
6. PR #145 current body/diff

The controlling semantic requirement is unchanged: a resumed execution whose original cognition/write cut is T1 must see model-visible World/cognition state **as known at T1**, including C14 runtime-derived evidence lineage.

## Historical blocker preservation

Historical independent acceptance remains unchanged:

- reviewed head: `b5a50435b3f9048bf94d88e9625b9e5bc2b83f42`
- review PR: #161
- verdict: `ACCEPTANCE_FAIL`
- sole blocker: `CORE-GAP-FIX-001-ACCEPT-BLOCKER-001 — C14_RUNTIME_DERIVED_LINEAGE_NOT_CUTOFF`

No historical FAIL report was modified by this review.

## Corrective red-state reproduction

Corrective reproduction-only head:

`e19bc90440ed236709a58bbe6077b5a5b255c29e`

C14 workflow:
- run `35978909940`
- targeted job `107565857185`
- conclusion: **FAILURE**

Raw job logs independently re-read by this reviewer show checkout of the synthetic PR merge containing exact head `e19bc90440ed236709a58bbe6077b5a5b255c29e`, followed by two dedicated failures:

1. `test_cg001_corrective_resumed_c14_lineage_excludes_t2_dependency_and_leaf`
   - actual resumed T1 `runtime_derived_lineage` contained `obs_cg001_corrective_t2_leaf`
   - assertion failed at the intended no-future-leaf check.

2. `test_cg001_corrective_resumed_c14_bundle_lineage_excludes_t2_support`
   - actual resumed bundle-member T1 lineage contained `obs_cg001_corrective_bundle_t2_leaf`
   - assertion failed at the intended no-future-leaf check.

This is a real pre-corrective red state for the exact independent blocker, not a later-created unrelated failure.

**Old blocker reproduction verdict: PASS / faithfully reproduced.**

## Corrective implementation scope

From corrective red head `e19bc904...` to final exact head `a56f113a...`, exactly two corrective commits exist:

1. `416de08f1d0b6360f609b668aa9d97c4ae9e3568`
   - implementation: `src/aios_core/runtime/turn_runtime.py`
2. `a56f113ace3c5e01af3acb724468bc2e0fbd4e98`
   - regression strengthening: `tests/integration/test_v3_c14_cognitive_derivation_runtime.py`

The implementation adds `_derive_c14_lineage_at_cutoff(summary_ref, cutoff)`, constructs the existing `CognitionEvidencePolicy` over the existing read-only `_KnowledgeCutoffStoreView`, and routes both:
- direct C14 `runtime_derived_lineage`, and
- C14 bundle/member `runtime_derived_lineage`

through that helper using the already established `active_write_time`.

Relative to historical failed head `b5a50435...`, the branch ancestry also contains governance/review/corrective-dispatch material. That ancestry is not corrective implementation expansion. The actual corrective implementation surface is limited to the runtime file above, plus its C14 integration regression file.

## Cutoff-aware lineage path review

### Dependency enumeration

`CognitionEvidencePolicy._support_dependencies()` enumerates Dependencies through `self.store.list_payloads(object_type=DEPENDENCY)`.

Under the corrective C14 reader, `self.store` is `_KnowledgeCutoffStoreView`.

That view forcibly injects `knowledge_cutoff=Tcut` into `list_payloads`.

The underlying `SQLiteWorldStore.list_payloads(..., knowledge_cutoff=Tcut)` reconstructs the latest visible revision using rows satisfying `learned_at <= Tcut` before applying object filtering.

Therefore T2-only Dependencies are not enumerated into a resumed T1 lineage graph.

**Dependency enumeration verdict: PASS.**

### Exact leaf traversal

`CognitionEvidencePolicy._walk()` resolves each pinned ref by:
- reading immutable mechanical provenance with `object_revision_record`; and
- reading the exact payload through `self.store.get_payload(object_id, revision=...)`.

Under `_KnowledgeCutoffStoreView`, `get_payload` forcibly injects the same `knowledge_cutoff=Tcut`.

The underlying exact payload query includes both the requested revision and `learned_at <= Tcut`; a T2-only pinned leaf therefore fails closed instead of becoming model-visible.

The unwrapped `object_revision_record` call does not itself expose semantic payload content and the policy path does not use its current `latest_revision/is_latest` fields to admit lineage. Payload traversal still requires the cutoff-constrained exact payload read.

**Exact leaf traversal verdict: PASS.**

### No post-hoc filtering

The corrective does not derive against the current graph and then filter the output. The cutoff is applied at both store read primitives before dependency graph construction and before exact payload traversal.

**Cutoff-aware lineage verdict: PASS.**

## Direct C14 adversarial regression

The final candidate regression strengthens the original red test by preserving a valid pre-cut dependency-only support leaf.

At T1:
- Summary S is valid.
- ordinary T1 leaf remains present.
- T1 Dependency D1 points S to a T1 dependency-only leaf L1.
- C14 starts and its durable execution cut becomes T1.

At T2:
- new Dependency D2 is added.
- new leaf L2 is added.
- the original T1 execution is resumed.

Exact-head expectation/assertion:
- original T1 leaf remains visible;
- T1 dependency-only leaf L1 remains visible;
- T2 Dependency D2 is absent;
- T2 leaf L2 is absent.

This proves the corrective did not merely disable Dependency traversal.

The exact-head C14 runtime job is green.

**Direct C14 verdict: PASS.**

## Bundle/member C14 adversarial regression

The bundle regression applies the same construction to a targeted C14 member:
- a valid T1 dependency-only leaf is added before the execution cut;
- a T2 Dependency and T2 leaf are added after the cut;
- the bundle is resumed;
- the target member's `runtime_derived_lineage` must retain the T1 dependency leaf and exclude both T2 support objects.

Both direct and bundle paths call the same `_derive_c14_lineage_at_cutoff(..., active_write_time)` helper.

The exact-head C14 runtime/loop gates are green.

**Bundle C14 verdict: PASS.**

## Independent adversarial probe — three-level temporal ladder

This reviewer performed a new source-level/data-flow probe against the exact candidate rather than treating the author's two-level test as the independent probe.

Probe model:

- T0: S -> D0 -> L0
- T1: add D1 -> L1
- T2: add D2 -> L2
- historical cut: T1

The exact candidate's read path gives:

1. Dependency enumeration:
   - `_KnowledgeCutoffStoreView.list_payloads`
   - -> `SQLiteWorldStore.list_payloads(..., knowledge_cutoff=T1)`
   - -> historical selection only among rows satisfying `learned_at <= T1`
   - therefore D0 and D1 are eligible; D2 is not.

2. Exact leaf traversal:
   - `_KnowledgeCutoffStoreView.get_payload(exact revision)`
   - -> exact revision plus `learned_at <= T1`
   - therefore L0 and L1 are readable; L2 is unavailable/fail-closed.

3. Direct C14:
   - `run_wake` calls `_derive_c14_lineage_at_cutoff(summary_ref, active_write_time)`.

4. Bundle/member C14:
   - each member calls the same helper with the same `active_write_time`.

Result of this independent path probe:
- L0 visible: YES
- L1 visible: YES
- L2 visible: NO
- direct path obeys cut: YES
- bundle/member path obeys cut: YES

This probe is a source/data-flow adversarial verification, not a separately executed local pytest run. The execution environment available to this reviewer did not provide a local cloned repository; runtime execution evidence is therefore taken only from the independently re-read GitHub Actions logs described below.

**Independent adversarial probe verdict: PASS.**

## Prior FIX-001 surface regression

The previous independent review had already accepted these temporal surfaces, and the corrective does not change their implementation files beyond the narrowly scoped C14 lineage call site:

- Search historical cutoff
- floating historical Inspect
- latest knowable revision
- AI-world temporal cut
- policy context
- World map
- Relations
- Timeline
- Entity recall
- conversation summaries
- proactive recommendation
- ALL_DIMENSIONS
- malformed/missing `learned_at` fail closed
- current-time control

Relevant exact-head gates independently re-read as SUCCESS include:
- fused-turn-runtime `35979326656 / 107567178072` — 31 passed
- P15 `35979326726 / 107567177861` — 107 passed
- P10 AI-world `35979326679 / 107567178219` — 69 passed
- memory recommendation `35979326608 / 107567177716` — 18 passed
- world-index `35979326640 / 107567177883` — 12 passed
- ALL_DIMENSIONS `35979326757 / 107567178030` — 4 passed
- constitutional cognition `35979326725 / 107567177814` — 91 passed; associated habitation subgate 92 passed
- C09 Wake `35979326702 / 107567177934` — SUCCESS

**Prior FIX-001 surface regression verdict: PASS.**

## FIX-002 compatibility

Corrective implementation delta from `e19bc904...` to `a56f113a...` changes only:
- `src/aios_core/runtime/turn_runtime.py`
- `tests/integration/test_v3_c14_cognitive_derivation_runtime.py`

No FIX-002 background attempt store/state-machine file is modified.

The corrective call-site changes only replace uncut C14 lineage derivation with the cutoff-aware reader; they do not alter:
- background attempt identity;
- admitted / dispatching / IN_DOUBT state;
- reconciliation;
- metering;
- budget;
- Wake lifecycle;
- Periodic Review lifecycle;
- completion semantics.

Compatibility evidence:
- C09 Wake exact-head gate: SUCCESS
- P15 Periodic Review exact-head gate: 107 passed
- full P16: SUCCESS

**FIX-002 compatibility verdict: PASS.**

## FIX-003 boundary

PR #145 changed-file set remains the original FIX-001 temporal surfaces plus tests:
- continuity
- ALL_DIMENSIONS projection
- search
- proactive recommendation
- turn runtime
- FIX-001 integration tests

The corrective delta does not modify `turn_execution.py`, user-turn pre-attempt protocol code, retry authorization, user-turn reconciliation, completion recovery, or claim->attempt recovery.

PR #157 remains the owner of those semantics.

**FIX-003 scope isolation verdict: PASS.**

## Exact-head CI

Exact corrective head:
`a56f113ace3c5e01af3acb724468bc2e0fbd4e98`

GitHub returned 17 pull-request workflow runs for this commit; every run is `completed / success`.

Key gates independently enumerated/re-read:

| Gate | Run / job | Verdict |
|---|---|---|
| C14 runtime | `35979326606 / 107567178158` | SUCCESS |
| C14 loop | `35979326610 / 107567178004` | SUCCESS |
| fused-turn-runtime | `35979326656 / 107567178072` | SUCCESS / 31 passed |
| P15 | `35979326726 / 107567177861` | SUCCESS / 107 passed |
| P10 AI-world | `35979326679 / 107567178219` | SUCCESS / 69 passed |
| memory recommendation | `35979326608 / 107567177716` | SUCCESS / 18 passed |
| world-index | `35979326640 / 107567177883` | SUCCESS / 12 passed |
| ALL_DIMENSIONS | `35979326757 / 107567178030` | SUCCESS / 4 passed |
| constitutional cognition | `35979326725 / 107567177814` | SUCCESS / 91 passed (+ 92 habitation subgate) |
| C09 Wake | `35979326702 / 107567177934` | SUCCESS |
| P16 full | `35979326698 / 107567178057` | SUCCESS |

Raw C14 runtime/loop logs show the synthetic PR checkout containing exact head `a56f113a...`, Python 3.12.14, pytest 8.4.2 and pydantic 2.13.5, with full targeted progress to 100%.

**Exact-head CI verdict: 17/17 SUCCESS.**

## Full regression

P16:
- run `35979326698`
- job `107567178057`
- exact PR synthetic checkout contains `a56f113ace3c5e01af3acb724468bc2e0fbd4e98`
- Python: 3.12.14
- pytest: 8.4.2
- pydantic: 2.13.5
- command: `pytest -q`
- raw progress: 651 pass markers
- fail markers: 0
- skip markers: 0
- job conclusion: SUCCESS

**P16/full regression verdict: PASS.**

## Current-main compatibility

Corrective engineering began against `main@a6f8e585b2a8669c000f7bc7bcd0176f64ca3e6b`.

Review-time live main is `5532772a4bebbe36eb545e690b3b0efe834260b9`.

Independent compare `a6f8e585... -> 5532772a...` shows only:
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `governance/prompts/CORE_GAP_FIX_003_CORRECTIVE_001_2026-09-24.md`
- `reviews/CORE_GAP_FIX_003_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

No `src/**` Core file changed in that main advance.

Therefore the review-time main advance is governance/review-only and does not introduce a competing Core implementation change against #145.

**Current-main compatibility verdict: PASS.**

## Serialization / rebase status

At review start and final pre-report recheck:
- PR #157 = OPEN
- merged = false
- non-draft
- exact corrective head = `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`

Therefore the condition for `REBASE_REVALIDATION_REQUIRED` was not met during this acceptance.

If #157 is accepted and merged after this report but before PM integrates #145, the governing serialization ruling still requires PM to stop and rebase/merge then-live main into #145, rerun affected + full gates, produce a new exact head, and obtain fresh independent acceptance.

**Serialization verdict at review completion: NORMAL ACCEPTANCE PATH / NO REBASE TRIGGERED.**

## Final decision

- old blocker red state: **REPRODUCED**
- cutoff-aware Dependency enumeration: **PASS**
- cutoff-aware exact leaf traversal: **PASS**
- direct C14 historical lineage: **PASS**
- bundle/member C14 historical lineage: **PASS**
- T1 dependency-only support preservation: **PASS**
- prior FIX-001 surface regression: **PASS**
- FIX-002 compatibility: **PASS**
- FIX-003 scope isolation: **PASS**
- independent three-level adversarial probe: **PASS**
- exact-head workflows: **17/17 SUCCESS**
- P16 full regression: **PASS**
- current-main compatibility: **PASS**
- serialization/rebase trigger: **NOT TRIGGERED**
- blocker count: **0**
- final verdict: **ACCEPTANCE_PASS**

**PR #145 corrected exact candidate is independently accepted for PM integration.**

Do not merge from this review window.
