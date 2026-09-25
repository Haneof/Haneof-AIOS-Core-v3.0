# C15-RCC-RES-B-PREFLIGHT-002 — Completion Report (CORRECTIVE-013-FIXUP-001)

Date: 2026-09-26
Task: `C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-013-FIXUP-001`
Role: Release / Test Infrastructure Engineer

## Current state: **FIXUP_001_HANDOFF_READY**

PM blocker review `5319913802` was released by task record `5835591147`. This fixup is limited to current evidence/canonical synchronization; no Corrective-013 implementation bytes are to change. `corrective_012_report.md` and earlier corrective reports remain historical.

The only preflight reveal is a disposable operator-side reveal on a copied release state. Its projection is never presented to a Resident or model and is not a Resident B reveal.

Remote parent: `86aafc1937b58071d4780c77cf2e8abe7fcbed5b`; its tree is `a22f14753e0627a95b08cfb8e60ae3ad80304620`. Local source commit `4ad5f980c2a041c88f9c0fdec62753d7f8b38fb4` has that same tree but different ancestry. PM must rebuild from the remote parent.

## Current CORRECTIVE-013 gate contract

- `EXPECTED_CHECKS=158`
- `ALL_CHECKS=158/158 FAILURES=0`
- `RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS cases=5`
- `RUNBOOK_EXECUTABLE_MUTATION_RED_PASS cases=18`
- `RUNBOOK_SHELL_SEMANTICS_MUTATION_RED_PASS cases=34`
- required markers also include `CANONICAL_PIN_CONSISTENCY_PASS` and `CANONICAL_RUNBOOK_EXECUTABLE_PASS`
- final marker `CORRECTIVE_013_E2E_PASS`

Fresh frozen E2E passed with exit 0. The actual raw log is `/tmp/CORRECTIVE_013_DEBIAN12/rootfs/tmp/c013-e2e-fresh-20260926-002/e2e.log` (SHA-256 `1352c0208a3feb5d435f59f41b57c40b3e61880f778710b9676512f396e321cf`); `isolation/e2e_probe_output.txt` is an exact byte-for-byte copy with the same SHA-256. No hand-assembled E2E output was used.

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

## Current CORRECTIVE-013-FIXUP-001 gate and evidence

Active gate: `EXPECTED_CHECKS=158`; required result `ALL_CHECKS=158/158 FAILURES=0`; final marker `CORRECTIVE_013_E2E_PASS`. Required markers include `ENVIRONMENT_PASS`, `RAW_USAGE_NO_SYNTHESIS_PASS`, `CANONICAL_PIN_CONSISTENCY_PASS`, `CANONICAL_PIN_MUTATION_RED_PASS`, `CANONICAL_RUNBOOK_EXECUTABLE_PASS`, `CANONICAL_RUNBOOK_ORDER_PASS`, `RUNBOOK_CROSS_DOCUMENT_ORDER_PASS`, `RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS cases=5`, `RUNBOOK_EXECUTABLE_MUTATION_RED_PASS cases=18`, and `RUNBOOK_SHELL_SEMANTICS_MUTATION_RED_PASS cases=34`.

Fresh frozen E2E: **PASS, exit 0**, Debian GNU/Linux 12 (bookworm) disposable runtime. Both `python3 --version` and `/usr/bin/python3 --version` were `Python 3.11.2`; package versions were Pydantic `2.13.5`, pydantic_core `2.46.5`, annotated-types `0.8.0`, typing-inspection `0.4.4`, and typing_extensions `4.16.0`. The exact `requirements.freeze.txt` SHA check and live `pip freeze` line check passed.

Raw log `/tmp/CORRECTIVE_013_DEBIAN12/rootfs/tmp/c013-e2e-fresh-20260926-002/e2e.log`: SHA-256 `1352c0208a3feb5d435f59f41b57c40b3e61880f778710b9676512f396e321cf`. Committed evidence `isolation/e2e_probe_output.txt`: SHA-256 `1352c0208a3feb5d435f59f41b57c40b3e61880f778710b9676512f396e321cf`, byte-identical to the raw log. Cursor-14 exact-byte scan: raw hits `0`; committed evidence hits `0`. Required lifecycle self-test markers passed with mutation-red cases cross-document `5`, executable `18`, shell-semantics `34`.

Historical C012 `157/157` results and the old C012 raw-log digest are not current evidence; see the unchanged `corrective_012_report.md`.

## Invariants preserved

- frozen software remains `773876f92d5f8e53422f8f5a68cc651953d93052`;
- frozen Core tree remains `fe77f8a0706acfaf369041d0882b6d0e6de39f22`;
- PR #205 remains pinned at `d17ae972ad1d312735c355f775ac024bc4cebdf7`;
- no `src/aios_core/**`, fixture, evaluator, governance, or #205 changes;
- no real cursor-14 reveal to a Resident/model;
- no Resident B/C;
- no merge, force-push, rebase, or squash.

## Exit condition

After a passing fresh gate, stop at `FIXUP_001_HANDOFF_READY` for PM reconstruction from the remote parent. This local worktree does not have the remote parent ancestry.

Do not merge #209. Do not start Independent Acceptance from this packet. Do not enter B release.
Do not reveal cursor 14 to a Resident or model.
