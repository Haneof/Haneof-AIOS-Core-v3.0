# S2 Parallelism Ruling — CORE-GAP-FIX-001 ∥ CORE-GAP-FIX-002

Date: 2026-09-24
Issued by: Core Delivery PM (integrating PM window)
Live main at ruling: `0d0d2a2` lineage (post `CORE-OPERATOR-001` integration; Core tree `src/aios_core = 7db4f72e7b3c29c74082f9984141159f8f1d6071`)
Status: ACTIVE — binding on the two S2 engineering windows and on their independent reviewers

## 1. Why this ruling exists

The existing dispatch released `CORE-GAP-FIX-001` and `CORE-GAP-FIX-002` in parallel on the stated ground that they use "different owner / branch / path, no write conflict".

The path half of that statement is **not accurate** and was verified against the current source rather than assumed:

| Task | Audited affected source | Defining symbols |
|---|---|---|
| `CORE-GAP-FIX-001` (CG-001) | `src/aios_core/runtime/turn_runtime.py`, `src/aios_core/query/search.py` | `_search_world` (line ~1129), `_inspect_world_object` (line ~1166), `_world_map_context` (~1292), `_active_turn_time` plumbing |
| `CORE-GAP-FIX-002` (CG-002) | `src/aios_core/runtime/turn_runtime.py`, `src/aios_core/runtime/cognitive_runtime.py`, `src/aios_core/wake/service.py`, `src/aios_core/review/periodic.py`, `src/aios_core/runtime/metering.py` | `run_wake` (line ~2954), `run_periodic_review` (line ~3608) |

Both tasks must write `src/aios_core/runtime/turn_runtime.py` (3,810 lines). Parallel work is therefore **same-file, different-region**, not path-disjoint.

## 2. Ruling

Parallel execution of `CORE-GAP-FIX-001` and `CORE-GAP-FIX-002` **remains authorized**, under the following binding conditions. The reason is that the two edit regions are far apart and semantically independent (a read-time visibility cut versus a provider-attempt durability state machine); serialising them would cost a full task cycle for a low textual-conflict risk. The risk is managed instead of assumed away.

### 2.1 Symbol-level ownership inside `turn_runtime.py`

- `CORE-GAP-FIX-001` owns: model-visible read paths — `_search_world`, `_inspect_world_object`, `_world_map_context`, and the read-cut helper(s) it introduces. It may read `_active_turn_time` but must not change how `run_wake` / `run_periodic_review` / `run_turn` establish execution state.
- `CORE-GAP-FIX-002` owns: background execution admission — `run_wake`, `run_periodic_review` and the durable provider-attempt state they require. It must not change the semantics of the model-visible read paths.
- Neither window may refactor, reorder, reformat or re-indent regions it does not own, and neither may perform a whole-file reformat. A diff that moves unrelated lines will be returned by the PM before review.
- If a window concludes it must change a symbol owned by the other task, it **stops and reports to the PM**. The PM then serialises the two tasks. Cross-editing is not permitted on the window's own judgement.

### 2.2 Serialised integration, not serialised development

- Development is parallel. **Integration is strictly one at a time.**
- Whichever candidate is independently accepted first is integrated first.
- The second candidate must then: rebase / merge current main, re-run its own targeted regressions **and** the full repository gate on the rebased head, and have its independent reviewer confirm the verdict still holds on that exact rebased head. A pre-rebase `ACCEPTANCE_PASS` does not carry over to a new head automatically.
- The PM never merges two Core candidates in the same integration step.

### 2.3 Out of write scope for both windows

`governance/**`, `reviews/**`, `tools/c15_preflight/**`, `tests/preflight/**`, historical evidence, fixtures, sealed futures, private Worlds, and any Resident material. Governance status writeback is performed by the PM at integration, never by the engineering author.

A Core fix must never edit the operator surface to make a Core regression pass. If a Core fix legitimately breaks an operator-surface test, the window stops and reports the conflict.

### 2.4 CORE-GAP-FIX-003 stays BLOCKED

`CORE-GAP-FIX-003` (CG-003, user-turn IN_DOUBT recovery) also writes `turn_runtime.py` and `turn_execution.py`, and its recovery state model must be consistent with the state machine that `CORE-GAP-FIX-002` establishes. It therefore starts only after FIX-002 is independently accepted **and** integrated, from live main at that time. This preserves the existing dispatch decision and now has an explicit source-level justification.

## 3. What this ruling does not do

- It does not modify the audit verdicts, the completion plan, or the task board's queue order.
- It does not authorize any Resident execution, any fixture activation, or any RC freeze.
- It does not weaken the requirement that each candidate is independently accepted by a window that did not author it.
