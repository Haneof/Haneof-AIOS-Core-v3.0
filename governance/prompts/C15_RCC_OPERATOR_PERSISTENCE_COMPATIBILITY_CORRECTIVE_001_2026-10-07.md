# WINDOW 49 — C15-RCC-OPERATOR-PERSISTENCE-COMPATIBILITY-CORRECTIVE-001

Formal task:

`C15-RCC-OPERATOR-PERSISTENCE-COMPATIBILITY-CORRECTIVE-001`

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Window:

`49`

Role:

C15 Downstream Operator / Persistence Compatibility Corrective Engineer

You are not PM, Fresh IA reviewer, Core product engineer, Resident, evaluator, release operator, UI/hardware engineer, or merge owner.

## Mission

Adapt the downstream C15 operator/persistence harness to the accepted finalized Core contract after RC004, without modifying Core product code or weakening trusted-return/recovery security.

## Fresh entry

Start with `git fetch --all --prune` and verify live `main` is the PM-integrated RC004 finalization baseline. Do not trust SHAs in this prompt permanently.

Navigation identities at release time:

- accepted RC004 finalization integration merge: `08585f9e0b2ca80cb7eacbb55b5f1c206eb10bcb`
- accepted Corrective-008 head: `8aec087367ead24cb9c0a40d7fd97beb783066cb`
- frozen Core software: `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`

Current `main` may be a governance-only descendant of the accepted integration merge. Before editing, prove `08585f9e0b2ca80cb7eacbb55b5f1c206eb10bcb..origin/main` contains only governance/checkpoint/prompt documentation changes and zero `src/**`, `tests/**`, `tools/**`, package/dependency, or `.github/workflows/**` drift. If any non-governance drift exists, stop for PM adjudication. Construct the Window 49 branch from the fresh verified current `main`.

## Strict scope

Allowed implementation changes:

- `tools/c15_persistence/**`
- `tests/c15_persistence/**`
- dedicated `reviews/C15_RCC_OPERATOR_PERSISTENCE_COMPATIBILITY_CORRECTIVE_001/**`
- dedicated governance/prompt evidence only when needed

Forbidden:

- `src/aios_core/**`
- product tests outside `tests/c15_persistence/**`
- `.github/workflows/core-rc-refreeze-004-formal-gate.yml`
- weakening or bypassing Core trusted-return verification
- reintroducing caller-manufacturable authenticity
- treating Python-private naming as a trust boundary
- turning post-binding attempts into `not_submitted`
- second provider request after durable dispatch/binding
- Resident execution
- self-review
- merge

## RED-first

Before any edit, run the complete fresh C15 persistence/operator suite on live main in the formal supported Python environment. Record exact pytest exit status, pass/fail/error counts, failing nodeids, and JUnit if available.

Historical `45 failed` is navigation only. Do not assume the current failure count.

Classify each fresh failure into a finite matrix such as:

- accepted-Core API/contract adaptation
- stale operator trust/authenticity assumption
- stale recovery-state expectation
- persistence/reattach durability defect
- remote-authority/provenance defect
- resident-surface harness defect
- test/environment-only defect
- real Core regression suspicion

If any failure appears to require a Core product change, STOP and report `CORE_CHANGE_REQUIRED_PM_ADJUDICATION`; do not expand scope.

## Binding semantic rules

The operator layer may persist bytes/state and reattach requests, but may not mint or assert provider-return authenticity.

For a provider boundary crossed without an already durable trusted return, recovery must fail closed: no invented receipt, no caller-supplied trusted bytes, no redispatch, no ACK/progress.

A durable trusted return may be resumed only through accepted Core recovery surfaces and exact proof/verifier semantics.

Preserve exactly-once application, cursor/ACK truthfulness, remote durability provenance, and Resident-visible surface equivalence.

Do not make tests green by restoring an unsafe local trust callback, capability nonce, signing secret, public mint helper, or equivalent authority inside the recovery/operator object graph.

## Required attack/regression matrix

At minimum cover:

1. normal operator run;
2. K1/K2 pre-provider crash recovery;
3. K3 after request dispatch with no durable trusted return -> fail closed;
4. K3_TRUSTED_RETURN_DURABLE -> exact trusted return recovers once;
5. K4/K5 exactly-once application/ACK;
6. restart in a fresh process;
7. local cache wipe + remote materialization;
8. stale/corrupt remote state rejected;
9. wrong run/session/ref provenance rejected;
10. forged/caller-supplied response bytes cannot become trusted;
11. no second request after durable binding;
12. resident-visible request/capability/model surface unchanged;
13. platform/namespace reattach limitations explicitly disclosed rather than simulated as proven.

## Candidate construction

Create a new branch from fresh main:

`c15-rcc-operator-persistence-compatibility-corrective-001-window49`

Do not reuse failed/historical C15 branches.

Create one new PR with title:

`C15-RCC-OPERATOR-PERSISTENCE-COMPATIBILITY-CORRECTIVE-001`

No force push.

Keep engineering commits reviewable; final candidate identity must be explicitly reported.

## Completion gates

Before REVIEW_READY, require:

- fresh C15 persistence/operator suite: zero unexplained failures;
- failure matrix fully adjudicated;
- all security-negative tests above green;
- no `src/aios_core/**` diff;
- no non-C15 product test diff;
- resident-surface no-drift gate non-vacuous;
- remote durability/provenance tests green;
- exact changed-file scope audit;
- fresh full Core regression remains green;
- evidence packet complete;
- PR exact head stable.

If a formal hosted gate exists for this C15 line, run it on exact head. Do not invent a substitute gate.

## Stop boundary

Success:

`WINDOW_49 = COMPLETE`

`C15-RCC-OPERATOR-PERSISTENCE-COMPATIBILITY-CORRECTIVE-001 = REVIEW_READY`

`READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE`

`DO NOT MERGE`

Failure/block:

`WINDOW_49 = BLOCKED`

`PM_ADJUDICATION_REQUIRED`

`DO NOT MERGE`

Never perform Fresh IA or merge inside Window 49.

## Final report

Report at minimum:

- WINDOW / FORMAL_TASK / ROLE
- LIVE_MAIN
- BRANCH / PR
- EXACT_HEAD / DIRECT_PARENT / TREE
- CHANGED_FILES / SCOPE_RESULT
- PRE_EDIT_RED_COUNTS / failing nodeids
- FAILURE_CLASSIFICATION_MATRIX
- CORE_CHANGE_REQUIRED = YES/NO
- TRUST_AUTHORITY_REGRESSION_RESULT
- K1/K2/K3/K3_TRUSTED_RETURN_DURABLE/K4/K5 results
- FRESH_PROCESS_RECOVERY
- REMOTE_WIPE_REATTACH
- PROVENANCE_REJECTION
- NO_SECOND_REQUEST
- RESIDENT_SURFACE_RESULT
- FULL_CORE_REGRESSION
- C15_FINAL_COUNTS
- HOSTED_GATE identity/result if applicable
- FORCE_PUSH_USED = NO
- SELF_REVIEW_PERFORMED = NO
- BLOCKERS
- FINAL_DISPOSITION
