# CORE-GAP-FIX-003 Integration Receipt — 2026-09-24

Status: DONE
Task: CORE-GAP-FIX-003 / CORE-GAP-FIX-003-CORRECTIVE-001 / post-FIX001 revalidation
Finding closed: CG-003 — USER_TURN_IN_DOUBT_RECOVERY

## Historical chain

- Original PR: #157.
- Original failed reviewed head: `81d626820cfa31e4f3f1aba0e892eb48cb11e46c`.
- Historical independent review: PR #162 = ACCEPTANCE_FAIL.
- Historical blocker: `CORE-GAP-FIX-003-ACCEPT-BLOCKER-001`.
- Corrective pre-FIX001 head: `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`.
- Historical corrective review #174 correctly returned `REBASE_REVALIDATION_REQUIRED` after FIX-001 integrated.
- These historical reports remain unchanged and must not be rewritten as PASS.

## Corrective mechanism

The accepted user-turn recovery protocol uses:
- `model_attempt_pre_admission_v1` for the mechanically proven pre-provider-attempt phase;
- the shared `background_model_attempts` ledger as the sole provider-attempt truth once an attempt exists;
- explicit one-shot retry authorization with non-blank reconciliation evidence;
- fail-closed handling for legacy / old `model_attempt_v1 + zero attempts`;
- IN_DOUBT for ambiguous post-dispatch execution;
- durable response/output/completion reconciliation without blind provider reinvocation;
- A09 exact turn/input identity and conflicting-input fail-closed behavior.

No second user-turn provider-attempt truth store was introduced.

## FIX-001 serialization

FIX-001 was independently accepted and integrated first:
- accepted exact head: `a56f113ace3c5e01af3acb724468bc2e0fbd4e98`;
- merge: `d97a1bfa527caadb4ab22d232fd627c0483e02d8`.

PR #157 then absorbed the FIX-001-integrated main:
- absorbed main: `9cfcd2d7e5293e0596eb1de5c203f61213973494`;
- post-FIX001 exact head: `7c0c51a7e9cda41a5aa61357ebba96955948a4a7`.

The shared `turn_runtime.py` was independently reviewed to retain both:
- FIX-001 temporal read-cut / cutoff-aware C14 lineage semantics;
- FIX-003 user-turn recovery semantics.

## Exact-head revalidation

Exact candidate:
`7c0c51a7e9cda41a5aa61357ebba96955948a4a7`

All 13 required workflows completed SUCCESS:
- P16 `35986286182`
- fused-turn-runtime `35986286308`
- C09 `35986286147`
- P15 `35986286137`
- C14 runtime `35986286215`
- C14 loop `35986286171`
- P9 `35986286173`
- P10 `35986286193`
- P11 `35986286157`
- P12 `35986286175`
- P14 `35986286246`
- constitutional cognition closure `35986286165`
- C15 cognition evidence policy `35986286133`

Full P16:
- job `107589604043`
- CPython 3.12.14
- pytest 8.4.2
- pydantic 2.13.5
- command: `pytest -q`
- reached 100%
- 662 pass markers / 0 failures / 0 errors / 0 skips / 0 xfail / 0 xpass
- workflow/job conclusion: SUCCESS

## Fresh final independent acceptance

Final review-only PR:
- PR #178
- review head: `d7fe9446904f79a945362da73b35baed9f7c2e85`
- report: `reviews/CORE_GAP_FIX_003_POST_FIX001_REVALIDATION_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
- verdict: ACCEPTANCE_PASS
- blocker count: 0

Independent adversarial evidence:
- probe PR #176 was evidence-only and CLOSED / UNMERGED;
- crash-x3 recovery: provider call = 1, deterministic round-0 attempt row = 1, assistant output = 1;
- forged/stale pre-admission marker with real IN_DOUBT attempt: attempt ledger dominated and retry was rejected;
- probe P16 run `35987450415`, job `107593343933`, 664 pass markers, 13/13 probe workflows SUCCESS.

## Integration

PM merged acceptance evidence first:
- PR #178 merge: `0cb1a848ab24128fcea90cb08e94b9e2994cb157`.

Before candidate merge, PM re-read PR #157:
- exact head remained `7c0c51a7e9cda41a5aa61357ebba96955948a4a7`;
- only new main drift was the #178 review report;
- GitHub recomputed `mergeable=true / mergeable_state=clean / rebaseable=true`.

PM then merged #157 with expected-head pin:
- merge: `78c103322b14c60cabf92174b0b5a7385752d758`.

## Honest post-merge note

At integration writeback time, GitHub returned no automatic workflow runs for merge commit
`78c103322b14c60cabf92174b0b5a7385752d758`.
No post-merge green run is claimed.
The accepted exact-head 13/13 workflow set, full P16 662-pass evidence, independent final acceptance #178, and adversarial probe evidence are the authoritative integration evidence.

## Release effect

CG-001 = CLOSED.
CG-002 = CLOSED.
CG-003 = CLOSED.

All three audited Core gap blockers are now integrated.

This does not mean AIOS Core is complete.
The next S2 task is `CORE-HEADLESS-001`.
RECOVERY, SCALE, RC-FREEZE, fresh Resident A/B/C, C16, broad P16, and P17 remain gated by their own completion criteria.

No Resident was run during this integration.
