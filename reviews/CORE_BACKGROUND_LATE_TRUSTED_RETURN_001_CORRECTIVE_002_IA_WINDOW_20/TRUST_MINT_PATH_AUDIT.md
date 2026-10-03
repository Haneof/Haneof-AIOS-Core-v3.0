# Window 20 — Trust-Mint Path Enumeration & Attack (`TRUST_MINT_PATH_AUDIT.md`)

Reviewed exact candidate: `fec30bd1495017bf13f08b0ef5b1e241dfb0e247`.

## 1. Fresh enumeration of every writer of durable trust state

`grep` over `src/aios_core/**` for `INSERT/UPDATE/DELETE/DROP` against
`background_model_response_receipts`, `background_model_return_handoffs`,
`background_model_responses` (the only durable trust tables) yields exactly four
enclosing functions in the candidate:

| # | Function | Table/effect | Authority required | Recovery caller reachable? | Verdict |
|---|---|---|---|---|---|
| 1 | `_migrate_legacy_authenticity_authority` (legacy conversion) | UPDATE proofs, DELETE + DROP authority table | verify-before-convert of complete legacy trust state under the legacy HMAC key | yes (runs on store open) | **SAFE** — refused unless every legacy row authenticates and cross-checks; whole-database transaction with rollback (reviewer probes `IA20-MIGRATE-003/004`) |
| 2 | `attach_late_trusted_return` | INSERT receipt + handoff | genuine external RSA PKCS#1 v1.5 proof over the 13-field canonical message, bound to attempt/round/relay/request/response/digest | yes | **SAFE** — reviewer-signed genuine return accepted once; all 12 field transplants refused; conflicting replay refused (`IA20-RSA-TRANSPLANT-001`, `IA20-EXACTONCE-001`) |
| 3 | `stage_exact_response` | INSERT staged response | pre-existing durable receipt row whose fingerprint matches | yes | **SAFE** — caller-computed `bgresponse_v2_<sha256>` cannot create the receipt, so the staged row never becomes trustworthy on its own (`IA17-DOWNGRADE-001` green on candidate) |
| 4 | **`record_live_provider_return`** | INSERT receipt + handoff | **the ephemeral `LiveProviderReturnWindow` only** | yes | **FAIL / CRITICAL — `BLK-W20-001`** |

## 2. The ephemeral authority, as implemented

`src/aios_core/runtime/live_return.py`:

- `open_live_provider_return_window(*, attempt_id)` is a **public module-level
  context manager** exported in `__all__`. Its only precondition is
  `_ACTIVE_WINDOW.get() is None`. It mints the window itself and arms it via
  `_ACTIVE_WINDOW.set(window)`.
- `register_handler_return(window, directive)` is a **public module-level
  function**; it records `id(directive)` for that window. The docstring says it is
  "Called by cognitive_runtime in the same frame", but nothing verifies the caller.
- `consume_live_provider_return_window` checks: `isinstance`,
  `_OPEN_WINDOWS[window.window_id] is window`, `_ACTIVE_WINDOW.get() is window`,
  `window._state == "open"`, `window.attempt_id == attempt_id`, and
  `_HANDLER_RETURNS[window_id] == id(directive)`.

Every one of those predicates is satisfied by a caller that issued the window
itself: the registry entry *is* the caller's own object, the `ContextVar` is armed
*by the caller's own `with` block*, the handler-return identity is whatever object
the caller passed to `register_handler_return`, and the attempt id is chosen by the
caller. The module docstring discloses that the design "is not a defence against
arbitrary Python code that already executes inside the Core process and
deliberately drives this module's issuing helpers" — but that is exactly the class
of caller Window 17 proved must not be able to mint (`BLK-W17-001`,
`T1`/`T2`/`T3`/`T4`/`T6`), and here nothing but the caller's own cooperation stands
between "arbitrary bytes" and a durable trusted receipt.

## 3. Mechanical attacks executed (frozen reviewer probes)

Frozen before execution (`PROBE_FREEZE_MANIFEST.md`), raw in
`raw/candidate_w20_probes_v3_on_fec30bd.txt`:

1. **Public-API forgery (`IA20-MINT-003`, FAIL).** Post-crash recovery caller,
   no RSA key, no provider call:
   `open_live_provider_return_window` → `register_handler_return(forged)` →
   `record_live_provider_return(live_window=window)` → `run_turn`.
   Observed: `minted=True, state=metered, receipts=1, handoffs=1, responses=1,
   meters=1`, turn response is the attacker's string, and the subsequent genuine
   external RSA return is rejected as a conflict (`genuine_rsa_return_poisoned=True`)
   — identical end-to-end effect to `IA17-MINT-001`.
2. **Verifier-less bypass (`IA20-MINT-004`, FAIL).** Same forgery on an attempt
   dispatched with `late_return_verifier=None` (no verifier row bound):
   `state=metered, receipts=1, handoffs=1, responses=1, meters=1,
   turn_response='FORGED_ON_VERIFIERLESS_ATTEMPT_VIA_PUBLIC_WINDOW'` — the
   `C8`/`T6` permanent-`in_doubt` requirement is broken, as in `IA17-MINT-002`.
3. **Object-graph reachability (`IA20-OBJGRAPH-002`, FAIL).** Without importing
   `live_return` by name, starting only from the recovery runtime:
   `type(store).record_live_provider_return.__globals__` →
   `LiveProviderReturnWindow._issue.__func__.__globals__` exposes
   `_ISSUE_SENTINEL`, `_OPEN_WINDOWS`, `_HANDLER_RETURNS`, `_ACTIVE_WINDOW`;
   the probe then mints `receipts=1, handoffs=1` from the forged directive. This is
   the W17 object-graph criterion applied to the new design (the frozen
   `IA17-OBJGRAPH-001` probe cannot see it because it is a name-filtered,
   depth-limited walk).

Attempts **outside** these three remain correctly refused (`IA20-WINDOW-001`): no
window, wrong attempt id, closed window, consumed window, `copy`/`deepcopy`/`pickle`,
use from another thread, unregistered forged object, direct construction. The
design's *token hygiene* is real; its *issuance authority* is not.

## 4. Enumeration of non-authority residue

- No private RSA material or nonce is stored in the DB/WAL/SHM/dump/backup
  (`IA17-DB-AT-REST-001` green; reviewer batch-2 signing key never entered the DB).
- The legacy authority secret is deleted + table dropped only after full
  verification, with `wal_checkpoint(TRUNCATE)`; on any failure the secret and
  table are preserved (`IA20-MIGRATE-003/004`).
