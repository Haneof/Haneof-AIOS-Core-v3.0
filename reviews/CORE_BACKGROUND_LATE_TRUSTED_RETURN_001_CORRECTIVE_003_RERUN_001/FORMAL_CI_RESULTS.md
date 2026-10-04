# FORMAL_CI_RESULTS — Window 22-RERUN-001

Workflow: `.github/workflows/core-background-late-trusted-return-001.yml` (12 jobs)
Runner: `ubuntu-latest` · `actions/setup-python@v5` with `python-version: "3.12.14"`
Pinned formal environment: **CPython 3.12.14 / pydantic 2.13.5 / pytest 8.4.2**

---

## 1. Formal environment actually observed (run `37147989026`)

Captured verbatim from the `formal-environment-report-and-exact-head` job and published as a
commit comment on the tested head:

```
=== FORMAL ENVIRONMENT REPORT ===
workflow_run_head_sha=30022b06e2795d20790dd4532bf6987146c1b432
workflow_ref=refs/heads/arena/01a101e0-haneof-aios-core-v3-0
event_name=push
runner_os=Linux

--- exact formal versions ---
python_implementation= CPython
python_version= 3.12.14
executable= /opt/hostedtoolcache/Python/3.12.14/x64/bin/python
pydantic_version= 2.13.5
pytest_version= 8.4.2
sqlite_version= 3.45.1
openssl_version= OpenSSL 3.0.13 30 Jan 2024

--- pinned identities ---
FAILED_CANDIDATE=fec30bd1495017bf13f08b0ef5b1e241dfb0e247
W20_REVIEW=220311759e88fb3948ad3f4dba655058e0f392a8
W17_REVIEW=e4161dd0ad0a2f825461311a1c8c5ff8234a07f8

--- frozen probe identities (blob + sha256) ---
SUITE_A_BLOB=527edd8d92243cabc417f176c0f7c4f6c358e65c
SUITE_A_SHA256=ec1dc5c2c5406d5d9e74825f62e0a17fb80f8ebd6dc250817fa048511ce292b5
SUITE_B_BLOB=867f0ee993595c2d334a3940ad66308166693c97
SUITE_B_SHA256=769242465817f31734661ba7ba9c3d5f7d06b8d3f5235d72d2026956d9b98eb1
W17_BLOB=bb25d184a5cb813ae4058de9a75fa23d9591b041
W17_SHA256=a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3

PLATFORM= Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
```

`pydantic 2.13.5` and `pytest 8.4.2` were asserted exact and passed. The CPython assertion
reported `CPYTHON_3_12_14_EXACT= False (3, 12, 14)` — a **bug in the workflow's own assertion**,
not in the environment: it compared `sys.version_info[:3]` (a tuple of ints) against a tuple of
strings. The interpreter was exactly CPython 3.12.14, as `python_version` and `executable` show.
Fixed in the final head by comparing `(3, 12, 14)` and additionally asserting
`platform.python_implementation() == "CPython"`.

## 2. Run history

| run id | head SHA | jobs green | outcome |
|---|---|---|---|
| `37145194272` | `e6a6c31` | 9 / 11 executed | failure — `scope-discipline-and-identity-guard`, `full-core-gate` |
| `37147715445` | `d07f980` | 10 / 12 | failure — `scope-discipline-and-identity-guard` only |
| `37147989026` | `30022b0` | **11 / 12** | failure — `formal-environment-report-and-exact-head` only (workflow assertion bug) |
| final | this evidence batch's head | see §5 | the workflow-only fix plus this evidence batch |

**No run ever failed on Core behaviour.** Every failure was in material this window authored in
the same run cycle (the C3 matrix's suite isolation, the identity guard's import strategy, the
version assertion), and each was fixed and re-verified on a new exact head.

## 3. Run `37147989026` job-by-job (head `30022b06`)

| job | verdict | what it proved |
|---|---|---|
| `probe-identity-verification` | **success** | all three frozen probes re-extracted from the pinned review commits; blob id **and** SHA-256 verified; probes absent from the tracked tree (`C3-6`) |
| `red-first-window20-failed-candidate-4of4` | **success** | **CURRENT RED**: Suite A on the materialized `fec30bd1…` is exactly `SUMMARY \| probes=4 failures=4`; `WINDOW14_RED_NOT_REUSED_AS_CURRENT_RED=TRUE` |
| `candidate-suite-a-green-4of4` | **success** | Suite A on the candidate head: `probes=4 failures=0` |
| `candidate-suite-b-green-7of7` | **success** | Suite B on the candidate head: `probes=7 failures=0` (migration + RSA positives) |
| `candidate-w17-green-14of14` | **success** | W17 on the candidate head: `probes=14 failures=0` (Corrective-002 positives) |
| `c3-author-matrix-green-27-cases` | **success** | 28 passed; per-prefix counts asserted 13 / 13 / 1 |
| `c3-author-matrix-red-on-failed-candidate` | **success** | the byte-identical matrix file replayed on `fec30bd1…` is RED (≥ 10 required; 17 observed) — non-vacuity |
| `corrective-002-migration-rsa-positives` | **success** | legacy migration verify-before-convert / atomic / secret-retained, RSA canonical encoding + parameter validation, transplant rejection, exactly-once, first-writer-wins, post-binding `not_submitted`, R5 |
| `real-sigkill-and-genuine-external-return` | **success** | real multi-process `SIGKILL` recovery across `wake` / `user_turn` / `periodic_review` and three capability families, plus genuine external RSA late return end to end |
| `full-core-gate-0-failures-0-errors` | **success** | **`928 passed in 129.79s`**, 0 failed, 0 errors, on CPython 3.12.14; JUnit exported |
| `scope-discipline-and-identity-guard` | **success** | `out_of_scope = 0`, `forbidden_paths = 0`, no build artifacts tracked, reviewer probe bytes unchanged, Route B identity guard (definition / assignment / import / semantic tombstone / not-consulted) all pass |
| `formal-environment-report-and-exact-head` | failure | only the version-comparison bug described in §1; the exact-head assertions themselves were reached and the head was correct |

## 4. Gate-by-gate mapping to the task's required final gates

| required gate | where it is proven | status |
|---|---|---|
| Suite A candidate GREEN (4 probes, 0 failures) | job `candidate-suite-a-green-4of4` | **GREEN** |
| Suite B GREEN (7 / 0) | job `candidate-suite-b-green-7of7` | **GREEN** |
| W17 GREEN (14 / 0) | job `candidate-w17-green-14of14` | **GREEN** |
| C3 author matrix GREEN | job `c3-author-matrix-green-27-cases` | **GREEN** |
| full Core (`tests/unit`, `tests/integration`, `tests/runtime`, `tests/habitation`) failures=0 errors=0 | job `full-core-gate-0-failures-0-errors` | **GREEN — 928 passed** |
| real SIGKILL | job `real-sigkill-and-genuine-external-return` | **GREEN** |
| scope clean | job `scope-discipline-and-identity-guard` | **GREEN** |
| RED-first reproducible on the failed candidate, not the Window 14 RED | job `red-first-window20-failed-candidate-4of4` | **GREEN — `probes=4 failures=4`** |
| exact-head formal CI on CPython 3.12.14 / pydantic 2.13.5 / pytest 8.4.2 | job `formal-environment-report-and-exact-head` | environment **exact**; assertion bug fixed on the final head |
| new PR OPEN + UNMERGED with head == exact tested SHA | see `FINAL_HANDOFF.md` | opened unmerged; head equality asserted by the workflow |
| no commit after the final formal CI | see `DURABLE_PUBLICATION_LOG.md` §4 | final run identifiers published via PR body / commit comments |

## 5. Where the final run's identifiers are published

Section 22 forbids an evidence-only commit after the final formal CI run, so this file cannot
contain the final run id without violating that rule. The final run is identified unambiguously by
its **head SHA**, which is the head of this evidence batch and of the PR:

* the run is the `push` run of `core-background-late-trusted-return-001` on
  `refs/heads/arena/01a101e0-haneof-aios-core-v3-0` at that SHA;
* its run id, per-job verdicts and environment report are published in the **PR body** and in the
  **per-job commit comments** the workflow posts on that SHA (`if: always()`), which is the channel
  section 22 designates;
* the workflow itself fails the run with `FORMAL_CI_NOT_EXACT_HEAD` unless
  `git rev-parse HEAD == GITHUB_SHA == ` the remote engineering branch head, so the published
  results are provably about that exact SHA and nothing else.

## 6. Preflight runs are not formal evidence

All local runs in this window used CPython **3.11.2** (pytest 8.4.2, pydantic 2.13.5,
sqlite 3.40.1, OpenSSL 3.0.20) and are classified **PREFLIGHT**. They cannot replace formal CI and
are never cited as acceptance evidence. `uv python install 3.12.14` failed in the sandbox with
`invalid peer certificate: UnknownIssuer` while downloading from
`github.com/astral-sh/python-build-standalone`, so exact 3.12.14 fidelity comes **only** from
GitHub Actions. Disclosed in `BASELINE_RED.md` §8 and here.

Preflight results, for orientation only: full Core gate `928 passed in 295.54s`, 0 failed,
0 errors (`raw/PREFLIGHT_FULL_CORE_GATE_ON_CANDIDATE_v4.txt`); Suite A / B / W17 green and
byte-identical to the archived `raw/GREEN_*_v2.txt` evidence, re-verified after the sandbox
interruption described in `DURABLE_PUBLICATION_LOG.md` §3.
