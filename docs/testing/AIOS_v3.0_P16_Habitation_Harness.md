# AIOS v3.0 P16 Multi-Agent Habitation Harness

> Status: parallel infrastructure foundation  
> Branch: `parallel/p16-habitation-harness-20260920`  
> Scope: test infrastructure only; no Core runtime semantics are changed.

## 1. Purpose

P16 must answer a different question from ordinary unit/integration tests:

> After living inside a long-running synthetic life, does a real resident model
> actually build, revise and use a coherent world over time?

It must not prove capability by giving the model a known expected answer and then
checking a string.

The harness therefore separates three things:

1. **Resident-visible life**: conversations, calendar entries, purchases, sensor
   events, outcomes and other facts that the AIOS instance may legitimately see.
2. **Hidden oracle**: latent truths and evaluation annotations that the resident
   model must never receive.
3. **Evaluator**: a post-run judge that may compare the world/run against the
   hidden oracle.

## 2. Parallel-development boundary

This foundation intentionally does **not** modify:

- `src/aios_core/runtime/**`
- `src/aios_core/dimensions/**`
- Goal / Task / Action / Outcome contracts
- Scheduler
- WorldStore semantics
- project checkpoint or current-stage status

That makes it safe to build while P12 is being implemented.

Future P16 adapters may consume P12-P15 public APIs after those stages stabilize,
but the harness must not define those APIs for them.

## 3. Test topology

```text
Hidden-life scenario
├─ resident-visible events
│  ├─ conversation
│  ├─ calendar
│  ├─ transaction
│  ├─ sensor
│  ├─ app/device event
│  └─ later outcome
└─ hidden oracle
   ├─ latent user change
   ├─ causal truth used only for evaluation
   ├─ important facts the model should eventually discover
   └─ traps / ambiguous evidence

                       same sealed life
                            │
             ┌──────────────┼──────────────┐
             ↓              ↓              ↓
         Resident A     Resident B     Resident C
         real model     real model     real model
             │              │              │
             └──── independent AIOS worlds ┘
                            │
                            ↓
                    post-run evaluators
                            │
                            ↓
                findings / metrics / failures
```

No resident receives the hidden oracle.

## 4. Current harness contract

`tests/habitation/harness.py` provides:

- `LifeEvent`: one chronological synthetic-life event.
- `ResidentEvent`: the sanitized view delivered to the system under test.
- `HabitationScenario`: a sealed ordered life with scenario-level hidden truth.
- `HabitationTarget`: adapter protocol for a resident AIOS instance.
- `HabitationRunner.run`: execute one resident against one life.
- `HabitationRunner.run_many`: execute several independent residents against the
  same life.
- `HabitationEvaluator`: post-run evaluator protocol.
- `evaluate_run`: evaluation boundary that runs only after habitation.

The runner validates deterministic mechanics only: timeline order, identity,
resident isolation and oracle separation.

It does **not** decide whether the AI's interpretation was semantically correct.

## 5. What a real P16 Gate must eventually measure

The full P16 Gate should use real resident models and hidden lives spanning days,
weeks or months. Candidate measurements include:

- cross-session factual continuity;
- recovery of relevant history without flooding every turn;
- distinction between raw fact, summary and cognition;
- willingness to leave uncertain states unresolved;
- correction after contradictory evidence;
- propagation of revised cognition;
- long-term user/relationship understanding;
- useful dynamic-dimension creation without dimension spam;
- Goal/Task/Action behavior after P12;
- outcome-based strategy/calibration changes after P12/P15;
- robustness when irrelevant or misleading events are injected;
- model replacement continuity: a new model should inherit the world without
  receiving an answer key.

These measurements may use model judges, human review and deterministic invariants,
but no single fixed keyword/expected-response string may constitute the cognition
Gate.

## 6. Scenario authoring rule

A scenario author may know the latent truth. The resident may not.

Example:

```text
Week 1: user repeatedly asks for guided help
Week 2: user schedules independent practice
Week 3: user solves harder tasks with less assistance
Week 5: one noisy failure occurs

Hidden oracle:
  learning independence is generally improving, with normal variance
```

The hidden statement above is for the evaluator. It must never appear in
resident-visible event metadata, prompts or context.

## 7. Next isolated steps

Still safe to do in parallel with Core work:

1. add reusable hidden-life scenario fixtures;
2. add event-stream loaders (JSONL/YAML -> `LifeEvent`);
3. add run artifact serialization;
4. add evaluator result schema;
5. add sharding/reproducibility metadata.

Wait for stable P12-P15 public APIs before writing adapters that call Goal/Task,
Scheduler, periodic review or external-action capabilities.
