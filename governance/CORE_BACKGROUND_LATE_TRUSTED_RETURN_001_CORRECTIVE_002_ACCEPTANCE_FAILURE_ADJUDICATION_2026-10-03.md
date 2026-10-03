# CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002 — Acceptance-Failure PM Adjudication (WINDOW 21)

- **Date:** 2026-10-03
- **Window:** WINDOW 21
- **Formal task:** `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002-ACCEPTANCE-FAILURE-PM-ADJUDICATION`
- **Role:** Core Governance PM / Acceptance-Failure Adjudicator
- **Merge policy:** `GOVERNANCE_ONLY_AT_END` (this window performs no integration)
- **Repository:** `Haneof/Haneof-AIOS-Core-v3.0`
- **Status:** COMPLETE / CLOSED after the writeback defined in §7

## 0. Adjudication provenance and role disclosure

This adjudication is executed under the explicit instruction of the operator
("开启 Window 21 — PM Acceptance-Failure Adjudication，仅裁决 BLK-W20-001，不做集成、不修代码").
Its mandate is limited to ruling on the single Window 20 blocker; it does **not** integrate
PR #310, does not modify candidate code, and does not open the next corrective window.

**Disclosure.** The adjudicator is the same agent that performed the WINDOW 20 independent
acceptance. A separate adjudicator was not available. This record therefore does not rest on
reviewer authority: every material fact below was **re-derived by this window** from
(a) fresh live ground truth, (b) fresh source inspection of the exact candidate
(`fec30bd1495017bf13f08b0ef5b1e241dfb0e247` fetched anew), and (c) a fresh re-execution of the
frozen blocker probe suite in a new sandbox worktree (§2.3, log published in §7). All Window 20
artifacts are published and independently checkable in review-only PR #311.

## 1. Fresh ground truth

WINDOW 21 independently re-fetched the repository before adjudication.

- live `main`: `ca47087fb68c90d6ac380c11143a0e36e80fc04a`
- PR #310: `OPEN / UNMERGED / DO NOT MERGE`, head `fec30bd1495017bf13f08b0ef5b1e241dfb0e247`
  (unchanged since the Window 20 review; **no drift**, therefore `REVALIDATION_REQUIRED` is **not**
  triggered and the acceptance verdict is adjudicated on the exact reviewed SHA)
- Window 20 review commit (verdict + blocker evidence): `220311759e88fb3948ad3f4dba655058e0f392a8`
- Window 20 review branch: `arena/01a1006b-haneof-aios-core-v3-0` (`REVIEW_ONLY / DO_NOT_MERGE`),
  review PR **#311** (tip at adjudication `6582af6dab708221d4f598f5d7715d38e191a65c`)
- formal Window 20 IA comment on PR #310: id `5966444269` (`2026-10-03T06:41:12Z`)
- changes from `22031175…` to `6582af6d…`: additive documentation only
  (`PR_COMMENT.md`, `PR_COMMENT.md.sha256`, `PUBLICATION_RECORD.md`,
  `REVIEWER_STATE_LEAK_IN_TOOL_PROCESS.txt`, completed `PROBE_REVISION_LOG.md`, regenerated
  `SHA256SUMS`). Verified by `git diff`: every blocker evidence file — both probe sources,
  `SHA256SUMS.v3`, both v3 raw logs, both freeze manifests, `IA_REPORT.md`,
  `TRUST_MINT_PATH_AUDIT.md` — is **byte-unchanged** since the review commit.

No candidate drift, main drift, or review-parent mismatch was observed at adjudication start.

## 2. Adjudicated verdict

`CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002 = DONE / ACCEPTANCE_FAIL / blocker=1`

Disposition: `CORRECTIVE_REQUIRED`.

The single Window 20 blocker is **BINDING**. It is not downgraded to an observation, hardening
item, test-only issue, documentation issue, or "already known limitation". The author-owned green
formal CI (run `37099376296`, all five jobs success), the 896-test claim, the reviewer's own 231
consecutive focused passes, and the substantial positive properties independently reproduced by
Window 20 (§4) remain valid evidence — and they do not override a trust-minting oracle.

PR #310 exact candidate `fec30bd1495017bf13f08b0ef5b1e241dfb0e247` is permanently frozen as:

`FAILED_EXACT_CANDIDATE / FROZEN / OPEN / UNMERGED / DO_NOT_MERGE`

No corrective commit may be appended to PR #310. No force-push, rebase, squash, amend, or history
rewrite is authorized. The freeze is recorded on the PR itself (§7).

The Window 20 review commit `220311759e88fb3948ad3f4dba655058e0f392a8` and branch
`arena/01a1006b-haneof-aios-core-v3-0` are permanently:

`REVIEW_ONLY / IMMUTABLE / DO_NOT_MERGE`

(only the append-only appendix additions already recorded in §1 remain allowed; no review
evidence may be rewritten, and the review branch must never be merged).

### 2.3 Adjudicator re-verification of the blocker

To exclude transcription and environment artifacts, this window re-executed the frozen blocker
suite in a fresh sandbox:

- probe: `window20_independent_attack.py`, SHA-256
  `ec1dc5c2c5406d5d9e74825f62e0a17fb80f8ebd6dc250817fa048511ce292b5` (verified against
  `SHA256SUMS.v3`; nothing edited, no expectation changed)
- target: fresh detached worktree at `fec30bd1495017bf13f08b0ef5b1e241dfb0e247`
  (re-fetched via `refs/pull/310/head`; worktree clean before and after)
- environment: CPython 3.11.2 / pydantic 2.13.5 / SQLite 3.40.1 / OpenSSL 3.0.20
  (reviewer-class environment; the formal 3.12.14 target remains unobtainable in-sandbox, as
  disclosed in Window 20 — the disclosure is carried forward, not re-adjudicated)
- result: `SUMMARY | probes=4 failures=4`, **byte-identical** to the Window 20 record
- log: `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002_IA_WINDOW_20/adjudication/ADJUDICATION_RERUN_SUITE_A_v3.txt`

The blocker is reproducible from a clean checkout; it is not an artifact of the Window 20 sandbox.

## 3. Blocker ruling

### 3.1 BLK-W20-001 — BINDING

`RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW`

**PM ruling:** BINDING / Core trust-boundary defect / curable only in a new corrective candidate.
Severity: CRITICAL.

**Root cause:** `TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE` — the corrective replaced
a recovery-reachable minting *helper* with a publicly issuable *authority object*, so the property
required by `C2-1` / `C2-2` ("a caller cannot create trusted receipt/handoff state without a valid
external proof or a capability that the caller cannot manufacture") is still not implemented.

**Fresh source inspection of the exact candidate (file:line):**

- `src/aios_core/runtime/live_return.py:156` — `open_live_provider_return_window(*, attempt_id)`
  is a **public module-level context manager**. Its only precondition is "no window is already
  armed on this call stack" (`:167`); it then calls `LiveProviderReturnWindow._issue(...)` itself
  with the module's own `_ISSUE_SENTINEL` (`:173`), registers the window in `_OPEN_WINDOWS`
  (`:179`) and arms `_ACTIVE_WINDOW` (`:180`). Every element of the identity check is therefore
  satisfied *by construction* for any caller that calls this function.
- `src/aios_core/runtime/live_return.py:191` — `register_handler_return(window, directive)` is also
  public and requires only an open window the caller itself armed; it stores `id(directive)` in
  `_HANDLER_RETURNS` (`:204`).
- `src/aios_core/runtime/live_return.py:207-227` — `_require_open_window` checks isinstance,
  process-registry identity, armed-on-this-stack, and open state. All four are caller-manufactured,
  so this is a *consistency* check, not an *authority* check.
- `src/aios_core/runtime/live_return.py:231-259` — `consume_live_provider_return_window` adds the
  "exact bytes the provider handler returned" test (`_HANDLER_RETURNS[window_id] == id(directive)`).
  That registry is written **only** by the public `register_handler_return`, so a caller registers
  its own directive as the handler return and the freshness binding is likewise self-satisfied.
- `src/aios_core/runtime/live_return.py:273-281` — `__all__` exports both functions (plus
  `LiveProviderReturnWindow`, `consume_live_provider_return_window`, `live_return_authority_snapshot`).
- `src/aios_core/runtime/background_attempt.py:2416` — `record_live_provider_return(...)` is an
  ordinary public store method reachable as `runtime.background_model_attempts`; its **only** gate
  is `consume_live_provider_return_window(...)` (`:2443`), after which it writes durable receipt +
  handoff rows and completes/meters the turn.
- `src/aios_core/runtime/background_attempt.py:2426-2434` — the method's own docstring asserts
  "it is not an API that accepts caller-supplied bytes on its own: the mandatory ephemeral
  ``live_window`` can only be satisfied from inside the live model-call frame" and "A post-crash
  recovery caller calling this method directly fails closed." **Both claims are falsified by the
  probes.** The candidate therefore does not merely leave a gap in an unclaimed area; it claims a
  property it does not have.
- Reflection: `type(store).record_live_provider_return.__globals__` and
  `LiveProviderReturnWindow._issue.__func__.__globals__` expose the live-return module namespace,
  so the same authority is reachable without importing the module by name (probe `IA20-OBJGRAPH-002`).
- Genuine use sites exist and are unaffected as *call sites*
  (`cognitive_runtime.py:210`, `:407`) — the defect is that the same API is equally usable by any
  other caller.

**Empirical reproduction (frozen reviewer probes, run by WINDOW 20 and re-run by this window):**

| Probe | Expected | Observed on `fec30bd…` |
|---|---|---|
| `IA20-MINT-003` | caller outside the genuine provider frame cannot mint | `minted=True, state=metered, receipts=1, handoffs=1, responses=1, meters=1, turn_response='FORGED_VIA_PUBLIC_LIVE_WINDOW_API_NO_PROVIDER_CALL', genuine_rsa_return_conflicted=True` |
| `IA20-MINT-004` | verifier-less attempt stays permanently `in_doubt` | `state=metered, receipts=1, handoffs=1, responses=1, meters=1, turn_response='FORGED_ON_VERIFIERLESS_ATTEMPT_VIA_PUBLIC_WINDOW'` |
| `IA20-OBJGRAPH-002` | no mint authority reachable from the recovery object graph | `reachable_via=[record_live_provider_return.__globals__, _issue.__func__.__globals__], minted=True, receipts=1, handoffs=1` |
| `IA20-WINDOW-001` | all non-live satisfactions refused | refused: none / wrong-attempt / closed / copy / deepcopy / pickle / other-thread / unregistered / direct ctor — **admitted: self-issued window (`d_replay.first=MINTED`), cloned store world (`g_other_world=MINTED`), detached context (`j_detached_context=MINTED`)** |

**Contract mapping (violations):**

- `C2-1` — recovery-reachable code can create trusted receipt/handoff state with no external proof.
- `C2-2` — the live-return authority is neither call-stack-confined nor non-reissuable: it is
  *issued on demand* by a public function, and it is process-global state that a cloned world or
  detached context will also accept (`g_other_world`, `j_detached_context`).
- `T1` / `T2` / `T4` (frozen in the WINDOW 15 adjudication and inherited by this line) — the
  recovery caller must be able to *verify* but never *mint*; here any process-local caller mints.
- `T6` (verifier-less strict fail-closed) — bypassed: a `late_return_verifier=None` attempt leaves
  `in_doubt` and reaches `metered`.
- The frozen anti-regression rule of this task line ("Python underscore naming / call convention is
  not an authorization boundary") reappears in new form: a single-caller *convention documented in
  a docstring* is likewise not a boundary.

**Counter-arguments considered and rejected:**

1. *"This requires code execution inside the Core process, which is already a compromise."* —
   Rejected. This task line's own `C2-1`/`T1`–`T4` define the recovery/process-local caller as
   in-scope; the line's history (`BLK-W14-001` → `BLK-W17-001` → this) is precisely about the
   caller being unable to mint. A structural invariant cannot be discharged by an attacker-model
   argument that the frozen contract already excludes.
2. *"The frozen Window 17 probe suite is GREEN on `fec30bd…`, so `BLK-W17-001` is closed."* —
   Rejected. The frozen MINT probes are name-based and `IA17-OBJGRAPH-001` is name-filtered and
   depth-limited; they cannot observe a renamed successor mechanism. Within this line, green frozen
   probes are necessary but not sufficient, exactly as Window 20 recorded.
3. *"The window is ephemeral and absent after process death, so `C2-2` is satisfied."* — Rejected.
   `C2-2` requires the capability to be ephemeral **and** call-stack scoped **and** non-reissuable;
   here issuance is public and repeatable, the armed state is process-global, and residue from one
   stack denies genuine returns on another (`OBS-W20-003`).
4. *"Impact is bounded to an already-dispatched attempt."* — Rejected. The probe shows durable
   receipts/handoffs written from caller bytes, a completed and metered turn with attacker content
   (`turn_response='FORGED_…'`), a genuine external RSA return for the same attempt conflicted, and
   a verifier-less attempt forced out of its mandated permanent `in_doubt` state.

**Minimal corrective scope (mandated; the corrective window owns the design, not this window):**
issuance of trusted-return authority must require something a caller cannot manufacture — for
example a capability minted inside the genuine model-call frame, never exported, never importable,
never reachable via `__globals__`/`sys.modules`/registry/bound-method/closure, with any
caller-satisfiable identity checks removed from the authorization path; or the removal of the
live fast path in favour of requiring verifiable external proof for all trusted returns. See §5.

## 4. Positive properties that must not regress

Window 20 independently established the following on `fec30bd…`; Corrective-003 must preserve all
of it (regression here is itself blocking):

- frozen Window 17 reviewer probes, extracted fresh from canonical review `e4161dd0…`
  (SHA-256 `a6db3395…`, byte-verified): RED `probes=14 failures=6` on `cb8a6b3c…` →
  GREEN `probes=14 failures=0` on `fec30bd…`;
- migration: verify-before-convert, whole-DB atomicity, tampered last row converts nothing,
  legacy secret preserved, every retry and all edge branches fail closed (`IA20-MIGRATE-003/004`);
- RSA: canonical `bglate_rsa_v1:<key_id>:<sig_hex>` round-trip, key-id grammar enforcement,
  parameter validation matrix (`IA20-RSA-ENC-001`, `IA20-RSA-PARAM-001`), and 12/12 bound-field
  transplant rejection with a reviewer-generated RSA-2048 key (`IA20-RSA-TRANSPLANT-001`);
- post-binding `not_submitted` closure and no redispatch (`IA20-NOTSUB-002`); exactly-once /
  first-writer-wins / effect-free replay / R5 durable effects (`IA20-EXACTONCE-001`);
- Window 16/17 positives: `MIGRATE-001`, `VERIFIER-SUB-001`, `DB-AT-REST-001`, `RSA-001`,
  `RACE-CRASH-001`, `NS-ROUTE-B-001`, `ID-JSON-001`, `SIGKILL-001`;
- scope/identity: 39 files `+6049/−261`, out-of-scope `0`, forbidden paths `0`, and the final
  evidence-only commit byte-identical in `src/**`, `tests/**`, `.github/**`;
- test-diff discipline: the seven modified test files were adjudicated as TIGHTEN-only, with no
  security assertion removed.

**Non-blocking observations carried forward** (no change of status by this window):
`OBS-W20-001` stale manifest metadata (closed as observation); `OBS-W20-002` resident-surface gate
passes vacuously when `--base main` is unresolvable — tooling debt, **not** this corrective's scope;
`OBS-W20-003` process-global armed window can deny genuine returns and foreign-issued windows are
accepted across worlds/contexts — folded into `C3-7`; `OBS-W20-004` odd-length hex signature
representable but never verifiable (fail-closed encoding nit); `OBS-W20-005` pydantic lax coercion
of integral float exponents to `int` (no authority impact); `OBS-W20-006` CI artifact bytes not
retrievable from the reviewer sandbox (accepted disclosure; metadata verified).

## 5. Unique next READY — WINDOW 22

The only next READY task is:

`CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003`

WINDOW 22 must use a **brand-new engineering branch + brand-new PR from fresh live main**. It must
not append commits to PR #310, and it must not modify any review branch or the Window 20 evidence.

### 5.1 Frozen Corrective-003 scope

1. **C3-1 — No caller-manufacturable authority.** No module-level function, exported symbol, store
   method, classmethod, registry entry, context manager, or test helper reachable by an ordinary
   process-local caller may issue or arm trusted-return authority. Issuance must require authority
   the caller cannot produce (e.g. minted inside the genuine model-call frame by non-exported code,
   or not present at all in favour of external proof).
2. **C3-2 — Reflection-proof.** The authority must be unreachable from recovery object graphs via
   `__globals__`, `sys.modules`, module attributes, closure cells, bound methods, `object.__new__`
   or similar; the `IA20-OBJGRAPH-002` walk must be unable to reach any mint path.
3. **C3-3 — Verifier-less stays `in_doubt`.** Any attempt without a durable external verifier
   binding must be structurally unable to leave `in_doubt` other than by a genuine external proof;
   the `IA20-MINT-004` path must fail closed.
4. **C3-4 — Exact-bytes binding must not be self-assertable.** The "handler returned these bytes"
   fact must be established by code the caller cannot invoke or forge, not by a public
   registration call.
5. **C3-5 — Preserve Corrective-002 positives.** All properties in §4, including the migration, RSA
   and exactly-once results, must remain green on the new candidate.
6. **C3-6 — RED-first, reviewer probes unchanged.** Extract the Window 20 reviewer probe suites
   byte-for-byte from review PR #311 (`window20_independent_attack.py` `ec1dc5c2…`;
   `window20_migration_rsa_attack.py` `76924246…`), verify their SHA-256 values, run them against
   `fec30bd…`, and preserve the real failing results before editing `src/**`. No probe edit, no
   expectation change, no test weakening; the same suites must be GREEN on the new candidate.
7. **C3-7 — Window hygiene closure.** A window must be bound to the genuine world/store and call
   stack it was issued for (no cross-world or detached-context acceptance), and residual/abandoned
   authority state must not deny genuine returns (`OBS-W20-003`).
8. **C3-8 — Scope discipline.** No C15 persistence/operator/Resident evidence mutation; no changes
   to PR #302, #305, #308, #310, the Window 14/17/20 review branches, historical persistence refs,
   retired run evidence, or the task board's frozen history. Engineering owns implementation only,
   may push/update its new branch/PR, and must not merge. It stops at
   `REVIEW_READY / READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE`.

## 6. Mandatory sequence after WINDOW 21

1. WINDOW 22 — `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003`
2. WINDOW 23 — Fresh Independent Acceptance of the exact Corrective-003 candidate
3. WINDOW 24 — PM Integration Receipt **only if** Window 23 returns `ACCEPTANCE_PASS / blocker=0`
4. then `CORE-RC-REFREEZE-004` + Fresh IA
5. then fresh `C15-RCC-RES-A-RERUN-005` + Fresh IA
6. then `C15-RCC-RES-B-OPERATOR-PROVENANCE-CORRECTIVE-001` + Fresh IA
7. then `C15-RCC-RES-B-RELEASE-004`
8. then `C15-RCC-RES-B-RERUN-004`
9. then `C15-RCC-RES-B-ACCEPT-004`

All downstream C15 release/Resident/evaluator/close work remains BLOCKED until its upstream
dependency is accepted and integrated.

## 7. WINDOW 21 writeback policy (as executed)

WINDOW 21 is governance-only. It changes only:

- this adjudication record;
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md` (new top control entry);
- `AIOS_v3.0_CURRENT_CHECKPOINT.md` (new top section);
- the adjudicator re-verification log inside the published Window 20 review package
  (`reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002_IA_WINDOW_20/adjudication/`),
  which is additive and modifies no existing review evidence;
- PR #310 freeze metadata (title marker) and the formal adjudication comment on PR #310.

Zero `src/**`, `tests/**`, `tools/**`, workflow, Resident, evaluator, or release changes; no
candidate branch push; no merge. After the writeback and the PR #310 comment, WINDOW 21 is
COMPLETE / CLOSED, and WINDOW 22 engineering must not begin inside it.

### 7.1 Published under a branch constraint (disclosure)

This session's publication channel is fixed to the review branch
`arena/01a1006b-haneof-aios-core-v3-0` (review PR #311). Unlike WINDOW 18/15, whose adjudication
records were merged to `main` through a dedicated governance PR, this record is therefore
published as a commit on that review branch and is durable there. No merge to `main` is performed
by this window, and no other branch is created, switched, or pushed to. Downstream readers should
treat the adjudication record, the task-board entry, and the checkpoint entry as **pending PR
#311 merge** for their `main`-visible effect while the ruling itself is final and immediately
binding on the process.

## 8. Delivery receipts (as executed)

| Item | Value |
|---|---|
| Adjudicator re-run log commit | `88a52d9d00c6327505ceaff2797518468a681a4d` |
| Governance writeback commit | `28209d7b3bbe124292760d86fcae1032f407f7af` |
| Publication channel | review PR **#311**, branch `arena/01a1006b-haneof-aios-core-v3-0` (branch-constrained session; see §7.1) |
| PR #310 freeze title | `[IA_FAIL / blocker=1 / FROZEN / DO NOT MERGE] CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002 — PM adjudicated; Corrective-003 READY` |
| Formal adjudication comment on PR #310 | id `5967132469`, `2026-10-03T08:21:36Z`, <https://github.com/Haneof/Haneof-AIOS-Core-v3.0/pull/310#issuecomment-5967132469> |
| Review package integrity at publication | 52 files, `SHA256SUMS` verified, 0 failures |
| Candidate state | PR #310 `OPEN / UNMERGED`, head `fec30bd1495017bf13f08b0ef5b1e241dfb0e247` (unchanged) |
| Integration / merge / code change performed | **none** (by mandate) |
