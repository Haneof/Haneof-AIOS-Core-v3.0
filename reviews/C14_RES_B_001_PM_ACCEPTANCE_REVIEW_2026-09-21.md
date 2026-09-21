# C14-RES-B-001 Independent PM Acceptance Review

> Date: 2026-09-21  
> Task: `C14-RES-B-001`  
> Review scope: Resident-B execution completeness, isolation evidence, durable handoff integrity, and whether the produced artifacts are sufficient for the independent evaluator.  
> Semantic C14 PASS/FAIL: **NOT DECIDED HERE**.

## 1. Pinned evidence

- Evaluated main: `9578d990fc47943b69c77b12d126255f6691a6dc`
- Resident-B evidence PR: #79 — **open / unmerged**
- Exact evidence head: `546449a453e6e6dff3a2eeb2b52e7cf6786927be`
- Resident-B branch: `arena/01a0c517-haneof-aios-core-v3-0`
- Evidence manifest: `reviews/internal_habitation/c14-resident/v2/runs/resident-b-20260921/evidence/MANIFEST.md`
- Final World SHA256: `a288fc5d11a1a73006725efdd906a7ab014d4228085c610b4a32f887cfe3d615`
- Final release-state SHA256: `9281ced5013b45445574698d53ff9a2d57d5308ac5d1221e5db178efcf0c8a4f`

PR #79 contains 280 changed files, all under the single Resident-B evidence run directory. There are no `src/aios_core/**`, governance, task-board, fixture, or release-contract changes in the evidence PR.

## 2. Fresh-window / inherited-state boundary

The run records the exact inherited Resident-A World digest:

`0ee338aa8f2845bb376610da3c450e09ff9cc8bec5184ca60608b2465d7ba72f`

and release-state digest:

`e922d268fbb11364a7bb558aed60b88e7a3c075032f4fa4e1c47a84de3f765f1`.

The Resident-B manifest records a fresh session `resb-20260921-282770` and Phase-B initialization through release operator v4.

Repository artifacts cannot prove a negative about every file the model may have viewed outside recorded tooling. Therefore the strongest defensible audit wording is **no evidence of Phase-A prose/chat contamination in the committed run artifacts**, not an absolute claim that contamination was mathematically impossible.

## 3. Sequential release / canonical conversation

Phase B processed cursors 25 through 36:

- 9 ordinary mechanical ingests;
- 3 canonical USER conversation ingests;
- exact durable ack receipts for all released events;
- release state ends at last_acked_sequence=36, next_sequence=37, pending reveal absent.

The committed `cursor_037/event.json` file is empty. No cursor-37 future payload is present.

For the three USER conversation events, the canonical user Observation is reused by normal `FusedTurnRuntime.run_turn()`; no duplicate fixture user Observation is recorded.

## 4. Same-model semantic bridge

The committed `bridge/bridge_server.py` is a thin synchronous rendezvous bridge.

It:
- instantiates real AIOS World/index/runtime;
- serializes exact RuntimeSnapshot / Summary input;
- pauses for model-authored response files;
- executes the exact requested capability calls;
- persists results/logs.

The reviewed bridge contains no keyword-to-cognition mapping, no expected-answer table, no search-target chooser, no Claim/revise/retract/silence policy, and no pseudo-LLM decision rules.

## 5. Fresh-runtime cognition recovery evidence

The evidence contains a direct recover-and-consume chain.

At the first Phase-B cognitive wake, the Resident itself requested:

`search_timeline(... object_types=["claim"] ...)`

and received:

`clm_79df61916b8bb4c10cb3faa3@2`.

The next model step explicitly requested `inspect_world_object` for that exact Claim.

Later, during cursor 26 normal conversation runtime, the current RuntimeSnapshot automatically carried:

`clm_79df61916b8bb4c10cb3faa3@3`

as a memory card with `retrieval_score=10`.

The Resident then created:

`task_5029111ade74171bc3758e98@1`

with `reason_refs` containing both:
- the current canonical user Observation;
- the recovered Claim @3.

The Resident response used the earlier writing-block evidence pattern to choose the 09:00 interruption-first schedule and preserve a continuous writing block.

This is stronger than mere retrieval: the prior cognition is pinned into the durable reason lineage of a new Task.

## 6. Later result / cognition update

Cursor 31 provides a later real `dim:work_outcome` Observation. During the resulting task/wake lifecycle:

- the Task progresses to completed using world evidence;
- `clm_79df61916b8bb4c10cb3faa3` is revised @3 -> @4;
- confidence changes 0.5 -> 0.6.

Cursor 32 then provides user feedback supporting the mechanism. The Resident deliberately retains rev4 rather than revising on every supporting confirmation.

An additional user-understanding Claim is created at cursor 36:

`clm_42e66b47b667be52da20ae8a@1`.

These artifacts are available for the independent evaluator; this PM review does not decide whether every semantic update is valid.

## 7. Negative/silence behavior

The manifest reports:
- 5 C14 derivation bundle silences;
- 3 Periodic Review silences;
- no retract.

The run does not appear to force a Claim on every wake or every supporting observation. Independent evaluator must still inspect whether each silence/revision is semantically justified.

## 8. Provenance deviations / caveats

1. Arena.ai did not expose the underlying model identity. The run correctly records only `Arena.ai Agent Mode`; exact provider/model identity is unverified.
2. The Resident run environment used Python 3.11.2 because the sandbox lacked Python >=3.12. This differs from the repo's formal runtime requirement. It is recorded rather than hidden.
3. The run notes that the mechanical fixture-ingest path does not pass through the normal RealityIngestService observation listener. No attention watch was registered in this run, so no concrete semantic effect is demonstrated here. Evaluator may decide whether this affects the specific C14 claims.
4. Exact semantic hidden-case validity remains evaluator-only.

These are provenance limitations, not reasons to discard the evidence run at PM handoff.

## 9. PM verdict

`C14-RES-B-001`: **DONE — RUN COMPLETE / EVIDENCE ACCEPTED FOR INDEPENDENT EVALUATION**.

This verdict means:
- the Phase-B Resident run completed its sealed release range;
- evidence is durable and remotely inspectable;
- the evidence PR is pinned and remains unmerged;
- the artifacts are sufficient to start the evaluator.

It does **not** mean C14 has passed.

Next task:
`C14-RES-EVAL-001 = READY`.

The evaluator must independently rule VALID / PARTIAL / INVALID for:
- Phase-A cross-dimensional positive cognition;
- matched-negative silence;
- fresh-window cognition consumption;
- contradiction/revision behavior;
- future leak / contamination;
- pseudo-LLM / semantic shortcut risk.
