# TRUST_MINT_PATH_AUDIT — static source audit of every trusted-state write site

Scope of the audit: the Corrective-002 head, `src/aios_core/runtime/**`
(`background_attempt.py`, `late_return.py`, `live_return.py`, `cognitive_runtime.py`,
`turn_runtime.py`, `__init__.py`).  Method: enumerate every SQL statement that
writes the three trust tables, then determine the authority each site requires and
whether that authority survives process death.  `grep` evidence below is verbatim
from the audited head.

## 1. Complete write-site inventory

```
$ grep -rn "INTO background_model_response_receipts\|UPDATE background_model_response_receipts\
|INTO background_model_return_handoffs\|UPDATE background_model_return_handoffs\
|INTO background_model_responses\|UPDATE background_model_responses" src/aios_core
src/aios_core/runtime/background_attempt.py:991   UPDATE background_model_response_receipts
src/aios_core/runtime/background_attempt.py:996   UPDATE background_model_return_handoffs
src/aios_core/runtime/background_attempt.py:1011  UPDATE background_model_responses
src/aios_core/runtime/background_attempt.py:2301  INSERT OR IGNORE INTO background_model_response_receipts
src/aios_core/runtime/background_attempt.py:2350  INSERT OR IGNORE INTO background_model_return_handoffs
src/aios_core/runtime/background_attempt.py:2530  INSERT OR IGNORE INTO background_model_response_receipts
src/aios_core/runtime/background_attempt.py:2582  INSERT OR IGNORE INTO background_model_return_handoffs
src/aios_core/runtime/background_attempt.py:2872  INSERT OR IGNORE INTO background_model_responses
```

No other module contains a write to these tables; there is no `executescript`
against them (`executescript` appears once in `metering.py` for the metering table),
no dynamic table-name construction, no `f`-string SQL in `runtime/**`, and no
`INSERT ... ON CONFLICT`/`REPLACE` variant anywhere else.

## 2. Write site → method → authority → crash survival

| Line | Enclosing method | What it writes | Authority required | Does that authority survive crash? |
| --- | --- | --- | --- | --- |
| 2301 / 2350 | `BackgroundModelAttemptStore.attach_late_trusted_return` | new receipt row + exact handoff row, `bgresponse_v2_…` proof | durable `background_model_return_verifiers` row bound **before dispatch** + RSA PKCS#1 v1.5 SHA-256 signature over the canonical message (attempt, subject, work kind/id, round, outbound fingerprint, relay id, provider, model, provider request id, response fingerprint, payload SHA-256) verified by `verify_late_return_proof` + one-shot `consumed_at` gate, all inside `BEGIN IMMEDIATE` | Yes — but the authority is the *external private key*, which Core does not hold. A recovery caller can only produce this row if the genuine trusted side signed these exact bytes. |
| 2530 / 2582 | `BackgroundModelAttemptStore.record_live_provider_return` | new receipt row + exact handoff row, `bgresponse_v2_…` proof | mandatory `live_window: LiveProviderReturnWindow` consumed by `consume_live_provider_return_window`, which requires (a) registry identity of the exact object issued by the live frame, (b) `_ACTIVE_WINDOW` armed on the **current** call stack, (c) open state, (d) matching attempt id, (e) captured directive *is* the object the in-process handler returned | **No.** Registry, `ContextVar` and handler-return identity all die with the process; nothing about the window is persisted (no column, no row, no WAL frame). |
| 991 / 996 / 1011 | `BackgroundModelAttemptStore._migrate_legacy_authenticity_authority` | proof-string **conversion** of pre-existing legacy rows only (no new row, no new attempt) | legacy `bgresponse_v1_` HMAC verified with the legacy 256-bit `trusted-return-v1` secret **plus** full cross-table scope verification for every row, before any `UPDATE`; single transaction, full rollback on any failure | The legacy secret is destroyed by the same migration. The only state affected is that which already existed; a recovery caller cannot create a row through this path. |
| 2872 | `BackgroundModelAttemptStore.stage_exact_response` | staged copy of already-trusted bytes in `background_model_responses` | `_verify_response_authenticity` requires an **existing** receipt row for the attempt whose twelve bound columns and proof equal the supplied values; a missing receipt raises `BackgroundModelResponseConflict("trusted provider-return authenticity …")` before the `INSERT` | Yes, but only for bytes already covered by a receipt — the receipt is the authority, and it can only have come from site 1, 2 or 3. |

Callers of the two minting sites in the whole source tree:

```
$ grep -rn "record_live_provider_return\|attach_late_trusted_return" src/aios_core
background_attempt.py:2416:  def record_live_provider_return(            # definition
turn_runtime.py:1362:        self.background_model_attempts.record_live_provider_return(  # live frame only
background_attempt.py:2111:  def attach_late_trusted_return(              # definition
background_attempt.py:2440:  …:meth:`attach_late_trusted_return`         # docstring reference
```

`turn_runtime.py:1362` is inside `FusedTurnRuntime._capture_live_provider_return`,
which is only reachable as the `model_response_authenticator` callback invoked from
`cognitive_runtime.py:413` **inside** the `with _live_provider_return_window(...)`
block that wraps the provider-handler invocation
(`cognitive_runtime.py:391–415`).  Recovery code paths never enter that block.

## 3. Object-graph reachability

`FusedTurnRuntime` after a crash exposes (mechanically enumerated in `CA2-001`):
attempt store, turn-execution store, metering ledger, wake bus, capability registry,
world store, search index, session/conversation state, handlers and policy objects.
The sweep invokes every reachable callable whose name suggests trust state with
attacker-controlled arguments and asserts the three trust tables stay empty; it also
asserts the removed names are **absent**:

```
runtime._authenticate_background_model_response            # removed (was in the IA17 report)
runtime.background_model_attempts._capture_trusted_response_return   # removed
```

`_capture_live_provider_return` still exists as a method name, but it carries no
authority: it raises `LiveReturnAuthorityError` unless a genuine `live_window` is
supplied, and no recovery path can obtain one.  It writes nothing by itself (the
write happens in the store method, gated by the window).

## 4. The specific anti-pattern that is gone

Old: `caller bytes → caller-supplied attempt id → _capture_trusted_response_return
→ keyless public checksum row → trusted receipt/handoff → turn completion`.

New: `caller bytes × (no live window, no verified RSA proof over exactly these
bytes, no pre-existing receipt) → BackgroundModelResponseConflict / LiveReturnAuthorityError
→ no row, no completion`.  Public checksum recomputation is worthless because the
checksum is compared against a row that must already exist, and row creation
requires one of the three authorities above.

## 5. C2-7 preservation check

Removed: the two recovery-reachable mint helpers.  Untouched (verified by
`git diff` and re-run tests): `admit`, `mark_dispatching`, `mark_failure`,
`record_response`, `reconcile_not_submitted`, `reconcile_response`,
`attach_late_trusted_return`, `recover_trusted_handoff`, `pending_exact_response`,
`exact_response_directive`, `stage_exact_response` semantics, plus the whole
Route-B `not_submitted` contract, exactly-once metering, first-writer-wins
consumption and the verifier-substitution refusals
(`IA17-VERIFIER-SUB-001`, `IA17-RACE-CRASH-001`, `IA17-NS-ROUTE-B-001`,
`IA17-ID-JSON-001`, `IA17-SIGKILL-001` remain GREEN).

## 6. Non-necessary observations (not actioned, `C2-10`)

* The in-process authority limitation described in `DESIGN_SECURITY_MODEL.md` §
  "Residual trust boundary" is inherent to a single-process Python trust boundary.
* `background_model_response_receipts.authenticity_proof` is `UNIQUE`; the new
  proof is a pure function of the twelve bound columns, which makes accidental
  duplicate proofs across distinct attempts practically impossible but is not a
  security property.
* No other module in `src/aios_core` reads or writes trust tables directly; the
  store API is the only surface.
