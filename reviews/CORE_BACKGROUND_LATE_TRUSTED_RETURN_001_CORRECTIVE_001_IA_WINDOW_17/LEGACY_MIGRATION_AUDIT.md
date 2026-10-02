# Legacy Secret Migration & Corruption Laundering Audit (`LEGACY_MIGRATION_AUDIT.md`)

- **Reviewed Exact Candidate:** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)
- **Audited Source Location:** `src/aios_core/runtime/background_attempt.py:582-674` (`BackgroundModelAttemptStore._initialize`)

---

## 1. Case 1 — Valid Pre-Upgrade HMAC Receipt & Handoff (`IA17-MIGRATE-001` = `PASS`)

When a pre-upgrade SQLite database created under accepted `main` (`0b883c71d91e5f0772334514925237f1570fa780`) contains:
- `background_model_authenticity_authority` (`authority_id='trusted-return-v1'`, 32-byte `secret_hex`),
- `background_model_attempts` (`in_doubt` / `dispatching`),
- `background_model_request_bindings`,
- valid HMAC-authenticated `background_model_response_receipts` (`bgresponse_v1_<valid_hmac>`), and
- valid `background_model_return_handoffs` (`bgresponse_v1_<valid_hmac>`),

opening `BackgroundModelAttemptStore` in candidate `cb8a6b3c...`:
1. Enables `PRAGMA secure_delete = ON`,
2. Rewrites `authenticity_proof` in `background_model_response_receipts`, `background_model_return_handoffs`, and `background_model_responses` to `bgresponse_v2_<sha256>`,
3. Deletes and drops `background_model_authenticity_authority` (and `background_model_return_capabilities` if present),
4. Checkpoints the WAL via `PRAGMA wal_checkpoint(TRUNCATE)` so the legacy secret bytes do not remain in the DB file, WAL, or SQL dump, and
5. Allows `FusedTurnRuntime.run_turn(...)` to recover the exact response once without provider redispatch (`IA17-MIGRATE-001` = `PASS`).

---

## 2. Case 2 — Tampered Pre-Upgrade Database Normalization / Laundering (`IA17-MIGRATE-002` = `FAIL` / `BLK-W17-002`)

Look at `src/aios_core/runtime/background_attempt.py:613-665`:

```python
            if legacy_authority is not None:
                rows = conn.execute(
                    "SELECT * FROM background_model_response_receipts"
                ).fetchall()
                for receipt_row in rows:
                    fields = {
                        "attempt_id": receipt_row["attempt_id"],
                        "subject_id": receipt_row["subject_id"],
                        "work_kind": receipt_row["work_kind"],
                        "work_id": receipt_row["work_id"],
                        "model_round_index": int(receipt_row["model_round_index"]),
                        "outbound_request_fingerprint": receipt_row[
                            "outbound_request_fingerprint"
                        ],
                        "relay_id": receipt_row["relay_id"],
                        "provider": receipt_row["provider"],
                        "model": receipt_row["model"],
                        "provider_request_id": receipt_row["provider_request_id"],
                        "response_fingerprint": receipt_row["response_fingerprint"],
                        "payload_sha256": receipt_row["payload_sha256"],
                    }
                    proof = self._receipt_proof(**fields)
                    attempt_id = receipt_row["attempt_id"]
                    conn.execute(
                        """
                        UPDATE background_model_response_receipts
                        SET authenticity_proof=?
                        WHERE attempt_id=?
                        """,
                        (proof, attempt_id),
                    )
                    conn.execute(
                        """
                        UPDATE background_model_return_handoffs
                        SET authenticity_proof=?
                        WHERE attempt_id=?
                        """,
                        (proof, attempt_id),
                    )
                    conn.execute(
                        """
                        UPDATE background_model_responses
                        SET authenticity_proof=?
                        WHERE attempt_id=?
                        """,
                        (proof, attempt_id),
                    )
                conn.execute("DELETE FROM background_model_authenticity_authority")
                conn.execute("DROP TABLE background_model_authenticity_authority")
```

### Critical Defect (`BLK-W17-002`)

Before overwriting `authenticity_proof` in all three tables with the new keyless SHA-256 checksum (`bgresponse_v2_<sha256>`) and deleting `background_model_authenticity_authority`, `_initialize()` **never verifies the existing pre-upgrade HMAC (`bgresponse_v1_<hmac>`) against `background_model_authenticity_authority.secret_hex`**, nor does it verify that `background_model_return_handoffs.authenticity_proof` or `background_model_responses.authenticity_proof` matched the receipt's valid HMAC!

Reviewer probe `IA17-MIGRATE-002` mechanically proved all three corruption-laundering subcases:
1. **Subcase A (`subcase_A_invalid_hmac_completed`):** Pre-upgrade receipt and handoff had a forged/invalid `authenticity_proof = "bgresponse_v1_" + "00"*32`. Pre-upgrade Core (`0b883c71...`) rejects this with `BackgroundModelResponseConflict("trusted provider-return receipt authenticator is invalid")`. Candidate `_initialize()` overwrote `authenticity_proof` with a valid `bgresponse_v2_<sha256>` and `run_turn()` completed with `'tampered subcase A invalid HMAC'`.
2. **Subcase B (`subcase_B_tampered_payload_completed`):** Pre-upgrade receipt `response_fingerprint`/`payload_sha256` and handoff `directive_payload`/`payload_sha256` were modified to `'TAMPERED_PRE_UPGRADE_PAYLOAD_WITHOUT_KEY'` without updating the HMAC. Pre-upgrade Core rejects this as `FAIL_CLOSED`. Candidate `_initialize()` computed a fresh `bgresponse_v2_<sha256>` over the tampered columns and `run_turn()` completed with `'TAMPERED_PRE_UPGRADE_PAYLOAD_WITHOUT_KEY'`.
3. **Subcase C (`subcase_C_corrupted_handoff_proof_completed`):** Pre-upgrade `background_model_return_handoffs.authenticity_proof` was corrupted to `'CORRUPTED_HANDOFF_PROOF'`. Pre-upgrade Core rejects this with `BackgroundModelResponseConflict("supplied provider-return authenticity proof is invalid")`. Candidate `_initialize()` overwrote `background_model_return_handoffs.authenticity_proof` with the receipt's new `bgresponse_v2_<sha256>` and `run_turn()` completed with `'handoff proof mismatch subcase C'`.

### Why Author Tests Missed It

`tests/integration/test_core_background_late_trusted_return_secret_upgrade_001.py` only created dummy `background_model_return_capabilities` and `background_model_authenticity_authority` tables with **zero rows** in `background_model_response_receipts`, `background_model_return_handoffs`, or `background_model_responses`. It never tested pre-upgrade receipt validation or tampered pre-upgrade rows.
