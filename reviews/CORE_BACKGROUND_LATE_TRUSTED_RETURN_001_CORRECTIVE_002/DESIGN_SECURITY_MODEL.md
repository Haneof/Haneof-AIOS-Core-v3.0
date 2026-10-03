# DESIGN_SECURITY_MODEL — Corrective-002 trust authority

## Threat model that Corrective-001 failed

`BLK-W17-001` established the operative fact: **Python underscore naming is not an
authorization boundary**.  After a crash, any code that holds a `FusedTurnRuntime`,
a `BackgroundModelAttemptStore` or a `SQLiteWorldStore` can call any method on them.
Corrective-001 therefore had, in effect, a public "mint trusted state" API: the
helper `_capture_trusted_response_return` accepted only caller-supplied arguments
(attempt id, timestamp, directive) and wrote a durable trusted receipt + exact
handoff with a keyless `bgresponse_v2_…` proof.  A recovery caller could fabricate
bytes, mint the trusted row for them, and complete the interrupted turn with a
response the provider never returned.

The same defect had a second face (`BLK-W17-002`): because the proof was a public
SHA-256 over public fields, `stage_exact_response` accepted a proof the caller
computed by hand; and the legacy `bgresponse_v1_` HMAC migration rewrote proofs
*without verifying the HMAC*, laundering tampered pre-upgrade rows into trusted
state.

## Corrective-002 authority model

Durable trust state is `background_model_response_receipts`,
`background_model_return_handoffs` and the `authenticity_proof` on
`background_model_responses`.  Under Corrective-002 there are exactly **three**
ways such state can come into existence, and none of them is "a caller passed
arguments":

1. **Live provider-return authority (ephemeral, `C2-2`).**
   `aios_core.runtime.live_return.open_live_provider_return_window()` is opened by
   the live model-call frame only, in
   `CognitiveRuntime` — the same frame that invokes the provider handler
   (`cognitive_runtime.py`, "`with _live_provider_return_window(...)`").  The
   authority is a `LiveProviderReturnWindow`: a one-shot, attempt-bound token that
   exists in **three** process-local structures only (an `RLock`-guarded registry,
   a `ContextVar` armed on the issuing stack, and a handler-return identity map)
   and is destroyed when the frame exits. It is not persisted, not serialized, not
   copyable (`__reduce__`/`__getstate__`/`__copy__`/`__deepcopy__` all raise), not
   attached to any runtime/store object, and not reconstructible after process
   death.  Consumption requires *all* of: registry identity, being armed on the
   current stack, still-open state, matching attempt id, and the captured directive
   being the exact object the in-process handler returned.
   `BackgroundModelAttemptStore.record_live_provider_return(..., live_window=…)` is
   the single writer on this path.

2. **Verified external RSA late return (`C2-3`, `C2-4`).**
   `attach_late_trusted_return(...)` requires a durable, pre-dispatch-bound
   `LateReturnVerifier`, verifies an RSA PKCS#1 v1.5 SHA-256 signature over the
   canonical message binding attempt/scope/provider/response fields, and only then
   writes receipt + handoff + staged response inside one `BEGIN IMMEDIATE`
   transaction with a durable one-shot consumption gate.  No private key, nonce or
   capability exists inside Core.

3. **Verified legacy conversion (`C2-4`).**
   `_migrate_legacy_authenticity_authority(conn)` converts an existing
   `bgresponse_v1_` HMAC proof into the public integrity fingerprint **only after**
   the legacy HMAC verifies and every cross-table scope check passes for every row
   (see `LEGACY_MIGRATION_AUDIT.md`).  It creates no new row and trusts no caller
   argument.

Everything else fails closed:

* `authenticity_proof` (`bgresponse_v2_<sha256>`) is an **integrity fingerprint**
  only — it localizes which row is corrupt.  Recomputing it by hand confers nothing,
  because `_verify_response_authenticity` requires the row to already exist and to
  match byte-for-byte; a caller-computed proof cannot create a receipt.
* A verifier-less / anonymous dispatch (`late_return_verifier is None` at
  `mark_dispatching`) can never be recovered through an external proof: the
  `background_model_return_verifiers` row is absent, so `attach_late_trusted_return`
  refuses, and no live window exists after the crash.  The attempt stays `in_doubt`.
* `recover_trusted_handoff` promotes only bytes that already have a durable receipt
  whose proof matches; it mints nothing.

## Residual trust boundary (disclosed honestly)

The ephemeral-authority design separates the live provider-return call stack, the
post-crash recovery object graph and the durable database.  It is **not** a defence
against arbitrary Python code that already executes inside the Core process and
deliberately calls `open_live_provider_return_window()` itself to fake a live
provider boundary.  That is the same in-process limitation disclosed for the
accepted Window 12/14/16 trust rulings (any in-process caller could previously reach
the authority helpers directly), and it is not a contradiction of `C2-1`/`C2-2`: a
post-crash recovery process has no window, no registry entry, no armed stack and no
handler-returned object, and nothing about them is persisted.

## What is proven mechanically

| Property | Evidence |
| --- | --- |
| no receipt/handoff/staged-response mint API in the recovery object graph | `IA17-OBJGRAPH-001`, `CA2-001` (mechanical sweep over the reachable graph) |
| direct writer calls fail closed without a genuine live window | `IA17-MINT-001`, `CA2-002` |
| anonymous/verifier-less interrupted dispatch stays `in_doubt` | `IA17-MINT-002`, `CA2-003` |
| keyless public proof is not authority | `IA17-DOWNGRADE-001` |
| live authority is ephemeral and non-persisted | `CA2-004` (+ real-fork SIGKILL variant) |
| legacy conversion is verify-before-convert and atomic | `IA17-MIGRATE-002`, `CA2-005` … `CA2-009` |
| canonical proof/key-id and RSA parameter contract | `IA17-RSA-DELIMITER-001`, `IA17-RSA-001`, `test_late_return_canonical_encoding_002.py` |
