# RSA Verifier Implementation & Delimiter Attack Audit (`RSA_VERIFIER_ATTACKS.md`)

- **Reviewed Exact Candidate:** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)
- **Audited Source Location:** `src/aios_core/runtime/late_return.py:44-188`

---

## 1. PKCS#1 v1.5 SHA-256 Verification & 12-Field Canonical Binding (`IA17-RSA-001` = `PASS`)

Independent probe `IA17-RSA-001` tested:
- Signature byte-length `-1`, `+1`, and leading-zero hex variants -> rejected (`len(signature) != width`).
- Integer boundaries `signature_int == 0`, `1`, `modulus`, `modulus + 1` -> rejected (`signature_int <= 0 or signature_int >= modulus`).
- Crafted PKCS#1 v1.5 blocks signed with the real private exponent `_RSA_D`:
  - Block type `0x00 0x02 ...` -> rejected.
  - Leading byte `0x01 0x01 ...` -> rejected.
  - Non-`0xff` byte inside PS padding -> rejected.
  - Missing `0x00` separator before `DigestInfo` -> rejected.
  - Flipped ASN.1 `DigestInfo` OID byte -> rejected.
  - Trailing garbage byte after SHA-256 digest (Bleichenbacher-style) -> rejected (`hmac.compare_digest(decoded, expected)` compares the full `width`-byte block).
- `< 2048`-bit modulus and even `public_exponent` -> rejected with `ValueError`.
- Individual transplant of all 12 fields in `late_return_message` (`attempt_id`, `subject_id`, `work_kind`, `work_id`, `model_round_index`, `outbound_request_fingerprint`, `relay_id`, `provider`, `model`, `provider_request_id`, `response_fingerprint`, `payload_sha256`) -> all 12 rejected.

---

## 2. `key_id` Colon Delimiter Ambiguity & Negative Hex Modulus (`IA17-RSA-DELIMITER-001` = `FAIL` / `BLK-W17-003`)

### 2.1 Colon Delimiter Ambiguity in `LateReturnVerifier.key_id` (`src/aios_core/runtime/late_return.py:49, 160-165`)

`LateReturnVerifier` defines:
```python
key_id: str = Field(min_length=1)
```
without forbidding `":"` in `key_id`.

Meanwhile, `verify_late_return_proof` (`late_return.py:160-165`) parses `"bglate_rsa_v1:<key_id>:<signature_hex>"` via:
```python
encoded = proof[len(LATE_RETURN_PROOF_PREFIX) :]
try:
    key_id, signature_hex = encoded.split(":", 1)
except ValueError:
    return False
if key_id != verifier.key_id:
    return False
```

Because `encoded.split(":", 1)` splits on the **first** colon, the parsed `key_id` can **never** contain `":"`.
- When a `LateReturnVerifier` is configured with any namespaced key identifier containing `":"` (e.g. `key_id="provider:key-2026-v1"`, `"kms:rsa:1"`, `"arn:aws:kms:..."`), `LateReturnVerifier(...)`, `FusedTurnRuntime(...)`, and `mark_dispatching(...)` all accept it without error and durably bind `key_id="provider:key-2026-v1"` in `background_model_return_verifiers`.
- After process loss, when the genuine external signer signs the exact provider response and formats `bglate_rsa_v1:provider:key-2026-v1:<sig_hex>`, `verify_late_return_proof` splits at the first colon (`key_id = "provider"`, `signature_hex = "key-2026-v1:<sig_hex>"`), sees `"provider" != "provider:key-2026-v1"`, and **permanently rejects every genuine signature** (`BackgroundModelResponseConflict`), stranding the turn in `in_doubt` (`T5` violation).

### 2.2 Negative Hex Modulus Acceptance (`src/aios_core/runtime/late_return.py:51, 56-60`)

In `LateReturnVerifier.__init__`:
```python
modulus = int(self.modulus_hex, 16)
if modulus.bit_length() < 2048:
    raise ValueError("late return verifier RSA modulus must be at least 2048 bits")
```
In Python, `int("-f0d1...", 16)` is a negative integer whose `.bit_length()` equals `abs(modulus).bit_length()` (`2048`). `LateReturnVerifier` therefore accepts negative hex strings (`modulus_hex="-f0d1..."`), and `verify_late_return_proof` then unconditionally fails because `signature_int >= modulus` is always `True` when `modulus < 0`.
