# CORE-GAP-FIX-001-CORRECTIVE-001

Repository: Haneof/Haneof-AIOS-Core-v3.0

Role: Core Runtime / Temporal Integrity Engineer.

Continue the existing:
- PR #145
- branch `core-gap-fix-001-temporal-read-cut-20260924-r2`

Do not create a competing PR. Do not restart CORE-GAP-FIX-001 from scratch.

## Trigger

Independent acceptance PR #161 reviewed exact candidate
`b5a50435b3f9048bf94d88e9625b9e5bc2b83f42`
and returned ACCEPTANCE_FAIL with exactly one blocker:

`CORE-GAP-FIX-001-ACCEPT-BLOCKER-001 — C14_RUNTIME_DERIVED_LINEAGE_NOT_CUTOFF`.

Historical acceptance report:
`reviews/CORE_GAP_FIX_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`.

## Required start

1. Fetch current live main.
2. Read:
   - governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md
   - AIOS_v3.0_CURRENT_CHECKPOINT.md
   - governance/AIOS_CORE_S2_POST_FIX002_PARALLELISM_RULING_2026-09-24.md
   - governance/prompts/CORE_GAP_FIX_001_RESUME_AFTER_FIX_002_2026-09-24.md
   - reviews/CORE_GAP_FIX_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md
3. Confirm `CORE-GAP-FIX-001-CORRECTIVE-001 = READY`.
4. Reuse the existing #145 branch and preserve all prior reproduction / CI evidence.

## Only blocker to fix

A resumed C14 execution pinned to T1 can still compute
`runtime_derived_lineage` using the current uncut Dependency graph.

The leaking path identified by independent review is:

`run_wake`
-> `CognitiveDerivationScheduler.derive_lineage`
-> `CognitionEvidencePolicy.derive_lineage_for_refs`
-> `_support_dependencies / _walk`
-> `DerivedLineageView.audit_payload`
-> model-visible C14 cockpit `runtime_derived_lineage`.

A Dependency or leaf learned only at T2 must not enter a resumed T1 cockpit.

## Minimal corrective requirement

Make C14 runtime lineage derivation honor the same active temporal knowledge cut already established by FIX-001.

The corrected mechanism must ensure BOTH:
- Dependency enumeration is restricted to objects knowable at Tcut;
- exact object traversal during lineage walking is restricted to the latest knowable revision at Tcut / fails closed beyond Tcut.

Acceptable designs include:
- constructing the derivation/evidence reader over the existing read-only cutoff store view; or
- threading an explicit `knowledge_cutoff` / equivalent through lineage derivation.

Do not create a second dependency graph, second World, or second lineage truth store.

## Required regression

Add a dedicated regression for the independent blocker:

1. Summary S@1 is valid at T1.
2. C14 execution starts at T1 and remains resumable.
3. At T2 add late fact L@1.
4. At T2 add valid `summary_uses_source` Dependency D@1 from S@1 to L@1.
5. Resume the C14 execution with historical Tcut=T1.
6. Assert D@1 and L@1 do NOT appear in model-visible `runtime_derived_lineage`.
7. Assert pre-T1 valid dependencies still remain visible.
8. Also cover the C14 bundle/member path if it uses the same lineage construction.

## Preserve all already-passing semantics

Do not redesign or weaken:
- search_world temporal cutoff;
- exact historical revision selection;
- AI-world / policy / world-map cutoff;
- relation / timeline / entity / summary / recommendation / ALL_DIMENSIONS cutoff;
- missing/corrupt learned_at fail-closed behavior;
- current-time control;
- FIX-002 background attempt identity/state/reconciliation/metering/budget/lifecycle/completion;
- FIX-003 user-turn recovery semantics.

Do not modify historical Resident evidence, fixtures, operator, UI or hardware.

## Serialization with FIX-003

PR #157 is independently being reviewed in parallel.

If PR #157 becomes ACCEPTANCE_PASS and is integrated before this corrective reaches final REVIEW_READY:
- merge/rebase then-live main into #145;
- resolve only necessary conflicts;
- rerun corrective targeted gates + all affected FIX-001 gates + full P16;
- the resulting new exact head must receive a fresh independent acceptance.

No old acceptance result may be carried across a post-#157 rebased head.

If #157 is still unmerged at final handoff, normal #145 corrective acceptance may proceed on the new exact head.

## Verification before handoff

At minimum rerun:
- dedicated late-dependency C14 regression;
- C14 runtime;
- C14 loop;
- fused-turn-runtime;
- P15 periodic review;
- P10 AI-world;
- memory recommendation;
- world-index;
- ALL_DIMENSIONS;
- constitutional cognition closure;
- C09 Wake;
- full P16 `pytest -q`.

Preserve and report exact run/job IDs.

## Deliverable

Update existing PR #145 body with:
- failed reviewed head `b5a50435...`;
- blocker ID;
- exact corrective implementation;
- late-dependency regression evidence;
- final live-main compatibility / #157 serialization state;
- new exact candidate head;
- targeted/full CI.

Set author state REVIEW_READY only.

Do not self-accept.
Do not merge.
Do not modify task board/checkpoint from the engineering window.
