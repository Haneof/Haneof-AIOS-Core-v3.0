# AUDIT-001 — Issue #30 Current-Main Evidence Matrix

> Audit task: `AUDIT-001`  
> Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
> Audited exact main SHA: `e9862103a753be026edf1745c6a5d07fa56c0cf4`  
> Audit date: 2026-09-21  
> Scope: T34 / #34, T36 / #36, T28 / #28, T35 / #35, T33 / #33, plus the corresponding historical triage evidence in PR #37.  
> Constraint: audit only. No Core/runtime/test implementation changes are part of this task.

## Audit method

This audit does not treat an old open Issue, an old green workflow, or PR #37 as proof of current status. For each finding it:

1. froze the current `main` SHA;
2. inspected the current implementation at that exact SHA;
3. inspected current tests/capability surfaces that cover or fail to cover the path;
4. re-read the original issue/reproduction evidence;
5. where a historical deterministic reproduction existed, checked its workflow head/log and compared the relevant implementation against current `main`;
6. issued exactly one current-main verdict.

PR #37 is still open, with head `058bada3893ce262107796fbb208762047764a5f`, base `b1576a9c4f482e89b5bdbb87b1581fd9d0e40e94`, and one changed file (`reviews/internal_habitation/CENTRAL_TRIAGE_2026-09-21.md`). It remains historical triage context, not current-main truth. Its policy that findings must be independently revalidated on current `main` is followed here.

## Evidence matrix

| Finding | Verdict | Current source path / evidence | Current test or reproduction evidence | Historical evidence still applicable? | Follow-up construction |
|---|---|---|---|---|---|
| T34 / #34 — Action cancel → authorize parent Task race | **STILL_OPEN** | `src/aios_core/execution/service.py` blob `3bbb1362af254c9e0a43234943c3069211077584`. In `authorize_action()`, current Action revision/status and authorization refs are checked, then the external authorizer is called; the current parent `task_ref` / Task state is not revalidated before the Action is advanced to SUBMITTED. | Historical deterministic repro run `35524926833`, job `106115314890`, head `6cf204f5b64bbf9f7bfefc35e238816faba2f141` produced `PARENT_TASK_STATE=cancelled`, `ACTION_BEFORE=proposed`, `ACTION_AFTER=submitted`, `REPRO_RESULT=STALE_ACTION_AUTHORIZED`. The repro head's `execution/service.py` blob is exactly the same `3bbb1362...` blob as current main. Current `tests/integration/test_v3_execution_world.py` covers allow/deny and duplicate dispatch, but has no cancel→authorize regression. | **Yes.** This is stronger than merely carrying an old issue forward: the exact implementation file that reproduced the defect is byte-identical on audited main. | Yes — `T34-EXEC-001`. |
| T36 / #36 — structured Observation scalar retrieval | **STILL_OPEN** | `src/aios_core/query/search.py` blob `5e6458b6b7878f9bc422d0569dfb7a9c5f27af18`. `_TEXT_FIELDS["observation"]` includes `value`, but `_index_row()` only appends a field when `isinstance(value, str)`; dict/list/number/bool values still contribute no haystack text or content tokens. | Historical deterministic repro run `35526364073`, job `106119110133`, head `8b57fe83da254b34c5647d42653d614f4daa4f00` produced `REPRO_RESULT=STRUCTURED_OBSERVATION_VALUE_NOT_SEARCHABLE`, empty structured haystack/excerpt, and hits only for the text control. The whole file later changed (`ca8ee53e...` → `5e6458b6...`), but the audited `_index_row()` block that caused the failure is unchanged. Current `tests/integration/test_m0_prime_store_delta_and_search.py` constructs Observation search fixtures with string `value`; it has no nested structured-scalar regression. | **Yes, for the defect mechanism.** Later unrelated search-file edits do not alter the failing string-only projection block. | Yes — `T36-SEARCH-001`. |
| T28 / #28 — assistant raw dialogue may be proactively recommended as user/world fact | **STILL_OPEN** | `src/aios_core/recommendation/proactive.py` blob `26a6b20f03a885b17cc5e6b22d64dfe492bceca6`, identical to baseline `b1576a9...`. The main lexical candidate loop filters assistant dialogue only inside `if antecedent_fallback ...`; ordinary proactive recommendation has no equivalent assistant-role exclusion. `src/aios_core/runtime/turn_runtime.py` passes `antecedent_fallback=topic_state.antecedent_recall_needed`, so normal history-driven recommendation and antecedent recovery are separate paths. | Current tests prove the narrower antecedent filter but not the ordinary path: `tests/integration/test_p16_cross_session_antecedent_recall.py` asserts assistant dialogue is absent during antecedent fallback, while `tests/integration/test_v3_memory_recommendation.py` seeds assistant observations without asserting they are excluded from ordinary proactive cards. For a history-cued but non-deictic query, the audited code can enter the ordinary lexical path with `antecedent_fallback=False`, leaving assistant raw dialogue eligible. | **Yes.** The implicated recommender blob is unchanged from the historical baseline, and current tests only protect the antecedent branch described by Issue #30, not ordinary recommendation. PR #37's broad proactive/deictic triage remains context only. | Yes — `T28-REC-001`. |
| T35 / #35 — non-Action Task completion credential semantics | **STILL_OPEN** | `src/aios_core/execution/service.py` blob `3bbb1362...`. `TaskTransitionRequest` still rejects every COMPLETED/FAILED transition without `outcome_refs`, and `transition_task()` still requires every outcome ref to point to `ObjectType.OUTCOME`. The Resident capability catalog in `src/aios_core/runtime/turn_runtime.py` exposes `transition_task` and `propose_action` but no generic `create_outcome` / `record_outcome` capability. | Current `tests/integration/test_v3_execution_world.py::test_task_cannot_claim_completion_without_outcome` explicitly asserts the universal requirement. Independent live reproduction run `35527419451`, head `05c1899cc64d01e2eb395e895cdb7985d79e0515`, job `106121904943`, records `CAPABILITY_EXECUTION_ERROR` with `COMPLETED/FAILED task transition requires outcome_refs` for a verification Task grounded by real user + photo Observations. That run uses the exact same current `execution/service.py` blob. | **Yes.** The mechanism and exact service blob remain unchanged. The constitution still contains a semantic tension: it forbids self-declared completion, says real-execution Tasks follow Action→Outcome→Task, yet implementation applies typed Outcome universally. That requires a dedicated semantic ruling before implementation. | Yes — first `T35-RULE-001`; only after that ruling, `T35-IMPL-001` if implementation is required. |
| T33 / #33 — cross-session recall / antecedent false trigger | **STILL_OPEN** | `src/aios_core/recommendation/topic_state.py` blob `863106418d8b9190df22d3a537f6f23a27bb8f32`, identical to `b1576a9...`. `_CONTINUATION_CUES` still contains bare `"这个"`. `resolve()` uses substring matching; with no previous same-session user turn, a continuation cue sets `antecedent_recall_needed=True`, which also sets `history_may_help=True`. | Deterministic current-code trace for the historical self-contained form: input `先帮我记住这个偏好。`, `recent_turns=()` ⇒ `previous=None`; `"这个"` is found ⇒ `continuation_cue=True`; no same-session antecedent ⇒ `antecedent_recall_needed=True`; therefore `history_may_help=True`. Current `tests/integration/test_p16_cross_session_antecedent_recall.py` has a positive deictic case (`那天...`) and a concrete no-history case, but no self-contained `这个` contrast. | **Yes.** The exact topic-state blob is unchanged from the issue baseline. The old report is therefore still mechanically applicable to this cue, while repair must remain generic and must not become a benchmark phrase blacklist. | Yes — `T33-RECALL-001`. |

## Current-main audit conclusion

All five historical findings are still present on audited `main@e9862103a753be026edf1745c6a5d07fa56c0cf4`.

- T34 / #34: **STILL_OPEN**
- T36 / #36: **STILL_OPEN**
- T28 / #28: **STILL_OPEN**
- T35 / #35: **STILL_OPEN**
- T33 / #33: **STILL_OPEN**

No finding is classified `ALREADY_FIXED` or `NOT_REPRODUCED` on this audited SHA.

## Governance consequences

- Activate `T34-EXEC-001`.
- Activate `T36-SEARCH-001`.
- Activate `T28-REC-001`.
- Activate semantic-only `T35-RULE-001`; keep `T35-IMPL-001` blocked until the rule is complete and T34 integration ordering is satisfied.
- Activate `T33-RECALL-001`.
- Keep `P16-TRIAGE-001` blocked until all activated findings are resolved.
- Do not merge PR #37 as current truth merely because it exists; its central triage must later be rebased/reconciled by `P16-TRIAGE-001`.

No Core fix was performed by AUDIT-001.
