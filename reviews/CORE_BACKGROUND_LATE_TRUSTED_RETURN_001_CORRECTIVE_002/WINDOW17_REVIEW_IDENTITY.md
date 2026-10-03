# WINDOW17_REVIEW_IDENTITY — Fresh Independent Acceptance (Window 17)

| Item | Value |
| --- | --- |
| Review commit | `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8` |
| Review tree | `30ba1a1d74561abb5db13f4ece587836bbc48df2` |
| Review parent | `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (the failed candidate) |
| Verdict | `ACCEPTANCE_FAIL` / `blocker=3` / `DO NOT MERGE` |
| Evidence root | `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_001_IA_WINDOW_17/` (51 files extracted to `/home/user/_w19/w17_review/…`) |
| Frozen probes | `window17_independent_attack.py`, `_v1`, `_v2`, `SHA256SUMS`, `SHA256SUMS_S3`, `SHA256SUMS_SUPPLEMENTARY`, `PROBE_CONTRACT.md`, `PROBE_REVISION_LOG.md`, `PROBE_FREEZE_MANIFEST.md` |
| Final probe revision | v3, SHA-256 `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3` |
| Probe semantics | 14 independent probes, `PASS|FAIL | <id>` lines + `SUMMARY | probes=14 failures=N`, exit 1 on any failure |
| Reviewer raw logs re-read | `raw/candidate_w17_independent_probes_v3.txt`, `raw/candidate_resident_surface_1.txt`, `raw/candidate_resident_surface_base_head_1.txt`, `raw/author_ci_run_37026619012.json`, `raw/author_ci_run_37026619676.json`, `raw/author_ci_run_37026619676_jobs.json` |

## Adjudicated binding blockers (Window 18)

* `BLK-W17-001` (CRITICAL) — `RECOVERY_TRUSTED_RECEIPT_AND_HANDOFF_MINTING_ORACLE_VIA_CAPTURE_HELPER`
  (probes `IA17-MINT-001`, `IA17-MINT-002`, `IA17-OBJGRAPH-001`).
* `BLK-W17-002` (HIGH-CRITICAL) — receipt authenticity downgrade + legacy migration
  laundering (probes `IA17-DOWNGRADE-001`, `IA17-MIGRATE-002`).
* `BLK-W17-003` (MEDIUM-HIGH) — proof/key-id colon ambiguity + negative modulus
  acceptance (probe `IA17-RSA-DELIMITER-001`).

The Window 17 review evidence, its probes, its raw logs and its commit were treated
as immutable: nothing under `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_001_IA_WINDOW_17/`
was modified, and the probes were copied out byte-for-byte for RED-first reuse.
