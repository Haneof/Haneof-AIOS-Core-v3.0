# INDEPENDENT ACCEPTANCE REPORT

Task: `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`
Role: **Independent Core Runtime Recovery Acceptance Reviewer**
Repository: `Haneof/Haneof-AIOS-Core-v3.0`
Reviewer suite: `reviews/CORRECTIVE_001_IA2/` (review-only; nothing added to PR #264)

---

## FINAL VERDICT

# `ACCEPTANCE_PASS / blocker=0`

# `READY_FOR_PM_INTEGRATION`

PR #264 was **not** merged, repaired, or integrated. No RC-REFREEZE, A-004,
persistence Corrective-003, Resident B/C, evaluator, or release work was started.

---

## 1. Review-time live main

Freshly fetched this session (`git fetch origin --prune`):

```
live main = 0df757e9666c2c75571df7a7a3dedf27d44e5b7f
```

This matches the PM-dispatched value, but was re-derived, not inherited.

**Note on the initial fetch:** the sandbox clone was **shallow** — `.git/shallow`
contained `0df757e`. The first `git merge-base <candidate> origin/main` returned
*empty*, which would have looked like a broken lineage. It was a clone artifact.
After `git fetch --unshallow`, `is-shallow-repository` = `false` and the real
merge-base resolved to `5288822`. All lineage conclusions below are from the
full history.

## 2. Exact candidate identity

| field | expected | measured | |
|---|---|---|---|
| PR #264 head | `a73e186d40688f5dc181b1128a62eff37a974409` | `a73e186d40688f5dc181b1128a62eff37a974409` | MATCH |
| parent | `71f6d106a697b0c61410d42114545f2645e12510` | `71f6d106a697b0c61410d42114545f2645e12510` | MATCH |
| tree | `352f47ac4e3098b10b1b78e4757543477371548d` | `352f47ac4e3098b10b1b78e4757543477371548d` | MATCH |

**No drift. `REVALIDATION_REQUIRED` not triggered.**

## 3. Reviewer probe SHA-256 (frozen before candidate execution)

`evidence/SHA256SUMS.probes` — 16 frozen files. The executed revisions:

```
f33bfa33649e9b13f0ac884acf71dc3e4a1a9d76b0919d91b543ed12411c429b  rev10_inventory_and_replay.py.frozen
0b43e4806db5e2d08c09ca1bff9853b1541777358b5bc933acb6b313acf17040  rev2_trust_and_store.py.frozen
5945972941727f410b13cc4327f93452a64121002946b1c9e2969758fc15905c  rev1_process_loss.py.frozen
bb2ed9e93bed68efcd835844af4b1e6faa6d5c239a49c0f59cd98ab9f216211e  rev2_enumerate_independent.py.frozen
3229bbb6bf5afb3809c2148f38415bea0f426d1659090a7f9256499c3a048546  runner.sh.frozen
```

rev1…rev9 of the inventory/replay probe are all preserved; none was overwritten.
Every revision was a **harness** correction (wrong `ObjectType` names, seed calls
passing kwargs instead of a dict, invalid enum literals, an over-strict wording
assertion). **No expected outcome was ever weakened to match observed candidate
behaviour.** Where a probe asserted the wrong contract, the correct contract was
established from the code first (see §8, `commit_or_replay`).

## 4. Frozen static enumeration

`evidence/collect_only_frozen.txt`:

```
tests/reviewer_ia2/test_ia2_inventory_and_replay.py: 63
tests/reviewer_ia2/test_ia2_process_loss.py:          3
tests/reviewer_ia2/test_ia2_trust_and_store.py:      20
                                          total:     86
```

Frozen and hashed **before** the first candidate execution.

### A methodology defect this review caught in itself

The first 60-probe run reported **60 failures** against the candidate. They were
fake. The probe files live under the main repo tree, so pytest walked up and used
**the main repo's** `pyproject.toml`, whose `pythonpath = ["src"]` resolved
`aios_core` to `/home/user/Haneof-AIOS-Core-v3.0/src` — the live-main checkout,
which does **not** contain the corrective (`replay_exact_operation` absent).

A plugin that printed `aios_core.__file__` exposed it:

```
WITHOUT guard: /home/user/Haneof-AIOS-Core-v3.0/src/aios_core/__init__.py   has replay_exact_operation: False
WITH    guard: /home/user/wt/candidate/src/aios_core/__init__.py            has replay_exact_operation: True
```

`runner.sh` now copies probes into the target worktree and runs with that
worktree's own inifile, and `test_z00_probes_execute_the_intended_tree` fails the
run if the loaded `aios_core` is not the intended checkout. Had this gone
unnoticed, this review would have reported a false `ACCEPTANCE_FAIL`.

## 5. Historical baseline RED

`evidence/baseline_RED_against_1ebf51c4.txt`, `evidence/baseline_RED_parts2_3_against_1ebf51c4.txt`

Reviewer suite vs failed exact `1ebf51c4cb905e2a2578a09b64007b50bca0d4ac`:
**50 failed / 36 passed**. Against the candidate: **0 failed / 86 passed**.

The five required prior IA RED families all reproduce:

```
propose_goal               RED      form_event               RED
propose_entity             RED      propose_dimension        RED
propose_cognitive_policy   RED
```

Revision-advancing duplicate/rejection families also RED:

```
upsert_relation  update_cognitive_policy  rollback_cognitive_policy
transition_goal  transition_task  transition_dimension  transition_event
revise_claim     revise_entity    propose_action  record_communication_experience
retract_claim    form_event
```

**Real process-loss RED** (the strongest single result) — `wake` +
`upsert_relation` after a real SIGKILL:

```
E  AssertionError: recovery produced a SECOND durable relation revision
E  assert [('relation_b...a0a64ba1', 2)] == [('relation_b...a0a64ba1', 1)]
E    Left contains one more item: ('relation_b03afb5d939f3f3ea0a64ba1', 2)
```

That is `IA-BLK-TRUSTED-RETURN-001` reproduced independently under real process
death. On the candidate the same probe converges at revision 1.

Trusted-return authenticity negative controls (`test_d1`–`test_d6`) **pass on
both** #258 and the candidate — see §9.

## 6. Complete side-effecting registry inventory

Independently derived (`evidence/independent_enumeration.json`). The reviewer did
**not** take the author's `side_effecting` flag on trust:

```
model_callable                    : 43
declared side_effecting           : 22
runtime authorize allowlist       : 22
declared XOR authorize allowlist  : []      <- exact agreement
```

The authorize allowlist was parsed out of the real
`FusedTurnRuntime._authorize_side_effect` source plus the module constant
`_C14_COGNITIVE_SIDE_EFFECT_ALLOWLIST`, not re-typed.

The author's "43 model-callable / 22 side-effecting" claim is **confirmed**.

**Why the reachability argument is sound:** the enforcement gate is
`cognitive_runtime.py:447` — `if spec is not None and spec.side_effecting:`. It
keys on the *declared* flag, so a capability that wrote durably while declared
read-only would bypass authorization entirely. `test_a2` therefore measures it
rather than declaring it: it invokes all 21 read-declared capabilities with real
arguments and asserts the durable digest is unchanged. Result: none writes.
`test_a3` is the converse control — every one of the 22 declared writers must
measurably change durable state, so `test_a2` cannot be vacuously green.

(An earlier static whole-program call-graph classifier was built first; it
over-approximated to 42/43 and was replaced by this measurement.)

## 7. Exact replay results — all 22 reachable side-effecting capabilities

For each: seed → apply once durably → **unrelated later World revision** inside
the crash window → brand-new runtime → identical recovered invocation.

Asserted per capability: convergence; no provider redispatch (the runtime's
handler raises if called); identical durable digest; unchanged World revision;
no added operation row; no changed idempotency record; no second object
revision; and (`test_b2`) the replay must report the **same** durable identities
as the original, not freshly minted ones.

**22/22 pass**, covering create / revise / transition / register / relation /
policy / communication / experience / cognition-revision families.

## 8. rev5 → rev6 independent adjudication

### A. Was rev5's expectation part of the binding recovery contract?

The decisive mechanical fact, read from the code:

```
src/aios_core/world_graph.py    idempotency_key=f"relation-upsert:{relation_id}:{identity[:24]}"
src/aios_core/policy/service.py idempotency_key=f"policy-update:{object_id}:{update_identity[:24]}"
src/aios_core/policy/service.py idempotency_key=f"policy-rollback:{object_id}:{rollback_identity[:24]}"
```

where `identity = canonical_request_identity(...)` = SHA-256 over the **complete
canonical request**. The durable key for these three *is a function of the
request*. A changed request therefore **cannot** land on the same key — the
"same-key conflict" scenario rev5 specified is unreachable by construction for
exactly these three. rev5 derived those rows from the pre-corrective
state-derived schemes (`relation-upsert:{id}:{revision}`,
`policy:{id}:{revision}`), which are themselves the defect under correction.

For the other capabilities the key is state-independent (`{object_id}:1`,
`{experience_id}`, …), so a changed request *does* share the key — and those
still fail closed. Measured (`evidence/rev5_rev6_changed_field_matrix.txt`):

```
propose_entity          canonical_name   FAIL CLOSED    new revisions: 0
revise_entity           reason           FAIL CLOSED    new revisions: 0
revise_claim            reason           FAIL CLOSED    new revisions: 0
retract_claim           reason           FAIL CLOSED    new revisions: 0
transition_goal         reason           FAIL CLOSED    new revisions: 0
transition_task         reason           FAIL CLOSED    new revisions: 0
transition_dimension    reason           FAIL CLOSED    new revisions: 0
transition_event        reason           FAIL CLOSED    new revisions: 0
upsert_relation         confidence 0.9   ok -> NEW key  new revisions: 1
update_cognitive_policy current_value    ok -> NEW key  new revisions: 1
rollback_cognitive_policy reason         ok -> NEW key  new revisions: 1
```

For the three that succeed, the reviewer verified mechanically:

```
created keys             : ['relation-upsert:relation_5a76...:7c7b08ed6d2e239d342445b3']
key reuse (must be empty): []
original revs intact     : True
new revisions            : [('relation_5a76779997ebcf2fb9b06261', 2)]
reused_existing flag     : False
```

Zero key reuse, original operation/idempotency/object rows byte-intact, a new
revision rather than a silent overwrite, and the receipt reports
`reused_existing=False` — it does not claim to be the original. That is the
upsert / policy-version contract these capabilities already documented via
`RelationReceipt.reused_existing` and `CognitivePolicy.previous_version` /
`rollback_pointer`.

### B. Can a real recovery path present changed arguments as the same call?

No. Recovered bytes come only from `background_model_return_handoffs`, written
in the **same transaction** as the HMAC receipt at the trusted provider-return
callback. `_receipt_message` binds `payload_sha256` into the HMAC.
`test_d1` rewrites the directive arguments in that durable row; recovery fails
closed **before any capability application**:

```
BackgroundModelResponseConflict: trusted provider-return receipt does not bind
the exact attempt, request, provider identity, and response bytes
```

### C. The four concepts, tested separately

| concept | required | measured | probe |
|---|---|---|---|
| 1. same durable key + changed request | FAIL CLOSED, zero writes | `IDEMPOTENCY_CONFLICT`, digest unchanged | `test_c1`, `test_c1b`, `test_e2`, `test_e3` |
| 2. same trusted recovered attempt + changed directive args | fail **before** capability application | binding rejection, no application | `test_d1` |
| 3. same `call_id` + changed args | independently classified | **correlation only** — no authority | `test_c2` |
| 4. changed args → new canonical request identity | legal new operation *iff* the domain allows | new key + new revision, original intact | `test_c4` |

**`call_id` was classified from the code, not from the author's description.**
It occurs 17 times in `src/`, all pass-through (`capabilities.py` field +
results, `cognitive_runtime.py` error results, `turn_runtime.py:1257`
serialization, `background_attempt.py` directive decode). It appears **zero**
times in `storage/idempotency.py`, and an AST scan of every `idempotency_key=`
keyword in the tree found no `call_id` contribution. Behaviourally, two
different `commit_claim` requests sharing one `call_id` both succeed with
different `claim_id`s, and a third capability under the same `call_id` is
unaffected. `call_id` is neither durable identity nor authorization.

**On the store-layer contract, one reviewer probe was wrong and was corrected
from the code, not from the candidate's behaviour.** `commit_or_replay()`
deliberately ignores caller-supplied objects and replays the originally
committed ones — that is what lets an identical recovered replay converge after
the world advanced. Verified separately:

```
commit()          changed objects, same key -> IDEMPOTENCY_CONFLICT / request_fingerprint_mismatch, durable unchanged
commit_or_replay() changed objects, same op -> replayed=True, durable unchanged, caller bytes NOT in durable state
```

So the fingerprint contract is intact at `commit()`, and the replay path neither
writes nor leaks. The probe was split into both assertions (`test_e3`).

### D. VERDICT

# `LEGITIMATE_HARNESS_CORRECTION`

Not `PROHIBITED_EXPECTATION_WEAKENING`. Grounds, each independently established:

1. rev5's three rows were derived from the state-derived key schemes that *are*
   the defect; the scenario they specified is unreachable under the corrected
   contract.
2. The binding recovery safety property is unchanged and now enforced at a
   single stronger layer (the store), proven by 13 independent fail-closed
   probes rather than by the three reclassified rows.
3. Authenticated exact recovery **cannot** pass a changed directive as the
   original replay — the HMAC binds `payload_sha256` (§8.B).
4. A changed request never overwrites and is never reported as the original:
   zero key reuse, byte-intact originals, new revision, `reused_existing=False`.
5. Governance integrity: rev5 is preserved verbatim
   (`15bc7a93ad7e0d2386c89bb665ad081af9ba4185caad65a9dde2853b3b616488`,
   re-hashed by the reviewer); `diff rev5 rev6` shows **only** those three rows
   moving class plus a docstring; the live test file hashes to rev7
   (`835f2740008b22116957aeea925b1552241c97992481bd1fc50c1efe75f96561`).

## 9. Trusted-return trust-boundary attacks

`test_d0`–`test_d6`, all pass on the candidate.

| attack | result |
|---|---|
| recovery entry point accepts caller bytes | impossible — `_pending_exact_response(self, work_kind, work_id)`; `recover_trusted_handoff(self, subject_id, work_kind, work_id)`; no `directive`/`payload`/`proof` parameter |
| tampered directive args in durable handoff | fail closed, binding rejection, before application |
| tampered `payload_sha256` | fail closed |
| cross-work receipt transplant | fail closed |
| provider-identity transplant | fail closed |
| missing authenticity proof | fail closed |
| receipt not bound to payload/attempt | re-capturing different bytes for one attempt conflicts; original proof unchanged |

**These pass on #258 as well.** That is the expected and important result: #258
already contained the trusted-return handoff (`recover_trusted_handoff` and
`background_model_return_handoffs` are both present at `1ebf51c4`), and the
corrective left it untouched. **Trusted-return authority was not widened.**

## 10. Storage replay fail-closed matrix

`test_e1`–`test_e13`, 13/13 pass:

identical request → original result, zero writes · same key + changed request →
`IDEMPOTENCY_CONFLICT` · changed objects → `request_fingerprint_mismatch` ·
unused key → read-only · missing committed object revision →
`replay_object_missing` · corrupt committed payload → fail closed · corrupt
idempotency result → `corrupt_idempotency_result` · operation/idempotency skew →
`operation_idempotency_skew` · missing idempotency record → fail closed ·
reused operation identity under another key → fail closed ·
`expected_world_revision` still in `request_fingerprint` (asserted from source,
along with the other seven fingerprint fields) · replay never persists
caller-supplied objects · unrelated later World revision does not break replay.

All 13 are RED on #258 (the helpers do not exist there).

## 11. Real process-loss results

`test_ia2_process_loss.py` — reviewer-chosen families, deliberately different
from the author's three:

| mode | capability | child death | result on candidate |
|---|---|---|---|
| `wake` | `upsert_relation` | `exitcode == -SIGKILL` | converges, exactly one relation revision |
| `user_turn` | `revise_entity` | `exitcode == -SIGKILL` | converges, exactly one entity revision |
| `periodic_review` | `propose_dimension` | `exitcode == -SIGKILL` | converges, exactly one dimension revision |

Each child runs a **real** model round through the real entry point
(`run_wake` / `run_turn` / `run_periodic_review`), lets the real handler commit
durably, then `os.kill(os.getpid(), SIGKILL)` before outer completion. The
parent asserts the child really died to SIGKILL, reopens the same World in a new
runtime, replays the identical authenticated recovered directive, and asserts no
second object revision and no second operation for the recovered capability.

One reviewer assertion was over-strict and was corrected: recovery legitimately
adds its **own** outer-completion operations (`conversation.commit_assistant_output`,
`wake.dispatch.completed`, `review.complete`). The probe now asserts the
meaningful property — no pre-existing operation row lost or mutated, and no
added row reusing an existing idempotency key or re-creating the recovered
capability's operation.

`wake` + `upsert_relation` is RED on #258 with a duplicate relation revision 2
(§5). These are real process kills, not exception simulation.

## 12. Full regression

Freshly run in the candidate worktree:

```
candidate-native suite : 919 passed in 215.89s
reviewer adversarial   :   86 passed
combined               : 1005 passed in 267.34s
```

`919` independently reproduces the author's claimed count. The author's 919 /
111 / 83 / 17 / 3 / 23-CI figures were treated as historical context only; every
number above is this reviewer's own execution.

## 13. Environment — including a real deviation

```
python        : 3.11.2  | CPython        <-- NOT the formal 3.12.14
pydantic      : 2.13.5
pytest        : 8.4.2
sqlite3 lib   : 3.40.1                   <-- NOT the author's 3.49.1
sqlite3 module: 2.6.0
platform      : Linux-6.1.158+-x86_64-with-glibc2.36
```

**The formal CPython 3.12.14 gate was NOT reproduced.** The sandbox provides
only CPython 3.11.2, and 3.12.14 could not be provisioned: `python.org`,
`astral.sh`, `release-assets.githubusercontent.com`, `objects.githubusercontent.com`,
`raw.githubusercontent.com`, `deb.debian.org` and the conda hosts are all
network-blocked (TLS handshake EOF / SSL_ERROR_SYSCALL / DNS 000). Debian 12
bookworm ships no `python3.12`, and PyPI publishes no standalone CPython.
`uv` was installed and reached the download step, failing only at
`release-assets.githubusercontent.com`.

`pyproject.toml` declares `requires-python = ">=3.12"`, yet the entire suite
executes green on 3.11.2. SQLite is recorded as actually measured (3.40.1), not
aligned to any prior run.

## 14. Limitations

1. **Interpreter deviation (material).** All results are CPython **3.11.2**, not
   the formal **3.12.14**. The 1005-test regression, the 86 reviewer probes, and
   the #258 baseline RED are all valid on 3.11.2 but do not constitute a
   formal-gate reproduction. PM should require a 3.12.14 CI confirmation before
   integration; the GitHub checks on #264 head are all `pass`, which is the
   closest available formal-gate evidence and is **not** this reviewer's own run.
2. **SQLite 3.40.1**, older than both the author's 3.49.1 and the prior
   reviewer's 3.51.1. No version-dependent behaviour was observed.
3. **Process loss is real but fork-based.** Children are `fork`ed and
   `SIGKILL`ed; this is genuine process death with a genuinely new runtime in
   the parent, but it is not a container/OS-level restart.
4. **Threat-model boundary.** The HMAC authority key lives in
   `background_model_authenticity_authority` inside the same SQLite database. An
   attacker with direct write access to the database can mint valid proofs. The
   probes attack *recovery callers* and *corrupt/tampered durable state*, which
   is the documented boundary; a database-level adversary is outside it. This is
   pre-existing in #258 and not introduced by the corrective.
5. Reviewer probes for the 22-capability matrix were driven through
   `registry.invoke` at a pinned write time, not through three separate live
   turn/wake/review round-trips per capability. Mode coverage is provided
   separately by the three process-loss probes.

## 15. Lineage audit

| check | result |
|---|---|
| #264 head unchanged | `a73e186d…` — MATCH |
| candidate based on fresh main | merge-base `5288822` = the prompt's documented author-start base; the 5 later main commits touch only `AIOS_v3.0_CURRENT_CHECKPOINT.md`, `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`, the PM REVIEW_READY doc and this IA prompt — **no production source** |
| #258 not rewritten | head `1ebf51c4…`; `authored == committed` on every commit; SHA corroborated in-repo by `AIOS_v3.0_CURRENT_CHECKPOINT.md`, `PROJECT_MASTER_MAP.md`, the task board and the IA failure adjudication |
| #261 not modified / no implementation merged | #258 head **is** an ancestor of #261; all four src blobs **byte-identical** to #258's; #261's two extra commits are both `review(core): …` |
| #258 trusted-return carry-forward complete | `background_attempt.py` = `f6617aad47dd0b339dd954d9e0e430b733bef2ee` and `turn_runtime.py` = `062f7d8af03e599a39f962c29566a654a1963a13` on **both** #258 and #264 — identical to the PM-observed values, freshly re-derived. `sqlite_store.py` 178 insertions / **0** deletions; `execution/service.py` deletions are the state-derived `goal-transition:{id}:{revision}:{target}` key only — no trusted-return code removed |
| #261 review-only artifacts not imported | `reviews/IA_TRUSTED_RETURN_001_REV1/**` → 0 files in #264; `tests/independent_acceptance/**` → 0 files in #264 |
| no competing candidate | #264 is the only open PR at `a73e186d`; #258 and #261 remain at their historical heads |

One observation, not a defect: #264's first seven commits carry the same
messages and authored timestamps as #258's but different SHAs (all committed at
`10:26:53Z`) — the branch was replayed. #258's own history is untouched, and the
carry-forward was verified at **blob** level rather than inferred from SHAs.

## 16. Blocker count

# `blocker = 0`

---

## PASS conditions — all satisfied

| condition | evidence |
|---|---|
| complete reachable side-effecting surface converges under exact recovery | 22/22, §6–§7 |
| no duplicate meter / effect / operation / revision | `test_b`, `test_b2`, `test_c4`, process-loss §11 |
| changed / conflicting recovery stays fail closed | §8.C, §10 |
| rev5 → rev6 does not weaken the binding recovery contract | `LEGITIMATE_HARNESS_CORRECTION`, §8 |
| trusted-return authority unchanged | §9; blobs byte-identical to #258 |
| transplant / corruption attacks fail closed | §9, §10 |
| real process loss converges exactly once | §11; RED on #258 with a duplicate revision |
| full regression green | 1005 passed, §12 |

**`READY_FOR_PM_INTEGRATION`** — subject to limitation §14.1: this reviewer could
not execute the formal CPython 3.12.14 gate.

Review-only artifacts are under `reviews/CORRECTIVE_001_IA2/`. Nothing was
written into PR #264, #258, or #261. Independent Acceptance stops here.
