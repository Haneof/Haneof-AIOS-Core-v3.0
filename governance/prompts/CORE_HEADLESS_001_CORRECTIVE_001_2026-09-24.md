# CORE-HEADLESS-001-CORRECTIVE-001

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Continue the existing:
- PR #181 — `CORE-HEADLESS-001: installable persistent headless Core entrypoint`
- branch `core-headless-001-20260924-sol`

Do not create a competing PR.
Do not restart CORE-HEADLESS-001 from scratch.

## Trigger

Independent acceptance PR #185 reviewed:
- tested implementation exact head: `a43c2e9408e51ec8812e9f6ec808a71401bc2841`
- evidence-only handoff head: `12928af4ffa40e70d9ae80124dab388a486f7097`

and returned:

`ACCEPTANCE_FAIL`

with exactly one blocker:

`CORE-HEADLESS-001-ACCEPT-BLOCKER-001`

### Blocker

Same durable World writer exclusion can be bypassed by configuring a different `lock_path`.

Current mechanism:
- `HeadlessConfig.world_path` is canonicalized;
- `HeadlessConfig.lock_path` remains independently caller-configurable;
- `_WriterLease` obtains an OS advisory lock on that caller-selected lock-file inode.

Therefore:

same `world.sqlite`
+
`writer-a.lock`

and

same `world.sqlite`
+
`writer-b.lock`

can both acquire independent OS leases.

Independent probe evidence:
- PR #184 — CLOSED / UNMERGED
- probe head: `f36665541742badde3b7c20e24528668b5ba3f59`
- run: `35992018738`
- job: `107608100032`
- targeted result: `.........F [100%]`
- sole failure: alternate lock path allowed a second writer.

Historical report:
`reviews/CORE_HEADLESS_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

## Required start

1. Fetch live `main`.
2. Read:
   - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
   - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
   - `PROJECT_MASTER_MAP.md`
   - `governance/prompts/CORE_HEADLESS_001_2026-09-24.md`
   - `governance/prompts/CORE_HEADLESS_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
   - `reviews/CORE_HEADLESS_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
   - PR #181 current body/diff.
3. Confirm:
   `CORE-HEADLESS-001-CORRECTIVE-001 = READY`.
4. Continue the original PR #181 branch.

Do not rebase solely because main contains later governance/review files.
If live main has gained relevant semantic `src/**`, packaging-contract, test-contract, or workflow changes, stop and report PM before proceeding.

## Only blocker to fix

The writer lease identity must be derived from the canonical durable World identity and must not be selectable independently by the caller.

For one canonical `world_path`, there must be exactly one writer-exclusion identity.

A caller must not be able to bypass exclusion by:
- choosing another `lock_path`;
- setting another `AIOS_LOCK_PATH`;
- using CLI `--lock` to select another unrelated lock inode.

## Minimal acceptable designs

Prefer the smallest correct repair.

### Option A — canonical derived lease path

Derive the lease path exclusively from canonical resolved `world_path`, e.g. the existing canonical companion:
`<canonical-world-path>.writer.lock`.

Any caller-supplied lock path that differs from the canonical derived path must be rejected explicitly with `HeadlessConfigurationError`.

The caller must never be able to select a second writer identity for the same World.

### Option B — equivalent unbypassable World identity lease

An equivalent design is acceptable if the actual OS exclusion identity is mechanically tied to the canonical World identity and cannot be changed by a diagnostic/configuration pathname.

Do not create a global lock registry or second truth store.

## Required invariants

Preserve:
- OS-held advisory lease as the actual liveness/exclusion primitive;
- lock file metadata = diagnostic only;
- stale lock-file contents without an active OS lease do not brick the World;
- failed competing startup does not mutate/reset World state;
- clean stop releases the lease;
- subsequent writer can open after release.

Do not replace the OS lease with PID-file parsing or lock-file-content truth.

## Required regression

Add a permanent regression for the exact blocker.

At minimum:

1. configure the same canonical World twice;
2. attempt to supply two different explicit lock paths;
3. prove the configuration cannot create two distinct writer lease identities;
4. while writer A is live, writer B must fail closed;
5. World revision/state must not change from failed B startup;
6. stop A;
7. B (using the valid canonical configuration) can then open.

If the chosen design rejects noncanonical lock paths at configuration construction, assert the explicit configuration error and separately retain the normal competing-writer test.

Also verify:
- stale canonical lock file with no OS lock remains reopenable;
- same world through relative/absolute path normalization resolves to one canonical lease identity;
- if practical in the current tests, a symlinked World path that resolves to the same target does not create a second lease identity.

Hard-link/distributed-host coordination is not required by this corrective unless the implementation explicitly claims support for it.

## CLI / environment contract

Review `--lock` and `AIOS_LOCK_PATH`.

They may be:
- removed as override mechanisms; or
- retained only as explicit validation/diagnostic inputs that must equal the canonical derived lock path.

They must not remain a way to select a different writer identity.

If behavior changes, update CLI help/tests/evidence accordingly.

## Do not expand scope

Do not redesign:
- World storage;
- index;
- FusedTurnRuntime/CognitiveRuntime;
- Wake/Periodic Review;
- FIX-001 temporal cut;
- FIX-002 background attempt recovery;
- FIX-003 user-turn recovery;
- metering/budget;
- model/provider abstraction.

Do not enter:
- CORE-RECOVERY-001;
- CORE-SCALE-001;
- RC-FREEZE;
- Resident;
- UI/hardware.

## Preserve all already-passing HEADLESS behavior

Revalidate:
- clean non-editable install;
- installed `aios-core-headless`;
- same-World restart continuity;
- A–F restart matrix;
- pending Wake restart;
- FIX-001 historical cut;
- FIX-002 IN_DOUBT no blind reinvocation;
- FIX-003 pre-admission authorization/recovery;
- no duplicate Wake/assistant output/metering;
- provider-neutral ModelHandler;
- no second runtime/World/recovery ledger.

## Exact-head revalidation

The old exact implementation head `a43c2e94...` is historical only after the corrective.
Its green runs do not authorize the corrected code.

Produce a new exact implementation candidate head and rerun at minimum:

- dedicated `core-headless` clean install / installed CLI / lifecycle / corrective tests;
- `world-kernel`;
- `constitutional-cognition-closure`;
- full P16 direct `pytest -q`.

Also rerun the existing runtime compatibility suite included by the HEADLESS workflow.

Record exact run/job IDs and environment versions.

## Evidence handoff

Update:
`reviews/CORE_HEADLESS_001_COMPLETION_EVIDENCE_2026-09-24.md`

Preserve historical pins:
- old implementation head `a43c2e9408e51ec8812e9f6ec808a71401bc2841`;
- old evidence head `12928af4ffa40e70d9ae80124dab388a486f7097`;
- blocker ID;
- failed acceptance #185;
- probe #184.

Then record:
- corrective mechanism;
- new exact implementation candidate head;
- exact corrective regression;
- clean install / CLI proof;
- A–F compatibility;
- exact run/job IDs;
- full P16 result;
- any new evidence-only handoff head if the evidence update is a commit above the tested implementation head.

Do not blur the tested implementation head with an evidence-only handoff commit.

## Handoff

At completion:
- update original PR #181 body;
- set author state `REVIEW_READY`;
- do not self-accept;
- do not merge;
- do not modify task board/checkpoint from the engineering branch;
- do not start CORE-RECOVERY-001;
- do not run Resident.

A fresh independent acceptance on the new exact implementation head is mandatory.
