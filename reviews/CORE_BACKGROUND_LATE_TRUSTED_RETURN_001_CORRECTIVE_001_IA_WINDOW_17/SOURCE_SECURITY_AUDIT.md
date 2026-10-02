# Source Security Audit (`SOURCE_SECURITY_AUDIT.md`)

- **Reviewed Exact Candidate:** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)
- **Construction Base:** `0b883c71d91e5f0772334514925237f1570fa780`

## 1. Governance C1–C8 Independent Evaluation Matrix

| Clause | Requirement | Candidate Status | Binding Blocker(s) |
|---|---|---|---|
| **C1** | No Post-Hoc Signing / Trust-Minting Oracle on Recovery Surface | **FAIL** | `BLK-W17-001` (`_capture_trusted_response_return` & `_authenticate_background_model_response` on recovery object graph mint trusted receipts & handoffs for `dispatching`/`in_doubt` attempts without any external signature) |
| **C2** | Verifier-Only Recovery (Authenticity != Integrity) | **FAIL** | `BLK-W17-001`, `BLK-W17-002` (`_receipt_proof` downgraded to keyless public SHA-256 `bgresponse_v2_<sha256>`), `BLK-W17-003` (`LateReturnVerifier` accepts colon `key_id` & negative `modulus_hex` that `verify_late_return_proof` can never verify) |
| **C3** | Secret Separation & Safe Legacy Upgrade | **FAIL** | `BLK-W17-002` (`_initialize()` purges `background_model_authenticity_authority` after blindly overwriting `authenticity_proof` in receipts/handoffs/responses with `bgresponse_v2_<sha256>` without verifying existing `bgresponse_v1_<hmac>`, laundering tampered pre-upgrade rows into trusted state) |
| **C4** | Complete Closure of ALL `not_submitted` Write Sites | **PASS** | None (`reconcile_not_submitted`, `mark_failure`, runtime wrappers, and `admit`/`mark_dispatching` enforce `state == 'admitted'` + zero `_durable_submission_artifacts`) |
| **C5** | Caller Boolean / Exception Type Is Not Proof Post-Binding | **PASS** | None (`definitely_not_submitted=True` and `ModelDispatchNotSubmitted` after `mark_dispatching` route to `in_doubt` and raise `BackgroundModelResponseConflict`) |
| **C6** | Coherent Retry / Verifier Lifecycle (Route B) | **PARTIAL / FAIL** | Route-B post-binding retry elimination & first-writer-wins verifier consumption (`consumed_at`) pass, but `BLK-W17-001` bypasses `background_model_return_verifiers` and poisons genuine RSA returns, and `BLK-W17-003` breaks verifier lifecycle when `key_id` contains `:` |
| **C7** | Preserve R1–R5 / Exactly-Once | **FAIL** | `BLK-W17-001` and `BLK-W17-002` weaken the `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001` receipt authenticity boundary |
| **C8** | Anonymous / Local / No-Verifier Remains `FAIL_CLOSED` | **FAIL** | `BLK-W17-001` (`IA17-MINT-002`: an `in_doubt` attempt dispatched with `late_return_verifier=None` can be completed via `_capture_trusted_response_return`) |

## 2. Production Tree Secret & Private Key Scan

Fresh scan of `src/aios_core/**` at `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd`:
- Zero PEM private keys, zero RSA private exponents (`_RSA_D`), zero prime factors (`p`, `q`), zero `capability_nonce` columns, and zero `secret_hex` columns remain in `src/aios_core/**`.
- However, removing the HMAC secret from SQLite while leaving `_capture_trusted_response_return` exposed on `BackgroundModelAttemptStore` and replacing `_receipt_proof` with a keyless SHA-256 digest moved the vulnerability from *"secret key readable from DB"* (`BLK-W14-001`/`BLK-W14-002`) to *"no secret key needed at all to mint a receipt/handoff via `runtime.background_model_attempts._capture_trusted_response_return`"* (`BLK-W17-001`/`BLK-W17-002`).
