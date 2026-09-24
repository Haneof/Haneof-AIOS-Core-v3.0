# CORE-RECOVERY-001

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Role:
Storage / Runtime Recovery Engineer

You are not:
- AIOS total PM
- Resident A/B/C
- Semantic Evaluator
- UI engineer
- hardware engineer
- a new runtime architect

Your only task:

> On the current accepted headless Core, fault-inject and close real recovery gaps across World/WAL, index, execution ambiguity, model failure, write failure, restart, backup/restore and schema compatibility without creating a second truth store or bypassing FIX-001/002/003.

This task is primarily recovery validation.
Do not invent code work when current mechanisms already recover correctly.
For every scenario: reproduce first, then classify:
- PASS / ALREADY_SAFE
- REAL GAP -> minimal repair
- OUT_OF_SCOPE with evidence

## Required start

1. Fetch current live `main`; never use a SHA from this prompt as a permanent baseline.
2. Read:
   - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
   - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
   - `PROJECT_MASTER_MAP.md`
   - `governance/AIOS_CORE_COMPLETION_PLAN_2026-09-24.md`
   - `governance/CORE_GAP_FIX_001_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_GAP_FIX_002_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_GAP_FIX_003_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_HEADLESS_001_INTEGRATION_RECEIPT_2026-09-24.md`
   - `docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md`
3. Confirm:
   `CORE-RECOVERY-001 = READY`.
4. Inventory current storage/recovery code and tests before modifying anything:
   - SQLite World transaction / schema / connection paths;
   - index watermark/rebuild/catch-up paths;
   - background-model attempt ledger and reconciliation;
   - user-turn execution recovery;
   - metering/budget persistence;
   - Wake/Periodic Review durable state;
   - HEADLESS start/stop/restart paths;
   - any existing backup, restore, schema-version or migration helpers.
5. Work from the latest main and use one new engineering branch/PR for CORE-RECOVERY-001.

## Non-negotiable architecture boundary

The canonical SQLite World remains truth.

Do not:
- create a recovery database that becomes second truth;
- clear recovery tables to make tests pass;
- mint a new turn_id / wake_id / attempt_id to bypass an ambiguous execution;
- rewrite historical World facts during recovery;
- treat index/log/cache as authoritative World truth;
- turn filesystem metadata or process logs into durable cognition truth;
- weaken FIX-001 temporal cut;
- weaken FIX-002 background IN_DOUBT fail-closed behavior;
- weaken FIX-003 user-turn pre-admission / IN_DOUBT behavior;
- add broad automatic provider re-invocation after ambiguous dispatch.

## Recovery matrix

Use disposable private Worlds only.
Never fault-inject against production/user Worlds.

### R1 — SQLite transaction / WAL crash safety

Test mechanical process interruption around durable World writes.

At minimum distinguish:
- transaction not committed -> no fabricated partial WorldObject/revision after reopen;
- transaction committed -> durable object/revision survives reopen;
- restart after WAL/journal recovery opens same World coherently;
- World revision/history remain internally consistent.

Do not manually edit a real World to simulate success.
Use controlled private-test fault injection.

### R2 — World write failure boundaries

Inject failures around writes needed by:
- normal user-turn durable input/output path;
- completion/reconciliation path where applicable.

Verify:
- no false completed state if required durable World write failed;
- retry/recovery uses the existing execution identity;
- no duplicate assistant output;
- no duplicate metering;
- no clear-and-retry workaround.

If current code already fails closed correctly, record PASS without changing it.

### R3 — FIX-003 user-turn recovery after restart

Cover at least:
- pre-admission crash;
- definitely-not-submitted;
- ambiguous post-dispatch IN_DOUBT;
- response-returned / durable response reconciliation;
- assistant-output persistence failure;
- completion recovery;
- conflicting input.

Restart must not create a blind provider re-call.
Use existing turn-execution and attempt stores.

### R4 — FIX-002 background recovery after restart

Cover Wake and, where applicable, Periodic Review:
- pre-dispatch failure;
- ambiguous dispatch -> IN_DOUBT;
- response returned but downstream persistence fails;
- metering/completion reconciliation;
- no blind model reinvocation after ambiguous dispatch.

The shared provider-attempt ledger remains authoritative for provider execution state.

### R5 — FIX-001 historical read cut during recovery

A resumed historical Wake/Review after process restart must still use the original execution knowledge cutoff.

Inject late-known T2 facts/support after the T1 execution boundary and verify resumed execution cannot see them.

Recovery must never mean “rerun at current knowledge time”.

### R6 — index loss / stale / rebuild

The World is truth; index is rebuildable projection.

Test:
- delete a disposable World index and reopen/rebuild;
- stale watermark / lag catches up;
- rebuilt search results agree with a clean rebuild/current World projection;
- rebuild does not mutate World revision/history;
- corrupt/unopenable index produces an explicit recovery path rather than silently becoming truth.

If current tooling lacks an auditable offline rebuild path, implement only the minimal recovery command/API needed.

### R7 — backup / restore

Establish a documented, mechanically safe backup/restore path for the current SQLite World.

At minimum verify on disposable data:
- backup captures a coherent World snapshot;
- restore opens successfully through normal HEADLESS/Core paths;
- World revision/history/object revisions are preserved;
- no provider-attempt/execution ledger state is silently discarded;
- index may be copied only as optional cache; restored World must remain valid if index is rebuilt from scratch;
- restore to a separate path does not mutate the source backup.

Prefer SQLite-supported online backup/checkpoint semantics over raw copying of a live WAL database.

Do not claim cross-host/distributed replication unless actually implemented and tested.

### R8 — schema compatibility / upgrade boundary

Inventory current schema/version behavior.

Test:
- current World opens cleanly;
- clearly incompatible/future schema fails explicitly and non-destructively;
- any supported upgrade path is restart-safe and idempotent;
- failed upgrade does not leave the World falsely marked upgraded;
- repeated startup does not rerun destructive migration.

If the repository has no supported historical schema upgrade mechanism, do not invent a large migration framework.
Instead:
- make the current compatibility boundary explicit;
- fail safely;
- add only the minimal schema-version/migration mechanism necessary for the current release candidate.

### R9 — interrupted backup/rebuild/maintenance

Interrupt or fault-inject any new recovery maintenance introduced by this task.

Verify restart either:
- safely resumes, or
- safely restarts the mechanical operation from World truth,
without rewriting history or creating duplicate World state.

### R10 — headless operational recovery surface

The accepted `aios-core-headless` entrypoint must expose enough recovery behavior to operate the above safely.

Only add CLI/status/recovery commands if a real recovery need requires them.

Operational output may include:
- safe-to-retry vs IN_DOUBT vs manual-reconciliation-required;
- index lag/rebuild status;
- backup/restore status;
- schema compatibility error.

Do not expose hidden model chain-of-thought.
Do not make logs the truth store.

## Recovery disposition contract

For every failure class in the completion evidence, state one of:

- AUTO_RECOVERABLE — deterministic recovery without model/provider duplication risk;
- RETRY_WITH_EXPLICIT_AUTHORIZATION — retry mechanically proven safe only after explicit authorization/evidence;
- IN_DOUBT_MANUAL_RECONCILIATION — ambiguous provider execution; no blind retry;
- REBUILD_FROM_WORLD — index/cache loss only;
- FATAL_INCOMPATIBLE — unsafe schema/storage condition; startup refuses non-destructively.

Do not call an ambiguous provider failure AUTO_RECOVERABLE.

## Tests

Add focused recovery/fault-injection tests only where useful.

Prefer testing at the current public/runtime boundaries rather than monkeypatching past the invariant being tested.

At minimum retain/regress:
- HEADLESS lifecycle/corrective suite;
- world-kernel;
- fused-turn-runtime;
- C09 Wake;
- P15 Periodic Review;
- C14 runtime/loop where recovery touches background execution;
- FIX-002 targeted suite;
- FIX-003 targeted suite;
- constitutional cognition closure;
- full P16 direct `pytest -q`.

If backup/index/schema tooling is added, include dedicated mechanical tests for those surfaces.

## Clean restart proof

Provide at least one process-level sequence from an installed checkout:

1. create/open disposable World;
2. write normal user turn/fact;
3. create at least one recoverable or IN_DOUBT durable state;
4. stop process;
5. restart process;
6. inspect correct disposition;
7. perform only the permitted recovery;
8. stop/restart again;
9. prove no duplicate World/output/metering/provider execution.

## Deliverable

Create:
`reviews/CORE_RECOVERY_001_COMPLETION_EVIDENCE_2026-09-24.md`

It must include:
- construction live main;
- exact candidate head;
- inventory of pre-existing recovery mechanisms;
- recovery matrix R1-R10 verdicts;
- real gaps found vs ALREADY_SAFE findings;
- exact source/test files changed;
- recovery disposition table;
- fault-injection method and safety boundary;
- backup/restore procedure;
- index rebuild procedure;
- schema compatibility/upgrade statement;
- exact run/job IDs;
- full P16 result;
- known limitations.

## Scope stop conditions

Stop and report PM instead of broadening scope if recovery requires:
- constitutional change;
- second World/truth store;
- distributed consensus/HA architecture;
- changing accepted provider-at-most-once semantics;
- rewriting accepted FIX-001/002/003 design;
- destructive migration of historical Worlds with no reversible plan.

## Handoff

At completion:
- open one engineering PR for CORE-RECOVERY-001;
- set author state REVIEW_READY;
- do not self-accept;
- do not merge;
- do not update task board/checkpoint from engineering branch;
- do not start CORE-SCALE-001;
- do not run Resident;
- do not build UI/hardware.

Fresh independent acceptance is required before PM integration.
