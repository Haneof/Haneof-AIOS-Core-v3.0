# WINDOW 17 Independent Acceptance Probe Contract (`PROBE_CONTRACT.md`)

- **Task:** `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE` (`WINDOW 17`)
- **Reviewed Exact Candidate:** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)
- **Construction Base:** `0b883c71d91e5f0772334514925237f1570fa780`
- **Historical Failed Candidate:** `5ad0524c425592210ff184e00ad52abb2c14e366` (`PR #305`)
- **Canonical Window 14 Review:** `84457badc562416f59fb25ca41103700276e0df2`

## Frozen Expected Outcomes Before First Execution

| Probe ID | Attack Surface / Governance Clause | Fixed Expected Outcome |
|---|---|---|
| `IA17-MINT-001` | Critical Attack A (`C1`/`C2`/`C3`/`T1`–`T4`): Post-crash recovery caller without external RSA key invokes `BackgroundModelAttemptStore._capture_trusted_response_return` on an `in_doubt` attempt with bound `LateReturnVerifier` | `FAIL_CLOSED`: must refuse to mint receipt/handoff or complete turn without valid external RSA proof |
| `IA17-MINT-002` | Critical Attack A & §21 (`C1`/`C2`/`C8`/`T6`): Post-crash recovery caller invokes `_capture_trusted_response_return` on an `in_doubt` attempt dispatched with `late_return_verifier=None` | `FAIL_CLOSED`: attempt with no verifier must remain permanently `in_doubt` |
| `IA17-DOWNGRADE-001` | Critical Attack B (`C2`/`C3`): Receipt authenticity downgrade (`_receipt_proof` keyless SHA-256 `bgresponse_v2_<sha256>`) combined with `_capture_trusted_response_return` + `stage_exact_response` | `FAIL_CLOSED`: caller-computable public SHA-256 must not allow forging a staged response without external signer |
| `IA17-MIGRATE-001` | Critical Attack C Case 1 (`C3`/`C7`): Valid pre-upgrade HMAC (`bgresponse_v1_<hmac>`) receipt + handoff recovery across candidate secret-purge migration | `PASS`: valid historical receipt/handoff recovers exact response once and purges `secret_hex` |
| `IA17-MIGRATE-002` | Critical Attack C Case 2 (`C2`/`C3`): Tampered pre-upgrade DB (invalid HMAC proof, tampered payload/fingerprint without HMAC key, corrupted handoff proof) across candidate migration | `FAIL_CLOSED`: tampered pre-upgrade authentication evidence must be rejected and never laundered into valid `bgresponse_v2_` trusted state |
| `IA17-VERIFIER-SUB-001` | Critical Attack D (`C2`/`C6`): Public verifier substitution / rebinding attempts on an `in_doubt` attempt via `mark_dispatching` or `FusedTurnRuntime(late_return_verifier=...)` | `FAIL_CLOSED`: bound verifier cannot be replaced or bypassed by an attacker verifier |
| `IA17-OBJGRAPH-001` | Critical Attack E (`C1`/`C2`/`T1`–`T3`): Recursive Python object-graph audit on post-crash recovery `FusedTurnRuntime` / `BackgroundModelAttemptStore` / `SQLiteWorldStore` | `PASS` iff zero reachable callables on the recovery object graph can mint trusted receipts/handoffs/proofs (`_capture_trusted_response_return`, `_authenticate_background_model_response`, `_issue_external_return_capability`, `late_return_proof`) |
| `IA17-DB-AT-REST-001` | Critical Attack F (`C3`/`T3`): SQLite DB, WAL, SHM, SQL dump, and backup inspection for private RSA key material | `PASS` iff zero private key material is present in DB/WAL/SHM/dump/backup |
| `IA17-RSA-001` | Critical Attack G (`C2`): Adversarial PKCS#1 v1.5 SHA-256 verification matrix & 12-field canonical message transplant checks | `FAIL_CLOSED`: all malformed signatures, padding/ASN.1 mutations, invalid verifier parameters, and 12 field transplants are rejected |
| `IA17-RSA-DELIMITER-001` | Critical Attack G (`C2`/`C6`/`T5`): `LateReturnVerifier` `key_id` colon delimiter ambiguity (`split(":", 1)`) and negative hex modulus validation | `PASS` iff `LateReturnVerifier` either rejects colon `key_id` / negative `modulus_hex` at construction or `verify_late_return_proof` verifies genuine signatures for accepted verifiers |
| `IA17-RACE-CRASH-001` | Critical Attack H (`C6`/`C7`): Concurrent verifier consumption race between two valid signatures from the same key | `PASS` iff exactly 1 accepted + 1 refused and turn completes with 1 meter |
| `IA17-NS-ROUTE-B-001` | §§19–20 (`C4`/`C5`/`C6` Route B + PR #307): All post-binding `not_submitted` write sites fail closed (`in_doubt`); genuine pre-submission retry + late return succeeds | `PASS` iff all post-binding `not_submitted` paths raise `BackgroundModelResponseConflict` (`state == 'in_doubt'`) and pre-submission retry + late return completes once |
| `IA17-ID-JSON-001` | §22 (`C2`/`C7`): Provider/model/request_id conflicts, duplicate top-level/nested JSON keys, and non-canonical whitespace payload mutations | `FAIL_CLOSED`: all identity conflicts, duplicate keys, and byte-form mutations are rejected |
| `IA17-SIGKILL-001` | §23 (`C2`/`C7`/`T5`): Reviewer-owned multi-process real `SIGKILL` after `mark_dispatching` + external RSA signature recovery | `PASS` iff child dies with `-SIGKILL`, fresh process recovers with 0 redispatch, 1 meter, 1 capability effect, 1 output, and blocks replay |
