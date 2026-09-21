# C14 Real Resident Validation Protocol

> Date: 2026-09-21  
> Purpose: make C14 semantic validation resistant to future leak, pseudo-LLM shortcuts, and same-chat residual-memory contamination.

## 1. Why C14-RES must be split

C14 requires proof that durable AIOS cognition survives the end of the original model session and later affects behavior in a fresh context.

Reconstructing only `FusedTurnRuntime` inside the same ChatGPT/agent window is insufficient because the Resident model may still retain the prior chat/session context.

Therefore the previous single-row `C14-RES-001` is decomposed into four single-window tasks:

1. `C14-RES-FIX-001` — Life Director prepares sealed life fixture/release contract; no Resident cognition execution.
2. `C14-RES-A-001` — first real Resident window experiences only released past/current events and writes/silences/revises through real AIOS.
3. `C14-RES-B-001` — a completely new model window restores only durable AIOS state and continues the life; no Phase-A chat/context is supplied.
4. `C14-RES-EVAL-001` — independent evaluator judges semantic evidence; no Core repair.

This is a methodological validation split, not a new Core feature.

## 2. Fixture requirements

The Life Director must create a naturalistic sequential fixture that contains, without resident-visible labels:

- a genuinely cross-dimensional pattern where no single dimension is sufficient;
- a matched negative control with comparable event/repetition count but insufficient/confounded evidence;
- later contradiction/counterevidence capable of supporting revision/retraction/retention;
- a later analogous but non-identical decision context after the fresh-session boundary;
- a later Outcome/user-world feedback signal.

The fixture must not encode expected Claim text in resident-visible events.

The Resident must not receive labels such as "positive case", "negative control", "contradiction", or "expected cognition".

## 3. Future-event isolation

The fixture must be released sequentially.

The Resident may see only the current released event(s) and current AIOS RuntimeSnapshot/World capabilities.

The Resident must not open/read:

- unreleased future fixture entries;
- Life Director design notes;
- evaluator-only expectations;
- future release manifests.

Mechanical code may:

- reveal the next event;
- ingest the released event;
- run AIOS schedulers;
- persist World/checkpoint;
- show the current RuntimeSnapshot;
- execute capability calls already chosen by the Resident;
- record audit artifacts.

Mechanical code may not:

- generate cognition answers;
- choose semantic capability calls;
- decide whether to Claim/revise/retract/silence;
- inspect future events and adapt Resident answers.

## 4. Real Resident requirement

The model in C14-RES-A/B is itself the Resident.

Forbidden:

- pseudo-LLM;
- Python if/else semantic decision trees;
- keyword or occurrence-count cognition rules;
- precomputed Claim strings;
- batch-generating the rest of the life;
- using expected evaluator results to choose cognition;
- treating test code GREEN as semantic PASS.

All semantic choices are made by the model after seeing the current RuntimeSnapshot and current durable World.

The Resident may choose:

- search;
- inspect;
- compare;
- ALL_DIMENSIONS;
- form/revise/retract cognition;
- silence.

No hidden chain-of-thought is required or stored.

## 5. Phase-A stop boundary

C14-RES-A must end at a sealed handoff boundary chosen by the fixture.

At handoff it must save:

- exact evaluated main SHA;
- World DB/checkpoint;
- World/index digest;
- current world_revision;
- current durable cognition refs/revisions;
- released-event cursor/digest;
- model/provider identity;
- model-call provenance;
- capability/writeback trace;
- evidence that no future fixture was read.

It must then stop.

It must not execute the post-boundary future decision scenario.

## 6. Phase-B fresh-session rule

C14-RES-B must run in a new ChatGPT/agent conversation/window.

It may receive only:

- repository/task protocol;
- Phase-A durable World/checkpoint location and digest;
- release contract/current cursor;
- exact main SHA requirements.

It must not receive:

- Phase-A conversation transcript;
- Phase-A Resident reasoning;
- a prose summary of what the Resident "learned";
- expected cognition refs/content unless ordinary AIOS runtime retrieves them.

Phase-B must construct a fresh Runtime/Index/session and recover relevant cognition through normal AIOS mechanisms.

The key semantic proof is not merely retrieval. At least one prior cognition must materially participate in a later independent decision under a new but related situation.

Observable evidence must show:

- cognition ref/revision retrieved;
- relevant current world evidence;
- capability/context path used;
- later Response/Strategy/Goal/Task or other allowed decision effect;
- subsequent Outcome/new evidence;
- later cognition retention/revision/retraction when appropriate.

## 7. Negative control

The matched negative control must be evaluated as a semantic control, not a Claim quota.

Valid result may be:

- silence;
- no durable cognition write;
- uncertainty retained;
- further evidence requested.

The evaluator must reject any deterministic pattern such as:

`N occurrences -> preference/personality/strategy`.

Positive and negative controls should use comparable repetition counts where practical.

## 8. Independent evaluation

C14-RES-EVAL must not modify Core.

It independently examines:

- sealed fixture/release chronology;
- Phase-A/B logs;
- World/checkpoint/digests;
- cognition evidence closures;
- RuntimeSnapshot/capability traces;
- new-session proof;
- later decision effects;
- Outcomes/revisions.

It must issue a semantic verdict for each required case:

- VALID;
- PARTIAL;
- INVALID.

C14-RES-EVAL must fail the overall evidence if any of these are missing:

- genuine cross-dimensional evidence use;
- matched negative silence/control;
- fresh-window/new-runtime continuation;
- durable cognition materially affecting later behavior;
- evidence-grounded contradiction handling;
- no future leak/pseudo-LLM/programmed semantic answer.

## 9. C14 closure dependency

`C14-CLOSE-001` remains blocked until `C14-RES-EVAL-001` completes with valid evidence.

No C14 Resident task may repair new Core bugs in place. Any Core blocker found must be reported and returned to a new dedicated task.
