# C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003 — Engineering Report

Task: `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003`
Role: C15 Resident B Persistence Harness Corrective Engineer
Status: **REVIEW_READY** (fresh Independent Acceptance is the next step; this window does not self-accept)

---

## 1. Fresh identity

| Item | Value |
|---|---|
| Fresh fetch | `git fetch origin main` at session start |
| Starting live `main` | `016a2f7db5ed01b41fc614701079c507d2c2c02e` (equals the PM re-release post-integration baseline; **no main drift**) |
| Baseline restore commit | `852e0831cb23db46766890573e7f61c9512e55e7` (restores the scope-compliant harness from the frozen WIP onto fresh main) |
| Work branch | `arena/01a0ed87-haneof-aios-core-v3-0` (session-fixed branch; no other branch is created or pushed) |
| Candidate continuation commit | `4178cbd5b764b521eb4344851b131b5936d00e5d` (repair) |
| Candidate final head (this report) | `af3404b7f6b7ac4ea1f28e8e6702ce6179523a89` — parent `4178cbd5b764b521eb4344851b131b5936d00e5d`, tree `19f04f6446a75497921efc79fd116917228ffd17` |
| Candidate merge-base with `main` | `016a2f7db5ed01b41fc614701079c507d2c2c02e` (exact latest-main base) |
| PR | publication blocked in this sandbox: GitHub credentials return `401 Bad credentials` (see §12) |
| Governance state confirmed | `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003 = READY`; `RESIDENT_B = BLOCKED`, `RESIDENT_C = BLOCKED`, `EVALUATOR = BLOCKED`, `C15_CLOSE = BLOCKED` |
| Governance drift | none: the fresh main is exactly the PM re-release baseline and the task board still lists this task as the unique next READY |

Documents read fresh: `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`, `AIOS_v3.0_CURRENT_CHECKPOINT.md`,
`governance/C15_RCC_RES_B_PERSISTENCE_SCOPE_ADJUDICATION_2026-09-28.md`,
`governance/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003_CORE_DEPENDENCY_ADJUDICATION_2026-09-28.md`,
`governance/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-29.md`.

## 2. Historical preservation (unchanged, not rewritten)

* PR #251 failed exact candidate `7b2556e738d9c9386ec21c13fec39400c87d0916` — preserved as
  `historical reviewer verdict = ACCEPTANCE_FAIL / blocker=6`.
* PM narrowed ruling — `PM frozen-contract release blockers = 3` (`C002-001 / C002-002 / C002-004`),
  non-blocking hardening `C002-003 / C002-005 / C002-006`.
  The historical `6` is **not** rewritten into `3`; both numbers are stated.
* PR #254 stays **CLOSED / DRAFT / UNMERGED / FROZEN**; PM STOP comment `5863009559` untouched.
* First scope-violating WIP `f7848952b6519fc40f50806f4a4d8d350ac0f38a` stays
  `SCOPE_VIOLATION / NOT_A_CANDIDATE`; PR #254 closed head `a2d815c9f5154d87a56b152ed7cf5d1eb1baaaae`
  stays reported and untouched.
* No WIP commit was cherry-picked, rebased, amended or force-pushed. Neither the frozen WIP head nor the
  scope-violating commit is an ancestor of this candidate (proven mechanically in
  `evidence/EVIDENCE_MANIFEST.json` → `historical_preservation`).
* The two Core files the frozen WIP modified were **not** restored; no red/green WIP evidence was deleted.

## 3. Current baseline constructed on fresh main

The frozen WIP harness (`tools/c15_persistence/**`, `tests/c15_persistence/**`) was selectively restored onto
`016a2f7` (commit `852e083`), excluding its `.github/workflows/**`, `pyproject.toml` and all `src/aios_core/**`
content. Running that restored harness on fresh main produced the honest baseline RED
(`evidence/baseline/baseline_pytest_restored_harness.log`, `evidence/RED_probe_matrix_v2_baseline.log`):

| Baseline failure class | Cause |
|---|---|
| K4 killpoints + Corrective-002 K4 remote-only | operator called the rejected Core modification `stage_trusted_returned_background_response` |
| later-round K3 + K5 pre-push probes | same rejected Core recovery surface |
| operator-wiring receipt probe | asserted a Core state that accepted Core legitimately no longer has (staging does happen) |
| resident-surface probe | pointed at the frozen Corrective-001 WIP evidence path |
| historical journal suite under pytest | probe-teardown mechanics, not a contract failure (13/13 green under its frozen `unittest` contract) |

The rejected Core surface is exactly the one the PM STOP forbade; the baseline therefore proves the harness
could not legally converge on fresh main without a repair.

## 4. Provider-return authority: the accepted Core boundary (freshly measured)

Accepted main (`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001`, integrated) owns provider-return
authenticity:

* `FusedTurnRuntime.stage_exact_background_response(...)` requires an existing receipt and fails closed
  without one (`trusted provider-return authenticity proof is missing`);
* `BackgroundModelAttemptStore._capture_trusted_response_return(...)` is private and is wired only to the
  normal trusted provider-return callback, which atomically commits the receipt **and** the exact
  `background_model_return_handoffs` payload;
* `recover_trusted_handoff(...)` promotes **only** those Core-owned bytes, and only for the latest round whose
  earlier rounds are durably metered.

Fresh measurement on `016a2f7` (scratch experiment, reproduced with the frozen probes): when a **later** round
crosses the provider boundary and the process dies **before** the trusted return is durable, a fresh runtime
refuses to continue — `TurnExecutionInDoubt: started_or_interrupted`, the attempt stays `dispatching`, the
provider is **not** redispatched, metering and capability effects do not change. That window has no legal
continuation by design (no caller-supplied bytes may become a trusted return, and blind redispatch is
forbidden).

Consequently Corrective-003 maps the frozen contract's `provider-staged` convergence window onto the
authenticatable boundary — `K3_TRUSTED_RETURN_DURABLE` (Core receipt + exact handoff durable, before
record/meter/apply) — and treats the unauthenticatable in-flight window as a **hard fail-closed stop**. This is
strictly stronger than a fabricated convergence: nothing converges by inventing authenticity.

## 5. C002-001 — authoritative checkpoint failure hard-stops

**Implementation decision (harness-only, zero Core change).**

1. `RemoteDurabilityAbort(BaseException)` is raised by the operator capability handler whenever the
   remote-authoritative K4 barrier fails. Because Core's `CapabilityRegistry.invoke()` wraps only `Exception`,
   the abort crosses the capability-result boundary instead of degrading into `CAPABILITY_EXECUTION_ERROR`.
2. `_persist_remote_barrier()` now distinguishes an **authoritative persistence failure** from an ordinary
   error: it records durable failure evidence (`state/evidence/failures.jsonl` + audit trail) and raises
   `AuthoritativePersistenceFailure` for every barrier (K1–K5, ACKED), so no barrier can fail silently.
3. The failed K4 state is never published: local writers that advanced past the last published barrier refuse
   to attach (immutable-head vs authoritative-remote mismatch), and the next recovery starts from the
   authoritative remote state.
4. `probe_cli` exposes the frozen exit codes: `42 = FAIL_CLOSED_HARD_STOP`, `43 =
   AUTHORITATIVE_PERSISTENCE_FAILURE`.

**Evidence.** `C002-001-A` proves the wrapping boundary mechanically (abort crosses `invoke()`; a control
`RuntimeError` is still wrapped as structured tool evidence). `C002-001-B` proves the end-to-end stop: exit 43,
no ACK, no round-1 model call, one dispatch, one capability effect, remote ref still at the authenticated
provider-return barrier, failure evidence durable. `C002-001-C` proves restart semantics: the destroyed local
cache is not used; a fresh process converges from authoritative state exactly once (1 reveal / 1 ingest / 1 ACK
/ 1 capability effect / 2 metered rounds / 2 dispatches). `C002-001-D` proves an ACK-barrier failure never acks
the cursor.

## 6. C002-002 — later-round remote-only recovery converges exactly once

**Implementation decision (harness-only, zero Core change).**

1. The operator no longer stages or mints anything through Core; `_recover_with_core()` reattaches an
   already-dispatched provider request (never a second dispatch), reads Core's receipt and lets Core's own
   `recover_trusted_handoff`/exact-response recovery resume the round.
2. Three post-crash shapes are classified explicitly: attempt missing → ordinary re-admit path that
   re-presents the exact durable bytes through Core's trusted callback; `dispatching`/`in_doubt` without a
   receipt → `DurableTrustedReturnMissing` hard stop with durable evidence; receipt present → Core-owned
   recovery.
3. Every round now publishes the **authenticated provider-return barrier** (`K3_TRUSTED_RETURN_DURABLE`)
   immediately after Core commits receipt + handoff. This guarantees the last durable authoritative state
   before any later crash contains a Core-owned trusted return, so recovery can never be forced into the
   unauthenticatable in-flight window by a dispatch-only barrier.

**Results (frozen probes, exit-code and exactly-once assertions).**

| Probe | Scenario | Result | dispatches | metered | capability effects | assistant outputs | ACKs |
|---|---|---|---|---|---|---|---|
| `C002-002-A` | first-round trusted return, total local loss, remote-only | converged | 2 (distinct request ids) | 2 | 1 | 1 | 1 |
| `C002-002-B` | later-round trusted return, total local loss, remote-only | converged | 2 (distinct request ids) | 2 | 1 | 1 | 1 |
| `C002-002-C` | later-round dispatch-only (in-flight, no trusted return) | **fail-closed stop (42)**, deterministic on repeat | 2 — **no new dispatch** | unchanged | unchanged | unchanged | **0** |
| `C002-002-D` | K5 applied-before-ACK barrier published, then local loss | converged; turn not rerun | 2 | 2 | 1 | 1 | 1 |
| `C002-002-E` | K5 crash after local commit, before remote push | converged from the last published authenticated barrier; unpublished commit never promoted | 2 | 2 | 1 | 1 | 1 |
| `C002-002-F` | exact trusted-return bytes changed under the same durable identity | fail-closed (Core re-verifies the handoff digest) | 2 — no redispatch | unchanged | unchanged | unchanged | **0** |
| `C002-002-G` | exact relay-journal reply bytes changed | fail-closed (operator integrity check) | 2 — no redispatch | unchanged | unchanged | unchanged | **0** |

Additional frozen coverage proving the same contract: `tests/c15_persistence/killpoints` K1–K5 convergence vs a
measured baseline, and `tests/c15_persistence/test_corrective_002_remote_durability.py` K1–K5 remote-only
recovery (marker + convergence for every barrier).

No provider redispatch, duplicate meter, duplicate capability side effect, duplicate semantic/World write,
duplicate assistant output, duplicate delivery, duplicate ACK, cursor skip or cursor replay appears in any
converged probe.

## 7. C002-004 — remote-authoritative binding cannot silently downgrade

**Implementation decision.** The durable owner record keeps the run-class classification
(`remote_authoritative` + canonical `remote_authority`), and `remote-durability.json` is a bound,
digest-carrying binding. Attach/resume for a remote-authoritative run verifies: binding present, JSON valid,
exact field set, self-digest, canonical ref for this run, run/session identity match, remote reachable and
remote head equal to the local expected head, and the immutable generation head byte-equal to the exact
authoritative commit. Any failure is `BackendError` — never a fallback to local-only operation.

**Evidence.** `C002-004-A` (valid binding survives total local loss and re-attach stays remote-authoritative),
`C002-004-B` (nine damaged shapes: missing, truncated, malformed JSON, extra field, missing field, unreadable,
wrong run, wrong session, non-canonical ref — all fail closed), `C002-004-K` (unreachable remote fails closed),
`C002-004-L` (an intentionally local-only synthetic run has no remote classification and cannot be promoted to
remote-authoritative by attach parameters, so the two run classes stay durably distinguishable).

## 8. Retained non-blocking findings (not release gates)

`C002-003` (coordinated/history tampering), `C002-005` (cross-run binding transplantation) and `C002-006`
(hostile concurrent ref rewrite) stay **NON-BLOCKING HARDENING / OUT OF C15 RELEASE GATE**. Their probes are
retained unchanged in `tests/c15_persistence/test_corrective_003_regressions.py` so ordinary corruption
detection cannot silently regress: seal-content tamper, unexpected generation artifact, history shortening by
lowering the mutable ledger and re-hashing the local head, cross-run config/ref transplantation, and the
atomic expected-old-value lease for the single controlled-writer model. No Byzantine storage architecture, no
generic distributed CAS subsystem and no new security architecture was built.

## 9. Frozen state-loss contract coverage

| Frozen requirement | Where proven |
|---|---|
| non-ephemeral authoritative run state | remote Git ref/commit barrier per step (`state/remote-barrier.json` markers) |
| durable cursor checkpoint before model exposure | K1/K2 barriers + `reveal`/`ingest` idempotence |
| durable exact provider relay journal | per-round `K3_TRUSTED_RETURN_DURABLE` barrier (Core receipt + exact handoff) + relay journal exact bytes |
| crash/restart after reveal / ingest / provider-staged / reply-application / pre-ACK | K1, K2, K3(+trusted return), K4, K5 probes in `killpoints` and `test_corrective_002_remote_durability.py` |
| recovery to the same durable cursor, no duplicate reveal/ingest/apply/output/ACK, no skipped cursor | `assert_convergence` vs a freshly measured baseline in every probe |
| projection / binding / mailbox / failure evidence survive | sealed generations + `test_environment_reattach.py` + re-attach manifests |
| no semantic reconstruction shortcut | operator stores bytes only (`test_no_second_semantic_engine_properties`), Core owns authenticity |
| frozen regression unchanged | K1–K5, journal state machine, generation admission, rewiring probes all green |
| disposable/synthetic state only, no real Resident B | every run/ref/identity is synthetic; no C15 fixture, release state or Resident artifact is read or written |

## 10. Regression

* persistence frozen blocker probes — green (see §5–§7)
* full persistence crash matrix — green (`evidence/GREEN_persistence_pytest.log`, 78 tests)
* historical journal suite under its frozen `unittest` contract — green (`evidence/GREEN_unittest_journal.log`, 13 tests)
* ordinary generation corruption checks / identity + binding checks — green (retained probes)
* trusted-return focused Core regression (11 suites) — green (`evidence/GREEN_core_trusted_return_focused.log`)
* resident-visible surface unchanged vs base (`src/aios_core` pinned clean) — `evidence/resident-surface-no-change.json`
* full repository suite — `evidence/GREEN_full_repository_pytest.log`
* Core was **not** modified to make any of this pass; no Core test was touched.

## 11. Candidate freeze

* scope gate: `evidence/EVIDENCE_MANIFEST.json` → every changed path classified; **`src/aios_core/**` diff = ZERO**;
  no product packaging change; no Resident A/B/C, evaluator, fixture or workflow change.
* probe matrix: `frozen/CORRECTIVE_003_PROBE_MATRIX.json` (+ `.sha256`), 21 probe ids, source SHA-256 per file,
  freeze history preserved (initial freeze before RED, final freeze after documented probe corrections).
* evidence manifest hash: see `evidence/EVIDENCE_MANIFEST.json.sha256`.
* environment: CPython 3.11.2 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.40.1. **Disclosed delta**: this
  sandbox cannot obtain CPython 3.12.14 (GitHub release-asset and python.org downloads are blocked; Debian 12
  ships only CPython 3.11). The pinned dependency versions are exact; the interpreter/SQLite delta is disclosed
  rather than hidden.
* CI/workflow status: no `.github/workflows/**` file is added or modified by this candidate; all gates were
  executed locally with the exact commands recorded in the evidence logs (the frozen WIP's corrective-003
  workflow is deliberately **not** restored because it had been changed to require the scope-violating Core
  diff).
* Re-verification on the exact committed head: the frozen probe matrix (`C002-001/002/004` ids plus the
  retained non-blocking probes) passes 29/29 against `af3404b...`, and the scope gate reports
  `src_aios_core_diff_is_zero = true` with zero scope violations.

## 12. Status

```text
C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003 = REVIEW_READY (engineering complete, candidate frozen)
NEXT = FRESH_INDEPENDENT_ACCEPTANCE
```

**Publication blocker (infrastructure, not engineering):** this sandbox's GitHub credentials are invalid
(`401 Bad credentials`), so the continuation branch could not be pushed and the PR could not be opened from
this window. Everything an Independent Acceptance needs is committed on
`arena/01a0ed87-haneof-aios-core-v3-0` at the exact head above, with the PR declaration already recorded in
`reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003/PR_BODY.md`. GitHub access needs to be reconnected in
Arena; the push + PR creation are the only remaining mechanical steps.

Not entered: Resident B, RELEASE-003, RERUN-003, ACCEPT-003, Resident C, evaluator, C15 close.
