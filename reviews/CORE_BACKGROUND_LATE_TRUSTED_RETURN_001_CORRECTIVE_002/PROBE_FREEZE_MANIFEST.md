# PROBE_FREEZE_MANIFEST — Window 17 frozen probes as RED-first harness

The reviewer probes were **extracted from the review commit**, never edited.  They
are the RED-first harness for Corrective-002: the candidate must be shown to fail
them, and the Corrective-002 head must be shown to pass them unchanged.

## Provenance

| Item | Value |
| --- | --- |
| Source commit | `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8` |
| Source path | `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_001_IA_WINDOW_17/reviewer_probes/` |
| Extraction command | `git archive e4161dd0… <path> \| tar -x -C /home/user/_w19/cand` |
| Local path | `/home/user/_w19/cand/reviewer_probes/` |
| Integrity | `sha256sum -c SHA256SUMS`, `SHA256SUMS_S3`, `SHA256SUMS_SUPPLEMENTARY` → all OK |
| Final probe file | `window17_independent_attack.py` |
| Final probe SHA-256 (v3) | `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3` |
| Earlier revisions retained | `window17_independent_attack_v1.py`, `window17_independent_attack_v2.py` |
| Contract / history | `PROBE_CONTRACT.md`, `PROBE_REVISION_LOG.md`, `PROBE_FREEZE_MANIFEST.md` |

## Probe inventory (14 probes, all required)

| Probe | Adjudicated meaning |
| --- | --- |
| `IA17-MINT-001` | recovery caller without external RSA signature cannot mint receipt/handoff or complete an `in_doubt` turn |
| `IA17-MINT-002` | attempt dispatched with **no** `LateReturnVerifier` stays permanently `in_doubt` / FAIL_CLOSED |
| `IA17-DOWNGRADE-001` | `authenticity_proof` cannot be caller-computed from public fields and minted into a staged response without the external signer |
| `IA17-MIGRATE-001` | valid pre-upgrade HMAC receipt/handoff recovers the exact response and purges the legacy secret |
| `IA17-MIGRATE-002` | tampered pre-upgrade authentication evidence must FAIL_CLOSED and never be normalised into trusted state |
| `IA17-VERIFIER-SUB-001` | bound verifier cannot be substituted or rebound |
| `IA17-OBJGRAPH-001` | recovery object graph exposes zero trusted-receipt/handoff/proof minting callables |
| `IA17-DB-AT-REST-001` | no RSA private key material in DB/WAL/SHM/dump/backup |
| `IA17-RSA-001` | malformed PKCS#1 v1.5 signatures and all 12 field transplants fail closed |
| `IA17-RSA-DELIMITER-001` | verifier either rejects colon key id / negative modulus at construction or verifies genuine signatures accurately |
| `IA17-RACE-CRASH-001` | concurrent valid proofs → 1 accepted + 1 refused, 1 metered completion |
| `IA17-NS-ROUTE-B-001` | post-binding `not_submitted` refused; pre-submission retry + late return succeeds |
| `IA17-ID-JSON-001` | provider/model/request_id conflicts, duplicate JSON keys, non-canonical byte mutations fail closed |
| `IA17-SIGKILL-001` | real SIGKILL child + external RSA signature recovers the turn exactly once with 0 redispatch |

## Invocation contract used for both RED and GREEN

```
PYTHONPATH=<candidate-tree>/src /home/user/.local/venv311/bin/python \
    /home/user/_w19/cand/reviewer_probes/window17_independent_attack.py
```

Exit code 0 ⇔ `SUMMARY | probes=14 failures=0`.  The harness was run with
`sys.path` pointing at the candidate/Corrective-002 `src` tree; no probe file was
copied into the repository and no probe was modified to obtain a GREEN.
