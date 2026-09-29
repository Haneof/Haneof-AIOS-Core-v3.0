# C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 - RESUMED CANDIDATE PIN

**Role:** Release / Runtime Persistence Engineer.
**Scope:** resume the frozen WIP of PR #216 and close the five kill/restart
convergence gates K1-K5. Nothing else.

> A document cannot contain the hash of the commit that contains it. The
> candidate commit SHA and tree are therefore published on the branch tip and in
> the PR #216 comment. Every hash and proof below is reproducible from
> `reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_001/resumed/evidence/EVIDENCE_MANIFEST.json`,
> which is itself hashed (`EVIDENCE_MANIFEST.json.sha256`).

---

## 1. Historical frozen WIP vs resumed candidate (do not conflate)

| | historical frozen WIP | resumed candidate |
|---|---|---|
| commit | `6db057a5fddbaf403be8377682b81219a074fef6` | branch tip of `arena/01a0e31e-haneof-aios-core-v3-0` (see PR #216 comment) |
| status | preserved, immutable historical checkpoint | candidate under review |
| result | `CORRECTIVE_CONVERGENCE_BLOCKED` (`PCORE-BLK-001`) | K1-K5 converged (engineering env) |
| relationship | **ancestor** of the candidate (normal merge commit, no rebase/squash/force) | |

The candidate was produced by a **normal merge** of live `main`
(`56c01b919c397b67024df1acb320874144d87f42`) into the #216 branch. The merge is
main-authoritative for the task board / checkpoint / master map / governance
control entry; persistence tools, tests and preserved evidence keep the #216
content. `6db057a5...` is an ancestor of the candidate head.

Historical red evidence is untouched, byte-for-byte:
`frozen-attempt-01.log`, `persistence-attempt-01.log`,
`core-boundary-attempt-01.log`, `evidence/synthetic-core-boundary/**`, reply
SHA256 `5cfc42b2f36aba93f32045d8a40022ec8b9f99a669b51eab0d8b725cef10421f`,
result `CORRECTIVE_CONVERGENCE_BLOCKED`. New runs use new filenames under
`resumed/evidence/`.

## 2. Absolute invariants re-checked for the candidate

* `src/aios_core/**` diff vs the resume base: **0 files** (asserted by the
  evidence manifest and by the CI gate, which fails the build otherwise).
* No RELEASE-003, no B-RERUN-003, no real Resident B run, no real cursor 14
  reveal, no Independent Acceptance, no sealed-fixture modification, no A-003
  canonical evidence modification.
* Retired RERUN-002 identities remain permanently banned and are asserted so by
  test (`c15-rcc-res-b-rerun-002-65e6e826`,
  `c15-rcc-res-b-session-002-65e6e826` + its outstanding request identity).
* Authoritative non-ephemeral state only: the backend rejects `/tmp`,
  `/var/tmp`, `/dev/shm`, `/run`, tmpfs/ramfs backing mounts (checked against
  `/proc/self/mountinfo`), excluded snapshot components and symlink aliases that
  resolve outside the persisted workspace. Local `/home/user` is degraded to a
  disposable local cache/materialization target; the authoritative backend across
  Arena attachments is durable remote storage on GitHub (`origin`).

## 3. Frozen K1-K5 probe suite

Frozen **before** first execution: code complete -> `pytest --collect-only`
enumeration -> SHA256 -> commit -> only then run.

| revision | manifest SHA256 | outcome |
|---|---|---|
| 1 | `aa85573f2041ad24c2dcc9b00cdf9ce809aeb5f5c9f899564aef79e010f1553c` | **failed**, all 5 - harness pre-created the backend root that `RunBackend.create` correctly refuses to adopt. Run, log and hash preserved. |
| 2 | `dea5c179a78949bcb1380dd78f1806784b4f8d54ac2a05c1e8dbbb0a242619eb` | **5/5 PASS** (harness-only fix; rev1 was not edited) |

rev1 first-execution log:
`resumed/evidence/killpoint-probe-rev1-first-execution.log`.

Kill points (frozen enumeration, unchanged since the WIP):

| gate | window |
|---|---|
| K1 | after the cursor is durably revealed, before ingest |
| K2 | after the event is durably ingested, before provider dispatch |
| K3 | after the exact provider request is durably staged/exposed/dispatched, before any reply exists |
| K4 | after Core's trusted-return boundary durably authenticated the exact reply, before downstream application completed (the historical `PCORE-BLK-001` window) |
| K5 | after model/capability work is durably applied, before the cursor ACK |

Convergence invariant enforced by the harness (`assert_convergence`), which is
what "converged" means here:

* the acked cursor equals the revealed projection sequence and event id;
* `reveals`, `ingests`, `acks`, `observations_for_event`, `assistant_outputs`,
  `metering_rows`, `turns_completed` equal the uninterrupted baseline - so no
  second reveal, no duplicate ingest, no duplicate output, no duplicate ACK;
* `dispatch_ledger` and `capability_side_effects` equal the baseline - **above**
  baseline means a redispatch or a duplicated side effect, **below** means
  skipped work;
* any `no_core_receipt` or `authorize_skipped` recovery action fails the gate.

`terminal` / `in_doubt` is never counted as convergence: the harness fails on
any leftover doubt state, and no gate was relaxed to make a result pass.

K4 specifically returns to the **normal accepted Core runtime path**: the
operator reads Core's own trusted-return receipt, stages the exact durable bytes
through `stage_exact_background_response` and lets Core revalidate them via
`authorize_exact_response_recovery`. Post-K4 the run resumes with
`handler_rounds == [1]` - round 0 is never redispatched - and the capability
ledger is unchanged.

## 4. Gates the frozen WIP did not have

1. **Environment detach / re-attach and remote persistence**
   (`tests/c15_persistence/test_environment_reattach.py`,
   `tools/c15_persistence/remote_backend.py`).
   The WIP only proved process restart; the original incident was an
   *environment* loss. Furthermore, local `/home/user` is confirmed not to
   persist across new Arena execution environments. Therefore:
   - `/home/user` is degraded to a disposable local cache/materialization target.
   - The authoritative backend is durable remote storage on GitHub (`origin`),
     persisted under `refs/heads/persistence/<run_id>`.
   - The test proves both namespace-level detach/reattach AND remote backend
     round-trip durability where local cache is completely wiped, materialized
     from the Git ref, verified byte-for-byte (`verify_reattach`), and advanced
     to the next cursor. All pinned slots (World, search index, release state,
     current event, binding, projection, provider request, provider reply,
     mailbox, failure evidence, persistence journal) report `OK`.
2. **Production-wiring tests**
   (`tests/c15_persistence/test_operator_wiring.py`, 16 tests) over the real
   release operator and the real Core `FusedTurnRuntime` - durable path policy,
   exclusive create vs reopen, live-process lock ownership, identity mismatch,
   retired-identity ban, exact bytes + SHA256 and tamper detection,
   conflicting-reply refusal, interrupted-transaction rollback, state-machine
   skip prevention, generation immutability and re-verification, vanished/changed
   slot detection, Core receipt revalidation against an operator-forged proof,
   and source-level assertions that the journal is not a second semantic engine.
3. **Resident-visible surface proof**
   (`tools/c15_persistence/resident_surface_check.py`). The same synthetic event
   is run twice: once through the full wired production path, once through the
   same Core runtime with **no** backend, no relay, no sealing and no kill
   barriers. Result `RESIDENT_SURFACE_UNCHANGED`: byte-identical resident
   payload, projection, ingest receipt, 44-entry capability catalog, model round
   ordering, provider request bytes, provider reply bytes, directive semantics,
   capability side-effect count, assistant output, metering rows and world
   revision. Evidence:
   `resumed/evidence/resident-surface-no-change.json`.
4. **Formal CPython 3.12.14 gate**
   (`.github/workflows/c15-rcc-res-b-persistence-corrective-001-formal-gate.yml`).
5. **Platform Reattach Stage A / Stage B Runner**
   (`tools/c15_persistence/platform_reattach.py`). Separates execution into Stage A
   (durable remote push and parameter pinning) and Stage B (independent window reattach).

## 5. Environment identity

| | engineering (this sandbox) | formal |
|---|---|---|
| CPython | 3.11.2 | **3.12.14** (`actions/setup-python`) |
| pydantic | 2.13.5 | 2.13.5 (pinned) |
| pytest | 8.4.2 | 8.x (pinned 8.4.2) |
| interpreter | `/usr/bin/python3` | ubuntu-latest runner |

CPython 3.12.14 is not obtainable in this sandbox (python.org and the apt
mirrors are unreachable and the build headers are missing), so **per the task
owner's decision the formal gate runs in CI**. The workflow asserts the exact
`(3, 12, 14)` interpreter triple, `pydantic == 2.13.5` and `pytest 8.x` before
any test runs, then executes the frozen K1-K5 suite, the wiring tests, the
reattach tests, the resident-surface test, the historical journal tests, the
frozen E2E probe and the runbook lifecycle checker self-test, and fails if
`src/aios_core` has any diff.

**Local CPython 3.11.2 results are engineering evidence only and are not
claimed as a formal `REVIEW_READY` result.**

## 6. Fresh reruns of the frozen checks (this candidate)

* frozen E2E `reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/probe_e2e.sh`
  (unchanged) -> `ALL_CHECKS=158/158 FAILURES=0`
  (log: `resumed/evidence/frozen-e2e-probe-candidate-pin.log`)
* `runbook_lifecycle_checker.py --self-test` -> green,
  `RUNBOOK_SHELL_SEMANTICS_MUTATION_RED_PASS cases=82`
  (log: `resumed/evidence/runbook-lifecycle-checker-self-test-candidate-pin.log`)
* persistence test suites -> 5/5 K1-K5, 16 wiring, 4 reattach, 1 resident
  surface, 13 historical journal tests
  (log: `resumed/evidence/persistence-tests-candidate-pin.log`)

## 7. Platform Reattach Stage A / Stage B Architecture

* **Stage A (this session):**
  - Creates a fresh synthetic run in disposable local cache;
  - Advances at least one synthetic cursor through the fully wired pipeline;
  - Seals the generation and pins the run-state manifest;
  - Persists the complete authoritative run state to the remote backend (`refs/heads/persistence/<run_id>`);
  - Verifies that remote state exists and is readable;
  - Asserts that local worktree in the repository remains clean;
  - Fixes and outputs the 7 parameters;
  - Stops at `PLATFORM_REATTACH_STAGE_A_READY`.
* **Stage B (new independent window):**
  - Executed exclusively in a new Arena AI session;
  - Re-attaches to the run directly from the remote Git ref;
  - Proves true cross-attachment durability across execution environment destruction.

## 8. Status

`PLATFORM_REATTACH_STAGE_A_READY`

PR #216 remains a **draft** until the formal gate is green. Nothing here may be
merged or treated as self-accepted. Stage B must be executed in a separate Arena AI window.
read as Independent Acceptance, and no gate was relaxed to reach this state.
