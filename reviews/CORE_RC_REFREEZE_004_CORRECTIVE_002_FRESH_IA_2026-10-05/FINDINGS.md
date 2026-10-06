# Findings — REVIEW_ONLY / DO NOT MERGE

## `IA27-BLK-002` — Final whole-run identity seal has a post-read TOCTOU

**Disposition: BINDING / CRITICAL / NOT CLOSED.**

**Location:** `.github/workflows/core-rc-refreeze-004-formal-gate.yml`, final-seal step, lines 637–677 at candidate `5a5d384f16798bfff46ffe03f87310b0eafb2321`.

The step reads the canonical branch at lines 644–652 and compares the returned `branch_head` with `GITHUB_SHA`. It then separately queries the run (656–663), fetches and validates the provisional comment (665–676), and prints `WHOLE_RUN_IDENTITY_SEAL=PASS` (677). There is no subsequent canonical-branch read, atomic compare-and-seal, or server-side state that invalidates the already-published provisional pin if the ref changes after the one branch response.

### Reproduction

`probes/final_seal_postread_race.py` extracts the shell block from the exact candidate commit. Its mocked `curl` returns canonical branch A, then advances the mock canonical ref to B immediately after that one response. The mocked run and comment continue to match A. The exact candidate shell exits `0` and prints `WHOLE_RUN_IDENTITY_SEAL=PASS`, while the ref at completion is B. See `raw/final_seal_postread_race.txt`.

This probe is local and mocked. It is **not** a hosted GitHub Actions reproduction of the final instruction interval, and it does not simulate server-side cancellation. The candidate's actual hosted GREEN control `37267746540` advanced the branch during the preceding 30-second guard; the final seal then detected B and the old run was cancelled. That proves the guard interval is handled, but not the interval after the final branch response. GitHub `cancel-in-progress: true` is not an atomic transaction binding branch state to workflow completion; the candidate has not demonstrated that cancellation always wins this final race.

The candidate's latest exact-head run `37320392029` passed while the branch remained at A; it does not exercise this counterexample.

**Required closure evidence:** a design that mechanically prevents a stale run from becoming authoritative after a ref movement at any point up to durable completion, plus a controlled test that advances the ref immediately after the final branch response and proves the old run cannot end authoritative SUCCESS. Do not treat another earlier-guard test or static identity assertion as closure.

## `IA28-BLK-001` — Terminal protected-drift regex has false negatives

**Disposition: BINDING for the required protected-drift carry-forward gate.**

**Location:** same workflow, line 464. The initial protected-drift check at line 93 uses normal single escaping. The terminal check at line 464 contains two backslashes before each escaped dot in the ERE (`pyproject\\.toml`, `setup\\.cfg`, `\\.github/workflows/`, etc.). In the literal YAML block, those backslashes reach `grep -E` unchanged.

The extracted terminal ERE misses `.github/workflows/late-added.yml`, `pyproject.toml`, and `setup.cfg`, while it still matches `src/**` and `tests/**`. The exact terminal step prints the name-status diff but fails only if the ERE matches. Thus, if one of those protected paths changes on `main` after the initial `live_main` snapshot and before `terminal_main`, the change can appear in the log without making the formal job fail. The initial check at line 93 catches drift already present at startup, but does not make the terminal recheck redundant: the terminal check exists to catch drift introduced during the run.

`probes/terminal_protected_drift_regex.py` runs the exact extracted patterns against a disposable Git diff containing only late `.github/workflows/**` and packaging-file changes. The startup pattern detects them; the terminal pattern does not. See `raw/terminal_protected_drift_regex.txt`.

The formal run was green with no reported current protected drift. That does not demonstrate this dynamic guard is sound. The Window 28 contract explicitly carries forward protected-drift verification, so this fail-open check is binding until corrected and positively/negatively tested.

## `OBS-IA28-001` — Credential-presence regex is over-escaped (non-binding as configured)

**Disposition: NON-BINDING HARDENING OBSERVATION.**

The `git config --local --get-regexp` pattern at workflow lines 69 and 457 contains four literal backslashes around dots. A disposable config containing `http.https://github.com/.extraheader` is not matched by that pattern; the intended one-backslash ERE does match. See `probes/credential_guard_regex.py` and `raw/credential_guard_regex.txt`.

This is not elevated to a blocker for the current candidate: Job A explicitly configures `actions/checkout` with `persist-credentials: false` and has read-only permissions. The regex should nevertheless be corrected before relying on this check as a future credential-presence control.

## Verdict accounting

- Binding blocker carried forward and not closed: **1** (`IA27-BLK-002`).
- Additional binding false-green in required carry-forward gate: **1** (`IA28-BLK-001`).
- Non-binding hardening observation: **1** (`OBS-IA28-001`).
- Candidate PR #336 disposition: **OPEN / UNMERGED / DO NOT MERGE**.
