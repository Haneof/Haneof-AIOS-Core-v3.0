# CORE-HEADLESS-001 INDEPENDENT ACCEPTANCE

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Role:
Independent Headless Core / Runtime Integration Acceptance Reviewer

Candidate:
- PR #181 — `CORE-HEADLESS-001: installable persistent headless Core entrypoint`
- tested implementation exact head: `a43c2e9408e51ec8812e9f6ec808a71401bc2841`
- evidence-only handoff head: `12928af4ffa40e70d9ae80124dab388a486f7097`

The evidence-only head is one commit above the tested implementation head and must contain only:
`reviews/CORE_HEADLESS_001_COMPLETION_EVIDENCE_2026-09-24.md`.

Your task is to independently decide whether CORE-HEADLESS-001 is complete, minimal, restart-safe, and compatible with the already integrated Core semantics.

You are not:
- PR #181 author
- CORE-HEADLESS-001 engineer
- AIOS total PM
- Resident A/B/C
- Semantic Evaluator
- UI engineer
- hardware engineer

This window:
- acceptance only
- no candidate repair
- no merge
- no Resident
- no CORE-RECOVERY-001
- no UI/hardware

## Start

1. Fetch live `main`.
2. Read:
   - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
   - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
   - `PROJECT_MASTER_MAP.md`
   - `governance/AIOS_CORE_COMPLETION_PLAN_2026-09-24.md`
   - `governance/prompts/CORE_HEADLESS_001_2026-09-24.md`
   - `governance/CORE_GAP_FIX_001_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_GAP_FIX_002_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_GAP_FIX_003_INTEGRATION_RECEIPT_2026-09-24.md`
   - `reviews/CORE_HEADLESS_001_COMPLETION_EVIDENCE_2026-09-24.md`
   - PR #181 current body/diff.
3. Confirm `CORE-HEADLESS-001 = GATE / REVIEW_READY`.
4. Pin PR #181 and both heads above. If implementation head or evidence-only delta differs, do not inherit this evidence.

## Candidate structure

Independently verify:
- PR #181 construction base was `8d724f96aa286549e4e12a2245d28ff5dce6f77b`;
- implementation candidate changes exactly seven implementation files:
  - `.github/workflows/core-headless.yml`
  - `pyproject.toml`
  - `src/aios_core/headless/__init__.py`
  - `src/aios_core/headless/cli.py`
  - `src/aios_core/headless/core.py`
  - `src/aios_core/headless/testing.py`
  - `tests/integration/test_core_headless.py`
- handoff head adds only the one completion-evidence file;
- no `src/aios_core/runtime/**` implementation is rewritten by HEADLESS;
- no second World, runtime, scheduler, recovery ledger, cognition truth store, or model contract is introduced.

## Architecture acceptance

The headless layer must remain only a lifecycle/configuration shell around existing Core.

Verify it reuses:
- `SQLiteWorldStore`;
- `WorldSearchIndex`;
- `FusedTurnRuntime / CognitiveRuntime`;
- normal user-turn path;
- `RealityIngestService`;
- Wake / Periodic Review;
- FIX-002 background attempt ledger;
- FIX-003 turn-execution recovery;
- existing metering/budget;
- existing `ModelHandler = RuntimeSnapshot -> ModelDirective` abstraction.

Fail if the headless wrapper creates a parallel semantic runtime or bypasses accepted execution/recovery paths.

## Installation / packaging

Independently inspect `pyproject.toml` and installed CLI behavior.

Verify:
- Python >=3.12 remains the repository contract;
- `aios-core-headless` console entrypoint installs normally;
- clean wheel/install path works;
- deterministic model handler is test-only and not an implicit production default;
- production model adapter remains provider-neutral through existing `ModelHandler`;
- missing required configuration fails clearly rather than silently constructing a fake/default model.

## Persistent World / index

Verify:
- configured World path is the canonical durable World;
- restart opens the same World;
- World revision does not reset;
- search index remains a rebuildable projection, not truth;
- index catch-up after reopen is correct;
- headless status does not become a second state database.

## Single-writer lifecycle

Review the writer lease critically.

Required:
- concurrent writable open on the same World fails closed;
- failed competing startup does not mutate/reset the World;
- clean stop releases the lease;
- restart after clean stop succeeds;
- lock metadata is not used as World truth;
- a stale lock-file pathname alone must not permanently brick the World if the OS lease is no longer held;
- process lifetime owns the actual exclusion primitive.

If the implementation depends only on lock-file contents instead of the OS lease, FAIL.

## Required restart matrix A–F

Freshly verify each scenario:

A. clean start -> normal user turn -> durable assistant output -> stop -> restart same World;

B. durable pending Wake -> stop before execution -> restart -> Wake remains due/processable -> completion is not redispatched after another restart;

C. FIX-003 pre-admission state -> restart -> no blind provider call -> explicit recovery authorization -> provider executes once;

D. FIX-002 background IN_DOUBT -> restart -> remains IN_DOUBT -> no blind reinvocation;

E. FIX-001 historical temporal cut -> resumed background execution after restart must not see late-known data;

F. repeated start/stop does not duplicate:
- user turn
- assistant output
- Wake/Review completion
- metering row.

Do not accept only high-level evidence prose; inspect tests and relevant runtime call paths.

## Operational surface

Verify the CLI/status output:
- exposes operational state only;
- does not expose hidden chain-of-thought;
- distinguishes configuration error, writer-busy, recovery-required, already-completed, input-conflict, storage failure, ordinary operation failure;
- exits non-zero for real operational failure where appropriate;
- logs/status are not used to reconstruct World truth.

## Due-work semantics

Headless due-work processing must use existing Wake/Periodic Review mechanics.

Verify:
- bounded processing cannot silently skip durable due work;
- completed work is not re-executed;
- current/pending/IN_DOUBT semantics come from existing stores;
- headless does not invent a parallel queue;
- clock handling uses existing Core time semantics.

## Exact-head evidence

All following runs must be independently re-read and tied to implementation exact head
`a43c2e9408e51ec8812e9f6ec808a71401bc2841`:

- core-headless: run `35990125345`, job `107601955259`
- world-kernel: run `35990125344`, job `107601955124`
- constitutional-cognition-closure: run `35990125360`, job `107601955110`
- full P16: run `35990125343`, job `107601954956`

PM pre-check observed:
- CPython 3.12.14
- pytest 8.4.2
- pydantic 2.13.5
- direct `pytest -q`
- 100%
- 668 pass markers
- workflow SUCCESS.

Headless job PM pre-check observed:
- clean non-editable install `pip install ".[dev]"`;
- installed `aios-core-headless` command;
- first status world_revision=0;
- normal installed CLI turn returned `HEADLESS_MECHANICAL_OK`;
- reopened status world_revision=2 / index_watermark=2 / index_lag=0;
- dedicated headless tests: 6/6;
- compatibility suite reached 100%.

Re-read raw logs yourself.

## Independent adversarial probes

Perform at least three focused probes, without modifying PR #181.

At minimum include:

### Probe 1 — stale lease artifact
Create/open/close a World, leave or recreate stale lock-file contents without an active OS lock, then confirm a new process can still acquire the writer lease safely.

### Probe 2 — competing writer
Hold writer A; attempt writer B; confirm B fails closed without World mutation; stop A; confirm B can then open the same World.

### Probe 3 — recovery state survives wrapper restart
Use either:
- FIX-003 pre-admission state, or
- FIX-002 background IN_DOUBT,
restart through the headless wrapper, and prove no blind provider reinvocation.

Strongly recommended fourth probe:
- run installed CLI against same World across separate processes and verify world_revision/index watermark/turn identity continuity.

If using an evidence-only probe PR, keep it closed/unmerged after capturing CI.

## Live-main drift

If main advanced after construction:
- governance/review-only drift does not automatically invalidate candidate;
- any semantic `src/**`, packaging contract, test-contract, or workflow change relevant to HEADLESS requires explicit compatibility review and possibly revalidation.

## Verdict

ACCEPTANCE_PASS only if:
- architecture remains single-runtime / single-World;
- installable CLI is real;
- writer exclusion is mechanically safe;
- A–F restart matrix holds;
- FIX-001/002/003 semantics are preserved;
- no duplication/recovery regression exists;
- provider-neutral model boundary holds;
- exact-head four Gate set passes;
- full P16 passes;
- independent adversarial probes pass;
- live-main drift does not invalidate the candidate;
- blockers = 0.

ACCEPTANCE_FAIL for any real blocker.

REBASE_REVALIDATION_REQUIRED only for a new semantic main change that materially invalidates the reviewed candidate.

## Report

Create a new review-only report:
`reviews/CORE_HEADLESS_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

Create one review-only PR from review-time main.

Report:
- review-time main
- PR #181
- tested implementation exact head
- evidence-only head
- candidate scope
- architecture verdict
- install/CLI verdict
- writer lease verdict
- A–F restart verdict
- FIX-001/002/003 compatibility
- independent probes
- exact-head CI
- P16 result
- live-main drift
- blocker count
- final verdict

Do not merge PR #181.

If PASS, state:
`PR #181 CORE-HEADLESS-001 implementation exact head a43c2e9408e51ec8812e9f6ec808a71401bc2841 with evidence-only handoff 12928af4ffa40e70d9ae80124dab388a486f7097 is independently accepted for PM integration.`
