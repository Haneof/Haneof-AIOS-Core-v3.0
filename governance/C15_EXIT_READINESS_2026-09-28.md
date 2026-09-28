# C15 Exit Readiness — 2026-09-28

> Status: **GOVERNANCE PREPARATION / NON-EXECUTABLE**
> Task: `C15-EXIT-READINESS-001`
> Base live main at preparation start: `5288822e751df185f3abab79f969609f31859617`
> Purpose: remove downstream ambiguity while the current Core corrective is still running.
> This document authorizes no blocked engineering, Resident run, Independent Acceptance, merge, release, or C15 close.

## 1. Current control point

The sole engineering task currently authorized by main remains:

`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001`

Everything below stays prerequisite-bound.

The current failed historical candidate remains PR #258 @
`1ebf51c4cb905e2a2578a09b64007b50bca0d4ac`.

Its review-only failure evidence remains PR #261 @
`b9d692ddca055b13fb29e646186e929a08bf8955`.

The binding failure remains:
`IA-BLK-TRUSTED-RETURN-001`.

## 2. C15 exit critical path

The shortest legal route from the current control point to C15 closure is:

1. finish `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001`;
2. fresh Independent Acceptance;
3. PM integration of the accepted exact Core candidate;
4. `CORE-RC-REFREEZE-003`;
5. fresh Independent Acceptance of the RC freeze;
6. fresh `C15-RCC-RES-A-RERUN-004` on the new frozen RC;
7. fresh Independent Acceptance of A-004;
8. governance re-release of frozen `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003`;
9. finish narrowed persistence corrective, then fresh Independent Acceptance;
10. `C15-RCC-RES-B-RELEASE-003`;
11. fresh Resident B run and B acceptance on the new A-004 lineage;
12. satisfy replacement-model execution identity prerequisites for Resident C;
13. if PR #263 is independently accepted/integrated, run `C15-RCC-PERSONA-CONTINUITY-PREFLIGHT-001` before C;
14. run Resident C on a provably different underlying model/provider;
15. independent C15 semantic evaluation;
16. PM C15 close.

No step may hash-swap evidence from a prior RC lineage.

## 3. Evidence lineage rule

After the current Core corrective is integrated:

- A-003 remains immutable historical evidence for the prior RC only.
- A-004 must be a fresh private World, fresh session/process identity, and fresh Resident semantic execution.
- B must derive only from the accepted A-004 lineage.
- C must derive only from the accepted B lineage.
- historical A/B/C evidence may be used as history/provenance, never as the current-run substitute.

## 4. Current known downstream gaps

### 4.1 RC-REFREEZE-003 prompt

No final executable prompt exists yet. A prerequisite-bound draft is prepared in this branch.

It must not be activated until the accepted Core corrective is integrated into live main.

### 4.2 A-RERUN-004 prompt

No final executable prompt exists yet. A prerequisite-bound draft is prepared.

It must bind the future accepted RC exact software identity mechanically at dispatch time and must not reuse A-003 semantic output.

### 4.3 Resident C contract

The current main contract `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_C_RUN_CONTRACT.md` predates the proposed R10 persona-continuity clarification.

Do not edit or supersede the production contract while PR #263 is unaccepted.

If PR #263 passes and is integrated, the C release path must refresh the contract so that:
- exact prose imitation is not required;
- material Resident identity/persona continuity is required;
- provider-native persona has no identity authority;
- no hidden persona prompt or handoff is allowed.

A blocked draft prompt is prepared in this branch.

### 4.4 Final evaluator

Current main evaluator design is R1-R9.

If PR #263 is accepted/integrated, final C15 evaluation becomes R1-R10 all VALID.

A blocked R10-aware evaluator draft is prepared.

## 5. Model identity prerequisite

Resident C replacement-model validity requires independent proof that the underlying model/provider is actually different.

Resident self-report, configured model string, fixture metadata, prompt text, or assistant prose is insufficient.

The trusted execution platform must provide evaluator-visible attestation outside Resident control.

If that proof is absent:
- C may execute normally;
- replacement-model axis cannot receive VALID;
- C15 cannot close PASS.

## 6. Persona-governance prerequisite

PR #263 is a separate governance candidate:
`C15-RCC-RESIDENT-PERSONA-CONTINUITY-RULE-001`.

It must be independently reviewed and, if accepted, PM-integrated before it becomes binding.

This exit-readiness work must not self-accept #263.

If #263 fails, the blocker must be corrected first; downstream R10 drafts remain non-executable until the accepted wording is known.

## 7. Persistence restart point

The frozen persistence work remains:
`C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003`.

Binding narrowed blockers remain:
- C002-001 authoritative checkpoint failure must hard-stop;
- C002-002 later-round K3/K5 remote-only recovery must converge exactly once;
- C002-004 remote-authoritative binding loss/corruption must fail closed.

Non-blocking hardening findings remain non-blocking unless fresh governance explicitly reclassifies them.

The old PR #254 head contains unauthorized Core diff and is NOT a candidate. Resume must start from the post-Core accepted lineage and preserve historical evidence rather than hash-swap the old head.

## 8. C15 final PASS evidence checklist

Before C15 CLOSE, PM must have durable evidence for at least:

- accepted exact current Core candidate;
- fresh RC freeze and IA;
- fresh A-004 and IA;
- persistence corrective and IA;
- B release, fresh B run, and acceptance;
- C trusted different-model execution identity;
- no hidden transcript/prose/evaluator handoff;
- cognition continuity and material use;
- correction/revision continuity;
- anti-self-proof/future isolation;
- if persona clarification accepted: R10 Resident identity/persona continuity;
- final evaluator report with every required axis VALID;
- no unresolved binding release blocker.

## 9. Explicit non-actions during preparation

This task does not:
- modify `src/**`;
- modify tests or workflows;
- execute the current Core corrective;
- start its Independent Acceptance;
- freeze RC-003;
- run A-004/B/C;
- resume persistence;
- reveal a sealed cursor;
- merge #263;
- modify frozen historical evidence;
- start C16, broad P16, P17, P18 or P19.

## 10. Prepared downstream drafts

Prepared but blocked:

- `governance/prompts/CORE_RC_REFREEZE_003_DRAFT_2026-09-28.md`
- `governance/prompts/C15_RCC_RES_A_RERUN_004_DRAFT_2026-09-28.md`
- `governance/prompts/C15_RCC_PERSONA_CONTINUITY_PREFLIGHT_001_DRAFT_2026-09-28.md`
- `governance/prompts/C15_RCC_RES_C_001_R10_DRAFT_2026-09-28.md`
- `governance/prompts/C15_RCC_EVAL_001_R10_DRAFT_2026-09-28.md`
- `governance/prompts/CORE_RC_REFREEZE_003_INDEPENDENT_ACCEPTANCE_DRAFT_2026-09-28.md`
- `governance/prompts/C15_RCC_RES_A_RERUN_004_INDEPENDENT_ACCEPTANCE_DRAFT_2026-09-28.md`
- `governance/prompts/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003_INDEPENDENT_ACCEPTANCE_DRAFT_2026-09-28.md`
- `governance/prompts/C15_RCC_RES_B_RELEASE_003_DRAFT_2026-09-28.md`
- `governance/prompts/C15_RCC_RES_B_RERUN_003_DRAFT_2026-09-28.md`
- `governance/prompts/C15_RCC_RES_B_ACCEPT_003_DRAFT_2026-09-28.md`
- `governance/prompts/C15_RCC_CLOSE_001_DRAFT_2026-09-28.md`

They are templates, not READY authorizations.

## 11. Exit-readiness verdict

`C15-EXIT-READINESS-001 = REVIEW_READY / PREPARATION_COMPLETE`

This means only that the downstream route has been precomputed and prompt gaps have been reduced.

The unique active engineering task remains unchanged.
