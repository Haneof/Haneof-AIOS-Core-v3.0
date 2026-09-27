# CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001 — Candidate Evidence Report

Status: `GATE / REVIEW_READY`. Not self-accepted. Not merged. Not an Independent Acceptance.

Handoff: `LOCAL_REVIEW_READY / REMOTE_HANDOFF_BLOCKED`

This window had no GitHub write credentials (`git push` failed: could not read Username for https://github.com). No remote SHA is claimed for the corrective commits. PR #219 was not updated from this window. The local candidate is preserved on branch `engineering`, which tracks `origin/arena/01a0dcf6-haneof-aios-core-v3-0`.

## 1. Identity

| Item | Value |
|---|---|
| Repository | `Haneof/Haneof-AIOS-Core-v3.0` |
| Engineering PR | #219 (existing; no competing PR created) |
| Branch | `arena/01a0dcf6-haneof-aios-core-v3-0` (local `engineering`) |
| Live main used for construction/revalidation | `acf8ac3ea3e8da2b5c77e81534ba62d5166879f2` |
| New tested exact candidate | `030acbfe2d935dfc166ff7a9a1760b6ddd46d42d` |
| Parent | `b8bc7b32497dc0fdc0a15194256795a7c6771048` (merge of live main into the engineering branch) |
| Exact tree | `b1c39039db6c48e2aa6fb111b03394eb5d0b8f9c` |
| Historical failed tested exact | `3f9ec00d0fa283bc5294574d6da1e84d654d6645` |
| Historical failed tree | `4e9e3a5685373f46ba56d51259f39af710a3cf53` |
| Historical verdict | `ACCEPTANCE_FAIL`, blocker count = 2 |
| Reviewer-local evidence commit | `5c59f17658524c0ad23f409a8c108402cea34452` — not a remote GitHub object |

`3f9ec00d...` remains reachable and is not redescribed as PASS. Its tree is unchanged. Historical author red logs under `reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001/red/` are unchanged from engineering head `2ea8dd03`.

## 2. What closed the two blockers

### IA-BLK-001

`mark_dispatching()` now commits a `background_model_request_bindings` row in the existing runtime SQLite database, in the same transaction as the `admitted → dispatching` transition, before the provider handler runs. The row binds:

- subject
- work kind
- work id
- model round
- background attempt id
- outbound request fingerprint
- relay id derived only from those fields (`relay_id_for`)

The recovery caller does not supply this token. `stage_exact_response()` loads the pre-existing row and, for `dispatching` / `in_doubt`, requires the exact response's provider request id to echo that stored relay id. Copying work A's self-consistent response, including A's request id, onto work B fails before any staged row is inserted and before attempt provenance is rewritten.

This is not a second World or cognition store. `in_doubt` and `not_submitted` semantics are unchanged. Recovered rounds still do not redispatch the provider.

Honest limitation: Core still has no provider signature. A party who can read B's already-stored relay id can construct a *new* directive that echoes it. That is the legitimate journal shape for B, not a transplant of A's exact bytes. No operator semantic judgment is used.

`response_returned` / `metered` attempts already have in-process provenance. Staging those still must find a consistent pre-dispatch binding and must match that recorded provenance. The normal provider path is not forced to replace its own request id with the relay id.

### IA-BLK-002

`decode_model_directive()` parses with `object_pairs_hook` and raises on a duplicate key before the object is returned and before `ModelDirective` is constructed. The hook runs for every JSON object, including nested `usage`, `provenance`, capability-call objects, and nested `arguments`. There is no last-key-wins pass and no normalize-then-compare.

A rejected duplicate payload does not insert a staged row, does not move the attempt to `response_returned`, and does not create capability, assistant-output, metering, or World-revision effects.

## 3. Red-first evidence (preserved, not overwritten)

Old implementation, before the fix, Python 3.12.14:

- `reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001/red/red_before_fix_pytest.txt`
  - cross-work, copied token+response, wake→periodic_review, periodic_review→user_turn, cross-subject, identical provider/model: `DID NOT RAISE`
  - duplicate-key matrix (response, silence, capability_calls, nested usage, nested provenance, capability name, nested arguments): `DID NOT RAISE ValueError`
  - the first cross-round case in that log is a setup error (`TimeoutError` not raised) because round 0 was terminal; it is preserved and not edited into a success
- `reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001/red/red_before_fix_cross_round.txt`
  - corrected cross-round probe, still before the fix: staging `DID NOT RAISE`

Historical author red logs were not deleted or rewritten green.

## 4. Green evidence at the tested exact SHA

Environment (`reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001/environment.txt`):

- Python 3.12.14
- pytest 8.4.2
- pydantic 2.13.5

Blocker probes plus original fault matrix, after the fix: all passed (included in the focused log).

Focused runtime regression (`focused_regression.txt`): `159 passed`, exit 0. Covers background attempt, CognitiveRuntime, turn-execution recovery, metering, Wake, Periodic Review, fused turn / user turn, headless, core recovery, FIX-002 background attempts, the original 10-case fault matrix, and the corrective probes including two real `SIGKILL` process tests.

Full `pytest -q` (`full_suite.txt`, junit `full_suite_junit.xml`):

- `734 passed, 1 failed`, exit 1, 168.07s
- the single failure is `tests/preflight/test_round5_fixes.py::test_isolation_exception_classification_namespace_permission`
- same Python 3.12.14 environment against clean live main `acf8ac3e` fails the same assertion (`red/main_control_isolation_same_env.txt`, exit 1)
- classification: pre-existing / environmental. This sandbox has no non-symlink `/usr/bin/python3.11`, `/usr/bin/python3.12`, or `/usr/bin/python3.10`, and `/usr/bin/python3` is a symlink, so the isolation probe raises `no suitable python interpreter found` before the patched `unshare` permission path. The isolation test was not modified. The gate was not relaxed. Production semantics were not changed to accommodate it.

Process-kill evidence is in the corrective test module:

- exact response staged, then `SIGKILL`, reopen, recover, provider call count 0
- capability side effect committed, then `SIGKILL`, reopen, recover, one task revision, recovered round does not call the provider

## 5. Scope

Changed in the tested exact commit only:

- `src/aios_core/runtime/background_attempt.py`
- `src/aios_core/runtime/cognitive_runtime.py`
- `src/aios_core/runtime/turn_runtime.py`
- `tests/integration/test_core_background_response_recovery_001.py`
- `tests/integration/test_core_background_response_recovery_001_corrective_001.py`
- `tests/integration/test_core_gap_fix_002_background_attempts.py`
- `tests/runtime/test_background_model_attempt.py`

Diff stat of that commit: 7 files, +1310 / -15.

Not done, and not authorized from this window:

- merge PR #219
- self-acceptance
- `CORE-RC-REFREEZE-002`
- B persistence corrective
- Resident
- sealed fixture or historical Resident evidence changes
- PR #216 frozen WIP changes
- second World / cognition store
- provider redispatch on recovery
- weakening `in_doubt` or `not_submitted`

If CI runs on a future push, the two fixture-task zero-Core-diff checks are expected to stay RED for this genuine Core change. They must not be relabeled SUCCESS.

## 6. Required next step

Fresh `CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE` by a different reviewer, against tested exact `030acbfe2d935dfc166ff7a9a1760b6ddd46d42d`.

This window stops at `REVIEW_READY`.
