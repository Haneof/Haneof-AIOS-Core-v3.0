# CORE-RC-REFREEZE-004 — Corrective-003 Trusted-Return Security Spot Checks

Status: **PASS — fresh mechanical proof on the frozen target.** No design change was made in this window.

## 1. Local trust authority removed / tombstone inert

- `src/aios_core/runtime/live_return.py` is a tombstone: schema marker `aios.background-model-live-return-window.v2-decommissioned`, `LOCAL_LIVE_RETURN_AUTHORITY_DECOMMISSIONED = True`, `LiveProviderReturnWindow` unconstructible/unpicklable, `open_live_provider_return_window` inert, `register_handler_return` a no-op.
- The runtime `__init__` re-exports only the inert compatibility names (`LiveProviderReturnWindow`, `LiveReturnAuthorityError`, `live_return_authority_snapshot`) so reviewer probes still import; no module under `src/aios_core/runtime/**` (other than `live_return.py` and `__init__.py`) imports the tombstone (AST audit `TOMBSTONE_AUTHORIZATION_IMPORT_AUDIT=PASS`).
- Removed symbols (`record_live_provider_return`, `consume_live_provider_return_window`, `_ISSUE_SENTINEL`, `_OPEN_WINDOWS`, `_HANDLER_RETURNS`, `_capture_trusted_response_return`, `ModelResponseAuthenticator`, …) have no definition, assignment or import anywhere in `src/` (grep gates in the CI workflow).
- Suite A `IA20-WINDOW-001` enumerates 10 non-live-window satisfactions (none/wrong-attempt/closed/consumed/copied/pickle/other-thread/other-world/unregistered/direct ctor/detached context) — all refused. `IA20-OBJGRAPH-002` finds zero reachable minting callables.
- Live completion path (`record_response`) writes only the `dispatching → response_returned` transition plus unverified live provenance, mints no receipt/handoff/staged row, and is refused when durable trust rows already exist (first-writer-wins for the external authority).

## 2. Alternate-mint write-path inventory (AST, source-level)

`TRUST_MINT_INVENTORY=PASS` on the frozen tree: every `INSERT/UPDATE/DELETE/CREATE` naming the five trust tables lives only in `src/aios_core/runtime/background_attempt.py`; the only INSERT roots are:

- `attach_late_trusted_return` → `background_model_response_receipts`, `background_model_return_handoffs`, `background_model_return_verifiers` (insert/update);
- `stage_exact_response` → `background_model_responses` (exact staged response).

`record_response` (the `response_returned` path) has no trust-table write. Metering is written only by the ordinary metering path after a proven/recovered response; verifier-less or forged proofs never reach it (see below).

## 3. Durable external verifier + genuine proof still required

`attach_late_trusted_return` requires: non-blank payload/proof/evidence; a decoded directive with provider/model/request-id; `BEGIN IMMEDIATE`; attempt in `_STAGABLE_STATES`; `_require_origin_binding(require_relay_echo=False)`; an existing `background_model_return_verifiers` row; a verifier scope tuple (attempt_id, subject_id, work_kind, work_id, model_round_index, outbound_request_fingerprint, relay_id) equal to the durable binding; a canonical `LateReturnVerifier`; `verify_late_return_proof` over `late_return_message(...)`; and the durable one-shot `consumed_at` gate (a consumed verifier must already have both receipt and handoff, else conflict fail-closed).

## 4. Live-execution evidence (focused suite, 388 passed)

Cases: direct-mint refusals, recovery-object-graph scan, verifier-less forged recovery staying `in_doubt`, legacy-keyed-authenticator migration fail-closed/atomicity, cross-attempt transplant refusal, concurrent attach yielding exactly one winner, genuine live-return ephemerality (mints nothing), replay/idempotency, conflict handling, capability-effect replay, and real SIGKILL. Raw JUnit `raw/local/trusted-return-junit.xml`; SIGKILL selection `raw/local/real_process_loss.txt` (9 passed).

Coverage mapped to the window's required spot checks: local trust authority removed (§1); tombstone inert/outside the authorization chain (§1–§2); `attach_late_trusted_return` still requires the durable verifier + genuine proof (§3–§4); alternate-mint write paths enumerated (§2); verifier-less ambiguous recovery fail-closed (C3-3, Suite B `IA20-MINT-004`); supersession of forged local provenance by a later genuine proof (`stage_exact_response` supersedes unproven provenance; Suite B exact-once); conflict/replay (first-wins, conflicting proof refused, exact replay effect-free, transplant refused, exactly-once meter/effect); partial commit (receipt + handoff + staged committed before any downstream effect; winning exact-proof retry recovers, conflict refused, no duplicate effect).

## 5. Registry inventory

`trusted_return_registry_inventory.py` (RC-003 window's own probe, re-run here): **43 reachable capabilities / 22 side-effecting**, matrix match, no provider dispatch, `REGISTRY_MATRIX_PASS` (`raw/local/trusted-return-registry-inventory.txt`).
