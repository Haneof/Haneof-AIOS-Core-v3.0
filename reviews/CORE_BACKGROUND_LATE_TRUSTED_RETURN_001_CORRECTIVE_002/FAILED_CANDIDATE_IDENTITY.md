# FAILED_CANDIDATE_IDENTITY — Window 17 candidate `cb8a6b3c…`

The RED-first baseline was executed against the exact failed candidate, extracted
into an isolated directory, never against the working tree and never against
`main`.

| Item | Value |
| --- | --- |
| Candidate commit | `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` |
| Candidate tree | `a762df979826d3a599b93d937c53b633d0cb8466` |
| Candidate parent | `293d32c683033ba27c11059fd021e68342a82c77` |
| Candidate construction base | `0b883c71d91e5f0772334514925237f1570fa780` |
| PR | #308 (state OPEN, never merged, never continued) |
| Isolated checkout | `git archive cb8a6b3c… | tar -x -C /home/user/_w19/cand` (780 files) |
| Raw source snapshot retained for the audit | `/home/user/_w19/cand_background_attempt.py` (byte copy of `cb8a6b3c:src/aios_core/runtime/background_attempt.py`, 2746 lines) |
| Reviewer probes | `/home/user/_w19/cand/reviewer_probes/` (byte-for-byte from `e4161dd0…`) |

## Frozen probe verification at the candidate

```
$ cd /home/user/_w19/cand/reviewer_probes && sha256sum -c SHA256SUMS
… all OK
$ sha256sum window17_independent_attack.py
a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3  window17_independent_attack.py
```

This SHA-256 equals the value recorded by the Window 17 review evidence
(`PROBE_FREEZE_MANIFEST.md` / `PROBE_REVISION_LOG.md`, probe revision v3), so no
`WINDOW17_PROBE_HASH_MISMATCH` was raised.  The probe file was never edited,
renamed, weakened or deleted; no expectation was changed and no failing probe was
removed at any point of this window.

## Candidate source facts relevant to the three blockers (pre-fix)

`src/aios_core/runtime/background_attempt.py` @ `cb8a6b3c…`:

* `BackgroundModelAttemptStore._capture_trusted_response_return(attempt_id, *,
  captured_at, directive, ...)` — accepted only caller-supplied arguments and
  wrote `background_model_response_receipts` + `background_model_return_handoffs`
  with a keyless `bgresponse_v2_…` proof.  Reachable from any caller holding the
  attempt store, including a post-crash recovery caller: the minting oracle of
  `BLK-W17-001`.
* `FusedTurnRuntime._authenticate_background_model_response(...)` — a runtime-level
  callback that could be invoked directly and produced the same keyless proof.
* `authenticity_proof` was a public SHA-256 over public row fields, so
  `stage_exact_response` accepted a caller-computed proof with no external signer
  (`BLK-W17-002` downgrade).
* `_migrate_legacy_authenticity_authority(...)` rewrote legacy `bgresponse_v1_`
  HMAC proofs into the new public fingerprint **without verifying the legacy HMAC**
  or the cross-table scope, so tampered legacy rows were laundered into trusted
  state (`BLK-W17-002` laundering).
* `LateReturnVerifier` accepted `key_id` containing `":"` and accepted a negative
  `modulus_hex`; `verify_late_return_proof` split the proof on the first `":"`,
  so a delimiter-bearing key id was permanently unverifiable at dispatch time
  (`BLK-W17-003`, C2-5/C2-6).

These facts are reproduced by the RED logs (`BASELINE_RED.md`,
`BASELINE_RED_RAW.txt`).
