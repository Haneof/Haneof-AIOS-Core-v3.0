# CORE-RC-FREEZE-001 Completion Evidence — 2026-09-24

Status: **REVIEW_READY**  
Task: `CORE-RC-FREEZE-001`  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Engineering/release PR: **#202 — OPEN / UNMERGED**  
Exact RC-freeze candidate: `11f4aed2eba055356730dc77922ced39b25a7d63`  
Frozen software SHA inside candidate: `773876f92d5f8e53422f8f5a68cc651953d93052`  
Resident runs performed by this task: **0**  
Public release/tag performed: **NO**


## 0. Candidate / handoff pins

- Frozen software RC commit: `773876f92d5f8e53422f8f5a68cc651953d93052`.
- Tested exact RC-freeze packet candidate: `11f4aed2eba055356730dc77922ced39b25a7d63`.
- Candidate -> final PR handoff is evidence-only: the next commit changes only this completion-evidence report.
- At exact candidate `11f4aed2...`, compare against frozen main changes exactly seven documentation/governance files:
  - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
  - `PROJECT_MASTER_MAP.md`
  - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
  - `release/rc/CORE_RC_FREEZE_001_DEPENDENCIES.json`
  - `release/rc/CORE_RC_FREEZE_001_MANIFEST.json`
  - `release/rc/CORE_RC_FREEZE_001_OPERATOR_PACKET.md`
  - `reviews/CORE_RC_FREEZE_001_COMPLETION_EVIDENCE_2026-09-24.md`
- Candidate protected software delta is exactly zero:
  - `src/aios_core/** = 0`
  - `tests/** = 0`
  - `.github/workflows/** = 0`
  - `pyproject.toml = 0`

## 1. Exact freeze target

RC-FREEZE started from and continued to observe live `main` at:

`773876f92d5f8e53422f8f5a68cc651953d93052`

Exact frozen software/evidence boundary:

- repository tree: `2cc91595532fcd437b7aaa4efebd39ca9a0b3786`
- Core tree `src/aios_core/**`: `fe77f8a0706acfaf369041d0882b6d0e6de39f22`
- tests tree `tests/**`: `815a3a460f14d073cf07d6191ea4c3edfd5457e5`
- workflow tree `.github/workflows/**`: `8d1ea1cbb9993f9ff29155e4d04833bd53b45272`
- `pyproject.toml` Git blob: `b38833c7537fa60d5c2f02ed4bb19158d8995a11`
- `pyproject.toml` SHA256: `993a6e9dd821d8d5885f4cc1f2da0aa34d40284618097a1de507e885f2eaab30`
- constitution registry SHA256: `8bb6e2e0d9f6b87e41a291f74f4a0841565588d807442360e01314e3efa78f06`
- start task-board SHA256: `95ae56fe2de3baf1dc038c541a242431d61f265314133fbf815cb4de6deef34d`
- start checkpoint SHA256: `591a4deb135d9f1bb24cdff67cfcc069dd3d66bf9f1c614136d836da0e1f3820`

The machine-readable source manifest is:

`release/rc/CORE_RC_FREEZE_001_MANIFEST.json`

It was generated mechanically from the frozen commit and contains SHA256 plus Git blob identity for all 77 tracked `src/aios_core/**` files and all 39 release workflow files. Private Resident Worlds, private run databases, credentials and generated caches are excluded.

## 2. Prerequisite closure

The task-board/checkpoint were re-read at live main and confirmed:

`CORE-RC-FREEZE-001 = READY`.

Every activated S2 prerequisite is accepted and integrated:

- FIX-001: #145 merged as `d97a1bfa527caadb4ab22d232fd627c0483e02d8`.
- FIX-002: #143 merged as `3d980fadf6beefcdd02ff4367ba834a5b013d871`.
- CI-FIX corrective: #146 merged as `c3ec42214db57864f7951e28b75811b10db8be21`.
- FIX-003: #157 merged as `78c103322b14c60cabf92174b0b5a7385752d758`.
- HEADLESS: #181 merged as `6ccd79d93f8fa8845bf392bd3c1ef0641ad1cde6`; corrective independent acceptance #189 = ACCEPTANCE_PASS / blocker 0.
- RECOVERY: #191 merged as `17e3807024359e990890ff4c249e55da93886475`; independent acceptance #195 = ACCEPTANCE_PASS / blocker 0.
- SCALE: #197 merged as `46c7cf9771274559b42dade9359e2e2cae5f245f`; independent acceptance #200 = ACCEPTANCE_PASS / blocker 0.

No currently accepted-but-unmerged Core candidate was found that should be pulled into the RC.

## 3. Open-PR contamination review

Open PRs were inventoried directly from GitHub. Classification for release-relevant/history-bearing open PRs:

| PR | Classification | RC disposition |
|---|---|---|
| #144 | SUPERSEDED / NOT INTEGRATED | Historical first CI-FIX line; corrective accepted/integrated elsewhere. Do not merge. |
| #130 | SUPERSEDED / NOT INTEGRATED | Competing CORE-OPERATOR candidate; task board explicitly supersedes it. |
| #126 | SUPERSEDED / NOT INTEGRATED | Old draft branch; its ten Core fixes were separately integrated through #127. Do not bulk merge. |
| #125 | SUPERSEDED / NOT INTEGRATED | BLOCKED / DO NOT MERGE historical C15 preflight line. |
| #121 | HISTORICAL EVIDENCE ONLY | Failed/non-canonical historical Resident B package. |
| #119 | OUT_OF_SCOPE | Governance-only anchor reconciliation. |
| #118 | OUT_OF_SCOPE | Governance-only single-anchor plan. |
| #117 | HISTORICAL EVIDENCE ONLY | Canonical historical Resident A; retained pinned, never hash-swapped. |
| #113 | INTEGRATED | C15 hardening content integrated through accepted #115 route; old open PR is not a new RC candidate. |
| #112 | HISTORICAL EVIDENCE ONLY | Historical SCALE benchmark/risk clue only. |
| #111 | INTEGRATED | C15 cognition-field content integrated through accepted #115 route. |
| #110 | INTEGRATED | C15 evidence-policy content integrated through accepted #115 route. |
| #109 | HISTORICAL EVIDENCE ONLY | Older Resident-A rerun evidence, superseded by canonical #117. |
| #107 | HISTORICAL EVIDENCE ONLY | Historical blocked startup evidence. |
| #101 | HISTORICAL EVIDENCE ONLY | PRE-FIX diagnostic/superseded Resident A run. |
| #92 | HISTORICAL EVIDENCE ONLY | Pinned C14 semantic-repair Resident evidence. |
| #79 | HISTORICAL EVIDENCE ONLY | Pinned C14 Resident B evidence. |
| #75 | HISTORICAL EVIDENCE ONLY | Pinned C14 Resident A evidence. |
| #74 | HISTORICAL EVIDENCE ONLY | Older draft C14 A evidence. |
| #37 | OUT_OF_SCOPE | Historical P16 triage review. |
| #202 | OUT_OF_SCOPE (current task PR) | This RC-FREEZE release/evidence PR itself, not contamination. |

**BLOCKER — MUST RESOLVE BEFORE FREEZE: none found.**

No old PR was merged, closed, deleted or pulled into the RC by this task.

## 4. Fresh software-only regression

A transient release-probe branch was constructed from the exact frozen main. Its test-trigger commits modified workflow comments/probe infrastructure only; they did not alter `src/aios_core/**`, `tests/**`, or package semantics. The final RC candidate removes all transient workflow changes.

Fresh successful probe source head:

`58de2e39bc6acd06eb9b5dcf93b846560685f524`

That head executes the frozen Core/test/package tree.

Fresh workflows — all **SUCCESS**:

- full P16 convergence: `36019155127`
- RC non-editable clean-install/full-regression probe: `36019155145`
- world-kernel: `36019155008`
- world-index: `36019154864`
- memory-recommendation: `36019154801`
- fused-turn-runtime: `36019154857`
- C09 Wake: `36019154941`
- P15 Periodic Review: `36019154821`
- C14 runtime: `36019155213`
- C14 scheduler: `36019154823`
- C14 loop: `36019154793`
- constitutional cognition closure: `36019154893`
- HEADLESS: `36019154789`
- RECOVERY: `36019154783`
- SCALE: `36019154843`
- P9 revision: `36019154840`
- P10 AI-world: `36019154749`
- P11 dimension: `36019155156`
- P12 execution: `36019154854`

The RC probe itself ran direct `pytest -q` to 100% with no failure and then separately reran the bounded writer/recovery/FIX/SCALE semantic subset to 100%.

No Resident or sealed habitation life was executed.

## 5. Clean non-editable install / environment freeze

Fresh RC probe `36019155145` built a wheel and installed it non-editably.

Recorded environment:

- CPython 3.12.14
- Linux `6.17.0-1022-azure`, x86_64 / 64-bit ELF
- SQLite 3.45.1
- `aios-core 0.3.0.dev0`
- build backend: `setuptools.build_meta`
- console entrypoint: `aios-core-headless = aios_core.headless.cli:main`
- pydantic 2.13.5
- pytest 8.4.2

Exact environment and installed distributions are frozen in:

`release/rc/CORE_RC_FREEZE_001_DEPENDENCIES.json`

The repository continues to use bounded dependency ranges rather than a lockfile. RC-FREEZE does not silently introduce a new lockfile/release policy.

## 6. Clean-install HEADLESS smoke

Fresh installed-wheel smoke passed:

1. new disposable World opened at world revision 0 / index watermark 0;
2. deterministic mechanical turn returned `HEADLESS_MECHANICAL_OK`;
3. completed turn advanced World revision to 2;
4. new process status reopened the same World with revision 2 / index watermark 2 / index lag 0;
5. durable turn inspection succeeded;
6. no provider credential or Resident fixture was required.

This is software smoke only.

## 7. Backup / restore / index rebuild smoke

Fresh RC smoke on a disposable World passed:

- normal mechanical turn produced World revision 2;
- source logical state before backup:
  - object revisions = 2
  - background model attempts = 1
  - metering records = 1
- supported SQLite online backup completed;
- source authoritative logical state remained unchanged;
- restore to a different World path completed at World revision 2;
- rebuilt index reached watermark 2 with 2 indexed rows;
- restored World reopened with index lag 0;
- restored logical World/execution/metering identity exactly matched source.

The online SQLite backup may checkpoint/rewrite main-database page layout, so raw main-DB file SHA can change while authoritative logical state remains unchanged. The accepted Recovery contract separately proves the immutable **backup snapshot** bytes are not modified by restore/rebuild. No raw live-file copy is treated as a supported backup.

## 8. Writer / restart smoke

Fresh targeted tests passed for:

- active same-World competing writer fails closed;
- canonical World identity determines the writer lease;
- alternate caller-supplied lock path cannot bypass writer exclusion;
- relative/absolute and symlinked same-World identities share exclusion;
- stale lock-file metadata without a live OS lease does not prevent restart;
- clean stop releases the lease;
- restarted same World continues durable state and due work.

No distributed multi-host/HA writer claim is made.

## 9. FIX-001 / FIX-002 / FIX-003 spot checks

Fresh targeted RC suite passed:

### FIX-001

`test_headless_restart_keeps_fix001_historical_knowledge_cut` plus SCALE temporal-cut semantics prove historical execution excludes later-known data while current-time control sees current state.

### FIX-002

Fresh background-attempt regressions prove Wake and Periodic Review ambiguous provider dispatch remains `IN_DOUBT` across restart and does not blindly reinvoke the provider. Safe retry is limited to mechanically proven/authorized states with stable attempt identity.

### FIX-003

Fresh turn-execution recovery regressions prove ambiguous user-turn dispatch remains `IN_DOUBT`, preserves stable execution identity, does not mint a replacement turn/provider attempt, and requires existing reconciliation/authorization semantics before retry.

No FIX was weakened or modified by RC-FREEZE.

## 10. SCALE provenance at final RC

RC-FREEZE does not rerun the one-million corpus because the frozen RC contains **zero Core/SCALE-harness/SCALE-semantic-test drift** from independently accepted SCALE implementation head:

`ba23767d4c1565fbe494419dd01c32123495884c`

to frozen main:

`773876f92d5f8e53422f8f5a68cc651953d93052`.

Fresh RC `core-scale` run `36019154843` reran the bounded semantic-equivalence/correctness surface successfully.

Accepted fresh S1M provenance remains pinned to independent run `36013144779`:

- one million current Claim objects;
- 1,020,000 Claim revision rows;
- 998,000 active / 2,000 retracted;
- explicit 4 GiB `RLIMIT_AS`;
- core-context p95 about 4.043 s;
- snapshot p95 about 5.609 s;
- recall p95 about 0.427 s;
- recall SQL max 54.

The historical baseline red run `36007169180` remains preserved and is not rewritten.

## 11. Historical #117 impact decision

Historical canonical Resident A #117 exact evidence head:

`3e51f728d7959048b75fea01d405bc837b0e8185`

has Core tree:

`eed27d58041dbaf2ceb0a65c1305bb332aef082e`

which exactly matches its historical frozen Core anchor
`bcd6bf353126318f9a97076b52ec1740d43f35a4`.

The new frozen RC Core tree is:

`fe77f8a0706acfaf369041d0882b6d0e6de39f22`.

Old anchor -> new RC includes Resident-visible/execution-relevant changes in cognition, context continuity, retrieval/search, recommendation, Periodic Review, Wake, runtime/turn execution, background provider-attempt recovery, summaries/scheduler, HEADLESS and Recovery paths.

The required impact disposition is therefore:

**FRESH_A_REQUIRED**

Historical #117 remains valid historical evidence for the old frozen Core only. It is not rewritten, rebased, or hash-swapped onto this RC.

After RC-FREEZE receives fresh independent acceptance and PM integration, the next Resident chain must start with a new fresh private World and fresh-context A on the frozen RC.

This task does not run that A.

## 12. Preserved RC probe red evidence

RC-FREEZE preserves its own probe mistakes rather than relabeling them green:

- `36016762621`: probe incorrectly required the main SQLite DB file SHA to remain byte-for-byte identical across online backup. Logical source state was unchanged; the assertion over-specified SQLite checkpoint/page-layout behavior.
- `36017499523`: restore/index operations had succeeded, but probe inspection queried nonexistent column `object_revision` instead of authoritative `revision`.
- `36019994350`: all software validation steps succeeded; a later attempt to auto-materialize manifests failed because the probe script used a literal `$RUNNER_TEMP` path inside Python. This is evidence-publishing harness failure, not a Core failure.

No Core bug was repaired in response to these probe failures. The successful canonical software probe is `36019155145`.

## 13. Operator packet and known limitations

Operator packet:

`release/rc/CORE_RC_FREEZE_001_OPERATOR_PACKET.md`

Known limitations carried without concealment:

- no public UI/hardware/platform completion claim;
- no phone/wearable performance claim from GitHub SCALE data;
- S1M World was mechanically bulk-loaded into production schemas rather than produced by one million production write API calls;
- S1M search projection was mechanically loaded for fixture practicality;
- no finite GitHub cgroup/swap value was observed; S1M memory proof uses explicit 4 GiB `RLIMIT_AS`;
- no distributed multi-host writer/HA claim;
- provider/token cost remains UNKNOWN where not directly measured;
- deterministic mechanical smoke is not Resident/real-provider semantic evidence;
- this software RC is not AIOS Core-complete until the applicable fresh Resident/C16/broad-P16/P17 gates pass;
- no public release/tag is authorized by this task.

## 14. Freeze verdict

Software blockers found: **0**.

All mandatory RC-FREEZE deliverables and software checks are satisfied.

**REVIEW_READY**

PR #202 must remain OPEN / UNMERGED and be evaluated by a fresh Independent Acceptance window. The author does not self-accept. Resident A/B/C, C16, broad P16, P17, UI and hardware remain outside this window.
