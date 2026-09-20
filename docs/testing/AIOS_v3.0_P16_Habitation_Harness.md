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

That keeps this foundation safe to develop and review in parallel with Core work.
It must consume stabilized public Core APIs later rather than defining Core semantics from the test side.

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
9. mandatory per-target `isolation_key` for private world/store identity;
10. virtual-clock `advance_to()` before every resident-visible event;
11. evaluator-only `audit_snapshot()` after each completed life;
12. physically separate resident event streams and evaluator-only oracle fixtures;
13. CI checks that guard oracle non-leakage, future-information leakage, mutation isolation, and shared-world rejection.

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

## 11. Core integration boundary

The benchmark consumes stabilized public Core interfaces for execution, reality
ingestion, long-session continuity, periodic review and Wake dispatch. It still must
not redefine Core semantics from the test side.

Provider adapters remain external to cognition logic: they translate one resident
model API into the existing `ModelHandler` / round-summary surfaces only.


## 12. Anti-contamination execution rules

The benchmark fixture repository may contain evaluator-only semantic labels and
oracle files, but a real resident model run must not receive them indirectly.

Required runtime isolation:

- do not mount `tests/habitation/fixtures/oracle/**` into a model-accessible
  filesystem/tool sandbox;
- do not include semantic scenario IDs, fixture filenames, manifest `purpose`,
  catalog `focus`, or evaluator criteria in model prompts/context;
- model-side target factories receive only `ResidentScenarioDescriptor`, which
  currently contains only the opaque synthetic `subject_id`; it exposes no scenario
  label, oracle, seed, future event count, future time range, or future channels;
- every model target must expose a unique `isolation_key` representing its
  private AIOS world/store;
- the resident event payload and metadata are deep-copied for each delivery so one
  model cannot mutate the life stream seen by another model.

Evaluator labels and oracle content may be loaded only after or outside the
resident execution boundary.


## 13. Long-horizon execution contract

A resident target is not just a chat callback. To test AIOS over simulated days or
months it must implement three independent surfaces:

1. `advance_to(instant)`: advance that target's private virtual clock and process
   deterministic work due up to the next visible life event.
2. `handle_event(event)`: ingest exactly one resident-visible event after the
   clock reaches that event's timestamp.
3. `audit_snapshot()`: after the life finishes, expose an evaluator-only snapshot
   of the resulting AIOS world/state.

The runner deep-copies resident payloads, metadata, clock results, model responses,
and the final audit snapshot. One model therefore cannot mutate the scenario or
artifacts later consumed by another model.

Hidden evaluator-only events are absent from the resident run entirely: their IDs,
timestamps and channels are not emitted in `HabitationRun` or its serialized
artifact.

## 14. Current-Core adapter

After P12-P15 and C09 stabilized on `main`, P16 now includes a thin adapter:

`tests/habitation/current_core.py`

It does **not** implement cognition. It creates a private `SQLiteWorldStore`,
`WorldSearchIndex`, `RealityIngestService` and the real `FusedTurnRuntime` for one
model candidate, then feeds resident-visible events through those existing public
Core surfaces.

Important boundaries:

- conversation events go through the real fused turn loop;
- non-conversation events go through P13 reality ingest;
- virtual-clock advancement processes P12 due tasks, C09 pending Wakes and P15
  periodic review;
- the current utterance itself is used as the topic-gate seed, never evaluator labels;
- hidden oracle data is never accepted by the target constructor;
- evaluator snapshots are read only after the life run;
- deterministic contract tests use a silent stub **only to verify plumbing and
  isolation**. They are not evidence that AI cognition passed P16.

Real habitation runs must inject a real provider-backed `ModelHandler` (and a real
round-summary handler where long-session P14 behavior is under test). Each provider
must use a fresh private target/database.


## 15. Long-horizon scheduler hardening

The Current-Core target advances through **intermediate deterministic timestamps**,
not only visible event timestamps.

Between two resident-visible events it processes, in chronological order:

- P12 Task `next_wake_at`;
- resulting C09 durable Wake dispatch;
- P15 periodic-review ticks;
- Tasks created by Review/Wake that are already due at that same tick.

This matters because a synthetic life may have days between visible events. A Task
due on Tuesday must not sleep until Friday merely because Friday is the next fixture
event.

A cycle guard fails closed if model behavior creates a pathological same-time
background loop.

## 16. Final horizon

A scenario may define evaluator-side `end_at`.

The target factory does **not** receive this future timestamp. Only after all
resident-visible events have been delivered does the runner advance the private
virtual clock to `end_at`.

This ensures legitimate post-event Task/Review/Wake work can occur after the last
external life event without leaking the future schedule during target construction.

All shipped fixture manifests define a final horizon beyond their final visible
event.

## 17. Reality-source paths used by habitation

The current Core adapter preserves P13 source boundaries:

- ordinary note/calendar/order/etc. records use `RealityRecord`;
- `photo_description` uses `MediaDescriptorRecord`, never raw image bytes;
- `sensor_numeric` uses `NumericSample + MechanicalSeriesPolicy`;
- resulting registered mechanical markers may enter C09
  `ObservationTriggerService`;
- mechanical trigger code still cannot manufacture Claim semantics.

The benchmark therefore tests the same reality ingestion and Wake path intended for
the runnable Core instead of a test-only shortcut.

## 18. Fresh worlds and visible-life fingerprint

`CurrentCoreHabitationTargetFactory` creates a new SQLite database for every model
candidate. Existing database paths are rejected by default.

The public scenario fingerprint hashes only actual resident execution input:

- opaque subject identity;
- resident-visible event stream;
- final execution horizon.

Semantic scenario ID, benchmark version, seed, evaluator focus and oracle truth are
excluded from that fingerprint. They remain evaluator-side provenance and must never
change whether two candidates received the same visible life.

Deterministic tests prove plumbing, isolation, lifecycle and leak resistance only.
They do **not** prove cognition quality. P16 cognition evidence requires a real
provider-backed resident model living through the sealed scenario.
