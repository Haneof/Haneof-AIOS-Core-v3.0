# CORE-BACKGROUND-LATE-TRUSTED-RETURN-001 — baseline RED manifest

Task: `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001` · Window `13`
Baseline: live `main` `25591825d88e98f30dfd3de1c7e7cbc6e53267dd`

## How the baseline was produced (reproducible)

```text
git worktree add --detach /tmp/baseline_wt origin/main
#   -> 25591825d88e98f30dfd3de1c7e7cbc6e53267dd
# only the 4 new probe files were copied in; src/aios_core/**, tools/** and
# every pre-existing test were byte-identical to main.
pytest -o addopts='' -q --tb=line \
  tests/integration/test_core_background_late_trusted_return_001.py \
  tests/integration/test_core_background_late_trusted_return_001_not_submitted.py \
  tests/integration/test_core_background_late_trusted_return_001_adversarial.py
```

Result: **56 failed, 5 passed, 0 errors** — `baseline_red_raw.txt`.

Probe sources used for that run (sha256, also the sources executed for GREEN):

| file | sha256 |
|---|---|
| `tests/integration/late_trusted_return_fixture.py` | `159e557a99f6790340965a6c8ae9ba95c99837a34c954062ab2eb11056fab33b` |
| `tests/integration/test_core_background_late_trusted_return_001.py` | `7482c69a734946ac61d56652c5db355e14841cff8db988849af5b80c3432c70d` |
| `tests/integration/test_core_background_late_trusted_return_001_not_submitted.py` | `94bb807fb196e2c8291626d3dfab28952468465722fea1aad40001e165b892a4` |
| `tests/integration/test_core_background_late_trusted_return_001_adversarial.py` | `ac0a576c3743b5abef5b4fa4cc0cf27875a02526d6d924244d6e5c9dc28516b5` |

## RED-first history

An earlier freeze-time capture also exists, taken **before any production line was
written** on this branch: `baseline_red_preimplementation_capture.txt`
(**35 failed, 5 passed**). It predates the adversarial probe file and two documented
harness revisions listed below. The authoritative, reproducible baseline above was
produced with the final probe sources so that a reviewer can re-run it byte-for-byte
and get the same result.

## Failure classification at baseline

### `PRODUCT_RED` — class B: the post-dispatch durable false state is writable today

**7 probes** fail with

```text
Failed: DID NOT RAISE <class 'aios_core.runtime.background_attempt.BackgroundModelResponseConflict'>
```

These use **only already-accepted public Core API** and reference no new symbol, so
they are an unambiguous product RED rather than a missing-feature artifact. They
prove that on unchanged `main`, after the provider dispatch boundary was already
crossed (`request published` → Core process death → `dispatching` / `in_doubt`),
`BackgroundModelAttemptStore.reconcile_not_submitted(...)` **succeeds** and durably
writes `state='not_submitted'` plus caller-supplied `reconciliation_evidence`.

This is the mechanical enabler recorded by the WINDOW 12 adjudication as the Core half
of `IA-B-R003-BLK-002` (`FALSE_NOT_SUBMITTED_RECONCILIATION`): absence of a
trusted-return receipt is used as if it were proof of non-submission.

Probes: `test_ns_r2_post_dispatch_reconcile_not_submitted_is_mechanically_refused`
(×2), `test_ns_r2_false_state_cannot_be_written_even_with_a_verbose_justification`,
`test_ns_r3_missing_receipt_alone_never_justifies_not_submitted`,
`test_ns_r5_caller_forged_non_submission_assertion_fail_closed`,
`test_ns_r5_runtime_level_turn_reconciliation_is_refused_after_dispatch`,
`test_ns_r6_legitimate_late_return_proof_uses_attach_not_reconciliation`,
`test_a3_..._post_dispatch_false_non_submission_assertion`.

### `PRODUCT_RED / ABSENT_CAPABILITY` — class A: no legal late-return attach path

**49 probes** fail because Core exposes no surface for a trusted external return that
arrives after the Core process died:

| mechanism | count | meaning |
|---|---|---|
| `FusedTurnRuntime.__init__() got an unexpected keyword argument 'external_return_observer'` | 42 | Core has no way to register an authorized observer of the real external return, so no per-attempt return capability can ever be issued |
| `'BackgroundModelAttemptStore' object has no attribute 'attach_late_trusted_return'` | 2 | no public late-return attach entry point |
| `'BackgroundModelAttemptStore' object has no attribute 'late_trusted_return_state'` | 1 | no observability for the capability lifecycle |
| `No module named 'aios_core.runtime.late_return'` | 1 | no one-shot return-capability type at all |
| `child exit=1` (real SIGKILL probe) | 1 | the subprocess dies before crossing the boundary, because the capability-issuing dispatch path does not exist |
| `test_a1` public-surface audit (`__weakref__` assertion) | 1 | the audit cannot even enumerate the intended surface |
| `... is admitted` (`test_ltr_r3_pre_dispatch_attempt_has_no_return_capability_at_all`) | 1 | existing correct Core refusal (`stage_exact_response` on a pre-dispatch attempt); the probe expects the *new* surface to refuse the same attempt — recorded so the baseline is not read as claiming a pre-existing defect |

`ABSENT_CAPABILITY` is a **product** RED, not a harness artifact: the adjudication
already established by source reading (`turn_runtime.py:1304-1326`,
`background_attempt.py:811-921`, `:1257`, `:1462`) that for a `dispatching` /
`in_doubt` attempt there is no legal continuation. This suite makes that absence
mechanically reproducible instead of only source-asserted.

### The 5 baseline passes

`test_ns_r1_in_process_definitely_not_submitted_dispatch_failure_still_retries`,
`test_ns_r1_pre_dispatch_attempt_...` variant pieces, and the receipt/metadata
invariants that were already correct on main. They are regression guards, and they
are green both before and after.

## Harness issues encountered (revision history, not product blockers)

Every harness defect found while freezing is recorded here so no window mistakes one
for a product finding. No probe was deleted, and no expected outcome was changed after
seeing a result.

| revision | issue | classification |
|---|---|---|
| r1 | probes passed `external_return_observer=None` unconditionally, so even the class-B probes died on a constructor `TypeError` instead of reaching the real defect | `REVIEWER/HARNESS FALSE POSITIVE` — probes were made observer-free unless the late-return path was under test |
| r2 | user-turn restart refuses at the turn-execution claim *before* the attempt admission guard, so the attempt stays `dispatching` rather than `in_doubt`; probes hard-coded `in_doubt` | `REVIEWER/HARNESS FALSE POSITIVE` — probes now accept either post-crash state and reach `in_doubt` deterministically through `admit()` itself |
| r3 | `late_trusted_return_state` readback compared a SQLite `0/1` to a Python `bool`; the seeded anchor object id collided when a second attempt was created; a `multiprocessing.Queue` feeder thread is raced by `SIGKILL` | `REVIEWER/HARNESS FALSE POSITIVE` — fixture casts to `bool`, seeds a unique object id, and the SIGKILL probe uses a synchronous `Pipe` |
| r4 | one accepted test hard-coded a `dispatching` state where `in_doubt` was meant, and one accepted test used a walrus in a positional slot | `REVIEWER/HARNESS FALSE POSITIVE` — fixed without changing any expected outcome |

## One deliberate design finding during implementation (not a harness issue)

The first implementation exposed capability issuance as
`BackgroundModelAttemptStore.issue_external_return_capability`, a **public** method
returning the proof-minting nonce. That is a signing oracle, and it was closed during
a self-audit before the candidate was formed: the method is now private
(`_issue_external_return_capability`), mirroring the accepted
`_capture_trusted_response_return`, and `test_a1_capability_issuer_is_not_publicly_callable`
plus `test_a1_recovery_caller_cannot_self_issue_a_capability` lock it down.

## Runtime of this capture

```text
CPython 3.11.2 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.40.1 / OpenSSL 3.0.20
```

This is a **development** capture only. Per the task's formal-environment rule it is
**not** presented as the formal gate; the formal gate is GitHub CI on
**CPython 3.12.14** (pinned `pydantic==2.13.5`, `pytest==8.4.2`) — see
`green_ci_formal_31214.txt`.
