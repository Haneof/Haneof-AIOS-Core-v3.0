# WINDOW 17 — Fresh Independent Acceptance Report (`IA_REPORT.md`)

```text
WINDOW_17 = COMPLETE / CLOSED

CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE
= ACCEPTANCE_FAIL / blocker=3

CORRECTIVE_OR_ADJUDICATION_REQUIRED

candidate:
cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd

PR #308:
OPEN / UNMERGED / FAILED_EXACT_CANDIDATE_PENDING_PM_ADJUDICATION / DO NOT MERGE
```

---

## 1. Executive Summary & Independent Verdict

As Fresh Independent Core Runtime Acceptance Reviewer (`WINDOW 17`), I performed a clean-room source, cryptographic, object-graph, database-migration, and multi-process adversarial audit of `PR #308` exact candidate `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (branch `core-background-late-trusted-return-corrective-001-window16`, parent `293d32c683033ba27c11059fd021e68342a82c77`, tree `a762df979826d3a599b93d937c53b633d0cb8466`, construction base `0b883c71d91e5f0772334514925237f1570fa780`).

While the candidate properly closes post-binding `not_submitted` write sites (`C4`/`C5` Route B) and adds an external RSA PKCS#1 v1.5 verifier path on `attach_late_trusted_return(...)`, **it fails `C1`, `C2`, `C3`, `C6`, `C7`, `C8`, and Frozen Security Boundary Constraints `T1`, `T2`, `T3`, `T4`, `T5`, `T6` with three binding blockers (`blocker=3`)**, reproduced mechanically by 6 failing probes in the frozen reviewer suite (`reviewer_probes/window17_independent_attack.py`, SHA-256 `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3`):

1. **`BLK-W17-001` (`CRITICAL` — `RECOVERY_TRUSTED_RECEIPT_AND_HANDOFF_MINTING_ORACLE_VIA_CAPTURE_HELPER`):**
   Candidate removed the HMAC key table `background_model_authenticity_authority` and downgraded `BackgroundModelAttemptStore._receipt_proof(...)` (`src/aios_core/runtime/background_attempt.py:807-817`) to a **keyless public SHA-256 digest (`bgresponse_v2_<sha256>`)**, while leaving `BackgroundModelAttemptStore._capture_trusted_response_return(...)` (`lines 2050-2217`) and `FusedTurnRuntime._authenticate_background_model_response(...)` (`src/aios_core/runtime/turn_runtime.py:1329-1352`) directly mounted on the ordinary recovery-reachable runtime/store object graph and accepting `attempt.state in {"dispatching", "in_doubt", "response_returned", "metered"}`.
   - Any ordinary post-crash recovery caller holding `FusedTurnRuntime` / `BackgroundModelAttemptStore` — with **zero** external RSA private key and **zero** valid RSA signature — can call `recovery.background_model_attempts._capture_trusted_response_return(attempt.attempt_id, captured_at=..., directive=forged)` on an `in_doubt` or `dispatching` attempt to mint durable rows in `background_model_response_receipts` and `background_model_return_handoffs`, and then call `recovery.run_turn(...)` to complete and meter the turn with arbitrary caller-chosen directive bytes (`IA17-MINT-001` = `FAIL`, `IA17-OBJGRAPH-001` = `FAIL`).
   - Doing so completely bypasses any bound `LateReturnVerifier` in `background_model_return_verifiers` and **permanently poisons/blocks** the genuine external signer's subsequent valid RSA-signed `attach_late_trusted_return(...)` call (`BackgroundModelResponseConflict: verified late return conflicts with existing durable receipt`).
   - Even when an attempt was dispatched with `late_return_verifier=None` (`C8` / `T6` anonymous/no-verifier dispatch, which must remain permanently `in_doubt / FAIL_CLOSED`), calling `_capture_trusted_response_return(...)` mints a receipt + handoff and completes the turn (`IA17-MINT-002` = `FAIL`).
   - Per Window 15 Adjudication §4.1 & §4.3 (`BLK-W14-001`): Python `_` naming conventions are strictly rejected as a security boundary.

2. **`BLK-W17-002` (`HIGH-CRITICAL` — `RECEIPT_AUTHENTICITY_DOWNGRADE_TO_PUBLIC_CHECKSUM_AND_UNVERIFIED_LEGACY_MIGRATION_LAUNDERING`):**
   - **Unverified Legacy Migration Laundering (Critical Attack C Case 2 — `IA17-MIGRATE-002` = `FAIL`):** In `BackgroundModelAttemptStore._initialize()` (`src/aios_core/runtime/background_attempt.py:613-665`), when `background_model_authenticity_authority` is present on upgrade, the migration iterates over `background_model_response_receipts`, computes a fresh keyless `bgresponse_v2_<sha256>` via `self._receipt_proof(**fields)`, and unconditionally `UPDATE`s `authenticity_proof` in `background_model_response_receipts`, `background_model_return_handoffs`, and `background_model_responses` **without first verifying the pre-upgrade HMAC (`bgresponse_v1_<hmac>`) against `background_model_authenticity_authority.secret_hex` or checking cross-table proof/digest consistency**. As proven by `IA17-MIGRATE-002`, tampered or forged pre-upgrade rows (invalid HMAC, payload/fingerprint modified without the HMAC key, or corrupted handoff proof) that pre-upgrade Core (`0b883c71...`) rejects as `FAIL_CLOSED` are **laundered into valid `bgresponse_v2_<sha256>` trusted state** on startup and executed to completion by `run_turn()`.
   - **Keyless Public Checksum Downgrade (Critical Attack B — `IA17-DOWNGRADE-001` = `FAIL`):** Because `_receipt_proof(**fields)` (`lines 807-817`) is a pure public SHA-256 over public attempt/binding/directive fields, any caller can compute `bgresponse_v2_<sha256>` without any secret key and pass it with `_capture_trusted_response_return` + `stage_exact_response`.

3. **`BLK-W17-003` (`MEDIUM-HIGH` — `RSA_VERIFIER_KEY_ID_COLON_DELIMITER_AMBIGUITY_AND_NEGATIVE_MODULUS_ACCEPTANCE`):**
   - **`key_id` Colon Delimiter Ambiguity (`src/aios_core/runtime/late_return.py:49, 160-165`):** `LateReturnVerifier` allows `":"` in `key_id` (`Field(min_length=1)`), and `mark_dispatching` durably binds such verifiers (e.g., `key_id="provider:key-2026-v1"`). However, `verify_late_return_proof` parses `bglate_rsa_v1:<key_id>:<signature_hex>` via `encoded.split(":", 1)`, splitting on the **first** colon. Thus the extracted `key_id` can never contain `":"`, and **100% of genuine external RSA signatures for any attempt bound to a colon-containing `key_id` are permanently rejected** (`BackgroundModelResponseConflict`), stranding the turn in `in_doubt` (`T5` violation; `IA17-RSA-DELIMITER-001` = `FAIL`).
   - **Negative Hex Modulus Acceptance (`src/aios_core/runtime/late_return.py:51, 56-60`):** `LateReturnVerifier.__init__` checks `int(self.modulus_hex, 16).bit_length() < 2048` without checking `modulus > 0`. In Python, `(-x).bit_length() == x.bit_length()`, so `LateReturnVerifier` accepts negative hex moduli (`modulus_hex="-f0d1..."`), for which `verify_late_return_proof` unconditionally fails (`signature_int >= modulus` is always `True` when `modulus < 0`).

---

## 2. Formal Blocker Specifications (Section 36)

### Blocker 1 — `BLK-W17-001`

- **Blocker ID:** `BLK-W17-001`
- **Title:** `RECOVERY_TRUSTED_RECEIPT_AND_HANDOFF_MINTING_ORACLE_VIA_CAPTURE_HELPER`
- **Severity:** `CRITICAL`
- **Exact Invariants Violated:**
  - `C1` (No Post-Hoc Signing / Trust-Minting Oracle)
  - `C2` (Verifier-Only Recovery)
  - `C3` (Secret Separation)
  - `C8` (Anonymous / Local / No-Verifier Remains `FAIL_CLOSED`)
  - Frozen Security Boundary Constraints `T1`, `T2`, `T3`, `T4`, `T6` (`governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_ACCEPTANCE_FAILURE_ADJUDICATION_2026-10-01.md` §4.1–§4.3, §7.2)
- **Exact Source Path & Lines:**
  - `src/aios_core/runtime/background_attempt.py:807-817` (`BackgroundModelAttemptStore._receipt_proof`)
  - `src/aios_core/runtime/background_attempt.py:2050-2217` (`BackgroundModelAttemptStore._capture_trusted_response_return`)
  - `src/aios_core/runtime/turn_runtime.py:249` (`FusedTurnRuntime.background_model_attempts`)
  - `src/aios_core/runtime/turn_runtime.py:1329-1352` (`FusedTurnRuntime._authenticate_background_model_response`)
- **Frozen Reviewer Probes:**
  - `IA17-MINT-001` (`FAIL`)
  - `IA17-MINT-002` (`FAIL`)
  - `IA17-OBJGRAPH-001` (`FAIL`)
  - File: `reviewer_probes/window17_independent_attack.py` (frozen SHA-256 `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3`)
- **Raw Reproduction Output (`raw/candidate_w17_independent_probes_v3.txt`):**
  ```text
  FAIL | IA17-MINT-001
    expected: recovery caller without external RSA signature cannot mint receipt/handoff or complete in_doubt turn
    actual:   FORGED TURN COMPLETED without RSA signature! response='FORGED_BY_RECOVERY_CALLER_WITHOUT_RSA_PRIVATE_KEY', attempt_state=metered, meters=1, genuine_rsa_return_poisoned=True
  FAIL | IA17-MINT-002
    expected: attempt dispatched with no LateReturnVerifier remains permanently in_doubt / FAIL_CLOSED
    actual:   NO-VERIFIER ATTEMPT BYPASSED FAIL_CLOSED and completed turn with response='FORGED_ON_VERIFIERLESS_ATTEMPT'
  FAIL | IA17-OBJGRAPH-001
    expected: recovery object graph exposes zero trusted-receipt/handoff/proof minting callables
    actual:   REACHABLE TRUST-MINTING CALLABLES FOUND: ['runtime._authenticate_background_model_response', 'runtime.background_model_attempts._capture_trusted_response_return']
  ```
- **Why Author Tests Missed It:**
  Window 16 `CA1` (`tests/integration/test_core_background_late_trusted_return_corrective_001.py:194-216`) only checked `assert not hasattr(attempts, "_issue_external_return_capability")` and `name not in {"sign", "mint", "prove_external_return", "late_return_proof"}`. It never audited or invoked `_capture_trusted_response_return` or `_authenticate_background_model_response` on the post-crash recovery object graph.
- **Mechanically Reproducible:** `YES` (`PYTHONPATH=src python3 reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_001_IA_WINDOW_17/reviewer_probes/window17_independent_attack.py`).

---

### Blocker 2 — `BLK-W17-002`

- **Blocker ID:** `BLK-W17-002`
- **Title:** `RECEIPT_AUTHENTICITY_DOWNGRADE_TO_PUBLIC_CHECKSUM_AND_UNVERIFIED_LEGACY_MIGRATION_LAUNDERING`
- **Severity:** `HIGH-CRITICAL`
- **Exact Invariants Violated:**
  - `C2` (Verifier-Only Recovery — Integrity != Authenticity)
  - `C3` (Secret Separation & Safe Legacy Upgrade without Corruption Normalization)
  - `C7` (Preserve R1–R5 / `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001` Authenticity Guarantees)
- **Exact Source Path & Lines:**
  - `src/aios_core/runtime/background_attempt.py:613-665` (`BackgroundModelAttemptStore._initialize` legacy `background_model_authenticity_authority` migration loop)
  - `src/aios_core/runtime/background_attempt.py:807-817` (`BackgroundModelAttemptStore._receipt_proof`)
  - `src/aios_core/runtime/background_attempt.py:2235-2320` (`BackgroundModelAttemptStore._verify_response_authenticity`)
- **Frozen Reviewer Probes:**
  - `IA17-DOWNGRADE-001` (`FAIL`)
  - `IA17-MIGRATE-002` (`FAIL`)
  - File: `reviewer_probes/window17_independent_attack.py` (frozen SHA-256 `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3`)
- **Raw Reproduction Output (`raw/candidate_w17_independent_probes_v3.txt`):**
  ```text
  FAIL | IA17-DOWNGRADE-001
    expected: authenticity_proof cannot be caller-computed from public fields and minted into staged response without external signer
    actual:   KEYLESS SHA-256 PROOF (bgresponse_v2_64f3fabf9081e9...) computed from public fields and accepted by stage_exact_response
  FAIL | IA17-MIGRATE-002
    expected: tampered pre-upgrade authentication evidence must FAIL_CLOSED and never be normalized into trusted state
    actual:   LAUNDERED TAMPERED PRE-UPGRADE ROWS INTO TRUSTED STATE: subcase_A_invalid_hmac_completed('tampered subcase A invalid HMAC'); subcase_B_tampered_payload_completed('TAMPERED_PRE_UPGRADE_PAYLOAD_WITHOUT_KEY'); subcase_C_corrupted_handoff_proof_completed('handoff proof mismatch subcase C')
  ```
- **Why Author Tests Missed It:**
  `tests/integration/test_core_background_late_trusted_return_secret_upgrade_001.py` inserted dummy rows only into `background_model_return_capabilities` and `background_model_authenticity_authority` with zero rows in `background_model_response_receipts`, `background_model_return_handoffs`, or `background_model_responses`, and never tested tampered pre-upgrade rows.
- **Mechanically Reproducible:** `YES`.

---

### Blocker 3 — `BLK-W17-003`

- **Blocker ID:** `BLK-W17-003`
- **Title:** `RSA_VERIFIER_KEY_ID_COLON_DELIMITER_AMBIGUITY_AND_NEGATIVE_MODULUS_ACCEPTANCE`
- **Severity:** `MEDIUM-HIGH`
- **Exact Invariants Violated:**
  - `C2` (Verifier-Only Recovery)
  - `C6` (Coherent Verifier Lifecycle)
  - Frozen Security Boundary Constraint `T5` (Legitimate External Return Verification Across Restart)
- **Exact Source Path & Lines:**
  - `src/aios_core/runtime/late_return.py:44-66` (`LateReturnVerifier` field & `__init__` validation)
  - `src/aios_core/runtime/late_return.py:160-165` (`verify_late_return_proof` `encoded.split(":", 1)`)
- **Frozen Reviewer Probe:**
  - `IA17-RSA-DELIMITER-001` (`FAIL`)
  - File: `reviewer_probes/window17_independent_attack.py` (frozen SHA-256 `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3`)
- **Raw Reproduction Output (`raw/candidate_w17_independent_probes_v3.txt`):**
  ```text
  FAIL | IA17-RSA-DELIMITER-001
    expected: LateReturnVerifier either rejects colon key_id / negative modulus_hex at construction or verifies legitimate signatures accurately
    actual:   LateReturnVerifier accepted key_id='provider:key-2026-v1' at dispatch, but verify_late_return_proof split(':', 1) permanently rejected genuine signature: exact provider response rejected: late trusted return signature is invalid for this exact attempt, request and response; attempt bgattempt_c4bfe953afe75af5bfee86e54fdaec9d is dispatching; LateReturnVerifier accepted negative modulus_hex (modulus_int < 0, bit_length=2048)
  ```
- **Why Author Tests Missed It:**
  Author tests used a single static `key_id="w16-test-external-key"` (containing no colon) and a single positive hex modulus string.
- **Mechanically Reproducible:** `YES`.

---

## 3. Summary of All 14 Reviewer-Owned Probes (`window17_independent_attack.py`)

| Probe ID | Verdict | Summary |
|---|---|---|
| `IA17-MINT-001` | **`FAIL`** | Post-crash recovery caller without RSA key mints receipt + handoff via `_capture_trusted_response_return`, completes turn, and poisons genuine RSA return (`BLK-W17-001`) |
| `IA17-MINT-002` | **`FAIL`** | Post-crash recovery caller completes a verifier-less (`late_return_verifier=None`) `in_doubt` attempt via `_capture_trusted_response_return` (`BLK-W17-001`) |
| `IA17-DOWNGRADE-001` | **`FAIL`** | Keyless `bgresponse_v2_<sha256>` computed from public fields + `_capture_trusted_response_return` + `stage_exact_response` succeeds without external signer (`BLK-W17-001` / `BLK-W17-002`) |
| `IA17-MIGRATE-001` | `PASS` | Valid pre-upgrade HMAC receipt + handoff recovers exact response once and purges `secret_hex` |
| `IA17-MIGRATE-002` | **`FAIL`** | Tampered pre-upgrade rows (invalid HMAC, tampered payload without key, corrupted handoff proof) are laundered into valid `bgresponse_v2_` state on migration (`BLK-W17-002`) |
| `IA17-VERIFIER-SUB-001` | `PASS` | Direct `LateReturnVerifier` rebinding via `mark_dispatching` or `FusedTurnRuntime(late_return_verifier=...)` is refused |
| `IA17-OBJGRAPH-001` | **`FAIL`** | Reachable trust-minting callables found on recovery object graph (`_capture_trusted_response_return`, `_authenticate_background_model_response`) (`BLK-W17-001`) |
| `IA17-DB-AT-REST-001` | `PASS` | Zero RSA private key material in DB, WAL, SHM, SQL dump, backup, or `src/aios_core/**` |
| `IA17-RSA-001` | `PASS` | Malformed PKCS#1 v1.5 signatures, padding/ASN.1 mutations, `<2048`-bit / even-exponent verifiers, and all 12 field transplants fail closed |
| `IA17-RSA-DELIMITER-001` | **`FAIL`** | `LateReturnVerifier` accepts `key_id` with `:` at dispatch, then `verify_late_return_proof` `split(":", 1)` permanently rejects genuine signatures; negative `modulus_hex` accepted (`BLK-W17-003`) |
| `IA17-RACE-CRASH-001` | `PASS` | Concurrent valid proofs yield 1 winner + 1 refused (`consumed_at` atomic) and 1 metered completion |
| `IA17-NS-ROUTE-B-001` | `PASS` | All post-binding `not_submitted` write sites fail closed (`in_doubt`); genuine pre-submission retry + first real dispatch + late return succeeds |
| `IA17-ID-JSON-001` | `PASS` | Conflicting provider/model/request_id, duplicate JSON keys, and whitespace byte mutations fail closed |
| `IA17-SIGKILL-001` | `PASS` | Reviewer multi-process real `SIGKILL` (`exitcode == -9`) + external RSA signature recovers once with 0 redispatch, 1 meter, 1 output |

---

## 4. Reviewer Environment & Fresh Regression Summary (Sections 26–28)

- **Reviewer Sandbox Environment (`REVIEWER_ENVIRONMENT_DEVIATION` explicitly disclosed):**
  - `CPython 3.11.2` (formal target `3.12.14`)
  - `Pydantic 2.13.5` (exact match)
  - `pytest 8.4.2` (exact match)
  - `SQLite 3.40.1` (formal target `3.45.1`)
  - `OpenSSL 3.0.20 7 Apr 2026` (formal target `3.0.13`)
- **Freshly Executed Suites on `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd`:**
  - Historical Window 14 RED reproduction on `5ad0524c425592210ff184e00ad52abb2c14e366`: `IA14-ORACLE-001 = FAIL`, `IA14-NONCE-001 = FAIL`, `IA14-NS-001 = FAIL` (`probes=7 failures=3`), original `S3 = FAIL` (`failures=2`).
  - Window 17 frozen reviewer probes (`window17_independent_attack.py`): `probes=14, passed=8, failures=6`.
  - Author Route-B + CA1–CA5 + consumption + secret-upgrade (`21` tests): `21 passed`.
  - Author real SIGKILL (`1` test): `1 passed`.
  - Accepted trusted-return (`50` tests): `50 passed`.
  - Focused trusted-return & recovery (`270` tests): `270 passed`.
  - Full Core-domain regression (`811` tests): `811 passed`.
  - Non-Core suites (`tests/c15_persistence`, `tests/preflight` — `209` tests with `C15_SURFACE_BASE=HEAD`): `209 passed`.
  - Per Section 30 governance rule: mechanical regression green (`811` Core + `209` non-Core) never overrides reviewer-owned security and migration blockers (`BLK-W17-001`, `BLK-W17-002`, `BLK-W17-003`).
