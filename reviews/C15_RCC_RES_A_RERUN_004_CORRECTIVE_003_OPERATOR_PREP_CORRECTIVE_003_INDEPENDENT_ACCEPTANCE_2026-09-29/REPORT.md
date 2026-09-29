# Independent Resident Launch Infrastructure Acceptance Report

**Task**: `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE`
**Role**: Independent Resident Launch Infrastructure Acceptance Reviewer — not the author, not a
prior corrective author, not the Resident, not the PM, not a Core implementer, not a semantic evaluator.
**Review type**: review-only / evidence-only / DO NOT MERGE.
**No real Resident was executed.** All execution state is disposable and synthetic (pytest temp dirs).

## Verdict

| | |
| --- | --- |
| **result** | `ACCEPTANCE_PASS / blocker=0` |
| **disposition** | `READY_FOR_PM_INTEGRATION` |
| **blockers** | none |
| **candidate** | PR #292, final freeze H2 `42a63ed4416585fc0a02045e0bd5190f32a01a2b` |
| **candidate drift** | none — PR #292 head equals H2 exactly; no `REVALIDATION_REQUIRED` |
| **review evidence** | this directory (`REPORT.md`, `probes*/`, `raw/`, `env/`, `REVIEW_SHA256SUMS`) |
| **branch** | `arena/01a0ecaa-haneof-aios-core-v3-0` (session-assigned; the candidate branch was never touched) |

No blocker is recorded, so no blocker ID / corrective scope is applicable. No candidate repair was
performed in the review window, and the candidate tree was never modified.

## 1. Candidate identity and scope control (§4)

Verified from git objects, never from the PR description:

| Item | Expected | Observed |
| --- | --- | --- |
| H2 commit | `42a63ed4416585fc0a02045e0bd5190f32a01a2b` | equal (PR #292 head) |
| H2 tree | `80440bdd70aa658053bc5bf33a902c46cd7138e0` | equal |
| H1 commit / tree | `77dac70e…` / `52aa366b…` | equal (H2's sole parent) |
| RED commit | `083dd9506f01ade04d4cbe805f58bf80d40607b0` (H1's parent) | equal |
| probe freeze commit | `4b2ca9fd48da2f1f44789c664de66bd471a39ee9` | equal (RED's parent; parent = #288 carry `41de3f66…`) |
| starting main | `c8e9e42f8ae6e6724c0c7e9eb9dbb21b100f4487` | equal to `git merge-base origin/main <H2>` |
| live main at review start | `1cdd9e0ef3fa0ee51f0791bc2309d100cd8e760a` | equal (repository was at it) |

Chronology is correct for an un-tunable corrective: **probe freeze (`4b2ca9f`) → RED evidence
(`083dd95`) → corrective implementation H1 (`77dac70`) → evidence-only final freeze H2 (`42a63ed`)**.

Scope enumeration (git objects, `c8e9e42..H2`): **546 changed files, +103 063 lines, every path under
`reviews/`** — zero paths in `src/`, product `tests/`, `fixture/`, `evaluator/`, `release/`,
`resident/runs/`, or any real-state artifact. `H1 → H2`: **188 files, evidence/raw/report only** —
zero `harness/`, `bootstrap/` or probe-source changes. `4b2ca9f → H2` (post-probe-freeze): **zero
changed probe sources**, and the harness/bootstrap changes are confined to the intended corrective
implementation (`083dd95 → H1`: 6 `harness/aios_exchange` modules + 3 `harness/operator_tools`
modules). The pre-existing `reviews/.../preflight-002/lineage_copy/{private_world.sqlite,
release_state.json,world_index.sqlite}` files are present in `main` and are **unchanged by this PR**.

## 2. Reviewer runtime (§6)

Built from a fresh, absent scratch root by `bootstrap_runtime.sh --build` (never the author runtime
`/home/user/.cache/c003/final-runtime-001`, which does not exist in this environment):

- CPython **3.12.14**, Pydantic **2.13.5**, pytest **8.4.2**, SQLite **3.45.1**, OpenSSL **3.0.13**
- Linux 6.1.158+, x86_64, glibc 2.36 (Debian-class), gcc 12.2.0
- 11 wheels installed from the repo's hash-pinned wheel lock (`bootstrap/PYTHON_WHEEL_LOCK.json`,
  file sha `6fa2587c98662588e4758ac9b579fee8d800ce4fc2d36e692dbaaabd6f4c8afe`), no index, no deps
- `aios_core` resolves to the frozen RC working tree `/home/user/ia_review/rc/src/aios_core/…`
- `bootstrap_runtime.sh --verify` rc=0 (VERIFY OK)
- Evidence: `env/runtime_build.log`, `env/environment_record.json`, `env/bootstrap_verify.log`,
  `env/reviewer_environment_probe.json`

Frozen RC identity re-verified in the review: software `f20f2edfa7af00d0286493fd15196ca9503bc315`,
repository tree `1ac3a675b884167d3a29aa432e7ef3eaff94d404`, Core tree
`9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`, tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`;
Core content manifest `220718d6b5a2650b5e4263bbe8b7e661444cb33b486a7ecd7b5ad3d7d3399caa` (77 files).

## 3. Reviewer probes (§5) and adversarial results

Probes are authored independently of the candidate's own C10/C11 suite, hashed, enumerated with
per-probe expectations, and executed only under the reviewer runtime against the frozen H2 package.

| Revision | Sources SHA-256 | Enumeration SHA-256 | Execution |
| --- | --- | --- | --- |
| 1 (`probes/`) | `778d48e0e6cf9e0c6c04057eab1684e5d4dd0d4b22e621611cf1e0a9b060ae2f` | `cc2d805c22a6ffc2683252d6a1b5183d53fceec81275e4f35d0b88be5ae9fab1` | 39 passed / 9 failed (100.63 s) |
| 2 (`probes_v2/`, corrected) | `a4e8b0e58b9636ba4e41124507da39c2c235b58761111d0c1e4a12ac1f22f47d` | `83d2ab281d6e046e9175437e087f624434d6f5de1d1dc80559b0ec69958d4231` | 49 passed / 0 failed (154.31 s) |
| 3 (`probes_v3/`, final) | `0d299c288169e27a9068c15e9cbd3a2e8da372f6c815e640b84695c235c1db29` | `fdad15300e65e069eea365dfdd3af8e3a2f0a3fe3fdc2d43ef5ddef440730ad9` | **50 passed / 0 failed (153.50 s)** |

- Every revision-1 failure was triaged to a **probe or execution-method defect** (documented in
  `REVISION_NOTES_v2.md`, one row per failure, with root cause). No candidate defect was concluded
  from revision 1, and no revision-2/3 expectation was weakened after seeing candidate behavior;
  `raw/reviewer_probes_v2_integrity.json` and `raw/reviewer_probes_v3_integrity.json` record the
  frozen vs post-run source hashes (**identical**) and all mtimes.
- A critical execution-method defect was found and fixed: the product repository's `pyproject.toml`
  declares ini `pythonpath = ["src"]`, which injected the live-main source tree ahead of the frozen
  RC when the probes ran from below the repository root (observed as the revision-1 C7 failure).
  Revision 2+ pin `-o pythonpath=`, run outside the product repository, and a conftest guard fails
  loudly if any foreign `aios_core` is importable.
- Freeze/commit ordering for revisions 2 and 3 is disclosed in `REVISION_NOTES_v3.md`; the freeze
  artifact preceded the first execution of each revision and the sources were byte-identical after
  execution. Revision 1 was committed before its execution.
- Collected enumeration equals the frozen enumeration for revisions 2 and 3
  (`raw/reviewer_probes_v{2,3}_enumeration.diff` empty).

### 3.1 Requirement-to-evidence map (§7–§15, §18, §22)

| Requirement | Attack executed | Result |
| --- | --- | --- |
| §7 two ledgers / same legal prefix; real subprocess writers; no deadlock or starvation | RA-01 four-process distinct publishers; RA-05 nested transactions over two ledger objects | PASS |
| §7 concurrent distinct publication self-consistency (stale-prefix ID computed outside the lock) | RA-01 stale-prefix identity probe (revision 3) | PASS (loser fails closed; no artifact, no record) |
| §7 duplicate same-request race idempotent / fail-closed | RA-01 declared-identity race (idempotent replay, single dispatch) | PASS |
| §7 response / consume races exactly-once chronology | RA-01 response-publish race, consume race, publish-vs-consume race | PASS |
| §7 two ExternalSessionModelHandler processes → one dispatch | RA-01 handler race on one snapshot | PASS |
| §7 lock-failure injection fails closed | RA-05 symlinked lock path, directory at lock path, inode replacement | PASS |
| §8 lock design (dedicated persistent inode, O_NOFOLLOW, inode re-check, RLock never sole authority, nested-safe, held through artifact+ledger durability, released before awaiting external bytes) | RA-05 lock-path/inode/nesting/awaiting-release probes + full module read (`ledger.py`, `atomic.py`) | PASS |
| §9 directory-fsync/open injection (request dir, response dir, first ledger creation, append) | RA-02 seven fault-injection probes | PASS (no success receipt on any fault) |
| §10 visible-but-unproven retry (re-prove bytes/digests, ≤1 durable event, exactly-once) | RA-03 five retry probes (request + response, including mutated visible bytes) | PASS |
| §11 initial ledger creation durability (empty, repeated, concurrent-first-writer) | RA-02 first-ledger probes; RA-01 four-process cold start; RA-03 first-ledger retry | PASS |
| §12 crash boundaries (temp fsync → replace → dir fsync → ledger append → receipt) | RA-04 crash-point sweep and no-orphan-dispatch probe | PASS |
| §13 C1 tampered/missing response replay fail-closed | RA-07 C1 probes (3) | PASS |
| §13 C2 wheel trust root pre-download frozen SHA; wrong/missing/extra wheel; no-index install; no live resolver | RA-07 C2 probes (2) + reviewer runtime built offline from the pinned lock | PASS |
| §13 C3 gate collect/result/execution consistency | Gate tier below: collected vs executed vs reported counts identical per gate | PASS |
| §14 C4 recovery ↔ RuntimeSnapshot binding | RA-07 C4 probe | PASS |
| §14 C5 ledger integrity (mutation, deletion, duplication, illegal order, sequence, digest) | RA-07 C5 probes (6) | PASS |
| §14 C6 frozen-RC wrong repo / missing git / Core or tests mutation / foreign import → BLOCKED | RA-07 C6 probe | PASS |
| §14 C7 SQLite/OpenSSL pin + import purity | RA-07 C7 probe (exact pins, frozen Core tree, no foreign `aios_core`) | PASS |
| §14 C8 clean-room four-input boundary | RA-07 C8 probe (AST reachability; four approved startup inputs) | PASS |
| §14 C9 run_due_work via frozen Core with external model boundary | RA-06 due-work probe + author C9 in the regression tier | PASS |
| §15 #290 request-file mutation retest | RA-06 direct-consume mutation probe (response binding intact; mutated request unusable; integrity reports the drift) | PASS |
| §18 synthetic due-work integration with a disposable World | RA-06 mixed due-work + user-turn probe (frozen Core → due work → durable request → external test-only response → consume → `wake_state == completed`) | PASS |
| §22 lock path replacement / symlink / inode race, stale lock across restart, abandoned holder, nested ordering, durability-proof→ledger-append TOCTOU, cross-process retry after partial failure, simultaneous due-work + user-turn, packet/hash coverage omissions | RA-05 (4 lock probes), RA-06 (TOCTOU + mixed root), RA-03/RA-04 (retry/convergence), §6 below (coverage audit) | PASS |

## 4. Regression tier (§16) and gates (§17)

Author suites were executed as **regression evidence only**, under the reviewer runtime, against the
frozen H2 package and frozen RC (`raw/`, `raw/gates/gates/`):

| Tier | Expected | Observed |
| --- | --- | --- |
| C10/C11 (author concurrency/durability probes) | 18 PASS | **18 passed** (13.58 s) |
| C1–C3 runner | GREEN | **GREEN** (`C1_IA_OP_001`, `C2_IA_OP_002`, `C3_IA_OP_003`) |
| C4–C9 (corrective-002 frozen probes) | 103 PASS | **103 passed** (collected 103, 8.91 s) |
| Gate A | PASS / 24 | **PASS / 24** (enumeration `14de1d5d…`, raw `6d4280c2…`) |
| Gate B | PASS / 7 | **PASS / 7** (enumeration `b4d99aa4…`, raw `666ab4d8…`) |
| Gate C | PASS / 2 | **PASS / 2** (enumeration `910f9f5f…`, raw `fba9d7bf…`) |
| Gate D | PASS / 5 | **PASS / 5** (enumeration `bc0afa61…`, raw `ecc118e7…`) |

- Every gate verified collect rc, collected count, execution total, per-test IDs and outcomes
  (0 failures/errors/skips) in its `gate_*_result.json`; the environment triple in each gate equals
  the reviewer runtime pins.
- **Gate C is non-vacuous**: the two-round integration ran real frozen-Core capability work — round-1
  request `req-0002-model_directive-1822126c` carries a real `CapabilityResult`
  (`name=search_world`, `ok=true`, real object ids, `call_id=synthetic-call-0001`), the world
  revision advances 0 → 2, the exchange ledger chains 6 records, and recovery classifies `COMPLETE`.
- **Gate D reviewer pass**: independent AST review of all 11 runtime modules found no keyword→capability
  routing, no cursor/event→response mapping, no hard-coded claim/goal/policy text, no prewritten
  replies, no fallback or default directives, no callback/handler registries, and no reachability into
  test/synthetic/fixture/evaluator code. Long string literals are documentation and error text only;
  the only `pytest` reference is inside the mechanical environment probe (`verify_environment`).
  `raw/reviewer_gate_d_manual_scan.txt`.
- Note (non-blocking, evidence-tooling): `gate_runner` writes its artifacts one level below the
  supplied `--evidence-dir` (`raw/gates/gates/`); `scripts/run_regression.sh`'s summary printer
  expected `raw/gates/gate_summary.json` and printed "gate_summary.json missing". All gate evidence
  exists and is complete at the nested path; no gate re-run was needed.

## 5. Freeze integrity recompute (§19) and hash coverage (§20, §22)

Recomputed independently against the frozen H2 package:

| Artifact | Declared | Recomputed |
| --- | --- | --- |
| Launch packet | `3c2d04c2…` (status `PREP_REVIEW_READY`) | equal, status unchanged |
| Package freeze manifest | `5e79464e…` | equal |
| `P/evidence/SHA256SUMS` | `27ab476a…` | equal (73/73 files, zero uncovered, zero hash mismatch) |
| Final packet audit | `43fec69d…` | equal |
| Harness manifest content digest / file | `f3fbd788…` / `2bc303cd…` | equal (30 entries: 27 harness + 3 bootstrap) |
| Wheel trust root (wheel lock file) | `6fa2587c…` | equal (11 pinned wheels) |
| Frozen Core content manifest | `220718d6…` | equal (77 files) |
| `Q/SHA256SUMS` | `2286803e…` | equal (170 entries; self-excluding, complete) |

Packet-declared hashes were verified file-by-file: bootstrap `e98965d8…`, clean-room contract
`ed5140bd…`, Resident run contract `9b8a6cc5…`, environment record `a43ceea3…`, clean-bootstrap
evidence `59285dfd…`, durability fault evidence `de528b16…`, concurrency integration `0334f38e…`,
C1–C3 regression `416ebb9f…`, RC identity `11c985fe…`, C10/C11 probe freeze `573a55d1…`, enumeration
`7af537fd…`, source hashes `1f956a7e…`, corrective probe freeze (corrective-002 `PROBE_FREEZE.v2.json`)
`a0813c69…`, `atomic.py` `b2f8df92…`, `ledger.py` `31356e9d…` — **all equal**.

**Coverage audit from git objects** (not from the working copy): P = 73 files / 73 sums entries,
zero uncovered, zero mismatches, zero ghost entries; Q = self-excluding, 170 covered entries including
the nested `probes/PROBE_SHA256SUMS`. No packet/hash coverage omission found. Self-reference design is
sound: no sums file lists itself; the packet carries no self-hash (the audit carries `packet_sha256`).

## 6. No real Resident / no fixture / no release state (§21)

- Packet status remained `PREP_REVIEW_READY`; the packet's own audit reports
  `no_real_resident_or_fixture=true`, `independent_acceptance_not_claimed=true`, and its forbidden
  startup list (fixture payload, evaluator expected semantics, release operator source and state,
  Resident runs, PM governance) is enforced by the launch tools (C8 probe).
- The forbidden directories exist in the repository (they are pre-existing `main` content) but are
  **untouched by PR #292** and were not read or used by this review; all review execution state is
  disposable pytest temp state (`/tmp/pytest-of-user/...`).
- No cursor was revealed, no release state was initialized, no evaluator or C15 close was run.

## 7. Revision-1 failures (transparency)

Nine revision-1 failures were all triaged to probe/execution defects and are individually documented
in `REVISION_NOTES_v2.md`: implicit-vs-declared identity conflation (1), over-specified resume route
(1), holder rendezvous assertion (2), artifact-aware helper on a raw record (1), drift-vs-detection
expectation conflation (1), wrong receipt field (1), live-main `src` shadowing via the repo's pytest
ini (1), naive substring match inside a prohibition docstring (1). Each correction is visible as a
diff between `probes/` and `probes_v2/`; all nine subjects pass in revisions 2 and 3, including under
the independent mechanisms introduced in revision 2 (import-purity guard, AST reachability).

## 8. Limitations and disclosures

1. Freeze/commit ordering for revisions 2 and 3 (freeze artifact written before execution, committed
   with the results afterwards) is disclosed in `REVISION_NOTES_v3.md`; mtime and post-run hash
   evidence prove no expectation changed after candidate behavior was observed.
2. Gate evidence is stored at `raw/gates/gates/` (gate-runner nesting), not `raw/gates/` as the
   regression script's summary printer assumed.
3. The review executed the candidate package from a reviewer-owned export; export-local
   `__pycache__` files are not part of the candidate tree and are absent from the candidate's
   `SHA256SUMS`.
4. This review does not claim semantic evaluation, PM integration, or Resident launch authority.

## 9. Evidence index

| Path | Content |
| --- | --- |
| `probes/`, `probes_v2/`, `probes_v3/` | probe revisions 1–3 with freezes, enumerations, expectations |
| `REVISION_NOTES_v2.md`, `REVISION_NOTES_v3.md` | failure triage, corrections, freeze/commit ordering |
| `make_freeze_v2.py`, `make_freeze_v3.py` | freeze generators (self-hashed inside each freeze file) |
| `env/` | reviewer runtime build/verify logs, environment record, environment probe |
| `raw/reviewer_probes_v{1,2,3}.*` | raw probe execution logs, JUnit XML, collections, enumeration diffs |
| `raw/reviewer_probes_v{2,3}_integrity.json` | frozen vs post-run source hashes (identical), mtimes, freeze hashes |
| `raw/c10_c11.*`, `raw/c1_c3.*`, `raw/c4_c9.*` | regression tier raw outputs |
| `raw/gates.raw.txt`, `raw/gates/gates/` | gate runner output, per-gate results/raw/tests, Gate C and Gate D test evidence |
| `raw/regression_integrity.json` | regression tier result/hash manifest |
| `raw/reviewer_gate_d_manual_scan.txt` | reviewer-side AST scan for semantic scripting |
| `REVIEW_PLAN.md` | declared method and revision table |
| `REVIEW_SHA256SUMS` | self-excluding checksum listing of this review directory |

**Statement**: this review is an independent acceptance artifact for PR #292. It does not modify,
merge, or repair the candidate; it does not authorize a Resident run; it publishes no real Resident
evidence. Its verdict derives solely from the frozen probe revisions, the independent regression
execution, and the integrity checks recorded above.
