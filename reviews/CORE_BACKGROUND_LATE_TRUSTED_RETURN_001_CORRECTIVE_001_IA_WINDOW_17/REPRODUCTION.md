# Mechanical Reproduction Guide (`REPRODUCTION.md`)

## 1. Reproduce Historical Window 14 RED on Failed Candidate `5ad0524c425592210ff184e00ad52abb2c14e366`

```bash
git worktree add --detach /tmp/w17-failed 5ad0524c425592210ff184e00ad52abb2c14e366
git archive 84457badc562416f59fb25ca41103700276e0df2 \
  reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/reviewer_probes | tar -x -C /tmp/w17-failed
cd /tmp/w17-failed
sha256sum -c reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/reviewer_probes/SHA256SUMS
sha256sum -c reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/reviewer_probes/SHA256SUMS_S3
PYTHONPATH=src python3 reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/reviewer_probes/window14_independent_attack.py
PYTHONPATH=src python3 reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/reviewer_probes/window14_s3_stale_capability_rotation.py
```

Expected and observed (`raw/historical_w14_red_on_5ad0524c.txt`):
- `FAIL | IA14-ORACLE-001`
- `FAIL | IA14-NONCE-001`
- `FAIL | IA14-NS-001`
- `SUMMARY | probes=7 failures=3`
- `S3`: `SUMMARY | failures= 2`

---

## 2. Reproduce Window 17 Frozen Reviewer Probes on Candidate `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd`

```bash
git checkout cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd
sha256sum -c reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_001_IA_WINDOW_17/reviewer_probes/SHA256SUMS
PYTHONPATH=src python3 reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_001_IA_WINDOW_17/reviewer_probes/window17_independent_attack.py
```

Expected and observed (`raw/candidate_w17_independent_probes_v3.txt`):
- `FAIL | IA17-MINT-001` (`BLK-W17-001`)
- `FAIL | IA17-MINT-002` (`BLK-W17-001`)
- `FAIL | IA17-DOWNGRADE-001` (`BLK-W17-001` / `BLK-W17-002`)
- `PASS | IA17-MIGRATE-001`
- `FAIL | IA17-MIGRATE-002` (`BLK-W17-002`)
- `PASS | IA17-VERIFIER-SUB-001`
- `FAIL | IA17-OBJGRAPH-001` (`BLK-W17-001`)
- `PASS | IA17-DB-AT-REST-001`
- `PASS | IA17-RSA-001`
- `FAIL | IA17-RSA-DELIMITER-001` (`BLK-W17-003`)
- `PASS | IA17-RACE-CRASH-001`
- `PASS | IA17-NS-ROUTE-B-001`
- `PASS | IA17-ID-JSON-001`
- `PASS | IA17-SIGKILL-001`
- `SUMMARY | probes=14 failures=6` (`exit_code=1`)
