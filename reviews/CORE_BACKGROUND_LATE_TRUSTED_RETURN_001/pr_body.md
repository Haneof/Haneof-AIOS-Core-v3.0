# CORE-BACKGROUND-LATE-TRUSTED-RETURN-001

**WINDOW 13 · Core Runtime Recovery Engineer · MERGE_POLICY = DO_NOT_MERGE**

Closes the new Core failure class frozen by the WINDOW 12 adjudication
(`governance/C15_RCC_RES_B_ACCEPT_003_FAILURE_ADJUDICATION_2026-09-30.md` §11, C1–C5).

> **Status: engineering candidate for fresh Independent Acceptance.**
> This PR is **not** merged by this window and must not be merged by it.
> `REVIEW_READY` / `READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE` / `DO_NOT_MERGE`.
> No `ACCEPTED` and no `PASS` is claimed anywhere in this PR.

- Baseline `main`: `25591825d88e98f30dfd3de1c7e7cbc6e53267dd`
- Branch: `arena/01a0f07b-haneof-aios-core-v3-0`
- Candidate: `dab7af82cd009dbc8ab8838c839e16a2b2a803e1`
- Parent: `30a38c48418b220197213cf412aa6ea1fd977a33`
- Tree: `bbe393c617a0da887391a1dade47272d3dd13947`

> The candidate pin above is this branch's head. The file cannot embed the SHA of
> the commit that contains it, so the authoritative head is the one shown on the
> PR itself; both are asserted equal in the CI comment below.

---

## 1. The defect

### Class A — a trusted external return arrives after the Core process died

`admit()` converts `dispatching → in_doubt` and raises **before** the model handler,
so `_capture_trusted_response_return` — the only receipt minter — is unreachable for
that round. `stage_exact_response` needs a receipt row that does not exist,
`reconcile_response` is permanently disabled, and `recover_trusted_handoff` promotes
only Core-owned callback bytes. An externally produced, contemporaneous, genuine
return was **unattachable even with perfect external provenance**.

### Class B — a post-dispatch `not_submitted` false state was writable

`reconcile_not_submitted(...)` was callable for `dispatching` / `in_doubt` attempts
and its only guard was *absence of a trusted-return receipt*. That made
«I have no return evidence» into «therefore the request was never submitted» — the
mechanical enabler of `IA-B-R003-BLK-002`.

---

## 2. Design — trust root

A **pre-issued, single-use, per-attempt return capability**.

```text
Core at dispatch                         External responder
─────────────────                        ──────────────────
mark_dispatching() commits attempt state + binding
_issue_external_return_capability()  ───►  nonce persisted (private)
        └─ handed ONCE to the registered ExternalReturnObserver
             ... Core process dies ...
             ◄── observer receives the real external response AFTER the death
                  capability.prove_external_return(directive)
                    = HMAC-SHA256(nonce, canonical(binding ‖ response))
                  └─ proof + exact bytes → recovery caller
Core: recompute HMAC under the stored nonce, compare_digest,
      compare every binding field against the DURABLE pre-dispatch row,
      then commit receipt + exact-bytes handoff atomically
```

### Why it is not a signing oracle

| attack route | why it fails |
|---|---|
| correct bytes + invented proof | the proof is an HMAC under a nonce the caller never sees; Core recomputes and `compare_digest`s it |
| correct bytes + self-computed binding fields | all binding fields are compared against the **durable pre-dispatch row**, and are inside the MAC |
| ask Core for the capability | the issuer is **private** (`_issue_external_return_capability`), mirroring the accepted `_capture_trusted_response_return`; asserted by `test_a1_*` |
| ask Core to mint a receipt for bytes | no such public API exists; a receipt is minted only after a capability proof verifies |
| leaked capability on another attempt/round/subject/work/request | all pinned inside the MAC message and compared against the durable binding |
| leaked capability used twice | single-use: `consumed_at` is set in the same transaction as the receipt; a second presentation is only deterministic exact recovery of identical bytes |
| replay of an old proof | cannot create a second effect; downstream stays the accepted R5 exactly-once path |

Residual, stated explicitly: the registered observer can mint **one** return for
**one** attempt. That is inherent to any design where an external party proves its
own return, it is the same trust domain as the provider call, and it is bounded to
one attempt / one round / one originating request / one response / once.

`background_model_authenticity_authority` (the receipt HMAC key) is untouched: still
store-private, never returned by an API, never in a snapshot, evidence or metering,
and used only after a capability proof verifies.

### `not_submitted` — frozen new semantics

> `not_submitted` ⇔ Core holds mechanical, trustworthy evidence that this attempt
> **never crossed** the semantic/provider dispatch boundary.

Legal only from a pre-dispatch Core-owned state with no originating-request binding.
The binding row — written in the same transaction as `admitted → dispatching`,
before the handler runs, never caller-supplied — is the mechanical proof of
crossing, so the post-dispatch transition is now **impossible**. Absence of a
receipt, a timeout, a caller/operator statement and "recovery needs to continue" are
all refused.

The in-process typed `ModelDispatchNotSubmitted` contract is **retained** as the
other legal route: it is a Core-internal signal raised synchronously at the dispatch
site while the process is alive, frozen by existing FIX-002/CG003 tests. Removing it
would break accepted invariants the adjudication told us to preserve.

---

## 3. Evidence

All in `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001/`.

| file | content |
|---|---|
| `design_note.md` | trust-boundary note, the nine required answers, exact binding, preserved invariants, scope discipline |
| `baseline_red_manifest.md` | RED classification, probe hashes, full harness revision history |
| `baseline_red_raw.txt` | **authoritative** reproducible RED |
| `baseline_red_preimplementation_capture.txt` | the original freeze-time capture, taken before any production line existed |
| `green_raw_output.txt` | raw GREEN for all three suites |
| `matrices.md` | late-return, non-submission, authenticity/adversarial and regression matrices |
| `changed_path_manifest.txt` | exact changed paths |

### Baseline RED (reproducible)

```text
git worktree add --detach /tmp/baseline_wt origin/main   # -> 25591825…
# only the 4 new probe files copied in; src/**, tools/**, existing tests pristine
56 failed, 5 passed, 0 errors
```

- **7 `PRODUCT_RED`** — *"DID NOT RAISE BackgroundModelResponseConflict"*, using only
  already-accepted public API: Core **succeeds** in writing a durable false
  `not_submitted` after the dispatch boundary. This is the class-B enabler.
- **49 `PRODUCT_RED / ABSENT_CAPABILITY`** — no `external_return_observer`, no
  `attach_late_trusted_return`, no `aios_core.runtime.late_return`, real-SIGKILL
  probe dies before dispatch.

### Green

| suite | count | result |
|---|---|---|
| late trusted return + not_submitted + adversarial | 61 | **61 PASS** |
| accepted trusted-return / background-response / gap-fix / runtime regression | 249 | **249 PASS** |
| **full Core suite (full history)** | **1059** | **1059 PASS — 0 fail, 0 error, 0 skip** |

Baseline `main` = 997 PASS, so `+61` new probes and `+1` from splitting one accepted
test, with **no previously passing test lost**.

The full-Core run was first recorded as `1058 passed, 1 failed` on a
full-history checkout; the lone failure was the historical scope tripwire, since
resolved as described in section 7. The current full-history result is
**1059 passed, 0 failed, 0 errors, 0 skipped**, and the same suite on CPython
3.12.14 in formal CI is 1059/0/0/0. No test is now passing by relying on a
missing `main` ref.

### Formal gate

`.github/workflows/core-background-late-trusted-return-001.yml`, pinned to
**CPython 3.12.14** with `pydantic==2.13.5`, `pytest==8.4.2`, publishing the exact
SQLite / OpenSSL versions and exact JUnit counts. The local numbers above are from a
CPython 3.11.2 development runtime and are **not** presented as the formal gate;
GitHub CI at 3.12.14 is.

**CI results on the final candidate** — all 17 repository workflows report
`success` and all 33 PR checks pass, on the exact head. Formal CPython 3.12.14
environment and exact JUnit counts:

Python **3.12.14** / Pydantic **2.13.5** / pytest **8.4.2** /
SQLite **3.45.1** / OpenSSL **OpenSSL 3.0.13 30 Jan 2024**

| suite | tests | fail | err | skip | time (s) |
|---|---|---|---|---|---|
| full Core regression | 1059 | 0 | 0 | 0 | 283.370 |
| accepted trusted-return regression | 249 | 0 | 0 | 0 | 34.125 |
| resident-visible behavioural + historical scope gate | 1 | 0 | 0 | 0 | 0.701 |
| late trusted return / not_submitted / adversarial | 61 | 0 | 0 | 0 | 10.636 |

Formal gate: workflow `core-background-late-trusted-return-001`, run
**`36678925987`**, job `formal-core-gate` — **success**. The steps
`Verify required refs resolve (no shallow-clone false green)` and
`Resident-visible behavioural and historical scope gate` both executed and
passed; only `Annotate failure identities` is skipped, which is its intended
`if: failure()` behaviour. Full run list in
`reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001/formal_ci_results.md`.

**The earlier evidence gap is now closed.** A previous revision of this body had
to record the native SQLite/OpenSSL values *by reference* because the run log and
artifact hosts were unreachable from the sandbox. They are now read verbatim from
the check-run annotations API for check run `109769899901` and transcribed above.

### Historical R1–R5 replay families re-proved

`propose_goal`, `form_event`, `revise_claim`,
`propose_entity` / `propose_dimension` / `propose_cognitive_policy`, and R5-A/B/C/D —
all PASS, untouched.

---

## 4. Two accepted tests updated (adjudication C2 requires "with tests")

| test | preserved | added |
|---|---|---|
| `tests/runtime/test_background_model_attempt.py::test_background_model_attempt_reconciliation_keeps_same_identity_and_non_world_revision` | same attempt identity across reconcile → re-admit → dispatch → response → meter; World revision untouched; restart durability; full lifecycle to `metered` | post-dispatch `in_doubt` refused, stays `in_doubt`, `reconciliation_evidence IS NULL` |
| `tests/runtime/test_turn_execution_recovery.py::test_cg003_reconciled_not_submitted_attempt_can_be_authorized_after_restart` → `..._not_submitted_...` | a `not_submitted` turn can still be authorized after a restart and re-run to completion | reached via the still-legal typed in-process contract; new `test_cg003_post_dispatch_reconciliation_is_refused_after_restart` asserts the retired shape fails closed, the turn stays `in_doubt`, and `authorize_turn_retry` / `run_turn` both refuse |

No expected outcome was weakened to make a test pass.

---

## 5. Scope discipline

Changed: `src/aios_core/runtime/{late_return.py (new), background_attempt.py,
turn_runtime.py, __init__.py}`, the four new probe files, the two updated accepted
tests, one new CI workflow, one `.gitignore` for `__pycache__`, and the evidence
directory.

**Not touched:** `tools/c15_preflight/**`, `tools/c15_persistence/**`,
`evidence/w08/**`, PR #302, the Window 10 review `bc403bc…`, the transport commit
`0978e735…`, the persistence ref, generations 1..48, any run evidence. No Resident
was run and no cursor was revealed. `IA-B-R003-BLK-001` (`UNPROVEN_RESIDENT_AUTHORSHIP_REQ0039`)
is **not** addressed here — Window 12 assigned it to the C15 operator / exchange
provenance layer, and it remains with the blocked
`C15-RCC-RES-B-OPERATOR-PROVENANCE-CORRECTIVE-001`.

---

## 6. What a reviewer should attack first

1. `test_a1_*` — is capability issuance genuinely unreachable from the public surface?
2. `test_a2_*` — can a caller who knows every binding field and computes the payload
   digest still not mint a proof?
3. `test_ltr_r9_*` / `test_a3_..._late_proof_for_completed_stronger_terminal_receipt`
   — is a leaked capability bounded to one attach, and can a completed round ever
   re-enter the model path?
4. `test_ltr_r4_*` — cross-attempt / cross-round / cross-subject / cross-work /
   binding-tamper transplant.
5. `reconcile_not_submitted` — is any post-dispatch `not_submitted` write still
   reachable by any path, including raw SQL, `adopt_legacy_in_doubt`, or
   `mark_failure`?
6. Whether the local 3.11 development runtime was ever presented as the formal gate
   (it was not) and whether the 3.12.14 CI run is green.

---

## 7. C15 resident-surface tripwire — RESOLVED, validation split in place

**Status: `CI_VALIDATION_GAP` CLOSED.** This section supersedes the earlier
disclosure, which reported the tripwire but left the combined verdict in place.

### The preserved RED

The real failing result is retained, not deleted and not relabelled as green:
**`HISTORICAL_SCOPE_TRIPWIRE_RED`** — `1058 passed, 1 failed`, the single failure
being `tests/c15_persistence/test_resident_surface.py`. Recorded in
`reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001/historical_scope_tripwire_red.md`.
It is explicitly **not** a `RESIDENT_BEHAVIOR_RED`: all 12 behavioural comparisons
measured `True`, and the failure came from a scope guard that a legitimately
authorised Core change trips by construction.

### The validation split

`tests/c15_persistence/test_resident_surface.py` is corrected **test-only**. The
checker tool and the committed historical evidence are untouched. The two
constraints are now adjudicated separately:

1. **Resident-visible behaviour (binding).** All 12 comparisons asserted
   exhaustively against a named list, so none can be dropped silently.
2. **Frozen Resident review trees.** `c15-rcc/v1` and
   `c14-resident/v2/release` must stay clean against the current base,
   re-derived independently of the checker's own report.
3. **Historical Persistence Corrective-003 scope.** The `src/aios_core`
   zero-diff is re-bound to the range it was actually written for:
   `016a2f7db5ed01b41fc614701079c507d2c2c02e -> 19476641be95e666068e6299f42df9a411f4c0ba`,
   which is empty, while that same range changed 56 files / 12,433 insertions
   elsewhere — so the invariant is real and non-vacuous.
4. **No false green.** A shallow checkout now reports **skipped**, never passed.
   A full-history checkout with a missing ref is still a hard failure.

### The shallow-clone blind spot, closed in CI

`.github/workflows/core-background-late-trusted-return-001.yml` now uses
`fetch-depth: 0` and adds a **Verify required refs resolve (no shallow-clone false
green)** step that fails the build if the repository is shallow, and prints
`rev-parse`/`cat-file -e` results for the base ref and both historical pins. A new
**Resident-visible behavioural and historical scope gate** step runs the split
gate on 3.12.14. Both steps executed and passed on the final head.

Note the first version of the split made a shallow checkout a *hard failure*,
which correctly refused to lie but also redded the five other repository
workflows that still use the default `fetch-depth: 1`. That was resolved by the
skip-not-pass rule above, so unrelated gates stay honest rather than being
quietly waived.

### The gate is not a rubber stamp

| injected fault | result |
|---|---|
| `assistant_output` comparison forced False | **FAILED** — behavioural comparison is live |
| historical range pointed at a Core-touching commit | **FAILED** — scope invariant is live |
| frozen review tree dirtied in a commit | **FAILED** — review-tree constraint is live |
| shallow clone | **skipped**, not passed |
| full history, no local `main` branch | **passed** — PR-checkout shape handled |

### Scope discipline held

`tools/c15_persistence/**` and
`reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003/evidence/resident-surface-no-change.json`
were **not** modified. No persistence product or harness contract was changed to
make a test green. The late-return trust design, the public API, and the C15
operator surface are untouched by this corrective.
