# C15-RCC-RES-A-001 PM Evidence Acceptance Review — 2026-09-22

> Task: `C15-RCC-RES-A-001 Evidence Acceptance / Governance Handoff`
>
> Reviewer role: Independent PM / Resident Evidence Acceptance Reviewer
>
> Scope: provenance + integrity + isolation + freeze only
>
> Acceptance disposition: **PASS**

## 1. Starting / live main

- Reviewed live `main`: `cc00082b039a2931c474d6c2a19755218e23c052`.
- The authoritative task board still showed `C15-RCC-RES-A-001 = READY` and `C15-RCC-RES-B-001 = BLOCKED` immediately before governance writeback.
- No earlier Resident A evidence acceptance was present on live main.

## 2. Canonical evidence identity

- Evidence PR: **#101**
- Evidence branch: `arena/01a0c83a-haneof-aios-core-v3-0`
- Exact evidence head: `bfbfa059e2ac616326eecdfe3ffa7a927bdc7ce2`
- Session: `resident-a-c15-rcc-20260922`
- Run directory: `reviews/internal_habitation/c15-rcc/v1/runs/resident-a-20260922/`
- GitHub PR state at review: **OPEN / UNMERGED**.
- The evidence branch compared identical to the exact evidence head: 0 commits ahead / 0 behind.

PR #101 at this exact head is the canonical Resident A evidence candidate. It must remain open and unmerged; its private World is not governance content and must not be merged into `main`.

## 3. Cursor 1..13 lifecycle verification

Mechanical lifecycle evidence contains:

- exactly one reveal record for each fixture cursor `1..13`;
- exactly one ingest receipt and one durable ack receipt for each cursor `1..13`;
- monotonic event ids `c15rcc-001..c15rcc-013`;
- monotonic ack `next_sequence` values `2..14`;
- no skip, reorder, duplicate ack, or duplicate reveal in the frozen artifacts;
- final release state `active_phase=A`, `last_acked_sequence=13`, `last_acked_event_id=c15rcc-013`, `next_sequence=14`, and `pending_reveal=null`;
- no `cursor_lifecycle/cursor_0014_*` artifact;
- `phase_b_initialized=false`.

`cp0014.json` and `cap0014.json` are checkpoint / capability-trace sequence numbers, not fixture cursor 14.

## 4. Boundary time and due-work verification

- Final simulated timestamp: `2026-11-06T11:10:00-08:00` (`2026-11-06T19:10:00Z`).
- Cursor 13 was durably ingested at World revision 79.
- At that same boundary, genuinely due maintenance ran without another fixture reveal:
  - three new dimension-summary commits at World revisions 80, 82, and 84;
  - their associated Wake signals at revisions 81, 83, 85, and 86;
  - periodic-review schedule/begin at revisions 87/88;
  - the Resident-directed review write at revision 89;
  - review completion at revision 90.
- Cursor 13 runtime contains no `run_turn` and no duplicate fixture ingest.
- No virtual-time jump was used to drain future background work.

This establishes that the cursor-13 day-summary work was due maintenance at the Phase A boundary, not a second reveal of cursor 13.

## 5. Exact-byte digest verification

The reviewer independently re-read the exact PR #101 bytes and recomputed SHA256:

- `private_world.sqlite` (630,784 bytes):  
  `ea9ea2384bc10e7fbe12c2015074f25193ada134530882cf5b3276d9201df15a`
- `world_index.sqlite` (770,048 bytes):  
  `0d73069608a0293f938a8bb711096273cbad81dd9e6117118d9517e5791ffc80`
- `release_state.json` (10,777 bytes):  
  `3ca82ff1454deaa9c703c7a0d8e2d7a01b581751bac52286ae390728651591b0`

All three independently recomputed digests exactly match the frozen `final/digests.json`.

Independent SQLite inspection also found:

- `world_commits`: 90 rows;
- maximum / current World revision: 90;
- `object_revisions`: 217 rows;
- `search_meta.search_watermark_world_revision`: 90;
- index `search_doc`: 217 rows;
- index `search_occurred`: 217 rows;
- index lag: 0.

## 6. Artifact completeness and mechanical counts

Frozen evidence includes the required manifest, private World, index, release state, release receipts, cursor lifecycle, checkpoints, summary requests, capability traces, final runtime checkpoint, final digests, Resident run report, consumed directives, and the mechanical transport.

Cross-checks from the artifacts / SQLite / runtime reports:

- cursors acknowledged: 13;
- World revision: 90;
- checkpoints: 42;
- capability traces: 42;
- summary requests / committed summaries: 11 / 11;
- periodic reviews: 4, all terminated silence;
- Wake dispatches: 4 = 2 silence + 2 responded;
- USER turns: 7, all responded;
- total runtime responses: 9;
- total runtime silences: 6;
- current Claims: 13;
- current Claims with revision > 1: 3;
- retracted current Claims: 0;
- runtime transport errors across cursor 1..13: 0.

## 7. Canonical USER conversation ingest

USER fixture cursors are `1, 3, 5, 6, 8, 10, 12`.

- All seven ack receipts use session `resident-a-c15-rcc-20260922`.
- Turn indices are exactly `1..7`.
- Each release receipt binds the exact released USER event to one canonical user Observation.
- Subsequent `run_turn` reports reuse the same user Observation id and the same user World revision created by ingest.
- The seven canonical user World revisions are `1, 10, 15, 22, 55, 67, 76`.
- Independent SQLite inspection found exactly 20 current Observations: 7 user, 7 assistant, and 6 non-conversation/platform.
- Therefore the seven USER releases did not produce duplicate USER Observations.

The runtime's `idempotent_replay_flag=false` reflects that the assistant side was newly committed; it does not indicate a duplicate user commit.

## 8. Real Resident / no pseudo-LLM audit

The only added executable file is `mechanical/resident_transport.py` inside the frozen run directory.

Inspection confirms that it:

- serializes the real RuntimeSnapshot;
- writes a decision request and waits for a Resident-authored directive;
- executes only capability calls / response / silence supplied by that directive;
- archives consumed directives;
- waits separately for Resident-authored summary text;
- performs only mechanical watch matching and ordinary due-work dispatch;
- feeds USER turns through the normal `run_turn` path using the exact current reveal;
- contains no keyword-to-Claim mapping, event-to-fixed-cognition mapping, expected-answer table, automatic confidence assignment, scripted revise/retract decision, evaluator oracle, or future-aware semantic branch.

The 42 checkpoints, 42 capability traces, and archived directives show model-selected reads, writes, retries, responses, and silences rather than a program synthesizing fixed cognition.

**Verdict: PASS for real-Resident / no-pseudo-LLM provenance.**

## 9. Capability failure audit

Three expected failures are preserved as failures, not cleaned up or rewritten as successes:

1. `cp0007-revise-relationship`: `revise_ai_world_claim` → `CAPABILITY_NOT_FOUND`; the Resident then used the legal `revise_claim` capability.
2. `cp0010-search-outcome`: `search_world` → `CAPABILITY_ARGUMENT_ERROR` because an unsupported `dimensions` argument was supplied; the Resident retried with legal query/limit arguments.
3. `cp0027-revise-boundary`: `revise_claim` → `CAPABILITY_EXECUTION_ERROR` with the fail-closed cross-subject error `'ai_agent_self' != 'user_1'`.

The cross-subject target remains at its original revision; no illegal revision was created. Later legal capability work proceeded normally.

## 10. Subject-isolation verification

Successful typed Claim writes observed in the evidence use these subject bindings:

- `user_understanding` → `user_1`;
- `relationship` → `user_1`;
- `calibration` → `ai_agent_self`;
- `cognitive_boundary` → `ai_agent_self`;
- `intent` → `ai_agent_self`.

No current `strategy` or `self` Claim exists in Phase A, so there is no write in those absent domains to classify. This statement is mechanical only and is not a judgment about semantic completeness.

The failed cross-subject `revise_claim` produced no subject leakage.

## 11. Interrupt-Wake non-conversation boundary

Two interrupt Wakes responded:

- cursor 9: `wake_3df17e4ced76971ebbf90c05`;
- cursor 11: `wake_c9ebc3c1cf7b2a3f1b9b953a`.

For both:

- Wake lifecycle became durable `completed`;
- runtime evidence contains an auditable response and `delivery_response`;
- `conversation_commit` is absent / null;
- neither is a USER interaction;
- neither was backfilled as an assistant conversation Observation.

SQLite contains exactly seven assistant conversation Observations, matching the seven USER turns and leaving no extra assistant Observation for these two Wake deliveries.

Disposition: **non-conversation Wake delivery boundary**. No replay or private-World mutation is authorized by this review.

## 12. Pending-not-due Wake disposition

The four final NEW Wakes are:

- `wake_12750e5b9505300ff0479e90`
- `wake_38e0e19a9a8d6f551c225a58`
- `wake_74e9321c82c22fcf551c050d`
- `wake_c4d03a4cf3b9aaf13fab44a4`

Each first hit is `2026-11-06T19:10:00Z`, while background dispatch becomes legal at `2026-11-06T19:11:00Z`. The Phase A final timestamp is `19:10:00Z`.

Disposition: **legitimate pending state; not due at the freeze boundary**. They must not be run for this acceptance.

## 13. Core / fixture / evaluator / release diff and contamination audit

PR #101 changes 227 files, and every changed path is under:

`reviews/internal_habitation/c15-rcc/v1/runs/resident-a-20260922/`

There are zero changes to:

- `src/aios_core/**`;
- `reviews/internal_habitation/c15-rcc/v1/fixture/**`;
- `reviews/internal_habitation/c15-rcc/v1/evaluator/**`;
- `reviews/internal_habitation/c15-rcc/v1/release/**`;
- Resident B/C contracts;
- the RCC ruling;
- constitution / registry authority.

The lifecycle directory contains no cursor 14 reveal artifact, the frozen release state contains no pending reveal, and the frozen run has no Phase B initialization. No B/C contract or evaluator payload is embedded in the evidence artifacts. The Resident run report also records that fixture/evaluator/release source and other Resident material were not opened.

Within the evidence that is available for audit, no future-leak / hidden-handoff artifact was found.

## 14. Python environment deviation

Resident A ran under Python `3.11.2` because Python 3.12 was unavailable.

This is accepted as a **non-blocking environment deviation** because:

- all 13 cursor runtimes completed;
- runtime transport errors are zero;
- both SQLite artifacts parse consistently;
- exact-byte digests match;
- Core source is unchanged;
- World revision / index watermark / lag are internally consistent.

The Resident life is not rerun.

## 15. Freeze and handoff disposition

All integrity, provenance, isolation, and freeze checks required by this PM window pass.

- PR #101 @ `bfbfa059e2ac616326eecdfe3ffa7a927bdc7ce2` is the canonical Resident A evidence.
- PR #101 must remain **OPEN / UNMERGED / PINNED**.
- `C15-RCC-RES-A-001` may advance to **DONE**.
- `C15-RCC-RES-B-001` may advance to **READY**.
- `C15-RCC-RES-C-001`, `C15-RCC-EVAL-001`, and `C15-RCC-CLOSE-001` remain **BLOCKED**.

Resident B may recover only accepted durable AIOS state: private World bytes, rebuildable index, runtime/checkpoint state, release state, mechanical digests, the B-safe run contract, and normal RuntimeSnapshot/capabilities. It must not receive A transcript, A run report, this PM report as a semantic handoff, checkpoint prose dumps, expected cognition, or evaluator notes.

**This PM acceptance verifies Resident A evidence completeness, provenance, isolation and freeze only. It does not judge R1–R9 semantic validity.**
