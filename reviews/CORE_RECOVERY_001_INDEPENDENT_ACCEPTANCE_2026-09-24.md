# CORE-RECOVERY-001 Independent Acceptance — 2026-09-24

Status: **ACCEPTANCE_PASS**
Task: CORE-RECOVERY-001-INDEPENDENT-ACCEPTANCE
Repository: Haneof/Haneof-AIOS-Core-v3.0
Engineering PR: #191

## 1. Review pins and live state

- Review-time live main: d697d1ea14774d574af8a0f240da799a18ffc8d4.
- PR #191 remains OPEN / UNMERGED at review completion.
- Tested implementation exact head: 58b6b5e2e653e258e778a0f2dd3d77978cd585ff.
- Evidence-only handoff: f90b93608a13f9e04ff9b7997f2b4f92b5331f88.
- CORE-RECOVERY-001 was confirmed GATE / REVIEW_READY in the live task board/checkpoint.
- CORE-SCALE-001, CORE-RC-FREEZE-001 and fresh Resident execution remain outside this acceptance window.

No implementation repair, merge, Resident execution, UI work, or hardware work was performed by this review.

## 2. Candidate scope verification

Independent compare established:

Construction main 06b3a98fd3c098f861f49ab936500f81de030991 -> tested implementation 58b6b5e2e653e258e778a0f2dd3d77978cd585ff changes exactly five files:

1. .github/workflows/core-recovery.yml
2. src/aios_core/headless/cli.py
3. src/aios_core/headless/recovery.py
4. src/aios_core/storage/sqlite_store.py
5. tests/integration/test_core_recovery.py

Tested implementation 58b6b5e2e653e258e778a0f2dd3d77978cd585ff -> evidence handoff f90b93608a13f9e04ff9b7997f2b4f92b5331f88 changes exactly one file:

- reviews/CORE_RECOVERY_001_COMPLETION_EVIDENCE_2026-09-24.md

The evidence layer therefore does not alter implementation, tests, or workflow behavior.

No second World truth store, provider-attempt ledger, turn-recovery ledger, log-as-truth mechanism, destructive clear-and-retry path, identity minting bypass, or automatic provider retry path was found in the candidate.

## 3. Live-main drift

Construction main 06b3a98f... -> review-time live main d697d1ea... contains only governance/review drift:

- AIOS_v3.0_CURRENT_CHECKPOINT.md
- PROJECT_MASTER_MAP.md
- governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md
- governance/prompts/CORE_RECOVERY_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md

No src/**, storage schema implementation, HEADLESS/recovery runtime contract, package behavior, or candidate test/workflow semantic change landed on main after construction.

Verdict: **governance-only drift; no REBASE_REVALIDATION_REQUIRED condition exists.**

## 4. Recovery architecture invariants

Independent source inspection confirmed:

- the canonical SQLite World remains the durable World truth;
- search index remains a rebuildable projection;
- backup is an immutable SQLite snapshot, not an active second truth store;
- recovery status is observational and does not become cognition truth;
- shared background_model_attempts remains provider-execution truth;
- existing user-turn execution identity remains stable;
- recovery does not replace FIX-001 historical knowledge cut with current-time replay;
- mechanical recovery commands use the same canonical World-derived writer lease as HEADLESS.

HeadlessConfig derives the lease exclusively as the resolved canonical World path plus .writer.lock. Caller-provided lock_path is validation-only and cannot select a competing lease identity.

## 5. Independent R1-R10 verdict

| Matrix | Independent verdict | Evidence |
|---|---|---|
| R1 SQLite transaction / WAL crash safety | **PASS** | Fresh acceptance probe used real forked child processes and os._exit. Uncommitted transaction reopened at world revision 0 with no fabricated commit; committed revision/object survived; SQLite quick_check remained ok. Candidate exact-head focused gate also passed 12/12. |
| R2 durable World write failure boundaries | **PASS / ALREADY_SAFE** | Fresh retained recovery run re-executed user-turn failure/reconciliation tests covering response provenance with later metering failure, assistant-output persistence failure, durable-output completion recovery, and conflicting input. No duplicate output/metering or provider reinvocation path was found. |
| R3 FIX-003 user-turn restart recovery | **PASS / ALREADY_SAFE** | Fresh retained suite covers pre-admission crash, legacy zero-attempt fail-closed, proven not-submitted + explicit authorization, ambiguous dispatch across restart, response-returned recovery, persistence failure, idempotent completion, and input conflict. Exact clean-restart proof retained the same turnexec and attempt id across backup/restore. |
| R4 FIX-002 background recovery | **PASS / ALREADY_SAFE** | Fresh retained suite covers Wake and Periodic Review ambiguous dispatch, pre-dispatch failure, same-attempt safe retry, response-before-meter, meter-before-completion, budget rollover and normal metered completion. Ambiguous execution stays IN_DOUBT and is not blindly reinvoked. |
| R5 FIX-001 historical temporal cut | **PASS / ALREADY_SAFE** | Fresh headless retained test test_headless_restart_keeps_fix001_historical_knowledge_cut passed. Accepted FIX-001 cutoff-aware lineage remains unchanged by candidate code. |
| R6 index loss / stale / corrupt / interrupted rebuild | **PASS** | Candidate tests cover stale catch-up, missing/corrupt rebuild, strict search and unchanged World revision. Fresh Probe C injected failure at the actual os.replace index publication boundary: World revision and existing canonical index hash stayed unchanged, staged residue was not published, and clean retry rebuilt/searchable index successfully. |
| R7 backup / restore | **PASS** | Source inspection confirms canonical writer lease + SQLite online backup API + staged read-only validation + no-overwrite publication. Fresh Probe B forced a non-empty live WAL, backed up and restored to a separate World, rebuilt index, verified source backup hash immutability, and compared every SQLite-resident table row source-vs-restored. |
| R8 schema compatibility | **PASS** | Future-schema preflight is a mode=ro SQLite open before writable/WAL initialization. Fresh Probe A verified hash, size/mtime, sentinel, user_version and WAL/SHM sidecar state unchanged after refusal. Fresh Probe E interrupted v0 migration before marker publication: user_version remained 0; clean retry then advanced to current version idempotently. |
| R9 interrupted maintenance | **PASS** | Candidate focused tests cover backup, restore and index interruptions. Fresh Probe C independently faults actual index publication. Backup/restore publication uses no-overwrite hard-link publication; late fsync failure raises and does not silently delete/replace an already-published artifact. |
| R10 operational recovery surface | **PASS** | Installed surface contains recovery-status, backup, restore, rebuild-index and retained inspect-turn. Mechanical commands do not require a model provider. TimeoutError after ambiguous dispatch maps to reconciliation_required and does not authorize automatic retry. |

**R1-R10: PASS.**

## 6. Fresh adversarial acceptance probes

Probe-only PR: **#194**
Probe head: 6e0dd3a0fbe4ca4842ad1723794b91f352c7afb3
Workflow run: **36000803577**
Disposition after evidence capture: **CLOSED / UNMERGED**
Probe delta: only .github/workflows/core-recovery.yml; no candidate implementation file changed.

Run 36000803577 completed SUCCESS with all five jobs green:

- acceptance-adversarial-probes — job 107636687444 — SUCCESS
- acceptance-retained-semantics — job 107636687121 — SUCCESS
- installed-clean-restart-proof — job 107636687382 — SUCCESS
- retained-recovery-regressions — job 107636687453 — SUCCESS
- recovery-fault-injection — job 107636687467 — SUCCESS

### Fresh R1 — process crash boundary

PASS.

- forked child wrote an uncommitted World transaction then os._exit;
- reopened World remained revision 0 and no synthetic commit survived;
- committed child transaction survived abrupt exit as revision 1;
- quick_check remained ok.

### Probe A — future-schema non-destructive refusal

PASS.

- future user_version was synthesized on a disposable file;
- normal SQLiteWorldStore open refused with incompatible_future_schema;
- file SHA-256 remained unchanged;
- file size and mtime remained unchanged;
- WAL/SHM sidecar existence state remained unchanged;
- sentinel data and future user_version remained intact;
- no world_meta initialization occurred.

Observed pre/post file hash:
344ed0b9047ef8f4463d73b2428ea127a41147156acfddb015d68ab2e5261323

This independently confirms a real pre-write fail-closed boundary rather than only an error string.

### Probe B — live-WAL backup and restored ledger equivalence

PASS.

Probe created:
- one successful metered user turn;
- one durable ambiguous user-turn provider attempt that became IN_DOUBT;
- a deliberately non-empty live WAL held across backup.

Observed live WAL size during backup: **24,752 bytes**.

SQLite online backup succeeded while WAL was live. After separate-path restore and index rebuild:

- source and restored World table snapshots were exactly equal for all SQLite-resident user tables;
- tables included runtime_turn_executions, background_model_attempts, metering_records, object_revisions, world_commits/world_meta and the WAL probe table;
- IN_DOUBT count remained exactly 1;
- metering count remained exactly 1;
- the two provider attempt IDs were unchanged;
- source backup SHA-256 remained unchanged after restore and rebuild.

Observed attempt IDs:
- bgattempt_191d324bfd4f2f012d1792faf375e9f2
- bgattempt_f38b81e8d6d5e062b08dd7f34b4b75a5

Observed backup SHA-256:
246aa2f5029678375e93e808e5724980e40f6b206536915270730dcd60397705

This proves backup includes SQLite-resident execution/attempt/metering state rather than only WorldObject rows.

### Probe C — interrupted index publication

PASS.

Failure was injected at the real os.replace staged-index publication boundary.

After injected failure:
- canonical World revision was unchanged;
- prior canonical index hash was unchanged;
- staged rebuild file was not treated as canonical;
- subsequent clean rebuild succeeded;
- strict search returned the expected object.

### Probe D — recovery command vs live writer lease

PASS.

A live HeadlessCore held the canonical World writer lease.

While held:
- backup_world failed closed with HeadlessWriterBusy;
- rebuild_index failed closed with HeadlessWriterBusy;
- an alternate caller-selected lock_path was rejected by HeadlessConfigurationError.

After the live writer released:
- backup proceeded;
- rebuild proceeded.

No second maintenance lock identity exists.

### Probe E — migration marker interruption

PASS.

A disposable legacy v0 database was made to fail during supported initialization/migration before version publication.

After failure:
- PRAGMA user_version remained 0;
- sentinel data remained intact.

After removing injected failure:
- normal open upgraded to the current schema version;
- repeated open was idempotent;
- sentinel data remained intact.

### Fresh retained semantics

Job 107636687121 reran:

- tests/runtime/test_turn_execution_recovery.py
- tests/integration/test_core_gap_fix_002_background_attempts.py
- tests/integration/test_core_headless.py
- tests/integration/test_core_recovery.py

Result: **45 pass markers / 0 failure-error markers / 100%**.

Fresh recovery focused job 107636687467:
**12 pass markers / 0 failure-error markers / 100%**.

## 7. Backup / restore verdict

**PASS.**

Backup:
- obtains canonical World writer lease;
- validates live World integrity;
- uses SQLite online backup instead of raw live-file copy;
- validates staged snapshot;
- checks snapshot revision/schema against source;
- fsyncs staged data;
- refuses target overwrite through no-overwrite publication.

Restore:
- reads source backup read-only;
- refuses an existing target World/WAL/SHM;
- restores into staged separate-path SQLite;
- applies any supported migration only to staged copy;
- validates integrity and unchanged World revision before publication;
- publishes without overwriting;
- does not require index as backup truth;
- leaves source backup bytes unchanged.

Fresh live-WAL table-equivalence proof closes the key acceptance risk.

## 8. Index recovery verdict

**PASS.**

The index remains disposable and World-derived.

Verified:
- missing index -> rebuild path;
- stale index -> safe catch-up/current watermark;
- corrupt/unopenable index -> rebuild path;
- future/invalid watermark is not trusted;
- rebuild watermark must equal World revision;
- rebuild does not increment World revision;
- strict search works after rebuild;
- interrupted staged publication does not turn a partial index into truth;
- clean restart/retry is safe.

## 9. Schema compatibility verdict

**PASS.**

CURRENT_SCHEMA_VERSION = 1.

Exact call-order inspection confirms:
1. existing path is checked;
2. user_version is read with SQLite mode=ro;
3. future version is rejected there;
4. only compatible World proceeds to the normal connection path that enables WAL/current initialization;
5. supported DDL/migrations execute before the version marker is published;
6. user_version is published only at the end of successful initialization.

Fresh Probe A proves future-schema refusal is non-destructive.
Fresh Probe E proves migration interruption does not falsely publish v1.

## 10. FIX-001 / FIX-002 / FIX-003 compatibility

### FIX-001

PASS.

Accepted historical cutoff behavior remains intact. Candidate recovery code adds no replay path that substitutes current World knowledge for a historical execution. Fresh headless retained test for historical knowledge cut passed.

### FIX-002

PASS.

background_model_attempts remains the sole provider-attempt truth. Fresh Wake/Review recovery tests passed, including ambiguous dispatch, pre-dispatch, response-before-meter and meter-before-completion boundaries. IN_DOUBT is retained across restart with no blind provider call.

### FIX-003

PASS.

User-turn stable execution identity, pre-admission semantics, explicit retry authorization, IN_DOUBT, durable assistant-output reconciliation and input-conflict fail-closed behavior remain intact. Fresh retained tests passed all applicable recovery states.

## 11. Recovery disposition verdict

| Failure class | Accepted disposition |
|---|---|
| SQLite uncommitted crash | AUTO_RECOVERABLE |
| SQLite committed WAL crash | AUTO_RECOVERABLE |
| mechanically proven pre-attempt / not-submitted | RETRY_WITH_EXPLICIT_AUTHORIZATION |
| ambiguous user/background provider dispatch | IN_DOUBT_MANUAL_RECONCILIATION |
| durable output / missing completion marker | AUTO_RECOVERABLE |
| missing/corrupt disposable index | REBUILD_FROM_WORLD |
| future/incompatible World schema | FATAL_INCOMPATIBLE |
| interrupted mechanical recovery before safe publication | safe mechanical restart/retry without World history rewrite |
| destination already exists | fail closed; no destructive overwrite |

**Ambiguous provider execution is not AUTO_RECOVERABLE.**

## 12. Exact-head CI re-read

All runs below were independently re-read and verified to have exact head:
58b6b5e2e653e258e778a0f2dd3d77978cd585ff.

### core-recovery — run 35998900821 — SUCCESS

- recovery-fault-injection / job 107630398418:
  - direct pytest -q tests/integration/test_core_recovery.py
  - **12 pass markers / 0 failure-error markers / 100%**
- installed-clean-restart-proof / job 107630398731:
  - SUCCESS
  - first ambiguous TimeoutError surfaced as reconciliation_required;
  - same turnexec and same attempt id remained IN_DOUBT before/after backup/restore;
  - provider marker stayed one;
  - source/restored attempts = one response_returned + one in_doubt;
  - source/restored metering = 1;
  - source/restored assistant output count = 1.
- retained-recovery-regressions / job 107630398704:
  - **193 pass markers / 0 failure-error markers / 100%**

### full P16 — run 35998900838 / job 107630397697 — SUCCESS

- command: direct pytest -q
- **687 pass markers**
- **0 failure/error markers**
- reached **100%**

### HEADLESS — run 35998900833 / job 107630397105 — SUCCESS

- installed smoke plus retained suites
- **226 pass markers / 0 failure-error markers**

### World kernel — run 35998900847 / job 107630397780 — SUCCESS

- **24 passed**

### World index — run 35998900841 / job 107630396863 — SUCCESS

- **12 passed**

### Constitutional cognition — run 35998900832 / job 107630396989 — SUCCESS

- relevant pytest invocations completed **91 passed** and **92 passed**.

### C14 scheduler/runtime — run 35998900826 — SUCCESS

All relevant jobs completed SUCCESS, including:
- dimension-summary 107630397323
- cognitive-runtime 107630397452
- c13-metering 107630397469
- memory-recommendation-t28 107630397481
- fused-turn-runtime 107630397534
- c09-wake-dispatch 107630397559
- p15-periodic-review 107630397575
- p16-habitation-harness 107630397593
- p14-long-context 107630397602
- p16-convergence-gate 107630397606
- world-index 107630397615
- c14-scheduler-targeted 107630397730

## 13. Development-time red evidence review

Historical red evidence was preserved and independently distinguished from final green evidence.

Initial recovery run:
- run 35997231887
- head 742033a3362ee9ea7c5c2b4b0acee6d9a83354d4
- conclusion FAILURE

Its retained recovery regression job was already green, while the clean restart and focused recovery jobs were red.

Independent log review found:

1. Bad R1 test expectation:
   - the test expected get_payload on a missing object to return None;
   - the established API correctly raised StoreError NOT_FOUND.
   - final test was corrected to expect the existing API contract.

2. Bad R10 output-capture expectation:
   - the JSON recovery-status was visibly emitted in the raw log;
   - the test's capsys assumption saw an empty local capture.
   - final test validates the recovery status function directly instead of pretending the emitted status was absent.

3. Real CLI classification defect:
   - first ambiguous provider TimeoutError did not satisfy the intended reconciliation exit classification.
   - final source change explicitly adds TimeoutError to the reconciliation_required branch.
   - no provider retry behavior was added.

4. Publication-boundary hardening/test correction:
   - backup/restore publication moved from overwrite-capable os.replace to no-overwrite hard-link publication.
   - R9 fault injection was updated to patch the actual os.link publication primitive, not an obsolete primitive.

The final fresh exact-head and independent probe evidence therefore does not rewrite red history as green.

## 14. Known limitation review

The documented late-filesystem-fsync limitation is acceptable for this task:

- after a successful no-overwrite link, a later fsync failure may leave an artifact present;
- the operation raises instead of reporting success;
- code does not silently delete or overwrite the potentially published artifact;
- canonical source World/backup remains truth-preserving.

This is conservative fail-closed behavior and is not a second truth-store claim or an impossible cross-filesystem durability guarantee.

## 15. Blockers and verdict

Blocker count: **0**

Final verdict: **ACCEPTANCE_PASS**

PR #191 CORE-RECOVERY-001 tested exact implementation head 58b6b5e2e653e258e778a0f2dd3d77978cd585ff with evidence-only handoff f90b93608a13f9e04ff9b7997f2b4f92b5331f88 is independently accepted for PM integration.

This acceptance does not merge PR #191 and does not authorize this review window to enter CORE-SCALE-001, RC-FREEZE, Resident, UI, or hardware work.
