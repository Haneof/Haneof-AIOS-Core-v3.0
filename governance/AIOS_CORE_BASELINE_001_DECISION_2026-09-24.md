# CORE-BASELINE-001 Baseline Decision — 2026-09-24

Task: `CORE-BASELINE-001`  
Role: Release PM / Architect  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`

## 1. Reviewed live state

- PR #128 was reviewed as a five-file governance-only change and merged normally. Actual merge / live main at this decision: `33436565c109c2c47cf2c3150084fcce22810124`.
- Live main Core tree: `src/aios_core = 7db4f72e7b3c29c74082f9984141159f8f1d6071`.
- Live main tests tree: `a788fd702ba5a42da52847e5d4d2be21f97e56ea`.
- PR #127: merged; head `ba3ed05ec751f80b890aed2dfc2be12ec80d597d`; merge `6924d8b50cf08eb632f9cfa513a3cc49faad0c72`. Its Core tree is the same `7db4f72e...`.
- PR #126: OPEN / DRAFT / UNMERGED; exact head `8e31deca02a5062d7bb9ffe6dd840abbaaf6970e`. Its `src/aios_core` tree is also `7db4f72e...`; therefore its Core repair is already represented on main and MUST NOT be merged again as a Core implementation. Its tests/tools/CI deltas remain reviewable references only.
- PR #125: OPEN / UNMERGED; exact head `b14b5d84b6a4c843dc7dc38cde51f08a92fac86b`; 41 commits / 64 changed files. Its Core tree is still historical `eed27d58041dbaf2ceb0a65c1305bb332aef082e`, so the PR cannot be merged wholesale onto current main.
- PR #125 exact-head CI:
  - `c15-operator-preflight` run `35952205324`, job `107482934617`: **128 passed / 3 failed**.
  - `p16-convergence-gate` run `35952205318`, job `107482934372`: same three failures.
  - failures:
    1. `test_clock_reuses_existing_scheduler_at_intermediate_deadline_without_future_input` — no 24h periodic review was emitted;
    2. `test_old_wake_cannot_see_future_input` — an old wake observed `SYNTHETIC event 1` from the future;
    3. `test_budget_deferral_not_forced` — expected pre-ingest deferred wake was absent.
- PR #125 head commit states that B14 was released/acked and a dimension-summary request was emitted. This is retained as a WIP execution statement only; it is NOT accepted Resident evidence and does not make B complete.
- PR #125 `PROTOCOL_REVISION.md` records the owner-selected protocol: **rules constraints + process audit**. Hard isolation is not a start prerequisite for this round, but missing audit records cannot be used to claim absence of contamination, and no result may be described as a hard-isolation experiment.
- Canonical A evidence remains PR #117 @ `3e51f728d7959048b75fea01d405bc837b0e8185`, OPEN / UNMERGED / PINNED, accepted for the historical frozen Core `bcd6bf353126318f9a97076b52ec1740d43f35a4`.
- Old B candidate remains PR #121 @ `b6e5ac939bef83615292bcf9b9099d76737d82b0`, OPEN / UNMERGED / PINNED / NON-CANONICAL and previously rejected as execution evidence.

## 2. Baseline separation

| Class | Exact baseline | Decision |
|---|---|---|
| Development main | `33436565c109c2c47cf2c3150084fcce22810124`; Core tree `7db4f72e...` | Sole forward engineering baseline |
| Historical accepted A | PR #117 @ `3e51f728...`; frozen Core `bcd6bf3...` | Historical accepted evidence only |
| Historical failed B | PR #121 @ `b6e5ac9...` | Preserve immutable / non-canonical; never initialize C from it |
| Operator WIP source | PR #125 @ `b14b5d84...`; old Core tree `eed27d58...` | Harvest only reviewed operator/test assets; do not merge whole PR |
| Duplicate Core / CI reference | PR #126 @ `8e31deca...`; Core tree `7db4f72e...` | No Core re-integration; inspect test/CI deltas only when useful |
| Future experiment baseline | Not yet frozen | Created only by `CORE-RC-FREEZE-001` after S2 acceptance |

## 3. Change-impact ruling

The ten repairs already integrated through #127 modify dependency propagation, Event/Policy behavior, search/index handling, revision propagation, turn admission/storage, dimension-summary preparation and scheduler behavior. These mechanisms can change Resident-visible context, due work, summary inputs, revision lineage or admissible turn behavior.

Therefore:

1. PR #117 A remains valid as historical evidence for its frozen Core.
2. It MUST NOT be relabeled or hash-swapped into the new Core experiment.
3. A **fresh A is required for the new release candidate**, but it MUST NOT run now. It is scheduled only after `CORE-RC-FREEZE-001`, so later S1/S2 Core changes do not force repeated A reruns.
4. Old B #121 remains historical failed evidence and is not reusable.
5. No Resident A/B/C is authorized by this S0 decision.

## 4. Fixed integration route

1. All forward engineering starts from live `main`, never from PR #125's old Core.
2. `CORE-OPERATOR-001` ports only the necessary operator bridge / clock / restart / transport / audit tooling and its tests from PR #125 exact head onto a fresh branch from current main.
3. The three exact #125 failures MUST first be reproduced on that current-main-based candidate before any fix.
4. `CORE-OPERATOR-001` does not modify `src/aios_core/**`. If a reproduced failure is proven to require Core semantic code changes, the engineer stops and returns a candidate `CORE-GAP-FIX-NNN` finding instead of mixing scopes.
5. `CORE-GAP-AUDIT-001` runs independently and read-only against current main. It does not fix code.
6. Only audit-confirmed or newly reproduced gaps create `CORE-GAP-FIX-NNN` tasks.
7. Headless / recovery / scale work follows accepted audit results. After all S2 exits are accepted, `CORE-RC-FREEZE-001` freezes the exact candidate and only then may the new C15 fresh A → fresh B → C chain begin.
8. PR #117, #121 and PR #125 historical/WIP evidence remain untouched. PR #126 is not merged as a duplicate Core route.

## 5. S0 exit and newly released work

`CORE-BASELINE-001 = DONE`.

The following two tasks are dependency-clean and may proceed in parallel because their write scopes do not conflict:

- `CORE-OPERATOR-001 = READY / NOT_STARTED` — Test Infrastructure Engineer; prompt: `governance/prompts/CORE_OPERATOR_001_2026-09-24.md`.
- `CORE-GAP-AUDIT-001 = READY / NOT_STARTED` — Independent Core Architect; prompt: `governance/prompts/CORE_GAP_AUDIT_001_2026-09-24.md`.

No subordinate execution is claimed by this document. A task becomes IN_PROGRESS only when a separate execution window actually starts it.
