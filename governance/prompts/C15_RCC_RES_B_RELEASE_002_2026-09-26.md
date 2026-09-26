# C15-RCC-RES-B-RELEASE-002 — Independent B Release Review

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Task:

`C15-RCC-RES-B-RELEASE-002`

Role:

**Independent B Release PM / Non-Resident Release Reviewer**

You are not:
- Resident B;
- Resident C;
- preflight implementation engineer;
- semantic evaluator;
- fixture designer;
- Core feature engineer.

Your only task is:

> Independently revalidate the accepted B-preflight packet on current main, freeze one exact Resident-B launch identity and Resident-safe startup packet, and release B-RERUN-002 without revealing or consuming cursor 14.

## 1. Start gate

Fetch live latest `main`.

Read:
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/C15_RCC_RES_B_PREFLIGHT_002_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-26.md`
- accepted preflight root `reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/**`
- `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md`

Confirm exactly:

`C15-RCC-RES-B-RELEASE-002 = READY`

If not the unique legal READY task, STOP.

## 2. Exact accepted preflight pins

The accepted preflight PR is #209.

- accepted candidate: `aab3a30cc48e8c7041ef4b37e0e5f379c3060c93`
- candidate tree: `6de6c9bcc8cc7de64802f68b59178e0881e3a42d`
- integrated merge: `65e6e8266bb0541d624eb8e5bba825b91145564f`
- PM review: `5323959000`
- Independent Acceptance: `5323972504`
- acceptance verdict: `ACCEPTANCE_PASS / blocker=0`

Re-read from GitHub/current main. Do not trust this prompt if the branch/head has drifted.

Exact active surfaces:

- lifecycle checker blob: `72f674b2d430262a5eff9cb66c7004917c0f4ae4`
- startup runbook blob: `c56f528f4ea181ae002ed22d3e810ab6022ddb17`
- per-cursor runbook blob: `17f27956152f4edd49b57f72c7546eef668406fa`
- Resident-safe packet manifest blob: `ac3da8b204b93fc47b32a7d5a98ae6a2a89e0d7c`
- Resident-B contract blob: `32d2dc99c2a9d391fad1a4c84824ebce8ca46d79`
- Resident-B contract SHA-256: `28d3262f56b7ef93a32a842f1d4d66f99748f2b07adcece43e815eb9d5cd18ef`
- environment manifest blob: `c6ce70a78a413510f8ae52ff21616c1638c81f7d`
- final-freeze procedure blob: `d77a25c11304d142d8e3fc816f5dde78a6fafbb6`
- current committed E2E blob: `52da0673309781ab9f9a98aa9b59b4748d9bd225`

The legacy task label inside the frozen Resident-visible contract is not authority for PM scheduling. Its semantics are the frozen fresh-context Resident-B contract for cursors 14..22. Do not edit it during release review.

## 3. Frozen RC and A lineage

Require:

- frozen software `773876f92d5f8e53422f8f5a68cc651953d93052`
- Core tree `fe77f8a0706acfaf369041d0882b6d0e6de39f22`
- canonical A PR #205 exact head `d17ae972ad1d312735c355f775ac024bc4cebdf7`
- World/index = `98/98`
- last ACK = `13`
- next sequence = `14`
- pending reveal = `null`

Recompute accepted freeze hashes:

- World `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa`
- index `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1`
- release-state `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8`

If #205 moved or any pin fails, BLOCKED.

## 4. Fresh release validation

Independently confirm:

1. the merged preflight tree still has zero `src/aios_core/**` drift from the frozen Core tree;
2. `World/index/release-state` copied lineage is byte-exact and the A→B boundary is still 13→14 with no pending reveal;
3. Resident-safe sandbox exposes only the approved contract/Core/state/current-event/capability IPC surfaces;
4. fixture/evaluator/governance/.git/A evidence/old transcripts/Phase-C material are not Resident-readable;
5. production transport is `ProductionResidentHandler + ExternalBrokerClient`, not a synthetic responder;
6. provider usage is not synthesized;
7. canonical lifecycle is exactly:
   `REVEAL → INSTALL_CURRENT_EVENT → PERSIST_PROJECTION_EVIDENCE → CREATE_BINDING_RECEIPT → VERIFY_BINDING → DERIVE_OCCURRED_AT → INGEST → MODEL_WORK → FINISH_CURSOR_MODEL_WORK → DURABLE_ACK → CLEAR_BINDING → NEXT_REVEAL`;
8. no model dispatch is legal without the current event + binding;
9. final freeze/evidence procedure is frozen before B;
10. no real cursor-14 payload has been consumed or presented to a model.

Do not reveal cursor 14 merely to review the packet.

## 5. Exact environment

Release packet must require:

- Debian 12 or an equivalent environment proven to satisfy the same frozen execution contract;
- `python3 == Python 3.11.2`;
- `/usr/bin/python3 == Python 3.11.2`;
- Pydantic `2.13.5`;
- pydantic_core `2.46.5`;
- annotated-types `0.8.0`;
- typing-inspection `0.4.4`;
- typing_extensions `4.16.0`;
- requirements freeze SHA-256 `bd7a76d1171c137f9daee9c0a3dbff029b8cbbccef88f0a1aff7907710a82375`.

No package upgrade or adaptive candidate mutation is allowed at B start.

## 6. Release identity to freeze

If all checks pass, publish exactly one B run identity and one B session identity.

Use:

- run ID: `c15-rcc-res-b-rerun-002-65e6e826`
- B session ID: `c15-rcc-res-b-session-002-65e6e826`
- operator/preflight source anchor: PR #209 merge `65e6e8266bb0541d624eb8e5bba825b91145564f`
- accepted candidate anchor: `aab3a30cc48e8c7041ef4b37e0e5f379c3060c93`
- Resident-safe packet manifest blob: `ac3da8b204b93fc47b32a7d5a98ae6a2a89e0d7c`
- Resident contract SHA-256: `28d3262f56b7ef93a32a842f1d4d66f99748f2b07adcece43e815eb9d5cd18ef`

Do not generate a second competing run/session identity.

## 7. Release deliverables

Create a release record under governance that includes:

- live main reviewed;
- exact preflight/IA pins;
- exact run/session IDs;
- exact safe-packet/contract pins;
- exact B entry procedure;
- frozen environment;
- stop conditions;
- identity evidence inventory;
- explicit statement that no cursor 14 was revealed during release review.

Also create one Resident-safe launch prompt/instruction that contains only:
- Resident role;
- fresh-context rule;
- allowed cursor range 14..22;
- run/session IDs;
- approved safe contract/runtime interface;
- requirement to decide semantics itself from current reality + durable AIOS state;
- RUN_COMPLETE stop boundary after cursor 22 freeze.

It must not contain:
- fixture future;
- evaluator criteria;
- expected cognition;
- A transcript/prose decisions;
- PM reports;
- acceptance conclusions.

## 8. PASS exit

If blockers = 0:

- `C15-RCC-RES-B-RELEASE-002 = DONE / RELEASED`
- set exactly `C15-RCC-RES-B-RERUN-002 = READY`
- keep B acceptance, C, evaluator, close, C16, broad P16/P17 blocked.

The governance release record must be integrated on main before Resident B starts.

## 9. BLOCKED exit

If any pin/isolation/provenance/runtime blocker exists:

- keep `C15-RCC-RES-B-RERUN-002 = BLOCKED`;
- preserve exact evidence;
- record the blocker;
- do not repair Core or reveal B data in this window.

## 10. Stop boundary

This release-review task never acts as Resident B.

Do not:
- reveal cursor 14;
- execute Resident cognition;
- write Resident semantic answers;
- run Resident C;
- enter evaluator/closure.

After release writeback is on main, the only next task is:

`C15-RCC-RES-B-RERUN-002`
