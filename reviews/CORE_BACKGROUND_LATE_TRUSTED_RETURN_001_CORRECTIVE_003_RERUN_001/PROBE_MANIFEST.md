# PROBE_MANIFEST — Window 22-RERUN-001

All three frozen reviewer probe suites were **fresh-extracted from canonical review commits in
the GitHub object graph** and hash-verified before first execution, per contract §12 / §13.
No old local copy was used as an authoritative source.

Extraction method (byte source is the git blob at the canonical review commit, never a working
tree file and never a prior sandbox copy):

```
git cat-file blob <blob-sha> > <probe>.py
```

---

## 1. Suite A — Window 20 independent attack (RED-first anchor)

| item | value |
|---|---|
| canonical source review commit | `220311759e88fb3948ad3f4dba655058e0f392a8` |
| path at that commit | `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002_IA_WINDOW_20/reviewer_probes/window20_independent_attack.py` |
| expected git blob | `527edd8d92243cabc417f176c0f7c4f6c358e65c` |
| actual git blob (`git ls-tree`) | `527edd8d92243cabc417f176c0f7c4f6c358e65c` — **MATCH** |
| expected SHA-256 | `ec1dc5c2c5406d5d9e74825f62e0a17fb80f8ebd6dc250817fa048511ce292b5` |
| actual SHA-256 of extracted bytes | `ec1dc5c2c5406d5d9e74825f62e0a17fb80f8ebd6dc250817fa048511ce292b5` — **MATCH** |
| size | 28246 bytes, 729 lines |
| probe ids | `IA20-MINT-003`, `IA20-MINT-004`, `IA20-OBJGRAPH-002`, `IA20-WINDOW-001` |
| summary line format | `SUMMARY | probes=4 failures=<n>` |

No `WINDOW20_PROBE_HASH_MISMATCH`.

Sibling blobs at the same path that were deliberately **not** used (they are the reviewer's own
superseded/defective drafts, listed here so the choice is auditable):
`window20_independent_attack_v1.py` (`b1ad43619eea38c5b5b14bb09161f4950c7ace4f`),
`window20_independent_attack_v2_defective.py` (`224135e373dfa0ca106dbb5b17d0fc17d2249872`).

## 2. Suite B — Window 20 migration / RSA positive baseline

| item | value |
|---|---|
| canonical source review commit | `220311759e88fb3948ad3f4dba655058e0f392a8` |
| path at that commit | `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002_IA_WINDOW_20/reviewer_probes/window20_migration_rsa_attack.py` |
| expected git blob | `867f0ee993595c2d334a3940ad66308166693c97` |
| actual git blob | `867f0ee993595c2d334a3940ad66308166693c97` — **MATCH** |
| expected SHA-256 | `769242465817f31734661ba7ba9c3d5f7d06b8d3f5235d72d2026956d9b98eb1` |
| actual SHA-256 | `769242465817f31734661ba7ba9c3d5f7d06b8d3f5235d72d2026956d9b98eb1` — **MATCH** |
| size | 48027 bytes, 1157 lines |
| probe ids | `IA20-MIGRATE-003`, `IA20-MIGRATE-004`, `IA20-RSA-ENC-001`, `IA20-RSA-PARAM-001`, `IA20-RSA-TRANSPLANT-001`, `IA20-NOTSUB-002`, `IA20-EXACTONCE-001` |
| summary line format | `SUMMARY | probes=7 failures=<n>` |

Not used: `window20_migration_rsa_attack_v1_defective.py` (`22c8455bc81054d71eaef1dda6f7bc4c9db59d46`),
`window20_migration_rsa_attack_v2.py` (`5ad3530733293f8c12842a4f01bf932f899e8739`).

## 3. Window 17 independent attack (historical positive requirement)

| item | value |
|---|---|
| canonical source review commit | `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8` |
| path at that commit | `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_001_IA_WINDOW_17/reviewer_probes/window17_independent_attack.py` |
| git blob at that commit | `bb25d184a5cb813ae4058de9a75fa23d9591b041` |
| expected SHA-256 | `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3` |
| actual SHA-256 | `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3` — **MATCH** |
| size | 58971 bytes, 1511 lines |
| probe ids | `IA17-MINT-001`, `IA17-MINT-002`, `IA17-DOWNGRADE-001`, `IA17-MIGRATE-001`, `IA17-MIGRATE-002`, `IA17-VERIFIER-SUB-001`, `IA17-OBJGRAPH-001`, `IA17-DB-AT-REST-001`, `IA17-RSA-001`, `IA17-RSA-DELIMITER-001`, `IA17-RACE-CRASH-001`, `IA17-NS-ROUTE-B-001`, `IA17-ID-JSON-001`, `IA17-SIGKILL-001` |
| summary line format | `SUMMARY | probes=14 failures=<n>` |

No `WINDOW17_PROBE_HASH_MISMATCH`.

Not used: `window17_independent_attack_v1.py` (`0dc5546f12d2d4f88657ad2a7767a2f4bda7b8d6`),
`window17_independent_attack_v2.py` (`9a7105aa613ef57a7612918311ff9d5024ff6a9b`).

Retrieval disclosure: `e4161dd0…` was not reachable from the shallow sandbox clone until an
explicit `git fetch origin e4161dd0ad0a2f825461311a1c8c5ff8234a07f8`. GitHub confirmed the commit
server-side (`gh api repos/.../commits/e4161dd0…` →
`docs(reviews): publish Window 17 Fresh IA review evidence for PR #308 (ACCEPTANCE_FAIL /
blocker=3 / DO NOT MERGE)`, committed `2026-10-02T16:35:39Z`). It is also the tip of remote ref
`refs/heads/arena/01a0fd4d-haneof-aios-core-v3-0`. This is a local clone-depth artifact, not
remote absence and not identity drift.

## 4. C3-6 compliance — reviewer probe bytes are NOT modified

The three frozen probes are executed **in place from the extracted bytes** and are never copied
into the repository, never edited, never wrapped and never re-ordered:

- they are not added to the tracked tree of this branch;
- the formal workflow re-extracts them from the pinned canonical review commits at CI runtime and
  re-verifies the same blob ids and SHA-256 values before executing them;
- probe verdicts are consumed only from their own `SUMMARY | probes=N failures=M` line.

`C3-6 SATISFIED — reviewer probe bytes unchanged.`

## 5. How each suite is executed

```
PYTHONPATH=<candidate>/src python <extracted-probe>.py
```

Each probe module is a standalone script with a `main()` that prints one
`PASS|FAIL | <probe-id>` block per probe plus the final `SUMMARY` line, and exits non-zero if any
probe failed. No pytest, no candidate-side helper and no candidate-side signing key is used by
Suite A / Suite B / W17 — the only RSA material in them is the reviewer-owned key embedded in the
probe bytes.

## 6. Raw outputs stored in this evidence package

| file | what it is |
|---|---|
| `raw/RED_SUITE_A_ON_FAILED_CANDIDATE_fec30bd.txt` | Suite A on materialized `fec30bd` — `probes=4 failures=4` |
| `raw/RED_SUITE_A_ON_CARRY_FORWARD_BASE.txt` | Suite A on `BYTE_EXACT_CARRY_FORWARD_BASE` — `probes=4 failures=4` |
| `raw/POSITIVE_SUITE_B_ON_FAILED_CANDIDATE_fec30bd.txt` | Suite B on `fec30bd` — `probes=7 failures=0` |
| `raw/POSITIVE_W17_ON_FAILED_CANDIDATE_fec30bd.txt` | W17 on `fec30bd` — `probes=14 failures=0` |
| `raw/GREEN_SUITE_A_ON_CANDIDATE_v1.txt` | Suite A on the Route B candidate |
| `raw/GREEN_SUITE_B_ON_CANDIDATE_v1.txt` | Suite B on the Route B candidate |
| `raw/GREEN_W17_ON_CANDIDATE_v1.txt` | W17 on the Route B candidate |

`raw/RED_SUITE_A_ON_FAILED_CANDIDATE_fec30bd.txt` and
`raw/RED_SUITE_A_ON_CARRY_FORWARD_BASE.txt` are **byte-identical**
(SHA-256 `a138c12d8c1d807280ed38ef534f3de3325f8cb6260173543cfc5e5312a67506` for both), which is the
mechanical proof required by contract §14 that the byte-exact carry-forward neither silently fixed
nor altered the frozen Window 20 failure.
