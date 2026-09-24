# CORE-HEADLESS-001 Independent Acceptance — 2026-09-24

## Verdict

**ACCEPTANCE_FAIL**

- Blocker count: **1**
- Review-time live `main`: `19b1b427cc8e28d23bd4ae13828027d38fcf1649`
- Candidate PR: #181 — `CORE-HEADLESS-001: installable persistent headless Core entrypoint`
- Tested implementation exact head: `a43c2e9408e51ec8812e9f6ec808a71401bc2841`
- Evidence-only handoff head: `12928af4ffa40e70d9ae80124dab388a486f7097`
- Construction base confirmed: `8d724f96aa286549e4e12a2245d28ff5dce6f77b`

PR #181 is not independently accepted for PM integration at this head because the same durable World can be opened by two writable HeadlessCore processes when they are configured with different lock paths.

No candidate repair was performed. PR #181 was not merged. CORE-RECOVERY-001, Resident, UI, and hardware were not entered.

## 1. Pin and candidate structure

The implementation/evidence pin is valid:

- `a43c2e9408e51ec8812e9f6ec808a71401bc2841 -> 12928af4ffa40e70d9ae80124dab388a486f7097` is exactly one commit.
- That delta adds only:
  - `reviews/CORE_HEADLESS_001_COMPLETION_EVIDENCE_2026-09-24.md`
- The tested implementation candidate is based on construction base `8d724f96aa286549e4e12a2245d28ff5dce6f77b`.
- Relative to that construction base, the implementation changes exactly seven files:
  1. `.github/workflows/core-headless.yml`
  2. `pyproject.toml`
  3. `src/aios_core/headless/__init__.py`
  4. `src/aios_core/headless/cli.py`
  5. `src/aios_core/headless/core.py`
  6. `src/aios_core/headless/testing.py`
  7. `tests/integration/test_core_headless.py`
- No `src/aios_core/runtime/**` implementation is changed by HEADLESS.

At final review recheck, PR #181 remained OPEN / non-draft / unmerged with handoff head `12928af4...`.

## 2. Governance state

Live repository control files confirm:

`CORE-HEADLESS-001 = GATE / REVIEW_READY`.

FIX-001, FIX-002, and FIX-003 are already integrated and CLOSED. RECOVERY, SCALE, RC-FREEZE, and fresh Resident work remain blocked behind HEADLESS acceptance.

## 3. Architecture verdict — PASS

The headless layer remains a lifecycle/configuration shell over the existing Core.

`HeadlessCore.start()` opens:

- the existing `SQLiteWorldStore`;
- the existing rebuildable `WorldSearchIndex`;
- the existing `FusedTurnRuntime`.

The wrapper routes work through existing accepted paths:

- user turn -> `FusedTurnRuntime.run_turn(...)`;
- external fact -> existing `RealityIngestService`;
- Wake -> `dispatch_next_pending_wake(...)` / existing `run_wake(...)`;
- Periodic Review -> existing `run_periodic_review(...)`;
- user-turn recovery -> existing `TurnExecutionStore` / inspection and authorization mechanisms;
- background provider attempt truth -> existing `BackgroundModelAttemptStore`;
- metering/budget -> existing runtime-owned mechanisms.

No second World database, semantic runtime, cognition truth store, scheduler, attempt/recovery ledger, or model contract was found in the HEADLESS implementation.

## 4. Installation / CLI verdict — PASS

`pyproject.toml` preserves:

- `requires-python = ">=3.12"`;
- normal console entrypoint:
  `aios-core-headless = "aios_core.headless.cli:main"`.

The exact-head `core-headless` workflow used a clean non-editable install:

`pip install ".[dev]"`

and successfully built/installed `aios-core-0.3.0.dev0`.

Installed CLI smoke then ran three separate processes against the same configured World:

1. status: `world_revision=0 / index_watermark=0 / index_lag=0`;
2. normal turn: response `HEADLESS_MECHANICAL_OK`, resulting `world_revision=2`;
3. reopened status: `world_revision=2 / index_watermark=2 / index_lag=0`.

The deterministic handler is test-only and is not selected by default. Missing World/model handler configuration fails explicitly. Production adapter loading remains provider-neutral through the existing callable `ModelHandler` boundary.

## 5. Persistent World / index verdict — PASS

The configured World path is opened through `SQLiteWorldStore`; restart reopens the same durable World and does not reset its revision.

`WorldSearchIndex` remains a projection:

- it owns a separate index SQLite path;
- its watermark is derived from World revisions;
- `catch_up()` replays World revisions;
- status reports World/index operational values only.

No headless status database or reconstruction ledger was introduced.

## 6. Single-writer verdict — FAIL

### CORE-HEADLESS-001-ACCEPT-BLOCKER-001

**Same-World writer exclusion is bypassable by configuring a different `lock_path`.**

Mechanism:

- `HeadlessConfig` accepts an arbitrary `lock_path` independent of `world_path`.
- `HeadlessCore` creates `_WriterLease(config.lock_path)`.
- POSIX exclusion is therefore an `flock` on the chosen lock-file inode, not on an identity that is obligatorily canonical for the resolved World.
- Two HeadlessCore instances can point at the same `world.sqlite` while pointing at `writer-a.lock` and `writer-b.lock`.
- Those two OS leases do not conflict.

Independent probe PR #184 (CLOSED / UNMERGED) mechanically confirmed the defect.

Probe head:
`f36665541742badde3b7c20e24528668b5ba3f59`

Probe run:
- workflow: `core-headless`
- run: `35992018738`
- job: `107608100032`
- conclusion: **FAILURE**

The job first passed clean install and installed-CLI smoke. Targeted tests then ended:

`.........F [100%]`

The sole failure was:

`test_independent_probe_same_world_cannot_bypass_writer_lease_with_alt_lock_path`

Expected:
`HeadlessWriterBusy`

Observed:
no exception; the second HeadlessCore opened successfully.

This violates the acceptance requirement that a concurrent writable open on the same World fail closed.

The fix must preserve a single writer identity that cannot be bypassed by choosing another diagnostic/configured lock pathname. This review does not implement that repair.

## 7. Writer-lease adversarial probes

Independent probe PR #184 was created only against the PR #181 handoff branch, changed the headless test file only, and was closed without merge after evidence capture.

Results at final probe head:

1. **Stale lease artifact — PASS**
   - A stale lock-file body without an active OS lease did not brick the World.
   - A new HeadlessCore acquired the OS lease and reopened the same World.

2. **Competing writer using the same configured lease path — PASS**
   - Writer B raised `HeadlessWriterBusy` while writer A held the lease.
   - World revision did not change during the failed startup.
   - After writer A stopped, writer B could open.

3. **FIX-002 IN_DOUBT through wrapper restart — PASS for preservation/no blind reinvocation**
   - First headless due execution crossed the provider boundary and failed ambiguously.
   - Provider call count became one.
   - After restart, `process_due_work(...)` did not invoke the provider again.
   - Directly re-addressing the same durable Wake through the existing runtime raised `BackgroundModelExecutionInDoubt`.
   - Provider call count remained one.

4. **Same World with alternate lock path — FAIL**
   - Writer A and writer B used the same World with different lock paths.
   - Writer B was not rejected.
   - This is the acceptance blocker above.

Observation for later recovery work: after restart, the IN_DOUBT Wake is not blindly redispatched by bounded due processing; the existing attempt ledger still reports IN_DOUBT when the exact Wake is addressed. This review counts preservation/no-blind-reinvoke as PASS for matrix D and does not treat recovery/reconciliation UX as a second HEADLESS blocker.

## 8. Restart matrix A-F

### A — PASS

Normal user turn and durable assistant output survive stop/restart on the same World. Installed CLI smoke and `test_headless_start_turn_ingest_stop_restart_same_world` both support this.

### B — PASS

A durable pending Wake survives stop/restart, executes after reopen through existing Wake mechanics, and is not redispatched after a further restart.

### C — PASS

FIX-003 pre-admission recovery survives restart:

- simulated failure occurs before provider-attempt admission;
- provider call count remains zero;
- inspection reports the existing safe-to-retry disposition;
- blind rerun fails closed;
- existing explicit retry authorization allows one provider execution.

### D — PASS

FIX-002 background IN_DOUBT survives restart and does not cause blind provider reinvocation. The independent probe above rechecked this through the headless due wrapper plus direct existing-runtime inspection.

### E — PASS

FIX-001 historical knowledge cut survives restart. A late-known fact is excluded from model-visible historical search when the resumed Wake executes at the earlier cutoff.

### F — PASS

Repeated lifecycle does not fabricate duplicates in reviewed paths:

- no World revision change from idle reopen;
- user-turn model-meter count remains unchanged across reopen;
- completed Wake is not dispatched again;
- assistant output is not reconstructed from process logs.

Existing Periodic Review/runtime compatibility tests also passed at the exact implementation head.

## 9. FIX-001 / FIX-002 / FIX-003 compatibility — PASS

The HEADLESS candidate does not rewrite the accepted runtime implementations.

- FIX-001 temporal cut remains in existing runtime call paths and the dedicated headless historical-cut test passes.
- FIX-002 attempt truth remains in the existing background attempt ledger; restart does not blindly reinvoke the provider.
- FIX-003 user-turn recovery remains in existing turn execution + shared attempt truth; explicit authorization is still required before the safe retry path.

No second recovery ledger was introduced.

## 10. Wake / Review / metering / output duplication — PASS

The reviewed wrapper uses the existing Wake/Periodic Review methods rather than a new queue.

Exact-head headless compatibility covered:

- fused turn runtime;
- Wake dispatch;
- Periodic Review;
- Reality ingest;
- C14 derivation runtime;
- AI World;
- execution World;
- FIX-002 background attempts;
- FIX-003 turn recovery;
- CognitiveRuntime.

The dedicated restart tests show no repeated completed Wake dispatch and no extra user-turn metering row or assistant reconstruction on reopen.

## 11. Provider-neutral ModelHandler — PASS

`load_model_handler("module:attribute")` imports a callable and passes it to the existing `FusedTurnRuntime` / `CognitiveRuntime` model boundary.

No OpenAI/Anthropic/other provider is hard-coded as a constitutional runtime dependency. Provider credentials/configuration remain adapter responsibilities.

The deterministic `aios_core.headless.testing:deterministic_model_handler` is explicitly test-only and not an implicit production default.

## 12. Exact-head CI — PASS

All required recorded workflows are tied to PR #181 merge-ref with exact implementation head `a43c2e9408e51ec8812e9f6ec808a71401bc2841` merged into construction base `8d724f96aa286549e4e12a2245d28ff5dce6f77b`.

| Gate | Run | Job | Result |
|---|---:|---:|---|
| core-headless | `35990125345` | `107601955259` | SUCCESS |
| world-kernel | `35990125344` | `107601955124` | SUCCESS |
| constitutional-cognition-closure | `35990125360` | `107601955110` | SUCCESS |
| full P16 | `35990125343` | `107601954956` | SUCCESS |

Exact-head environment re-read from raw logs:

- CPython `3.12.14`
- pytest `8.4.2`
- pydantic `2.13.5`

The headless exact run passed six dedicated tests and its existing runtime compatibility step reached 100%.

## 13. Full P16 — PASS

Full P16 job `107601954956` ran direct:

`pytest -q`

and reached `[100%]`.

Independent raw-log marker count: **668 pass markers**, with zero failure/error output and workflow conclusion SUCCESS.

## 14. Live-main drift — COMPATIBLE / NO REBASE REVALIDATION REQUIRED

Review-time main is:

`19b1b427cc8e28d23bd4ae13828027d38fcf1649`

Compared with construction base `8d724f96...`, the live-main drift is limited to governance/control material:

- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `governance/prompts/CORE_HEADLESS_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

No `src/**`, packaging-contract, candidate test-contract, or relevant workflow change occurred on main after construction.

Therefore the verdict is not `REBASE_REVALIDATION_REQUIRED`. The candidate fails on an independently reproduced implementation property.

## 15. Final decision

**ACCEPTANCE_FAIL**

**Blocker count: 1**

Open blocker:

`CORE-HEADLESS-001-ACCEPT-BLOCKER-001 — same-World writer exclusion can be bypassed by alternate lock_path configuration.`

PR #181 must not be integrated as accepted until this single-writer defect is corrected and the corrected exact head receives fresh independent revalidation.

This review-only report does not merge PR #181 and does not enter CORE-RECOVERY-001.
