# CORE-RC-FREEZE-001

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Role:
Release PM / Release Engineer

You are not:
- Resident A/B/C
- Semantic Evaluator
- feature engineer
- cognition redesign engineer
- UI engineer
- hardware engineer

Your only task:

> Freeze the exact software release-candidate boundary after accepted GAP fixes + HEADLESS + RECOVERY + SCALE, generate reproducible manifests and final software-only regression evidence, and produce the impact/rerun decision required before any fresh Resident execution.

This task is a freeze and evidence task.
It is not permission to redesign or repair Core.

If a real blocker is found:
STOP, preserve evidence, and route a minimal corrective task back through independent acceptance.
Do not repair inside RC-FREEZE unless the PM explicitly dispatches a separate corrective task.

## 1. Required start

1. Fetch current live `main`.
2. Read:
   - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
   - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
   - `PROJECT_MASTER_MAP.md`
   - `governance/AIOS_CORE_COMPLETION_PLAN_2026-09-24.md`
   - `docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md`
   - `governance/CORE_CI_FIX_001_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_GAP_FIX_001_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_GAP_FIX_002_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_GAP_FIX_003_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_HEADLESS_001_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_RECOVERY_001_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_SCALE_001_INTEGRATION_RECEIPT_2026-09-24.md`
   - final independent acceptance reports for HEADLESS / RECOVERY / SCALE.
3. Confirm:
   `CORE-RC-FREEZE-001 = READY`.
4. Confirm every prerequisite task is DONE and integrated.
5. Confirm there is no currently accepted-but-unmerged Core candidate that should be part of the freeze.
6. Do not run Resident.

## 2. Freeze target

Use the live main software tree after all accepted S2 integrations.

Pin:
- exact live main SHA;
- exact `src/aios_core/**` tree SHA;
- exact `tests/**` tree SHA;
- exact workflow/config tree relevant to release;
- `pyproject.toml` hash;
- constitution registry hash;
- governance task-board/checkpoint hashes;
- Python/runtime dependency versions.

The freeze target is an exact software/evidence boundary, not a moving branch name.

No tag/public release is authorized by this task unless separately requested.
Do not claim P17 release.

## 3. Open-PR / branch contamination review

Inventory open PRs that touch any of:
- `src/aios_core/**`
- `tests/**`
- `.github/workflows/**`
- `pyproject.toml`
- Core release/runtime/recovery/scale surfaces.

Classify each:
- INTEGRATED
- SUPERSEDED / NOT INTEGRATED
- HISTORICAL EVIDENCE ONLY
- OUT_OF_SCOPE
- BLOCKER — MUST RESOLVE BEFORE FREEZE

Do not bulk merge/close/delete branches.
Do not pull old work into RC merely because it is open.

Explicitly preserve historical failed/probe PRs as historical evidence.

## 4. Dependency / environment freeze

From a clean environment:
- Python 3.12.x;
- install using repository-supported clean non-editable path;
- record exact installed dependency versions;
- record SQLite version;
- record OS/kernel/architecture;
- record package entrypoints;
- record build backend/wheel metadata.

Create a machine-readable dependency manifest.

Do not add a new lockfile unless the repository already uses one or a real reproducibility blocker requires a separately approved task.
If dependency resolution is not reproducible enough for RC, report BLOCKER rather than silently introducing release-policy changes.

## 5. Source manifest

Create a machine-readable manifest covering at least:
- tracked source files relevant to Core;
- SHA256 for each;
- top-level exact commit;
- Core tree SHA;
- test tree SHA;
- workflow/config hashes;
- constitution registry hash;
- package metadata hash.

The manifest must be generated mechanically and reproducibly.

Do not include private World data, Resident fixtures not intended for public CI, credentials, or generated local caches.

## 6. Software-only final regression

Run fresh software-only gates on the exact freeze target.

At minimum:
- full P16 direct `pytest -q`;
- world-kernel;
- world-index;
- memory-recommendation;
- fused-turn-runtime;
- C09 Wake;
- P15 Periodic Review;
- C14 runtime/scheduler/loop;
- constitutional cognition closure;
- HEADLESS;
- RECOVERY;
- SCALE semantic-equivalence / bounded correctness subset.

For SCALE:
- RC-FREEZE does not need to rerun the full 1M corpus if the exact integrated SCALE source tree is unchanged and its accepted provenance is pinned;
- it must rerun the semantic-equivalence/bounded correctness surface and verify the accepted S1M artifacts remain tied to the integrated tree;
- if the integrated tree differs from the independently accepted SCALE implementation tree in Core semantics, full SCALE revalidation is mandatory.

Do not use Resident or sealed habitation data in public software regression.

## 7. Clean-install headless smoke

From a fresh checkout/environment:

1. build/install the package using the normal non-editable release path;
2. verify installed `aios-core-headless`;
3. create a disposable private World;
4. run status;
5. submit a deterministic mechanical user turn through the normal runtime;
6. stop;
7. restart same World;
8. verify World/index continuity;
9. exercise one safe recovery-status path;
10. close cleanly.

No hidden Resident fixture.
No real provider required.
Use a mechanical adapter only for software smoke.

## 8. Backup / restore / index smoke

On the exact freeze target:

- create disposable World with execution/metering state;
- create supported online backup;
- restore to a new path;
- rebuild index from restored World;
- reopen;
- verify world_revision/object identity/execution state preserved;
- verify backup source remains unchanged.

This may reuse the accepted Recovery tooling but must be fresh smoke evidence on the freeze target.

## 9. Writer / restart smoke

Freshly verify:
- canonical single-writer lease blocks competing same-World writer;
- stale lock-file metadata alone does not block restart;
- clean stop releases lease;
- restarted same World continues correctly.

## 10. Historical read-cut / recovery spot checks

Fresh software-only spot checks must prove:
- FIX-001 historical cutoff still excludes late-known data;
- FIX-002 ambiguous background dispatch remains IN_DOUBT/no blind retry;
- FIX-003 user-turn ambiguous dispatch remains IN_DOUBT/no blind retry;
- current-time control still sees current state.

These may be targeted tests, not a Resident run.

## 11. RC impact / Resident rerun decision

This is mandatory.

Compare the final RC software tree against the software tree used by historical canonical Resident A evidence (#117 / old accepted A).

Do not hash-swap old A onto the new RC.

Produce an explicit decision:

### FRESH_A_REQUIRED
if any integrated post-A change can affect:
- model-visible context;
- search/retrieval;
- temporal knowledge;
- cognition writeback;
- Wake/Review behavior;
- recovery identity/ordering;
- model invocation or tool results;
- Summary/Claim/Task/Action behavior.

### HISTORICAL_A_REUSABLE
only if you can prove the frozen RC is semantically identical for all Resident-visible/execution-relevant paths.

Given the integrated GAP fixes, HEADLESS/RECOVERY/SCALE changes, do not assume reuse.
The burden of proof is on reuse.

If `FRESH_A_REQUIRED`, record that old #117 remains historical evidence only and that the next Resident chain must start with a new fresh private World / fresh context A on the frozen RC.

Do not run A in this task.

## 12. Freeze packet / operator packet

Produce an RC packet containing:
- exact RC SHA;
- source manifest;
- dependency/environment manifest;
- clean-install instructions;
- headless run instructions;
- World path/data-path rules;
- backup/restore/index-rebuild commands;
- operator preflight checklist;
- model adapter configuration contract;
- known limitations;
- accepted SCALE budgets and measurement caveats;
- accepted Recovery dispositions;
- exact links/SHAs to final acceptance evidence.

The packet must not include future hidden Resident fixture answers.

If the existing operator packet can be reused, update/derive minimally rather than creating a second competing operator protocol.

## 13. Known limitations

Carry forward at least:
- no public UI/hardware/platform claims;
- no phone/wearable performance claim from GitHub SCALE data;
- S1M fixture was mechanically bulk-loaded into production schemas rather than one million production write API calls;
- no finite GitHub cgroup/swap value was observed; S1M memory proof uses 4 GiB RLIMIT_AS;
- no distributed multi-host writer/HA claim;
- provider/token cost remains UNKNOWN where not directly measured;
- software RC is not Core-complete until applicable Resident/C16/P16/P17 gates pass.

Do not hide limitations to make the RC appear finished.

## 14. Required deliverables

Create:
- `release/rc/CORE_RC_FREEZE_001_MANIFEST.json`
- `release/rc/CORE_RC_FREEZE_001_DEPENDENCIES.json`
- `release/rc/CORE_RC_FREEZE_001_OPERATOR_PACKET.md`
- `reviews/CORE_RC_FREEZE_001_COMPLETION_EVIDENCE_2026-09-24.md`

Optional:
- checksums file generated mechanically.

Do not commit disposable Worlds, indexes, backup DBs, credentials, or private Resident data.

## 15. Freeze verdict

At task completion choose exactly one:

### REVIEW_READY
Only if:
- prerequisite integrations are complete;
- exact freeze target is pinned;
- manifests generated;
- open-PR contamination review complete;
- fresh full software regression passes;
- clean install/headless smoke passes;
- backup/restore/index smoke passes;
- writer/restart smoke passes;
- FIX-001/002/003 spot checks pass;
- Resident impact decision is explicit;
- freeze packet complete;
- no software blocker remains.

### BLOCKED
If any blocker remains.
Preserve red evidence and stop.
Do not fix inside this task.

## 16. Handoff

If REVIEW_READY:
- open one engineering/release PR for `CORE-RC-FREEZE-001`;
- pin the exact frozen candidate head;
- author does not self-accept;
- do not merge;
- do not run Resident;
- do not start fresh A/B/C from this window;
- do not enter C16/P16/P17;
- do not build UI/hardware.

Fresh independent acceptance is required before PM integrates the RC-freeze packet and formally releases the next Resident task.
