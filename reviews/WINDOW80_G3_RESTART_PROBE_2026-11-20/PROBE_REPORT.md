# Window80 G-3 — Live Kill-and-Restart Probe Report

- **Task:** `PM-WINDOW80-G3-RESTART-PROBE-001`
- **Verifier:** independent verification window (fresh window; no prior involvement with the provenance fix, G-1/G-2 implementation or acceptance, Window80 wiring acceptance, the two reviews RV20261120-001 / RV20261120-002, PM adjudication, Operator, Core fixes, or merges)
- **Verification object:** headless runtime restart recovery on the exact local tree — local HEAD `5a2a088` (2026-11-20 PM adjudication governance commit, not pushed; remote main still `8317769`)
- **Date:** 2026-11-20 (UTC)
- **Overall exit:** **RECOVERY_VERIFIED** (restart recovery holds end-to-end across SIGTERM, SIGKILL, and graceful stops; no data loss, no duplicate writes)

## 0. Independence declaration and baseline confirmation

This verifier has no prior involvement with any earlier review, acceptance, fix, or adjudication in this project. The probe only read the repo and ran its own CLI; it modified no code and no existing file, submitted nothing, pushed nothing, opened no PR, touched no `reviews/` frozen evidence or review outputs, touched no credentials, called no external model, started no Resident, and ran no live-provider test. The temporary World lived in `/tmp/g3_probe/world` and was deleted after the probe; the probe scripts lived in `/tmp/g3_probe` and were deleted with it. All evidence below is embedded in this report (snapshot digests, object lists, command outputs).

Baseline: `git log` local HEAD `5a2a088`; probe ran 2026-11-20 09:27:45–09:29:52 UTC (127 s, mostly two 60 s harness poll loops — see §4).

## 1. Method

The probe drove the repo's own CLI (`python -m aios_core.headless.cli`, `PYTHONPATH=src`, repo venv) with the repo's deterministic local handler (`aios_core.headless.testing:deterministic_model_handler`, model `deterministic-v1`, response `HEADLESS_MECHANICAL_OK`). No other handler, no provider endpoint, no credentials.

**Read-only snapshots.** Before/after every step, `snapshot.py` opened both SQLite files read-only (`mode=ro`, immutable fallback only when no process held the lease) and recorded: world revision, object counts, the full `object_revisions` table SHA-256, `world_commits` / `turn_executions` / metering / background-attempts SHA-256s, search-index counts and SHA-256s, and the writer-lease state (lock-file content + a non-blocking `flock` probe). Content comparison across snapshots is by these hashes, not by file size.

**Sequence.** One session (`g3-restart-probe`), three turns, two live kills of a long-running `serve` process holding the lease:

| Step | Time (UTC) | Action | Result |
|---|---|---|---|
| P1 | 09:27:46 | CLI `turn` — session `g3-restart-probe`, turn 1, text `g3 probe turn one alpha lighthouse`, at 2026-11-20T09:30:00Z | rc=0, `turn_completed`, response `HEADLESS_MECHANICAL_OK`, `world_revision` (conversation commit) 2, `idempotent_replay` false |
| S1 | 09:27:46 | Snapshot | world rev 3, 4 objects, 3 commits, 1 turn exec, 1 metering, index doc 4 / postings 24 |
| P2 | 09:27:46 | CLI `serve --interval 20 --max-cycles 100` in background, pid 19368; second concurrent `status` while it lives | serve alive; second `status` rc=3, `{"error": "World writer already active: …/world.sqlite.writer.lock", "status": "writer_busy"}` — lease held by the live process |
| S2 | 09:28:47 | Snapshot (serve alive) | world rev 4, 5 objects, 4 commits — serve's first due-work cycle committed one periodic-review object (see §2) |
| P3 | 09:28:47 | `SIGTERM` to serve pid 19368 | `wait` rc=143 (terminated by SIGTERM). Lock file still shows dead pid 19368, but flock probe: **FREE** |
| S3 | 09:28:47 | Snapshot | **byte-identical to S2** (world + index hashes equal) |
| P4 | 09:28:48 | CLI `status` (fresh process) | rc=0, `world_revision` 4, `index_watermark` 4, `index_lag` 0, `writer_lease_held` true |
| S4 | 09:28:48 | Snapshot | **byte-identical to S3** |
| P5 | 09:28:49 | CLI `turn` — turn 2, text `g3 probe turn two bravo beacon`, at 10:30:00Z | rc=0, `turn_completed`, conversation commit rev 6 |
| S5 | 09:28:49 | Snapshot | world rev 7, 9 objects, 7 commits, 2 turn execs, 2 metering, index doc 9 / postings 63 |
| P6 | 09:28:49 | CLI `serve` again, pid 19581; then `SIGKILL` | `wait` rc=137 (terminated by SIGKILL). Lock file still shows dead pid 19581, flock probe: **FREE** |
| S6 | 09:29:49 | Snapshot | **byte-identical to S5** |
| P7 | 09:29:50 | CLI `status` (fresh process) | rc=0, `world_revision` 7, `index_watermark` 7, `index_lag` 0 |
| S7 | 09:29:50 | Snapshot | **byte-identical to S6** |
| P8 | 09:29:51 | CLI `turn` — turn 3, text `g3 probe turn three charlie drift`, at 11:30:00Z | rc=0, `turn_completed`, conversation commit rev 9 |
| S8 | 09:29:51 | Snapshot | world rev 10, 13 objects, 10 commits, 3 turn execs, 3 metering, index doc 13 / postings 87 |
| P9 | 09:29:52 | CLI `status` (final) | rc=0, `world_revision` 10, `index_watermark` 10, `index_lag` 0. No `-wal`/`-shm` files remain (clean checkpoint on graceful stop) |

## 2. Snapshot comparison (the core evidence)

| Pair | What happened in between | World identical? | Index identical? | Detail |
|---|---|---|---|---|
| S1 → S2 | serve1 ran due-work cycles | No — **+1 object, +1 commit** | No — doc 4→5, postings 24→39 | Added `wake_review_c09e1ba1ca8e49052ced7d5e` (type `wake`, rev 1), commit 4 `periodic review checked; no eligible world changes` (maintenance, 09:27:47). A legitimate serve write, not restart damage. |
| S2 → S3 | SIGTERM kill of serve1 | **Yes** | **Yes** | All SHA-256s equal. |
| S3 → S4 | fresh `status` process (restart) | **Yes** | **Yes** | Restart is a content no-op. |
| S4 → S5 | turn 2 | No — **+4 objects, +3 commits** | No — doc 5→9, postings 39→63 | Exactly the turn-2 objects: `obs_conv_user_c6e8f70db6b77cd440fbe6e9`, `obs_conv_ai_75f70988acbc4ccdd24ea70f`, `commexp_1687fb4cb1c43c7d0780fc71`, `dep_214e54079d244d933550b872`. |
| S5 → S6 | SIGKILL of serve2 | **Yes** | **Yes** | All SHA-256s equal. |
| S6 → S7 | fresh `status` process (restart after hard kill) | **Yes** | **Yes** | Restart is a content no-op. |
| S7 → S8 | turn 3 | No — **+4 objects, +3 commits** | No — doc 9→13, postings 63→87 | Exactly the turn-3 objects: `obs_conv_user_0e85fd49cddf1ba7cf7564e9`, `obs_conv_ai_70faea264e02389b5a21167a`, `commexp_1eb141a9a9be821261acd6d2`, `dep_36f522c028741d6bab469a5f`. |

**No duplicates, no losses.** Across all 8 snapshots: every object appears exactly once at revision 1; object sets are strictly additive (S1 ⊆ S2 ⊆ … ⊆ S8); no object was removed, re-versioned, or re-applied; `world_commits` grew 3 → 4 → 7 → 10 with no gaps and no repeated operation ids; turn executions 1 → 2 → 3; metering records 1 → 2 → 3.

**Payload spot-check.** Turn-1 user observation `obs_conv_user_db27acc65c7545decc7d8c76` still contains the exact input text `g3 probe turn one alpha lighthouse` (session `g3-restart-probe`, turn_index 1) after all restarts; turn-3 observation likewise contains its exact text. Metering: 3 records, provider `headless-test`, model `deterministic-v1`, `usage_complete` 1, distinct `provider_request_id`s (`headless-smoke-983145ad…`, `headless-smoke-133adf4d…`, `headless-smoke-01f58bba…`).

**Index survival.** Final `search_meta.search_watermark_world_revision` = 10 = final world revision; final `status` shows `index_lag` 0. Keyword postings after all restarts: `alpha`/`lighthouse` → turn-1 user observation only; `bravo`/`beacon` → turn-2 only; `charlie`/`drift` → turn-3 only; `probe` → all three. 44 distinct tokens total.

**Lease behavior.** While a serve process lived, a second `status` failed closed (rc=3, `writer_busy`). After SIGTERM and after SIGKILL, the lock file still contained the dead pid as diagnostic metadata, but the `flock` was free in both cases and the next process acquired it and overwrote the metadata — matching the repo's own stale-lock test (`test_headless_stale_canonical_lock_file_without_os_lease_reopens`).

## 3. Itemized conclusions

| # | Probe item | Verdict | One-line evidence |
|---|---|---|---|
| 1 | Data survives SIGTERM kill | **PASS** | S2 → S3 byte-identical (all SHA-256s equal). |
| 2 | Data survives SIGKILL (hard kill) | **PASS** | S5 → S6 byte-identical (all SHA-256s equal). |
| 3 | Restart rebuilds runtime, no content change | **PASS** | S3 → S4 and S6 → S7 byte-identical; `status` rev == watermark, lag 0. |
| 4 | Work continues after restart, no duplicates | **PASS** | Turn 3 after the hard-kill restart added exactly 4 new objects / 3 commits; all objects rev 1, sets strictly additive. |
| 5 | Writer lease held while live, freed on death | **PASS** | Second writer rc=3 `writer_busy` while serve lived; flock FREE after both kills despite stale pid in the lock file. |
| 6 | Search index survives restarts, stays caught up | **PASS** | Final watermark 10 == world rev 10, lag 0; turn keywords resolve to the correct observations. |
| 7 | Graceful stop path | **PASS** | Every `turn`/`status` CLI invocation exited rc=0 through `with core:` (`stop()` → `index.catch_up()` + lease release); no `-wal`/`-shm` left at the end. |

## 4. Notes and limitations (read before citing this probe)

- **SIGTERM is abrupt in this codebase — the brief's "SIGTERM 优雅停" does not exist as written.** `grep signal.` across `src/aios_core/headless/` returns nothing; the CLI `serve` loop catches only `KeyboardInterrupt`. SIGTERM therefore terminates the process with the default disposition, without running `core.stop()`. The probe tested exactly that (P3) and recovery held. Graceful stop was covered separately by the `turn`/`status` commands' normal exit through `with core:`. See observation N-1 below.
- **Serve stdout buffering (harness artifact, not a product finding).** The probe waited for a `serve_cycle` JSON line in each serve log, but the line never appeared in the file: stdout is block-buffered when redirected, and both serve processes were killed before flush. The processes were demonstrably alive and working — `kill -0` succeeded, and serve1's first due-work cycle is proven by the durable periodic-review commit at 09:27:47 (~1 s after start). The two 60 s poll loops are why the probe took 127 s. Cycle counts for the serve phases are therefore not asserted from stdout; they are bounded by the durable writes (serve1: exactly one review commit; serve2: zero commits).
- **Serve's first cycle writes.** serve1's periodic review committed one `wake_review` object (rev 4). serve2's cycles committed nothing further — no duplicate review object. The review's `dedupe_key` is timestamped (`periodic-review:user_1:2026-11-20T09:27:47…`), so the absence of a second review commit is a scheduler/cadence behavior, not a dedup-key collision; either way it is not restart damage.
- **What this probe does NOT prove.** (a) Platform-level sandbox re-creation — same limitation the repo's own `test_environment_reattach.py` records (`platform_sandbox_reattach: NOT_PROVEN`); this probe kills OS processes, not the sandbox. (b) Kill *during* an in-flight turn — both kills landed while `serve` was idle between cycles, not mid-`run_turn`; mid-turn crash recovery is covered by the in-process FIX-002/FIX-003 tests (`test_core_headless.py`), not by this probe. (c) Anything involving a live provider — deterministic handler only; a live-provider restart probe is a separate matter and needs a real endpoint. (d) `serve` with summary handlers configured — none were configured here (the CLI warns about it on every invocation; the warning is expected for a lightweight run).
- **No FAIL-level issues found.** Two observations below, both low and non-blocking.

## 5. Observations

- **N-1 (low, design):** no SIGTERM/SIGINT handler is installed anywhere in the headless CLI (`src/aios_core/headless/cli.py`, `core.py`); SIGTERM kills the process without `core.stop()`. Recovery holds anyway (proven above), so this is not a correctness gap — but if the project wants SIGTERM to mean "graceful stop" (e.g. under systemd), a handler that calls `core.stop()` would need to be added to the serve loop. Suggested as a separate minimal task, not blocking this probe's exit.
- **N-2 (low, harness):** `serve` progress lines are not flushed when stdout is redirected to a file; a supervisor watching the log file would not see `serve_cycle` lines promptly. Flushing after each `_emit` (or line-buffered stdout) would fix it. Separate minimal task if the project cares; not blocking.

## 6. Recommendation to the PM

1. Accept this probe (**RECOVERY_VERIFIED**) and close G-3: restart recovery of the headless runtime is now proven live (SIGTERM, SIGKILL, graceful stops), where the Window80 acceptance had only static evidence plus in-process reattach tests.
2. N-1 and N-2 are optional follow-ups (SIGTERM handler; serve stdout flushing) — each a minimal task of its own if the PM wants them; neither blocks the G-3 exit.
3. Do not reopen the audit baseline on this probe — it verifies restart recovery only and touches no R1–R9 semantic evidence; audit exits still stand on RV20261120-001 / RV20261120-002.
