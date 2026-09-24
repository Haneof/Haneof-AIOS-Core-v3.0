# CORE-RECOVERY-001 Completion Evidence — 2026-09-24

Status: **REVIEW_READY (AUTHOR HANDOFF; NOT ACCEPTED; NOT MERGED)**  
Task: `CORE-RECOVERY-001`  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Engineering PR: #191  
Branch: `core-recovery-001-20260924-sol`

## 1. Pins and scope

- Construction live main: `06b3a98fd3c098f861f49ab936500f81de030991`.
- Live main was rechecked before handoff and remained exactly `06b3a98fd3c098f861f49ab936500f81de030991`.
- Tested implementation exact head: `58b6b5e2e653e258e778a0f2dd3d77978cd585ff`.
- The completion-evidence commit after that head is evidence-only; no implementation/test/workflow bytes are changed by the evidence handoff.
- `CORE-RECOVERY-001 = READY` was confirmed before construction.
- No task-board/checkpoint state was changed from the engineering branch.
- No CORE-SCALE-001, RC-FREEZE, Resident, UI, hardware, or sealed/private Resident fixture execution was entered.

The canonical SQLite World remains the only truth store. No recovery database, alternate cognition store, provider-execution truth store, or log-as-truth mechanism was introduced.

## 2. Pre-existing recovery inventory

The starting main already contained substantial accepted recovery machinery:

1. **SQLite World**
   - `SQLiteWorldStore` uses SQLite WAL mode, foreign keys, busy timeout, append-only object revisions, global `world_revision`, `BEGIN IMMEDIATE` write transactions, commit/rollback, and idempotency records.
   - Existing schema helpers already performed narrow additive/lossless legacy migrations such as source-class and revision-kind support.
2. **World index**
   - `WorldSearchIndex` is explicitly a rebuildable projection.
   - It already had durable watermark, lag reporting, commit-complete `catch_up()`, `drop_projection()`, and `rebuild()`.
3. **FIX-002 background execution**
   - `BackgroundModelAttemptStore` is the shared durable provider-attempt ledger for Wake / Periodic Review and now user-turn attempts.
   - Accepted states retain admitted / not-submitted / in-doubt / response-returned / metered boundaries and stable attempt identity.
4. **FIX-003 user-turn execution**
   - `TurnExecutionStore` retains stable turn execution identity, input identity, pre-attempt admission, explicit retry authorization only after durable proof of non-submission, and durable-assistant-output completion reconciliation.
5. **Metering / budget**
   - `ModelMeteringLedger` persists model usage outside World revision semantics and provides idempotent provider-response linkage.
   - Existing background budget accounting remains non-World mechanical state.
6. **Wake / Periodic Review**
   - Wake and Review durable lifecycle state remains in the accepted World/runtime mechanisms.
   - Provider execution state remains in the shared attempt ledger; recovery does not mint new wake/review/attempt identity to escape ambiguity.
7. **HEADLESS**
   - Accepted canonical same-World writer lease, start/stop/restart lifecycle, index catch-up, due-work processing, and `inspect-turn` recovery inspection were retained.

## 3. Real gaps found and minimal repairs

### RG-REC-01 — no mechanically safe supported World backup/restore surface

**Before:** no repository backup/restore implementation existed for the live WAL World. A raw copy could omit WAL state or silently drop non-World tables that share the canonical SQLite file.

**Repair:** added `src/aios_core/headless/recovery.py` and headless commands using SQLite online backup semantics, the canonical World writer lease, staged validation, fsync, and no-overwrite publication.

- Backup includes the complete SQLite database, therefore World history plus turn execution, background attempt, metering/budget and other SQLite-resident mechanical ledgers are captured together.
- Restore only publishes to a new World path; it never overwrites an existing World.
- The search index is not treated as backup truth and is rebuilt from the restored World.

### RG-REC-02 — no explicit schema compatibility version boundary

**Before:** narrow migrations existed, but there was no explicit current schema version / future-schema refusal boundary.

**Repair:** `SQLiteWorldStore.CURRENT_SCHEMA_VERSION = 1` and SQLite `PRAGMA user_version`.

- Existing unversioned legacy World = version 0 and remains eligible for the existing narrow idempotent migrations.
- Version 1 = current.
- Future version > 1 is rejected by a read-only preflight before a writable/WAL initialization path.
- The version marker is published only after supported current initialization/migrations complete.
- A failed upgrade is not falsely marked current.

No large migration framework was invented.

### RG-REC-03 — index loss/corruption had rebuild primitives but no auditable operational recovery surface

**Before:** `WorldSearchIndex.rebuild()` existed, but the accepted headless surface did not provide an explicit missing/corrupt/stale disposition and atomic offline rebuild command.

**Repair:** added:
- `recovery-status`;
- `rebuild-index`;
- staged rebuild + World watermark equality check + SQLite quick-check + atomic cache publication.

A missing/corrupt/unopenable/future-watermark index is classified `REBUILD_FROM_WORLD`, never as World truth.

### RG-REC-04 — first ambiguous provider timeout had correct durable state but misleading CLI classification

**Before:** FIX-003 correctly persisted an ambiguous timeout as `IN_DOUBT`, but Python `TimeoutError` is an `OSError`, so the headless CLI could surface the first ambiguous dispatch as generic `operation_error` instead of `reconciliation_required`.

**Repair:** the CLI now maps `TimeoutError` into the existing reconciliation-required operational class. No retry semantics changed; no provider re-invocation was added.

## 4. Recovery matrix R1–R10

| Matrix | Verdict | Evidence / behavior |
|---|---|---|
| **R1 SQLite transaction / WAL crash safety** | **PASS / ALREADY_SAFE** | Fresh process fault injection uses disposable Worlds and `os._exit`: uncommitted inserted rows disappear after reopen; committed World object/revision survives; `quick_check=ok`. No World code change was required for transactional atomicity. |
| **R2 World write failure boundaries** | **PASS / ALREADY_SAFE** | Retained FIX-003 tests cover assistant-output persistence failure, meter-write-after-response failure, completion-store failure and idempotent completion recovery. Failed required durable writes never fabricate completion; provider identity is not replaced. |
| **R3 FIX-003 user-turn restart recovery** | **PASS / ALREADY_SAFE** | Existing pre-admission / definitely-not-submitted / ambiguous `IN_DOUBT` / response-returned / durable assistant recovery / completion / conflicting-input tests remain green. Clean process proof additionally retains one exact ambiguous attempt through two restarts without provider re-call. |
| **R4 FIX-002 background restart recovery** | **PASS / ALREADY_SAFE** | `tests/integration/test_core_gap_fix_002_background_attempts.py` plus Wake/Review regressions remain green. Ambiguous dispatch remains fail-closed; no blind reinvocation. |
| **R5 FIX-001 historical read cut** | **PASS / ALREADY_SAFE** | Existing `test_headless_restart_keeps_fix001_historical_knowledge_cut` and retained C14/runtime regressions remain green; RECOVERY added no current-time rerun path. |
| **R6 index loss / stale / rebuild** | **REAL GAP CLOSED** | Tests cover stale watermark catch-up, deleted/missing index, corrupt index, rebuild from World, preserved World revision, fresh strict search after rebuild, and interrupted rebuild leaving canonical index untouched. |
| **R7 backup / restore** | **REAL GAP CLOSED** | SQLite online backup captures one coherent database snapshot. Restore to a separate path preserves World revision, object history and shared execution/attempt/metering tables; source backup hash remains unchanged; restored index is rebuilt from World. |
| **R8 schema compatibility / upgrade boundary** | **REAL GAP CLOSED** | Current schema opens repeatedly without World revision change; future schema fails read-only/non-destructively; failed upgrade does not set current version. Current supported legacy v0 -> v1 boundary is explicit. |
| **R9 interrupted backup/rebuild/maintenance** | **PASS** | Dedicated fault injection covers interrupted backup publication, interrupted restore publication and interrupted index rebuild. Staged state is cleaned or left fail-closed; source World/backup is unchanged; the operation can be restarted mechanically without rewriting World history. |
| **R10 headless operational recovery surface** | **REAL GAP CLOSED** | `recovery-status`, `backup`, `restore`, `rebuild-index` plus retained `inspect-turn` expose storage/index/schema and turn-recovery state without requiring a model handler for mechanical recovery commands. Ambiguous provider timeout reports `reconciliation_required`. |

## 5. Recovery disposition contract

| Failure class | Disposition | Rule |
|---|---|---|
| SQLite uncommitted transaction/process death | **AUTO_RECOVERABLE** | Reopen same World; SQLite rolls back non-committed transaction. |
| SQLite committed WAL transaction/process death | **AUTO_RECOVERABLE** | Reopen same World; committed revision/object survives. |
| User-turn pre-attempt crash or attempt durably proven not submitted | **RETRY_WITH_EXPLICIT_AUTHORIZATION** | Existing execution identity is retained; operator/provider evidence must authorize retry. |
| User-turn or background provider dispatch ambiguity | **IN_DOUBT_MANUAL_RECONCILIATION** | No blind model call; same turn/wake/review/attempt identity remains authoritative. |
| Response returned and durable assistant output exists while completion marker is missing | **AUTO_RECOVERABLE** | Existing completion reconciliation finishes mechanically without provider invocation. |
| Missing/stale/corrupt/unopenable search index | **REBUILD_FROM_WORLD** | World is truth; rebuild projection and require watermark == World revision. |
| Future World schema / corrupt or non-AIOS World snapshot | **FATAL_INCOMPATIBLE** | Refuse non-destructively; do not downgrade or fabricate schema. |
| Interrupted backup/restore/index rebuild before successful publication | **AUTO_RECOVERABLE** | Canonical World/backup truth is unchanged; restart the mechanical operation from the source of truth. |
| Recovery destination already exists | **RETRY_WITH_EXPLICIT_AUTHORIZATION** | Refuse overwrite. Operator must choose/validate a separate destination; no destructive retry. |

Ambiguous provider execution is never classified AUTO_RECOVERABLE.

## 6. Fault-injection method and safety boundary

All destructive/failure injection used disposable temporary Worlds only.

Focused recovery tests:
- forked child process starts an uncommitted SQLite transaction, inserts synthetic World rows, then `os._exit(0)`;
- second child commits normally and then exits abruptly;
- index bytes are deliberately replaced with invalid SQLite bytes only on disposable index files;
- future schema is synthesized with a high `PRAGMA user_version` in a disposable database;
- migration interruption is injected before the final version marker;
- index rebuild is interrupted after staged catch-up but before canonical publication;
- backup/restore publication is faulted at the actual no-overwrite publication boundary;
- no production/user/private Resident World is opened.

The installed process-level proof uses only:
- a temporary World;
- the repository deterministic mechanical model adapter for one successful normal turn;
- a temporary synthetic adapter that writes one provider-dispatch marker and then raises `TimeoutError`;
- no Resident semantics or sealed fixture.

## 7. Clean restart proof

Final process-level job: **SUCCESS**.

Sequence performed from a clean installed checkout:

1. create disposable World;
2. submit one normal user turn;
3. submit a second turn through a synthetic adapter that crosses a provider-dispatch marker then raises an ambiguous timeout;
4. stop that CLI process;
5. fresh process `inspect-turn` observes the same execution id and exactly one `in_doubt` attempt;
6. verify provider marker count remains exactly 1;
7. create SQLite backup; delete/rebuild index; restore backup to a new World; rebuild restored index;
8. fresh process re-inspects the restored turn;
9. exact execution/attempt remains `in_doubt`; provider marker remains 1; both source and restored DBs contain exactly one in-doubt attempt, one prior successful response-returned attempt, one metering record, and one successful assistant output.

Observed operational snippets in the final job include:
- first ambiguous timeout -> `status=reconciliation_required`;
- attempt id `bgattempt_1e741a1275121e7bdafc3d09f20aee33`, state `in_doubt`;
- backup World revision = 3;
- source and restored index watermark = 3;
- restored World revision = 3;
- source/restored provider-attempt state counts are identical;
- source/restored metering count = 1.

No blind provider re-call occurred.

## 8. Backup / restore procedure

### Backup

```bash
aios-core-headless --world /path/world.sqlite \
  backup --to /safe/path/world.backup.sqlite
```

Mechanical behavior:
1. derive/acquire the canonical World writer lease;
2. open current World and require SQLite `quick_check=ok`;
3. snapshot using SQLite's supported online backup API into a same-directory staged file;
4. probe staged snapshot read-only; verify World revision and schema version;
5. fsync staged bytes;
6. publish with an atomic no-overwrite link and fsync target/directory.

Raw copying a live WAL database is not the supported procedure.

### Restore

Restore always targets a **new** World path:

```bash
aios-core-headless --world /new/path/restored.sqlite \
  restore --from-backup /safe/path/world.backup.sqlite
aios-core-headless --world /new/path/restored.sqlite rebuild-index
```

Mechanical behavior:
1. source backup is inspected read-only and must be an intact compatible AIOS World;
2. any existing target World/WAL/SHM causes refusal;
3. SQLite backup API copies source to staged restore DB;
4. supported current schema initialization/migration occurs only on the staged copy;
5. World revision is verified unchanged;
6. staged DB is checkpointed/fsynced and atomically published without overwriting;
7. index is rebuilt independently from restored World.

The source backup is never modified by restore.

## 9. Index recovery procedure

Inspect:

```bash
aios-core-headless --world /path/world.sqlite \
  --index /path/world.search.sqlite recovery-status
```

Rebuild:

```bash
aios-core-headless --world /path/world.sqlite \
  --index /path/world.search.sqlite rebuild-index
```

The rebuild:
- reads canonical World revisions only;
- constructs a staged index;
- requires rebuilt watermark == current World revision;
- requires SQLite quick-check;
- publishes the rebuilt cache;
- never increments or rewrites World history.

## 10. Schema compatibility statement

Current explicit World schema version: **1**.

- v0: supported historical/unversioned boundary; existing narrow migrations may run.
- v1: current.
- >v1: **FATAL_INCOMPATIBLE**; rejected before writable initialization.

This task does not claim support for arbitrary historical or future migrations. It adds only the minimal release-candidate compatibility marker and non-destructive refusal rule. Existing narrow migrations remain the only supported v0 upgrade path.

## 11. Exact changed files

Implementation / test / gate diff from construction main to tested implementation head:

1. `.github/workflows/core-recovery.yml` — added dedicated recovery, retained-regression and installed clean-restart jobs.
2. `src/aios_core/headless/cli.py` — recovery commands and reconciliation-required timeout classification.
3. `src/aios_core/headless/recovery.py` — mechanical recovery status, SQLite backup/restore, index rebuild, validation and no-overwrite publication.
4. `src/aios_core/storage/sqlite_store.py` — explicit schema compatibility boundary, schema version and quick-check helper.
5. `tests/integration/test_core_recovery.py` — disposable fault-injection R1/R6/R7/R8/R9/R10 coverage.

No other file differs from construction main at the tested implementation head.

## 12. Final exact-head CI / jobs

All of the following are against exact implementation head:
`58b6b5e2e653e258e778a0f2dd3d77978cd585ff`.

### CORE recovery gate — run 35998900821 — SUCCESS
- recovery-fault-injection — job **107630398418** — SUCCESS — **12/12 pass markers**
- installed-clean-restart-proof — job **107630398731** — SUCCESS
- retained-recovery-regressions — job **107630398704** — SUCCESS — **193 pass markers**

### Full P16 direct pytest — run 35998900838 — SUCCESS
- full-core-regression — job **107630397697** — SUCCESS
- command: `pytest -q`
- result: **687 pass markers, 0 failure/error markers, reached 100%**

### HEADLESS — run 35998900833 — SUCCESS
- headless-lifecycle — job **107630397105** — SUCCESS
- installed smoke + permanent HEADLESS suite + runtime compatibility regressions
- **226 pass markers** across the two pytest invocations (13 targeted HEADLESS + 213 compatibility regressions)

### World kernel — run 35998900847 — SUCCESS
- test — job **107630397780** — SUCCESS — **24 passed**

### World index — run 35998900841 — SUCCESS
- test — job **107630396863** — SUCCESS — **12 passed**

### Constitutional cognition closure — run 35998900832 — SUCCESS
- constitutional-cognition-closure — job **107630396989** — SUCCESS

### C14 scheduler/runtime regression — run 35998900826 — SUCCESS
Jobs all SUCCESS:
- dimension-summary — **107630397323**
- cognitive-runtime — **107630397452**
- c13-metering — **107630397469**
- memory-recommendation-t28 — **107630397481**
- fused-turn-runtime — **107630397534**
- c09-wake-dispatch — **107630397559**
- p15-periodic-review — **107630397575**
- p16-habitation-harness — **107630397593**
- p14-long-context — **107630397602**
- p16-convergence-gate — **107630397606**
- world-index — **107630397615**
- c14-scheduler-targeted — **107630397730**

This retained the requested World kernel, fused-turn, Wake, Periodic Review, C14, FIX-002/FIX-003, metering and constitutional-cognition surfaces.

## 13. Development-time red evidence retained

No red run was rewritten as green.

- Initial recovery run `35997231887` exposed:
  - two incorrect new test expectations;
  - a real operational classification gap where first ambiguous provider `TimeoutError` was persisted `IN_DOUBT` but surfaced by CLI as generic operation error.
- That CLI classification gap was repaired without changing provider-at-most-once behavior.
- A later R9 backup fault test initially patched obsolete `os.replace`; final implementation already used the hardened `os.link` no-overwrite publisher. The test was corrected to inject the actual boundary.
- Final exact-head evidence above is fresh after those corrections.

## 14. Known limitations / non-claims

- No cross-host replication, HA, distributed consensus, or automatic failover is implemented or claimed.
- No ambiguous provider call is automatically retried.
- Provider-side reconciliation still requires real external/provider evidence where execution is ambiguous.
- The local SQLite backup command is a coherent snapshot mechanism, not continuous replication.
- Index is intentionally not authoritative and is not required in the World backup; rebuild is the supported recovery path.
- Schema v1 does not create a general migration framework; future schemas are refused.
- Filesystem failure after a no-overwrite publication may leave a published artifact whose final durability must be inspected; the implementation does not delete or overwrite such an artifact and does not claim success after an fsync error.
- Recovery commands expose mechanical state only; logs remain diagnostic and are never cognition/World truth.

## 15. Author handoff

Engineering disposition: **REVIEW_READY**.

The author does not self-accept this task and does not merge PR #191. Fresh Independent Acceptance must validate the pinned implementation head and the evidence-only handoff before PM integration.

No downstream task is started by this handoff.
