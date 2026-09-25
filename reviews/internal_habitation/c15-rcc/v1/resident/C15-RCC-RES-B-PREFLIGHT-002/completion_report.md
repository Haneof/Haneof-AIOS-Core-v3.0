# C15-RCC-RES-B-PREFLIGHT-002 — Completion Report (CORRECTIVE-011 implementation)

Date: 2026-09-25  
Task: `C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-011`  
Role: Release / Test Infrastructure Engineer

## Current state: **IMPLEMENTATION_READY / FRESH_E2E_REQUIRED**

Independent Acceptance review `5316831911` failed exact candidate
`a8576e8b60c400845ceeecc6b7145202e4d1f617` with three blockers. PM adjudication
`5316852416` substantiated the same three and released CORRECTIVE-011.

The implementation changes for all three blockers are present in this corrective candidate, but the old
committed `144/144` evidence belongs to the parent candidate and MUST NOT be reused as fresh evidence.
A new exact frozen-environment run of `isolation/probe_e2e.sh` is still required before this report may
be changed to `REVIEW_READY / AWAITING_PM_RE-REVIEW`.

## IA-BLK-001 — production usage no synthesis

`harness/bridged_model_handler.py::_reply_to_directive_production()` no longer derives a total from
input/output counts.

Frozen rule:

- complete `20/22/42` → preserve `42/20/22`;
- missing `total_tokens` with input/output present → `usage=None`;
- input-only or output-only without total → `usage=None`;
- total-only → preserve the reported total, optional fields remain `None`;
- valid total + one optional component → preserve only provider-reported values;
- `total < input + output` → `usage=None`;
- negative/bool/string token values → `usage=None`;
- `provider/model/request_id` provenance remains available independently of usage.

The adapter SHA-256 after this correction is
`da74eb97a6d35b535f298f52a72a32fc35dfbd1fca1ec4585aa1d7c090e92911`.

`probe_e2e.sh` adds nine counted regressions and emits
`RAW_USAGE_NO_SYNTHESIS_PASS` only after all data-shape cases and AST source inspection pass.

## IA-BLK-002 — strict canonical declaration checker

New `checks/canonical_pin_checker.py` is the single checker implementation used by both the real pin
gate and the mutation-red self-test.

For each of:

- `operator_manifest.md`
- `source_pins_and_digests.md`
- `procedure/b_startup_procedure.md`

it collects authoritative World / Index / Release declarations, including bare `World:` / `Index:` /
`Release:` labels, lineage labels, and `private_world.sqlite` / `world_index.sqlite` /
`release_state.json` declaration lines. Every authoritative occurrence must equal the canonical pin;
a correct occurrence elsewhere cannot mask a wrong declaration.

Self-test matrix: 9 one-hex mutations (3 pins × 3 docs), one duplicate wrong World declaration, and one
missing-all-World declaration. All 11 must red before
`CANONICAL_PIN_MUTATION_RED_PASS` is emitted.

Canonical values remain:

- World: `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa`
- Index: `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1`
- Release: `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8`

## IA-BLK-003 — one active lifecycle

`procedure/b_startup_procedure.md §7` is explicitly the single authoritative Phase-B cursor lifecycle.
`procedure/per_cursor_interaction.md` is now an exact operational mirror/reference and no longer
defines receipt-before-current-event ordering.

Both documents carry the same machine-readable sequence:

1. REVEAL
2. INSTALL_CURRENT_EVENT
3. PERSIST_PROJECTION_EVIDENCE
4. CREATE_BINDING_RECEIPT
5. VERIFY_BINDING
6. DERIVE_OCCURRED_AT
7. INGEST
8. MODEL_WORK
9. FINISH_CURSOR_MODEL_WORK
10. DURABLE_ACK
11. CLEAR_BINDING
12. NEXT_REVEAL

New `checks/runbook_lifecycle_checker.py` parses both documents and requires the exact same sequence.
Its self-test reintroduces the historical receipt-before-current-event ordering, removes projection
evidence, and duplicates projection evidence; every mutation must red. Required marker:
`RUNBOOK_CROSS_DOCUMENT_ORDER_PASS`.

## Fresh gate target

`isolation/probe_e2e.sh` has been recomputed to:

- `EXPECTED_CHECKS=156`
- required `RAW_USAGE_NO_SYNTHESIS_PASS`
- required `CANONICAL_PIN_CONSISTENCY_PASS`
- required `CANONICAL_PIN_MUTATION_RED_PASS`
- required `CANONICAL_RUNBOOK_ORDER_PASS`
- required `RUNBOOK_CROSS_DOCUMENT_ORDER_PASS`
- required `RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS`
- final marker `CORRECTIVE_011_E2E_PASS`

The success condition is exactly `ALL_CHECKS=156/156 FAILURES=0`.

## Execution evidence status

The previous `isolation/e2e_probe_output.txt` and FIXUP-001 raw log are historical evidence for the
parent candidate only. They are not CORRECTIVE-011 evidence.

This corrective session could execute targeted no-synthesis/checker mutation regressions, but its local
runtime is Python 3.13.5 and the container denies `unshare(CLONE_NEWNS|CLONE_NEWPID|CLONE_NEWNET)`
with `Operation not permitted`. The frozen probe requires Python 3.11.2 plus namespace privileges.
Therefore no `CORRECTIVE_011_E2E_PASS` is claimed here and no synthetic/local targeted log is
misrepresented as the frozen E2E.

## Invariants preserved

- frozen software remains `773876f92d5f8e53422f8f5a68cc651953d93052`;
- frozen Core tree remains `fe77f8a0706acfaf369041d0882b6d0e6de39f22`;
- PR #205 remains pinned at `d17ae972ad1d312735c355f775ac024bc4cebdf7`;
- no `src/aios_core/**`, fixture, evaluator, governance, or #205 changes;
- no real cursor-14 reveal to a Resident/model;
- no Resident B/C;
- no merge, force-push, rebase, or squash.

## Exit condition

Do **not** request PM re-review yet. The next permitted action is a fresh execution of the modified
`isolation/probe_e2e.sh` in the exact frozen environment. Only if it produces
`ALL_CHECKS=156/156 FAILURES=0` and `CORRECTIVE_011_E2E_PASS` may the packet transition to
`REVIEW_READY / AWAITING_PM_RE-REVIEW`.
