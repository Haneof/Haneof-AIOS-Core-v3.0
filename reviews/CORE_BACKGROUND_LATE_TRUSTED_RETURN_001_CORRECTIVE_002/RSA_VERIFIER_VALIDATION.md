# RSA_VERIFIER_VALIDATION — canonical proof/key-id contract (`C2-5`, `C2-6`)

Frozen encoding (`src/aios_core/runtime/late_return.py`):

```
proof      := "bglate_rsa_v1:" key_id ":" signature_hex
key_id     := [A-Za-z0-9][A-Za-z0-9._-]{0,127}          # 1..128 chars, ":" impossible
signature  := lowercase hex, no prefix, no whitespace
modulus_hex:= "^(0|[1-9a-f][0-9a-f]*)$"                 # canonical normalized lowercase
requires      modulus > 0, modulus odd, modulus.bit_length() >= 2048,
              f"{modulus:x}" == modulus_hex
public_exp := int (bool excluded), > 1, odd, < modulus
algorithm  := "rsa-pkcs1v15-sha256"
```

`canonical_late_return_proof()` mechanically checks `encode → decode → identical
key_id` (and identical signature) before returning, so an allowed id can never be
accepted at construction and then be permanently unverifiable at verification time.
`decode_late_return_proof()` additionally refuses any `":"` inside the signature
segment, so an ambiguous encoding cannot silently re-associate a signature with a
different key id.

## Evidence

| Item | Where |
| --- | --- |
| Colon-bearing, empty, padded, whitespace, control, unicode, over-length and non-canonical key ids are refused **at construction** (before any durable binding) | `tests/runtime/test_late_return_canonical_encoding_002.py::test_ca2_010_ambiguous_or_non_canonical_key_id_refused_at_construction` |
| Accepted ids round-trip exactly (`k`, `provider-key-2026-v1`, `provider.key_2026.v1`, `A1`, `0`, `0x-prefixed`, 128 × `x`) | same test |
| Negative / zero / even / undersized / leading-zero / uppercase / prefixed / signed / whitespace / malformed-hex moduli refused | `test_ca2_011_invalid_modulus_refused_before_durable_binding` |
| Exponent `-65537, -1, 0, 1, 2, 4, 6, 65536, N, N+2`, `None`, `3.0`, `True` refused; algorithm must be exactly `rsa-pkcs1v15-sha256` | `test_ca2_012_…`, `test_ca2_013_…` |
| Genuine external RSA-2048 signature verifies; all 12 field transplants fail | `test_ca2_014_…` / frozen probe `IA17-RSA-001` |
| The original defect is gone end-to-end (colon key id at dispatch + negative modulus accepted) | frozen probe `IA17-RSA-DELIMITER-001` → PASS |
| 2048-bit odd modulus, e = 65537, real `pow(...)` verification path exercised with an independent in-process key pair (no Core signing helper) | `tests/runtime/test_late_return_canonical_encoding_002.py` (inline `_RSA_N`/`_RSA_D`, `_SHA256_DER`, `rsa_sign`) |

## Notes

* The key pair used by the new matrix is generated/embedded independently of Core
  and of the frozen W17 probe material; the private exponent never appears in
  `src/aios_core`.
* `LateReturnVerifier` is `frozen=True, extra="forbid"`, so a durable row cannot
  carry additional uncontrolled fields.
* Verifier rows are re-validated through the model on load
  (`attach_late_trusted_return`), and non-canonical durable rows raise
  `LateReturnVerifierError` / `BackgroundModelResponseConflict` instead of being
  coerced.
* Minimum modulus strength is enforced as 2048 bits; a verifier that cannot verify
  a genuine signature can no longer be durably bound.
