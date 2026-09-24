# CORE-HEADLESS-001

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Role:
Runtime Integration Engineer / Headless Core Engineer

You are not:
- AIOS total PM
- Resident A / B / C
- Semantic Evaluator
- UI engineer
- hardware engineer
- a new architecture designer

Your only task:

> Turn the currently integrated AIOS 3.0 Core into a minimal installable/runnable/restartable headless Core entrypoint without creating a second runtime, second World, or UI layer.

## Required start

1. Fetch current live `main`; do not treat any SHA in this prompt as permanent.
2. Read:
   - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
   - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
   - `PROJECT_MASTER_MAP.md`
   - `governance/AIOS_CORE_COMPLETION_PLAN_2026-09-24.md`
   - `governance/CORE_GAP_FIX_001_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_GAP_FIX_002_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_GAP_FIX_003_INTEGRATION_RECEIPT_2026-09-24.md`
   - `docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md`
3. Confirm:
   `CORE-HEADLESS-001 = READY`.
4. Inventory existing runnable/operator/model-adapter/ingest/runtime entrypoints before writing code.
5. Reuse existing Core mechanisms. Do not design a replacement runtime.

## Required architecture boundary

The headless entrypoint must drive the existing:
- SQLite World / current WorldStore path;
- FusedTurnRuntime / CognitiveRuntime;
- existing user-turn ingestion;
- existing external-fact ingestion surfaces where already available;
- Wake / Periodic Review / due-work mechanisms;
- Metering / Budget / attempt recovery;
- current Search / Context / Summary / Claim / Goal / Task / Action / Outcome mechanisms.

Do not create:
- a second World database;
- a second cognition runtime;
- a second attempt/recovery ledger;
- a second truth store;
- fixed cognition/personality rules;
- web/App UI;
- Launcher/digital-human/device code.

## Functional deliverable

Produce the smallest headless interface needed to prove Core operation.

It may be a CLI, long-running service entrypoint, or a minimal combination, but it must support at least:

1. explicit configuration of persistent World path and runtime/model adapter;
2. start/open existing World;
3. submit a normal user turn through the existing runtime;
4. ingest supported external facts through existing ingest APIs rather than directly mutating cognition;
5. process due background work using existing Wake/Review scheduling semantics;
6. expose minimal operational health/status useful for debugging without exposing hidden model chain-of-thought;
7. graceful stop/close;
8. restart against the same World and continue correctly.

Do not use sealed/future C15 Resident fixture data to prove this task.

## Lifecycle and single-writer requirements

Independently define and test the mechanical process boundary:

- one configured writable Core process must not silently permit a competing writer that corrupts the same World;
- startup failure must be explicit and non-destructive;
- shutdown must close/flush durable state correctly;
- restart must not clear execution ledgers or fabricate completion;
- already-IN_DOUBT work must remain governed by FIX-002/FIX-003 rules;
- pending/due work must remain discoverable after restart;
- clock/time handling must reuse existing semantics rather than inventing a second time source;
- fatal vs recoverable errors must be distinguishable in logs/exit behavior;
- logs must not become a second source of World truth.

If a repository-level lock or equivalent already exists, reuse it. If not, implement only the minimal safe single-writer mechanism required by the current storage architecture.

## Model boundary

Use the existing model/provider abstraction.

Requirements:
- no hard-coded provider as constitutional dependency;
- missing model credentials/config fail clearly;
- test adapter/fake model may be used for mechanical tests;
- at least one documented normal adapter path must be usable by the headless entrypoint;
- provider execution must still flow through accepted attempt/recovery/metering semantics.

Do not run a Resident experiment in this task.

## Required restart scenarios

At minimum test:

A. clean start -> user turn -> durable output -> stop -> restart -> history/world continuity preserved;

B. process stops with pending due work -> restart -> due work remains processable under existing scheduling semantics;

C. user-turn pre-admission/retry state from FIX-003 survives restart without blind provider reinvocation;

D. background IN_DOUBT state from FIX-002 survives restart without blind provider reinvocation;

E. historical temporal read-cut behavior from FIX-001 remains intact in resumed background execution;

F. repeated start/stop does not duplicate user turns, Wake/Review work, metering, or assistant output.

## Installation / clean-run proof

Provide a reproducible headless smoke path from a clean checkout/environment on Python >=3.12:

- install dependencies using the repository-supported method;
- initialize/open a disposable private test World;
- run a deterministic mechanical smoke;
- stop;
- restart;
- prove the same World is resumed;
- exit cleanly.

Do not claim public packaging/tag/release completion; that belongs to P17.

## Tests and Gates

Add only the tests needed for the headless integration surface.

At minimum run:
- dedicated headless lifecycle/start-stop-restart tests;
- existing fused-turn-runtime;
- C09 Wake;
- P15 Periodic Review;
- C14 runtime/loop where affected;
- P10/P12 as affected;
- full P16 `pytest -q`.

If a new workflow is necessary, keep it mechanical and branch-shape safe under the already accepted CI fix. Do not add a workflow merely to manufacture a green badge.

## Evidence

Create:
`reviews/CORE_HEADLESS_001_COMPLETION_EVIDENCE_2026-09-24.md`

It must pin:
- construction live main;
- exact candidate head;
- inventory of reused existing entrypoints;
- exact files changed;
- architecture boundary;
- install/run command;
- start/stop/restart evidence;
- single-writer evidence;
- pending/IN_DOUBT restart evidence;
- targeted run/job IDs;
- full regression evidence;
- known limitations.

## Handoff

Create one engineering PR for `CORE-HEADLESS-001`.

At completion:
- set author state REVIEW_READY;
- do not self-accept;
- do not merge;
- do not update task board/checkpoint from the engineering branch;
- do not start CORE-RECOVERY-001;
- do not run Resident;
- do not build UI/hardware.

Stop after handoff for independent acceptance.
