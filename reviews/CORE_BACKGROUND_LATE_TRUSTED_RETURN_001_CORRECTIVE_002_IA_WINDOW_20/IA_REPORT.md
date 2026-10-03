# WINDOW 20 — Fresh Independent Core Runtime Acceptance Report (`IA_REPORT.md`)

```text
WINDOW_20 = COMPLETE / CLOSED

CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE
= ACCEPTANCE_FAIL / blocker=1

CORRECTIVE_OR_ADJUDICATION_REQUIRED

reviewed_exact_candidate:
fec30bd1495017bf13f08b0ef5b1e241dfb0e247          (PR #310, OPEN / UNMERGED / DO NOT MERGE)

historical_red_anchor:
cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd          (PR #308, frozen failed candidate)

verdict_owner: Fresh Independent Core Runtime Acceptance Reviewer (WINDOW 20)
merge_policy:  NO MERGE AUTHORIZED — return to PM (Window 21 integration not entered)
```

---

## 1. Executive Summary

I performed a clean-room, reviewer-owned acceptance of `PR #310` exact candidate
`fec30bd1495017bf13f08b0ef5b1e241dfb0e247`, without trusting the Window 19
summary, the author evidence package, author-owned tests, or the formal CI result
as security evidence.

**What holds up (independently re-proved):**

- The Window 17 frozen reviewer probe suite (`window17_independent_attack.py`,
  SHA-256 `a6db3395…`, extracted fresh from canonical review `e4161dd0…`, **not**
  copied from the author package) reproduces historical RED on
  `cb8a6b3c…` (`SUMMARY | probes=14 failures=6`, exactly `IA17-MINT-001`,
  `IA17-MINT-002`, `IA17-DOWNGRADE-001`, `IA17-MIGRATE-002`, `IA17-OBJGRAPH-001`,
  `IA17-RSA-DELIMITER-001`) and GREEN on `fec30bd…` (`probes=14 failures=0`).
- `BLK-W17-002` (legacy migration) is genuinely corrected: verify-before-convert,
  single-transaction, no partial rewrite, secret never purged on failure, retry
  fail-closed, orphan/duplicate/mismatch/transplant branches refused.
- `BLK-W17-003` (RSA encoding + parameters) is genuinely corrected: canonical
  `key_id` grammar with proven `encode → decode → identical` round-trip, canonical
  modulus/exponent validation, all 12 bound-field transplants rejected against a
  genuine reviewer-signed proof.
- Post-binding `not_submitted`, conflicting-replay fail-closed, first-writer-wins
  and exactly-once durable effects hold.

**What fails (binding):**

- `BLK-W17-001` is **not closed**. The old recovery-reachable mint oracle was not
  eliminated; it was relocated behind a token that the same class of caller can
  mint itself. `aios_core.runtime.live_return.open_live_provider_return_window` and
  `register_handler_return` are ordinary public module-level functions, and
  `BackgroundModelAttemptStore.record_live_provider_return` is an ordinary public
  store method. Three reviewer probes prove mechanically that a post-crash
  recovery caller with no RSA key and no provider call can mint a durable receipt +
  handoff, complete and meter the turn with attacker-authored bytes, poison the
  genuine external RSA return, complete an anonymous/no-verifier attempt that must
  stay `in_doubt`, and reach the same authority by pure reflection from the
  recovery object graph (`__globals__`) without importing the module by name.

**Verdict: `ACCEPTANCE_FAIL / blocker=1 / CORRECTIVE_OR_ADJUDICATION_REQUIRED`.**

---

## 2. Fresh Ground Truth (verified, not inherited)

| Item | Freshly verified value | Method |
|---|---|---|
| live `main` | `ca47087fb68c90d6ac380c11143a0e36e80fc04a` | `gh api …/git/ref/heads/main` + `origin/main` |
| `PR #310` | `OPEN`, `isDraft=false`, `mergeable=CLEAN`, base `main`, head branch `arena/01a10010-haneof-aios-core-v3-0`, `headRefOid=fec30bd1495017bf13f08b0ef5b1e241dfb0e247`, 39 files, `+6049 / −261` | `gh pr view 310 --json …` |
| `PR #310` commits | `f088ce10` (carry-forward) → `7db79da5` (Corrective-002 code) → `fec30bd1` (evidence-only) | `gh api …/pulls/310/commits` |
| `PR #308` | `OPEN`, head `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (frozen failed candidate) | `gh pr view 308 --json …` |
| Window 17 canonical review | `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8`, sole parent `cb8a6b3c…`, 20+ evidence files incl. `reviewer_probes/` | `gh api …/commits/e4161dd0…` |
| Frozen W17 probe | `window17_independent_attack.py` SHA-256 `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3` — **exact match** to the canonical claim | fresh extraction + `sha256sum` (`reviewer/W17_PROBE_IDENTITY.txt`) |
| construction base / merge-base | `ca47087…` for both `fec30bd…` and `cb8a6b3c…` (re-derived, not trusted) | `git merge-base` |
| Candidate drift | **none** — remote branch tip still `fec30bd…` at publication time | `gh api …/git/ref/heads/arena/01a10010-…` |

`7db79da54b26266c5ec519f3e70dd25dff4a95fb → fec30bd…` is **exactly one commit**
(`git rev-list --count` = 1) touching only:

- `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002/FINAL_HANDOFF.md` (A)
- `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002/FORMAL_CI_RESULTS.md` (A)
- `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002/SCOPE_MANIFEST.md` (M)

`src`, `tests`, `.github` subtree hashes are **byte-identical** across that commit
(`src 8215987…`, `tests 1d69b90…`, `.github 7220a4b…` at both SHAs). No
implementation or test byte changed in the evidence-only commit → no blocker on
this axis.

---

## 3. Scope Audit (`SCOPE_AUDIT.txt`, `SCOPE_DIFF_NAME_STATUS.txt`)

- Independently enumerated all **39** files of `main…fec30bd…`; totals
  `files=39 +6049 −261`.
- `out_of_scope_count=0`: every path is within
  `.github/workflows/core-background-late-trusted-return-001.yml`,
  `src/aios_core/runtime/**`, `tests/**`, or
  `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002/**`.
- Zero diff against `tools/c15_persistence`, `tools/c15_preflight`,
  `reviews/internal_habitation`, Window 17 review evidence, release/UI/hardware
  or unrelated architecture (`forbidden-path zero check = 0`).

**`OBS-PM-W19-001` independently confirmed as stale metadata, not hidden scope:**
`git diff --shortstat main 7db79da5` = `37 files, 5801 insertions(+), 261
deletions(-)` — exactly the numbers still printed in `SCOPE_MANIFEST.md` — and the
delta to the live PR is precisely the `+258 / −10` of the evidence-only commit.
The scope itself is clean, so this is recorded as an evidence-metadata
observation (`OBS-W20-001`), not a blocker.

---

## 4. Binding Blocker

### `BLK-W20-001` — `RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW`

- **Severity:** `CRITICAL`
- **Status of the Corrective claim:** `BLK-W17-001` **NOT CLOSED** (naming/indirection
  change only; authority remains caller-reachable)
- **Exact source paths / lines (candidate `fec30bd…`):**
  - `src/aios_core/runtime/live_return.py:157-181` — `open_live_provider_return_window`
    (public module-level function; exported in `__all__`; the only precondition is
    `_ACTIVE_WINDOW.get() is None`, i.e. the caller must not already hold one)
  - `src/aios_core/runtime/live_return.py:190-204` — `register_handler_return`
    (public; binds **any** object the caller passes to the window)
  - `src/aios_core/runtime/live_return.py:207-232` — `_require_open_window`
    (isinstance + registry identity + armed `ContextVar` + state — all four are
    satisfiable by the caller itself: the caller issues the window, so the registry
    entry *is* its own object, the `ContextVar` is armed *by its own `with` block*)
  - `src/aios_core/runtime/live_return.py:58-79` — `_ISSUE_SENTINEL`,
    `_OPEN_WINDOWS`, `_HANDLER_RETURNS`, `_ACTIVE_WINDOW` are module globals
    reachable from any reachable function object via `__globals__`
  - `src/aios_core/runtime/background_attempt.py:2416-2530ff` —
    `BackgroundModelAttemptStore.record_live_provider_return` (public; accepts
    `dispatching|in_doubt|response_returned|metered`; the window is the **only**
    gate; inserts the durable receipt and handoff with a keyless
    `bgresponse_v2_<sha256>` fingerprint)
  - `src/aios_core/runtime/cognitive_runtime.py:197-213, 391-414` — the production
    frame uses exactly the same public helpers, so the "live boundary" and the
    attacker path are literally the same code path
- **Reviewer probes (frozen before candidate execution):**
  - `reviewer_probes/window20_independent_attack.py` v3 SHA-256
    `ec1dc5c2c5406d5d9e74825f62e0a17fb80f8ebd6dc250817fa048511ce292b5`
    (`IA20-MINT-003`, `IA20-MINT-004`, `IA20-OBJGRAPH-002`, `IA20-WINDOW-001`)
  - raw: `raw/candidate_w20_probes_v3_on_fec30bd.txt` (`SUMMARY | probes=4 failures=4`)
- **Reproduction (minimal, ~4 lines, no private key, no reflection, no provider call):**
  ```python
  from aios_core.runtime.live_return import (
      open_live_provider_return_window, register_handler_return)
  with open_live_provider_return_window(attempt_id=attempt_id) as window:
      register_handler_return(window, forged_directive)      # attacker's own object
      store.record_live_provider_return(attempt_id, captured_at=…,
          directive=forged_directive, live_window=window)     # durable receipt+handoff
  recovery.run_turn(…)                                        # turn completes and meters
  ```
- **Observed:**
  - `IA20-MINT-003` → `minted=True, state=metered, receipts=1, handoffs=1,
    responses=1, meters=1, turn_response='FORGED_VIA_PUBLIC_LIVE_WINDOW_API_NO_PROVIDER_CALL',
    genuine_rsa_return_conflicted=True`
  - `IA20-MINT-004` (attempt dispatched with `late_return_verifier=None`) →
    `state=metered, receipts=1, handoffs=1, responses=1, meters=1,
    turn_response='FORGED_ON_VERIFIERLESS_ATTEMPT_VIA_PUBLIC_WINDOW'`
  - `IA20-OBJGRAPH-002` (no `import aios_core.runtime.live_return` statement;
    reflection via `type(store).record_live_provider_return.__globals__` →
    `LiveProviderReturnWindow._issue.__func__.__globals__`) →
    `minted=True, state=in_doubt, receipts=1, handoffs=1`
- **Expected (frozen before execution):** a caller that is not inside a genuine
  live provider-return frame cannot mint a trusted receipt/handoff, cannot complete
  or meter the `in_doubt` turn, and cannot make an anonymous/no-verifier attempt
  leave `in_doubt`.
- **Binding invariants violated:**
  - `BLK-W17-001` itself (`RECOVERY_TRUSTED_RECEIPT_AND_HANDOFF_MINTING_ORACLE`);
  - `C1` no post-hoc signing/minting oracle, `C2` verifier-only recovery,
    `C3` secret/authority separation across all recovery-reachable surfaces,
    `C8`/`T6` anonymous-no-authority stays `FAIL_CLOSED`;
  - `T1` verifier-only recovery surface, `T2` no recovery proof minting,
    `T3` recovery-facing object graph must not hold or re-issue minting authority,
    `T4` no post-crash re-issuance;
  - governance anti-regression rule in
    `governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_ACCEPTANCE_FAILURE_ADJUDICATION_2026-10-01.md`
    §4.1 (naming conventions and self-asserted boundaries are not authority) and the
    frozen chain that Corrective work must eliminate:
    `ordinary recovery caller + readable Core state + arbitrary response bytes → accepted trusted return`.
  - Note: the module docstring explicitly discloses "not a defence against
    arbitrary Python code … that deliberately drives this module's issuing
    helpers". That disclosure is honest, but it does not close `BLK-W17-001`: the
    helper is *public API* whose entire precondition set is satisfiable by the
    caller, so the `T1/T2/T3/T4/T6` "live provider-return boundary" does not exist
    as a mechanical boundary for the very caller class Window 17 tested.
- **Minimal corrective scope (not performed here):** make the receipt/handoff
  writer reachable only with authority that a recovery caller cannot manufacture —
  e.g. bind the capture to the cognitive frame's own closure (an object created
  inside `CognitiveRuntime.run_turn` and never exported or importable), remove the
  public issuance functions from the module namespace, and keep the sentinel,
  registry and armed-context out of any module that the recovery object graph can
  reach via `__globals__`; then re-run the frozen W17 suite **and** the W20
  probes in `reviewer_probes/` unchanged.

---

## 5. Independently Verified Positives (evidence of the rest of the corrective)

### 5.1 Frozen Window 17 RED-first reconstruction (mandatory)

The formal `red-first-window14` job is historical W14 evidence (it uses
`5ad0524c…` + canonical W14 review `84457bad…`) — confirmed by reading the workflow
in the candidate; it is **not** W17 frozen-probe evidence. I therefore replayed the
W17 probes myself, extracted fresh from the review object:

| Target | Probe SHA-256 | Result | Raw |
|---|---|---|---|
| `cb8a6b3c…` (frozen failed candidate) | `a6db3395…` | `SUMMARY \| probes=14 failures=6` — `IA17-MINT-001`, `IA17-MINT-002`, `IA17-DOWNGRADE-001`, `IA17-MIGRATE-002`, `IA17-OBJGRAPH-001`, `IA17-RSA-DELIMITER-001` | `raw/frozen_w17_probes_on_cb8a6b3c.txt` |
| `fec30bd…` (exact candidate) | `a6db3395…` | `SUMMARY \| probes=14 failures=0` (`exit 0`), incl. `IA17-MIGRATE-001`, `IA17-VERIFIER-SUB-001`, `IA17-DB-AT-REST-001`, `IA17-RSA-001`, `IA17-RACE-CRASH-001`, `IA17-NS-ROUTE-B-001`, `IA17-ID-JSON-001`, `IA17-SIGKILL-001` GREEN | `raw/frozen_w17_probes_on_fec30bd.txt` |

No probe expectation was modified. Instrument caveat recorded: `IA17-MINT-001/002`
now pass on the candidate because the removed attribute raises `AttributeError`
(the probe is name-based), and `IA17-OBJGRAPH-001` is a name-filtered, depth-limited
walk — so "frozen suite green" is a necessary but **not** sufficient condition; the
new W20 probes were required, and they fail.

### 5.2 Reviewer batch-2 probes (migration / RSA / not_submitted / exactly-once)

`reviewer_probes/window20_migration_rsa_attack.py` (v3 SHA-256 `7692424658…`):
`SUMMARY | probes=7 failures=0` (`raw/candidate_w20_probes_batch2_v3_on_fec30bd.txt`),
using reviewer-owned RSA-2048 material generated in-sandbox (`openssl genrsa 2048`)
and the reviewer's own PKCS#1 v1.5 signer — no candidate signing helper was used.

- `IA20-MIGRATE-003` **PASS** — 3 legacy rows with the **last** one tampered:
  `LegacyTrustMigrationError` on first attempt and on every retry,
  `state_unchanged=True`, `no_v2_proof_anywhere=True`, `secret_preserved=True`
  (no partial conversion; fail-closed retry).
- `IA20-MIGRATE-004` **PASS** — edge branches: empty trust state + staged legacy
  authenticator → fail-closed with staged row and secret intact; empty trust state
  + staged v2 row → completes, secret purged, `receipts_created=0`,
  attempt still `dispatching` (no laundering); two authority rows / wrong authority
  id / already-converted receipts / orphan receipt → fail-closed with secret
  preserved; malformed secret **with** trust state → fail-closed and state
  unchanged.
- `IA20-RSA-ENC-001` **PASS** — all accepted `key_id`s round-trip exactly and verify
  genuine signatures; colon/empty/padding/whitespace/control/NUL/unicode-confusable/
  129-char/leading-hyphen-dot-underscore ids refused at construction; every malformed
  or delimiter-ambiguous proof refused.
- `IA20-RSA-PARAM-001` **PASS** — signed/zero/even/undersized/leading-zero/`+`/`0x`/
  uppercase/whitespace/non-hex moduli and bool/None/negative/0/1/2/even/`e≥n`
  exponents and non-frozen algorithms refused at construction; legal 2048-bit odd
  modulus with `e∈{3,65537}` accepted.
- `IA20-RSA-TRANSPLANT-001` **PASS** — reviewer-signed genuine return completes with
  `meters=1`; all **12** bound-field transplants rejected.
- `IA20-NOTSUB-002` **PASS** — after the durable dispatch/binding boundary,
  `reconcile_not_submitted` and `mark_failure(definitely_not_submitted=True)` are both
  refused (`BackgroundModelResponseConflict`), state stays `in_doubt`, and a second
  `run_turn` performs **no** redispatch (`redispatch_called=False`).
- `IA20-EXACTONCE-001` **PASS** — first genuine return wins exactly once (1 meter,
  1 completion, assistant ref set); conflicting return refused; identical replay is
  effect-free (`NOOP_ACCEPTED`, exactly one staged row).

### 5.3 Independent regression & R1–R5

- Focused trusted-return / recovery / R5 / route-B set: **231 passed, 0 failed**
  (`raw/reviewer_focused_231_on_fec30bd.txt`), including
  `test_core_background_trusted_return_r5_001.py` and `…_r5_conflicts_001.py`
  (R5-A/B/C/D durable-effect exactly-once, terminal-receipt bypass, conflicting
  replay fail-closed) and the reworked historical tests.
- Full local suite: **1104 passed, 1 failed** (`raw/reviewer_full_suite_on_fec30bd.txt`);
  the single failure (`tests/c15_persistence/test_resident_surface.py`) is
  environment/instrument-related, see `OBS-W20-002`; it is **not** caused by this
  candidate and is not a security finding.

### 5.4 Historical test-modification audit (claim "stricter only" — confirmed)

Reviewed all 7 modified historical test files (`git diff main fec30bd -- tests/`):
`test_core_gap_fix_002_background_attempts.py`, `test_turn_execution_recovery.py`,
`test_background_model_attempt.py`, `test_cognitive_runtime_trusted_return.py`,
`test_core_background_response_recovery_001.py`,
`…_corrective_001.py`, `test_core_background_trusted_return_adversarial_001.py`.

- No security assertion was deleted or relaxed. The removed expectations are exactly
  the ones the PM authorized Corrective-001/002 to retire: the post-`mark_dispatching`
  `not_submitted` + retry path (`test_definitely_not_submitted_can_retry_same_attempt_identity`
  → replaced by `test_typed_not_submitted_after_durable_dispatch_stays_in_doubt`, which
  adds `in_doubt`, binding-preserved and no-redispatch assertions) and the
  reconciliation-retry path — both replaced by strictly stronger fail-closed
  expectations, with explicit history notes in the test docstrings (PM test-evolution
  rule satisfied).
- Direct calls to the removed private mint helper were replaced by a helper that
  drives the **production** live-window path, and additional negative assertions were
  added (`not hasattr(store, "_capture_trusted_response_return")`,
  `live_window=None` refused, no receipt rows).
- Adverse consequence for the corrective: those adapted tests also document that the
  "trusted relay return" simulation is nothing but `open_live_provider_return_window`
  + `register_handler_return` — i.e. they are themselves a working demonstration of
  `BLK-W20-001`.

---

## 6. Formal CI / Artifact Verification (`raw/ci_facts.txt`, `raw/ci_run_*.json`)

- Run `37099376296`, workflow `core-background-late-trusted-return-001`,
  `event=pull_request`, `head_sha=fec30bd1495017bf13f08b0ef5b1e241dfb0e247`,
  `status=completed`, `conclusion=success`, `run_attempt=1`.
- All five jobs `success` on the exact candidate SHA: `111135724970`
  (red-first-window14), `111135775618` (phase-a-truthfulness), `111135826231`
  (phase-bc-verifier-only), `111135874085` (phase-ef-sigkill-and-focused),
  `111135979861` (phase-f-full-core-regression).
- All four artifacts present and unexpired with GitHub-reported digests exactly as
  claimed: `11265940047 window16-formal-final`
  `sha256:f56bb9876c5bd45a498c649ed9ee5df88596bc45f14a94e26c85d521441dc18f`,
  `11265677515 window16-phase-ef`
  `sha256:1577ad88428568c8e52cf02a3c40c741b7149e7cdd7614d4a767ddded7e11d18`,
  `11265582727 window16-phase-bc`
  `sha256:997414615f86cf5bf51cb6d4ee21e727f66598886eec1bd268a71931141c2983`,
  `11265537692 window16-red-first`
  `sha256:fc2ebc6649c062357fee779d7b5825c12d3c5f17187062a70a4bbfc5801a61b2`.
- **Disclosed limitation:** the reviewer sandbox egress permits only `pypi.org`,
  `api.github.com`, `github.com`/`codeload` (git). Artifact **blobs** and job
  **logs** are served from `*.blob.core.windows.net`, which is unreachable
  (`EOF`), so I could verify artifact *identity/size/digest metadata* but could not
  download the bytes or read the JUnit XMLs. No reviewer claim in this report
  depends on those bytes; the CI result is used only as navigation plus the PM's
  quoted snapshot, and every security conclusion comes from reviewer probes and
  reviewer-run tests. The `window16-red-first` artifact remains, as PM noted,
  historical W14 RED evidence and is **not** W17 frozen-probe evidence.
- **Environment deviation (disclosed in full, per task §24):** reviewer execution
  used CPython `3.11.2` (formal `3.12.14`; exact 3.12.14 could not be established —
  `objects.githubusercontent.com` build assets are blocked and no
  `libsqlite3`/`zlib`/`openssl` headers exist to build 3.12.14 with `_sqlite3`),
  SQLite `3.40.1` (formal `3.45.1`), OpenSSL `3.0.20` (formal `3.0.13`); pydantic
  `2.13.5` and pytest `8.4.2` match exactly. No 3.11 result is presented as a
  3.12.14 result.

---

## 7. Observations (non-blocking, recorded for PM)

- `OBS-W20-001` — `SCOPE_MANIFEST.md` still prints the pre-evidence-commit totals
  (`37 / +5801 / −261` vs live `39 / +6049 / −261`); confirmed stale metadata, scope
  itself clean (see §3).
- `OBS-W20-002` — the resident-visible gate's pinned-tree check is structurally weak:
  `tools/c15_persistence/resident_surface_check.py:308-322` computes
  `clean = (git diff --stat "<base>...HEAD" -- <scope>.stdout.strip() == "")` and
  ignores the return code, so with `--base main` unresolvable in a CI checkout the
  check passes vacuously. In a correctly-resolved reviewer sandbox the same test
  fails, because this corrective *legitimately* modifies `src/aios_core`. Pre-existing
  tooling (zero diff for `tools/**` in this PR) — reported as an evidence-quality
  observation, not a Corrective-002 blocker.
- `OBS-W20-003` — module-global mutable authority state is hostile to the host
  process: a `ContextVar` left armed by any code that reaches `live_return` state
  permanently blocks subsequent provider returns on that call stack (observed as
  `LiveReturnAuthorityError: a live provider-return window is already open on this
  call stack` in `raw/candidate_w20_probes_v2_defective.txt`). Also, a window issued
  for an attempt id is accepted against a *cloned* durable world with the same id
  (attempt-id scope only).
- `OBS-W20-004` — `canonical_late_return_proof` accepts odd-length lowercase hex
  signatures (representable, but `verify_late_return_proof` always rejects them);
  harmless fail-closed encoding nit.
- `OBS-W20-005` — pydantic lax coercion converts an integral `float`
  (`65537.0`) into `int` `65537` for `public_exponent` instead of refusing a
  non-integer type; the coerced value is mathematically legal, so no authority or
  fail-closed impact.
- `OBS-W20-006` — reviewer sandbox cannot retrieve CI artifact bytes/logs (egress
  policy), see §6.
- `OBS-W20-007` — `IA20-WINDOW-001` confirms the design's genuine strengths: no
  window, wrong attempt id, closed window, consumed window, `copy`/`deepcopy`/
  `pickle`, other-thread use, unregistered forged object and direct construction are
  all refused; only the self-issued window and the (self-issued) armed-context copy
  pass — which is precisely the `BLK-W20-001` issue.

---

## 8. Final Handoff Data (task §32)

| Field | Value |
|---|---|
| fresh live `main` | `ca47087fb68c90d6ac380c11143a0e36e80fc04a` |
| `PR #310` exact head | `fec30bd1495017bf13f08b0ef5b1e241dfb0e247` |
| candidate identity | `fec30bd…`; sole parent `7db79da5…`; construction base `ca47087…`; evidence-only commit confirmed (3 review files, `src/tests/.github` byte-identical) |
| W17 failed candidate | `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (PR #308) |
| W17 review identity | `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8` (sole parent `cb8a6b3c…`) |
| frozen W17 probe hash | `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3` (fresh-extracted, matches canonical) |
| failed-candidate RED | `probes=14 failures=6` (exact W17 blocker set) |
| candidate frozen-probe result | `probes=14 failures=0` |
| reviewer probe revisions | batch 1: v1 `0381c6ce…` (defective harness), v2 `7cb32b5f…` (defective state-leak), **v3 `ec1dc5c2…` current, 4/4 FAIL**; batch 2: v1 `1e429dfe…` (defective harness), v2 `de621da3…` (expectation refinement), **v3 `76924246…` current, 7/7 PASS** |
| trust-mint audit result | 4 writers enumerated; `attach_late_trusted_return` (RSA-gated) OK, migration OK, `stage_exact_response` receipt-gated OK, `record_live_provider_return` **forgeable by any caller** → blocker |
| object-graph attack result | mint authority reachable by pure reflection (`__globals__`) from the recovery runtime; `receipts=1, handoffs=1` |
| migration attack result | verify-before-convert, atomic, secret-preserving, retry fail-closed — **PASS** |
| RSA/parser result | canonical encoding, parameter validation, genuine-proof binding, 12/12 transplants rejected — **PASS** |
| Route-B / `not_submitted` result | all post-binding downgrades refused, no redispatch — **PASS** |
| SIGKILL / exactly-once result | frozen `IA17-SIGKILL-001` green (`exitcode=-9, meters=1, replay_blocked=True`); reviewer exactly-once probe PASS |
| R1–R5 result | R5-A/B/C/D suites green locally; frozen race/crash + route-B positives green — **PASS** |
| historical test-diff audit | "stricter only" confirmed; no security assertion removed (see §5.4) |
| scope exact count | 39 files, `+6049 / −261`, out-of-scope = 0 |
| formal CI run / jobs | `37099376296` success; jobs `111135724970`, `111135775618`, `111135826231`, `111135874085`, `111135979861` all success |
| formal artifacts | 4 artifacts with digests verified as metadata (bytes blocked, `OBS-W20-006`) |
| review PR | see `PR_COMMENT.md` in this directory (number + SHA recorded at publication) |
| exact review SHA | see `PR_COMMENT.md` |
| PR #310 IA comment ID | see `PR_COMMENT.md` |
| **final verdict** | **`ACCEPTANCE_FAIL / blocker=1 / CORRECTIVE_OR_ADJUDICATION_REQUIRED`** |
| blocker count | **1** (`BLK-W20-001`, CRITICAL) |

**Disposition:** return to PM. This verdict does **not** authorize merge, Window 21
integration, RC-REFREEZE-004, Resident A/B/C, persistence, evaluator or release
work. No corrective work was performed in this window; the candidate was not
modified.
