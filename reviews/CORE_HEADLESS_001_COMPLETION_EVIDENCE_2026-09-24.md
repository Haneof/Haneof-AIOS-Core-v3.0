# CORE-HEADLESS-001 Completion Evidence — 2026-09-24

## Corrective-001 final handoff

**Author state: REVIEW_READY**

This file now includes the engineering completion evidence for
`CORE-HEADLESS-001-CORRECTIVE-001`. This is not independent acceptance,
merge authorization, or a release receipt.

### Historical pins preserved

- Original engineering PR: #181
- Historical tested implementation exact head:
  `a43c2e9408e51ec8812e9f6ec808a71401bc2841`
- Historical evidence-only handoff head:
  `12928af4ffa40e70d9ae80124dab388a486f7097`
- Independent acceptance PR #185: **ACCEPTANCE_FAIL**
- Historical blocker:
  `CORE-HEADLESS-001-ACCEPT-BLOCKER-001`
- Independent probe PR #184: CLOSED / UNMERGED
- Probe head:
  `f36665541742badde3b7c20e24528668b5ba3f59`
- Probe run/job:
  `35992018738 / 107608100032`
- Historical failure:
  same canonical World could be opened by two writable HeadlessCore instances
  when different caller-selected `lock_path` values produced different OS
  lock-file inodes.

The historical FAIL remains historical evidence and is not rewritten as PASS.

### Corrective construction / live-main review

Corrective work continued on the original branch:
`core-headless-001-20260924-sol`.

Corrective start/final recheck live `main`:
`e7817b499856808e68490d8a2b07524f87a79da1`.

Compared with the original construction base
`8d724f96aa286549e4e12a2245d28ff5dce6f77b`, live-main drift remained
governance/review-only: checkpoint, task board, project map, corrective/acceptance
prompts, and independent review evidence. There was no relevant `src/**`,
packaging-contract, test-contract, or workflow semantic drift, so no rebase was
required by the corrective prompt.

### New tested exact implementation head

`16e983a536b124ddb600981fc16326d9db54358f`

The corrective delta after the historical evidence head modifies only:

1. `src/aios_core/headless/core.py`
2. `src/aios_core/headless/cli.py`
3. `tests/integration/test_core_headless.py`

No `src/aios_core/runtime/**` implementation was changed.

### Corrective mechanism

The writer lease identity is now derived exclusively from the canonical resolved
durable World path:

`<canonical-world-path>.writer.lock`

`HeadlessConfig.lock_path` no longer selects writer identity. If supplied, it is
validation-only and must equal the canonical derived lease path; any differing
path raises `HeadlessConfigurationError` before World startup.

The CLI `--lock` option and `AIOS_LOCK_PATH` remain compatibility/validation
inputs only. They cannot choose an alternate writer inode for the same World.

The actual exclusion primitive remains the process-held OS advisory lock:

- POSIX: `fcntl.flock(..., LOCK_EX | LOCK_NB)`
- Windows: `msvcrt.locking(..., LK_NBLCK, 1)`

Lock-file contents remain diagnostic metadata only. No PID-file or lock-file
content is used as World truth or liveness truth.

### Corrective regressions

The permanent HEADLESS suite now additionally proves:

- noncanonical explicit `lock_path` is rejected;
- same World cannot create a second lease identity through alternate lock path;
- failed competing startup does not advance/mutate World revision;
- normal same-path competing writer remains fail-closed with
  `HeadlessWriterBusy`;
- writer B can acquire the lease after writer A cleanly stops;
- stale canonical lock-file contents without an active OS lease do not brick the
  World;
- relative and absolute forms of the same World resolve to one canonical lease
  identity;
- a symlinked existing World resolves to the same canonical World and lease
  identity;
- CLI `--lock` override is validation-only and noncanonical input exits as a
  configuration failure;
- `AIOS_LOCK_PATH` is likewise validation-only.

The original A-F restart/recovery tests remain in the same suite.

### New exact-head Gate evidence

All runs below are tied to tested implementation exact head
`16e983a536b124ddb600981fc16326d9db54358f`.
GitHub checkout logs show the PR merge-ref as:

`Merge 16e983a536b124ddb600981fc16326d9db54358f into e7817b499856808e68490d8a2b07524f87a79da1`

| Gate | Run ID | Job ID | Result |
|---|---:|---:|---|
| core-headless clean install / installed CLI / corrective + A-F / runtime compatibility | `35993796247` | `107613844756` | **SUCCESS** |
| world-kernel | `35993796267` | `107613844605` | **SUCCESS** |
| constitutional-cognition-closure + P16 harness | `35993796265` | `107613844757` | **SUCCESS** |
| full P16 direct `pytest -q` | `35993796249` | `107613844795` | **SUCCESS** |

Exact-head environment from raw logs:

- CPython `3.12.14`
- pytest `8.4.2`
- pydantic `2.13.5`

The `core-headless` job used clean non-editable
`pip install ".[dev]"`, successfully executed the installed
`aios-core-headless` CLI across separate processes, preserved
`world_revision 0 -> 2 -> 2` and `index_watermark 0 -> 2`, and passed:

- corrective/headless lifecycle suite: `............. [100%]` (13 tests);
- existing HEADLESS runtime compatibility suite: `[100%]`.

World-kernel: 24 passed.

Constitutional cognition closure:
- closure gate: 91 passed;
- P16 harness regression: 92 passed.

Full P16:
- command: direct `pytest -q`;
- reached `[100%]`;
- independent raw-log count: **675 pass markers**;
- 0 failed / 0 errors observed;
- workflow/job conclusion: **SUCCESS**.

### Preserved semantics

The corrective does not redesign or modify:

- `FusedTurnRuntime` / `CognitiveRuntime`;
- FIX-001 temporal read cut;
- FIX-002 background attempt / IN_DOUBT recovery;
- FIX-003 user-turn recovery;
- Wake / Periodic Review;
- metering / budget;
- World/index architecture;
- provider-neutral `ModelHandler`.

No second World, runtime, scheduler, cognition truth store, or recovery ledger was
introduced.

### Evidence-only handoff boundary

The tested implementation exact head is
`16e983a536b124ddb600981fc16326d9db54358f`.

The commit that finalizes this evidence file is evidence-only and is not the
tested implementation head. Its exact SHA is pinned separately in PR #181 body
after this commit is created.

Fresh independent acceptance is required. Do not merge from this engineering
handoff.

---


## Author state

**REVIEW_READY**

This is engineering completion evidence only. It is not an independent acceptance, merge authorization, or release receipt.

## Pinned construction baseline and candidate

- Repository: `Haneof/Haneof-AIOS-Core-v3.0`
- Construction live `main`: `8d724f96aa286549e4e12a2245d28ff5dce6f77b`
- Tested exact implementation candidate: `a43c2e9408e51ec8812e9f6ec808a71401bc2841`
- Engineering PR: #181
- Branch: `core-headless-001-20260924-sol`
- Final pre-handoff main recheck: still `8d724f96aa286549e4e12a2245d28ff5dce6f77b`
- Candidate relation at recheck: `ahead`, `behind_by=0`

The commit adding this evidence file is review-only evidence layered on top of the tested implementation candidate above. No runtime/source behavior is changed by this evidence file.

## Reused existing Core entrypoints

CORE-HEADLESS-001 does not define a second runtime, World, recovery ledger, cognition engine, or scheduler. The headless layer reuses:

- `SQLiteWorldStore` for the canonical persistent World.
- `WorldSearchIndex` as the rebuildable search projection.
- `FusedTurnRuntime` / `CognitiveRuntime` as the executable Core path.
- `FusedTurnRuntime.run_turn(...)` for normal user turns.
- `RealityIngestService.ingest_record(...)` / `ingest_mapping(...)` for external facts.
- `FusedTurnRuntime.dispatch_next_pending_wake(...)` for pending Wake work.
- `FusedTurnRuntime.run_periodic_review(...)` for Periodic Review.
- `TurnExecutionStore` and `FusedTurnRuntime.inspect_turn_execution(...)` / existing retry authorization for FIX-003.
- `BackgroundModelAttemptStore` for FIX-002 attempt admission / IN_DOUBT behavior.
- `ModelMeteringLedger` and the existing background budget path.
- Existing model contract `ModelHandler = Callable[[RuntimeSnapshot], ModelDirective]`.
- Existing Core time normalization / historical cutoff behavior; the headless layer does not add a second logical clock.

## Exact implementation files changed

Relative to construction `main`, the tested implementation candidate changes only:

1. `.github/workflows/core-headless.yml`
2. `pyproject.toml`
3. `src/aios_core/headless/__init__.py`
4. `src/aios_core/headless/cli.py`
5. `src/aios_core/headless/core.py`
6. `src/aios_core/headless/testing.py`
7. `tests/integration/test_core_headless.py`

This completion evidence file is the only review/evidence addition after that tested implementation head.

Not modified by the implementation candidate:

- `src/aios_core/runtime/**`
- canonical WorldStore semantics
- Wake / Periodic Review implementations
- FIX-001 / FIX-002 / FIX-003 implementations

## Architecture boundary

The new `HeadlessCore` is a lifecycle/configuration shell around the existing Core:

1. acquire a minimal OS advisory writer lease;
2. open the configured canonical SQLite World;
3. open/catch up the rebuildable search index;
4. construct the existing `FusedTurnRuntime`;
5. route user turns, reality ingest, Wake, Review, metering and recovery through existing APIs;
6. release the writer lease on stop.

The writer-lock file is diagnostic/process coordination only and is explicitly not World truth. It contains no cognition state and is never consulted to reconstruct World state after restart.

No provider is hard-coded as a constitutional dependency. The CLI loads an installed existing `ModelHandler` callable by `module:attribute`; credentials/provider configuration remain the adapter's responsibility. Missing World/model configuration fails explicitly.

## Install and clean-run path

Python requirement: repository-supported Python >= 3.12.

Clean install used by the exact-head gate:

```bash
python -m pip install --upgrade pip
pip install ".[dev]"
```

Mechanical installed-CLI smoke:

```bash
WORLD=/tmp/aios-headless-smoke/world.sqlite
MODEL=aios_core.headless.testing:deterministic_model_handler

aios-core-headless --world "$WORLD" --model-handler "$MODEL" status

aios-core-headless --world "$WORLD" --model-handler "$MODEL" turn \
  --session smoke \
  --turn-index 1 \
  --text "mechanical smoke" \
  --at "2026-09-24T12:00:00+00:00"

aios-core-headless --world "$WORLD" --model-handler "$MODEL" status
```

Normal adapter path is provider-neutral:

```bash
aios-core-headless \
  --world /persistent/path/world.sqlite \
  --model-handler your_installed_adapter:model_handler \
  status
```

The referenced callable must obey the already-existing `RuntimeSnapshot -> ModelDirective` contract. `aios_core.headless.testing:deterministic_model_handler` is mechanical-test-only and is never selected by default.

## Start / stop / restart proof

Exact-head `core-headless` run:

- Workflow run: `35990125345`
- Job: `107601955259`
- Conclusion: **SUCCESS**

Observed installed CLI smoke from that job:

- initial open: `world_revision=0`, `index_watermark=0`, `index_lag=0`;
- normal turn returned `HEADLESS_MECHANICAL_OK` through the existing runtime and committed durable user + assistant observations, reaching `world_revision=2`;
- after process exit and reopening the same configured World: `world_revision=2`, `index_watermark=2`, `index_lag=0`.

This proves the clean-run path resumes the same durable World rather than silently creating a new logical state.

## Single-writer proof

`test_headless_single_writer_fails_closed_and_releases_on_stop` proves:

- one live writable headless process owns the configured World writer lease;
- a competing process fails explicitly with `HeadlessWriterBusy`;
- startup refusal does not replace or reset the World;
- after clean stop/release, another process can open the same World.

The lock is an OS advisory lease held for process lifetime; lock-file contents are not durable Core truth.

## Required restart scenarios A–F

### A — durable normal turn / World continuity

`test_headless_start_turn_ingest_stop_restart_same_world`

- user turn uses existing `run_turn`;
- external fact uses existing Reality ingest;
- durable World revision and fact survive stop/restart;
- search projection catches up to the same World.

### B — pending due work survives restart

`test_headless_restart_keeps_pending_due_work_and_executes_after_reopen`

- a Wake is durably emitted;
- process stops before model execution;
- reopened Core discovers/processes the pending Wake through existing due-work semantics;
- another restart does not execute the completed Wake a second time.

### C — FIX-003 user-turn pre-admission recovery survives restart

`test_headless_restart_preserves_fix003_pre_admission_and_requires_authorization`

- simulated process failure occurs before durable model-attempt admission;
- no provider call occurs;
- after restart, existing FIX-003 inspection reports the durable recovery disposition;
- blind rerun remains fail-closed;
- only existing explicit retry authorization permits the single subsequent provider execution.

### D — FIX-002 background IN_DOUBT survives restart

`test_headless_restart_preserves_fix002_background_in_doubt_without_reinvoke`

- background Wake crosses the existing dispatch boundary and encounters an ambiguous provider failure;
- durable attempt state remains governed by FIX-002;
- after restart, the same Wake raises `BackgroundModelExecutionInDoubt`;
- provider call count remains unchanged, proving no blind reinvocation.

### E — FIX-001 historical read cut survives resumed background execution

`test_headless_restart_keeps_fix001_historical_knowledge_cut`

- a fact occurred earlier but was received after the Wake's historical cutoff;
- process stops after durable Wake creation;
- restarted Core runs that Wake at the historical time;
- model-visible `search_world` does not expose the later-known fact;
- the background Wake therefore retains the existing FIX-001 knowledge-time cut after restart.

### F — repeated lifecycle does not fabricate duplicates

Covered by the A/B tests plus durable ledgers:

- repeated start/stop without work does not advance World revision;
- completed Wake is not redispatched after another restart;
- user turn output is not reconstructed from transient logs;
- `ModelMeteringLedger.list_model_calls(...)` remains exactly one record across restarts for the metered deterministic user turn;
- no assistant-output, Wake, or metering duplication is introduced by the headless wrapper.

Targeted exact-head headless tests: `...... [100%]`.

## Targeted compatibility and full regression evidence

All IDs below are for tested exact implementation candidate `a43c2e9408e51ec8812e9f6ec808a71401bc2841`.

| Gate | Run ID | Job ID | Result |
|---|---:|---:|---|
| core-headless clean install / lifecycle / A–F / compatibility | `35990125345` | `107601955259` | **SUCCESS** |
| world-kernel | `35990125344` | `107601955124` | **SUCCESS** |
| constitutional-cognition-closure + P16 harness regression | `35990125360` | `107601955110` | **SUCCESS** |
| full P16 `pytest -q` | `35990125343` | `107601954956` | **SUCCESS** |

The dedicated compatibility step also passed existing fused-turn-runtime, C09 Wake, P15 Periodic Review, Reality ingest, C14 cognitive derivation runtime, AI World, execution World, FIX-002 background-attempt recovery, FIX-003 turn recovery, and CognitiveRuntime coverage.

Full P16 exact-head log completed at `[100%]` with workflow/job conclusion **SUCCESS**.

## Operational error boundary

The CLI distinguishes at least:

- configuration failure;
- competing writer;
- recovery/reconciliation required;
- already-completed turn;
- turn-input conflict;
- storage failure;
- ordinary operation error.

It reports operational JSON only; it does not expose hidden model chain-of-thought. Logs and process metadata are not used as a reconstruction source of World truth.

## Known limitations / deferred scope

- This is a minimal synchronous headless CLI / bounded due-work runner, not a UI or long-running service supervisor.
- Provider-specific HTTP clients are not made constitutional here. Production adapters are supplied through the existing `ModelHandler` contract.
- The bundled deterministic handler is test-only and intentionally not a default production model.
- The CLI exposes recovery inspection but does not add replacement recovery semantics; FIX-002/FIX-003 continue to own recovery behavior.
- Cross-host distributed writer coordination is outside this minimal SQLite/single-host process boundary.
- No Resident fixture or Resident run was used.
- No public package/tag/release claim is made; P17 remains separate.
- `CORE-RECOVERY-001`, UI and hardware are not started by this engineering PR.

## Handoff

Engineering implementation is complete at the tested implementation candidate above.

**Author state: REVIEW_READY**

Required next action is independent acceptance of PR #181. This engineering branch does not self-accept or merge.
