# CORE-GAP-AUDIT-001 — Independent Core Completion Gap Audit

Status: AUDIT_COMPLETE  
Task: CORE-GAP-AUDIT-001  
Role: Independent Core Architect / Core Gap Auditor  
Scope: current live main Core only; review-only; no Core/test/operator/Resident mutation  
Audit baseline acquisition: 2026-09-24 12:25 +08:00 (Asia/Taipei)

## 1. Exact audit baseline

- Repository: Haneof/Haneof-AIOS-Core-v3.0
- Audited live main SHA: c8807876ba62a4f4180beba8ff974e2342786340
- Audited root tree SHA: 093304598387853459d6260c3dc8b949223f491c
- Audited src/aios_core tree SHA: 7db4f72e7b3c29c74082f9984141159f8f1d6071
- Gate at audit start and immediately before report creation: CORE-GAP-AUDIT-001 = READY / NOT_STARTED.
- #127 merge SHA: 6924d8b50cf08eb632f9cfa513a3cc49faad0c72.
- Verified compare #127 merge -> audited main: 9 commits ahead, 0 behind, and all reported changed files are governance/checkpoint/prompt files; src/aios_core is unchanged.
- PR #126 was not treated as pending Core work because its Core tree duplicates the integrated Core.
- PR #125 was not treated as Core baseline; it is operator/preflight WIP and its Core tree is historical.

### Test / evidence environment

This audit did not modify or re-run the repository test suite. It inspected current main source and tests and used existing executable evidence only where the audited Core tree is byte-identical.

The exact Core tree was previously exercised by the #127 acceptance chain in:
- CPython 3.12.11
- pytest 8.4.2
- pydantic 2.13.5
- SQLite 3.40.1
- 409 Core unit/runtime/integration tests passed
- 42 audited repair regressions passed
- 492 permitted synthetic tests passed
- post-merge acceptance reported 23/23 workflows and 46/46 checks SUCCESS

Current main has no new Core delta after that tested tree. This report does not claim those suites were freshly re-run on c8807876.

### Normative / governance sources read

- governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md
- AIOS_v3.0_CURRENT_CHECKPOINT.md
- PROJECT_MASTER_MAP.md
- governance/AIOS_CORE_BASELINE_001_DECISION_2026-09-24.md
- governance/AIOS_CORE_COMPLETION_PLAN_2026-09-24.md
- governance/prompts/CORE_GAP_AUDIT_001_2026-09-24.md
- docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md
- docs/architecture/AIOS_v3.0_Legacy_Code_Migration_Matrix.md
- current source/tests under src/aios_core/** and tests/**
- historical issue/review evidence including AUDIT-001 and PRs #104, #127 and #125 only as evidence/lineage, never as substitute for current source.

## 2. Finding register

Counts below are finding IDs, not matrix row counts.

- STILL_OPEN: 3
- ALREADY_FIXED: 14
- NOT_REPRODUCED: 7
- OUT_OF_SCOPE: 6

### Open IDs

- CG-001 — RUNTIME_TEMPORAL_READ_CUT
- CG-002 — BACKGROUND_MODEL_EXECUTION_IN_DOUBT
- CG-003 — USER_TURN_IN_DOUBT_RECOVERY

All three block RC freeze. CG-001 and CG-002 also block safe headless due-work/recovery. CG-003 blocks recovery acceptance and therefore RC freeze.

## 3. Requirement matrix

| Domain | Requirement | Implementation | Tests / Evidence | Verdict | Gap / Next Action |
|---|---|---|---|---|---|
| A World | durable object revisions, global world_revision, append/update history | storage/sqlite_store.py uses append-only object_revisions + world_commits + optimistic expected_world_revision | tests/unit/test_store.py; tests/unit/test_world_revision_atomicity.py | NOT_REPRODUCED | NR-001 |
| A World | atomic multi-object commit / rollback / stale writer safety | one SQLite transaction, CAS against expected_world_revision, idempotency records | W01-W05 atomicity tests | NOT_REPRODUCED | NR-001 |
| A World | duplicate ingest / stable identity / provenance | ConversationIngestor and RealityIngestor stable identities + idempotency; object_revision_record joins exact commit source_class | conversation/reality ingest tests and store tests | NOT_REPRODUCED | NR-001 |
| B Index | structured Observation scalar retrieval | query/search.py mechanically flattens JSON-like scalar values into rebuildable projection | test_t36_structured_observation_scalars_feed_only_derived_projection | ALREADY_FIXED | AF-002 |
| B Index | whole logical commit indexing / watermark concurrency | catch_up uses BEGIN IMMEDIATE and revisions_after(... complete_commits=True); watermark published after all rows | #127 A05 regressions | ALREADY_FIXED | AF-010 |
| B Index | stale/missing index and crash/restart rebuild | projection is disposable; rebuild loops catch_up; failed index transaction does not publish watermark | test_dropped_projection_rebuilds_bit_identical; A05 failure test | NOT_REPRODUCED | NR-002 |
| C Context / Retrieval | assistant raw dialogue must not become independent user fact recommendation | ProactiveMemoryRecommender excludes assistant dialogue from proactive cards and antecedent fallback | tests/habitation/test_t28_proactive_memory_boundary.py | ALREADY_FIXED | AF-003 |
| C Context / Retrieval | cross-session antecedent must not trigger on self-contained text | topic_state uses bounded discourse/deictic gates rather than broad continuation matching | test_p16_cross_session_antecedent_recall.py | ALREADY_FIXED | AF-005 |
| C Context / Retrieval | historical / resumed execution must not read facts learned after its active cognition time | WorldSearchIndex supports AS_KNOWN learned_at cutoff, but FusedTurnRuntime search_world and inspect_world_object read current World without binding to _active_turn_time | current turn_runtime.py + search.py inspection | STILL_OPEN | CG-001 / CORE-GAP-FIX-001 |
| D Summary | forward revisions, subject isolation, source provenance and identity | DimensionSummary + #127 A06-A08 owner scope, provenance validation and owner-qualified identity | dimension summary tests; A06-A08 regressions | ALREADY_FIXED | AF-011 |
| D Summary | due review/backlog must not permanently skip eligible work when service is invoked | PeriodicReviewService reopens NEW/QUEUED/RUNNING review, drains truncated backlog pages and advances windows | test_periodic_review_backlog_pages_do_not_permanently_skip_candidates | NOT_REPRODUCED | NR-003 |
| D Summary | intermediate virtual-clock deadline must be dispatched before next sealed input | Core exposes due-review service; virtual event-clock dispatch ordering belongs to operator | #125 identifies clock.py / driver.py as failing layer; CORE-OPERATOR-001 owns it | OUT_OF_SCOPE | OOS-001 |
| E Evidence / Provenance | cognition evidence must close to qualifying current pinned reality/case evidence | writeback/policy/revision validate pinned current evidence and dependency lineage | test_v3_c15_cognition_evidence_policy.py | NOT_REPRODUCED | no additional Core gap beyond CG-001 temporal cut |
| E Evidence / Provenance | execution provenance must survive ambiguous provider boundary | user turn persists only started/completed admission; generic Wake/Review has no durable provider-attempt IN_DOUBT identity | turn_execution.py; cognitive_runtime.py; periodic review restart behavior | STILL_OPEN | CG-002 / CG-003 |
| F Claim / Event / Policy | root revision and downstream invalidation atomicity | revision/event services commit root + invalidation plan under shared CAS | #127 A01/A03 regressions | ALREADY_FIXED | AF-006 / AF-008 |
| F Claim / Event / Policy | paired user/AI-self propagation without other-user contamination | runtime invalidation scope explicitly includes resident user + paired AI self | #127 A02 regression | ALREADY_FIXED | AF-007 |
| F Claim / Event / Policy | stale/superseded policy evidence rejected | policy validation requires current active exact revisions under CAS | #127 A04 regressions | ALREADY_FIXED | AF-009 |
| F Claim / Event / Policy | long dependency DAG/cycle safety with exact revisions | iterative exact-version dependency cycle validation | #127 A10 regressions | ALREADY_FIXED | AF-012 |
| G Goal / Task / Action / Outcome | cancel -> authorize race must fail closed | execution service revalidates current RUNNING parent Task before authorization and forward-invalidates pending Action | test_cancelled_parent_task_cannot_authorize_retry_or_restart; test_cancel_authorize_race_is_fail_closed | ALREADY_FIXED | AF-001 |
| G Goal / Task / Action / Outcome | non-Action Task terminal state requires real configured evidence | completion_condition modes world_evidence / action_outcome / mixed; terminal evidence current/pinned/same-subject | test_non_action_verification_task_completes_from_real_world_evidence and negative cases | ALREADY_FIXED | AF-004 |
| G Goal / Task / Action / Outcome | prepared/queued must not be reported completed without completion evidence | terminal transition validation and Outcome/evidence lineage are enforced; no new bypass located | execution service + T35 regressions | NOT_REPRODUCED | NR-004 |
| H Wake | creation, merge, dedupe, cooldown, state lifecycle | WakeBus deterministic signal identity, exact retry detection, NEW/QUEUED/RUNNING lifecycle | test_v3_wake_dispatch.py | NOT_REPRODUCED | NR-005 |
| H Wake | user-visible Wake delivery exactly once across crash after delivery persistence | assistant delivery committed before Wake completion; restart detects durable delivery and completes without model reinvocation | test in test_v3_attention_watch.py simulating crash after delivery persistence | ALREADY_FIXED | AF-014 |
| H Wake | sealed old Wake must not see a later fixture event | current known failure is operator pre-ingest clock ordering, not a src/aios_core change | PR #125 round3 identifies clock.py/driver.py; dedicated CORE-OPERATOR-001 exists | OUT_OF_SCOPE | OOS-002; CG-001 separately covers true Core temporal read isolation |
| H Wake | ambiguous model execution while Wake is RUNNING must not be blindly re-invoked | no Wake-scoped durable model execution admission; RUNNING Wake can enter CognitiveRuntime again | current run_wake / WakeBus claim inspection | STILL_OPEN | CG-002 / CORE-GAP-FIX-002 |
| I Review / Cognitive Loop | periodic review restart, backlog, correction and no self-loop | RUNNING review resumable; backlog pages drain; cognition revision uses evidence; C14 loop has durable requeue/reconcile | periodic review + C14 runtime/scheduler regressions | NOT_REPRODUCED | NR-006, except CG-001/CG-002 |
| I Review / Cognitive Loop | Summary -> derivation crash-gap reconciliation / dedupe | scheduler reconciles current Summary revisions and deterministic wake identity | test_commit_crash_gap_is_recovered_after_store_and_scheduler_restart_and_retry_is_idempotent | ALREADY_FIXED | covered by accepted C14 scheduler hardening |
| J Metering / Budget | non-world model-call ledger must not advance world_revision | ModelMeteringLedger writes metering_records side table only | tests/runtime/test_metering_ledger.py | ALREADY_FIXED | AF-013 |
| J Metering / Budget | provider request identity / unknown usage / crash-before-Wake-complete accounting | provider request ID makes replay idempotent; unknown usage is unknown not zero; metering occurs immediately after ModelDirective return | metering tests; test_provider_usage_is_durable_even_if_wake_completion_crashes | ALREADY_FIXED | AF-013; provider exception before a Directive remains CG-002 |
| J Metering / Budget | budget denial, deferral and rollover | BackgroundBudgetGate reserves RUNNING spend; Wake/Review defer and next-window resume are durable | test_v3_background_budget_gate.py | NOT_REPRODUCED | NR-007 |
| J Metering / Budget | operator must not force budget-deferred Wake before release | driver/clock concern, not current Core budget semantics | #125 round3 | OUT_OF_SCOPE | OOS-003 |
| K Provider / Model Boundary | typed model result + provenance/usage handoff | CognitiveRuntime consumes ModelDirective; ModelUsage / ModelCallProvenance; metering callback immediately after return | cognitive runtime + metering tests | NOT_REPRODUCED | real production adapter wiring is CORE-HEADLESS-001 |
| K Provider / Model Boundary | timeout / transport exception / uncertain provider execution must have durable identity and safe retry disposition | model_handler exception happens before recorder; Wake/Review RUNNING state alone does not say whether provider accepted/executed request | cognitive_runtime.py ordering + current restart paths | STILL_OPEN | CG-002 |
| L Persistence / Restart | user-turn duplicate execution after completion/restart must be refused | TurnExecutionStore durable admission keyed by subject/session/turn; completed or existing assistant output blocks re-inference | #127 A09 tests | ALREADY_FIXED | A09 closed duplicate-replay bug |
| L Persistence / Restart | interrupted user turn must have supported inspect/reconcile/retry disposition without DB surgery | TurnExecutionStore only has started/completed; started retry raises TurnExecutionInDoubt; no supported resolve/reconcile transition | A09 exception/write-crash tests explicitly remain IN_DOUBT | STILL_OPEN | CG-003 / CORE-GAP-FIX-003 |
| L Persistence / Restart | install/start/stop/supervision/configuration entry | explicitly scheduled as CORE-HEADLESS-001 after audit/gaps | completion plan | OUT_OF_SCOPE | OOS-004 |
| L Persistence / Restart | full backup/restore/schema-upgrade/fault-injection campaign | explicitly scheduled as CORE-RECOVERY-001 | completion plan | OUT_OF_SCOPE | OOS-005 |

## 4. Confirmed open gaps

### CG-001 — RUNTIME_TEMPORAL_READ_CUT

Verdict: STILL_OPEN  
Blocker class: temporal integrity / provenance / recovery correctness

#### Reproduction / evidence

Current source has two incompatible time semantics:

1. WorldSearchIndex already implements AS_KNOWN filtering by learned_at and fails closed if learned_at is missing/corrupt.
2. FusedTurnRuntime._world_map_context(as_of) passes the active execution time into the dimension directory.
3. FusedTurnRuntime._search_world calls index.recall_candidates without an as_of/view cutoff.
4. FusedTurnRuntime._inspect_world_object calls store.get_payload directly and has no learned_at cutoff.
5. resumed COGNITIVE_DERIVATION work pins _active_turn_time to runtime_first_started_at / started_at.
6. resumed Periodic Review pins write time to the original started_at.

Therefore a resumed execution can have write time T1, ingest a new fact at T2 > T1, resume at T2, search/inspect the current World and read the T2 fact, then commit cognition whose learned_at/changed_at is T1.

This is a Core defect even though #125 also has an operator-specific old-Wake fixture-ordering defect. Correct operator ordering prevents one synthetic manifestation; it does not close the general resumed-execution temporal cut.

#### Affected source

- src/aios_core/runtime/turn_runtime.py
  - _search_world
  - _inspect_world_object / _scoped_payload
  - read capabilities that expose current cognition/world data
  - resumed C14 and Periodic Review _active_turn_time handling
- src/aios_core/query/search.py AS_KNOWN support

#### Expected

Any execution whose cognition/write clock is deliberately pinned to Tcut must either:
- read through the same AS_KNOWN cutoff across all relevant read capabilities, or
- advance its write clock to the real later execution time with explicit semantics.

It must not read T2 knowledge and persist it as if learned at T1.

#### Actual

World-map directory is time-cut, but semantic search/exact object reads remain current-world reads.

#### Impact

- future-data leakage into resumed/historical execution;
- backdated cognition/evidence;
- historical replay and recovery no longer deterministic;
- evidence lineage may be exact by revision but temporally impossible.

#### Minimal proposed fix scope

CORE-GAP-FIX-001:
- define one runtime read cutoff for an active execution;
- apply it to search_world, inspect_world_object, AI-world/current cognition reads and other model-visible World reads that can return learned-after-cut data;
- reuse existing AS_KNOWN machinery where possible;
- fail closed when an exact object is not yet known at the cutoff;
- add targeted regressions for resumed C14, resumed Periodic Review, ordinary historical turn, and exact-object drill-down;
- do not redesign World or operator.

Block headless: YES for safe due-work/resume  
Block recovery: YES  
Block RC freeze: YES  
Resident re-experiment after fix: YES; any Core tree change must be frozen first and followed by planned fresh A/B/C. Do not patch historical evidence.

### CG-002 — BACKGROUND_MODEL_EXECUTION_IN_DOUBT

Verdict: STILL_OPEN  
Blocker class: provider execution uncertainty / duplicate model invocation / recovery

#### Reproduction / evidence

CognitiveRuntime order is:
1. call model_handler(snapshot);
2. receive ModelDirective;
3. record usage/provenance immediately;
4. execute capability calls / finish Wake.

That correctly protects the post-return crash window, and C13 tests prove metering survives a crash after the provider returns and before Wake completion.

The unresolved window is before a ModelDirective is durably returned:
- provider may accept/execute a request;
- transport/process can fail before Core receives the response/provenance;
- model_usage_recorder is never called;
- the Wake or Periodic Review remains RUNNING;
- unlike run_turn, run_wake/run_periodic_review has no durable provider-attempt admission record equivalent to TurnExecutionStore.

WakeBus.claim treats an already RUNNING Wake as resumable. PeriodicReviewService explicitly treats RUNNING review as resumable. Existing tests confirm a restarted worker may invoke the model for a RUNNING review. Background budget reservations can delay retry, but absence of a budget policy or a later budget window does not resolve whether the prior provider request executed.

#### Affected source

- src/aios_core/runtime/cognitive_runtime.py
- src/aios_core/runtime/turn_runtime.py run_wake / run_periodic_review
- src/aios_core/wake/service.py
- src/aios_core/review/periodic.py
- src/aios_core/runtime/metering.py

#### Expected

A provider attempt must have a durable execution identity and explicit state sufficient to distinguish:
- definitely not submitted / retryable;
- completed with provider response identity;
- UNKNOWN / IN_DOUBT;
- reconciled terminal state.

RUNNING Wake/Review lifecycle state alone is insufficient proof that re-invoking the provider is safe.

#### Actual

A crash/timeout/transport exception before ModelDirective return leaves no model-attempt record. A later resumed RUNNING Wake/Review may invoke the provider again.

#### Impact

- duplicate provider execution and spend;
- non-deterministic recovery;
- inability to prove at-most-once or deliberate at-least-once semantics;
- UNKNOWN execution can be silently converted into a later fresh execution.

#### Minimal proposed fix scope

CORE-GAP-FIX-002:
- add durable model-attempt admission/provenance for non-user-turn Resident executions keyed to Wake/Review identity + model round;
- record attempt before provider dispatch and durable provider response identity immediately after return;
- introduce explicit UNKNOWN/IN_DOUBT on ambiguous failure;
- recovery must refuse blind provider reinvocation until reconciled by defined policy;
- integrate with existing MeteringLedger instead of creating a second truth store;
- add crash/timeout tests around before-send / after-send-before-response / after-response-before-meter / after-meter-before-Wake-complete.

Block headless: YES  
Block recovery: YES  
Block RC freeze: YES  
Resident re-experiment after fix: YES after RC freeze; no historical backfill.

### CG-003 — USER_TURN_IN_DOUBT_RECOVERY

Verdict: STILL_OPEN  
Blocker class: liveness / authorized recovery / durable execution state machine

#### Reproduction / evidence

The A09 repair correctly prevents duplicate model calls:
- runtime_turn_executions state is only started or completed;
- same input against started raises TurnExecutionInDoubt;
- provider exception leaves started;
- assistant-output write crash leaves started;
- restart with same turn identity remains IN_DOUBT and does not call the model twice.

The current module docstring explicitly says the mechanism is durable at-most-once admission, not general mid-turn crash recovery. There is no public supported transition to inspect/reconcile a started row into a safe retryable/aborted/completed disposition.

#### Affected source

- src/aios_core/runtime/turn_execution.py
- src/aios_core/runtime/turn_runtime.py
- tests/integration/test_v3_audit_bugfixes.py A09 cases

#### Expected

Keep A09 fail-closed admission, but provide a supported recovery path that can:
- inspect durable receipts/output/metering for the exact turn;
- resolve definitely-completed cases;
- preserve UNKNOWN where proof is insufficient;
- allow a narrowly authorized retry only when non-execution is established;
- never require clearing the table or changing turn_id.

#### Actual

started is a durable terminal dead-end for the same turn identity unless external code directly edits storage or abandons the turn.

#### Impact

- a transport/process interruption can strand a real user turn;
- recovery cannot close the uncertainty without unsupported DB surgery;
- CORE-RECOVERY-001 cannot satisfy the plan's “no clear-table / no turn_id bypass” rule using current public Core semantics.

#### Minimal proposed fix scope

CORE-GAP-FIX-003:
- add an explicit inspection/reconciliation API and typed durable states/receipts around started;
- preserve current refusal of blind retry;
- define authorized transitions and evidence requirements;
- targeted restart tests for provider interruption, pre-model failure, assistant-write failure, completed-output recovery and conflicting input.

Block headless: NO for a minimal smoke start, YES for robust resident service operation  
Block recovery: YES  
Block RC freeze: YES  
Resident re-experiment after fix: YES after RC freeze if the Core tree changes.

## 5. Already-fixed historical findings

Count: 14.

### AF-001 — T34 Action cancel -> authorize race
Verdict: ALREADY_FIXED. Current execution service verifies the parent Task is the current RUNNING revision before authorization and cancellation forward-invalidates the pending proposal. Current P12 tests cover same-process, restart and true cancel/authorize race.

### AF-002 — T36 structured Observation scalar retrieval
Verdict: ALREADY_FIXED. search.py recursively projects mapping keys and scalar values for Observation.value into the rebuildable index without rewriting World truth. T36 targeted tests cover incremental/rebuild/subject/current/inactive behavior.

### AF-003 — T28 assistant raw dialogue as proactive user memory
Verdict: ALREADY_FIXED. Raw assistant dialogue stays explicitly searchable for audit, but ProactiveMemoryRecommender rejects it as independent proactive/user evidence. Dedicated T28 regression proves assistant-only cards are empty while user dialogue remains eligible.

### AF-004 — T35 non-Action Task completion evidence
Verdict: ALREADY_FIXED. Task completion modes now distinguish world_evidence, action_outcome and mixed. Terminal transitions require qualifying pinned evidence and reject assistant self-assertion/fake Outcome/stale/cross-subject lineage.

### AF-005 — T33 cross-session antecedent over-trigger
Verdict: ALREADY_FIXED. Cross-session recall now requires discourse/deictic cues and bounded candidate recovery; self-contained continuation language no longer opens antecedent recall.

### AF-006 — A01 revision root + downstream invalidation atomicity
Verdict: ALREADY_FIXED. Root revision and propagation plan share CAS/transaction; failure leaves every revision intact. A01 tests cover forward history and injected commit failure.

### AF-007 — A02 invalidation propagation subject scope
Verdict: ALREADY_FIXED. Runtime invalidation includes resident user plus paired AI-self but excludes another user. Regression exists.

### AF-008 — A03 Event lifecycle downstream invalidation
Verdict: ALREADY_FIXED. Event rejection/correction invalidates dependent cognition under the same atomic boundary. Regression covers Claim/Summary/search effects.

### AF-009 — A04 stale/superseded policy evidence
Verdict: ALREADY_FIXED. Policy evidence is checked as current/active and validation shares CAS with commit. Regressions cover stale/superseded evidence and hard-limit fail-closed reads.

### AF-010 — A05 World/Index logical-commit alignment
Verdict: ALREADY_FIXED. catch_up consumes complete logical commits, serializes watermark publication, and failed projection work cannot advance the watermark. Concurrent catch-up and rebuild regressions exist.

### AF-011 — A06/A07/A08 Summary ownership, provenance and identity
Verdict: ALREADY_FIXED. User and paired AI-self scoping is explicit; prepared inputs are revalidated against exact World sources/cut; summary IDs include owner; legacy ownership is resolved rather than silently merged. Regressions cover late source, truncation, tampering and legacy ownership.

### AF-012 — A10 dependency graph exact-version / long-DAG safety
Verdict: ALREADY_FIXED. Cycle validation is iterative and exact-version aware; long DAG commits and long-cycle atomic rejection are covered.

### AF-013 — C13 metering / budget persistence
Verdict: ALREADY_FIXED. ModelMeteringLedger is a non-world SQLite side table; writes do not advance world_revision; provider response identity makes replay idempotent; unknown token usage remains UNKNOWN; budget uses durable ledger rows and RUNNING reservations. Budget-deferral/rollover tests exist.

### AF-014 — C15 Wake user-delivery persistence recovery
Verdict: ALREADY_FIXED. A delivered assistant response is persisted before Wake completion. Restart detects that durable delivery and completes the RUNNING Wake without invoking the model again; suppressed/internal/silent Wake paths do not fabricate user interaction.

## 6. Not reproduced

Count: 7.

### NR-001 — World transaction / duplicate / stale-write corruption
Verdict: NOT_REPRODUCED.
Method: inspected SQLiteWorldStore commit/idempotency/current-revision logic and W01-W05 atomicity tests. Existing exact-tree evidence covers rollback, concurrent writers and idempotent replay.
Why not STILL_OPEN: no path found that advances world_revision on a failed multi-object commit or accepts a stale writer.

### NR-002 — normal index crash/restart losing a newly committed World revision
Verdict: NOT_REPRODUCED.
Method: inspected catch_up/rebuild transaction and A05 failure/concurrency tests.
Why not STILL_OPEN: projection transaction publishes watermark only after indexed rows; restart can catch up from durable World. Historical already-corrupt projection still requires explicit offline rebuild, which is documented and does not rewrite World.

### NR-003 — Summary / Periodic Review silently skipping backlog when invoked
Verdict: NOT_REPRODUCED.
Method: inspected prepare_due_review and backlog paging tests.
Why not STILL_OPEN: truncated pages remain backlog and are drained; completed review does not self-trigger immediately. The service does not own wall-clock polling.

### NR-004 — prepared/queued work becoming completed without completion evidence
Verdict: NOT_REPRODUCED.
Method: inspected Task terminal boundary and T35 positive/negative regressions.
Why not STILL_OPEN: terminal Task transition requires the configured World evidence and/or real Outcome path; labels such as prepared/queued alone cannot create terminal proof.

### NR-005 — Wake dedupe/repeated-delivery lifecycle corruption outside provider ambiguity
Verdict: NOT_REPRODUCED.
Method: inspected WakeBus emit/claim/defer/finish and C09 retry/cooldown/out-of-order tests plus C15 delivery recovery.
Why not STILL_OPEN: exact signal retries are idempotent; pending same-scope hits merge; persisted delivery recovery is exactly-once. CG-002 is the separate provider-execution boundary.

### NR-006 — Periodic/C14 loop losing durable pending work across ordinary restart
Verdict: NOT_REPRODUCED.
Method: inspected RUNNING review recovery, C14 runtime-incomplete requeue and scheduler reconcile tests.
Why not STILL_OPEN: durable Wake/Review/Summary state is sufficient to rediscover pending work. CG-001 and CG-002 remain because rediscovery does not by itself make temporal reads or provider retries safe.

### NR-007 — Core budget deferral / rollover discarded
Verdict: NOT_REPRODUCED.
Method: inspected BackgroundBudgetGate, WakeBus.defer, PeriodicReviewService.defer_review and budget tests.
Why not STILL_OPEN: Core keeps deferred work durable and resumes in an eligible later window. PR #125's failure is a driver forcing problem, not the Core budget gate.

## 7. Out of scope

Count: 6.

### OOS-001 — PR #125 intermediate 24h virtual-clock Review dispatch
Verdict: OUT_OF_SCOPE.
Reason: owned by CORE-OPERATOR-001 clock/driver sequencing. Core exposes prepare_due_review; this audit does not implement the event loop.

### OOS-002 — PR #125 sealed fixture old-Wake future-input ordering
Verdict: OUT_OF_SCOPE.
Reason: the exact #125 repro identifies pre-ingest dispatch ordering in tools/c15_preflight/clock.py and driver.py. CORE-OPERATOR-001 owns that repair. CG-001 is retained separately because current Core itself also lacks a uniform historical read cutoff during resumed executions.

### OOS-003 — PR #125 budget-deferred Wake forced by operator
Verdict: OUT_OF_SCOPE.
Reason: current Core defer/rollover semantics are present; driver must not override them.

### OOS-004 — actual headless CLI/service/process supervisor/install/config entry
Verdict: OUT_OF_SCOPE.
Reason: explicitly assigned to CORE-HEADLESS-001 after this audit and blocking gap disposition.

### OOS-005 — full backup/restore/schema-upgrade/fault-injection certification campaign
Verdict: OUT_OF_SCOPE.
Reason: explicitly assigned to CORE-RECOVERY-001. This audit identifies foundational blockers but does not execute that campaign.

### OOS-006 — UI / Launcher appearance / digital human / animation / bracelet hardware / Android ROM
Verdict: OUT_OF_SCOPE.
Reason: explicitly excluded from Core completion.

## 8. Recommended task split

Only the following minimal Core tasks are recommended. Do not start them in this audit.

### CORE-GAP-FIX-001 — Runtime temporal read cutoff
Scope:
- bind all Resident model-visible read capabilities to one explicit active execution cutoff whenever writes are time-pinned;
- use existing AS_KNOWN semantics where possible;
- reject exact-object reads not yet known at cutoff;
- targeted regressions only.

Do not redesign World, Summary, or operator.

### CORE-GAP-FIX-002 — Wake/Review model execution uncertainty
Scope:
- durable model-attempt identity/state for Wake/Review + model round;
- provider attempt admission before dispatch, completed provenance after return, explicit UNKNOWN/IN_DOUBT;
- recovery must not blindly call provider again;
- integrate with MeteringLedger and existing Wake lifecycle.

Do not change Resident semantics or historical evidence.

### CORE-GAP-FIX-003 — user-turn IN_DOUBT reconciliation
Scope:
- supported inspection/reconciliation state machine for a started user turn;
- preserve A09 at-most-once default;
- narrowly authorize retry only with proof of non-execution;
- no clear-table, no turn-id swap.

## 9. RC-freeze disposition

RC freeze remains blocked by:
- CG-001 RUNTIME_TEMPORAL_READ_CUT
- CG-002 BACKGROUND_MODEL_EXECUTION_IN_DOUBT
- CG-003 USER_TURN_IN_DOUBT_RECOVERY

This audit does not declare Core DONE, Headless READY, Recovery PASS, RC READY, or Resident PASS.

Operator/preflight closure remains an independent parallel prerequisite and is not counted as a Core gap here.

## 10. Final audit verdict

AUDIT_COMPLETE

Current audited Core has broad mechanism closure and the historical T28/T33/T34/T35/T36, #127 A01-A10, C13 metering/budget and Wake-delivery defects inspected here are no longer open on the audited Core tree. Three release-level Core gaps remain, all centered on temporal consistency and ambiguous model execution/recovery boundaries. They require independent minimal fix tasks before RC freeze.
