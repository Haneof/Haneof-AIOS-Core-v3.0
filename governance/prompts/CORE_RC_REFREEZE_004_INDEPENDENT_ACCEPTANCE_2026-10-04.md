# CORE-RC-REFREEZE-004-INDEPENDENT-ACCEPTANCE

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

WINDOW:

`25`

Role:

**Fresh Independent RC Freeze Acceptance Reviewer**

You are not:
- Window 24 author / Release Engineer;
- PR #325 author;
- Core corrective engineer;
- PM integrator;
- C15 persistence/operator corrective engineer;
- Resident A/B/C;
- evaluator;
- public release operator;
- UI/hardware engineer.

Your only task:

> Independently attempt to falsify PR #325 exact candidate and determine whether it faithfully freezes the accepted post-Corrective-003 software boundary without hidden implementation drift, stale evidence substitution, false-positive gate repair, or downstream-debt laundering.

Do not repair the candidate.
Do not modify PR #325.
Do not merge anything.
Do not run any Resident.

## 0. Fresh start / candidate pin

Start with:

`git fetch --all --prune`

Freshly read:
- live `main`;
- PR #325 metadata/head/diff;
- PR #326 metadata and closure state;
- task board/checkpoint;
- `governance/CORE_RC_REFREEZE_004_ENTRY_DECISION_2026-10-04.md`;
- `governance/prompts/CORE_RC_REFREEZE_004_2026-10-04.md`;
- PR #325 release packet/evidence;
- accepted Corrective-003 integration record;
- Window 23 REVIEW_ONLY evidence PR #321;
- prior RC-REFREEZE-003 IA prompt/report only as historical comparison.

At PM dispatch the required exact candidate is:

PR:
`#325`

head:
`70134269ddfc7c80c4a703a933253bd099746504`

parent:
`b295e6a83b345864b40d6a731fb25812c0ed9ad4`

tree:
`5727143aa14359d67defb41113b46d6759ad7f2e`

branch:
`release/core-rc-refreeze-004-window24`

Expected PR state:
`OPEN / non-draft / UNMERGED / DO NOT MERGE`

If PR #325 head moves:

`REVALIDATION_REQUIRED`

Stop. Do not inherit acceptance to another SHA.

PR #326 must remain:
`CLOSED / UNMERGED / DUPLICATE / SUPERSEDED / NON-CANONICAL`.

If #326 or another RC004 candidate becomes competing/merged, stop for PM adjudication.

## 1. Frozen software identity

The software being frozen is not candidate head #325.

Canonical frozen software:

`1cee3c5ad12f4b9098232bae11b51df786c5eb2f`

Required identity:
- parent 1 `fb53cf938b138a67d1890618eed41282c61bce00`
- parent 2 `7ecb2250a488766915e1042a76472b3cd26d9107`
- repository tree `70b2711258567863ea0d93025a6a07e39631726a`
- `src/aios_core/**` tree `16f1487e291b009c55bee402abfd79fdacbae960`
- `tests/**` tree `9db1bfa08143bc99fe03836e2752ee6e05694eb6`
- frozen workflows tree `72cde9d2dc2b35d071bfa36c954dac2faff4a803`
- `pyproject.toml` blob `b38833c7537fa60d5c2f02ed4bb19158d8995a11`
- constitution tree `c4572dd929ec4d5510b9e08ae29fe9d4cdcf7bf3`
- Core baseline blob `e4af80b8b93d89df8f0229620f870c6d5855c381`

Freshly recompute all identities from Git objects.

Do not trust candidate manifests by inspection.

## 2. Freeze-integrity / candidate-scope attack

Independently prove PR #325:
- does not modify `src/**`;
- does not modify `tests/**`;
- does not modify `tools/**`;
- does not modify `pyproject.toml`;
- does not silently alter package implementation metadata;
- adds only RC freeze workflow, `release/rc/**`, and `reviews/CORE_RC_REFREEZE_004/**`.

Freshly inspect all 22 changed files.

Attack:
- symlink/path tricks;
- generated artifacts embedded under allowed directories;
- executable code in release evidence that could alter tested checkout;
- workflow checkout/ref confusion;
- environment variables or scripts that test a different tree than the declared frozen software;
- evidence probe importing live main instead of frozen software.

If candidate changes the frozen implementation boundary, FAIL.

## 3. Frozen software ↔ live main drift

Freshly compare:

`1cee3c5a...` → current live `main`.

Author claims nine post-software commits and final protected drift = zero.

Do not inherit that claim.

Independently enumerate every commit and path.

Require zero unaccepted drift in:
- `src/**`;
- `tests/**`;
- `pyproject.toml`;
- package implementation metadata;
- existing release-relevant implementation workflows.

Classify PR #321 reviewer evidence and Window 23 publication transport as evidence/transport only.

If any implementation drift is silently omitted from the freeze, FAIL.

## 4. Candidate / synthetic merge equivalence

Build/inspect a synthetic merge of PR #325 into fresh main.

Prove:
- merged `src/aios_core/**` tree equals frozen software Core tree;
- merged `tests/**` tree equals frozen software tests tree;
- package implementation identity is unchanged;
- RC metadata/workflow does not mutate runtime package content;
- formal gate is testing `1cee3c5a...`, not the RC candidate checkout by accident.

If the merge result introduces implementation drift, FAIL.

## 5. Manifest / external-pin two-layer audit

This is a specific independent attack.

The tracked manifest intentionally contains:
- `candidate_sha: null`;
- `candidate_parent: null`;
- `candidate_tree: null`;
- `run_id: null`;
- `status: PENDING_AT_MANIFEST_COMMIT_TIME`.

The final values are published after immutable-head CI in PR body/comment rather than by an evidence-only commit.

Do not automatically PASS or FAIL this design.

Independently adjudicate whether:
- the tracked manifest clearly declares this non-self-referential method;
- the PR body/comment unambiguously pins exact candidate/head/parent/tree/run;
- there is no second candidate/head that can satisfy the same manifest;
- checksums/artifact/evidence can be mechanically tied to `70134269...`;
- the external pin is durable GitHub evidence;
- the method cannot cause a release operator to freeze a stale or different SHA.

If the two-layer design is ambiguous or substitutable, raise a blocker.

## 6. Formal CI identity

Author formal run:

`37213157986`

Freshly verify via GitHub API:
- workflow = `core-rc-refreeze-004-formal-gate`;
- event = `push`;
- run head = `70134269ddfc7c80c4a703a933253bd099746504`;
- conclusion = `success`;
- remote branch head = PR #325 head = run head;
- no commit after run.

Formal environment claimed:
- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2
- SQLite 3.45.1
- OpenSSL 3.0.13
- Ubuntu 24.04.5 LTS
- kernel 6.17.0-1022-azure
- x86_64

Do not treat formal GREEN as independent acceptance.

## 7. Formal workflow audit

Read the full RC004 workflow.

Attack:
- checkout/ref substitution;
- testing live main instead of frozen software;
- testing candidate tree instead of frozen software;
- stale cached environment;
- author evidence substituted for fresh execution;
- grep/textual checks that can false-positive or false-negative;
- `continue-on-error`, ignored shell exit codes, pipes without `pipefail`;
- conditional steps that skip on common execution paths;
- environment assertions made from prose instead of runtime;
- artifact created before all binding checks finish;
- commit comment claiming success after a failed binding step;
- permissions that allow evidence/candidate mutation;
- token exposure to executed probe code;
- mutable branch/reference inputs after exact-head pin.

Any false-green route is a blocker.

## 8. Preserved RED adjudication — do not inherit author's labels

Preserved runs:
- `37210518501`
- `37210904177`
- `37211071106`
- `37211714127`

Author classifies them as release-gate / stale-probe defects rather than Core RED.

You must independently inspect/reproduce the failure conditions.

For each RED report:
- exact head;
- exact failing assertion;
- what software/evidence it exercised;
- whether the old expectation was actually invalid under accepted Corrective-003;
- whether the replacement probe tests an equal-or-stronger release property;
- whether any real safety property was weakened merely to make the gate green.

Especially attack:
- RC003 backup probe expectation that local handler return creates trusted receipt;
- RC004 probe expectation of retired `background_model_authenticity_authority`;
- textual live_return import scan.

If any “probe defect” classification hides a real accepted-Core regression, FAIL.

## 9. Reviewer probes — fresh extraction

Do not use author-carried copies.

Freshly extract from canonical review commits.

### Window 20 Suite A

review:
`220311759e88fb3948ad3f4dba655058e0f392a8`

blob:
`527edd8d92243cabc417f176c0f7c4f6c358e65c`

SHA-256:
`ec1dc5c2c5406d5d9e74825f62e0a17fb80f8ebd6dc250817fa048511ce292b5`

### Window 20 Suite B

blob:
`867f0ee993595c2d334a3940ad66308166693c97`

SHA-256:
`769242465817f31734661ba7ba9c3d5f7d06b8d3f5235d72d2026956d9b98eb1`

### Window 17

review:
`e4161dd0ad0a2f825461311a1c8c5ff8234a07f8`

blob:
`bb25d184a5cb813ae4058de9a75fa23d9591b041`

SHA-256:
`a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3`

Hash mismatch:
`REVIEWER_PROBE_IDENTITY_MISMATCH`

Stop.

Freshly run on frozen software target.

Expected accepted baseline:
- Suite A 4/0
- Suite B 7/0
- W17 14/0

But GREEN is only a minimum bar.

## 10. Reviewer-owned attacks

Before first execution of your own attack suite:
- author reviewer probes;
- freeze source/hash/enumeration;
- preserve revisions;
- do not tune expectations after seeing candidate behavior.

Attack beyond the author RC gate.

At minimum:
- alternate trusted-return mint writers;
- reflection/object graph;
- tombstone re-entry;
- external-proof supersession;
- proof transplant/canonicalization;
- backup/restore authority expansion;
- partial receipt/handoff/staging state;
- first-writer exactly-once race;
- restored/copied World replay;
- verifier-less fail-closed;
- writer/restart cross-process boundary;
- package clean-install import identity.

## 11. Fresh full Core regression

Fresh reviewer run at minimum:

`tests/unit tests/integration tests/runtime tests/habitation`

Goal:
`0 fail / 0 error`

Author formal count:
`928 passed`

Do not infer 928 from collection counts only; run the suite.

If reviewer environment differs from formal 3.12.14, state:
`REVIEWER_ENVIRONMENT_DEVIATION`.

Do not fake exact fidelity.

## 12. Corrective-003 security freeze independent attack

Freshly verify:
- no caller-manufacturable local trusted-return authority;
- `live_return.py` remains inert and not consulted by authorization;
- sole trust root is gated on durable external verifier + genuine proof;
- stage path cannot originate authority;
- verifier-less ambiguous recovery cannot become trusted;
- forged local provenance cannot poison later genuine proof;
- exact genuine replay idempotent/effect-free;
- changed/conflicting proof fails closed;
- bound-field transplant refused;
- exactly-once meter/effect preserved.

Do not rely only on author `214 passed`.

## 13. Real process loss

Freshly perform real process-loss/hard-restart coverage.

Prove:
- no provider duplicate;
- no meter duplicate;
- no capability duplicate;
- exact durable work converges or fails closed correctly.

Do not substitute ordinary exceptions for process loss.

## 14. Clean-install/headless

From reviewer-controlled clean checkout:
- build wheel;
- non-editable install;
- run `aios-core-headless`;
- create disposable World;
- deterministic mechanical turn;
- stop/restart same World;
- continuity;
- safe recovery status;
- clean close.

No Resident fixture.
No real provider required.

Independently record `aios_core.__file__`.

## 15. Backup / restore / index rebuild

Do not simply rerun the author probe.

Reviewer-owned attack must include:
- genuine external verifier/proof;
- receipt/handoff durable;
- crash/partial state before staging;
- supported backup;
- restore to new path;
- source backup immutability;
- index rebuild;
- exact winning proof retry;
- conflicting proof refusal;
- forged/local proof refusal;
- no provider redispatch;
- no duplicate meter/effect;
- restored state does not widen authority.

Attack copied/cloned database and stale verifier-consumption states.

## 16. Writer / restart / historical FIX

Freshly verify:
- same-World writer exclusion;
- stale lock/restart;
- lock-path override cannot create second writer;
- FIX-001 cutoff;
- FIX-002 ambiguous background dispatch;
- FIX-003 ambiguous user turn;
- current-time control;
- no second World/cognition truth store;
- bounded SCALE semantic equivalence.

## 17. C15 downstream classification — independent challenge

Author fresh C15 subset result:
`45 failed / 33 passed`

Author ruling:
`CORE_FREEZE_NOT_BLOCKED_BY_DOWNSTREAM_OPERATOR_DEBT`

`C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT`

Do not inherit this classification.

Freshly run/inspect downstream failures.

For every failure class determine:
- path;
- whether failure is caused by retired local self-trust assumption;
- whether it exposes a real Core safety/correctness regression;
- whether a normal supported Core API contract was broken unintentionally;
- whether restoring old local trust would be unsafe.

If any downstream failure mechanically proves the accepted frozen Core itself is wrong, RC freeze FAILS.

If failures are genuinely operator/harness compatibility debt, preserve them and PASS this section without fixing them.

No C15 repair in this window.

## 18. RC impact adjudication

Independently adjudicate:

`FRESH_A_REQUIRED`

and:

`FRESH_OPERATOR_PREP_REQUIRED`

Do not allow A-003/A-004 hash swap unless you can mechanically prove Resident-visible/execution semantics are identical.

Given Corrective-003 trust semantics changed, burden of proof is on reuse.

Do not run Resident.

## 19. Open PR / branch contamination

Fresh inventory of all open PRs/branches touching implementation/release surfaces.

At minimum classify:
- #310 historical failed;
- #311 historical REVIEW_ONLY;
- #321 Window 23 REVIEW_ONLY;
- #325 exact RC candidate;
- #326 closed duplicate/noncanonical;
- Window 23 publication staging/publisher;
- historical C15 WIP/drafts;
- any new PR.

No competing unaccepted implementation may be silently included.

## 20. Manifest/checksum/artifact audit

Independently recompute:
- `release/rc/CORE_RC_REFREEZE_004_MANIFEST.json` consistency;
- `source_manifest.json` Git object identities;
- `SHA256SUMS`;
- evidence file coverage;
- workflow blob identity.

Formal artifact:
- ID `11307078611`
- name `core-rc-refreeze-004-evidence`
- server digest `sha256:8c14ab631b361c57d5292fd94f6fde3755a215ed974d408574fa65c9b2bd4c7b`

If downloadable, independently inspect content and recompute digest/content hashes.

If artifact download is unavailable, do not pretend possession. Determine whether committed evidence + GitHub metadata is independently sufficient and disclose limitation.

## 21. Known limitations

Verify packet does not erase limitations merely to make RC look stronger.

At minimum preserve:
- direct `record_response` inherited residual boundary;
- no distributed multi-host HA claim;
- downstream C15 compatibility debt;
- no public release/tag;
- historical Resident evidence invalid for this RC;
- formal runtime authority tied to exact-head hosted run.

A missing material limitation can be a blocker.

## 22. Candidate immutability

Throughout review, repeatedly verify PR #325 head remains:

`70134269ddfc7c80c4a703a933253bd099746504`

If drift:
`CANDIDATE_DRIFT / REVALIDATION_REQUIRED`

Stop.

## 23. Review evidence publication

A chat verdict is not sufficient acceptance evidence.

Publish reviewer evidence on a separate:

`REVIEW_ONLY / DO NOT MERGE`

branch/PR.

Must include:
- report;
- reviewer-owned probes;
- frozen probe hashes/enumeration;
- raw outputs;
- environment record;
- exact review commit identity.

Do not commit review evidence onto PR #325 branch.

If write publication is unavailable after technical review:
- preserve exact local review commit;
- export exact git bundle + SHA-256;
- report `EVIDENCE_PUBLICATION_BLOCKED`;
- do not redo IA.

## 24. Verdict

### PASS

Only if the exact candidate faithfully freezes the accepted software boundary and all binding checks pass:

`ACCEPTANCE_PASS`
`blocker=0`
`READY_FOR_PM_INTEGRATION`

Do not merge.

### FAIL

`ACCEPTANCE_FAIL`
`blocker=N`
`CORRECTIVE_OR_ADJUDICATION_REQUIRED`

Every blocker must give:
- ID;
- severity;
- violated invariant;
- exact path/source;
- reproduction;
- expected;
- actual;
- why author gate missed it;
- independently reproducible = yes/no.

Do not repair.

### Candidate drift

`REVALIDATION_REQUIRED`

## 25. Prohibitions

Do not:
- modify or merge PR #325;
- reopen/merge #326 as candidate;
- repair Core;
- repair C15;
- perform PM integration;
- run Resident A/B/C;
- enter evaluator;
- create public tag/release;
- do UI/hardware work.

Stop after durable Fresh IA publication.

## 26. Final report

Report:
- fresh live main;
- PR #325 state/head/parent/tree;
- frozen software identities;
- candidate scope audit;
- post-integration drift;
- synthetic merge equivalence;
- manifest/external-pin ruling;
- formal CI identity;
- workflow security/false-green audit;
- four preserved RED rulings;
- canonical frozen probe hashes/results;
- reviewer-owned attacks;
- full Core regression;
- environment;
- Corrective-003 security ruling;
- real process loss;
- clean install/headless;
- backup/restore/rebuild;
- writer/restart/FIX;
- C15 downstream ruling;
- RC impact ruling;
- contamination review;
- checksum/artifact audit;
- candidate drift check;
- exact review evidence identity/publication;
- final verdict;
- blocker count.

Then stop.

DO NOT MERGE.
