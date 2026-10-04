# CORE-RC-REFREEZE-004 — Window 25 Fresh Independent Acceptance

## Verdict

**ACCEPTANCE_FAIL**

**blocker=3**

**CORRECTIVE_OR_ADJUDICATION_REQUIRED**

The exact software freeze is internally consistent and the frozen Core passed every fresh reviewer-owned functional and security run. Acceptance nevertheless fails because the candidate's formal workflow contains three independently reproducible false-green paths. This review does not repair the candidate and does not authorize merge, Resident, evaluator, public release, or tag.

## Blocking findings

### IA25-BLK-001 — C15 pytest exit laundering

- Severity: **HIGH**.
- Violated invariant: a pytest collection, usage, internal, interruption, or no-tests failure must fail the formal gate; downstream-debt classification may accept only an intentionally adjudicated test-failure result.
- Exact source: `.github/workflows/core-rc-refreeze-004-formal-gate.yml:324-342` at candidate `70134269ddfc7c80c4a703a933253bd099746504`.
- Mechanical reproduction: run `workflow_false_green_probe.py` (SHA-256 `fc7df49fdc80b340d2ddc065ad87c01c81987bef78f13fd6494ab035613796a9`). It feeds the candidate's exact classifier a simulated pytest exit `4` with a usage error and no `FAILED ...` summary records.
- Expected: classifier exits non-zero and blocks the job because pytest did not produce an adjudicable downstream test-failure result.
- Actual: classifier exits zero and prints both `CORE_FREEZE_NOT_BLOCKED_BY_DOWNSTREAM_OPERATOR_DEBT` and `C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT`.
- Why the author gate missed it: `rc=${PIPESTATUS[0]}` is printed but never used in the decision. The only rejection is a parsed `FAILED` path outside `tests/c15_persistence/`; exit codes 2–5 with no such records are laundered to GREEN.
- Independent evidence: `workflow-false-green.txt`, `workflow_false_green_probe.py`, and `WORKFLOW_ATTACK_FREEZE.md`.

### IA25-BLK-002 — write credential exposed across candidate-controlled execution with no terminal head check

- Severity: **HIGH**.
- Violated invariant: release probes must not receive repository-write authority; the candidate branch and frozen target must remain immutable throughout the formal run; a mutable branch input cannot be treated as exact-head evidence without a terminal equality check.
- Exact source: workflow lines `9-10` (`contents: write`), `44-47` (`actions/checkout@v4` with default credential persistence), `62-64` (the only remote-head check, before all tests), and `302-311` (candidate-carried executable probe). `workflow_dispatch` at lines `7-8` is also not restricted to the canonical branch.
- Mechanical reproduction: hosted job `111468269854` logs show `persist-credentials: true` and local `http.https://github.com/.extraheader AUTHORIZATION: basic ***`; it is removed only in the post-checkout step after all probes. In a disposable fork, a candidate-carried probe can mechanically show the extraheader with `git config --local --get-regexp 'http.*extraheader'` and, because the job grants `contents: write`, push a ref before job completion. The workflow performs no final `ls-remote == GITHUB_SHA`, no frozen-worktree-cleanliness check, and no final object-identity recheck.
- Expected: `permissions: contents: read`, `persist-credentials: false`, canonical-ref assertion for every entry path, and terminal candidate/frozen-object equality checks.
- Actual: write authorization remains available to every executed repository test and candidate probe; only a pre-execution branch-head comparison exists.
- Why the author gate missed it: exact-head validation is front-loaded and checkout authentication is left at its write-capable default.
- Independent evidence: `workflow-false-green.txt` plus the exact hosted-job log facts recorded there. The exact candidate probe was inspected and no malicious push was found; the blocker is the gate's admitted false-green/write path, not a claim that run `37213157986` exploited it.

### IA25-BLK-003 — mandatory external-pin comment publication failure is non-fatal

- Severity: **HIGH**.
- Violated invariant: the declared two-layer manifest design requires the post-run exact candidate/run pin to be durably published; failure to create that pin must prevent a successful formal gate.
- Exact source: workflow lines `402-445`, especially `set -uo pipefail` at `409` and `test "$code" = "201" || cat ...` at `445`.
- Mechanical reproduction: `bash -c 'set -uo pipefail; code=500; test "$code" = 201 || printf "simulated-comment-error\n"; printf "shell_exit=%s\n" "$?"'` returns `shell_exit=0`.
- Expected: any HTTP status other than 201 exits non-zero.
- Actual: the `cat`/diagnostic succeeds and becomes the step's final zero status, so the job can be GREEN with no required commit comment.
- Why the author gate missed it: the step deliberately omits `-e` but does not explicitly exit after the failed status test.
- Independent evidence: `workflow-false-green.txt`. The exact hosted run happened to receive HTTP 201 and its comment exists; this does not remove the false-green path.

## Fresh ground truth and candidate pin

- Fresh `git fetch --all --prune` live main: `deacf7d55c4c68fdf4580c02a4838f6c9cda1952`, message `Merge PR #327 governance: release CORE-RC-REFREEZE-004 Fresh IA Window 25`.
- Board/checkpoint/entry/release/prompt were read from fresh main. `CORE-RC-REFREEZE-004-INDEPENDENT-ACCEPTANCE = READY` was confirmed.
- PR #325: **OPEN**, non-draft, unmerged, title contains **DO NOT MERGE**; branch `release/core-rc-refreeze-004-window24`.
- Head: `70134269ddfc7c80c4a703a933253bd099746504`.
- Parent: `b295e6a83b345864b40d6a731fb25812c0ed9ad4`.
- Tree: `5727143aa14359d67defb41113b46d6759ad7f2e`.
- PR #326: **CLOSED**, unmerged, `b7820282cb2ca0f6ee071940baeed873ab5af4a1`; duplicate/superseded/non-canonical. No new competing canonical RC004 candidate was found.

## Frozen software identity

All identities below were recomputed from Git objects; manifest text was not used as proof.

- Frozen software: `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`.
- Parents: `fb53cf938b138a67d1890618eed41282c61bce00`, `7ecb2250a488766915e1042a76472b3cd26d9107`.
- Repository tree: `70b2711258567863ea0d93025a6a07e39631726a`.
- `src/aios_core/**`: `16f1487e291b009c55bee402abfd79fdacbae960`.
- `tests/**`: `9db1bfa08143bc99fe03836e2752ee6e05694eb6`.
- `.github/workflows/**`: `72cde9d2dc2b35d071bfa36c954dac2faff4a803`.
- `pyproject.toml`: `b38833c7537fa60d5c2f02ed4bb19158d8995a11`.
- Constitution tree: `c4572dd929ec4d5510b9e08ae29fe9d4cdcf7bf3`.
- Core baseline blob: `e4af80b8b93d89df8f0229620f870c6d5855c381`.

## Scope, drift, and synthetic merge

- Candidate scope: exactly 22 changed files. All are regular mode `100644`; there are no symlinks, submodules, path tricks, `src/**`, product `tests/**`, `tools/**`, `pyproject.toml`, package implementation, or package metadata changes.
- Allowed locations only: the one RC004 formal workflow, two `release/rc/**` files, and nineteen `reviews/CORE_RC_REFREEZE_004/**` files.
- The evidence directory contains executable Python release-probe logic. Its exact source was inspected; it imports the frozen checkout through the configured target, does not import live main, does not write package implementation, and was not found to hide implementation contamination.
- Frozen software to fresh main: 14 commits and seven changed paths, all governance/checkpoint/release records. Protected drift is zero under `src/**`, `tests/**`, `pyproject.toml`, package implementation metadata, and existing implementation workflows.
- PR #321 commit `22aa00cb3793c252512142a1eae33ca8aae9d841` remains REVIEW_ONLY and is not in frozen software. Window 23 staging/publisher branches remain transport.
- Synthetic merge of fresh main plus PR #325 produced tree `ae129dbe0c36111afcc5e1335dbc044814138e24`. Its Core tree, tests tree, and pyproject blob are exactly the frozen identities above. Runtime/package software is unchanged by the merge.

## Manifest and external-pin ruling

The two-layer design itself is **unambiguous for the current exact candidate**:

- The tracked manifest explicitly declares `candidate_sha`, `candidate_parent`, `candidate_tree`, and `run_id` null with `PENDING_AT_MANIFEST_COMMIT_TIME`, and names the PR/commit-comment external pin.
- PR #325 body binds one exact head/parent/tree/run/artifact. The candidate commit has one bot commit comment created at `2026-10-04T15:35:05Z` binding run `37213157986`, head `70134269...`, and frozen software `1cee3c5a...`.
- The Actions run, artifact metadata, artifact content, remote branch, and PR head all bind the same head. No second exact candidate matches those layers.
- The tracked manifest alone is not sufficient and could be reused textually; the declared external layer removes that substitution only when the operator verifies PR head + run head + artifact digest together.

Ruling: **CURRENT_PIN_UNAMBIGUOUS / TWO_LAYER_BINDING_PRESENT**, subject to IA25-BLK-003 because the workflow does not mechanically require successful publication in every run.

## Formal run and workflow audit

- Workflow: `core-rc-refreeze-004-formal-gate`.
- Run: `37213157986`; event `push`; head `70134269ddfc7c80c4a703a933253bd099746504`; conclusion `success`; attempt 1.
- Run interval: `2026-10-04T15:28:53Z` to `15:35:11Z`.
- Remote branch and PR head still equal the run head; there is no later candidate commit.
- Formal environment: CPython 3.12.14, Pydantic 2.13.5, pytest 8.4.2, SQLite 3.45.1, OpenSSL 3.0.13, Ubuntu 24.04.5, kernel 6.17.0-1022-azure, x86_64.
- Checkout/ref selection, frozen object identities, main drift, candidate scope, test pipelines with `set -euo pipefail`, and final artifact content were otherwise mechanically consistent.
- False-green audit result: **FAIL**, for IA25-BLK-001/002/003.

## Four preserved REDs

Each run and its artifact was fetched independently; artifact ZIP SHA-256 matched its server digest.

1. `37210518501` at `dde4750b...`: exact failure was the textual `live_return` import audit matching generated `__pycache__/live_return.cpython-312.pyc`. The invariant was that authorization code must not consult the tombstone. The replacement parses Python AST imports and is equal-or-stronger for the actual semantic property without binary-name false positives. **Release-probe RED, not Core RED.**
2. `37210904177` at `39855999...`: the inherited RC003 backup probe required a local handler return to create a durable trusted receipt. Corrective-003 Route B intentionally forbids that authority. **Stale release probe, not Core RED.**
3. `37211071106` at `736e8fb9...`: same stale local-self-trust assumption after a release-evidence-only retry. The replacement requires a durable external verifier plus genuine proof and is stronger. **Stale release probe, not Core RED.**
4. `37211714127` at `669cb96e...`: the new probe required retired table `background_model_authenticity_authority`. Accepted design uses `background_model_return_verifiers`; the old authority is intentionally absent. **Freeze-probe defect, not Core RED.**

No replacement weakened the safety property: all replacements require external proof, fail closed without a verifier, reject conflicts/transplants, and preserve exactly-once effects.

## Frozen probes and reviewer-owned attacks

- Window 20 Suite A: canonical blob/hash matched; **4/0**.
- Window 20 Suite B: canonical blob/hash matched; **7/0**.
- Window 17: canonical blob/hash matched; **14/0**, including a real SIGKILL case.
- Exact identities are in `frozen-probe-identities.txt`; raw outputs are `frozen-suite-a.txt`, `frozen-suite-b.txt`, and `frozen-window17.txt`.

Reviewer-owned attack source was enumerated, expectation-frozen, and SHA-256 frozen before its first execution. Result: **6 test functions passed**, covering eight enumerated properties:

- alternate local/reflection/tombstone mint paths;
- forged-before-genuine and exact replay;
- changed canonical bytes and proof transplant;
- verifier-less fail-closed;
- competing genuine proofs / exactly one winner;
- receipt/handoff partial commit, crash before staging, backup, restore to a new path, immutable backup, index rebuild, winning exact-proof retry;
- consumed verifier with missing receipt or missing handoff;
- cloned/restored World, provider redispatch zero, meter/effect exactly once, no authority expansion.

Probe SHA-256: `0c4451747ad4cd8bd399aa7a56042959cd87ba0c2bbb75c1a52171b98099461f`.

## Fresh execution results

- Full Core regression: **928 passed / 0 failed / 0 errors** in 119.01s. This was a real run, not collection-count inference.
- Corrective-003 focused security: **214 passed**.
- Real process loss: **9 passed**; selected tests use actual SIGKILL/fresh processes and prove no provider, meter, or capability-effect duplication with converge/fail-closed behavior.
- Writer/restart/FIX/current-time/SCALE: **52 passed**; canonical writer exclusion, override resistance, stale-lock restart, FIX-001/002/003, current-time, no-second-truth-store, and scale semantic-equivalence were covered.
- Reviewer-owned attack set: **6 passed**.
- Clean wheel/headless: non-editable wheel built from frozen software; installed import resolved under the clean venv's `site-packages`; five separate CLI processes proved deterministic turn, World/index continuity, provider-free recovery status, and clean close/reopen. **WINDOW25_CLEAN_INSTALL_HEADLESS_PASS**. No Resident fixture and no real provider were used.

Reviewer environment uses the exact Python/Pydantic/pytest versions but not the hosted SQLite/OpenSSL/OS/kernel. Therefore: **REVIEWER_ENVIRONMENT_DEVIATION**. Exact details are in `environment.txt`; formal-runtime fidelity is claimed only for hosted run `37213157986`.

## Trusted-return and backup/restore ruling

Fresh static inspection plus the 214 security tests, frozen suites, SIGKILL tests, and reviewer-owned attacks establish:

- local self-trust cannot mint authority; `live_return.py` is an inert compatibility tombstone;
- authorization does not consult the tombstone;
- the sole active trust root is a pre-bound external verifier plus genuine proof;
- stage paths consume authenticated state and cannot mint it;
- verifier-less ambiguous recovery stays fail-closed;
- forged local provenance cannot poison a later genuine proof;
- genuine exact replay is idempotent; changed/conflicting/transplanted proofs fail closed;
- restored/cloned state does not enlarge trust; provider redispatch and duplicate meter/effect remain zero.

Ruling: **CORE_ROUTE_B_SECURITY_PASS** and **BACKUP_RESTORE_REBUILD_PASS**.

## C15 downstream ruling

Fresh local run: **44 failed / 33 passed / 1 skipped**. The one difference from formal **45 failed / 33 passed** is `test_environment_detach_and_reattach`, skipped locally because the environment cannot create the required `unshare` namespace; it failed in the hosted run. Every local failure remained under `tests/c15_persistence/**`.

Failure inspection shows the downstream operator still assumes that an ordinary in-process model handler/response-recorder path yields Core trusted-return receipt/handoff authority. This is visible in `tools/c15_persistence/operator_session.py`; the operator lacks the Route B external signer/proof path, so relay ACK and remote recovery sequences stop at `ack requires a durable application` or the explicit no-trusted-return fail-closed boundary. `tools/c15_persistence/**` is downstream tooling, not the shipped `aios_core` package, and all supported Core tests remain green. Restoring the old assumption would reintroduce the local self-trust vulnerability rejected by Corrective-003.

Ruling: **CORE_FREEZE_NOT_BLOCKED_BY_DOWNSTREAM_OPERATOR_DEBT** and **C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT**. No C15 repair was performed.

## RC impact and contamination

- **FRESH_A_REQUIRED**.
- **FRESH_OPERATOR_PREP_REQUIRED**.
- A-003/A-004 reuse is rejected: Corrective-003 changed Resident-visible trust and recovery semantics, and no equivalence proof meets the burden for reuse.
- Resident was not run.
- Open inventory contained 52 PRs. Required PR identities and Window 23 publication branches are recorded in `open-pr-contamination.txt`. Open PRs and historical branches are not accepted software.

## Manifest, SHA-256, artifact, and limitations

- Tracked RC manifest Git identities and source-manifest object sizes were recomputed and matched.
- All 20 tracked `SHA256SUMS` entries verified. Observation: that list omits itself and `reviews/CORE_RC_REFREEZE_004/probes/backup_restore_route_b.py`; the exact candidate Git tree still binds both bytes, but the release checksum index is not exhaustive.
- Formal artifact ID `11307078611`, name `core-rc-refreeze-004-evidence`, downloaded successfully. ZIP SHA-256 equals server digest `8c14ab631b361c57d5292fd94f6fde3755a215ed974d408574fa65c9b2bd4c7b`; 28 internal files and every runtime checksum entry were independently verified.
- Workflow Git blob: `43b4b31225a6851cb8b9378f665966bcf1034acb`.
- Packet retains all material limitations: direct `record_response` residual; no distributed multi-host HA guarantee; C15 downstream compatibility debt; no public release/tag; historical Resident evidence invalid for this RC; exact hosted-run-only formal runtime fidelity.

## Immutability and publication

- PR #325 head was checked at start, before/after testing, and again after final fetch: `70134269ddfc7c80c4a703a933253bd099746504` throughout. **NO_CANDIDATE_DRIFT**.
- Review branch: `review/core-rc-refreeze-004-ia-window25`.
- Exact technical evidence commit: `TO_BE_PINNED_BY_PUBLICATION_COMMIT`.
- Publication status: `PUBLICATION_PENDING`.
- The publication PR is REVIEW_ONLY / DO NOT MERGE and targets the candidate branch so it cannot be mistaken for an implementation merge.

## Final state

**ACCEPTANCE_FAIL**

**blocker=3**

**CORRECTIVE_OR_ADJUDICATION_REQUIRED**

**DO NOT MERGE.**
