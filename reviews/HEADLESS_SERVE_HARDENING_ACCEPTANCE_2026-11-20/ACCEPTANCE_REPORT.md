# Headless Serve Hardening — Independent Acceptance Report

- **Task:** `PM-HEADLESS-SERVE-HARDENING-ACCEPTANCE-001`
- **Acceptance agent:** independent acceptance window (fresh window; no prior involvement with the serve-hardening implementation, PM adjudication, the G-3 probe, the two reviews RV20261120-001 / RV20261120-002, Window80 wiring acceptance, G-1/G-2 or provenance implementation or acceptance, Operator, Core fixes, or merges)
- **Acceptance object:** commit `b1fd221` (`fix(headless): graceful SIGTERM/SIGINT in serve loop, flush _emit output`, `Haneof/Haneof-AIOS-Core-v3.0`)
- **Acceptance execution tree:** local `5dfc816` (2026-11-20 PM adjudication governance commit, not pushed; remote main still at `8317769`)
- **Date:** 2026-11-20 (UTC)
- **Overall exit:** **ACCEPTED** (all 5 items PASS; no FAIL; 2 minor observations, see §4)

## 0. Independence declaration and baseline confirmation

This acceptance agent has no prior involvement with the fix, its implementation, or any earlier review, acceptance, probe, or fix in this project. This acceptance only read the accepted commit and the code and ran its own reproduction scripts and the repo's tests; it modified no code and no existing file, submitted nothing, pushed nothing, opened no PR, touched no `reviews/` frozen evidence or review outputs, touched no credentials, called no external model, started no Resident, and ran no live-provider test (they skip by default).

Baseline confirmation:

- `git log`: local HEAD `5dfc816`, beneath it `b1fd221` (fix commit), parent `f0bff78` (PM adjudication governance commit).
- `git show --stat b1fd221`: 2 files, 162 insertions, 33 deletions — `src/aios_core/headless/cli.py` (+117/−33), `tests/integration/test_core_headless.py` (+78, 3 new tests).
- Trailer: `Authorized-Task: PM-HEADLESS-SERVE-HARDENING-001`, matching the task registered in `governance/baseline.json` (17 tasks total). `tools/governance/check_baseline.py`: **PASS**.
- `git diff 8317769..b1fd221 --stat`: 15 files, of which 2 are this fix; the other 13 are the G-1/G-2 fix, the provenance fix, and PM adjudication governance commits in between — the hardening fix itself has no incidental changes.
- Working tree was clean apart from the pre-existing untracked `reviews/` review/acceptance directories. The unpatched control tree was a temporary `git worktree` of `b1fd221^`, removed after use (`git worktree list` shows only main at `5dfc816`).

## 1. Itemized conclusions

| # | Acceptance item | Verdict | One-line evidence |
|---|---|---|---|
| 1 | SIGTERM/SIGINT graceful stop | **PASS** | Real signals to a live `serve` subprocess: rc=0, `serve_stopped`, `interrupted=true` for both signals; seeded data intact (rev monotonic) |
| 2 | `_emit` flushes promptly | **PASS** | Independent pipe repro: both lines readable on the pipe without closing the writer |
| 3 | Regression tests genuine | **PASS** | Fixed tree 20/20; unpatched worktree: handler test ImportError, flush test AssertionError, SIGTERM test kills the runner (exit 143) |
| 4 | Scope discipline | **PASS** | `b1fd221` touches exactly 2 files, trailer present, no incidental changes |
| 5 | Full quick check | **PASS** | 558 passed, 3 skipped (live provider), governance PASS, VERDICT: PASS |

## 2. Itemized evidence

### 2.1 Graceful stop on real signals (PASS)

Mechanism verified by reading first: `_run` calls `_run_serve` inside `with core:` (`cli.py:422`); `HeadlessCore.__exit__` calls `stop()` (`core.py:282–284`), which runs `index.catch_up()` and then releases the writer lease in a `finally` (`core.py:267–277`). `_run_serve` catches `KeyboardInterrupt` and returns `serve_stopped` / `interrupted=True`. The fix installs handlers that convert SIGTERM/SIGINT into `KeyboardInterrupt` (`cli.py:305–344`), so a signal takes the same graceful path as Ctrl-C. Install/restore is main-thread-only (`_install_serve_signal_handlers` returns `{}` off the main thread).

Independent reproduction (own scripts in `/tmp/accept_hardening`, different from the shipped tests, which use `signal.raise_signal` inside the test process):

- `repro_sigterm_subprocess.py`: starts the real CLI (`python -m aios_core.headless.cli --world <tmp> --model-handler aios_core.headless.testing:deterministic_model_handler serve --interval 1 --max-cycles 0 --skip-periodic-review --skip-dimension-summaries`), seeds one real `turn` first (world rev 2), waits for a `serve_cycle` line on stdout, sends a real signal with `os.kill`, then runs a fresh `status`:
  - SIGTERM: rc=0, last line `{"status": "serve_stopped", "interrupted": true}`, 1 cycle; post-kill `status` rc=0, `ready`, world rev 3 (seed rev 2 intact).
  - SIGINT: identical outcome, rc=0, `serve_stopped`, `interrupted=true`, rev 3.
- `repro_handlers.py`: main-thread install returns the previous handlers for both signals, `getsignal` shows the converter, calling the converter raises `KeyboardInterrupt`, restore returns the previous handlers; in a non-main thread install returns `{}` and changes nothing. All PASS.

Two corrections made during my own repro (recorded, not defects in the fix):
- My first version asserted the post-kill `status` would show `writer_lease_held: false` and `world_revision >= 1` after a serve-only world. Both were wrong on my side: `writer_lease_held` is the *reporting* process's own lease (`core.py:302`, `self._lease.held`), so `True` is expected; and a serve cycle with skip flags on an empty world legitimately writes nothing (rev 0). The corrected script seeds a turn first and asserts revision monotonicity instead.
- The seeded run showed the serve cycle itself committed one world revision (2 → 3) even with periodic review and dimension summaries skipped — see observation O-2.

### 2.2 `_emit` flush (PASS)

Independent reproduction (`repro_emit_pipe.py`, pipe-based rather than the shipped test's tmp-file approach): write end of an `os.pipe()` opened as an 8 KiB-buffered file, two `_emit` calls, then `select` + `os.read` on the read end **without closing the writer** — both JSON lines were readable immediately. The shipped flush test (8 KiB-buffered tmp file, second handle read) passes for the same reason; the two approaches agree.

### 2.3 Regression tests genuine (PASS)

- Fixed tree: `tests/integration/test_core_headless.py` — **20/20 passed** (17 pre-existing + 3 new).
- Unpatched tree (temporary worktree of `b1fd221^`, new test file copied in, run with the repo venv and `PYTHONPATH` pointed at the worktree `src`):
  - `test_serve_signal_handlers_turn_sigterm_and_sigint_into_keyboard_interrupt` — **FAILED, ImportError** (helpers do not exist).
  - `test_emit_flushes_stream_immediately` — **FAILED, AssertionError** (content not on disk).
  - `test_serve_loop_stops_gracefully_on_real_sigterm` — **pytest process killed, exit code 143** (`Terminated` on stderr): with no handler, the signal is fatal. This is the sharpest confirmation that the old code had no graceful SIGTERM path.
- All 3 are genuine regression tests.

### 2.4 Scope discipline (PASS)

`git show --stat b1fd221`: exactly 2 files (`headless/cli.py` +117/−33, `tests/integration/test_core_headless.py` +78), trailer `Authorized-Task: PM-HEADLESS-SERVE-HARDENING-001` present. No other file changed by this commit. The `cli.py` diff is the three helpers + install/restore wiring in `_run_serve` + the `stream.flush()` line in `_emit`; the loop body is re-indented only (one extra nesting level), with no logic change.

### 2.5 Full quick check (PASS)

Ran on local HEAD `5dfc816`: `tools/check.py --quick` → **558 passed, 3 skipped** (live-provider tests, need a real endpoint), **governance PASS, VERDICT: PASS**. The 3 new tests live in `tests/integration`, which `--quick` does not collect, so the count is unchanged from before the fix — as expected and as the implementer reported.

## 3. Coverage completeness (own extra check)

- The signal-handler install/restore pair covers both SIGTERM and SIGINT, main thread only, with `try/except (ValueError, OSError, RuntimeError)` guards on install and restore — a handler that fails to install degrades to the old behaviour rather than crashing startup.
- `time.sleep` in the serve loop: when the handler raises `KeyboardInterrupt` inside `sleep`, the sleep is interrupted (a raising handler is not retried per PEP 475), so shutdown is not delayed until the interval elapses — confirmed by the subprocess repro, which exited within the 30 s wait after the signal with `--interval 1`.
- `_emit` flushes after every line, including the final `serve_stopped` dict emitted by `main()` — the subprocess repro read that line from the dead process's stdout, which is itself evidence the flush works on the exit path.

## 4. Observations (no FAIL-level issues)

- **O-1 (known, recorded):** the SIGTERM regression test depends on running in the main thread (`signal.signal` only allows main-thread installation); if the suite ever moves to a multiprocess/multithread executor, that test needs to test only the handler callback itself. Already recorded in the task-board CURRENT PM CONTROL block by the PM.
- **O-2 (low, informational):** a `serve` cycle committed one world revision (2 → 3) even with `--skip-periodic-review --skip-dimension-summaries` and no due work — `process_due_work` is not a guaranteed no-op. Not a defect (revision counts are not a promise), but anyone reasoning about world revisions from serve logs should know a cycle can bump the revision without a visible wake or review.
- **O-3 (low, probe ergonomics):** `status` reports `writer_lease_held` for the *reporting* process's own lease (`core.py:302`). A future probe author reading that field after a kill could misread `True` as "the dead process still holds the lease". The reliable check is that a fresh command starts at all (rc=0) plus content comparison.

## 5. Recommendation to the PM

1. Accept this hardening fix (**ACCEPTED**).
2. Publishing note (same as the previous acceptances): the fix push touches `src/aios_core/**` and will trigger `p16-convergence-gate` on main — verify that CI run after the push lands.
3. No new audit baseline is opened by this acceptance — it only verifies the serve-hardening fix and does not touch R1–R9 semantic evidence; audit exits still stand on RV20261120-001 / RV20261120-002.
4. No further follow-up task is needed from this acceptance: the G-3 items (N-1, N-2) are now both fixed and accepted, closing the Window80 wiring-acceptance gap list. The remaining open items are the external ones (L1/L4/L7, live re-capture for R6) and the pending pushes.
