# CORE-RC-FREEZE-001 Independent Acceptance — 2026-09-24

## Verdict

**ACCEPTANCE_PASS / blocker = 0**

Task: `CORE-RC-FREEZE-001-INDEPENDENT-ACCEPTANCE`  
Target: PR #202  
Reviewer scope: independent software-only RC freeze acceptance  
Resident A/B/C executed: **NO**  
Core modified: **NO**  
PR #202 modified or merged: **NO**

## 1. Frozen identities

Pinned and independently re-checked:

- frozen software SHA: `773876f92d5f8e53422f8f5a68cc651953d93052`
- exact RC-freeze packet candidate: `11f4aed2eba055356730dc77922ced39b25a7d63`
- final review handoff: `b392f73f53180620842a1c25575a8a7567cc8773`
- frozen Core tree: `fe77f8a0706acfaf369041d0882b6d0e6de39f22`
- frozen tests tree: `815a3a460f14d073cf07d6191ea4c3edfd5457e5`
- frozen workflow tree: `8d1ea1cbb9993f9ff29155e4d04833bd53b45272`

Live `main` was checked before verification and re-checked immediately before publication. It remained exactly:

`773876f92d5f8e53422f8f5a68cc651953d93052`

PR #202 remained OPEN / UNMERGED with base SHA `773876f9...` and final head `b392f73f...`.

## 2. Packet / handoff immutability

Independent Git compare of:

`11f4aed2eba055356730dc77922ced39b25a7d63 -> b392f73f53180620842a1c25575a8a7567cc8773`

showed exactly one changed path:

`reviews/CORE_RC_FREEZE_001_COMPLETION_EVIDENCE_2026-09-24.md`

No implementation, test, workflow, package metadata, manifest, dependency manifest, or operator-packet bytes changed in that interval.

Independent compare of frozen software `773876f9...` to final handoff `b392f73f...` showed only these seven RC/governance paths:

- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `release/rc/CORE_RC_FREEZE_001_DEPENDENCIES.json`
- `release/rc/CORE_RC_FREEZE_001_MANIFEST.json`
- `release/rc/CORE_RC_FREEZE_001_OPERATOR_PACKET.md`
- `reviews/CORE_RC_FREEZE_001_COMPLETION_EVIDENCE_2026-09-24.md`

Therefore the required final-handoff deltas are mechanically ZERO for:

- `src/aios_core/**`
- `tests/**`
- `.github/workflows/**`
- `pyproject.toml`

## 3. Manifest mechanical validation

The frozen commit object `773876f9...` resolves to top tree:

`2cc91595532fcd437b7aaa4efebd39ca9a0b3786`

Direct Git-tree traversal independently reproduced:

- `src/aios_core` = `fe77f8a0706acfaf369041d0882b6d0e6de39f22`
- `tests` = `815a3a460f14d073cf07d6191ea4c3edfd5457e5`
- `.github/workflows` = `8d1ea1cbb9993f9ff29155e4d04833bd53b45272`

Representative frozen-file SHA256 / size / Git-blob identities were recalculated independently and matched the manifest exactly, including:

- `src/aios_core/ai_world/cognition.py`  
  SHA256 `9898b2f9908fd20da72eb9a6a76ae6b82a10bf5d333d1503f1ffe9cc6e672ff9`, size 20786, blob `88f038dcf772a9013295c709ee078ba055573b6b`
- `src/aios_core/runtime/turn_runtime.py`  
  SHA256 `07a90adbe7147bd196cbb051fdf05607400cfa8c484bd26247d0f2045cf46443`, size 178076, blob `03722c989eb9dfaff5aa2b56985e8e82556a6d4f`
- `.github/workflows/c14-cognitive-derivation-loop.yml`  
  SHA256 `f1c652b17be610942c6861428ae9c5c63244196af26c041f77350796bd680cd1`, size 4423, blob `067a162e74a2ce32703bc24642912b92d0f4c37e`
- `pyproject.toml`  
  SHA256 `993a6e9dd821d8d5885f4cc1f2da0aa34d40284618097a1de507e885f2eaab30`, size 643, blob `b38833c7537fa60d5c2f02ed4bb19158d8995a11`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`  
  SHA256 `95ae56fe2de3baf1dc038c541a242431d61f265314133fbf815cb4de6deef34d`, size 126490, blob `64538f771257bbd74d87db5f7d3cbda094d8893d`

Manifest identity validation: **PASS**.

## 4. Dependency / environment manifest

Fresh independent RC probe: workflow run `36019155145`, attempt 2, job `107711132684`, SUCCESS.

Fresh environment:

- runner image: Ubuntu 24.04.5 / `ubuntu-24.04`
- kernel/platform: Linux 6.17.0-1022-azure, x86_64, glibc 2.39
- CPython: 3.12.14
- SQLite: 3.45.1
- pip: 26.2.1
- package: `aios-core==0.3.0.dev0`
- install mode: non-editable wheel
- console entrypoint: `aios-core-headless`

Resolved distributions matched the frozen dependency manifest:

- annotated-types 0.8.0
- iniconfig 2.3.0
- packaging 26.3
- pluggy 1.6.0
- pydantic 2.13.5
- pydantic_core 2.46.5
- pygments 2.21.0
- pytest 8.4.2
- typing-inspection 0.4.4
- typing_extensions 4.16.0

The fresh wheel was built with `python -m pip wheel . --no-deps` and installed from the wheel, not editable source.

Dependency/environment validation: **PASS**.

## 5. Fresh execution boundary

The fresh Actions reruns were triggered from PR #202's transient validation head `58de2e39bc6acd06eb9b5dcf93b846560685f524`. This was independently compared to frozen software before accepting the reruns.

There is ZERO `src/aios_core/**` or `pyproject.toml` delta.

The only test deltas are six files, each with exactly one added comment line:

`# CORE-RC-FREEZE-001 transient probe trigger; test semantics unchanged.`

The P16 / HEADLESS / RECOVERY / SCALE workflow deltas are likewise exactly one added trigger comment each:

`# CORE-RC-FREEZE-001 transient probe trigger; no command or test semantics changed.`

No test assertion, command, selector, fixture, or implementation semantics changed. The only substantive added workflow is the RC-specific probe itself.

Therefore these fresh reruns exercise the frozen RC implementation with mechanically unchanged test semantics.

## 6. Fresh direct regression and targeted gates

### Direct full regression

Fresh P16/full-core regression:

- run `36019155127`
- attempt 2
- job `107711145195`
- CPython 3.12.14
- result: **SUCCESS / 100%**

Fresh non-editable RC probe also executed direct `pytest -q` after wheel installation:

- run `36019155145`
- attempt 2
- job `107711132684`
- result: **SUCCESS / 100%**

No author-only prior green was used as the acceptance basis.

### HEADLESS lifecycle and canonical writer

Fresh HEADLESS:

- run `36019154789`
- attempt 2
- job `107711151627`
- result: **SUCCESS**
- `tests/integration/test_core_headless.py`: **13/13** passed

The frozen test file includes and the fresh job executed:

- start / turn / ingest / stop / restart on same World
- single-writer fail-closed + release on stop
- canonical non-overridable writer identity
- alternate `lock_path` bypass rejection
- relative/absolute path identity
- symlink identity
- CLI/env lock override validation-only
- restart preservation for FIX-001 / FIX-002 / FIX-003

HEADLESS status/turn/status also showed writer lease held and durable world revision/index catch-up.

HEADLESS + canonical single-writer: **PASS**.

## 7. Recovery / backup / restore / rebuild

Fresh RC probe performed:

- online SQLite backup of the live World
- source logical-state verification before/after backup
- restore to a separate new path
- index rebuild from authoritative World
- restored World logical-state equality check
- reopened restored World with writer lease held and zero index lag

Fresh outputs included:

- `backup_completed`
- `restore_completed`
- `REBUILD_FROM_WORLD`
- restored `world_revision = 2`
- restored object identity and execution/metering counts equal to source

The probe explicitly preserved the correct distinction that online backup/checkpoint activity may alter physical SQLite file bytes while the authoritative logical source state remains unchanged.

Fresh Recovery clean-restart proof was also rerun:

- run `36019154783`
- attempt 2
- job `107711167347`
- result: **SUCCESS**

SQLite online backup / separate-path restore / rebuild-from-World / restart: **PASS**.

## 8. FIX-001 / FIX-002 / FIX-003 fresh spot checks

The fresh RC probe targeted suite reached 100% for:

- `tests/integration/test_core_headless.py`
- `tests/integration/test_core_recovery.py`
- `tests/integration/test_core_scale_semantics.py`
- `tests/integration/test_core_gap_fix_002_background_attempts.py`
- `tests/runtime/test_turn_execution_recovery.py`
- `tests/integration/test_v3_periodic_review.py`
- `tests/integration/test_v3_c14_cognitive_derivation_runtime.py`
- `tests/integration/test_v3_fused_turn_runtime.py`

Relevant frozen tests independently inspected include:

### FIX-001 historical read-cut

- `test_headless_restart_keeps_fix001_historical_knowledge_cut`
- `test_cg001_historical_runtime_cut_excludes_late_search_and_exact_inspect`
- `test_cg001_current_time_control_keeps_current_fact_visible`
- `test_cg001_exact_read_fails_closed_for_missing_or_corrupt_learned_at`
- `test_cg001_historical_ai_world_reads_preserve_latest_knowable_revision`

Result: **PASS**.

### FIX-002 background IN_DOUBT / no blind retry

- `test_headless_restart_preserves_fix002_background_in_doubt_without_reinvoke`
- wake/review ambiguous failures remain IN_DOUBT across restart
- crash-before-dispatch / definitely-not-submitted paths retain explicit retry semantics
- response-before-meter / meter-before-completion remain fail-closed
- budget rollover does not erase IN_DOUBT

Result: **PASS**.

### FIX-003 user-turn IN_DOUBT / stable identity / no blind retry

- `test_headless_restart_preserves_fix003_pre_admission_and_requires_authorization`
- ambiguous provider interruption remains IN_DOUBT across restart
- known-not-submitted requires explicit retry authorization
- durable assistant output recovers without model reinvocation
- conflicting input remains fail-closed

Fresh recovery process proof showed the same durable `execution_id` and `attempt_id` after backup/restore/restart, with:

- `recovery_disposition = in_doubt`
- `retry_authorized = false`
- `retry_count = 0`

Result: **PASS**.

## 9. Bounded SCALE semantic equivalence

Fresh independent rerun:

- run `36019154843`
- attempt 3
- semantic-equivalence job `107712751627`
- result: **SUCCESS / 100%**

Fresh gate included:

- `tests/integration/test_core_scale_semantics.py`
- `tests/integration/test_core_headless.py`
- `tests/integration/test_v3_ai_world.py`
- `tests/integration/test_v3_c14_cognitive_derivation_runtime.py`
- `tests/integration/test_v3_periodic_review.py`
- `tests/integration/test_core_gap_fix_002_background_attempts.py`
- `tests/runtime/test_turn_execution_recovery.py`
- `tests/integration/test_v3_fused_turn_runtime.py`

The frozen scale semantics tests explicitly cover legacy cutoff, subject isolation, revision/partition semantics, current/historical/inactive recall semantics, evidence/dependency visibility, exact limit/order, and watermark catch-up.

Bounded SCALE semantic equivalence: **PASS**.

Historical SCALE performance/red evidence remains historical evidence and was not rewritten or relabeled.

## 10. Open-PR contamination review

A fresh GitHub-native inventory of all open PRs was performed rather than relying on search ranking.

No open PR is an unaccounted accepted software candidate for this RC.

Key dispositions:

- #202: target RC packet; governance/release/review files only, no Core/tests/workflow/pyproject delta.
- #144: superseded CI candidate; workflow-only; later corrective route was accepted/integrated.
- #130: superseded operator candidate; no Core; accepted operator assets were integrated through the later accepted route.
- #126: OPEN/DRAFT duplicate Core route. The S0 baseline decision explicitly records its Core repair as already represented on main and forbids re-integration.
- #125: old-Core operator WIP / DO NOT MERGE wholesale; only reviewed operator/test assets were subsequently ported onto current main.
- #121: historical failed/non-canonical Resident B evidence.
- #117: historical evidence-only canonical A for its historical frozen Core.
- #113 + #111: intended cognition hardening content was integrated into the canonical hardening anchor `bcd6bf353126318f9a97076b52ec1740d43f35a4`; that commit explicitly records integration from PR #111 and PR #113. Their still-open source PRs are not newer RC candidates.
- #110: explicitly superseded by review-remediated #113.
- #112: docs-only benchmark report.
- #109 / #107 / #101 / #92 / #79 / #75 / #74 / #37: historical evidence/review/governance lines, not current RC software candidates.
- #118 / #119: governance-only historical anchor planning/reconciliation.

Open-PR contamination verdict: **NO RC CONTAMINATION**.

## 11. Historical red evidence preservation

Final handoff evidence still explicitly preserves:

- `36016762621`: invalid byte-for-byte SQLite source-file hash assumption during online backup
- `36017499523`: evidence probe queried wrong revision column
- `36019994350`: software validation green; later evidence-publication script failed on literal temp path
- `36007169180`: historical SCALE baseline red

Accepted historical independent S1M provenance `36013144779` remains pinned.

No red was rewritten as green, and no Core patch was made in this acceptance window.

Historical red preservation: **PASS**.

## 12. Independent #117 impact adjudication

Historical canonical Resident A #117:

- evidence head `3e51f728d7959048b75fea01d405bc837b0e8185`
- historical Core tree `eed27d58041dbaf2ceb0a65c1305bb332aef082e`

New RC Core tree:

`fe77f8a0706acfaf369041d0882b6d0e6de39f22`

Independent recursive tree comparison found 26 changed/new Core files. Changes include Resident-visible or execution-relevant paths in:

- AI-world cognition
- context continuity
- dependency/events
- query/search
- recommendation
- Periodic Review
- revision propagation/service
- runtime cognitive state
- background attempts
- turn execution/runtime
- storage
- summaries/scheduler
- Wake
- new HEADLESS/recovery surface

This is not a report-only or storage-neutral change from #117's historical anchor.

Independent disposition:

**FRESH_A_REQUIRED**

#117 remains valid historical evidence for its own frozen Core only. It must not be hash-swapped, rebased, or treated as canonical evidence for this RC.

No Resident was run in this acceptance window.

## 13. Scope compliance

This acceptance window did **not**:

- modify or merge PR #202
- repair Core
- run Resident A/B/C
- enter C16
- enter broad P16 work beyond the existing direct regression gate
- enter P17
- perform UI / Android / hardware work
- create a public release or tag

## 14. Final acceptance

All required RC freeze invariants and fresh independent software checks passed.

**ACCEPTANCE_PASS / blocker = 0**

PR #202 must remain OPEN / UNMERGED.  
Next action belongs to independent PM integration.
