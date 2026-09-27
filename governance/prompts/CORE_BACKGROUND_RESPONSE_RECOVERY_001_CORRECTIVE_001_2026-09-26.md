# CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Role:
Core Runtime / Exact-Response Recovery Corrective Engineer

Continue the same engineering PR:
#219

Do NOT create a competing PR.

Historical failed tested exact candidate:
`3f9ec00d0fa283bc5294574d6da1e84d654d6645`

Independent Acceptance verdict:
`ACCEPTANCE_FAIL`

Blocker count:
`2`

Read first:
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_ACCEPTANCE_FAIL_ADJUDICATION_2026-09-26.md`
- `governance/prompts/CORE_BACKGROUND_RESPONSE_RECOVERY_001_2026-09-26.md`
- `governance/prompts/CORE_BACKGROUND_RESPONSE_RECOVERY_001_INDEPENDENT_ACCEPTANCE_2026-09-26.md`
- PR #219 current body/diff/comments

Fetch current live `main` before any work.

Confirm:
`CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001 = READY`

If not READY, STOP.

Your only task is to close exactly these two blockers.

## IA-BLK-001 — cross-work exact-response transplant

Current failed behavior:
an exact response from work A can be staged against an unrelated in-doubt work B because `stage_exact_response()` validates self-consistent response identity but lacks durable proof that the response belongs to B's exact outbound request.

Required closure:
- exact response adoption must require durable request-binding evidence for the exact originating subject/work-kind/work-id/model-round/attempt;
- the binding must be established mechanically before response adoption;
- provider/model/request_id self-consistency alone is not enough;
- operator semantic judgment is not allowed;
- do not create a second cognition/World truth store;
- do not fabricate a response or infer ownership from content.

Mandatory red-first probes:
1. work A -> work B transplant;
2. wake -> periodic_review transplant;
3. periodic_review -> user_turn transplant;
4. subject A -> subject B transplant;
5. round N -> round M transplant;
6. transplant where provider/model are identical and response metadata otherwise looks valid.

Every transplant must fail before semantic application and before attempt provenance is rewritten.

Positive control:
- same exact attempt + correct durable request binding must still recover;
- recovered round provider-call count must remain 0.

Implementation rule:
use the smallest durable Core request-binding mechanism that can actually prove origin. Do not merely add another caller-supplied string that can be copied from A to B without checking it against durable pre-existing attempt state.

## IA-BLK-002 — duplicate JSON semantic keys

Current failed behavior:
`json.loads()` accepts duplicate keys and uses the last value, so conflicting repeated fields can be silently normalized before `ModelDirective` validation.

Required closure:
reject duplicate JSON keys before semantic construction.

Detection must be recursive for every object in the exact directive.

Mandatory red-first probes include duplicates in:
- top-level `response`
- top-level `silence`
- top-level `capability_calls`
- `usage.provider/model/request_id`
- `provenance.provider/model/request_id`
- capability call `name/arguments/call_id`
- nested capability `arguments` objects

Requirements:
- duplicate-key payload -> fail closed;
- no staged response row;
- no attempt transition to response_returned caused by rejected payload;
- no capability/output/metering semantic effect.

Do not broaden this task into unrelated JSON hardening unless a change is strictly required to implement duplicate-key rejection.

## Historical evidence discipline

Preserve:
- failed exact candidate `3f9ec00d...`;
- Independent Acceptance FAIL / blocker=2;
- all existing author red evidence;
- any new red-first corrective evidence.

Do not rewrite historical failed evidence green.

The reviewer-local commit:
`5c59f17658524c0ad23f409a8c108402cea34452`
was not pushed and must not be claimed as a remote GitHub object unless it actually appears later.

## Required regression

After both blockers are fixed:
- blocker-specific tests;
- original `tests/integration/test_core_background_response_recovery_001.py`;
- runtime/background-attempt tests;
- turn-execution recovery tests;
- metering tests;
- Wake regressions;
- Periodic Review regressions;
- user-turn regressions;
- full `pytest -q`.

Record exact environment.

If PR fixture-only workflows reject genuine Core changes solely because of their zero-Core-diff invariant, preserve them as RED/non-applicable scope guards exactly as before; do not relabel them SUCCESS.

## Scope prohibitions

Do not:
- merge #219;
- self-accept;
- enter `CORE-RC-REFREEZE-002`;
- resume B persistence corrective;
- run Resident;
- modify sealed fixtures;
- modify historical Resident evidence;
- redesign the entire attempt ledger;
- weaken `in_doubt`;
- weaken `not_submitted` semantics;
- add provider redispatch on recovery;
- change unrelated product/UI/hardware code.

## Completion

Update PR #219 with the new corrective candidate.

Pin:
- new tested exact candidate SHA;
- parent/base relation;
- exact tree;
- blocker-specific red/green evidence;
- full regression evidence.

Then stop at:

`REVIEW_READY`

Required next step:
fresh `CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`

Do not perform that acceptance in this window.
