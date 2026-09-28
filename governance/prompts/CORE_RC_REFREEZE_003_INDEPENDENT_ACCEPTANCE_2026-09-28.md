# CORE-RC-REFREEZE-003-INDEPENDENT-ACCEPTANCE

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Role:

**Independent RC Freeze Acceptance Reviewer**

You are not:
- PR #269 author;
- Release engineer;
- PM integrator;
- Resident A/B/C;
- persistence engineer;
- final semantic evaluator.

Your only task:

> Independently attempt to falsify the exact RC-REFREEZE-003 candidate and determine whether it faithfully freezes the accepted post-Corrective-001 software boundary without hidden implementation drift or evidence substitution.

Do not repair the candidate.

Do not merge anything.

## 1. Fresh start

Fresh-fetch:
- live `main`;
- PR #269 metadata/head/diff;
- exact candidate commit;
- formal gate runs;
- current task board/checkpoint;
- Corrective-001 integration receipt;
- prior RC-REFREEZE-002 acceptance/integration evidence;
- PR #269 evidence packet.

At dispatch, expected candidate:

- PR #269
- exact head: `6f95431036dd0304947d67ec4a8de7229d1d3ba9`
- first parent: `f2ef4886cbd7253543e82debbaa14ea387417f03`
- tree: `a43a761ac3570dfc4aab296818310068f877e881`
- intended frozen software: `f20f2edfa7af00d0286493fd15196ca9503bc315`

If PR #269 head moved, return:

`REVALIDATION_REQUIRED`

Do not inherit acceptance to another SHA.

## 2. Freeze-integrity review

Independently prove:
- candidate does not modify `src/aios_core/**`;
- candidate does not modify `tests/**`;
- candidate does not modify package implementation metadata in a way that changes the frozen software;
- candidate only adds freeze evidence/release metadata/release workflow;
- frozen software `f20f2edf...` is the software actually tested;
- current main drift after `f20f2edf...` is governance/evidence-only or explicitly adjudicated;
- no implementation commit after the accepted Core merge is silently omitted from the freeze.

Mechanically compare:
- frozen software;
- current main;
- candidate head;
- synthetic merge-ref if available.

## 3. Candidate/merge-ref equivalence

Build or inspect the PR merge ref.

Prove:
- merge-ref `src/aios_core/**` tree equals the frozen software Core tree;
- merge-ref `tests/**` tree equals the frozen software tests tree;
- package implementation identity remains equivalent;
- the formal gate is not accidentally testing some other checkout/tree.

If merge-ref introduces implementation drift, FAIL.

## 4. Manifests and checksums

Independently verify:
- `release/rc/CORE_RC_REFREEZE_003_MANIFEST.json`;
- `reviews/CORE_RC_REFREEZE_003/source_manifest.json`;
- `reviews/CORE_RC_REFREEZE_003/environment_manifest.txt`;
- `reviews/CORE_RC_REFREEZE_003/SHA256SUMS`.

Recompute file hashes and tree identities.

Do not trust committed checksum files by inspection alone.

Any stale hash, wrong tree, missing file, or unresolvable Git object is a blocker unless proven non-material by explicit contract.

## 5. Formal environment

Use:
- CPython 3.12.14;
- Pydantic 2.13.5;
- pytest 8.4.2;
- record actual SQLite version;
- record OS/kernel/architecture.

If the exact environment cannot be provisioned, disclose it and determine whether independent hosted evidence can close the gap. Do not pretend equality.

## 6. Fresh independent regression

Do not treat run `36437699641` as independent acceptance.

Freshly run at minimum:
- complete repository pytest;
- trusted-return/recovery focused suites;
- capability replay/fail-closed/authenticity/transplant/corruption;
- world-kernel/index;
- Wake;
- Periodic Review;
- C14 runtime/scheduler/loop;
- cognition revision/policy;
- headless/recovery;
- bounded SCALE semantic-equivalence.

Freeze any reviewer-authored probes before first candidate execution and preserve their hashes/history.

## 7. Registry/replay surface

Independently enumerate the runtime capability registry.

Verify the actual reachable side-effecting surface.

Author claims:
- 43 total model-callable;
- 22 side-effecting.

Do not trust these counts.

If your independent inventory differs, explain and adjudicate.

For the side-effecting set, verify the accepted exactly-once recovery properties remain intact.

## 8. Trusted-return spot checks

On the frozen software target verify:
- exact authenticated replay converges exactly once;
- same-key changed request fails closed;
- tampered durable handoff bytes fail before capability application;
- authority cannot be widened by freeze tooling;
- relation/policy request-identity semantics remain legal;
- request fingerprint and expected-world-revision semantics remain intact;
- stronger terminal/output receipts still short-circuit duplicate work.

## 9. Real recovery/process-loss

Freshly exercise at least one real process-loss or hard-restart path sufficient to show:
- provider work is not duplicated;
- metering is not duplicated;
- capability side effect is not duplicated;
- logical work converges.

Do not substitute an in-process exception for process loss without disclosure.

## 10. Clean-install headless

From a clean checkout/install:
- build wheel/non-editable package;
- install;
- verify `aios-core-headless`;
- create disposable World;
- deterministic mechanical turn;
- stop;
- restart same World;
- verify continuity;
- exercise one safe recovery-status path.

No Resident fixture.
No hidden semantic oracle.
No real provider required.

## 11. Backup / restore / rebuild

Freshly verify:
- supported World backup;
- restore to a new path;
- source backup immutability;
- World/object/operation/recovery state preserved;
- index rebuild works;
- trusted-return authority/receipt state survives supported backup/restore;
- no second truth store is created.

## 12. Writer / restart

Freshly verify:
- canonical same-World writer exclusion;
- lock-path override cannot create another writer;
- clean stop releases lease;
- stale lock metadata does not prevent legal restart;
- restarted World does not redispatch already durable work.

## 13. Open-PR contamination

Freshly inspect open PRs and branches touching:
- `src/**`;
- `tests/**`;
- release workflows;
- package metadata;
- RC/recovery/runtime surfaces.

Explicitly classify at least:
- #258 historical failed candidate;
- #261 review-only failed IA;
- #263 persona-governance draft;
- #265 C15 exit-readiness draft;
- #269 current candidate;
- old persistence WIP/review-only branches;
- any newly opened PR.

Do not merge or import competing work.

## 14. Hosted artifact claim

The author states hosted artifact:
- run: `36436264055`;
- name: `core-rc-refreeze-003-36436264055`;
- server-reported SHA-256: `783b04438acbb982b584c3b6457727604d45695558a46f7d12a3574399bacb71`.

Independently inspect the Actions metadata.

If you can download it, verify content and hashes.

If the sandbox cannot download it, do not treat that as automatic failure if:
- committed evidence is independently reproducible;
- checksums are recomputed;
- hosted metadata is consistent;
- no claim of local possession is made.

Record the limitation explicitly.

## 15. RC impact adjudication

Independently adjudicate:

`FRESH_A_REQUIRED`

The prior A-003 lineage belongs to the prior RC.

Do not permit hash-swapping A-003 onto the new RC unless you can prove complete Resident-visible/execution semantic equivalence.

Given the accepted trusted-return recovery/replay change, the burden of proof is on reuse.

Do not run A-004 in this window.

## 16. Known limitations

Verify that the RC packet preserves relevant limitations rather than deleting them to make the RC look stronger.

At minimum inspect:
- trusted-store authority threat boundary;
- SCALE caveats;
- no public hardware/UI claims;
- no distributed HA claim;
- unknown provider/token cost where not measured;
- no claim that C15 is complete.

## 17. Required durable report

Create review-only evidence.

Report:
1. review-time live main;
2. exact candidate head/parent/tree;
3. merge-ref identity;
4. frozen software/Core/tests trees;
5. reviewer probe hashes/enumeration;
6. manifest/checksum verification;
7. fresh regression;
8. registry inventory;
9. trusted-return attacks;
10. real recovery/process-loss;
11. clean install/headless;
12. backup/restore/rebuild;
13. writer/restart;
14. contamination review;
15. artifact limitation/verification;
16. RC impact adjudication;
17. environment;
18. blocker count;
19. final verdict.

Preserve every reviewer harness revision and every RED.

## 18. Verdict

Choose exactly one:

### `ACCEPTANCE_PASS / blocker=0`

Only if the exact candidate faithfully freezes the accepted software boundary and all binding checks pass.

If PASS, state:

`READY_FOR_PM_INTEGRATION`

### `ACCEPTANCE_FAIL / blocker=N`

If any binding defect remains.

### `REVALIDATION_REQUIRED`

If candidate head moved.

Do not merge PR #269.

Do not run A-004.

Do not resume persistence.

Do not enter Resident B/C, evaluator, or C15 close.
