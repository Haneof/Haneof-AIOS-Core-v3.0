# Durable Trust-Minting Path Audit (`TRUST_MINT_PATH_AUDIT.md`)

- **Reviewed Exact Candidate:** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)
- **Audit Scope:** Every method and SQL write site in `src/aios_core/**` capable of creating, mutating, or recovering durable trust facts (`background_model_response_receipts`, `background_model_return_handoffs`, `background_model_responses`, `response_returned`, `background_model_return_verifiers`).

---

## 1. Complete Enumeration of Durable Trust Write Sites

| Durable Table / State | Write Method | Source Location | Preconditions Checked | External RSA Signature Required? | Audit Verdict |
|---|---|---|---|---|---|
| `background_model_response_receipts` (`INSERT OR IGNORE`) | `BackgroundModelAttemptStore.attach_late_trusted_return` | `src/aios_core/runtime/background_attempt.py:1935-1950` | `attempt.state in _STAGABLE_STATES`, origin binding match, `verify_late_return_proof` == `True` | **YES** | `SAFE` |
| `background_model_response_receipts` (`INSERT OR IGNORE`) | `BackgroundModelAttemptStore._capture_trusted_response_return` | `src/aios_core/runtime/background_attempt.py:2050-2152` | `attempt.state in {"dispatching", "in_doubt", "response_returned", "metered"}` and origin binding exists (`require_relay_echo=False`) | **NO** | **`FAIL / CRITICAL BLOCKER (BLK-W17-001)`** |
| `background_model_response_receipts` (`UPDATE SET authenticity_proof=?`) | `BackgroundModelAttemptStore._initialize` | `src/aios_core/runtime/background_attempt.py:613-647` | `background_model_authenticity_authority` table exists; **does NOT verify legacy HMAC before overwriting** | **NO** | **`FAIL / HIGH-CRITICAL BLOCKER (BLK-W17-002)`** |
| `background_model_return_handoffs` (`INSERT OR IGNORE`) | `BackgroundModelAttemptStore.attach_late_trusted_return` | `src/aios_core/runtime/background_attempt.py:1984-1997` | Verified RSA proof via `verify_late_return_proof` | **YES** | `SAFE` |
| `background_model_return_handoffs` (`INSERT OR IGNORE`) | `BackgroundModelAttemptStore._capture_trusted_response_return` | `src/aios_core/runtime/background_attempt.py:2195-2201` | Same as above: accepts `dispatching`/`in_doubt`, computes keyless `bgresponse_v2_<sha256>`, ignores `background_model_return_verifiers` | **NO** | **`FAIL / CRITICAL BLOCKER (BLK-W17-001)`** |
| `background_model_return_handoffs` (`UPDATE SET authenticity_proof=?`) | `BackgroundModelAttemptStore._initialize` | `src/aios_core/runtime/background_attempt.py:648-654` | Overwrites `authenticity_proof` without verifying legacy HMAC or prior match | **NO** | **`FAIL / HIGH-CRITICAL BLOCKER (BLK-W17-002)`** |
| `background_model_responses` (`INSERT OR IGNORE`) | `BackgroundModelAttemptStore.stage_exact_response` | `src/aios_core/runtime/background_attempt.py:2488-2504` | Requires pre-existing row in `background_model_response_receipts` matching `_receipt_proof` (`bgresponse_v2_<sha256>`) | Indirectly bypassed via `_capture_trusted_response_return` | **`BYPASSED VIA BLK-W17-001 / BLK-W17-002`** |
| `background_model_responses` (`UPDATE SET authenticity_proof=?`) | `BackgroundModelAttemptStore._initialize` | `src/aios_core/runtime/background_attempt.py:656-662` | Overwrites `authenticity_proof` without verifying legacy HMAC | **NO** | **`FAIL / HIGH-CRITICAL BLOCKER (BLK-W17-002)`** |
| `background_model_attempts.state = 'response_returned'` | `BackgroundModelAttemptStore.stage_exact_response` & `record_response` | `src/aios_core/runtime/background_attempt.py:1441-1452, 2538-2554` | Requires receipt row (when `has_recoverable_identity=True`) | Bypassed once `_capture_trusted_response_return` mints receipt | **`BYPASSED VIA BLK-W17-001`** |
| `background_model_return_verifiers` (`INSERT`) | `BackgroundModelAttemptStore.mark_dispatching` | `src/aios_core/runtime/background_attempt.py:1131-1151` | `state == 'admitted'` and zero `_durable_submission_artifacts` | N/A (first dispatch only) | `SAFE` (cannot rebind post-dispatch, though bypassed by `_capture_trusted_response_return`) |

---

## 2. Detailed Analysis of `BLK-W17-001`: `_capture_trusted_response_return` & `_authenticate_background_model_response`

In `src/aios_core/runtime/background_attempt.py:807-817`, the candidate replaced the keyed HMAC receipt authenticator (`bgresponse_v1_<hmac>`) with a **keyless public SHA-256 checksum**:

```python
    @classmethod
    def _receipt_proof(cls, **fields: object) -> str:
        """Integrity fingerprint for a Core-owned durable receipt row.

        This is deliberately not authentication authority.  Authenticity comes
        from where the row was created: either the live trusted return boundary,
        or a verified external RSA late-return proof.  Recovery can recompute this
        checksum but cannot create a missing receipt row through any API.
        """

        digest = hashlib.sha256(cls._receipt_message(**fields)).hexdigest()
        return f"bgresponse_v2_{digest}"
```

However, `BackgroundModelAttemptStore._capture_trusted_response_return(self, attempt_id: str, *, captured_at: datetime, directive: ModelDirective)` (`lines 2050-2217`) is mounted directly on the ordinary recovery-facing `runtime.background_model_attempts` instance (and wrapped by `FusedTurnRuntime._authenticate_background_model_response`, `turn_runtime.py:1329-1352`).

Inside `_capture_trusted_response_return`:
1. Lines `2085-2090` explicitly accept `attempt.state in {"dispatching", "in_doubt", "response_returned", "metered"}`.
2. Lines `2104-2121` require only that a `background_model_request_bindings` row exists (`require_relay_echo=False`).
3. It performs **zero** check on `background_model_return_verifiers` and requires **zero** external RSA signature.
4. Lines `2137-2201` compute `proof = self._receipt_proof(**receipt_fields)` (`bgresponse_v2_<sha256>`) and insert durable rows into both `background_model_response_receipts` and `background_model_return_handoffs`.

Consequently:
- **Probe `IA17-MINT-001` (`FAIL`):** On a post-crash `in_doubt` attempt that has a bound `LateReturnVerifier`, an ordinary recovery caller with **no RSA private key** and **no external signature** calls `recovery.background_model_attempts._capture_trusted_response_return(attempt.attempt_id, captured_at=..., directive=forged)` and then `recovery.run_turn(...)`. The turn completes (`state='metered'`, `1` meter, `response='FORGED_BY_RECOVERY_CALLER_WITHOUT_RSA_PRIVATE_KEY'`), and the unauthenticated receipt permanently blocks the genuine external RSA-signed return (`genuine_rsa_return_poisoned=True`)!
- **Probe `IA17-MINT-002` (`FAIL`):** On a post-crash `in_doubt` attempt dispatched with `late_return_verifier=None` (where C8 / `T6` requires permanent `in_doubt / FAIL_CLOSED`), calling `_capture_trusted_response_return` mints a receipt + handoff and completes the turn (`response='FORGED_ON_VERIFIERLESS_ATTEMPT'`).
- **Probe `IA17-OBJGRAPH-001` (`FAIL`):** Recursive object-graph inspection of post-crash `FusedTurnRuntime` locates both `runtime.background_model_attempts._capture_trusted_response_return` and `runtime._authenticate_background_model_response`.
