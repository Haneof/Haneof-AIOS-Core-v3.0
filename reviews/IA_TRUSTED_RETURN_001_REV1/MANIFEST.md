# Independent Acceptance rev1 — FROZEN MANIFEST

Task: `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-INDEPENDENT-ACCEPTANCE`
Reviewer role: Independent Core Trusted-Return Recovery Acceptance Reviewer
Freeze date: 2026-09-28

## Pinned target

| item | value |
|---|---|
| PR | #258 (`Haneof/Haneof-AIOS-Core-v3.0`) |
| exact candidate | `1ebf51c4cb905e2a2578a09b64007b50bca0d4ac` |
| candidate engineering base | `7b207362a0b148c5d49bb586f1c878583661a5a9` |
| live main (dispatch + verified) | `a3dab8bcffe83cddc523cac6d8d1e4346b5f33e3` |
| reviewer branch | `ia/independent-acceptance-trusted-return-001-rev1` |
| reviewer worktree | `/home/user/ia-review` (created from the exact candidate) |

`git diff 1ebf51c4cb905e2a2578a09b64007b50bca0d4ac -- src/aios_core` = EMPTY
`git diff 1ebf51c4cb905e2a2578a09b64007b50bca0d4ac --stat` = review-only additions only.

## Formal environment

| component | reviewer value | author value | match |
|---|---|---|---|
| CPython | 3.12.14 | 3.12.14 | YES |
| pytest | 8.4.2 | 8.4.2 | YES |
| pydantic | 2.13.5 | 2.13.5 | YES |
| SQLite | **3.51.1** | 3.45.1 | **NO — recorded deviation** |

SQLite deviation note: the review sandbox has no `sqlite3.h` / `libsqlite3-dev` and no
root, so a matching 3.45.1 `_sqlite3` could not be built. The reviewer ran on a newer,
stricter SQLite (3.51.1) than the author. This is not a weaker environment for the
invariants under test; it is recorded as a deviation, not silently ignored.

## Reviewer probe set (rev1)

59 probes across 5 files. Expected outcomes are encoded in each test's assertions and
docstring and were fixed BEFORE the first execution.

| file | probes |
|---|---|
| `test_ia_capability_breadth.py` | 10 |
| `test_ia_authenticity.py` | 20 |
| `test_ia_operation_replay.py` | 19 |
| `test_ia_r1_r4.py` | 8 |
| `test_ia_sigkill.py` | 2 |

## Frozen digests (rev1)

Probe source SHA256:

```
e3d9307c309cfc9f57eac49c0a03b777c989b52e23ec8a32bc5aa0b08b4a2f38  ia_harness.py
5f3ef79f853364dc28493a84eda29f6895044f551a3773bd87094b0741c8966e  test_ia_authenticity.py
45c5342de0bc76d3a068fbddb4123a5218aac8480eca8759fa104cb722e34a75  test_ia_capability_breadth.py
d8e61ecbc7a229ecc49a3647246779d4f85961f5ebeb475595e2c0092e4e8cba  test_ia_operation_replay.py
8a3a5ad47691af469981f6832efa386121939a142e1fba77bdbb94cc062b70de  test_ia_r1_r4.py
fab12907a498943f599f8107974114c9d5f81de244d00d987071b6a0bdc867d7  test_ia_sigkill.py
```

Enumeration SHA256 (`rev1_enumeration.txt`, 59 node ids):

```
94682d307709133b3d9efde3004d1fa138f3c3bb86d269d088b97e984e037dbd
```

Collect-only output SHA256 (`rev1_collect_only.txt`):

```
5191557497ba791f730d0d319d3910b925ddd570aacfa3a6348543f99ea8ae12
```

## Revision log (rev1 preserved; every later revision is a NEW file set)

The frozen **expected outcomes** were never weakened. Revisions fixed reviewer
harness mechanics only.

| rev | source SHA256 (first probe file) | enumeration SHA256 | result | what changed |
|---|---|---|---|---|
| rev1 | `5f3ef79f853364dc28493a84eda29f6895044f551a3773bd87094b0741c8966e` | `94682d307709133b3d9efde3004d1fa138f3c3bb86d269d088b97e984e037dbd` | 16 passed / 43 failed | initial freeze; run exposed harness defects |
| rev2 | `8602304d3efd4ded0b8c447b214142341cdb6d8effa3af50c9710724fdc1a516` | `94682d30…` | 37 passed / 22 failed | `RuntimeSnapshot.round_index`; capability-arg validation; crash points; **blocker first surfaced** |
| rev3 | `2b2a94da981f121e330f101d16cbf2a13888a8b6cc9fe8e60a5a27c92704933d` | `d3d31ccf9539b8d9b90f3a7e20982133b69af8000bd7e9ef45aa2112422dfe48` | 38 passed / 22 failed | capability effect identified by operations delta instead of object-type guessing |
| rev4 | see `evidence/rev4_probe_sources.sha256` | `d3d31ccf…` | 45 passed / 14 failed | pinned `operation_id`; fail-closed assertions; consumption-surface authenticity |
| rev5 | see `evidence/rev5_probe_sources.sha256` | `d3d31ccf…` | 48 passed / 9 failed | R1 fail-closed contract; trust-root probes marked informational |
| rev6 | see `evidence/rev6_probe_sources.sha256` | `d3d31ccf…` | 49 passed / 7 failed | SIGKILL identity comparison; R3 table-only assertion |
| **rev7 (BINDING)** | see `evidence/rev7_probe_sources.sha256` | **`d3d31ccf9539b8d9b90f3a7e20982133b69af8000bd7e9ef45aa2112422dfe48`** | **51 passed / 5 failed / 3 xfailed** | per-(attempt, round) metering identity; final binding run |

Two false positives were investigated and **withdrawn** rather than reported as
findings:

* `KILL-1 REDISPATCH` — the probe rejected a *legitimate new* round; recovery itself
  was correct (round 0 never reached the provider).
* `meter rows for killed attempt: 2` — one meter for the recovered round 0 and one
  for the new round 1; exactly one meter per `(attempt_id, model_round_index)`.

## Freeze rules honoured

- Probe source, expected outcomes, enumeration and collect-only were produced before the
  first execution of any probe.
- After the first run, no original rev1 expected outcome will be edited. If the reviewer
  harness itself is defective, rev1 is preserved and a new rev2 is cut with fresh
  digests.
- The candidate is never modified: no fix, amend, rebase, force-push, squash, merge or
  cherry-pick. Findings are recorded, not repaired.
