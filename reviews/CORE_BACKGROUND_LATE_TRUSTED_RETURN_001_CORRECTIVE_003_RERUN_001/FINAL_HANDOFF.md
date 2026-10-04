# FINAL_HANDOFF — `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003` / Window `22-RERUN-001`

## Stop state

```
REVIEW_READY
READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE
DO NOT MERGE
```

This window acted as **Core Runtime Corrective Engineer only**. It did not perform Independent
Acceptance, did not merge its own PR, did not enter Window 23 Fresh IA, did not enter
`RC-REFREEZE-004`, and did not run any Resident.

---

## 1. What was wrong, and what was done

**Frozen blocker.** `BLK-W20-001`
= `RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW`,
root cause `TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE`.

The Corrective-002 design guarded a trusted-return *writer* behind an ephemeral "live
provider-return window", but the window's **issuance** helpers were ordinary public module
functions. Any process-local recovery caller could therefore issue its own window, declare its own
bytes handler-returned, and mint a durable trusted receipt + exact handoff — completing and
metering an attempt that must have stayed `in_doubt`, and poisoning a later genuine RSA return.

**PM design ruling implemented: Route B.** The local self-trusting provider-return authority is
removed entirely. Durable trusted late return now depends **only** on a durable external verifier
bound before the provider boundary plus a genuine external cryptographic proof over it. Python
object identity is used for **nothing** — not even as a consistency guard — because the tombstone
keeps no identity-bearing state at all.

Removed: `record_live_provider_return` (187 lines), `LiveProviderReturnWindow._issue`,
`consume_live_provider_return_window`, `_ISSUE_SENTINEL`, `_OPEN_WINDOWS`, `_HANDLER_RETURNS`,
`CognitiveRuntime._live_provider_return_window` and its `model_response_authenticator` ctor hook /
`ModelResponseAuthenticator`, `TurnRuntime._capture_live_provider_return` and its wiring.
`src/aios_core/runtime/live_return.py` is now an **inert tombstone** that holds no authority and is
not imported by any Core authorization module.

Result: exactly **one** trust root remains — `attach_late_trusted_return`, gated on RSA
verification against the durably bound public verifier. `stage_exact_response` can only *consume*
trusted state, never originate it. Full enumeration in `TRUST_MINT_AUDIT.md`.

## 2. Required final gates

| gate | status | evidence |
|---|---|---|
| Suite A candidate GREEN (4 probes, 0 failures) | **GREEN** | CI job `candidate-suite-a-green-4of4`; `raw/GREEN_SUITE_A_ON_CANDIDATE_v2.txt` |
| Suite B GREEN (7 / 0) | **GREEN** | CI job `candidate-suite-b-green-7of7`; `raw/GREEN_SUITE_B_ON_CANDIDATE_v2.txt` |
| W17 GREEN (14 / 0) | **GREEN** | CI job `candidate-w17-green-14of14`; `raw/GREEN_W17_ON_CANDIDATE_v2.txt` |
| C3 author matrix GREEN (27 cases) | **GREEN** — 28 passed | CI job `c3-author-matrix-green-27-cases`; `C3_ATTACK_MATRIX.md` |
| C3 matrix non-vacuous (RED on the failed candidate) | **RED 17 / 27** | CI job `c3-author-matrix-red-on-failed-candidate`; `raw/RED_C3_AUTHOR_MATRIX_ON_FAILED_CANDIDATE_fec30bd.txt` |
| full Core failures=0 errors=0 | **GREEN — 928 passed** on formal CPython 3.12.14 | CI job `full-core-gate-0-failures-0-errors` |
| real SIGKILL | **GREEN** | CI job `real-sigkill-and-genuine-external-return` |
| Corrective-002 positives preserved | **GREEN** | CI job `corrective-002-migration-rsa-positives` + Suite B + W17 |
| RED-first reproducible, not the Window 14 RED | **GREEN — `probes=4 failures=4`** on `fec30bd1…` | CI job `red-first-window20-failed-candidate-4of4`; `BASELINE_RED.md` |
| scope clean | **GREEN** — `out_of_scope = 0`, `forbidden_paths = 0` | CI job `scope-discipline-and-identity-guard`; `SCOPE_AUDIT.md` |
| exact-head formal CI, CPython 3.12.14 / pydantic 2.13.5 / pytest 8.4.2 | environment **exact**; head equality asserted by the workflow | `FORMAL_CI_RESULTS.md` §1, §5 |
| new PR OPEN + UNMERGED, head == exact tested SHA | opened unmerged, `DO NOT MERGE` | §4 below |
| no commit after the final formal CI | final run identifiers published via PR body / commit comments | `DURABLE_PUBLICATION_LOG.md` §4 |

No stop condition was raised. See `SCOPE_AUDIT.md` §5 for the full table.

## 3. Disclosures the next reviewer must see

### 3.1 Section-10 inherited observation (not fixed, by instruction)

`attach_late_trusted_return` commits the receipt, the exact-bytes handoff and the
verifier-consumption marker **before** calling `stage_exact_response`. Classification:
**`INHERITED_OBSERVATION / NOT_NEW_CORRECTIVE003_REGRESSION`** — the identical statement order is
present in the frozen failed candidate `fec30bd1…` (lines 2301 / 2350 / 2387 / 2402 / 2404 there,
2330 / 2379 / 2416 / 2431 / 2433 on the candidate). It was **not** fixed, because doing so would
change the commit boundaries of the only trusted-return writer — Corrective-002 behaviour that
Window 17 and Window 20 already accepted.

It is safe (the intermediate state is fail-closed: `pending_exact_response` refuses, and a replay
with the same genuine proof is idempotent through `consumed_at` + `INSERT OR IGNORE`). It is
nonetheless **load-bearing for one Route B design decision**: an earlier draft gated supersession on
a boolean `has_verified_receipt(attempt_id)`, which — because the receipt is committed before
staging — was already true inside the same genuine call, so a forged local return *could* have
poisoned a later genuine external return. The shipped design replaces the boolean with a **proof
comparison** (`verified_conflicting_receipt`). Full analysis: `INHERITED_OBSERVATIONS.md` and
`DESIGN_SECURITY_MODEL.md` §4.

### 3.2 Residual risk, pre-existing, out of scope

A fresh-process caller invoking `store.record_response` **directly** on a `dispatching`
verifier-less attempt, before any `admit()` forced `in_doubt`, can close that round with
caller-supplied provider identity. It mints **no** receipt, handoff or staged row, so the round is
permanently not recovery-eligible, its bytes can never be replayed as an exact provider reply, and
a later genuine external proof supersedes the unverified provenance. It cannot move a verifier-less
attempt out of `in_doubt` once admission has run. Pre-existing on live main and on `fec30bd1…` for
anonymous directives. Classification:
`INHERITED_OBSERVATION / NOT_NEW_CORRECTIVE003_REGRESSION`-adjacent residual risk. Not fixed —
outside the frozen scope. Details: `DESIGN_SECURITY_MODEL.md` §6, `TRUST_MINT_AUDIT.md` §7.

### 3.3 Branch-name deviation

The suggested branch name was
`core-background-late-trusted-return-corrective-003-window22-rerun-001`. The execution platform
hard-binds this session to `arena/01a101e0-haneof-aios-core-v3-0` and cannot create, switch to or
push any other branch name. That bound branch **is** the new durable engineering branch: new,
remote, linear on fresh live main, carrying all work, and the head of the new PR. Naming difference
only; no effect on durability, identity or reviewability.

### 3.4 Local runs are PREFLIGHT only

Every local run used CPython **3.11.2**, because `uv python install 3.12.14` failed in the sandbox
with `invalid peer certificate: UnknownIssuer` against
`github.com/astral-sh/python-build-standalone`. Exact 3.12.14 fidelity comes **only** from GitHub
Actions. Local results are never cited as acceptance evidence.

### 3.5 Sandbox interruption, fully recovered

Mid-window the sandbox workspace was rolled back (local `HEAD` reset to the branch point
`054d15cd…`, the preflight virtualenv and `/tmp` removed). **No work was lost**: §22 staged durable
pushes had already put all 11 commits on the remote, `git ls-remote` confirmed the remote head was
exactly the last pushed commit, and recovery was `git fetch` + `git reset --hard` to it. The
virtualenv was rebuilt, the three frozen probes were re-extracted from their pinned git blobs with
blob id and SHA-256 re-verified, the `fec30bd1…` worktree was recreated, and all three probe suites
were re-run green and **byte-identical** to the archived evidence. Classification: infrastructure
interruption — not `GROUND_TRUTH_DRIFT`, not `FAILED_CANDIDATE_DRIFT`, not
`REMOTE_PUBLICATION_IDENTITY_CONFLICT`. Full record: `DURABLE_PUBLICATION_LOG.md` §3.

### 3.6 Downstream operator compatibility debt

C15 harness failures caused by Route B are classified
**`DOWNSTREAM_OPERATOR_COMPATIBILITY_DEBT`**. Unsafe live self-trust was **not** restored to make
C15 green. `tools/c15_persistence/**`, `tests/c15_persistence/**` and `tools/c15_preflight/**` are
untouched, and `tests/c15_persistence/**` (78 cases) is **not** part of the Core gate.

### 3.7 Workflow permissions

`permissions.contents` was widened from `read` to `write` **solely** so each job can publish its
verdict and diagnostics tail as a commit comment (`if: always()`). This was necessary because the
Actions log and artifact blob hosts are unreachable from some review environments, while
`api.github.com` is reachable. The workflow performs no branch protection change, no merge, no tag,
no release and no other write. It is also the channel §22 designates for post-formal-CI evidence.

### 3.8 No `pull_request` trigger, deliberately

A `pull_request` run checks out a **merge** commit, so `GITHUB_SHA` can never equal the engineering
branch head and the exact-head assertion would produce a misleading red run against the PR. The
formal exact-head gate is the `push` run on the branch head — which is also the PR head — and its
commit status is visible on the PR. `workflow_dispatch` allows a re-run on the same exact head
without creating a commit.

## 4. Historical test modification

13 historical test files were modified, all **TIGHTEN_ONLY**, all with the seven-item record
required by section 8 both in `TIGHTEN_AUDIT.md` and inline in the file itself. 0 were deleted, 0
were weakened. No expectation was changed merely to reach GREEN: every behavioural expectation
(crash points, conflict types, exactly-once counts, completion states, `SIGKILL` exit codes,
migration outcomes) is unchanged; only the *authority* a test uses to make bytes durable-trusted
changed, plus new assertions pinning the **absence** of the old authority.

The recurring strengthening is two-sided: where the old suite asserted "trusted state exists after
a local return", the new suite asserts "trusted state does **not** exist after a local return, and
**does** exist, byte-identically, after a genuine external proof".

## 5. What the next window should check first

1. Replay the three frozen probes from the pinned review commits — do not trust any local copy.
   Blob ids and SHA-256 values are in `PROBE_MANIFEST.md` and pinned in the workflow.
2. Run the C3 author matrix, then replay the **same file** on `fec30bd1…` and confirm it is RED.
   A matrix that is green on both is vacuous.
3. Read `TRUST_MINT_AUDIT.md` §1 for the complete writer inventory, and confirm independently that
   `attach_late_trusted_return` is the only function that can originate trusted rows.
4. Decide on the two disclosures in §3.1 and §3.2. Neither was fixed here, both by instruction.
5. If the C15 operator harness must go green, treat it as
   `DOWNSTREAM_OPERATOR_COMPATIBILITY_DEBT` in its own window — **not** by restoring local
   self-trust.

## 6. Evidence package

See `EVIDENCE_INDEX.md` for the full file-by-file index and `SHA256SUMS` for integrity.
