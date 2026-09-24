# CORE-HEADLESS-001-CORRECTIVE-001 Independent Acceptance — 2026-09-24

## Verdict

**ACCEPTANCE_PASS**

- Blocker count: **0**
- Review-time live `main`: `cf422cb882e659d4d024380aafa9b823499a103e`
- Candidate PR: #181 — `CORE-HEADLESS-001: installable persistent headless Core entrypoint`
- Corrected tested implementation exact head: `16e983a536b124ddb600981fc16326d9db54358f`
- Corrected evidence-only handoff: `f25218aac3812c4511351333704055ff90e7dd75`
- Historical tested implementation exact head: `a43c2e9408e51ec8812e9f6ec808a71401bc2841`
- Historical evidence-only handoff: `12928af4ffa40e70d9ae80124dab388a486f7097`
- Historical independent review #185: **ACCEPTANCE_FAIL**
- Historical blocker: `CORE-HEADLESS-001-ACCEPT-BLOCKER-001`
- Historical probe #184 head: `f36665541742badde3b7c20e24528668b5ba3f59`

PR #181 remains OPEN / UNMERGED. This review performs acceptance only, does not repair the candidate, does not merge #181, and does not enter CORE-RECOVERY-001, Resident, UI, or hardware.

## 1. Governance and exact pins

The current repository control files independently confirm:

`CORE-HEADLESS-001-CORRECTIVE-001 = GATE / REVIEW_READY`.

PR #181 was re-read at review time and remained:

- branch: `core-headless-001-20260924-sol`
- OPEN / non-draft / UNMERGED
- current handoff head: `f25218aac3812c4511351333704055ff90e7dd75`

The corrected exact-head boundary is valid:

- `16e983a536b124ddb600981fc16326d9db54358f -> f25218aac3812c4511351333704055ff90e7dd75`
- exactly one commit
- the only changed path is:
  `reviews/CORE_HEADLESS_001_COMPLETION_EVIDENCE_2026-09-24.md`

The implementation evidence is therefore pinned separately from the evidence-only handoff.

## 2. Historical FAIL preserved and independently re-established

The historical #185 verdict remains **ACCEPTANCE_FAIL** and is not rewritten.

At historical implementation head `a43c2e9408e51ec8812e9f6ec808a71401bc2841`,
`HeadlessConfig.__post_init__` independently selected:

`lock_path = caller-supplied resolved lock path`

when a lock path was supplied.

That made the real OS lease identity caller-selectable. The same durable `world.sqlite` could therefore be paired with `writer-a.lock` and `writer-b.lock`, producing two independent lock-file inodes.

Historical probe #184 was independently re-read:

- probe head: `f36665541742badde3b7c20e24528668b5ba3f59`
- run: `35992018738`
- job: `107608100032`
- PR: CLOSED / UNMERGED
- targeted result: `.........F [100%]`
- sole failure: the alternate-lock-path probe expected `HeadlessWriterBusy` but the second same-World writer opened.

This is a genuine historical bypass and remains the reason #185 failed.

## 3. Corrective scope — PASS

Comparison from historical evidence handoff
`12928af4ffa40e70d9ae80124dab388a486f7097`
to corrected tested implementation exact head
`16e983a536b124ddb600981fc16326d9db54358f`
shows only:

1. `src/aios_core/headless/core.py`
2. `src/aios_core/headless/cli.py`
3. `tests/integration/test_core_headless.py`

No `src/aios_core/runtime/**` path changed.

The corrective remains narrowly scoped to writer-identity configuration plus permanent regression tests. It does not redesign World storage, runtime, scheduler, recovery, cognition, metering, or provider semantics.

## 4. Canonical World -> one writer lease identity — PASS

At exact head `16e983a...`, `HeadlessConfig` now:

1. canonicalizes `world_path` with expanded/resolved path identity;
2. derives the actual lease path exclusively as:
   `<canonical-world>.writer.lock`;
3. treats caller-supplied `lock_path` only as validation input;
4. raises `HeadlessConfigurationError` if the supplied path differs;
5. overwrites the config field with the derived canonical lease path.

Therefore a caller cannot select a second lock-file inode for one canonical World.

The historical bypass mechanism is mechanically removed: alternate `lock_path` is rejected before `HeadlessCore.start()` can acquire another lease or open the World.

Hard-link identity and distributed-host coordination were not claimed by the corrective and are explicitly outside its required scope.

## 5. CLI `--lock` / `AIOS_LOCK_PATH` — PASS

The CLI help and build path were independently inspected.

- `--lock` remains a compatibility input but is explicitly validation-only.
- `AIOS_LOCK_PATH` feeds the same validation-only field.
- neither can choose the actual writer identity;
- a noncanonical value becomes `HeadlessConfigurationError` and CLI exit code 2;
- a canonical explicit value is accepted and still maps to the one derived lease.

Fresh probe #188 independently re-ran both CLI and environment override cases and also verified that rejected alternate lock paths are not created.

## 6. OS advisory lease semantics — PASS

The corrective preserves the existing process-held OS exclusion primitive.

POSIX path:

`fcntl.flock(fd, LOCK_EX | LOCK_NB)`

Windows path:

`msvcrt.locking(fd, LK_NBLCK, 1)`

Release remains the matching OS unlock followed by handle close.

The lock file metadata contains diagnostic PID/host/path information only. No code reads PID, host, or lock-file text to decide liveness or World truth. No in-process registry was introduced.

`HeadlessCore.start()` acquires the lease before opening `SQLiteWorldStore` / index / runtime. A writer-busy failure therefore fails closed before World startup. Cleanup releases the lease on startup failure and clean stop.

Fresh CI ran on Ubuntu; the POSIX primitive was exercised there. The Windows branch was verified by code inspection and is unchanged in exclusion semantics by the corrective.

## 7. Fresh independent adversarial probes — PASS

A dedicated probe-only PR was created from the corrected implementation exact head:

- PR #188 — `review probe: CORE-HEADLESS-001-CORRECTIVE-001 independent adversarial checks`
- probe base implementation: `16e983a536b124ddb600981fc16326d9db54358f`
- probe-only commit: `bf104da474049c3250b081a3d3616f172c4e8a9f`
- changed path: `tests/integration/test_core_headless.py` only
- final state: **CLOSED / UNMERGED**

Five new independent probes were added without modifying PR #181.

### Probe A — historical alternate lock bypass

Same durable World, live writer A, then caller attempts a textually unrelated alternate lock pathname.

Result:

- alternate `lock_path` raises `HeadlessConfigurationError`;
- alternate lock file is not created;
- World revision remains unchanged;
- a second valid same-World config is forced onto the canonical lease and raises `HeadlessWriterBusy`;
- after A stops, B acquires the same lease and opens the unchanged World.

**PASS**

### Probe B — textual relative/absolute alias

Used `alias/../world.sqlite` and the absolute resolved World.

Result:

- both canonical World paths are equal;
- both lease paths are equal;
- active A excludes B;
- failed B startup does not change World revision.

**PASS**

### Probe C — existing World symlink alias

After the target World existed, a symlink alias was created.

Result on the GitHub Actions Linux environment:

- symlink resolves to the same canonical World;
- lease identity is equal;
- live A excludes B reached through the symlink;
- failed B startup does not mutate World revision.

**PASS**

### Probe D — stale metadata artifact

After clean release, stale canonical lock-file text containing fake PID `424242` was written with no OS lease held.

Result:

- a new writer opens successfully;
- World revision is unchanged;
- stale text is replaced after acquisition.

This proves file contents are not liveness truth.

**PASS**

### Probe E — CLI / environment alternate path

Freshly exercised:

- CLI `--lock <alternate>`;
- `AIOS_LOCK_PATH=<alternate>`;
- canonical explicit lock path.

Result:

- both alternate forms exit as configuration errors;
- neither creates an alternate lock file;
- canonical explicit validation succeeds.

**PASS**

Fresh probe core-headless workflow:

- run: `35995070709`
- job: `107617941094`
- merge-ref checkout:
  `Merge bf104da474049c3250b081a3d3616f172c4e8a9f into cf422cb882e659d4d024380aafa9b823499a103e`
- CPython: `3.12.14`
- clean non-editable install: `pip install ".[dev]"`
- installed CLI smoke: World revision `0 -> 2 -> 2`, index watermark `0 -> 2`
- targeted headless suite: `.................. [100%]` = 18/18
  (the corrected 13 tests plus five fresh independent probes)
- runtime compatibility suite: `[100%]`
- workflow result: **SUCCESS**

## 8. Active competing writer / failed startup / release — PASS

The permanent corrected test and fresh probes jointly establish:

- writer A holds the canonical OS lease;
- writer B for the same canonical World fails with `HeadlessWriterBusy`;
- failed B startup occurs before World open;
- World revision/state remains unchanged;
- A clean stop releases the lease;
- B can then acquire and open the same World.

This closes the exact historical blocker.

## 9. Stale lock-file contents — PASS

Both the permanent corrected suite and fresh Probe D verify that a stale canonical lock-file pathname/body without an active OS advisory lease does not brick the World.

PID/host/text are diagnostic only.

## 10. Relative / absolute / symlink canonicalization — PASS

The corrected permanent suite contains:

- `test_headless_relative_and_absolute_world_share_writer_identity`
- `test_headless_symlinked_existing_world_shares_writer_identity`

Fresh probes independently used a different textual path shape and independently exercised an existing-World symlink while a writer was live.

All converge on one canonical World and one lease identity.

## 11. A-F restart matrix — PASS / no regression

The corrected exact head contains 13 dedicated HEADLESS tests and all 13 passed at the pinned exact-head run. The same 13 tests were then re-run in probe #188 alongside five fresh tests, for 18/18 total.

A. normal user turn + durable output + stop/restart same World:
**PASS**

B. pending Wake survives restart, remains processable, completed Wake is not redispatched:
**PASS**

C. FIX-003 pre-admission state survives restart, blind provider execution remains blocked, explicit recovery authorization permits one execution:
**PASS**

D. FIX-002 background IN_DOUBT survives restart with no blind provider reinvocation:
**PASS**

E. FIX-001 historical temporal read cutoff remains enforced in resumed background execution:
**PASS**

F. repeated start/stop does not fabricate duplicate turn/output/Wake/metering state:
**PASS**

## 12. FIX-001 / FIX-002 / FIX-003 compatibility — PASS

No accepted runtime implementation was changed by the corrective.

The exact-head and fresh probe HEADLESS compatibility suite both reached 100% and included existing coverage for:

- fused-turn runtime;
- Wake dispatch;
- Periodic Review;
- Reality ingest;
- C14 cognitive derivation runtime;
- AI World;
- execution World;
- FIX-002 background attempt recovery;
- FIX-003 turn execution recovery;
- CognitiveRuntime.

The dedicated HEADLESS tests also directly retain FIX-001 historical-cut, FIX-002 IN_DOUBT, and FIX-003 pre-admission/recovery scenarios.

No second World, runtime, scheduler, model-attempt ledger, turn-recovery ledger, cognition truth store, or provider contract was introduced.

## 13. Clean install / installed CLI — PASS

Exact `pyproject.toml` still states:

- `requires-python = ">=3.12"`
- console entrypoint:
  `aios-core-headless = "aios_core.headless.cli:main"`

Exact-head core-headless raw log confirms:

- CPython `3.12.14`
- clean non-editable `pip install ".[dev]"`
- `aios-core-0.3.0.dev0` installed normally
- pytest `8.4.2`
- pydantic `2.13.5`
- installed `aios-core-headless` ran across separate CLI invocations
- initial status: World/index `0 / 0`
- user turn: `HEADLESS_MECHANICAL_OK`, World revision `2`
- reopened status: World/index `2 / 2`, index lag `0`

Fresh probe #188 independently repeated this clean install + installed CLI smoke with the same continuity.

Provider loading remains through the existing provider-neutral `ModelHandler = RuntimeSnapshot -> ModelDirective` boundary; the deterministic handler is test-only and is not an implicit production default.

## 14. Required corrected exact-head Gates — PASS

All required runs were independently re-read from raw logs and are tied to corrected exact implementation head
`16e983a536b124ddb600981fc16326d9db54358f`.

GitHub checkout in each required run shows:

`Merge 16e983a536b124ddb600981fc16326d9db54358f into e7817b499856808e68490d8a2b07524f87a79da1`

| Gate | Run | Job | Raw-log result |
|---|---:|---:|---|
| core-headless | `35993796247` | `107613844756` | **SUCCESS**; 13/13 corrected HEADLESS tests; compatibility 100%; installed CLI continuity 0 -> 2 -> 2 |
| world-kernel | `35993796267` | `107613844605` | **SUCCESS**; 24 passed |
| constitutional-cognition-closure | `35993796265` | `107613844757` | **SUCCESS**; 91 passed + P16 harness 92 passed |
| full P16 | `35993796249` | `107613844795` | **SUCCESS**; direct `pytest -q`; 675 pass markers |

Required exact-head environment was independently re-read as:

- CPython `3.12.14`
- pytest `8.4.2`
- pydantic `2.13.5`

No failed/error result was found in these required Gate logs.

## 15. Full P16 — PASS

Required exact-head full P16:

- run: `35993796249`
- job: `107613844795`
- command: direct `pytest -q`
- result: `[100%]`
- independently counted pass markers: **675**
- workflow/job: **SUCCESS**

As supplemental live-main compatibility evidence, fresh probe #188 also automatically ran full P16 after adding five probe tests:

- run: `35995070680`
- job: `107617940907`
- merge-ref: corrected candidate/probes into review-time main `cf422cb...`
- direct `pytest -q`
- pass markers: **680**
- result: **SUCCESS**

This supplemental run does not replace the required exact-head run; it confirms that the governance-only live-main drift does not introduce a regression.

## 16. Supplemental fresh workflow set — PASS

Probe #188 automatically exercised all four relevant workflows against the corrected implementation plus independent probe tests:

| Gate | Run | Job | Result |
|---|---:|---:|---|
| core-headless | `35995070709` | `107617941094` | **SUCCESS**; 18/18 targeted |
| world-kernel | `35995070893` | `107617941955` | **SUCCESS**; 24 passed |
| constitutional-cognition-closure | `35995070706` | `107617941242` | **SUCCESS**; 91 + 92 passed |
| full P16 | `35995070680` | `107617940907` | **SUCCESS**; 680 pass markers |

PR #188 was then closed unmerged after evidence capture.

## 17. Live-main drift — COMPATIBLE / no rebase revalidation required

Final review-time main:

`cf422cb882e659d4d024380aafa9b823499a103e`

Compared with the corrective final live-main recheck
`e7817b499856808e68490d8a2b07524f87a79da1`,
the only changed paths are:

- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `governance/prompts/CORE_HEADLESS_001_CORRECTIVE_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

There is no relevant `src/**`, packaging-contract, HEADLESS test-contract, or workflow semantic drift.

Therefore `REBASE_REVALIDATION_REQUIRED` does not apply.

## 18. Final decision

**ACCEPTANCE_PASS**

**Blocker count: 0**

`CORE-HEADLESS-001-ACCEPT-BLOCKER-001` is independently closed at the corrected exact implementation head because one canonical World now mechanically maps to one derived writer lease identity and caller-supplied lock paths cannot select a second exclusion inode.

All required restart, FIX-001/FIX-002/FIX-003, installation/CLI, exact-head Gate, full-P16, stale-artifact, alias, and fresh adversarial checks pass.

PR #181 remains unmerged and is ready only for PM integration.

**PR #181 CORE-HEADLESS-001-CORRECTIVE-001 tested exact implementation head 16e983a536b124ddb600981fc16326d9db54358f with evidence-only handoff f25218aac3812c4511351333704055ff90e7dd75 is independently accepted for PM integration.**

This review stops here and does not enter CORE-RECOVERY-001.
