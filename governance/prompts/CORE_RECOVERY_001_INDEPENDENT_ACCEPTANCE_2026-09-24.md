# CORE-RECOVERY-001 INDEPENDENT ACCEPTANCE

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Role:
Independent Storage / Runtime Recovery Acceptance Reviewer

Candidate:
- PR #191 — `[REVIEW_READY] CORE-RECOVERY-001: storage/runtime recovery closure`
- tested implementation exact head:
  `58b6b5e2e653e258e778a0f2dd3d77978cd585ff`
- evidence-only handoff:
  `f90b93608a13f9e04ff9b7997f2b4f92b5331f88`

Your only task is to independently decide whether CORE-RECOVERY-001 is safe, mechanically correct, non-destructive, and compatible with the already accepted World / HEADLESS / FIX-001 / FIX-002 / FIX-003 semantics.

You are not:
- PR #191 author
- CORE-RECOVERY-001 engineer
- AIOS total PM
- Resident
- Semantic Evaluator
- UI/hardware engineer

This window:
- acceptance only
- no candidate repair
- no merge
- no CORE-SCALE-001
- no RC-FREEZE
- no Resident
- no UI/hardware

## Start

1. Fetch current live `main`.
2. Read:
   - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
   - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
   - `PROJECT_MASTER_MAP.md`
   - `governance/AIOS_CORE_COMPLETION_PLAN_2026-09-24.md`
   - `governance/prompts/CORE_RECOVERY_001_2026-09-24.md`
   - `governance/CORE_HEADLESS_001_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_GAP_FIX_001_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_GAP_FIX_002_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_GAP_FIX_003_INTEGRATION_RECEIPT_2026-09-24.md`
   - `reviews/CORE_RECOVERY_001_COMPLETION_EVIDENCE_2026-09-24.md`
   - PR #191 current body/diff.
3. Confirm:
   `CORE-RECOVERY-001 = GATE / REVIEW_READY`.
4. Pin both heads above.
5. Verify `58b6b5e2... -> f90b9360...` changes only:
   `reviews/CORE_RECOVERY_001_COMPLETION_EVIDENCE_2026-09-24.md`.

If implementation head changes, do not inherit this evidence.

## Candidate scope

Expected implementation/test/workflow delta from construction main
`06b3a98fd3c098f861f49ab936500f81de030991`
to tested exact head is exactly:

1. `.github/workflows/core-recovery.yml`
2. `src/aios_core/headless/cli.py`
3. `src/aios_core/headless/recovery.py`
4. `src/aios_core/storage/sqlite_store.py`
5. `tests/integration/test_core_recovery.py`

The evidence-only file is layered above the tested implementation head.

Fail scope review if candidate creates:
- second World / recovery truth store;
- second provider-attempt ledger;
- second turn recovery ledger;
- log-as-truth recovery;
- destructive clear-and-retry;
- new identity to evade IN_DOUBT;
- automatic provider retry after ambiguous execution.

## Recovery architecture invariants

The canonical SQLite World remains truth.

Verify:
- World history/revisions remain append-only;
- search index remains rebuildable cache/projection;
- backup files are immutable snapshots, not an active second truth store;
- recovery status/log output is observational only;
- FIX-002 background attempt ledger remains provider-execution truth;
- FIX-003 turn execution identity remains stable;
- FIX-001 historical knowledge cutoff is not replaced by current-time replay.

## R1 — SQLite transaction / WAL crash safety

Freshly fault-inject disposable Worlds.

Prove:
- abrupt process death before commit produces no partial fabricated object/revision;
- committed transaction survives abrupt process death and reopen;
- reopened SQLite quick_check is OK;
- World revision/history is coherent;
- no repair code manually edits durable history to manufacture the expected result.

At least one probe should use a real child process / abrupt exit rather than only exception rollback in one process.

## R2 — durable World write failure boundaries

Independently inspect existing retained recovery tests plus candidate interactions.

Verify failures around:
- user input/output persistence;
- metering after provider response;
- completion marker persistence;
- durable assistant output reconciliation.

Requirements:
- no false completed state if required durable write failed;
- no duplicate assistant output;
- no duplicate metering;
- same execution identity is retained;
- provider is not blindly reinvoked.

If already safe, PASS / ALREADY_SAFE is correct; no code change is required.

## R3 — FIX-003 user-turn restart recovery

Freshly verify at least:
- pre-admission crash;
- definitely-not-submitted + explicit authorization;
- ambiguous post-dispatch IN_DOUBT;
- response-returned recovery;
- assistant-output persistence failure;
- completion recovery idempotence;
- conflicting input fail-closed.

No recovery command may mint a new turn/attempt identity to bypass ambiguity.

## R4 — FIX-002 background recovery

Verify Wake and Periodic Review recovery:
- pre-dispatch failure;
- ambiguous dispatch remains IN_DOUBT;
- response-returned/persistence failure reconciliation;
- metering/completion recovery;
- no blind provider reinvocation.

## R5 — FIX-001 temporal cut during resumed recovery

Freshly verify a historical T1 Wake/Review resumes after restart while T2 data/support now exists.

The model-visible T1 execution must still exclude T2-only data/support.

Recovery must not silently become “rerun using current World knowledge”.

## R6 — index loss / stale / corrupt rebuild

Independently test:
- missing index;
- stale watermark;
- corrupt/unopenable index;
- future/invalid watermark where applicable;
- rebuild from World;
- strict search after rebuild;
- World revision unchanged by rebuild;
- rebuilt watermark equals World revision.

Adversarially interrupt rebuild around staged construction/publication.

Required safety:
- canonical World is untouched;
- index remains disposable cache;
- restart can safely rebuild again;
- no partially rebuilt index is treated as World truth.

## R7 — backup / restore

Critically inspect the new backup/restore implementation.

### Backup
Verify:
- canonical writer lease is acquired;
- SQLite online backup API is used instead of raw live WAL file copy;
- source passes integrity check;
- staged snapshot is validated;
- snapshot revision/schema match source;
- existing destination is never overwritten;
- backup includes SQLite-resident execution/attempt/metering state, not only WorldObject tables.

### Restore
Verify:
- source backup is read/validated without mutation;
- restore only targets a new World path;
- existing target/WAL/SHM is refused;
- staged restore is validated before publication;
- source backup bytes/hash remain unchanged;
- restored World revision/history/object revisions match;
- provider-attempt/turn/metering state survives;
- index can be rebuilt from restored World and is not required as backup truth.

Freshly test source backup hash before/after restore.

## R8 — schema compatibility

This is a high-priority acceptance area.

Verify exact call order in `SQLiteWorldStore`:
- future-schema preflight uses read-only SQLite open;
- future `user_version > CURRENT_SCHEMA_VERSION` is rejected before writable open / WAL mode;
- rejected future World bytes and filesystem sidecars remain unchanged/non-created;
- current schema opens normally;
- legacy v0 -> v1 supported path is idempotent;
- schema version is published only after supported migration/current DDL completes;
- injected migration failure does not leave `user_version=1` falsely published.

Do not accept merely because the error message says “fail closed”.

## R9 — interrupted maintenance

Fresh fault injection must cover interruption/failure around:
- backup publication;
- restore publication;
- index rebuild publication.

Verify:
- source World/backup remains unchanged;
- an operation that throws does not falsely report success;
- restart/retry is safe;
- existing destination is not overwritten;
- any already-published artifact after a late fsync failure is treated conservatively and not silently deleted/replaced.

The candidate explicitly documents a late-fsync limitation; judge whether behavior is fail-closed and truth-preserving, not whether every filesystem can guarantee impossible semantics.

## R10 — operational recovery surface

Verify installed `aios-core-headless`:
- `recovery-status`
- `backup`
- `restore`
- `rebuild-index`
- retained `inspect-turn`

Mechanical recovery commands should not require a model provider unless semantically necessary.

Verify operational classifications:
- ambiguous provider `TimeoutError` after dispatch -> `reconciliation_required`;
- this classification change does NOT cause automatic retry;
- recovery status distinguishes rebuild/fatal/reconciliation states without exposing hidden chain-of-thought.

## Canonical writer lease compatibility

Because recovery operations can mutate files mechanically, verify they respect accepted HEADLESS writer exclusion.

Fresh probe:
1. hold a live HeadlessCore writer on a World;
2. attempt backup/rebuild/recovery operation against the same World;
3. operation must not bypass the canonical writer lease;
4. after writer stops, the recovery operation may proceed.

Do not introduce a second maintenance lock identity.

## Recovery disposition contract

Independently verify the completion evidence classifications:

- SQLite uncommitted crash -> AUTO_RECOVERABLE
- committed WAL crash -> AUTO_RECOVERABLE
- proven pre-attempt/not-submitted -> RETRY_WITH_EXPLICIT_AUTHORIZATION
- ambiguous provider dispatch -> IN_DOUBT_MANUAL_RECONCILIATION
- durable output / missing completion marker -> AUTO_RECOVERABLE
- index loss -> REBUILD_FROM_WORLD
- future/corrupt incompatible World -> FATAL_INCOMPATIBLE
- interrupted mechanical recovery before safe publication -> safe restart/retry without history rewrite

Fail if ambiguous provider execution is classified AUTO_RECOVERABLE.

## Exact-head CI

Re-read raw logs tied to exact implementation head
`58b6b5e2e653e258e778a0f2dd3d77978cd585ff`.

Required:

### core-recovery
run `35998900821`
- fault injection job `107630398418`
- clean restart process proof `107630398731`
- retained regressions `107630398704`

PM pre-check:
- fault injection 12/12 PASS
- retained recovery regressions 193 pass markers
- process proof SUCCESS

### full P16
run `35998900838`
job `107630397697`

PM pre-check:
- direct `pytest -q`
- 100%
- 687 pass markers
- 0 failure/error markers
- SUCCESS

Also independently verify:
- core-headless `35998900833 / 107630397105`
- world-kernel `35998900847 / 107630397780`
- world-index `35998900841 / 107630396863`
- constitutional cognition `35998900832 / 107630396989`
- C14 scheduler/runtime workflow `35998900826` and its relevant jobs.

## Development-time red evidence

Do not erase red history.

The author reports:
- initial recovery run `35997231887` exposed two bad new test expectations and a real CLI classification gap;
- ambiguous `TimeoutError` was durably IN_DOUBT but surfaced as generic operation_error;
- later a backup fault test patched an obsolete publication primitive and was corrected to the actual no-overwrite path.

Independently inspect enough evidence to distinguish:
- real implementation bug fixed,
- bad test expectation corrected,
- final fresh exact-head evidence.

Do not accept a rewritten-red-as-green narrative.

## Fresh adversarial probes

Perform fresh independent probes, not only author tests.

At minimum include four:

### Probe A — future schema non-destructive refusal
Create disposable future-version World, hash/stat it and sidecars, attempt normal open, verify refusal before writable/WAL mutation.

### Probe B — live WAL backup / restored ledger equivalence
Create World with:
- one successful metered turn;
- one durable IN_DOUBT attempt.
Backup using supported command, restore separately, rebuild index, compare key World/execution/attempt/metering counts and IDs.

### Probe C — interrupted index rebuild
Inject failure after staged rebuild but before/around publication; verify World revision unchanged and subsequent clean rebuild succeeds.

### Probe D — recovery command vs live writer lease
Hold live canonical writer; attempt same-World backup/rebuild; verify writer exclusion fails closed, then succeeds after release.

Strongly recommended:
### Probe E — migration marker failure
Inject supported v0 migration failure before version marker; verify `user_version` is not falsely advanced to current.

If a probe PR is created:
- probe-only;
- do not modify #191;
- close unmerged after evidence capture.

## Live-main drift

If main advanced after construction:
- governance/review-only drift does not require rebase;
- any relevant `src/**`, storage schema contract, HEADLESS/recovery test contract, packaging, or workflow semantic change requires explicit revalidation and may yield `REBASE_REVALIDATION_REQUIRED`.

## Verdict

### ACCEPTANCE_PASS
Only if:
- R1-R10 are independently supported;
- real recovery gaps are closed without second truth store;
- backup/restore is coherent and non-destructive;
- future schema refusal is genuinely pre-write;
- index recovery is World-derived and restart-safe;
- FIX-001/002/003 behavior is preserved;
- ambiguous provider execution remains IN_DOUBT / no blind retry;
- canonical writer lease is respected by recovery operations;
- exact-head recovery/HEADLESS/World/C14/constitutional/P16 Gates PASS;
- fresh adversarial probes PASS;
- no semantic live-main drift invalidates candidate;
- blockers = 0.

### ACCEPTANCE_FAIL
Any real recovery/storage blocker.

### REBASE_REVALIDATION_REQUIRED
Only when a new relevant semantic main change materially invalidates the pinned candidate.

## Report

Create:
`reviews/CORE_RECOVERY_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

Create one review-only PR from review-time live main.

Report:
- review-time main
- PR #191
- exact implementation head
- evidence-only handoff
- candidate scope
- R1-R10 verdict table
- recovery disposition verdict
- backup/restore verdict
- index recovery verdict
- schema compatibility verdict
- FIX-001/002/003 compatibility
- writer lease compatibility
- fresh adversarial probes
- exact-head CI
- full P16
- red-evidence review
- live-main drift
- blocker count
- final verdict

Do not merge PR #191.

If PASS, state:

`PR #191 CORE-RECOVERY-001 tested exact implementation head 58b6b5e2e653e258e778a0f2dd3d77978cd585ff with evidence-only handoff f90b93608a13f9e04ff9b7997f2b4f92b5331f88 is independently accepted for PM integration.`
