# [G3 INDEPENDENT REVIEW] AIOS Gateway v0.4 — PR #376 exact-head security review

> **Publication channel note.** Direct comment publication to Issue #379 was attempted first and denied by the sandbox token (`POST /repos/…/issues/379/comments` → HTTP 403 `Resource not accessible by integration`). Per the PM fallback rule, this report is delivered as an **evidence-only Draft PR** whose sole change is this Markdown file under `reviews/AIOS_GATEWAY_V04_INDEPENDENT_REVIEW/**`. The PR is NOT a task-request PR (no `agent-tasks/gateway-request.json`), is NOT mergeable evidence of acceptance, and must not be merged.

**VERDICT: `REVIEW_PASS`** (candidate security/policy review only; one evidence sub-item `PARTIAL/BLOCKED` — see §6.3)
**`G3_REVIEW_CONDITION`: MET as review input.** Activation stays HOLD per PM. `G4 = NOT_TESTED`.

## 0. REVIEWER_IDENTITY_AND_CONFLICTS

- Reviewer: Arena.ai Agent Mode, fresh session on branch `arena/87ec51ad-haneof-aios-core-v3-0` (session worktree clean at base `528296d…` before review; no candidate files present locally).
- I did **not** author, edit, test-produce, or refresh PR #376, its branch, or its CI. I am not the PM, not the v0.4 engineering author, and not a merge/activation operator.
- Limitation (disclosed per PM): a fresh chat session is not cryptographic proof of organizational independence; Arena session provenance cannot be certified by GitHub. I made no claim to be an accredited security authority — this is an AI-generated independent technical review for PM adjudication.
- Review mode: read-only + isolated synthetic tests only. No modification to `PR #376`, `.github/workflows/**`, `tools/**`, `tests/**`, `src/**`, `agent-tasks/**`, PR370/371/367, Core/C15, Window69, Resident, Cursor1. No workflow activation, no merge, no task-request PR. The sole repository change is this evidence-only report file.

## 1. IDENTITY VERIFICATION (independently recomputed)

| Item | Value | Verified by |
|---|---|---|
| BASE_SHA (main) | `528296def47f8f409350889f11961ebedc4a38c2` | `git fetch origin main` + `git rev-parse origin/main` == workspace HEAD |
| TARGET_HEAD_SHA | `2a950f4ce78fe7d3e55ff103bd7d95bfcf8109c7` | `git fetch origin refs/pull/376/head`; `rev-parse FETCH_HEAD` == pinned SHA |
| Merge parents | `c8a821d094e1ea1eb7e3661ca478119d4c333e08` + `528296def47f8f409350889f11961ebedc4a38c2` | `git cat-file -p 2a950f4…` (matches PM statement) |
| PR state | OPEN / DRAFT / UNMERGED, author `Haneof`, 5 commits, 4 added files, +658/−0 | `gh pr view 376`, `gh api …/pulls/376/commits` (5) |
| Reviewer workspace during review | clean at BASE, candidate objects fetched as data only | `git status` → clean |

### 1.1 Diff inventory (main..candidate) — exactly four ADDED files, all mode 100644

`git diff-tree -r 528296d 2a950f4` + GitHub `pulls/376/files` API agree, blob SHA (local == GitHub API `file.sha`):

| Path | Status | Blob SHA |
|---|---|---|
| `.github/workflows/aios-remote-agent-pr-inbox-v04.yml` | A | `fa3947ad514dfc0ee6d6a0f31c5a44fa3588bd39` |
| `tools/agent_gateway/pr_request.py` | A | `8cd3d9fc05b8dd2dd548144e606dfcbef89a4ce8` |
| `tests/agent_gateway/test_pr_request.py` | A | `2ed147263fe92d03fc9421f646b1d9917b67035b` |
| `docs/AIOS_REMOTE_AGENT_PR_INBOX_V04.md` | A | `1bab8ff660c69624786e08885934e401dc2480bd` |

Tree relation: `tree(2a950f4) = tree(528296d) + exactly these 4 files` (no modifications/deletions of any main file; the merge kept main's `runner.py`, v01/v02 workflows, window67 audit tooling).

### 1.2 Scope-expansion check vs prior candidate (`c8a821d`)

- `tools/agent_gateway/pr_request.py`: **byte-for-byte identical** (`diff` empty).
- Workflow: only the non-privileged `public-policy-ci` step expanded from 1 task to the 5-task loop; the privileged `owner-pr-readonly-dispatch` job is unchanged.
- Tests: BASE fixture constant updated to the new main SHA + 1 added allowlist-completeness test.
- Docs: task list refreshed to v0.3 five-task allowlist + PM-hold/baseline-refresh section. No implementation change.
- Conclusion: **no undocumented scope expansion.**

## 2. pull_request_target / permissions / auth / execution-boundary analysis (source-inspected)

Workflow `.github/workflows/aios-remote-agent-pr-inbox-v04.yml` (blob `fa3947ad…`):

1. **Triggers**: `pull_request` (4 v0.4 paths → non-privileged `public-policy-ci`) and `pull_request_target: types:[opened]` (path `agent-tasks/gateway-request.json` → privileged `owner-pr-readonly-dispatch`). Trigger surfaces are disjoint by path.
2. **Privileged job always runs base code**: `pull_request_target` semantics = workflow from trusted base; job `if` requires `event_name=='pull_request_target' && user.login=='Haneof' && base.ref=='main' && head.repo.full_name==github.repository` (fork/bot/other-user never enter the job). Parser re-validates all of these independently (defense in depth).
3. **Permissions**: workflow-level and job-level `permissions: contents: read` on both jobs. **Zero** `secrets.*` references, zero `GITHUB_TOKEN` references in the file. `actions/checkout` uses `persist-credentials: false` in both jobs.
4. **Checkout pinning (privileged)**: `ref: ${{ github.event.pull_request.base.sha }}` — trusted base commit only; parser then requires `git rev-parse HEAD == event base.sha` before anything else touches the PR.
5. **Untrusted head = Git data only**: `git fetch --no-tags origin <head_sha>` (objects only), `rev-parse FETCH_HEAD == head_sha`, then only `diff --no-ext-diff --name-status --no-renames`, `cat-file -s/-t`, `ls-tree`, `show` (blob). No checkout/reset/merge/rebase/`pip install`/import/eval of head content anywhere in the privileged path; author tests assert the command set excludes mutating git verbs.
6. **Command-injection surface**: 4 `${{ }}` interpolation sites total — 2 artifact `name:`s (`run_id`/`run_attempt` integers), 2 checkout `ref:`s (SHA from trusted GitHub payload). `steps.task.outputs.task` is written to `GITHUB_OUTPUT` only as `task=<allowlisted-literal>` and consumed as a quoted env var re-validated by `argparse choices=TASKS`. No shell construction from untrusted text.
7. **git-diff/code-exec via attributes**: tree-to-tree `git diff` with `--no-ext-diff` (external diff drivers disabled); textconv/diff drivers require config-side command definitions (trusted checkout config), and only `--name-status` is parsed. No code execution path via `.gitattributes`.
8. **Origin pinning**: `git remote get-url origin` must equal `https://github.com/Haneof/Haneof-AIOS-Core-v3.0` modulo one trailing `.git`/`/`. Fail-closed on anything else.
9. **Execution boundary after approval**: `runner.py` (main's, unchanged by this PR) accepts only `--task` ∈ immutable 5-element `TASKS` tuple; tasks are fixed static byte-audits over pinned SHAs/digests writing `gateway-evidence/` JSON/JUnit/SHA256 receipts; self-declared `NON_FORMAL_PUBLIC_CI_EVIDENCE`, `real_resident_started:false`, `merge_authorized:false`.
10. **Event semantics / races**:
    - `types:[opened]` only: `synchronize`/`edited`/`reopened` never re-trigger; parser additionally rejects any action≠`opened` (replay via re-run reuses the same immutable payload).
    - **TOCTOU closed**: validation binds `event.pull_request.head.sha` (payload snapshot), not branch tip; later force-pushes cannot change what is validated; `FETCH_HEAD` is re-checked equal to that SHA.
    - Title check uses the `opened`-time title (exact `==`), so post-open title edits cannot influence a completed run.
    - `concurrency` per-PR with `cancel-in-progress: false` (no cancellation race).
    - Path-filter caveats (e.g. trigger firing more/less than expected) are fail-safe: the parser is the real gate and rejects anything that is not the exact one-file request.
    - Draft PRs are not excluded by the job `if` (see Finding F2).
    - `head.repo` null (deleted fork) makes the `if` false → skipped. Fail-closed.
11. **Trusted base staleness**: if main moves after `opened`, the job still pins and verifies the event `base.sha` (a previously-trusted main commit). Fail-closed/consistent; residual note only.

## 3. Adversarial matrix — 40+ numbered cases (TESTED = executed by me; SI = source-inspected; B = BLOCKED)

Independent harness: `/tmp/gw-review/adversarial_pr_request.py` — **41/41 OK** (real local git fixtures, real `git fetch`/`diff`/`cat-file`/`ls-tree`, no `unittest.mock` on the git path; e2e `main()` via subprocess with `python -I`). Author's suite: **63/63 OK** re-run independently on the exact candidate tree.

| # | Case | Method | Result |
|---|---|---|---|
| 1 | Valid one-file request (positive control) | TESTED (fixture) | ACCEPTED, `task=gateway-selftest` |
| 2 | Fork PR (`head.repo=attacker/repo`) | TESTED | REJECTED `unapproved…`/repo check |
| 3 | Non-owner authors: `other`, empty, `arena[bot]`, `haneof`, `Haneof `, homoglyph `Haneоf` | TESTED | REJECTED (all) |
| 4 | Wrong base ref: `Main`, `refs/heads/main`, `master`, `main␣`, empty | TESTED | REJECTED |
| 5 | Wrong `repository.full_name` / `base.repo` / `head.repo` | TESTED | REJECTED |
| 6 | Event name spoof: `pull_request`, `push`, `workflow_dispatch`, `issues`, `PULL_REQUEST_TARGET`, empty | TESTED | REJECTED |
| 7 | Action replay: `synchronize`, `edited`, `reopened`, `closed`, `ready_for_review`, `converted_to_draft`, missing | TESTED | REJECTED |
| 8 | Malformed SHAs: 39/41 chars, uppercase, non-hex, `HEAD:x`, `a/b`, `--upload-pack=…` | TESTED | REJECTED at 40-hex check **before any git argv** |
| 9 | `head_sha == base_sha` | TESTED | REJECTED |
| 10 | Extra changed file alongside request | TESTED | REJECTED (diff ≠ single `A\t` line) |
| 11 | Modify existing file alongside request | TESTED | REJECTED |
| 12 | Delete another file alongside request | TESTED | REJECTED |
| 13 | Rename to request path (`--no-renames` → A+D) | TESTED | REJECTED |
| 14 | Symlink (120000) at request path | TESTED | REJECTED (`100644 blob` prefix check) |
| 15 | Executable (100755) | TESTED | REJECTED |
| 16 | Submodule gitlink (160000) | TESTED | REJECTED (`cat-file -t` = commit) |
| 17 | Directory tree at request path | TESTED | REJECTED (diff shows inner path) |
| 18 | Request file present but **modified** (M not A) | TESTED | REJECTED |
| 19 | Oversized blob (valid JSON +600B) / 513B boundary | TESTED | REJECTED |
| 20 | Exactly 512 bytes (valid JSON + spaces) | TESTED | ACCEPTED (boundary correct) |
| 21 | Empty blob | TESTED | REJECTED |
| 22 | Duplicate JSON keys | TESTED | REJECTED (`no_duplicate_keys` hook) |
| 23 | UTF-8 BOM / raw NUL byte / non-object JSON (`[]`,`null`,`123`,`"str"`,`{}`,`true`) | TESTED | REJECTED (all) |
| 24 | JSON-escaped `\u0000` in task | TESTED | REJECTED (not in allowlist) |
| 25 | Task strings: `bash`, `task;id`, trailing space, uppercase, `../x`, embedded `\n` | TESTED | REJECTED (all) |
| 26 | Extra field (`cmd`), missing field | TESTED | REJECTED |
| 27 | Wrong schema (v0.3, trailing space, empty, null) | TESTED | REJECTED |
| 28 | `candidate_head` = workflow HEAD `2a950f4…` (not the runner pin `6fb7254…`), zeros, uppercase, non-str | TESTED | REJECTED (pins runner's frozen SHA exactly) |
| 29 | Title mismatch / leading space / task-mismatch | TESTED | REJECTED |
| 30 | Type confusion: `number:true`, `user:"Haneof"`, `sha:null`, `pull_request:null` | TESTED | REJECTED |
| 31 | Bad remote origin URL | TESTED | REJECTED |
| 32 | Checkout HEAD ≠ event base.sha | TESTED | REJECTED before head use |
| 33 | Unfetchable/unknown head SHA | TESTED | REJECTED (fetch fail-closed) |
| 34 | e2e `main()`: GITHUB_OUTPUT = exactly `task=gateway-selftest\n` (no injection); reject path writes nothing, exit 2, `REJECTED`/`NO_TASK_EXECUTED` | TESTED | PASS |
| 35 | **Real GitHub data**: historical probe heads `2de7ef27…` (#380), `a14d7cf…` (#381) fetched from live origin as git data only, real `remote=https://github.com/Haneof/Haneof-AIOS-Core-v3.0.git` | TESTED | **ACCEPTED** `task=pr370-artifact-audit` (both) |
| 36 | Negative controls on those real heads: author `mallory`; title `[AIOS-GW-V04] gateway-selftest` | TESTED | REJECTED (both) |
| 37 | Same-repo `pull_request` job runs head code (standard CI) | SI | read-only token, `contents: read`, no secrets referenced; only repo owner can create same-repo branches |
| 38 | `.gitattributes`/textconv/driver code-exec via `git diff` | SI | `--no-ext-diff`; drivers require trusted config; only `--name-status` parsed |
| 39 | GITHUB_OUTPUT/workflow-expression injection | SI + TESTED | allowlisted literal; ints in names; quoted env; argparse re-check |
| 40 | Live `pull_request_target` dispatch, real Arena task PR, live artifact from privileged job | **B / NOT_TESTED** | requires activation + G4 (explicitly out of scope; `owner-pr-readonly-dispatch=SKIPPED` in ordinary CI provides zero such evidence) |
| 41 | CI **raw job-log zip** and **artifact zip byte content** | **B (partial)** | sandbox egress blocks `results-receiver.actions.githubusercontent.com` + `*.blob.core.windows.net`; compensated per §6.3 |

Commands (representative; all exit codes recorded in my session): `git diff-tree -r …` (0), `python3 -I -m unittest discover -s tests/agent_gateway -p 'test_*.py'` → `Ran 63 tests … OK` (0), `python3 -I adversarial_pr_request.py` → `Ran 41 tests … OK` (0), `python3 -I real_github_validation.py` (0, output above), `python3 -I tools/agent_gateway/runner.py --task {each of 5}` → `PASS` ×5 (0 ×5).

## 4. Independent five-audit execution (not a rehash of author claims)

Ran the exact trusted-base `runner.py` five tasks myself against live GitHub pinned refs (branch `c15-rerun005-signed-ttyless-window66` still == `6fb7254…`; Window67 evidence ref pinned):

- `gateway-selftest` **PASS**, `pr370-source-boundary` **PASS**, `pr370-artifact-audit` **PASS**, `pr371-evidence-integrity` **PASS** (154 members, `immutable_members:PASS`, 723,754 verified bytes), `r005-binding-ledger` **PASS**.
- Receipts `result.json`/`junit.xml`/`SHA256.json` self-hashes all verified OK (10/10 files). All receipts carry `classification=NON_FORMAL_PUBLIC_CI_EVIDENCE`, `window69_formal_validation=NOT_PERFORMED`, `real_resident_started=false`, `merge_authorized=false` — the runner does not overclaim.

## 5. Findings (CVE-style; no exploitable defect found)

**F0 — none.** No HIGH/MEDIUM/LOW exploitable vulnerability identified in the candidate. All tested bypass classes fail closed.

Residual hardening observations (INFO, non-blocking):

- **F1 (INFO, supply chain)**: `actions/checkout@v4`, `actions/setup-python@v5`, `actions/upload-artifact@v4` are tag-pinned, not commit-SHA-pinned (workflow lines 36/42/54, 68/73/118). Reproducibility/supply-chain hardening candidate; consistent with repo convention. No immediate exploit.
- **F2 (INFO, event semantics)**: privileged job `if` does not exclude draft PRs (`github.event.pull_request.draft` unchecked). Impact limited to the trusted owner's own drafts; gate stays owner-only. Consider `&& !github.event.pull_request.draft` for exactness.
- **F3 (INFO, robustness)**: `pr_request.py` `main()` catch-set omits `RecursionError` (deeply nested JSON within the 512-byte cap). Process would exit non-zero with traceback → workflow step fails → runner step does not execute (`if: success()` default) — still fail-closed; catch-set widening would just tidy error reporting. (`pr_request.py` line ~168 `except (BadPrTask, KeyError, TypeError, UnicodeError, ValueError, OSError)`).
- **F4 (INFO, provenance)**: merge commit `2a950f4…` is **unsigned** (parent `528296d…` is GitHub web-flow signed). Provenance = TLS fetch from the official origin + PM-pinned SHA. A signed merge/attestation would strengthen the chain.
- **F5 (INFO)**: origin check is textual (`rstrip("/")` + one `.git` strip). Equivalent URL spellings are rejected — fail-closed, fine.

## 6. Independent CI / artifact reading (Run 39010003206)

### 6.1 Verified against GitHub API + public run page (independent of author comments)

- Run `39010003206`: workflow `aios-remote-agent-pr-inbox-v04`, event `pull_request` (displayed "synchronize #376"), head SHA **exactly** `2a950f4ce78fe7d3e55ff103bd7d95bfcf8109c7`, conclusion `success`, 12s.
- Job `public-policy-ci` (id 117330351019) `success` — all steps success incl. `Run public no-credential gateway tests` and `Preserve public unit-test receipts`.
- Job `owner-pr-readonly-dispatch` (id 117330352140) **`skipped`** — confirming the PM statement: this ordinary PR CI provides **zero** real `pull_request_target` dispatch / Arena integration evidence. `G4=NOT_TESTED`.
- Artifact `aios-pr-inbox-policy-39010003206-1`, id `12092885601`, 9,069 bytes, GitHub digest **`sha256:7513158bebcf4e902df91d8e0342d9f387ff1e3cf50f2d55f807ac2e392ad77e`** — matches the PM-pinned digest exactly (API and public run page agree).
- Benign annotations only: Node20 action deprecation + ubuntu-latest migration notice.

### 6.2 What the CI run does and does not prove

- Proves: at exact head `2a950f4…`, the non-privileged policy CI (63 synthetic policy tests + 5 fixed public audits) is green and produced the pinned artifact.
- Does NOT prove: any live `pull_request_target` `opened` dispatch, privileged job behavior, or Arena-created request routing (job skipped by design; no such event exists).

### 6.3 Evidence-limited sub-item (explicit BLOCKED disclosure)

Raw job-log zip and artifact **byte content** could not be downloaded from this sandbox: log/artifact storage hosts (`results-receiver.actions.githubusercontent.com`, `productionresultssa17.blob.core.windows.net`) are outside the sandbox egress allowlist (HTTP EOF at fetch; reproduced twice; `gh run view --log` and `gh run download` both fail at redirect target). Compensating controls: (a) job/step conclusions via REST API, (b) public run-page artifact name/size/digest (digest = GitHub-computed SHA-256 over the artifact — matches the PM pin byte-exactly), (c) **independent local reproduction**: `Ran 63 tests … OK` and five `PASS` audits re-executed by me on the exact candidate bytes with self-verified JSON/JUnit/SHA256 receipts. If byte-level artifact/log inspection is a hard PM gate, that single sub-item is `PARTIAL/BLOCKED` and requires an operator with Actions-download egress; it does not change the candidate-safety verdict.

## 7. Residual risks / uncertainty

1. Live `pull_request_target` behavior (GitHub-side path-filter/`opened` semantics under real event delivery) remains untested until authorized G4 activation; my assessment of those semantics is source-inspection + documented GitHub behavior, not observed execution.
2. Trust root = GitHub account `Haneof` + GitHub platform integrity + the pinned SHAs; compromise of the owner account is out of scope by definition (owner-authored gate).
3. Artifact/log byte-content gap (§6.3).
4. Floating action tags (F1); unsigned merge commit (F4).
5. `runner.py` audits are explicitly NON_FORMAL: seven historical RERUN-005 failures remain binding; Window69 formal validation NOT_PERFORMED — nothing in this review changes that.

## 8. Verdict

- **`REVIEW_PASS`** for the exact candidate `2a950f4ce78fe7d3e55ff103bd7d95bfcf8109c7` vs base `528296def47f8f409350889f11961ebedc4a38c2`: the four-file v0.4 diff is scope-exact, the `pull_request_target` design is fail-closed and runs trusted-base code only, malicious-input classes tested (2–36) all reject, and the five-task policy CI is independently reproducible.
- **`G3_REVIEW_CONDITION`: MET** as an independent-review input — subject to PM's standing rule that this AI review is not an accredited acceptance and that **activation requires a separate explicit PM/user exact-HEAD decision**.
- **`G4 = NOT_TESTED`**; DO NOT MERGE #376/#370/#371/#367; no workflow activation performed or requested.

— Arena Agent Mode independent reviewer, 2026-10-17 UTC. Test harnesses and candidate extracts held out-of-tree (`/tmp/gw-review/`, `/tmp/review-candidate/`); the sole repository change is this evidence-only report file.
