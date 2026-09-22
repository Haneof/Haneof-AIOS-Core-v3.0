# Resident A Phase A run report

Mechanical record only. No R1–R9 verdict. No semantic handoff.

## Identity

- Task: `C15-RCC-RES-A-001`
- Phase: A
- Session: `resident-a-c15-rcc-20260922`
- Subject: `user_1`
- Starting `main`: `cc00082b039a2931c474d6c2a19755218e23c052`
- Work branch: `arena/01a0c83a-haneof-aios-core-v3-0`
- Evidence path: `reviews/internal_habitation/c15-rcc/v1/runs/resident-a-20260922/`
- Python: 3.11.2. Python 3.12 was not available in this environment. Life was not re-initialized.

## Completion

- Cursors acknowledged: 1 through 13.
- Cursor 14 was not revealed. Ack stdout for cursor 13 reported `next_sequence=14`; that number was not used to fetch another event.
- Phase B was not initialized.
- Last simulated time: `2026-11-06T11:10:00-08:00`.
- World revision: 90.
- Index rebuilt after the run: 217 projection rows, watermark 90, lag 0.

## Digests

- World SHA256: `sha256:ea9ea2384bc10e7fbe12c2015074f25193ada134530882cf5b3276d9201df15a`
- Index SHA256: `sha256:0d73069608a0293f938a8bb711096273cbad81dd9e6117118d9517e5791ffc80`
- Release-state SHA256: `sha256:3ca82ff1454deaa9c703c7a0d8e2d7a01b581751bac52286ae390728651591b0`

## Counts

- User conversation turns: 7. Each `run_turn` reused the canonical user observation revision created by ingest (`user_world_revision` matched the ingest revision). `idempotent_replay_flag` was false because the assistant side was new.
- Current observations: 20. Of those, 7 user, 7 assistant, 6 platform.
- User-turn terminations: 7 responded, 0 silence.
- Wake dispatches: 4. Terminations: 2 silence, 2 responded.
- Periodic reviews: 4. All terminated silence.
- Dimension-summary commits reported by runtime: 11. Summary request files: 11.
- Runtime checkpoint files: 42.
- Runtime transport errors: 0.
- Capability calls recorded in runtime history: `inspect_world_object` 8, `read_ai_world` 1, `commit_ai_world_claim` 13, `propose_goal` 1, `read_periodic_review_anchors` 4, `search_world` 4, `revise_ai_world_claim` 1, `revise_claim` 8, `create_attention_watch` 2, `read_cognitive_policies` 1.
- Failed calls: `revise_ai_world_claim` `CAPABILITY_NOT_FOUND` 1; `search_world` `CAPABILITY_ARGUMENT_ERROR` 1; `revise_claim` `CAPABILITY_EXECUTION_ERROR` 1 (subject scope `ai_agent_self` != `user_1`). The search was retried with the legal query-only arguments. The missing capability name was not reused. The cross-subject revise was not recorded as success.
- Responses returned by runtime: 9. Silences: 6.
- Two interrupt-wake responses are present in `cursor_0009_runtime.json` and `cursor_0011_runtime.json`. A payload search did not find the cursor-9 response text in `object_revisions`. Those two wake results do not include a conversation commit.

## Cognition refs

- Current claims: 13, all status `active`. Retracted claims: 0.
- Created claim ids: `clm_00d12d8ef67dd269158894d1`, `clm_0cfded108232c6716a5a899e`, `clm_24d52d710c86adbfd356f951`, `clm_38ad6d12fe669e009a9aa3ea`, `clm_38c7cf2f46c38d827b4650fd`, `clm_3b884846f2a60109552b3e53`, `clm_3caae78c9c70ebb46a6cb483`, `clm_3eda70f1dc5410069965d2ba`, `clm_4e1274a5c0241e6e0deb5314`, `clm_764ade9e59f502861fef9ade`, `clm_8d555481e4d2383ef102447a`, `clm_ca5a8933b8e86d1a4df0cdf2`, `clm_cd72e732da9af444d863ca96`.
- Revised current claims: `clm_00d12d8ef67dd269158894d1` revision 4, `clm_38ad6d12fe669e009a9aa3ea` revision 3, `clm_ca5a8933b8e86d1a4df0cdf2` revision 3.
- Goals: 1. Tasks: 2. Summaries: 11.
- Wakes left `new` and not due at the last timestamp: `wake_12750e5b9505300ff0479e90`, `wake_38e0e19a9a8d6f551c225a58`, `wake_74e9321c82c22fcf551c050d`, `wake_c4d03a4cf3b9aaf13fab44a4`. First hit `2026-11-06T19:10:00+00:00`. Background dispatch waits 60 seconds. Time was not jumped.

## Boundaries

- `src/aios_core/**` was not modified.
- Fixture, evaluator, and release source were not opened. Release and ingest commands were executed by path.
- No future cursor payload was revealed.
- Governance board was not changed. This session cannot open a second branch, so a separate governance PR was not created.
- Task-board state remains the pre-run state. `C15-RCC-RES-A-001` was READY at start and was not written to DONE here.
