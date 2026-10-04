# FAILED_CANDIDATE_IDENTITY — Window 22-RERUN-001

## 1. The frozen failed candidate

| item | value |
|---|---|
| role | frozen failed candidate for `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002` (Window 20 Independent Acceptance) |
| full SHA | `fec30bd1495017bf13f08b0ef5b1e241dfb0e247` |
| short SHA | `fec30bd1` |
| reachable as | `refs/pull/310/head` **and** `refs/heads/arena/01a10010-haneof-aios-core-v3-0` |
| PR | #310 — **OPEN, UNMERGED** |
| code-bearing parent | `7db79da54b26266c5ec519f3e70dd25dff4a95fb` |
| nature of `fec30bd1` itself | documentation-only commit on top of `7db79da5` |
| merge base with live main | `ca47087f…` (see `CARRY_FORWARD_MANIFEST.md`) |

### Drift check — `FAILED_CANDIDATE_DRIFT` not raised

`git ls-remote origin` reports `refs/pull/310/head == fec30bd1495017bf13f08b0ef5b1e241dfb0e247`
and `refs/heads/arena/01a10010-haneof-aios-core-v3-0 == fec30bd1…`. The formal workflow
re-asserts both equalities in every job that materializes the candidate and fails the run
with `FAILED_CANDIDATE_DRIFT` if PR #310's head ever moves.

PR #310 was **not** committed to, force-pushed, rebased, squashed or amended at any point in
this window (task constraint). It is read-only evidence.

## 2. The forbidden prior Window 22 candidate

| item | value |
|---|---|
| reported prior Corrective-003 head | `39917591f07c2ed1aa679f9098c1fc368c3af42e` |
| presence in the GitHub object graph | **ABSENT** — confirmed by `git fetch`, `git cat-file -e`, `gh api repos/…/commits/39917591…` and `git ls-remote` |
| classification | `HISTORICAL_LOCAL_ONLY / NON_DURABLE / NOT_ACCEPTANCE_EVIDENCE` |
| use in this window | **NONE** — not used as a source candidate, not reconstructed, not used as evidence |

Per the task constraint this SHA was used for *nothing*: not as a source candidate, not for
reconstruction, not as acceptance evidence. The candidate in this window was rebuilt from
fresh live main plus a byte-exact engineering carry-forward of the 21 code-bearing paths at
`fec30bd1` (see `CARRY_FORWARD_MANIFEST.md`), then corrected under Route B.

## 3. What the failed candidate fails, and what it passes

Reproduced in a detached worktree at `/tmp/wt-fec` on preflight CPython 3.11.2 and re-verified
by the formal exact-head CI job `red-first-window20-failed-candidate-4of4` on CPython 3.12.14.

| suite | on `fec30bd1` | meaning |
|---|---|---|
| Window 20 Suite A (`window20_independent_attack.py`) | `probes=4 failures=4` | **RED** — the frozen blocker reproduces |
| Window 20 Suite B (`window20_migration_rsa_attack.py`) | `probes=7 failures=0` | migration + RSA positives already held |
| Window 17 (`window17_independent_attack.py`) | `probes=14 failures=0` | Corrective-002 positives already held |
| C3 author matrix (this window, 27 cases) | `17 failed, 11 passed` | **RED** — the matrix is non-vacuous |
| Full Core gate | all pass | the blocker is a *security* failure, not a functional one |

The four Suite A failures on `fec30bd1`:

* `IA20-MINT-003` — `minted=True, state=metered, receipts=1, handoffs=1, responses=1,
  meters=1, turn_response='FORGED_VIA_PUBLIC_LIVE_WINDOW_API_NO_PROVIDER_CALL',
  genuine_rsa_return_conflicted=True`
* `IA20-MINT-004` — `FORGED_ON_VERIFIERLESS_ATTEMPT_VIA_PUBLIC_WINDOW`
* `IA20-OBJGRAPH-002` —
  `reachable_via=[store.__class__.record_live_provider_return.__globals__,
  LiveProviderReturnWindow._issue.__func__.__globals__]`
* `IA20-WINDOW-001` — bad subcases `d_replay`, `g_other_world`, `j_detached_context` = `MINTED`

Together these are `BLK-W20-001`
(`RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW`), root cause
`TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE`.

## 4. Byte-exactness of the RED reproduction

`raw/RED_SUITE_A_ON_FAILED_CANDIDATE_fec30bd.txt` and
`raw/RED_SUITE_A_ON_CARRY_FORWARD_BASE.txt` are **byte-identical**, SHA-256
`a138c12d8c1d807280ed38ef534f3de3325f8cb6260173543cfc5e5312a67506` for both. That is the
mechanical proof required by contract section 14 that the byte-exact carry-forward neither
silently fixed nor altered the frozen Window 20 failure, and therefore that the RED observed
on this window's base is the *same* RED the reviewer froze.

## 5. Raw evidence

| file | content |
|---|---|
| `raw/RED_SUITE_A_ON_FAILED_CANDIDATE_fec30bd.txt` | Suite A on `fec30bd1`, `probes=4 failures=4` |
| `raw/RED_SUITE_A_ON_CARRY_FORWARD_BASE.txt` | Suite A on the carry-forward base, byte-identical |
| `raw/POSITIVE_SUITE_B_ON_FAILED_CANDIDATE_fec30bd.txt` | Suite B on `fec30bd1`, `probes=7 failures=0` |
| `raw/POSITIVE_W17_ON_FAILED_CANDIDATE_fec30bd.txt` | W17 on `fec30bd1`, `probes=14 failures=0` |
| `raw/RED_C3_AUTHOR_MATRIX_ON_FAILED_CANDIDATE_fec30bd.txt` | 27-case matrix on `fec30bd1`, `17 failed, 11 passed` |
