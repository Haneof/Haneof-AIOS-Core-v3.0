# Independent Acceptance Report — CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001

Reviewer role: **Independent Core Trusted-Return Recovery Acceptance Reviewer**
Task: `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-INDEPENDENT-ACCEPTANCE`
Date: 2026-09-28

---

## 1. Verdict

```text
CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-INDEPENDENT-ACCEPTANCE
= ACCEPTANCE_FAIL

blocker = 1   (IA-BLK-TRUSTED-RETURN-001, affecting 5 capability families)

READY_FOR_PM_INTEGRATION
```

Technical execution completed. The candidate was **not** modified. No fix, amend,
rebase, force-push, squash, merge or cherry-pick was applied to PR #258.

---

## 2. Pinned target and base-drift verification

| item | value |
|---|---|
| repository | `Haneof/Haneof-AIOS-Core-v3.0` |
| PR | **#258** — `OPEN / READY / UNMERGED`, `MERGEABLE` |
| exact candidate tested | `1ebf51c4cb905e2a2578a09b64007b50bca0d4ac` |
| candidate engineering base | `7b207362a0b148c5d49bb586f1c878583661a5a9` |
| live main (fresh fetch) | `a3dab8bcffe83cddc523cac6d8d1e4346b5f33e3` |
| governance state | `...-RECOVERY-001 = REVIEW_READY / AWAITING_INDEPENDENT_ACCEPTANCE`; `...-INDEPENDENT-ACCEPTANCE = READY` (sole next READY) |
| reviewer branch | `ia/independent-acceptance-trusted-return-001-rev1` (worktree `/home/user/ia-review`, created **from the exact candidate**) |

**Base drift `7b207362 -> a3dab8bc`** — governance only:

```
M  AIOS_v3.0_CURRENT_CHECKPOINT.md
M  governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md
A  governance/CORE_BACKGROUND_TRUSTED_RETURN_RECOVERY_001_PM_REVIEW_READY_WRITEBACK_2026-09-28.md
```

* `git diff 7b207362 a3dab8bc -- src/aios_core` → **0 lines**
* `git diff 7b207362 a3dab8bc -- tests` → **empty**
* `git diff 7b207362 a3dab8bc -- .github` → **empty**

No `BASE_SEMANTIC_DRIFT`. Main was **not** merged into the candidate.

---

## 3. Formal environment

| component | reviewer | author | match |
|---|---|---|---|
| CPython | **3.12.14** | 3.12.14 | YES |
| pytest | **8.4.2** | 8.4.2 | YES |
| pydantic | **2.13.5** | 2.13.5 | YES |
| SQLite | **3.51.1** | 3.45.1 | **NO — recorded deviation** |

**SQLite deviation (disclosed).** The review sandbox has no `sqlite3.h`,
no `libsqlite3-dev` and no root, so a matching SQLite 3.45.1 `_sqlite3` could not be
built. The reviewer built CPython 3.12.14 from source and ran it against a **newer**
SQLite (3.51.1). This is not a weaker environment for the invariants under test; the
deviation is recorded rather than silently ignored. The author's 3.45.1 result is
retained as author evidence and was not reproduced by the reviewer.

The reviewer did **not** rely on the author's workflow `36384741145`; every number in
this report comes from a fresh reviewer execution.

---

## 4. Architecture re-review (§8)

Source review of the candidate, not just test execution.

| question | answer | evidence |
|---|---|---|
| 1. Who can create a trusted-return receipt? | Only the **private** `_capture_trusted_response_return`, wired solely as CognitiveRuntime's trusted return callback. | `background_attempt.py:1462`; sole caller `turn_runtime.py:1322` |
| 2. Who can write the exact return handoff? | The same private method, inside the **same** SQLite transaction as the receipt. | `background_attempt.py` `_capture_trusted_response_return`, one `BEGIN IMMEDIATE` … single `conn.commit()` |
| 3. Can a recovery caller submit arbitrary directive bytes? | **No.** `recover_trusted_handoff(subject_id, work_kind, work_id)` takes no payload, proof, fingerprint or signing capability. | probe `test_ia_auth_no_public_receipt_mint_api` asserts the exact parameter set |
| 4. Can a recovery caller obtain signing/HMAC authority? | **No.** `_authority_key` is private and never returned; the public receipt read exposes a proof, not a signing callable. | `response_authenticity_receipt` docstring; probe `test_ia_auth_receipt_read_never_exposes_key_or_callable` |
| 5. New public receipt-mint API? | **No.** The only new public method, `recover_trusted_handoff`, promotes Core-owned handoff bytes and *verifies* the existing proof; it mints nothing. | candidate diff + probes above |
| 6. Is the exact response bound to the original outbound request? | **Yes** — receipt binds `outbound_request_fingerprint` and `relay_id`; `_require_origin_binding` re-checks on every consume. | `_verify_response_authenticity`, `exact_response_directive` |
| 7. Are receipt and exact payload atomic/durable? | **Yes** — one transaction, one commit. R3 probes found no half state. | `test_ia_r3_*` (all pass) |
| 8. Does restart only consume Core-owned handoff? | **Yes** — a handoff is written only by the trusted callback; recovery reads it and re-verifies. | probes 01–03, 07–13, 15, 18, 21–22 (all pass) |

**Conclusion: no receipt-mint authority was widened.** The trust-root limitation
(§22) was not reopened: probes that tamper durable rows directly were classified as
informational and are marked `xfail`, not treated as blockers.

---

## 5. The blocker

### IA-BLK-TRUSTED-RETURN-001 — R5-C exactly-once replay is repaired in one capability family, not in the capability contract

**Class:** legitimate exact replay of an already-durable side effect **fails**,
breaking exactly-once convergence of the logical turn.
Not a duplicate effect — a *refusal to converge*.

**Frozen contract violated.** The merged R5 scope clarification binds R5 as
**EXACTLY-ONCE DURABLE EFFECT** and requires, for R5-C:

* mandatory item 9 — "any replayed capability/application uses the same durable
  identity / write-time / idempotency boundary";
* mandatory item 10 — "conflicting replay remains fail-closed", implying an
  *identical* replay must be accepted.

The candidate implements exactly that for `execution.task.create` by looking up the
original operation by idempotency key and reusing the original `operation_id` and
`expected_world_revision`. **That repair is applied at one call site only.** Every
other reachable side-effecting capability still re-derives `expected_world_revision`
from `current_world_revision()`, so the replayed request fingerprint differs from the
stored one and Core refuses the replay.

**Root cause (source).** `request_fingerprint` includes `expected_world_revision`
(`src/aios_core/storage/idempotency.py:564`). After the capability's World effect is
durable, `current_world_revision()` has advanced by one, so the replay's expected
revision differs from the recorded one:

* `src/aios_core/execution/service.py:1240` — `execution.goal.propose`
* `src/aios_core/events/service.py:288` — `event-form`
* `src/aios_core/world_graph.py:369/468/597` — entity/relation writes
* `src/aios_core/dimensions/registry.py:297` — `dimension_key already exists`
* `src/aios_core/policy/service.py:309` — `policy already registered`

By contrast `cognition.commit_claim` passes **not** because of the candidate, but
because `src/aios_core/writeback/cognition.py:210` already carried a pre-existing
exact-retry guard (`get_payload(claim_id)` → `reused_existing=True`) that returns
before `store.commit`. That is why a single-family sweep can look green.

**Affected durable identities / exact crash point (reproduced, `evidence/IA_BLK_001_propose_goal.txt`):**

```
[PRE-CRASH] propose_goal ok=True data={'goal_id': 'goal_524378a4a79bc75381a50fcd', ...}
[CRASH STATE] world_revision = 3
  OP   execution.goal.propose  op_a247e5cec7824a5a9e4ef5015ebf92cc
       expected_world_revision=2  result_world_revision=3
  IDEM goal-propose:goal_524378a4a79bc75381a50fcd:1 -> op_a247e5...  world_revision=3
  GOALS before replay: [('goal_524378a4a79bc75381a50fcd', 1)]

[FRESH RECOVERY] same durable handoff, provider allowed only NEW rounds
  REPLAY call_id=ia-propose_goal-0 ok=False error_code=CAPABILITY_EXECUTION_ERROR
         error_message=StoreError: idempotency key was already used for a different request
  GOALS after replay: [('goal_524378a4a79bc75381a50fcd', 1)]     <- no duplicate, but no convergence
```

**Capability families proven affected (5 of 8 exercised; all reachable from a model
capability directive, `kind=write, side_effecting=True`):**

| capability | replay error on fresh recovery |
|---|---|
| `propose_goal` | `StoreError: idempotency key was already used for a different request` |
| `form_event` | `StoreError: idempotency key was already used for a different request` |
| `propose_entity` | `ValueError: entity_key already exists: entity:ia0` |
| `propose_dimension` | `ValueError: dimension_key already exists: dim:iax0` |
| `propose_cognitive_policy` | `ValueError: policy already registered: ia.policy.0` |

**Capability families proven unaffected:** `create_task` and
`create_attention_watch` (the candidate's repaired `execution.task.create` family) and
`commit_claim` / `commit_ai_world_claim` (pre-existing exact-retry guard).

**Why this is a blocker and not a callback-re-entry observation.** The frozen
clarification explicitly states that re-entering an idempotent function is *not* a
blocker **if it produces no second durable effect**. Here there is no second durable
effect — the failure is the opposite: the *legitimate identical* replay is rejected.
Task §28 lists as a blocker "legitimate exact replay错误失败，导致 logical turn不能
exactly-once convergence" and "side-effecting capability family存在实际可达 R5-C
replay failure". Both apply. The same logical model call yields a different outcome on
replay than it did originally, so the turn cannot exactly-once converge.

**Reachability.** These capabilities are registered `side_effecting=True` and are
reachable in any active AIOS turn — user turn, Wake and Periodic Review — so the
failure is not hypothetical.

**Not fixed by the reviewer.** Recorded only, per §29.

---

## 6. Per-contract verdicts

| contract | verdict | note |
|---|---|---|
| R1 (pre-submission) | **PASS** | no phantom receipt/handoff; Core refuses unauthorized retry (`TurnExecutionInDoubt`) and never invents a return |
| R2 (submitted, no trusted return) | **PASS** | no blind redispatch; crash at the trusted boundary leaves no receipt/handoff |
| R3 (handoff atomicity) | **PASS** | receipt and handoff always appear together; no receipt-only or handoff-only state; partial handoff fails closed |
| R4 (later rounds 1 and 2) | **PASS** | same attempt/round/request/fingerprint/payload/receipt; exactly one meter per attempt; recovered round never reaches the provider |
| R5-A | **PASS** (candidate suite + reviewer) | |
| R5-B | **PASS** (candidate suite + reviewer) | |
| R5-C | **FAIL — IA-BLK-TRUSTED-RETURN-001** | repaired for one family only |
| R5-D | **PASS** (candidate suite) | |
| §17 capability breadth | **FAIL — IA-BLK-TRUSTED-RETURN-001** | 5 reachable side-effecting families fail |
| §18 operation replay (13 attacks) | **PASS** | exact retry replays; changed arguments/object identity/source data/key all fail closed; reused `operation_id` under another key fails closed; replay after unrelated later revisions returns the original exact result; 6-way concurrent identical retry produced one World commit |
| §19 authority surface | **PASS** | `operation_for_idempotency_key` is an inert read; arbitrary lookup writes nothing; reused revision cannot smuggle a changed request |
| §21 authenticity matrix | **PASS** | 17 binding cases fail closed; 3 direct-row-tamper cases are trust-root (§22) and marked informational |
| §23 terminal conflicts | **PASS** (candidate `..._r5_conflicts_001`) | |
| §24 real SIGKILL | **PASS** | child exit `-9`; handoff+receipt durable; fresh process recovered exact response with identical identities, no round-0 redispatch, exactly one meter per (attempt, round) |

---

## 7. Reviewer probe discipline (§6)

The reviewer wrote and froze its **own** adversarial suite before executing anything,
and did **not** take the author's 24/24, 99/99, 816/816 as acceptance.

59 probes in 5 files. Seven revisions were cut; **rev1 is preserved unmodified** and
every later revision is a new file set with fresh digests. The frozen *expected
outcomes* were never weakened — revisions fixed harness mechanics only
(`RuntimeSnapshot.round_index`, capability-argument validation, over-specified
assertions, child-process template escaping), and each such revision is recorded in
`MANIFEST.md`.

| revision | source SHA256 (probe set root) | enumeration SHA256 | outcome |
|---|---|---|---|
| rev1 | `5f3ef79f…` | `94682d30…` | 16 passed / 43 failed — harness defects exposed |
| rev2 | `8602304d…` | `94682d30…` | 37 passed / 22 failed — blocker first surfaced |
| rev3 | `2b2a94da…` | `d3d31ccf…` | 38 passed / 22 failed |
| rev4 | — | `d3d31ccf…` | 45 passed / 14 failed |
| rev5 | — | `d3d31ccf…` | 48 passed / 9 failed |
| rev6 | — | `d3d31ccf…` | 49 passed / 7 failed |
| **rev7 (binding)** | see `evidence/rev7_probe_sources.sha256` | **`d3d31ccf9539b8d9b90f3a7e20982133b69af8000bd7e9ef45aa2112422dfe48`** | **51 passed / 5 failed / 3 xfailed** |

Final rev7 first-run raw output: `evidence/rev7_first_run.txt`.

---

## 8. Regression evidence

See `evidence/full_regression.txt` for the complete reviewer-executed regression,
and `evidence/REGRESSION_SUMMARY.md` for the per-suite breakdown.

Candidate-owned trusted-return and recovery suites, reviewer-executed:

```
78 passed in 12.03s
```

---

## 9. Candidate integrity at verdict

* PR #258 head, re-fetched at verdict time: **`1ebf51c4cb905e2a2578a09b64007b50bca0d4ac`** — **no drift**.
* Live main, re-fetched: **`a3dab8bcffe83cddc523cac6d8d1e4346b5f33e3`** — unchanged.
* `git diff 1ebf51c4cb905e2a2578a09b64007b50bca0d4ac -- src/aios_core` → **EMPTY**.
* `git diff 1ebf51c4cb905e2a2578a09b64007b50bca0d4ac -- tests .github` → **EMPTY**
  (the candidate's own tests and workflow were not rewritten).
* Reviewer branch adds only `reviews/IA_TRUSTED_RETURN_001_REV1/` and
  `tests/independent_acceptance/`.

### Publication topology (stated precisely to avoid a misleading claim)

The candidate-integrity claims above are asserted **on the review branch**, which is
created *from the exact candidate* and therefore shares the candidate's entire tree.

Two branches carry the evidence:

| branch | base | `src/aios_core` vs its own base | role |
|---|---|---|---|
| `ia/independent-acceptance-trusted-return-001-rev1` | the exact candidate `1ebf51c4…` | **EMPTY** | authoritative candidate-integrity proof; review-only PR #261 |
| `arena/01a0e711-haneof-aios-core-v3-0` (session) | live main `a3dab8bc` | **EMPTY** (vs main) | mirrors the same review artifacts so this window is tracked |

The session branch is main-based, so it naturally does **not** contain PR #258's
candidate changes. Comparing the session branch against the candidate would therefore
show all of PR #258's own diff — that is main lagging the candidate, **not** reviewer
modification. The two independent checks that matter are both green:

* review branch vs exact candidate: `src/aios_core` **EMPTY**, candidate tests/CI
  **byte-identical** (additions only, in a new directory);
* session branch vs live main: `src/aios_core` **EMPTY**, tests **additions only**.

---

## 10. Residual limitations

1. **SQLite 3.51.1, not 3.45.1** — disclosed in §3. A formal 3.45.1 run remains
   desirable before closure, although nothing in IA-BLK-001 is SQLite-version
   dependent (the failure is fingerprint/revision arithmetic inside Core).
2. **Five capability families were exercised directly**; the remaining reachable
   side-effecting capabilities were enumerated from the live registry (22 total) but
   not each individually driven through a crash. Given the shared root cause
   (`expected_world_revision` re-derived from `current_world_revision()`), the affected
   set is very likely a superset of the five proven. This is a *lower bound*.
3. **§21 direct-row-tamper probes** (wrong provider / model / request id / relay /
   outbound fingerprint) do not fail closed in every configuration. These mutate
   durable tables directly and therefore sit inside the accepted trust root (§22);
   they are recorded as informational `xfail`, **not** as blockers. They would only
   become binding if the candidate had widened that authority surface — it did not.
4. Periodic Review and Wake paths were covered through the candidate's own R5 suite
   plus reviewer R1–R4; the breadth sweep itself ran on the `user_turn` path, where
   `_active_turn_time` is pinned to `admitted_at` on recovery.
