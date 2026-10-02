# PROBE_FREEZE_MANIFEST

Canonical source: review commit `84457badc562416f59fb25ca41103700276e0df2`

Canonical path:
`reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/reviewer_probes/**`

The RED-first workflow materializes these bytes from the immutable review commit into a detached worktree at failed exact candidate `5ad0524c425592210ff184e00ad52abb2c14e366`, then runs `sha256sum -c` before execution.

| File | Required SHA-256 |
|---|---|
| `window14_independent_attack.py` | `969112b3a13566e30d7cbd4af4e2ecc3299a1cdd9f0f1a62419ef5688d46f181` |
| `window14_s3_stale_capability_rotation.py` | `7c548aca54e22520417adc2841f21093995ded9c311b40915b9d7fc77297b39f` |
| `window14_supplementary_probes.py` | `d4f3a2ce4c465f16a568ebfdb42e48d42002890aba922c05f728d44768708ac6` |
| `PROBE_CONTRACT.md` | `8a3cfe9006225ff121fe2d9abbb90c5bad94b4f79acddbbc674fd499fc67b0c2` |
| `PROBE_REVISION_LOG.md` | `198aebb41d47198c155a553bde00c78dac19d0bec4c7b7eae6178957a95c3b25` |

Expected historical execution:

- `IA14-ORACLE-001` = RED
- `IA14-NONCE-001` = RED
- `IA14-NS-001` = RED
- original S3 = RED, `failures=2`
- supplementary S1/S2 = GREEN

This is immutable historical RED evidence. The original S3 is **not** a Corrective Route-B GREEN gate.
