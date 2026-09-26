# CORE-BACKGROUND-RESPONSE-RECOVERY-001 — Candidate Evidence Report

Status: **GATE / REVIEW_READY** (candidate only; NOT self-accepted, NOT DONE, not merged)

- Task: `CORE-BACKGROUND-RESPONSE-RECOVERY-001` (`= READY` confirmed before any engineering work)
- Started from live main: `a310bf1202bf41644c2f3e25798053a6636e14be` (fetched live, no drift)
- Work branch: `arena/01a0dcf6-haneof-aios-core-v3-0`
- Tested exact candidate SHA: `3f9ec00d0fa283bc5294574d6da1e84d654d6645`
- Evidence-only commits that follow the tested SHA touch documentation/logs only.
- Candidate PR: **#219** (`arena/01a0dcf6-haneof-aios-core-v3-0` → `main`). Its head is the
  evidence-only commit; the tested exact SHA is the one named above. Independent acceptance must evaluate that exact SHA.
- Independent acceptance task (`CORE-BACKGROUND-RESPONSE-RECOVERY-001-INDEPENDENT-ACCEPTANCE`) is
  not performed here. No RC re-freeze, no Resident run, no operator-persistence work happened.

## 1. What the mechanism is

The smallest Core path that lets an exact, externally durably preserved provider reply resume the
**same** background model attempt/round after process death, without a provider call:

| File | Change |
|---|---|
| `src/aios_core/runtime/background_attempt.py` | Canonical exact-directive encode/decode (strict: exact field sets, no defaults, no fallback), durable `background_model_responses` staging table (+ identity index) in the *same* World store, `stage_exact_response` (fingerprint + provider/model/request_id + payload-hash verification, refuses attempts that provably never crossed the provider boundary), `pending_exact_response` (only the round where execution stopped, only when every earlier round is already metered), `exact_response_directive` (re-verifies payload hash, fingerprint and attempt provenance on every consumption). |
| `src/aios_core/runtime/cognitive_runtime.py` | `RecoveredModelResponse` + `model_response_recovery` hook, evaluated **before** admission. On a hit the exact directive continues through the ordinary downstream loop (terminal handling, capability application, metering) while admit/dispatch/provider/response-recorder are skipped for that round. |
| `src/aios_core/runtime/turn_runtime.py` | Public `stage_exact_background_response()` relay entry point; per-work recovery offset for `wake`, `periodic_review` and `user_turn`; recovered rounds resume the original execution write time so replayed capability writebacks stay idempotent; every round (including user turns) meters against its exact attempt id. |
| `src/aios_core/runtime/turn_execution.py` | `exact_response_ready` disposition and `authorize_exact_response_recovery()` (durable claim + same input hash + no completed output + no retry authorization + staged attempt present). It writes reconciliation evidence only: it never sets `retry_authorized` and never increments `retry_count`. |
| `src/aios_core/runtime/metering.py` | A user-turn meter row cannot carry the attempt work id, so its attempt binding is subject + exact model round; wake/review binding stays subject + work id + round. |

Explicit non-goals honoured: no second World/cognition store (the staging table lives in the existing
runtime store and holds provider bytes, not semantics), no operator-owned semantic engine, no
heuristic reconstruction/default/fallback, no provider re-dispatch, no Resident run, no change to the
sealed fixture, historical Resident evidence or PR #216 frozen WIP.

## 2. Fault-injection matrix (all ten required kill points)

All cases live in `tests/integration/test_core_background_response_recovery_001.py`.

| # | Required fault | Test | Asserted invariant |
|---|---|---|---|
| 1 | crash after dispatch, exact response unavailable | `test_case_01_...`, `test_user_turn_...` (pre-staging half), `test_metered_attempt_without_exact_bytes_stays_blocked` | attempt stays `in_doubt`/`metered`, restart raises `BackgroundModelExecutionInDoubt`/`BackgroundModelAttemptBlocked`, provider call count stays 1 |
| 2 | exact response durably reconciled | `test_case_02/05/05b_...`, `test_periodic_review_...` | wake/review completes, `recovered_response_attempts == (attempt_id,)`, provider call count 0, exactly one meter row bound to the attempt |
| 3 | wrong fingerprint | `test_case_03_...` | `ValueError`, nothing staged, still fail-closed |
| 4 | wrong provider/model/request_id | `test_case_04_...` (3 params), `test_case_04b_...`, `test_case_04c_...` | identity mismatch with the directive, missing identity, and mismatch with durable attempt provenance are all rejected (`BackgroundModelResponseConflict`); the identical durable bytes remain reconcilable |
| 5 | crash after response reconciliation, before application | `test_case_05_...`, `test_case_05b_...` | staged bytes survive a store reopen; recovery still has 0 provider calls and 1 meter row |
| 6 | crash during capability application | `test_case_06_...` | the exact directive is re-applied; the attention-watch Task exists exactly once at revision 1; the recovered round never reaches the provider (the only provider call is the fresh next round, on a different attempt id); meter rows = one per round |
| 7 | crash after capability result, before next model round | `test_case_07_...` | recovery resumes only the round where execution stopped; the already-applied round is not replayed; watch Task still exists exactly once |
| 8 | crash after terminal silence, before completion marker | `test_case_08_...` | wake is still `running` with a metered attempt and 1 meter row; recovery replays the terminal round with 0 provider calls, completes once, meter rows stay 1 |
| 9 | repeated recovery invocation | `test_case_09_...`, `test_user_turn_...` | re-invocation is refused (`ValueError` NEW/QUEUED/RUNNING; `TurnAlreadyCompleted`), re-staging identical bytes is idempotent, conflicting bytes raise, capability/output/metering counts stay 1 |
| 10 | normal path + `not_submitted` retry regression | `test_case_10_...` | normal wake/user-turn/review stay provider-driven with no recovered attempts; `not_submitted` keeps safe retry on the *same* attempt id with exactly one meter row |

Additional fail-closed coverage: `test_malformed_exact_payloads_are_rejected_without_defaults`
(strict decode: malformed JSON, extra/missing fields, double terminal, no terminal),
`test_tampered_staged_bytes_fail_closed_before_application` (durable payload-hash guard),
`test_no_exact_response_can_be_staged_for_a_call_that_never_reached_provider` (`admitted` and
`not_submitted` attempts cannot receive a staged reply; ordinary retry semantics unchanged).

## 3. Green evidence at the tested exact SHA

Full suite (`/home/user/.cache/aios-venv/bin/python -m pytest -p no:randomly`):

```
717 passed in 199.02s (0:03:19)
pytest exit=0
```

- `reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001/full_suite.txt` (stdout + exit code)
- `reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001/full_suite_junit.xml` — `tests=717 failures=0 errors=0 skipped=0`
- Random-order re-run: `reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001/full_suite_randomized.txt` (all dots, no failures)
- Focused gate subset (runtime + FIX-002 + headless + core recovery + this fault matrix): `93 passed in 6.93s`, see `gate_subset.txt`

## 4. Red evidence (preserved, not laundered)

Each red run was produced by a temporary one-line mutation of the candidate implementation, run
against the *same* fault matrix, then reverted. The mutations no longer exist in the tree.

| Log | Mutation | Observable red substrate |
|---|---|---|
| `red/red_A_recovery_hook_disabled.txt` | `_recover_exact_model_response` returns `None` | 10 recovery tests fail (`BackgroundModelResponsePending` / `Blocked` / provider not called); the fail-closed and normal-path tests still pass |
| `red/red_B_write_time_unpinned.txt` | recovered round uses a fresh `now` instead of the attempt's durable `admitted_at` | case 6 duplicates the capability side effect (`assert 2 == 1` watch Tasks) |
| `red/red_C_fingerprint_check_disabled.txt` | fingerprint verification in `stage_exact_response` disabled | case 3 `DID NOT RAISE` |
| `red/red_D_identity_check_disabled.txt` | provider/model/request_id verification disabled | case 4 params fail (`DID NOT RAISE`) |
| `red/red_E_staging_state_guard_disabled.txt` | staging allowed for attempts that never crossed the provider boundary | `test_no_exact_response_can_be_staged_for_a_call_that_never_reached_provider` fails |
| `red/red_F_payload_hash_guard_disabled.txt` | durable payload-hash guard disabled | tampered-bytes test fails (the fingerprint guard still caught the tampering — defence in depth) |

Historical red attempts from the predecessor work are untouched: PR #216 frozen WIP and
`reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_001/` evidence were not modified.

## 5. Requirement checklist

| Requirement | Evidence |
|---|---|
| no provider re-dispatch on exact-response recovery | every recovery test uses a provider that fails the test if invoked; provider call counts asserted per case |
| no semantic reconstruction/default/fallback | strict matched encoder/decoder, exact field sets, payload-hash + fingerprint + durable provenance re-verification; malformed/tampered cases fail closed |
| exact provider/model/request_id + fingerprint/directive verification | case 4 family, tampered-bytes test, `exact_response_directive` re-verification |
| missing/mismatched reply stays fail-closed | cases 1, 3, 4, metered-without-bytes test |
| downstream application uses the normal CognitiveRuntime path | recovery only substitutes the directive before the ordinary loop; capability application, terminal handling and metering are the same code paths (case 6/7/8) |
| capability/output/metering exactly once across restart | case 6/7/8/9 + user-turn test (one assistant Observation, one meter row, one Task at revision 1) |
| `not_submitted` safe retry unchanged | case 10 sub-case + existing FIX-002 suite |
| ambiguous no-response `in_doubt` protection unchanged | case 1 + `test_metered_attempt_without_exact_bytes_stays_blocked` + existing FIX-002 suite |
| ordinary uninterrupted provider path behavior-compatible | full 717-test suite + case 10 normal wake/user-turn/review |
| no second World/cognition store | staging table + identity index are created inside the existing runtime store; no new database, no semantic fields |
| no operator-owned semantic engine | staging accepts only raw exact bytes plus mechanical identity; all decisions are fingerprint/identity comparisons |

## 6. CI status on candidate PR #219 (head `b82ae25bcbef0d1d81cc3b7e5f303d75a4f0b507`)

32 of 34 checks PASS, including `full-core-regression` (4m40s), `p16-convergence`,
`p16-habitation-harness`, `constitutional-cognition-closure`, all C14/C15 cognition/runtime gates,
`scale-s1m`/`s100k`/`s10k`, `semantic-equivalence`, `p9`-`p15` gates and every `test` job.

Two checks FAIL, both fixture-task invariants that assert a Core diff is *absent*:

| Check | Failing step | Why it is red here |
|---|---|---|
| `semantic-repair-mechanical-gate` (`c14-semantic-repair-fixture`, run `36234237680`) | `Prove fixture task did not modify Core or historical C14 evidence` | the step's explicit rule is `if grep -q '^src/aios_core/' <<<"$changed"; then exit 1` — a Core task necessarily trips it |
| `c15-rcc-fixture-mechanical-gate` (`c15-rcc-fixture`, run `36234237724`) | `Prove fixture task has zero Core diff` | identical rule in the C15 fixture workflow |

These two workflows are the ones `governance/AIOS_CORE_CI_FINDING_001_2026-09-24.md` already
classifies as infrastructure/branch-shape artefacts, not policy violations. Their asserted invariant
("this *fixture* change must not modify `src/aios_core/**`") cannot hold for a Core recovery task.

Direct local proof that the invariants these guards exist to protect still hold:

- `git diff --name-only a310bf1202bf41644c2f3e25798053a6636e14be HEAD` = the five
  `src/aios_core/runtime/*` files, the new fault-matrix test and this evidence directory only;
- `git diff --name-only ... -- reviews/internal_habitation/` = 0 files (frozen v2 fixture and every
  historical Resident/C14 evidence file untouched);
- `sha256sum reviews/internal_habitation/c14-resident/semantic-repair-v1/fixture/sealed_fixture.json`
  = `1095d5aef52061753db7d9dab558af1361b92976f2ded0e6956d70afe3e6527f`, the frozen expected value.

No workflow file was changed by this candidate, so the checks were not waived or edited.

## 7. Honest limitations for the reviewer to attack

1. The relay/operator must supply the exact bytes and their identity; Core can only verify them against
   the durable attempt. For an attempt that died before any response was recorded (`dispatching` /
   `in_doubt`) there is no durable provider provenance to compare against, so exactness rests on the
   externally preserved journal being self-consistent with the staged bytes and fingerprint.
2. Recovery assumes the round's original execution write time equals the attempt's durable
   `admitted_at`. That holds for wake/review (`admitted_at ==` the run's `now`) and user turns
   (`admitted_at == occurred_at`), and is what makes replayed capability writebacks idempotent.
3. Local verification used CPython 3.11.2 while `pyproject.toml` declares `>=3.12`; CI must be the
   authoritative interpreter check (same limitation the board already records for earlier tasks).
4. Test-side fingerprint computation uses the store's canonical `_response_fingerprint` helper, the
   same helper the frozen PR #216 probe used; it is not a new public API surface.
5. Multi-round user turns (recovery resuming a round > 0) are exercised through the wake path; the
   user-turn test covers round 0.
