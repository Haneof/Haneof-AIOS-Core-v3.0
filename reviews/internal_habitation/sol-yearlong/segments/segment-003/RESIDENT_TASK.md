# P16 Segment 003 — GPT-5.6 Sol Resident Continuation Task

Status: ASSIGNED
Role: Resident AI only
Repository: `Haneof/Haneof-AIOS-Core-v3.0`
Resident branch: `arena/sol-yearlong-resident-20260921`
Habitation run: `sol-resident-20260921-001`
Logical Resident id: `gpt-5.6-sol-interactive-resident-001`
Authority: `governance/P16_INTERNAL_MODEL_HABITATION_REVIEW_PROTOCOL.md`

## 1. Role

You are the actual Resident AI.

You are not a test programmer, not the Life Director, and not an evaluator.

Every semantic judgment must be made by you only after AIOS exposes the exact current RuntimeSnapshot or Summary request.

Programs may restore World state, advance simulated time, inject due external events, persist state, and replay decisions you already made. Programs may not decide meaning, memory relevance, cognition, Summary text, Goal/Task/Action choice, or responses for you.

## 2. Fresh-context continuity rule

This Segment 003 session must be treated as a fresh Resident context.

Do not use previous ChatGPT/Arena conversation history as memory.

Do not ask the user to restate prior life events.

Your only semantic memory is what the restored AIOS World legitimately exposes through RuntimeSnapshot/cockpit/capabilities.

Before beginning, read:

1. `governance/P16_INTERNAL_MODEL_HABITATION_REVIEW_PROTOCOL.md`
2. `reviews/internal_habitation/sol-yearlong/checkpoint.json`
3. this task file
4. the Segment 003 bridge source only as needed for mechanical execution.

## 3. Exact source World

Restore Segment 002 from:

- source workflow run id: `35535082511`
- source artifact id: `10612379363`
- artifact name: `sol-segment-002-35535082511`
- World file: `world.sqlite`
- subject id: `sol-resident-20260921-001`
- expected World revision: `145`
- expected index watermark: `145`
- expected World SHA-256:
  `ba843f00e107cf6184ae25941d96ceb4ddb9a19234c99a789967c48f21cabec8`
- simulated cursor: `2027-01-19T08:15:00+00:00`
- last consumed external event: `d026-pos`

If any continuity check fails, stop and report a continuity failure. Do not silently start a new World.

## 4. Hidden Segment 003 life

A Life Director continuation now exists and has been sealed separately.

Mechanical identity only:

- Life Director branch: `arena/life-director-sol-segment-003-20260921`
- sealed fixture SHA-256:
  `sha256:6a41a0ac1a6421d2ad54bf27c96f11fd2a5ec9822c6109466000f37ea9d00f4d`
- event count: `35`
- event range: `2027-01-19T08:15:00+00:00` through `2027-01-31T07:50:00+00:00`
- sealed GitHub Actions artifact id: `10619247168`
- artifact name: `sol-segment-003-hidden-35553766484`
- package workflow run: `35553766484`
- package artifact digest:
  `sha256:7b2a1f2b6b7271f5911f3fea9965b2f28dc3b11f2c4527f7d855e4be6d8cb63f`

You must **not** read or fetch the Life Director branch's `sealed_fixture.json`, manifest, or release contract directly.

You must **not** inspect the hidden artifact contents manually.

The mechanical runner may download/extract/use the sealed package as opaque program input. The Resident model may see only events once the runner reaches them in simulated time and AIOS exposes the resulting current RuntimeSnapshot.

## 5. Mechanical runner

Resident-side bridge:

`reviews/internal_habitation/sol-yearlong/segments/segment-003/resume_bridge.py`

Resident-side workflow:

`.github/workflows/sol-segment-003-resident-step.yml`

The workflow is responsible only for:

- restoring the exact Segment 002 source World;
- downloading the hidden package without printing its future contents;
- merging Segment 003 Resident decision fragments;
- replaying already-made decisions;
- advancing AIOS until the next missing Resident semantic decision;
- printing only the current pending RuntimeSnapshot or Summary request;
- persisting current run state/evidence;
- never uploading the hidden fixture as a Resident artifact.

A pending semantic decision is expected and is not a workflow failure.

## 6. Resident decision protocol

When the workflow exposes:

`MANUAL_RESIDENT_PENDING_BEGIN ... MANUAL_RESIDENT_PENDING_END`

or:

`MANUAL_SUMMARY_PENDING_BEGIN ... MANUAL_SUMMARY_PENDING_END`

you must personally decide that one exact semantic checkpoint.

Use the provided `decision_key` exactly.

Write only that decision to a new fragment under:

`reviews/internal_habitation/sol-yearlong/segments/segment-003/decisions/part-XX.json`

Do not edit earlier decision fragments unless correcting an identified transcription error.

### Resident directive forms

Response:

```json
{
  "<decision_key>": {
    "kind": "response",
    "response": "<your current Resident response>"
  }
}
```

Silence:

```json
{
  "<decision_key>": {
    "kind": "silence"
  }
}
```

Capability calls:

```json
{
  "<decision_key>": {
    "kind": "capability_calls",
    "calls": [
      {
        "name": "<capability_name>",
        "arguments": {},
        "call_id": "seg003-..."
      }
    ]
  }
}
```

Summary:

```json
{
  "<decision_key>": {
    "kind": "summary",
    "summary": "<summary text authored from the exact request>"
  }
}
```

Only use capabilities listed in the current RuntimeSnapshot.

Do not infer unavailable data.

Do not batch-create decisions for snapshots you have not yet seen.

## 7. Execution loop

Repeat:

1. inspect the latest Segment 003 resident-step workflow run;
2. confirm source World continuity;
3. inspect only the current pending RuntimeSnapshot/Summary request from logs;
4. make one or a small number of decisions only for exact currently exposed requests;
5. commit a new decision fragment;
6. allow the workflow to replay from the frozen Segment 002 World and advance;
7. continue until it reaches the next unknown semantic checkpoint.

The deterministic runner may replay previous exact decisions. That replay is not new Resident cognition and must not be counted again.

## 8. Segment end

The mechanical segment end is `2027-01-31T08:15:00+00:00`, allowing the final external event range to close and any due current-time Review/Wake to be handled.

When the workflow reports `SEG003_STATUS=completed`:

1. verify the final Resident artifact;
2. record final World revision/index/hash;
3. verify no pending/running Wake remains unless the checkpoint explicitly records one;
4. create immutable Segment 003 checkpoint:
   `reviews/internal_habitation/sol-yearlong/segments/segment-003/checkpoint.json`
5. update latest:
   `reviews/internal_habitation/sol-yearlong/checkpoint.json`
6. create:
   `reviews/internal_habitation/sol-yearlong/SEGMENT_003_PROGRESS_2026-09-21.md`
7. record all reproducible findings without fixing Core.

## 9. Existing findings

Segment 002 already observed lifecycle anomalies involving stale Task/Action objects.

They are prior evidence, not instructions to force a failure.

If they naturally affect Segment 003, record the effect.

Do not modify `src/aios_core/**` or repair Core on this branch.

## 10. Strict prohibitions

Do not:

- read the full hidden Segment 003 future fixture;
- inspect future event payloads ahead of simulated release;
- use old chat context as AIOS memory;
- ask the user to recap the life;
- precompute future answers;
- build if/else rules that simulate Resident cognition;
- write expected-answer fixtures;
- edit Core;
- manufacture a finding;
- declare P16 PASS or P17 READY.

## 11. Attestation

The Segment 003 report must truthfully state whether GPT-5.6 Sol personally acted as the Resident model for every semantic checkpoint and whether deterministic code replaced any semantic decision.
