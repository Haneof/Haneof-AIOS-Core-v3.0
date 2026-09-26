# C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-010 — Closure Report

Closes the **single remaining blocker** from independent acceptance review `5315754508`
(`REVIEW_FAIL / BLOCKED`, verdict `REVIEW_FAIL`):

> **BLK-03 / `CANONICAL_RUNBOOK_ORDER_NOT_EXECUTABLE`** — `procedure/b_startup_procedure.md` is still
> not executable *in its documented 1→8 order*. Section 6 read `current-event.json` to derive
> `CURRENT_OCCURRED_AT` and then ran a production `headless … turn` **before** Section 7 revealed a
> cursor, but `current-event.json` and its immutable binding receipt only become legal after
> `release_operator reveal`. With the CORRECTIVE-009 BLK-05 behaviour (`current_event is None` ⇒ STOP)
> this is no longer documentation ambiguity: the numbered runbook could not be executed at all.

Scope: **documentation + probe ordering only.** No architecture expansion, no code-path redesign,
no `src/aios_core/**`, fixture, evaluator, governance or #205 change. `harness/bridged_model_handler.py`
is **byte-identical** to the CORRECTIVE-009 tip — the CORRECTIVE-009 BLK-01/02/04/05/06/07/08 fix
semantics are untouched.

Success marker: **`CORRECTIVE_010_E2E_PASS`** with `EXPECTED_CHECKS` recomputed from the executable's
own `pass_check` count (the retired 139 was **not** reused).

---

## 1. Section 6 is configuration only

`procedure/b_startup_procedure.md` §6 was rewritten. It still exports and pins everything that is
legal to pin before any reveal:

- `B_SESSION` / `B_PROCESS` identity (minted in §5),
- `AIOS_REAL_PROVIDER_API_KEY` / `AIOS_REAL_PROVIDER_ENDPOINT` / `AIOS_PROVIDER_ADAPTER`
  (`bridged_model_handler:ExternalBrokerClient`, HTTPS-only, pinned),
- `AIOS_CONTRACT_SHA256` / `AIOS_WIRE_PROTOCOL_SHA256` / `AIOS_ADAPTER_SHA256`
  (`AIOS_ADAPTER_SHA256` is computed with `sha256sum` and drift-checked against
  `environment_manifest.md`),
- the four canonical paths `AIOS_RELEASE_STATE_PATH`, `AIOS_CURRENT_EVENT_PATH`,
  `AIOS_CURRENT_EVENT_BINDING_PATH`, `AIOS_EVIDENCE_DIR`,
- `PYTHONPATH="src:$B_PREP/harness"`.

It now **forbids** (and asserts) the following:

```bash
[ ! -e "$RUN_ROOT/current-event.json" ] || { echo "STOP: current-event.json exists before reveal"; exit 1; }
[ ! -e "$RUN_ROOT/binding/current-event-binding.json" ] || { echo "STOP: binding receipt exists before reveal"; exit 1; }
```

plus a Python assertion that `release_state.json` is in the pristine Phase-B boundary
(`active_phase == "B"`, `pending_reveal is null`, `next_sequence == 14`), and it states verbatim:

> **No model dispatch occurs in this section. The first production model turn occurs only inside the
> per-cursor loop (Section 7) after reveal + binding receipt installation.**

§6 contains **no** `CURRENT_OCCURRED_AT` derivation, **no** `--at` and **no** `turn --session`.

## 2. The real turn moved into Section 7, in the only legal order

`b_startup_procedure.md` §7 now carries the whole per-cursor sequence as numbered steps
**7.1 – 7.12**, in order:

| Step | Action |
| --- | --- |
| 7.1 | `release_operator reveal --phase B` → `$RUN_ROOT/reveal.json` (exactly one per cursor) |
| 7.2 | write `current-event.json` (`install -m 0400`) |
| 7.3 | persist the immutable `$RUN_ROOT/evidence/event-XXX.projection.json` + `projection_digests.sha256` |
| 7.4 | **create the immutable binding receipt** — the exact `create_current_event_binding_receipt(...)` → `write_binding_receipt(...)` command is written inline in this runbook |
| 7.5 | verify receipt / state / event binding (`validate_current_event_binding`) |
| 7.6 | derive `CURRENT_OCCURRED_AT` from `current-event.json` (**after** reveal) |
| 7.7 | ingest the current cursor (`canonical_conversation_ingest.py` / `mechanical_ingest_adapter.py`) |
| 7.8 | run the exact production headless turn / `due` / model rounds (`--at "$CURRENT_OCCURRED_AT"`) |
| 7.9 | finish all model work for this cursor |
| 7.10 | durable ACK (`release_operator.py ack …`) |
| 7.11 | clear `current-event.json` + binding receipt (only now) |
| 7.12 | reveal the next cursor before any later model invocation |

`CURRENT_OCCURRED_AT` is documented as *the canonical ingest/run time of this cursor, read from the
projection produced by reveal in 7.1 — never hardcoded and never pre-read in Section 6*.

## 3. Receipt creation is explicit in the main runbook

Step 7.4 contains the full command chain at the point of use (no "see another document"):

```
release_operator reveal  →  reveal projection bytes
                         →  create_current_event_binding_receipt(...)
                         →  write_binding_receipt(receipt, AIOS_CURRENT_EVENT_BINDING_PATH)
                         →  current-event.json
                         →  handler
```

`create_current_event_binding_receipt` itself fails closed unless the live release state exists, is
readable, is valid JSON, has `next_sequence`, and carries a `pending_reveal` whose `sequence`,
`event_id` and `fixture_sha256` match the revealed projection exactly.

## 4. New mandatory regression — `CANONICAL_RUNBOOK_ORDER_PASS`

`isolation/probe_e2e.sh` gained a fresh disposable regression that executes the documented order on a
fresh Phase-B copy (never the accepted lineage):

```
prepare runtime (byte-exact A-002 lineage copy + writer.lock)
  → recovery-status            (rev98 / watermark98 / lag0 / AUTO_RECOVERABLE / ok, no model invocation)
  → init --phase B
  → configure handler env      (Section-6 configuration block only)
  → assert NO current event / NO binding receipt / pending_reveal == null / NO model turn yet
  → prove through the REAL production handler that a dispatch at this point STOPs
        (ModelDispatchNotSubmitted, 0 provider invocations, poisoned, durable 0400 receipt)
  → release_operator reveal --phase B      (exactly one; stdout captured in-process, never printed)
  → install current-event.json
  → create the immutable 0400 binding receipt from the reveal bytes
  → persist event-014.projection.json + projection_digests.sha256
  → validate_current_event_binding(...)
  → derive CURRENT_OCCURRED_AT from current-event.json
  → FusedTurnRuntime.run_turn → ProductionResidentHandler → ExternalBrokerClient → FakeBrokerServer
  → provider transport boundary reached
```

Observed in the fresh run:

```
RUNBOOK_STATIC_ORDER_PASS section6_config_only=True section7_steps=12
BEFORE_REVEAL: no current-event.json, no binding receipt, pending_reveal=null
PRE_REVEAL_STOP_OK provider_calls=0 receipts=1
REVEALED_SEQ=14 EVENT_ID_VISIBLE=True FIELDS=8
RECEIPT_CREATED_AFTER_REVEAL seq=14 mode=0400 sha_bound=True
BINDING_VERIFIED seq=14
DERIVED_CURRENT_OCCURRED_AT=<occurred_at of the revealed cursor 14, from current-event.json>
PRODUCTION_TURN_REACHED_TRANSPORT invocations=2 http_posts=2 provider=fake-broker
CANONICAL_RUNBOOK_ORDER_PASS order=1-12 reveal_before_event=True receipt_from_reveal=True
  occurred_at_derived_after_reveal=True transport_boundary_reached=True
```

Prohibitions honoured by the regression:

- **no** event or receipt is created before the documented reveal (asserted absent, and the receipt's
  `canonical_projection_sha256` is proven equal to the SHA of the reveal bytes);
- **no** mutation of `release_state.pending_reveal` to make the test green — the only writer of
  `pending_reveal` is `release_operator reveal` itself;
- **no** bypass of the production handler — the pre-reveal STOP is proven through
  `ProductionResidentHandler`, and the post-reveal turn goes through
  `ProductionResidentHandler` + `ExternalBrokerClient` + `FakeBrokerServer`;
- the cursor-14 payload is re-scanned out of the run log before the marker is emitted.

`CANONICAL_RUNBOOK_EXECUTABLE_PASS` (recovery-status only) is **retained** and still mandatory, but it
is no longer allowed to stand in for the full runbook order.

## 5. Gate recomputation

`EXPECTED_CHECKS` is derived from the executable's own `pass_check` count on every run — it was
recomputed for CORRECTIVE-010 (the retired 139 was **not** reused), and the probe fails closed unless
`CHECKS == EXPECTED_CHECKS` and `FAILURES == 0`. Stale-text greps now also assert that the retired
CORRECTIVE-009 marker and the retired CORRECTIVE-009 check count appear nowhere in `*.md`.

Final marker: **`CORRECTIVE_010_E2E_PASS`**.

## 6. Not performed

No PR #209 merge, no `src/aios_core/**` change, no sealed-fixture / evaluator / governance / #205
change, no real cursor-14 reveal to a model, no real Resident B run, no Resident C run, no B release
entry, no C15 evaluator/close, no C16/P16/P17. `b57ed6b36be80686cbae9e8700f851eba85edb4f` is
preserved in history as the CORRECTIVE-009 candidate.
