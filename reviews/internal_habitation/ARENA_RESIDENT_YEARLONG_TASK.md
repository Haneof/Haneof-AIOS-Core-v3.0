# P16 Arena Resident Year-Long Independent Habitation Task

Status: ACTIVE
Authority: `governance/P16_INTERNAL_MODEL_HABITATION_REVIEW_PROTOCOL.md`
Repository truth: `main`

## 1. Arena execution model

Arena.ai assigns each session its own automatic `arena/*` branch. That branch is the reviewer's private evidence branch for this run.

Do not assume you can checkout, push to, or continue another Arena session's branch.
Do not use another Arena branch as your working branch.
Do not modify `main`.
Do not modify `src/aios_core/**`.

Each Arena session is an independent Resident review unless the project lead explicitly assigns a continuation protocol.

## 2. Core rule

You, the actual large model in this session, are the Resident AI under test.

This is not a benchmark-generation task.
This is not a request to write a large fixture and let Python finish the year.
This is not a request to encode your cognition as if/else rules, keywords, expected answers, templates, or a pseudo-model.

Programs may:
- create or emit external-world observations;
- advance simulated time;
- persist and restore World state;
- execute capability calls that you already chose;
- save checkpoints and evidence;
- stop at the next semantic checkpoint.

Programs may NOT:
- choose what the user means;
- decide what memory is relevant;
- write your replies;
- author Summary text;
- decide Claim creation/revision/retraction;
- decide Goal/Task/Action/Outcome semantics;
- decide policy changes;
- infer conclusions for you;
- batch-generate future Resident decisions;
- fast-forward through semantic checkpoints without invoking you.

Every meaningful Resident semantic checkpoint must be decided by the model in this Arena session after seeing only information available at that simulated time.

A run that completes thousands of semantic decisions in seconds by deterministic code is INVALID.

## 3. Independent life

Create one materially unique life for this reviewer. Do not copy another reviewer's persona, event timeline, profession, relationships, habits, contradiction schedule, or expected findings.

Before your first frozen report, do not read other Arena habitation reports or use their findings to shape your life.

The external world may be generated dynamically, but do not precompute Resident answers or hidden answer keys.

If you author future external events yourself, keep unreleased future semantics outside the Resident context and do not use knowledge of future events when making current Resident decisions.

## 4. Long-horizon requirement

Target one coherent life totaling at least 365 consecutive simulated days and satisfy the density requirements in the governing P16 protocol.

Use resumable segments rather than a single bulk script.

Recommended segment size: roughly 7-30 simulated days.

At each segment:
1. expose only current-time external evidence;
2. run the real AIOS runtime;
3. stop whenever a Resident semantic judgment is required;
4. personally make that judgment as the model;
5. persist the decision and World;
6. continue;
7. freeze a durable checkpoint at the segment boundary.

If this Arena session cannot honestly reach 365 days before context/tool limits, do not fabricate completion. Freeze the exact durable checkpoint, report cumulative progress, and stop cleanly.

## 5. Evidence requirements

Keep evidence sufficient to prove:
- the model itself made the semantic decisions;
- deterministic code did not replace Resident cognition;
- simulated time was monotonic;
- World continuity was preserved;
- restart/resume state is reproducible;
- findings came from the real runtime;
- no Core source was modified.

Record reproducible bugs and optimization opportunities without repairing Core on the review branch.

## 6. Forbidden shortcuts

INVALID:
- pre-generating a year's answers;
- scripted keyword response tables;
- `expected_answer`, `expected_claim`, `expected_summary`, `expected_policy`;
- a fake/pseudo LLM;
- using another reviewer's decisions;
- using hidden future events to improve current answers;
- treating a passing scripted test suite as Resident habitation;
- claiming 365-day completion from event playback without real model cognition checkpoints.

## 7. Completion

When the session ends, commit:
- durable World/checkpoint evidence;
- cumulative simulated duration;
- event/interaction/cognition counts;
- restart/resume evidence;
- reproducible findings;
- a truthful attestation stating whether the actual Arena model personally made every semantic checkpoint represented as Resident cognition.

Do not declare P16 PASS or P17 READY.
