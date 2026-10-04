# START_GROUND_TRUTH — CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002

Task: `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002` (Window 19, Core Runtime
Corrective Engineer).  Binding input: the Window 18 PM adjudication
`governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_001_ACCEPTANCE_FAILURE_ADJUDICATION_2026-10-03.md`
(committed by merged PR #309) §5 `C2-1` .. `C2-10`.

## Verified ground truth at window start (re-read from GitHub, not assumed)

| Ref | SHA | Notes |
| --- | --- | --- |
| live `main` | `ca47087fb68c90d6ac380c11143a0e36e80fc04a` | merge commit of PR #309 (`a3b917d785366bf4c19c8bf150ff713a6b3b6b67` head) |
| `main` tree | `13c325d8bce2c145545bd1ea713584e19e0c99e9` | |
| failed candidate (Window 17) | `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` | PR #308 head, still OPEN / UNMERGED |
| failed candidate parent | `293d32c683033ba27c11059fd021e68342a82c77` | |
| failed candidate tree | `a762df979826d3a599b93d937c53b633d0cb8466` | |
| failed candidate construction base | `0b883c71d91e5f0772334514925237f1570fa780` | merge commit of PR #307 |
| Window 17 review evidence | `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8` | parent = `cb8a6b3c…`, subject "publish Window 17 Fresh IA review evidence for PR #308 (ACCEPTANCE_FAIL / blocker=3 / DO NOT MERGE)" |
| pre-created Corrective-002 remote branch | `core-background-late-trusted-return-corrective-002-window19` @ `ca47087…` | zero commits beyond main, no PR (#310/#311 do not exist) |

`git fetch --all --prune` does not fetch narrow-ref candidate/review objects in this clone;
`git fetch origin <sha>` was used for `cb8a6b3c…`, `e4161dd0…`, `0b883c71…`, `293d32c6…`.

No drift was observed for `GROUND_TRUTH_DRIFT`, `FAILED_CANDIDATE_DRIFT`,
`REVIEW_IDENTITY_MISMATCH` or `WINDOW17_PROBE_HASH_MISMATCH` during this window.

## Construction base of the Corrective-002 candidate

Fresh live `main` = `ca47087fb68c90d6ac380c11143a0e36e80fc04a`.  The Corrective-002
work was reconstructed onto that commit by re-materialising the accepted
Corrective-001 engineering content (blob-verified copies of the 14 files that PR
#308 changed, `git cat-file --batch-check` blob equality against `cb8a6b3c…`) as
commit `f088ce1067f412313a8e7fd85f37a2d7363b392e` (`carry-forward(core):
re-materialize Corrective-001 engineering content onto fresh main`), parent
`ca47087…`.  Corrective-002 changes are the commits after that one.

PR #308 (`cb8a6b3c…`, its branch and its history) was not pushed to, rebased,
squashed or amended; Window 17 review `e4161dd0…` and its evidence were not
modified.

## Runtime environment used for local (non-formal) evidence

| Component | Local sandbox | Formal gate |
| --- | --- | --- |
| Python | CPython 3.11.2 (`/home/user/.local/venv311/bin/python`) | CPython 3.12.14 required |
| pydantic | 2.13.5 | 2.13.5 |
| pytest | 8.4.2 | 8.4.2 |
| SQLite | 3.40.1 | 3.45.1 |
| OpenSSL | 3.0.20 | 3.0.13 |

Formal runtime download is unreachable from this sandbox
(`release-assets.githubusercontent.com`, `objects.githubusercontent.com`,
`raw.githubusercontent.com`, `www.python.org`, `astral.sh`, Debian/conda mirrors
all blocked), so the formal runtime evidence is produced exclusively by GitHub
Actions at the exact final candidate head (`FORMAL_CI_RESULTS.md`).  No 3.11 result
is presented as formal.
