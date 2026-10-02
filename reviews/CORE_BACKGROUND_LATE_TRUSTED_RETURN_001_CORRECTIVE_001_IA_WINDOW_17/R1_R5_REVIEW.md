# R1–R5 & Accepted Trusted-Return Regression Review (`R1_R5_REVIEW.md`)

- **Reviewed Exact Candidate:** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)

## 1. Mechanical Execution of R1–R5 & Focused Suites

Freshly executed in the reviewer sandbox against `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`raw/candidate_accepted_trusted_return_50.txt` and `raw/candidate_focused_270.txt`):
- Accepted trusted-return suite (`50` tests): `50 passed, 0 failed`.
- Focused recovery + R1–R5 + Route-B + CA1–CA5 suite (`270` tests): `270 passed, 0 failed`.
- Full Core-domain suite (`tests/unit`, `tests/integration`, `tests/runtime`, `tests/habitation` — `811` tests): `811 passed, 0 failed` (`raw/candidate_full_core_811.txt`).

## 2. Security Regression in Accepted R3/R4 Receipt Authenticity (`BLK-W17-001` & `BLK-W17-002`)

While the mechanical R1–R5 replay tests pass, candidate `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` regressed the security guarantee of `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001` in two ways:
1. It replaced the HMAC-SHA256 receipt authenticator (`bgresponse_v1_<hmac>`) with a keyless public SHA-256 checksum (`bgresponse_v2_<sha256>`) while keeping `BackgroundModelAttemptStore._capture_trusted_response_return(...)` accessible on `runtime.background_model_attempts` for `dispatching` and `in_doubt` attempts (`BLK-W17-001`).
2. Its `_initialize()` migration overwrites pre-upgrade `authenticity_proof` values with freshly computed `bgresponse_v2_<sha256>` checksums without verifying the pre-upgrade HMAC (`BLK-W17-002`).
