# BLOCKED DRAFT — CORE-RC-REFREEZE-003-INDEPENDENT-ACCEPTANCE

Status: `DRAFT / NOT READY / DO NOT EXECUTE`

Activation:
- exact RC-REFREEZE-003 candidate exists and is pinned;
- author reports REVIEW_READY;
- candidate head is immutable for review;
- task board explicitly releases this IA.

Role:
Independent RC Freeze Acceptance Reviewer.

Freshly verify, do not reuse author conclusions:
- exact candidate SHA/parent/tree;
- frozen software/Core/tests/workflow/package identities;
- zero unauthorized Core drift inside the freeze packet PR;
- source/environment manifest integrity;
- open-PR contamination classification;
- clean install/headless smoke;
- backup/restore/index rebuild;
- writer/restart;
- historical FIX spot checks;
- accepted trusted-return recovery semantics and authenticity;
- exact-replay side-effect matrix remains green;
- full regression;
- no second truth store.

Build at least one independent adversarial probe set, freeze it before execution, preserve every failed harness version rather than rewriting history.

Verify the RC impact adjudication:
`FRESH_A_REQUIRED` unless semantic identity can be mechanically proven.

Verdict:
- `ACCEPTANCE_PASS / blocker=0`
- `ACCEPTANCE_FAIL / blocker=N`
- `REVALIDATION_REQUIRED` if candidate head moves.

Do not merge and do not run Resident.
