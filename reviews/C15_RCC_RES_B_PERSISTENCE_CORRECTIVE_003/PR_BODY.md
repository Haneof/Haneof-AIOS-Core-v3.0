# [C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003] Corrective-003 binding blockers on accepted Core semantics — REVIEW_READY (do not merge)

## Declaration (binding)

* **Continuation from frozen historical WIP.** This branch continues the *scope-compliant* part of the
  Corrective-003 WIP that was frozen by the PM STOP on PR #254. No WIP commit is cherry-picked; only
  scope-compliant persistence-harness files were selectively recovered onto fresh latest `main`.
* **Old PR #254 remains immutable historical WIP:** `CLOSED / DRAFT / UNMERGED / FROZEN`, head
  `a2d815c9f5154d87a56b152ed7cf5d1eb1baaaae`, PM STOP comment `5863009559`, first scope-violating WIP
  `f7848952b6519fc40f50806f4a4d8d350ac0f38a` = `SCOPE_VIOLATION / NOT_A_CANDIDATE`. Nothing is reopened,
  force-pushed, rebased, amended or deleted.
* **Exact latest-main base:** `016a2f7db5ed01b41fc614701079c507d2c2c02e`
  (`git merge-base` of this branch and `main` = that commit; it equals the PM re-release post-integration
  baseline).
* **Binding scope is only `C002-001 / C002-002 / C002-004`.** `C002-003 / C002-005 / C002-006` stay
  `NON-BLOCKING HARDENING / OUT OF C15 RELEASE GATE`; their probes are retained unchanged so ordinary
  corruption detection cannot regress. Historical reviewer verdict `ACCEPTANCE_FAIL / blocker=6` on PR #251
  exact `7b2556e738d9c9386ec21c13fec39400c87d0916` is preserved verbatim, alongside the PM ruling
  `PM frozen-contract release blockers = 3`.
* **Zero `src/aios_core/**` diff** (mechanically verified in
  `reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003/evidence/EVIDENCE_MANIFEST.json`), no product packaging
  change, no `tools/c15_persistence` installation, no second truth store, no second World.
* **No Resident B execution, no RELEASE-003, no RERUN-003/ACCEPT-003, no Resident C, no evaluator, no C15
  close.** Every probe uses disposable synthetic state only.

## What changed

* `tools/c15_persistence/operator_session.py` — Core-owned provider-return authority: the operator reattaches
  a dispatched provider request (never a second dispatch), reads Core's own trusted-return receipt and lets
  Core's accepted `recover_trusted_handoff` / exact-response recovery resume the round; every round publishes
  the authenticated provider-return barrier; a provider boundary crossed without a durable trusted return
  hard-stops; authoritative barrier failures are durable failure evidence plus a distinct error.
* `tools/c15_persistence/probe_cli.py` — frozen exit codes `42 = FAIL_CLOSED_HARD_STOP`,
  `43 = AUTHORITATIVE_PERSISTENCE_FAILURE`; probe-only `--fail-barrier` injection.
* `tools/c15_persistence/freeze_corrective_003_matrix.py`, `freeze_corrective_003_evidence.py` — frozen probe
  matrix and evidence/scope-gate freeze.
* `tests/c15_persistence/**` — new frozen binding-blocker matrix (21 probe ids), retained non-blocking
  probes, probe-mechanics corrections (documented in the manifest `freeze_history` / `freeze_reason`), and
  `conftest.py`, the CI-parity corrective (see below).
* **CI-parity corrective A (formal-gate import parity)** — the first pushed head made three repository formal
  gates red (`formal-core-gate`, `formal-python312-full-suite`, `full-core-regression`): those gates call a *bare*
  `pytest`, which does not put the repository root on `sys.path`, so the probes' `from tools.c15_persistence
  import ...` aborted collection (`ModuleNotFoundError: No module named 'tools'`, exit `2`).
  `tests/c15_persistence/conftest.py` adds the repository root/`src` for that directory only. No root
  `conftest.py`, no global pytest config change, no packaging change, no harness installation, no
  `src/aios_core/**` change.
* **CI-parity corrective B (portable persisted workspace)** — on CPython 3.12.14 the gates then ran the whole
  suite and reported `tests=997, failures=13`: the 13 failures were **all of `test_journal.py::JournalTests**,
  every one of them `FileNotFoundError: '/home/user/c15-persistence-unit-probes'`. `journal.py` hard-coded
  `WORKSPACE = Path('/home/user')`, which exists only on this sandbox's account (`user`); the formal CI account is
  `runner` (`HOME=/home/runner`), so the whole frozen journal contract died in `setUp`. The workspace is now
  resolved exactly like `backend.py` already did (`C15_PERSISTED_WORKSPACE`, else the account home), and
  `test_journal.py` / `test_operator_wiring.py` / `probe_core_boundary.py` (plus the `resident_surface_check.py`
  default scratch root) derive from it. The durability contract is unchanged, and on non-`user` accounts the
  excluded-location cases are now *stronger* (they test real workspace-excluded paths instead of degrading to
  "outside the workspace"). Because two frozen probe sources changed, the matrix was re-frozen with a documented
  reason: **21 probe ids and all `EXPECT:` entries are byte-identical**, only those sources' hashes changed
  (matrix now `d5641f8fdab934a41ed0658ceb3c7a5d9d1c1f3ed88f64984876c9ad4ac22c9c`, `freeze_history` 3 entries).
* **Verification** — CI-style history-less checkout, and a simulated foreign account
  (`HOME=/home/user/c15-ci-home-sim`, repository outside `HOME`): 997 collected, persistence subset 78 passed,
  journal contract 13 passed under both pytest and the frozen `unittest` invocation, whole repository
  `tests=997 failures=0 errors=0 skipped=0`. Evidence in
  `reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003/evidence/ci_parity/` (incl. the captured CI RED annotations,
  `RED_ci_journal_workspace_hardcode.log`).
* `reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003/**` — report, baseline RED logs, GREEN logs, environment
  identity, resident-surface artifact, evidence manifest + scope gate, PR body.

## Evidence summary

| Item | Result |
|---|---|
| RED (restored baseline, final frozen probe sources) | 9 binding-blocker probes fail on fresh main before the repair |
| GREEN probe matrix v2 | 23 passed |
| persistence suite (pytest) | 78 passed |
| historical journal suite (frozen `unittest` contract) | 13 passed |
| trusted-return focused Core regression | 231 passed |
| full repository suite | 997 passed |
| CI-parity: bare `pytest`, history-less checkout, foreign `HOME` | collected 997; persistence subset 78 passed; journal 13 passed; repository 997 tests / 0 failures / 0 errors |
| `src/aios_core/**` diff | ZERO |
| scope violations | none |

Environment: CPython 3.11.2 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.40.1. The formal pin is CPython
3.12.14 / SQLite 3.45.1; the sandbox cannot obtain CPython 3.12.14 (GitHub release-asset and python.org
downloads are blocked) — **disclosed**, not hidden.

## Status

```text
C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003 = REVIEW_READY
NEXT = FRESH_INDEPENDENT_ACCEPTANCE
```

Do not merge. Do not enter Resident B / RELEASE-003 / Resident C / evaluator / C15 close from this PR.
