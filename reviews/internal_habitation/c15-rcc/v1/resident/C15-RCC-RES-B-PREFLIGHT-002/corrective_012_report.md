# C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-012 — Corrective Report

Parent candidate: `95cffb57a4e94acdc5538dd163f1fb6710ecefc4`  
Independent Acceptance failure: review `5317440556`, blocker count 1, IA-BLK-003  
PM adjudication: `5317453195`

Scope is IA-BLK-003 only. The two positive runbooks were not redesigned. Handler, isolation jail, binding, Scheme-A, usage translator, and the canonical pin checker were not changed.

## IA-BLK-003 — executable step-body lifecycle gate

`checks/runbook_lifecycle_checker.py` no longer treats the first `.projection.json` substring, or the first `current-event.json` mention inside a fence, as proof.

Each lifecycle step is sliced from its own heading. Only executable commands inside that step body satisfy that step. Cross-step prose, a later ACK command, and a comment cannot satisfy an earlier step.

`PERSIST_PROJECTION_EVIDENCE` must contain both exact lines:

- `install -m 0400 "$RUN_ROOT/current-event.json" "$RUN_ROOT/evidence/event-$(printf '%03d' "$SEQ").projection.json"`
- `sha256sum` of that same artifact appended to `projection_digests.sha256`

Source is `current-event.json`. Destination is `evidence/event-%03d.projection.json`.

Other step bodies must contain their own executable contracts: `release_operator.py reveal --phase B`, the exact `install` of `reveal.json` onto `current-event.json`, `create_current_event_binding_receipt` plus `write_binding_receipt`, `validate_current_event_binding(`, `CURRENT_OCCURRED_AT` read from `current-event.json`, canonical conversation ingest plus the mechanical ingest adapter, production `turn --session`, `release_operator.py ack --phase B`, and the exact `rm -f` of `current-event.json` and `binding/current-event-binding.json`.

Fenced bash is parsed after dropping blank lines, `#` comments, and echo-only lines. Continuations are joined before matching. Arrow fences are split on `→` and checked as their own sequence. A receipt-create/write followed later in the same executable sequence by `install`/`cp` of `reveal.json` onto `current-event.json`, or by a bare `current-event.json` step, fails. The old `min()` fence scan is gone.

Every mutation self-test calls `check_runbook_lifecycle()` on a disposable copy. It does not use a simplified checker.

Red through that production function:

- A: delete only the two executable persist lines in each runbook; token, heading, and prose `.projection.json` remain. FAIL.
- B: move those two lines to after `DURABLE_ACK`; tokens and headings unchanged. FAIL on both runbooks.
- C: append a bash fence whose comment mentions `current-event.json` and whose executable order is receipt-create, `write_binding_receipt`, then `cp` of `reveal.json` onto `current-event.json`. FAIL. The comment is not a command.
- Also red: sha256-only deleted, install-only deleted, wrong destination, source changed from `current-event.json` to `reveal.json`, receipt command moved before the projection step, persist command copied into the ACK step while the original remains.

Markers: `RUNBOOK_CROSS_DOCUMENT_ORDER_PASS` and `RUNBOOK_EXECUTABLE_MUTATION_RED_PASS`.

## Gate

`EXPECTED_CHECKS=157`. Prior checks remain. One new counted check records the executable mutation-red aggregate.

Fresh disposable run:

- raw log `/tmp/b-preflight-e2e-c012/e2e.log`
- raw log SHA-256 `38a414ac1f2600d11efa7eb9179c33bc8133bf06c8668092e032d5b0c86be5a2`
- committed copy `isolation/e2e_probe_output.txt` SHA-256 `8af79734c8e5aebfb10a16c2cb19025f89ff52a1e85c62e60811bf16f91780c9`
- `ALL_CHECKS=157/157 FAILURES=0`
- markers include `RAW_USAGE_NO_SYNTHESIS_PASS`, `CANONICAL_PIN_MUTATION_RED_PASS`, `CANONICAL_RUNBOOK_ORDER_PASS`, `RUNBOOK_CROSS_DOCUMENT_ORDER_PASS`, `RUNBOOK_EXECUTABLE_MUTATION_RED_PASS`
- final marker `CORRECTIVE_012_E2E_PASS`

The disposable reveal printed mechanical metadata only and was never presented to a Resident or model. The raw log contains no sealed cursor-14 payload.

## Exit

`REVIEW_READY / AWAITING_PM_RE-REVIEW`.

No Core, fixture, evaluator, governance, or #205 changes. No Resident B/C. No real cursor-14 reveal to a model. No merge, force-push, rebase, or squash. This packet does not perform Independent Acceptance.
