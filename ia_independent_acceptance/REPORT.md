# Window 05 — Independent Acceptance Report

Task: `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003`
Role: Independent Persistence Acceptance Reviewer (Window 05)
MERGE_POLICY: **DO_NOT_MERGE** (no merge, no PM integration, no downstream work performed)

---

## 1. Fresh identity (verified by fresh fetch at window start)

| Item | Value |
|---|---|
| Fresh live `main` | `016a2f7db5ed01b41fc614701079c507d2c2c02e` (== merge-base) |
| PR #299 state | OPEN / DRAFT / UNMERGED, head branch `arena/01a0ed87-haneof-aios-core-v3.0` |
| Exact candidate | `19476641be95e666068e6299f42df9a411f4c0ba` — **PR head == exact candidate, NO DRIFT** |
| Candidate parent / tree | `2d01ee2a…` / `7cd3dd81345f164cd932094cf7f8c98463a9c2f2` |
| Scope diff `main→candidate` | 56 files, +12433 / −0, all additions; **zero** `src/aios_core/**` diff; **zero** `pyproject.toml` diff (identical blob `b38833c7…`, never touched on the branch) |
| GitHub formal CI on exact head | 4 runs / 8 jobs all `success`: `core-rc-refreeze-002-formal-gate` run `36597294889` (job `formal-python312-full-suite` `109505375406`), `core-background-trusted-return-recovery-001` run `36597294962` (job `formal-core-gate` `109505375746`), `p16-convergence-gate` run `36597295058` (job `full-core-regression` `109505376225`), `core-scale` run `36597295207` (jobs `109505378919/9526/9536/9658/9727`) |
| Formal-run identity proof | run `36597294889` `head_sha` = `19476641…` (Actions API); PR-event `github.sha` `6334777f…` = `origin/pr/299-merge` (synthetic merge commit); merge-ref tree `7cd3dd81…` == candidate tree — **the formal gate tested the exact candidate tree** |

## 2. Historical provenance (preserved verbatim, not rewritten)

* PR #251 failed exact candidate `7b2556e738d9c9386ec21c13fec39400c87d0916` —
  historical reviewer verdict = **`ACCEPTANCE_FAIL / blocker=6`**. The historical `6`
  is not rewritten into `3`.
* PM narrowing ruling: binding release blockers = 3 (`C002-001 / C002-002 /
  C002-004`); non-blocking hardening = `C002-003 / C002-005 / C002-006`
  (both 2026-09-28 adjudications, read fresh).
* PR #254 stays **CLOSED / DRAFT / UNMERGED / FROZEN** (head `a2d815c9…`, PM STOP
  comment `5863009559` untouched); WIP `f7848952b6519fc40f50806f4a4d8d350ac0f38a`
  = `SCOPE_VIOLATION / NOT_A_CANDIDATE` (11-file Core diff); neither is an ancestor
  of the candidate (re-verified via merge-base checks + EVIDENCE_MANIFEST
  `historical_preservation`).
* Candidate provenance timeline (PR #299 comments, read fresh):
  * `d49f5131…` pinned (5893510053); CI RED on all 3 formal gates — bare-`pytest`
    collection `ModuleNotFoundError: No module named 'tools'` (exit 2, 6 collection
    errors, `evidence/ci_parity/RED_bare_pytest_collection_error.log`); PM HOLD
    5893623478 `REVIEW_BLOCKED / CI_COLLECTION_BLOCKER` (earlier frozen local
    candidate `aaf0f14c…` never published to GitHub);
  * `c73a4471…` pinned (5893873841) — test-only import fix
    (`tests/c15_persistence/conftest.py`), matrix unchanged; on 3.12.14 the gates
    then ran 997 tests with 13 failures = all `test_journal.py::JournalTests`,
    `FileNotFoundError '/home/user/c15-persistence-unit-probes'` (captured from
    check-run annotations of run `36594465996` job `109495689480`,
    `evidence/ci_parity/RED_ci_journal_workspace_hardcode.log`);
  * `2d01ee2a…` pinned (5894015515) — CI annotation diagnostic
    (`pytest_terminal_summary` hook, GITHUB_ACTIONS-only, read-only);
  * `19476641…` pinned (5894343481) — workspace portability repair; 3rd matrix
    freeze `d5641f8f…`; EVIDENCE_MANIFEST `1df3ec56…` (56 paths,
    `scope_violations=[]`);
  * PM release 5894484997: hold lifted, `REVIEW_READY`, `NEXT =
    FRESH_INDEPENDENT_ACCEPTANCE`, DO NOT MERGE during IA.
* No RED was rewritten to GREEN; no blocker count collapsed. The baseline RED of
  the restored harness on fresh main is preserved at
  `evidence/RED_probe_matrix_v2_baseline.log` (9 binding probes FAILED) and
  `evidence/baseline/baseline_pytest_restored_harness.log`.

## 3. Authorities read fresh (repository-only; no chat summaries used)

`governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md` (unique next READY =
Corrective-003), `governance/C15_RCC_RES_B_PERSISTENCE_SCOPE_ADJUDICATION_2026-09-28.md`
(frozen binding contract + must-not list),
`governance/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003_CORE_DEPENDENCY_ADJUDICATION_2026-09-28.md`
(10-step sequence; #254 WIP rules),
`governance/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-29.md`
(sequence done through step 8; Corrective-003 re-released; RESIDENT_B/C /
EVALUATOR / C15_CLOSE still BLOCKED), `AIOS_v3.0_CURRENT_CHECKPOINT.md`,
PR #299 body + 8-commit log + all 7 comments, PR #254 state, formal gate
workflows, and the full candidate source (all 15 `tools/c15_persistence/`
modules, all `tests/c15_persistence/` files, evidence + frozen matrices).

## 4. Frozen-probe integrity (independent mechanical verification)

* `frozen/CORRECTIVE_003_PROBE_MATRIX.json` sha256 = `d5641f8fdab934a41ed0658ceb3c7a5d9d1c1f3ed88f64984876c9ad4ac22c9c`
  == its `.sha256` sidecar == PR-comment pin. 21 probe ids; 15 binding + 6 retained
  non-binding; per-file source hashes all **match the candidate working tree**.
* `killpoints/PROBE_MANIFEST.json` sha256 = `a3c2a7c9…` == sidecar (K1–K5,
  all expectations `eq_baseline` vs a freshly measured baseline).
* Re-freeze integrity (old matrix `d4afe24b…` — identical at historical heads
  `d49f5131` / `c73a4471` / `2d01ee2a` — vs final `d5641f8f…`): **21 probe ids
  identical, every `test_function` mapping identical, every `EXPECT:` entry
  identical, node-id relative paths identical**; exactly 2/11 source hashes
  changed (`test_journal.py` `c8ec2ca0…→426b7336…`,
  `test_operator_wiring.py` `64199f3a…→1d48d735…` — precisely the two
  portability-touched files); `test_corrective_003_binding_blockers.py`
  unchanged (`15e13786…`). **No probe semantics or expectation changed; no
  expectation tuning detected.**
* Cosmetic documentation nits (non-blocking): the matrix top-level `head`
  label pins `2d01ee2a` (pre-tip) although its source hashes equal the final
  tree (binding property verified by hash equality); `freeze_history` carries
  three "initial freeze" strings; `PROBE_MANIFEST.json` rev3 note still says
  "pyproject adds the repository root to pytest's configured import path" —
  stale wording from an intermediate candidate (`dca2a220`); the final
  candidate never touched `pyproject.toml` (identical blob) and the actual
  mechanism is the directory-scoped `conftest.py`.

## 5. Independent reviewer probes (reviewer-authored, frozen before execution)

Written from scratch for Window 05; reuse only read-only harness helpers;
run against the exact candidate on the review-only branch
`review/c15-persistence-c003-ia`. Frozen source SHA-256 chain (no
expectation tuning in any direction; v2→v4 = mechanical fixes to the
reviewer's own probe code + the documented IA-14 conversion):

```text
9795e384…  v1 draft (import-bootstrap gap in reviewer file)
08cc8a61…  v2 (10/15 pass; 5 reviewer-probe bugs)
2fd99a3d…  v3 (14/15 pass; IA-14 → observation probe)
2e01947e…  v4 FINAL — 15/15 pass in 21.38s
```

| Probe | Class | Scenario (reviewer's own, not the author's) | Result |
|---|---|---|---|
| IA-01 | C002-001 | `RemoteDurabilityAbort` crosses `CapabilityRegistry.invoke` unwrapped in a reviewer-built runtime; control error still wrapped as `CAPABILITY_EXECUTION_ERROR` | PASS |
| IA-02 | C002-001 | K4 barrier failure: exit 43, durable failure evidence + audit, no ACK, no turn completion, remote still at `K3_TRUSTED_RETURN_DURABLE`, advanced local cache **refuses re-attach** (restart latch without local loss) | PASS |
| IA-03 | C002-001 | IA-02 failure + **total local loss** → fresh `materialize-resume` converges exactly once; all counts taken independently from remote commit bytes (2 distinct dispatch ledger entries, 2 `metering_records`, both attempts `metered`, 1 assistant observation, release state acked=1/next=2, relay final states `{applied:1, acked:1}`) | PASS |
| IA-04 | C002-001 | ACK-barrier failure: fatal, cursor never published as acked (remote release state un-acked, marker at K5) | PASS |
| IA-05 | C002-002 | later-round `K3_TRUSTED_RETURN_DURABLE` (round 1) + total local loss → remote-only recovery converges exactly once (independent counts: 2 dispatches distinct, 2 metered, acked once) | PASS |
| IA-06 | C002-002 | later-round dispatch-only (round 1, no durable trusted return) → exit 42 `FAIL_CLOSED_HARD_STOP`, no redispatch (ledger stays 2), attempt stays `dispatching`, no ACK, **deterministic on a second recovery** | PASS |
| IA-07 | C002-002 | K5 push success then total local loss → exactly one ACK, turn **not rerun** (`skipped: true`; 2 dispatches, 2 metered, 1 capability effect from materialized ledger bytes) | PASS |
| IA-08 | C002-002 | K5 barrier push **fails** (injected network error) after local commit → authoritative-failure stop, remote unchanged (marker at K3-trusted-return), advanced local cache refuses re-attach, remote-only recovery still converges exactly once (2 distinct dispatches) | PASS |
| IA-09 | C002-002 | tampered relay-journal **REQUEST** bytes (author's matrix tampered the reply) → fail-closed on `request corruption`, no redispatch, no ACK | PASS |
| IA-10 | C002-004 | valid binding + tampered local `.remote-head` marker → attach fails closed (never local-only) | PASS |
| IA-11 | C002-004 | storage rewound: (a) ref force-rewound to previous full commit, (b) pinned commit rebuilt **without** `generation-head.json` → attach fails closed in both shapes | PASS |
| IA-12 | C002-004 | remote ref deleted from the server → attach fails closed | PASS |
| IA-13 | 7B portability | foreign `HOME` + foreign `C15_PERSISTED_WORKSPACE` → frozen journal unittest contract 13/13 OK (historical `/home/user` hardcode failure mode closed) | PASS |
| IA-14 | 7B portability | relative `C15_PERSISTED_WORKSPACE` override — observed: `ACCEPTED (resolved workspace: <CWD>/relative/override)` — recorded, classified below (non-blocking observation; behaviour predates the candidate, `backend.py` byte-identical across the freeze history) | OBSERVED |
| IA-15 | 7B portability | `C15_PERSISTED_WORKSPACE` pointed at a platform-excluded directory (`.cache`) — observed: `ACCEPTED` — recorded, classified below (non-blocking observation; same pre-existing class) | OBSERVED |

## 6. Blocker verdicts (the three PM-bound classes)

* **C002-001 (authoritative checkpoint failure hard-stops): RESOLVED.**
  Author's frozen probes C002-001-A…D green (23/23 matrix run) and my
  independent IA-01…IA-04 green. The abort is a `BaseException` that crosses
  Core's capability-result boundary; the failed barrier is never published;
  the failure latch survives restart (attach refusal) and total local loss
  (recovery from authoritative state exactly once); the ACK barrier failure
  never acks the cursor.
* **C002-002 (later-round K3/K5 remote-only exactly-once): RESOLVED.**
  Author's frozen probes C002-002-A…G green and my independent IA-05…IA-09
  green. Convergent boundaries (first + later round, SIGKILL, total run-root
  destruction, push-success + cache loss, push-failure, remote-only fresh
  attach, request-staged-without-trusted-return vs trusted-return-durable)
  independently counted for dispatch/meter/effect/semantic-write/output/
  delivery/ACK: no duplicates, no skips, no reuse. Changed request/reply/
  payload bytes under the same identity (IA-09, author's F/G) stay
  fail-closed. The unauthenticatable in-flight window is a deterministic
  fail-closed stop (never a fabricated convergence).
* **C002-004 (remote-authoritative binding fail-closed): RESOLVED.**
  Author's frozen probes C002-004-A/B(×9)/K/L green and my independent
  IA-10…IA-12 green (marker tamper, remote rewind both shapes, ref deletion).
  Missing/corrupt/unreadable/wrong-run/wrong-session/non-canonical/
  unavailable bindings all refuse with `BackendError`; local-only runs can
  never be promoted; the durable owner classification survives total local
  loss.

**blocker = 0.**

## 7. Non-blocking findings (C002-003 / 005 / 006) — retained, green

`test_corrective_003_regressions.py` 6/6 pass (seal-content tamper, unexpected
generation artifact, history shortening by lowered ledger + re-hashed local
head rejected by authoritative remote head, cross-run config/ref
transplantation, atomic expected-old-value lease vs ref-delete race). Per the
2026-09-28 scope adjudication these stay **NON-BLOCKING HARDENING / OUT OF C15
RELEASE GATE**; no Byzantine storage or distributed CAS architecture was
required or built.

Additional non-blocking observations (Window 05, reviewer-authored):

1. **IA-14/IA-15 workspace-root validation gap (pre-existing).** A
   misconfigured `C15_PERSISTED_WORKSPACE` that is relative (resolved
   CWD-dependently) or that itself points at a platform-excluded directory is
   accepted by the production `backend.durable_root` check, which validates
   only the *child* path against the declared workspace root. The journal
   prototype (`journal.durable_path`) behaves differently (rejects relative
   overrides via non-resolved comparison) — an internal inconsistency.
   Classification: **non-blocking hardening** — it requires the operator to
   actively declare a workspace the platform does not persist; it cannot
   trigger any of the three binding failure classes (no silent binding
   downgrade, no exactly-once violation, no swallowed authoritative failure);
   absolute ephemeral roots (`/tmp`, `/var/tmp`, `/dev/shm`, …) remain
   rejected via `EPHEMERAL_ROOTS` regardless of the declaration; and the
   behaviour predates this candidate (`backend.py` is byte-identical across
   all freeze-history heads). Suggested future hardening: reject workspace
   roots that are relative, non-absolute-resolving, or located under an
   excluded component.
2. Cosmetic documentation nits on the frozen artifacts (matrix `head` label,
   `freeze_history` reason strings, stale PROBE_MANIFEST rev3 wording) — see §4.

## 8. CI portability (independent verification)

**A) `tests/c15_persistence/conftest.py` — test-only, no masking.**
* Adds repo root + `src` to `sys.path`, scoped to that directory (no root
  `conftest.py` exists; no global pytest-config change; no `.pth`; no package
  install — the harness is not in any venv, and `pyproject.toml` is
  byte-identical to main, so `tools.c15_persistence` is not installed or
  discoverable by packaging).
* Fresh-checkout / enumeration parity: bare `pytest --collect-only -q` on the
  candidate = **997** (exit 0 — the exact invocation that went RED at
  `d49f5131`); `python -m pytest --collect-only -q` = 997; on fresh `main`
  = **919**, and the per-file enumeration diff (candidate minus the new
  `tests/c15_persistence` directory) is **zero lines** — no other suite's
  collection is affected.
* Masking check: the conftest only prepends two real existing directories;
  it fabricates no module. A missing `tools` or `aios_core` module still
  raises `ModuleNotFoundError` (reproduced: running
  `probe_core_boundary.py` without the path bootstrap fails exactly that
  way). The `pytest_terminal_summary` hook is `GITHUB_ACTIONS`-gated,
  read-only annotation printing (max 10 + remainder), no effect on outcomes.
  **No product package discovery change, no installation, no masking.**

**B) Workspace portability (`/home/user` → `C15_PERSISTED_WORKSPACE` or
`Path.home()`).**
* Foreign `HOME` simulation: journal contract 13/13 under the frozen
  `unittest` invocation (IA-13) and 78/78 persistence suite.
* Foreign `C15_PERSISTED_WORKSPACE` (fresh dir, non-default): full persistence
  suite 78/78.
* Contract preservation: "durable path = private child of a valid persisted
  workspace" — workspace-root-itself, outside-workspace, excluded children
  (`.cache`/`.venv`/`node_modules`/`build`/`dist`/`out`/`target`/`.git`/…),
  symlink aliases, absolute ephemeral roots, and tmpfs/ramfs backing are all
  rejected on every account (frozen probes green; the excluded-directory
  cases now exercise *real* workspace-excluded locations on non-`user`
  accounts — strictly stronger than the hardcoded revision). Relative /
  excluded-root workspace *overrides* are accepted (observation 1, §7,
  non-blocking, pre-existing). Restart identity: every `attach`/`open`
  re-validates the durable owner record + generation chain + (when
  remote-authoritative) the remote binding before any mutable work
  (IA-02/08/10-12).

## 9. Scope compliance

* `src/aios_core/**` diff = **zero**; `pyproject.toml` diff = **zero**
  (identical blob; never committed on the branch); no packaging change; no
  `.github/workflows/**` change by the candidate (all gates are pre-existing).
* 56 files, all additions: `tools/c15_persistence/**` (harness),
  `tests/c15_persistence/**` (probes), `reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003/**`
  (declaration + evidence). No real Resident B/C, no evaluator, no RELEASE-003,
  no C15 fixture/release-state read or write (all runs/refs/identities
  synthetic; retired RERUN-002 identities hard-forbidden in the backend).
* No second semantic engine: operator layer stores bytes and state labels only
  (frozen property probe green; forbidden-call scan over the operator source).
* PR #254 `CLOSED/DRAFT/UNMERGED/FROZEN` untouched; `f7848952…`
  `SCOPE_VIOLATION/NOT_A_CANDIDATE`, not an ancestor of the candidate.
* `EVIDENCE_MANIFEST.json` sha256 = `1df3ec56…` (== sidecar == PR comment),
  56 paths, `scope_violations=[]`, `src_aios_core_diff_is_zero=true`.

## 10. Runtime

* **IA sandbox (disclosed non-formal):** CPython 3.11.2 / pydantic 2.13.5 /
  pytest 8.4.2 / SQLite 3.40.1, venv `/home/user/.venv-ia`. CPython 3.12.14 is
  unobtainable in this sandbox (GitHub release CDN, python.org, mirrors all
  blocked; documented dead ends). These results are **not** passed as formal
  3.12.14 results.
* IA results on the exact candidate (all GREEN): enumeration 997 (main 919;
  delta = the new suite only); full repo suite 997/0/0; persistence suite
  78/78; journal frozen unittest 13/13; killpoints 5/5; binding matrix
  23/23; retained regressions 6/6; trusted-return focused 98/98 (refreeze-002
  list), 24/24 (r5), 99/99 (trusted-return-001 list); C15 preflight/operator
  131/131; foreign-workspace persistence 78/78; reviewer probes 15/15;
  `probe_core_boundary.py` exit 2 `CORRECTIVE_CONVERGENCE_BLOCKED` (by design —
  documents the unresolved Core staged-reply/in-doubt boundary, 0 redispatches).
* **Formal 3.12.14 identity (GitHub CI, used for identity/env verification
  only):** workflow `core-rc-refreeze-002-formal-gate.yml` pins
  `python-version: "3.12.14"`; run `36597294889` on `head_sha 19476641…`
  (tree == candidate) concluded success; bot comment (5894325493) records
  JUnit full `tests=997 failures=0 errors=0 skipped=0` (266.42 s) and the
  focused dot-stream (98 tests); the trusted-return-001 gate recorded
  r5 24 / focused 99 / full 997 — **every formal count was independently
  reproduced in the IA sandbox** (3.11.2).

## 11. Verdict

```text
Window 05: 05
Candidate: 19476641be95e666068e6299f42df9a411f4c0ba (no drift)
blocker   = 0
ACCEPTANCE_PASS / blocker=0 / READY_FOR_PM_INTEGRATION
```

PASS authorizes **only** PM integration review. It does NOT authorize merge,
Resident B, RELEASE-003, RERUN-003, Resident C, evaluator activation, or C15
close — all remain `BLOCKED` per the governance receipt, and none of them was
performed in this window. PR #299 remains `OPEN / DRAFT / UNMERGED / DO_NOT_MERGE`;
the reviewer's evidence lives only on the review-only branch
`review/c15-persistence-c003-ia` (local commit; nothing written to, pushed to,
or merged from the PR branch).

*Stop.*
