# BASELINE_RED — RED-first reproduction of all three blockers (C2-8)

RED-first was performed **before** any byte of `src/aios_core/**` was touched, using
the frozen Window 17 probes against the isolated failed candidate.

## Executions

| # | Tree | Command | Exit | Result |
| --- | --- | --- | --- | --- |
| 1 | failed candidate `cb8a6b3c…` (`/home/user/_w19/cand`) | `PYTHONPATH=/home/user/_w19/cand/src python reviewer_probes/window17_independent_attack.py` | 1 | `SUMMARY \| probes=14 failures=6` |
| 2 | carry-forward base `f088ce10…` (pre-fix working tree) | same probe, `PYTHONPATH=/home/user/Haneof-AIOS-Core-v3.0/src` | 1 | `SUMMARY \| probes=14 failures=6` |

Raw logs (byte-for-byte, unmodified):

* `BASELINE_RED_RAW.txt` — run against `cb8a6b3c…`
* `BASELINE_RED_ON_CARRYFORWARD_RAW.txt` — run against the pre-fix carry-forward tree

Run 1 is byte-identical in its probe verdict lines to the Window 17 reviewer log
`raw/candidate_w17_independent_probes_v3.txt`, so the RED is a faithful
reproduction of the failed acceptance, not a new or different failure.

## Reproduced failures (6/14) — mapping to the binding blockers

| Probe | Blocker | Observed on the candidate (verbatim from the raw log) |
| --- | --- | --- |
| `IA17-MINT-001` | `BLK-W17-001` | `FORGED TURN COMPLETED without RSA signature! response='FORGED_BY_RECOVERY_CALLER_WITHOUT_RSA_PRIVATE_KEY', attempt_state=metered, meters=1, genuine_rsa_return_poisoned=True` |
| `IA17-MINT-002` | `BLK-W17-001` | `NO-VERIFIER ATTEMPT BYPASSED FAIL_CLOSED and completed turn with response='FORGED_ON_VERIFIERLESS_ATTEMPT'` |
| `IA17-OBJGRAPH-001` | `BLK-W17-001` | `REACHABLE TRUST-MINTING CALLABLES FOUND: ['runtime._authenticate_background_model_response', 'runtime.background_model_attempts._capture_trusted_response_return']` |
| `IA17-DOWNGRADE-001` | `BLK-W17-002` | `KEYLESS SHA-256 PROOF (bgresponse_v2_64f3fabf9081e9...) computed from public fields and accepted by stage_exact_response` |
| `IA17-MIGRATE-002` | `BLK-W17-002` | `LAUNDERED TAMPERED PRE-UPGRADE ROWS INTO TRUSTED STATE: subcase_A_invalid_hmac_completed(...)`; `subcase_B_tampered_payload_completed(...)`; `subcase_C_corrupted_handoff_proof_completed(...)` |
| `IA17-RSA-DELIMITER-001` | `BLK-W17-003` | `LateReturnVerifier accepted key_id='provider:key-2026-v1' at dispatch, but verify_late_return_proof split(':', 1) permanently rejected genuine signature … ; LateReturnVerifier accepted negative modulus_hex (modulus_int < 0, bit_length=2048)` |

## Probes that were already GREEN on the candidate (preserved, C2-7)

`IA17-MIGRATE-001`, `IA17-VERIFIER-SUB-001`, `IA17-DB-AT-REST-001`,
`IA17-RSA-001`, `IA17-RACE-CRASH-001`, `IA17-NS-ROUTE-B-001`, `IA17-ID-JSON-001`,
`IA17-SIGKILL-001` — these are the Window 16/17 positive properties that
Corrective-002 must not regress; they are re-run unchanged on the Corrective-002
head in `GREEN_RESULTS.md`.

## Honesty notes

* No probe file, probe expectation, `SHA256SUMS` entry or probe contract was
  modified, weakened or deleted in order to obtain GREEN.
* The RED was produced with the local CPython 3.11.2 dev runtime, which is also the
  runtime the reviewer's own raw logs were produced with (the Window 17 reviewer
  environment); the formal 3.12.14 runtime is exercised by the workflow at the
  exact final head (`FORMAL_CI_RESULTS.md`).
