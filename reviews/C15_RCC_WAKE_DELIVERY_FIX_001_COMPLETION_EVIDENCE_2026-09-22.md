# C15-RCC-WAKE-DELIVERY-FIX-001 Completion Evidence — 2026-09-22

> Task: `C15-RCC-WAKE-DELIVERY-FIX-001`
>
> Role: AIOS Core Engineer / Wake / Conversation Persistence Engineer
>
> Scope: persist real user-delivered non-conversation Wake assistant output as durable User-AI interaction World fact; no Resident rerun, no historical backfill, no PR #101 mutation.

## 1. Starting main

- Starting live `main`: `ff47e82f586a47a3d9bb28b83545b8b9044e7ed3`.
- Governance at start:
  - `C15-RCC-WAKE-DELIVERY-FIX-001 = READY`
  - `C15-RCC-RES-A-001 = BLOCKED`
  - `C15-RCC-RES-B-001 = BLOCKED`
  - `C15-RCC-RES-A-REPAIR-DECISION-001 = BLOCKED`
- PR #101 remained OPEN / UNMERGED / PINNED at exact head `bfbfa059e2ac616326eecdfe3ffa7a927bdc7ce2`.

## 2. Pre-fix reproduction

A test-only reproduction was committed first, before any Core code change:

- reproduction commit: `2c0dfc10b92b6122ce08754407393ef87a3ea073`
- file: `tests/integration/test_v3_attention_watch.py`
- case: interrupt `WATCH_MATCH` Wake, Step0 delivery allowed, non-empty Resident response.

The reproduction asserted and observed:

- `delivery_response` was non-empty;
- the Wake was a legal user-facing delivery;
- durable assistant `dim:user_ai_interaction` Observation delta was **0**.

The test-only reproduction commit passed the then-current full Core/P16 convergence workflow:

- `p16-convergence-gate` run **35714790836** — SUCCESS.

This establishes the defect independently of the later implementation.

## 3. Root cause

Ordinary `FusedTurnRuntime.run_turn()` already persisted assistant output via:

`ConversationIngestor.commit_assistant_output(...)`

but `FusedTurnRuntime.run_wake()` only:

- ran the Resident;
- computed `delivery_allowed`;
- completed/requeued the Wake;
- returned `WakeDispatchRunResult.delivery_response`.

There was no assistant interaction persistence path for a real proactive delivery.

Therefore a response could be user-delivered while existing only as a runtime return/artifact, not as durable User-AI interaction World history.

## 4. Exact Core changes

### `src/aios_core/ingest/conversation.py`

Added the minimal assistant-only API:

`ConversationIngestor.commit_assistant_delivery(...)`

It:

- persists only an assistant Observation;
- uses the existing `SQLiteWorldStore`;
- writes to `dim:user_ai_interaction`;
- uses `source_kind=user_ai_interaction`;
- uses `SourceClass.AI_COGNITION`;
- never creates a USER Observation;
- requires an exact pinned Wake ref;
- validates the Wake exists and belongs to the same subject.

### `src/aios_core/runtime/turn_runtime.py`

`run_wake()` now persists a delivery interaction only when:

- the runtime is not being requeued as incomplete;
- `delivery_allowed == true`;
- `runtime_result.response is not None`.

The write happens after the delivery gate has selected the response and before Wake completion.

`WakeDispatchRunResult` now exposes:

`delivery_observation_ref: ObjectRef | None`

so audit/test/evaluator code can mechanically follow:

Wake → delivered response → durable assistant interaction Observation.

No conversation-session or turn index is fabricated.

## 5. Assistant-only interaction persistence API

`commit_assistant_delivery` stores:

- exact delivered assistant text;
- `role=assistant`;
- subject id;
- `dimension=dim:user_ai_interaction`;
- `source_kind=user_ai_interaction`;
- delivered/occurred time;
- `interaction_kind=wake_delivery`;
- `delivery_provenance=wake_user_delivery`;
- exact `origin_wake_ref`;
- `origin_wake_id`;
- `origin_wake_revision`;
- deterministic `delivery_key`.

The raw locator is Wake-specific, not a fabricated conversation turn locator.

## 6. Stable delivery identity

The assistant Observation id is deterministic from the **logical Wake delivery identity**:

- subject id;
- originating Wake object id;
- constant delivery class `wake_user_delivery`.

The exact RUNNING Wake revision used by the first delivery execution is **not** part of the Observation identity; it is retained immutably in provenance as `origin_wake_ref` / `origin_wake_revision`.

This distinction is deliberate: the same logical Wake can remain RUNNING across process recovery or budget-window transitions without becoming a second user delivery.

Format:

`obs_wake_ai_<stable digest>`

The operation id is deterministic from the same logical delivery key:

`op_wake_ai_<stable digest>`

No random UUID participates in delivery identity.

## 7. Exact idempotency rule

The store idempotency key is deterministic:

`wake-assistant-delivery:<subject>:<wake-id>`

Exact replay with the same text/time/provenance:

- returns `idempotent_replay=true`;
- keeps the same Observation id;
- does not advance World revision.

Reusing the same delivery identity with changed text changes the request fingerprint and fails closed with the existing idempotency-conflict path rather than overwriting or duplicating the delivery.

## 8. Delivery truth boundary

A durable assistant interaction write occurs only after the runtime has a real response selected for user delivery.

Zero interaction writes are preserved for:

- background Wake response suppressed by Step0;
- user/channel delivery denial;
- Resident silence;
- C14 cognitive derivation internal response;
- periodic-review internal response path;
- runtime-incomplete/requeued C14 work.

The existing `delivery_response`/suppression semantics remain intact.

## 9. Restart-safe ordering / exactly-once recovery

The delivery interaction is persisted **before** Wake completion.

This removes the unsafe ordering:

completed Wake → crash → permanently missing interaction fact.

If a crash occurs after the delivery fact commit but before Wake completion:

- the Wake remains RUNNING;
- a fresh runtime first detects the already-durable delivery by logical Wake id;
- the Resident model/provider is **not invoked again**;
- the stored exact delivery text, first exact Wake provenance, Step0 and mechanical runtime-completion metadata are validated and reused to finish the Wake;
- only Wake completion advances the World on recovery.

A targeted test injects a simulated failure at Wake completion, reopens the SQLite World with a fresh runtime whose model handler would fail if called, and verifies final convergence to:

- exactly 1 completed Wake;
- exactly 1 delivered assistant interaction Observation;
- zero model replay during recovery;
- fail-closed validation of stored delivery key / exact Wake ref / subject / Step0 delivery grant;
- no duplicate World write.

A second replay after the Wake is already completed is also a no-write idempotent return. Direct persistence retry with changed text under the same logical delivery identity fails closed.

## 10. No-synthetic-USER proof

Delivered proactive Wake tests explicitly count User-AI interaction Observations before/after.

Result:

- assistant interaction count increases by exactly 1;
- `role=user` interaction count is unchanged;
- there is no empty USER message;
- there is no synthetic `System Wake` USER Observation;
- there is no fabricated user/assistant pair.

## 11. Fresh-runtime retrieval proof

After a delivered interrupt Wake:

1. the original runtime is no longer used;
2. the same SQLite World is reopened;
3. a new `WorldSearchIndex` is rebuilt;
4. a fresh `FusedTurnRuntime` is created;
5. normal indexed recall finds the proactive assistant Observation by its text.

This proves the delivery is durable World history, not only `WakeDispatchRunResult` data.

## 12. Wake provenance proof

The durable assistant Observation metadata mechanically identifies the exact originating Wake:

- exact object id;
- exact revision;
- full `origin_wake_ref`.

The test verifies the stored exact ref matches the RUNNING Wake revision used for that Resident execution.

## 13. Suppressed / denied / internal / silence tests

Added/strengthened regressions verify:

- background response + suppressed delivery → 0 interaction write;
- interrupt + `user_delivery_allowed=false` → 0 interaction write;
- interrupt + silence → 0 interaction write;
- C14 cognitive-derivation internal response → 0 interaction write;
- all these results expose `delivery_observation_ref=None`.

## 14. Ordinary `run_turn()` non-regression

No existing `commit_user_input`, `commit_assistant_output`, turn identity, session identity, canonical USER ingest, or ordinary conversation write path was rewritten.

Relevant workflows on the Core candidate are GREEN:

- `fused-turn-runtime` run **35716484136** — SUCCESS.
- `conversation-world` run **35716484085** — SUCCESS.
- `p14-long-context` run **35716484194** — SUCCESS.

Ordinary USER turn semantics remain USER Observation + assistant Observation with existing canonical identities.

## 15. Assistant dialogue / T28 / anti-self-proof

The new delivery Observation intentionally uses the same interaction dimension and `role=assistant` classification as ordinary assistant dialogue.

Current proactive recommendation filtering identifies dialogue by interaction dimension/source kind and excludes `role=assistant`, independent of `created_by` or raw locator.

Relevant T28/continuity jobs are GREEN on the candidate:

- C14 loop workflow `p15-c13-p14-t28` job in run **35716484077** — SUCCESS.
- C14 runtime workflow `p15-c13-p14-t28` job in run **35716484000** — SUCCESS.

The new output is searchable interaction history but is not promoted as independent user/world fact.

## 16. Targeted Gate results

Core implementation candidate:

`5ad62fbfe341cf0d7cfd9c3f0129b1c6522372bb`

Targeted / relevant workflow results:

- `fused-turn-runtime` **35716484136** — SUCCESS.
- `conversation-world` **35716484085** — SUCCESS.
- `c09-wake-dispatch` **35716484146** — SUCCESS.
- `p15-periodic-review` **35716484113** — SUCCESS.
- `p10-ai-world-gate` **35716484140** — SUCCESS.
- `p11-dimension-gate` **35716484172** — SUCCESS.
- `p12-execution-gate` **35716484121** — SUCCESS.
- `p13-ingest-gate` **35716484094** — SUCCESS.
- `p13-reality-ingest` **35716484006** — SUCCESS.
- `p14-long-context` **35716484194** — SUCCESS.
- `p9-revision-gate` **35716484071** — SUCCESS.
- `constitutional-cognition-closure` **35716484100** — SUCCESS.
- C14 loop `c14-loop-targeted`, `runtime-wake-attention-budget`, `p15-c13-p14-t28`, `p16-habitation-harness` jobs in run **35716484077** — SUCCESS.
- C14 runtime `c14-runtime-targeted`, `runtime-wake-turn`, `p15-c13-p14-t28`, `p16-habitation-harness` jobs in run **35716484000** — SUCCESS.

## 17. Full Core / P16 regression

- standalone `p16-convergence-gate` run **35716484139** — **SUCCESS** on validation head `e60cdb5d131ea34f42084bc6799737c1fb952104`; Core bytes are identical to exact implementation candidate `5ad62fbfe341cf0d7cfd9c3f0129b1c6522372bb`.

Test counts are intentionally not copied from historical prompts; the workflow's current suite is authoritative.

## 18. Changed files at exact Core candidate

Core:

- `src/aios_core/ingest/conversation.py`
- `src/aios_core/runtime/turn_runtime.py`

Tests:

- `tests/integration/test_v3_attention_watch.py`
- `tests/integration/test_v3_c14_cognitive_derivation_runtime.py`

No fixture, constitution, RCC ruling, Resident evidence, PR #101 artifact, or historical private World was modified.

## 19. PR / gated candidate

- PR: **#104**
- branch: `core/c15-rcc-wake-delivery-fix-20260922`
- exact Core implementation candidate: `5ad62fbfe341cf0d7cfd9c3f0129b1c6522372bb`
- full validation head (Core-identical; evidence-only follow-up): `e60cdb5d131ea34f42084bc6799737c1fb952104`
- pre-fix reproduction commit: `2c0dfc10b92b6122ce08754407393ef87a3ea073`

The governance/evidence writeback that follows this report does not alter the Core implementation.

## 20. Handoff

With the Core fix and required Gates GREEN:

- `C15-RCC-WAKE-DELIVERY-FIX-001` may advance to DONE.
- `C15-RCC-RES-A-REPAIR-DECISION-001` may advance to READY.
- `C15-RCC-RES-A-001` remains BLOCKED.
- `C15-RCC-RES-B-001` remains BLOCKED.
- `C15-RCC-RES-C-001` remains BLOCKED.
- `C15-RCC-EVAL-001` remains BLOCKED.

The next window is an independent PM repair decision. This Core window does not choose historical mechanical repair vs fresh Resident A rerun.
