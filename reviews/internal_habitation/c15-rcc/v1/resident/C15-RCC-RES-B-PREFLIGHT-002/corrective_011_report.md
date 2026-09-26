# C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-011 — Corrective Report

Parent candidate: `a8576e8b60c400845ceeecc6b7145202e4d1f617`  
Independent Acceptance failure: review `5316831911`, blocker count 3  
PM adjudication: `5316852416`

Scope is limited to the three adjudicated blockers. No architecture expansion is authorized.

## 1. IA-BLK-001 — RAW usage, no synthesis

Changed `harness/bridged_model_handler.py` so `ModelUsage.total_tokens` can only originate from the
provider's own `total_tokens` field. The removed behavior was the local
`input_tokens + output_tokens -> total_tokens` synthesis.

New adapter SHA-256:
`da74eb97a6d35b535f298f52a72a32fc35dfbd1fca1ec4585aa1d7c090e92911`.

The E2E regression now covers:

- full 20/22/42;
- missing total + 20/22;
- input only;
- output only;
- total only;
- valid total + partial optional input/output;
- inconsistent 10/20/22;
- negative/bool/string fields;
- AST inspection proving every production `ModelUsage(total_tokens=...)` uses `tot_i` directly and
  `sum_tot` is absent.

Target marker: `RAW_USAGE_NO_SYNTHESIS_PASS`.

## 2. IA-BLK-002 — declaration-complete pin gate

Added `checks/canonical_pin_checker.py`.

The production gate and the mutation self-test both call `check_canonical_pin_docs()` on real files.
Mutations are written to disposable copies; the self-test does not keep a second comparison
implementation. The checker does not use “canonical hash appears somewhere” as its success
criterion: it enumerates every authoritative declaration occurrence and rejects any wrong occurrence.

Mutation matrix contains 11 red cases:

1–3. operator manifest World/Index/Release one-hex mutations (bare declarations preferred);
4–6. source pins World/Index/Release one-hex mutations;
7–9. startup procedure World/Index/Release one-hex mutations;
10. duplicate wrong World declaration;
11. missing all World declarations.

Target markers: `CANONICAL_PIN_CONSISTENCY_PASS` and `CANONICAL_PIN_MUTATION_RED_PASS`.

## 3. IA-BLK-003 — synchronized lifecycle

`b_startup_procedure.md §7` is the sole authority.

`per_cursor_interaction.md` is an exact operational mirror/reference of `b_startup_procedure.md §7`.
If any wording diverges, startup §7 is authoritative and execution must STOP until the documents are
resynchronized. The candidate itself is synchronized. Both documents expose this exact mechanical
sequence:

`REVEAL > INSTALL_CURRENT_EVENT > PERSIST_PROJECTION_EVIDENCE > CREATE_BINDING_RECEIPT > VERIFY_BINDING > DERIVE_OCCURRED_AT > INGEST > MODEL_WORK > DURABLE_ACK > CLEAR_BINDING > NEXT_REVEAL`

Finish-all-cursor-model-work remains required prose between `MODEL_WORK` and `DURABLE_ACK`.
Executable snippets follow the same order. Receipt is not created before `current-event.json`.
Projection evidence is persisted before the receipt.

`checks/runbook_lifecycle_checker.py` reads both active docs. Token block, operational headings,
executable anchors, and fenced/arrow chains must agree. Disposable-copy self-tests, all calling
`check_runbook_lifecycle()`, red:

- swapping the per_cursor receipt and current-event step sections back to the old order;
- missing projection evidence;
- duplicate projection evidence;
- restoring the old receipt-before-current-event chain while leaving headings untouched;
- reordering only the token block.

Target markers: `RUNBOOK_CROSS_DOCUMENT_ORDER_PASS` and
`RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS`.

## Gate count

Parent exact gate: 144 checks.

CORRECTIVE-011 adds:
- 9 usage checks;
- 1 pin mutation-red aggregate check (the existing four pin consistency checks remain);
- 2 cross-document lifecycle checks.

New exact target: `EXPECTED_CHECKS=156`.

## Evidence boundary

Fresh frozen E2E was executed after the residual false-green fixes. Python `3.11.2`.

- raw log `/tmp/b-preflight-e2e-c011b/e2e.log`
- raw log SHA-256 `94f7388ced02512a61a3933648cb520de7cfe74e0ec778887cb7f00a78803ed8`
- committed copy SHA-256 `6f860779c08d891bb02c83031e84054481954af3a419207b7063b6df5df34792`
- `ALL_CHECKS=156/156 FAILURES=0`
- `CORRECTIVE_011_E2E_PASS`

The parent 144/144 log remains historical only and is not relabeled.

State: `REVIEW_READY / AWAITING_PM_RE-REVIEW`.

No Resident B/C, B release, merge, Core/fixture/evaluator/governance/#205 modification, force-push,
rebase, or squash is part of CORRECTIVE-011.
