# AIOS v3.0 P16 Multi-Model Independent Habitation Benchmark

> Status: parallel test-infrastructure foundation  
> Branch: `parallel/p16-habitation-harness-20260920`  
> Scope: benchmark infrastructure only; no Core runtime semantics are changed.

## 1. Definition

P16 here does **not** mean a group of AI agents cooperating inside one world.

It means:

> Different model candidates each enter their own isolated AIOS instance, live
> through the same synthetic life independently, and are evaluated afterward.

For example:

```text
same hidden life dataset
        │
        ├── GPT model    -> private AIOS world A
        ├── Claude model -> private AIOS world B
        ├── Gemini model -> private AIOS world C
        └── other model  -> private AIOS world D

No communication.
No shared WorldStore.
No shared memory.
No cooperation.
No answer exchange.

After all independent runs finish:
        ↓
compare long-term cognition / continuity / correction / action behavior
```

The purpose is to test **AIOS + resident-model compatibility and emergent behavior**,
not multi-agent collaboration.

## 2. Core question

P16 must answer a different question from normal unit tests:

> After independently living inside the same long-running synthetic life, how do
> different real models use AIOS to build, revise and apply a coherent world model?

It must not prove capability by supplying a known expected answer and checking a
string.

## 3. Hidden-life separation

Each benchmark scenario contains:

1. **Resident-visible life**: conversations, calendar entries, purchases, sensor
   events, outcomes and other facts that AIOS may legitimately receive.
2. **Hidden oracle**: latent truths and evaluation annotations that no resident
   model may receive.
3. **Post-run evaluator**: inspects a finished run and may compare it with the
   hidden oracle.

A scenario may be replayed identically to several model candidates, but every
candidate receives a **fresh isolated AIOS instance**.

## 4. Parallel-development boundary

This foundation intentionally does **not** modify:

- `src/aios_core/runtime/**`
- `src/aios_core/dimensions/**`
- Goal / Task / Action / Outcome contracts
- Scheduler
- WorldStore semantics
- project checkpoint or current-stage status

That makes it safe to build while P12 is being implemented.

Future P16 adapters may consume P12-P15 public APIs after those stages stabilize,
but this benchmark must not invent those APIs.

## 5. Benchmark topology

```text
                    sealed virtual life
                 ┌─────────┴─────────┐
                 │ resident events   │ hidden oracle
                 │                   │ evaluator only
                 ↓                   │
       ┌─────────┼─────────┬─────────┘
       ↓         ↓         ↓
    Model A    Model B    Model C
       │         │         │
       ↓         ↓         ↓
    AIOS A     AIOS B     AIOS C
  private DB  private DB  private DB
       │         │         │
       └─────────┼─────────┘
                 ↓
          post-run evaluation
                 ↓
       per-model findings + comparison
```

There is intentionally no Model A -> Model B channel.

## 6. Current harness contract

`tests/habitation/harness.py` provides:

- `LifeEvent`: one chronological synthetic-life event.
- `ResidentEvent`: the sanitized event delivered to one model.
- `HabitationScenario`: one sealed life reused across candidates.
- `HabitationTarget`: one isolated AIOS instance backed by one model.
- `HabitationRunner.run`: run one model independently.
- `HabitationRunner.run_models`: replay the same life across multiple independent
  model/AIOS pairs.
- `MultiModelHabitationResult`: holds independent per-model runs.
- `HabitationEvaluator`: post-run evaluator protocol.
- `evaluate_run`: evaluation boundary invoked only after one run completes.

The runner rejects reuse of the same target instance for two model IDs, preventing
accidental shared state.

## 7. What the full P16 Gate should compare

With real models and hidden lives spanning days, weeks or months, compare:

- cross-session factual continuity;
- relevant-memory recovery without context flooding;
- raw fact vs summary vs cognition separation;
- ability to remain uncertain when evidence is insufficient;
- correction after contradictory evidence;
- propagation of revised cognition;
- long-term user and relationship understanding;
- useful dynamic-dimension creation without dimension spam;
- Goal/Task/Action behavior after P12;
- outcome-based strategy/calibration changes after P12/P15;
- robustness to irrelevant/noisy/misleading events;
- continuity after replacing one resident model with another on a copied world.

The comparison may use deterministic invariants, model judges and human review.
No fixed expected-response string may serve as the cognition Gate.

## 8. Example hidden life

```text
Week 1: user repeatedly asks for guided help
Week 2: user schedules independent practice
Week 3: user solves harder tasks with less assistance
Week 5: one noisy failure occurs

Hidden evaluator oracle:
  learning independence is generally improving, with normal variance
```

GPT, Claude, Gemini, or any other candidate receive only the visible events.
None receives the hidden sentence above.

## 9. Parallel foundation now implemented

The isolated P16 foundation currently includes:

1. reusable hidden-life event contract;
2. JSON and JSONL scenario/event loaders;
3. scenario version + deterministic seed;
4. public visible-life SHA-256 fingerprint;
5. per-model run artifact serialization;
6. evaluator finding/report schema;
7. cross-model comparison matrix with no built-in winner or aggregate score;
8. fresh-target factory path that creates one isolated AIOS target/world per model;
9. physically separate resident event streams and evaluator-only oracle fixtures;
10. CI checks that guard oracle non-leakage and shared-target rejection.

Example fixture layout:

```text
tests/habitation/fixtures/
├── learning_independence_v1.manifest.json
├── resident/
│   └── learning_independence_v1.jsonl   <- delivered to each model
└── oracle/
    └── learning_independence_v1.json    <- evaluator only
```



## 10. Initial hidden-life scenario catalog

The foundation now ships with four resident/oracle-separated scenario families:

| Scenario | What the resident model experiences | Evaluator focus |
|---|---|---|
| `learning-independence-v1` | learning behavior evolves across weeks with one setback | longitudinal pattern, useful dimension discovery, noise resilience |
| `cross-session-continuity-v1` | later conversation uses a vague reference to an earlier trip | cross-session continuity, relevant recall, context restraint |
| `cognition-revision-v1` | an old routine is explicitly changed by later evidence | forward revision, historical preservation, stale suppression |
| `uncertainty-restraint-v1` | sparse ambiguous behavior could tempt over-generalization | epistemic restraint, uncertainty preservation |

These fixtures do not contain expected model response strings. The resident stream
contains only life events. Evaluator truth lives in separate oracle files.

## 11. Deliberately deferred until Core APIs stabilize

Do not wire these into the benchmark yet:

- P12 Goal / Task / Action / Outcome internals;
- Scheduler implementation details;
- P13 device/data adapters;
- P15 periodic review implementation;
- real provider-specific model adapters and credentials.

Those integrations should consume stabilized public interfaces later rather than
forcing P12-P15 to conform to an early test harness.
