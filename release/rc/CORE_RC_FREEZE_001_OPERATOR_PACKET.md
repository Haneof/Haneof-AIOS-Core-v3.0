# CORE-RC-FREEZE-001 Operator Packet

Status: **REVIEW_READY candidate — pending independent acceptance**  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`

## 1. Frozen software boundary

The software release-candidate boundary is the exact live-main state captured at RC-FREEZE start:

- frozen software commit: `773876f92d5f8e53422f8f5a68cc651953d93052`
- repository tree: `2cc91595532fcd437b7aaa4efebd39ca9a0b3786`
- `src/aios_core/**` tree: `fe77f8a0706acfaf369041d0882b6d0e6de39f22`
- `tests/**` tree: `815a3a460f14d073cf07d6191ea4c3edfd5457e5`
- `.github/workflows/**` tree: `8d1ea1cbb9993f9ff29155e4d04833bd53b45272`
- package: `aios-core 0.3.0.dev0`
- required Python: `>=3.12`
- installed console entrypoint: `aios-core-headless = aios_core.headless.cli:main`

The RC PR carries release manifests/evidence only. It must not redefine this software boundary.

## 2. Clean build and install

Use a fresh Python 3.12 environment and a clean checkout of the frozen software commit.

```bash
git checkout 773876f92d5f8e53422f8f5a68cc651953d93052
python -m pip install --upgrade pip
mkdir -p dist
python -m pip wheel . --no-deps -w dist
python -m pip install dist/aios_core-0.3.0.dev0-py3-none-any.whl
```

For exact RC-reproduction versions, use
`release/rc/CORE_RC_FREEZE_001_DEPENDENCIES.json`.
The repository intentionally retains dependency ranges in `pyproject.toml`; RC-FREEZE does not add a new lockfile.

## 3. Persistent data-path contract

The authoritative durable truth is the SQLite World selected by `--world` / `AIOS_WORLD_PATH`.

Rules:

1. Keep the World on durable local storage.
2. The search index is a rebuildable projection, never an authority.
3. Do not raw-copy a live World as a backup. Use the supported online-backup command.
4. Restore only to a new World path. The supported restore path does not overwrite an existing World.
5. Do not commit private Worlds, index databases, backups, provider credentials, or Resident evidence databases.
6. A single durable World has one canonical writer lease:
   `<canonical-world>.writer.lock`.
7. `--lock` / `AIOS_LOCK_PATH` are validation-only compatibility inputs. They cannot select a second writer identity.
8. Distributed multi-host/HA writer coordination is not claimed by this RC.

Recommended environment variables:

```bash
export AIOS_WORLD_PATH=/durable/path/world.sqlite
export AIOS_SUBJECT_ID=user_1
export AIOS_MODEL_HANDLER=your_adapter_module:model_handler
# Optional:
export AIOS_INDEX_PATH=/durable/path/world.search.sqlite
export AIOS_ROUND_SUMMARY_HANDLER=your_adapter_module:round_summary_handler
export AIOS_DIMENSION_SUMMARY_HANDLER=your_adapter_module:dimension_summary_handler
```

## 4. Model adapter contract

`AIOS_MODEL_HANDLER` / `--model-handler` must resolve to an existing importable AIOS `ModelHandler` callable. The Core owns context assembly, durable execution identity, metering/recovery state, World writeback, Wake/Review scheduling, and recovery semantics.

The adapter must not create an alternate World, cognition truth store, turn ledger, or provider-attempt authority. Provider ambiguity must be surfaced to the existing execution/reconciliation machinery rather than converted into a blind retry.

The RC software smoke uses only
`aios_core.headless.testing:deterministic_model_handler`.
That is a deterministic mechanical smoke adapter, not Resident evidence and not a production-provider claim.

## 5. Headless lifecycle

Set a model handler and inspect the World:

```bash
MODEL="aios_core.headless.testing:deterministic_model_handler"
WORLD="/tmp/aios-rc/world.sqlite"
INDEX="/tmp/aios-rc/world.index.sqlite"

aios-core-headless --world "$WORLD" --index "$INDEX" \
  --model-handler "$MODEL" status
```

Submit one mechanical user turn:

```bash
aios-core-headless --world "$WORLD" --index "$INDEX" \
  --model-handler "$MODEL" turn \
  --session smoke --turn-index 1 \
  --text "mechanical smoke" \
  --at "2026-09-24T12:00:00+00:00"
```

A new process may then reopen the same World and run `status`.
World revision and index continuity must persist across restart.

Inspect durable user-turn recovery state without invoking the provider:

```bash
aios-core-headless --world "$WORLD" \
  --model-handler "$MODEL" inspect-turn \
  --session smoke --turn-index 1 \
  --text "mechanical smoke" \
  --at "2026-09-24T12:00:00+00:00"
```

## 6. Recovery operations

Recovery status requires no provider:

```bash
aios-core-headless --world "$WORLD" recovery-status
```

Create a coherent SQLite online backup:

```bash
aios-core-headless --world "$WORLD" backup --to /backup/world.backup.sqlite
```

Restore to a **new** World path:

```bash
aios-core-headless --world /restore/world.sqlite \
  restore --from-backup /backup/world.backup.sqlite
```

Rebuild the non-authoritative search projection from World truth:

```bash
aios-core-headless --world /restore/world.sqlite rebuild-index
```

Then verify:

```bash
aios-core-headless --world /restore/world.sqlite recovery-status
```

Accepted Recovery behavior includes:

- SQLite transaction/WAL crash safety;
- durable turn identity across restart;
- ambiguous user-turn dispatch remains `IN_DOUBT` with no blind provider retry;
- ambiguous Wake/Periodic Review dispatch remains `IN_DOUBT` with no blind provider retry;
- index loss/staleness/corruption is recoverable by rebuilding from World;
- online backup includes World/execution/attempt/metering state;
- restore preserves source backup bytes and restores to a separate path;
- future-schema refusal occurs before writable initialization;
- interrupted maintenance fails closed.

## 7. Due work

Bounded existing Wake/Periodic Review work is processed through the same Core:

```bash
aios-core-headless --world "$WORLD" --index "$INDEX" \
  --model-handler "$MODEL" due \
  --at "2026-09-24T12:05:00+00:00" \
  --max-wakes 8
```

Do not use this RC-FREEZE packet to run a sealed Resident life. Resident execution remains a separately gated task.

## 8. Operator preflight checklist

Before starting a durable RC process:

- confirm software commit/tree matches the frozen boundary above;
- confirm Python is 3.12.x and installed dependencies match the RC dependency manifest;
- confirm `aios-core-headless` resolves to the installed RC wheel;
- confirm the configured World path is the intended durable World;
- confirm any explicit lock path equals the canonical derived lease path;
- confirm no other writer holds the same World lease;
- confirm the model handler is importable and obeys the existing ModelHandler contract;
- confirm provider credentials are supplied outside the repository;
- run `recovery-status`;
- if the index is missing/stale/corrupt, rebuild it from World instead of treating Search as truth;
- create a supported backup before maintenance;
- restore only to a new path;
- after restart, verify World revision/index watermark and any unresolved execution state before accepting new work;
- never turn `IN_DOUBT` into a fresh provider call without the existing explicit reconciliation/retry authorization path.

## 9. Accepted SCALE envelope

The accepted SCALE gate is tied to tested implementation
`ba23767d4c1565fbe494419dd01c32123495884c`
and fresh independent probe run `36013144779`.

Frozen budgets include:

- S10K: core-context p95 <= 0.75 s; snapshot p95 <= 1.5 s; recall p95 <= 1.0 s; recall <= 200 SQL statements.
- S100K: core-context p95 <= 2.0 s; snapshot p95 <= 5.0 s; recall p95 <= 2.5 s; recall <= 500 SQL statements; no candidate-level N+1 growth.
- S1M: one million current Claims; core-context p95 <= 10 s; snapshot p95 <= 20 s; recall p95 <= 10 s; recall <= 1,000 SQL statements; retrieval under the frozen memory envelope.
- S1M hard memory proof uses `RLIMIT_AS = 4,294,967,296` bytes.

Fresh independent S1M results were approximately:
core-context 4.043 s, snapshot 5.609 s, recall 0.427 s, recall SQL 54.

Measurement caveats:

- the S1M one-million-Claim World was mechanically bulk-loaded into the production World schema rather than generated by one million production write API calls;
- the S1M search projection was mechanically loaded into the production search schema for fixture practicality;
- production index rebuild/catch-up was separately exercised by smaller tiers and World-index gates;
- no finite GitHub runner cgroup/swap cap was observed; the hard memory boundary is the explicit 4 GiB process address-space limit;
- these GitHub measurements are not phone/wearable performance claims.

## 10. Accepted evidence anchors

Final prerequisite acceptance anchors:

- HEADLESS corrective acceptance: PR #189, `ACCEPTANCE_PASS / blocker=0`; tested implementation `16e983a536b124ddb600981fc16326d9db54358f`; evidence handoff `f25218aac3812c4511351333704055ff90e7dd75`.
- RECOVERY acceptance: PR #195, `ACCEPTANCE_PASS / blocker=0`; tested implementation `58b6b5e2e653e258e778a0f2dd3d77978cd585ff`; evidence handoff `f90b93608a13f9e04ff9b7997f2b4f92b5331f88`.
- SCALE acceptance: PR #200, `ACCEPTANCE_PASS / blocker=0`; tested implementation `ba23767d4c1565fbe494419dd01c32123495884c`; evidence handoff `2c8f16fed52c2a13183870da4ec5dff27892ceb4`.
- SCALE baseline red remains preserved: run `36007169180`.

## 11. Known limitations

This software RC explicitly does **not** claim:

- public UI, launcher, phone integration, Android ROM, wearable, or hardware completion;
- phone/wearable performance from GitHub-hosted SCALE measurements;
- one million production write calls in S1M;
- a finite GitHub cgroup/swap memory bound beyond the explicit 4 GiB `RLIMIT_AS`;
- distributed multi-host single-writer/HA behavior;
- known provider/token cost where not directly measured;
- final AIOS Core completion.

The software RC remains subject to fresh Resident continuity, C16, applicable broad P16, and P17 release-closure gates. No public release/tag is authorized by CORE-RC-FREEZE-001.


## 12. Fresh RC-FREEZE verification

The final software-only probe ran against the frozen Core/tests tree with only transient workflow trigger comments plus the RC probe workflow on the PR branch. The final release candidate removes all transient workflow changes.

Fresh successful evidence:

- full P16: run `36019155127`, job `107699305204` — SUCCESS, 692 pass markers / 100%;
- RC clean-install/full-regression probe: run `36019155145`, job `107699305699` — SUCCESS;
- non-editable wheel build/install — SUCCESS;
- direct full `pytest -q` — 692 pass markers / 100%;
- installed headless lifecycle — SUCCESS;
- backup/restore/index rebuild/source-logical-immutability smoke — SUCCESS;
- writer/restart + FIX-001/002/003 spot checks — 156 pass markers / 100%;
- headless: `36019154789` — SUCCESS;
- recovery: `36019154783` — SUCCESS;
- scale: `36019154843` — SUCCESS;
- world-kernel: `36019155008` — SUCCESS;
- world-index: `36019154864` — SUCCESS;
- memory-recommendation: `36019154801` — SUCCESS;
- fused-turn-runtime: `36019154857` — SUCCESS;
- C09 Wake: `36019154941` — SUCCESS;
- P15 Periodic Review: `36019154821` — SUCCESS;
- C14 runtime/scheduler/loop: `36019155213` / `36019154823` / `36019154793` — SUCCESS;
- constitutional cognition closure: `36019154893` — SUCCESS.

The RC probe artifact is `10816735414`, digest
`sha256:b759cd6d74a33f8cebc9e58576181c81ede2fe788e0ea1be4ed873d020f4c093`.

## 13. Historical Resident A impact decision

**FRESH_A_REQUIRED**

Historical canonical A #117 used Core tree
`eed27d58041dbaf2ceb0a65c1305bb332aef082e`.

This RC freezes Core tree
`fe77f8a0706acfaf369041d0882b6d0e6de39f22`.

The post-A integrated changes reach Resident-visible/execution-relevant paths including context/retrieval, temporal knowledge cut, Wake/Review, user-turn/background execution recovery, headless lifecycle, and SCALE read paths. Semantic identity for every Resident-visible path is therefore not proven.

Historical #117 remains historical evidence only. It must not be hash-swapped or relabeled as new-RC Resident evidence. After independent RC-freeze acceptance and PM integration, any released Resident chain must start with a fresh private World / fresh context A on this frozen RC.
