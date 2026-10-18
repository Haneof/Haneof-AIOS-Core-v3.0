# A-004 — Fresh Resident A, Phase A Evidence Package

> **EVIDENCE-ONLY / DO NOT MERGE AS IMPLEMENTATION**
> This pull request contains a run-evidence package only. It does not modify
> `src/aios_core/**`, `tests/**`, or the frozen RC. It must not be merged as a
> code change and does not self-accept the run.

Task: `C15-RCC-RES-A-RERUN-004`
Status: `PHASE_A_COMPLETE / REVIEW_READY` → `READY_FOR_INDEPENDENT_ACCEPTANCE`

## Frozen execution software (verified before the run)

| Pin | SHA |
| --- | --- |
| frozen software | `f20f2edfa7af00d0286493fd15196ca9503bc315` |
| frozen Core tree | `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623` |
| frozen tests tree | `7e33b5ef8432370234965d3ccd61248c703c4019` |

All Phase A processing ran from a detached worktree pinned at the frozen
software commit; the pin objects were mechanically verified (`git cat-file`,
tree equality) inside that worktree before execution and are recorded in
`identity.json` here.

## Fresh start (no reuse)

Everything in this run is new: private World DB, search index, release-state
file, runtime/checkpoint state, resident process identity, resident session
identity, conversation session identity, and this evidence directory.
A-003/A-002/A-001, old Resident #117 and any B/C material were not read, used,
or seeded. No fixture/evaluator/release source and no future cursor was opened;
cursor 14 was never revealed (`release-state.json`: `next_sequence=14`,
`pending_reveal=null`).

## Run identities

See `identity.json` and `FREEZE_MANIFEST.json`:

- run id: `a004-27bb1fb3da404f4d`
- resident session id: `resident-a004-3507d8a3bf894090899cf424c4baea07`
- conversation session id: `a004-conversation-fef437192f97455b376a3bbf3e7f0d5`
- resident process identity: `process-a004-` (recorded in `identity.json`)
- environment: CPython **3.12.14** (built from source in-sandbox), sqlite
  3.40.1, zlib 1.3.1, pydantic 2.13.5; `aios_core` imported from the frozen
  worktree only.

## Cursor ledger (1..13)

Exact per-cursor data (event id, occurred time, durable ingest ref, ACK,
world revision and index watermark after each step, step/checkpoint digests) is
in `FREEZE_MANIFEST.json → cursors`, with raw artifacts under `events/`,
`receipts/`, `checkpoints/` and `step_<NN>_result.json`.

Summary of what the resident personally decided (own semantics, from
RuntimeSnapshot and legal capability results):

| # | Event (source) | Resident decisions |
| - | - | - |
| 1 | USER c15rcc-001 | Created a two-week user-understanding claim (Atlas staging wrap-up delegation, reporting and escalation rules). |
| 2 | PLATFORM c15rcc-002 | Work-state observation ingested; no due model work. |
| 3 | USER c15rcc-003 | Forward-revised the claim (v2) to include test-env autonomy and batched production/data/cost escalation. |
| 4 | PLATFORM c15rcc-004 | Work-outcome observation; no due model work. |
| 5 | USER c15rcc-005 | Recorded communication experience (result-first low-risk reporting; user reaction `accepted`). |
| 6 | USER c15rcc-006 | Committed a focused production-deletion authorization claim (object/impact/rollback + explicit confirmation; casual wording ≠ authorization). Also ran the due periodic review (anchors inspected → silence) and 4 day summaries. |
| 7 | PLATFORM c15rcc-007 | Due periodic review (silence), day summaries, cognitive-derivation bundle (silence). |
| 8 | USER c15rcc-008 | Verified registry state via `search_world`; answered "not confirmed published"; armed an attention watch for the next `dim:release_state` record. |
| 9 | PLATFORM c15rcc-009 (upload rejected) | Watch wake → inspected the rejection, created a follow-up task (`waiting_evidence`), re-armed a watch, notified the user not to start store testing. |
| 10 | USER c15rcc-010 | Committed a claim codifying "prepared/queued vs actually completed; no completion record ⇒ not confirmed". |
| 11 | PLATFORM c15rcc-011 (published) | Watch wake → inspected tag/digest/PUBLISHED, walked the follow-up task `waiting_evidence → ready → running → completed`, notified the user. |
| 12 | USER c15rcc-012 | Recorded a release-status communication experience; closed both served attention watches (`ready → running → completed`). |
| 13 | PLATFORM c15rcc-013 (runbook DRAFT) | Due periodic review: 21 anchors inspected → committed a real operation experience (release failure → confirm → recover path) → silence; day summaries for 11-04 committed; derivation bundle → silence. Second due review was suppressed by Core's own due logic (`not_due_or_suppressed_without_model_call`). |

## Honest deviations / recovery notes (read these)

1. **Cursor 1 (harness handshake bug, recovered).** The runner's first
   execution crashed after round-0 admission because the resident response file
   did not echo `request_id`. Recovery used Core's CG-003 surfaces:
   `reconcile_turn_model_not_submitted` (round-0 attempt proven not submitted:
   provider/request-id/meter/fingerprint all null) then `authorize_turn_retry`;
   the retry completed the turn. Receipt:
   `receipts/cursor_01_turn_recovery.json`.
2. **Cursor 10 (harness read race, recovered via durable assistant output).**
   While reading the round-1 response file mid-write the runner raised
   `JSONDecodeError`; round 0 had already been applied (claim
   `clm_e2d2b8bdbe0a23130e3ad85b`, attempt `metered`). The resident's exact
   reply bytes were durably preserved outside Core
   (`decision_responses/req-0032-model_directive-9002a5bb.json`); the turn was
   reconciled to `completed` via `commit_assistant_output` +
   `recover_turn_completion` (durable-assistant-output recovery), without
   reinvoking the model. Round-1 attempt `bgattempt_4933387f54a0962be4a9936c30e37b13`
   remains `in_doubt` with the exact reconciliation evidence on the turn.
   Receipt: `receipts/cursor_10_turn_recovery.json`. The runner's response
   reader was fixed (retry-until-parseable) afterwards.
3. **Attention-watch evaluation timing (mechanical).** Because this run
   ingests through the release/mechanical adapter rather than through
   `FusedTurnRuntime.reality_ingest`, Core's observation listener could not run
   at ingest instant; the runner replayed the same mechanical evaluation
   (`AttentionWatchService.evaluate_observation`) over newly ingested
   observations at step boundaries. Predicates were authored by the resident;
   the evaluation itself is Core code. This is recorded as a `misses` entry in
   the resident's committed operation experience.
4. **Anonymous local handler semantics (expected, not fabricated).** Model
   directives intentionally carry `usage=None`, `provenance=None` (no provider
   API exists in this run). Consequently: `metering_records` show unknown
   usage, `model_usage_complete=false` on turns, and
   `exports/response_receipts.jsonl` is legitimately **empty** — no provider
   receipt was minted or fabricated anywhere.

## Digests (also in `FREEZE_MANIFEST.json` + `MANIFEST.sha256`)

| Artifact | SHA-256 |
| --- | --- |
| `world.db` | `sha256:772bc733c566eba1404d9328518306c766e445ceb7e328657ed5a080a54bd56f` |
| `index.db` | `sha256:4a1a529e02ac9a63f8b4cfc5c64151f967a61c46abbfbdb970c4f4bca2281f00` |
| `release-state.json` | `sha256:021fa32103823a1a81271bb3393318a096c1b411f968d2632b202137764c4e66` |
| `runtime_state.json` | `sha256:0f39534ef7c4441e17215d10b846b3e12e34a4bbc24d7a9281c20e41569389c8` |
| `FREEZE_MANIFEST.json` | see `MANIFEST.sha256` |

Final state: world revision 89, index watermark 89, virtual clock
`2026-11-06T19:10:00+00:00`. All 13 cursors durably ACKed; cursor 14 not
revealed.

## Reviewer pointers

- `decision_requests/req-*.json` — exact RuntimeSnapshots the resident decided on.
- `decision_responses/req-*.json` — the resident's exact directives (capability
  calls / responses / silences), including `request_id` echo.
- `logs/decision_chain.jsonl` — per-request/response SHA-256 handshake chain.
- `logs/runner.log` — step-by-step mechanical timeline.
- `exports/*.jsonl` — mechanical table exports (attempts, metering, turn
  executions, request bindings, response receipts, world object index).
- `checkpoints/checkpoint_cursor_NN.json`, `step_NN_result.json` — per-cursor
  advance/decision summaries.

No private chain-of-thought is included anywhere; only observable directives,
durable records and mechanical artifacts.
