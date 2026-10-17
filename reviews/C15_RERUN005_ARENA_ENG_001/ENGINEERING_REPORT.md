# Arena C15-ENG-001 — Signed TTY-less Regression Engineering

**Task:** `C15-ARENA-ENG-001-SIGNED-TTYLESS-REGRESSION-CORRECTIVE-PILOT` (Issue #388)
**Role:** C15 Follow-on Harness Development Engineer (Arena Agent Mode). Not Window66 engineer, not Window69 reviewer, not Window68 Operator, not PM, not a Real Resident, not Merge Owner.

**`DEVELOPMENT_ONLY` / `FORMAL_VALIDATION_NOT_PERFORMED` / `DO_NOT_MERGE`**

Nothing here is formal C15 validation. The public Gateway #385 G4 static PASS is **not** treated as formal C15 validation. No real Resident was started. The Gateway was not re-tested.

---

## 1. Frozen starting candidate — verified, then used as the branch base

Fresh `git fetch`, then verified against the Issue #388 §0 values:

| Item | Expected (PM) | Observed | Match |
| --- | --- | --- | --- |
| Remote `c15-rerun005-signed-ttyless-window66` | `6fb725407569bc719c049587f67fe65e797eb734` | `6fb725407569bc719c049587f67fe65e797eb734` | ✅ |
| Tree | `f9adc59f53f9599bc5ee9d4f3a7448d0b0f0bbe4` | `f9adc59f53f9599bc5ee9d4f3a7448d0b0f0bbe4` | ✅ |
| Sole parent (Window57) | `9d3b19b0e7bf090e5d472d9781b9156f73ea2088` | `9d3b19b0e7bf090e5d472d9781b9156f73ea2088` | ✅ |
| PR #370 state | OPEN / DRAFT / UNMERGED | OPEN / DRAFT / UNMERGED, `MERGEABLE` | ✅ |

The candidate had **not** moved, so no STOP/BLOCKED decision was required.

Engineering started from `6fb7254…`, **not** from `main` (`457e101…`), because the candidate code is not merged to `main`.

```
git fetch --all --prune
git ls-remote origin refs/heads/c15-rerun005-signed-ttyless-window66
git fetch origin c15-rerun005-signed-ttyless-window66
git rev-parse 6fb725407569bc719c049587f67fe65e797eb734^{tree}
git rev-parse 6fb725407569bc719c049587f67fe65e797eb734^
git reset --hard 6fb725407569bc719c049587f67fe65e797eb734
```

### Branch-name deviation (declared)

Issue #388 §1.3 asks for a branch named `arena/c15-eng-001-<unique>`. This Arena
Agent Mode session is **pinned by the platform** to the branch
`arena/4df539f0-haneof-aios-core-v3-0`; the session cannot create, switch to or
push any other branch, and work on another branch would not be associated with
this session. The engineering substance required by §1.3 is met on the pinned
branch: it is a new unique same-repository branch whose history starts at the
exact frozen `6fb7254…`, and PR #370 / PR #367 / PR #371 / `main` / archived
evidence were never pushed to, rebased, reset or edited. Only the literal branch
string differs.

---

## 2. Environment — actual, with the limitations stated plainly

| Fact | Value |
| --- | --- |
| Python | CPython **3.11.2** (`/usr/bin/python3`) |
| Approved Python 3.12.14 | **NOT present, NOT exercised, NOT claimed** |
| pytest / pydantic | 8.4.2 / 2.14.1 in a venv at `/tmp/c15venv` (outside the repo) |
| OpenSSL | 3.0.20, Ed25519 supported (`genpkey -algorithm ed25519` works) |
| Platform | Linux 6.1.158+ x86_64, glibc 2.36 |
| Identity | `uid=1001(user) gid=1001(user)`, groups include `sudo` (**never used**) |
| Controlling TTY | **absent** — `isatty(0/1/2)` all false; `os.open('/dev/tty')` → `ENXIO` |
| `AF_UNIX` / `SO_PEERCRED` / `pidfd_open` / `O_NOFOLLOW` | all present |
| `/var/lib/aios-window65/trust` | **absent** |
| `/run/aios-w66-responses` | **absent** |
| `chown 999:985` | **denied** (`Operation not permitted`) |
| git | 2.39.5 |

Dependency versions were aligned to the project's own declared constraints
(`pyproject.toml`: `requires-python >=3.12`, `pytest>=8,<9`, `pydantic>=2.10,<3`).
An initial pytest 9.1.1 install violated `pytest>=8,<9` and was replaced with 8.4.2.

The Window55 runner's own record independently corroborates the runtime gap:
`approved_runtime_status: NOT_PRESENT`, `approved_runtime_used: false`,
`formal_runtime_validation: PENDING_APPROVED_RUNTIME_AND_PM_AUTHORIZATION`.

### What this makes impossible (honest limits)

1. **No real UID999 Runner / UID996 Resident isolation.** `chown` to 999:985 is
   denied and privilege escalation was not attempted. `SignedResponseAuthority`
   peer checks (`peer[1:] == (996, 983)`) and `os.getuid() == 999` are therefore
   driven with literal synthetic fixtures / a mocked `os.getuid`, never with real
   OS principals.
2. **No real response endpoint.** `open_endpoint()` needs a root-owned
   `/run/aios-w66-responses` (0755) containing a `999:985` `02750` directory.
   Neither exists and neither can be created here. The test asserts it fails
   closed and leaves no listening socket.
3. **No real Operator trust root.** `load_grant` is exercised against a synthetic
   in-memory trust root with throwaway Ed25519 keys. The pinned
   `ISSUER_SHA256`/`RESIDENT_SHA256` are asserted unchanged; no real key was read,
   exported or substituted.
4. **The original38 suite cannot be executed here.** `ORIGINAL38_SOURCE_SHA256.json`
   pins `draft_runner.py`, `test_artifact_delivery.py`, `test_crash_recovery.py`,
   `test_current_trusted_adapter.py`, `test_identity_delivery.py`,
   `test_mechanical_candidate.py`, and Window66's own log shows them living under
   `reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW53/` on the Operator Codespace.
   **That directory does not exist in this repository.** The original38 tests were
   left completely unchanged and were not run; their 31 PASS / 7 FAIL and the seven
   failure names remain historical records, not Arena execution evidence.
5. **No full remote CAS claim.** The remote-authority tests use a real disposable
   *local bare Git* repository — portable and unprivileged, the same technique
   Window66 recorded. That is mechanical local Git authority only, **not**
   production remote durability, a hosted platform, or the real C15 remote CAS
   under Operator UID isolation.

---

## 3. New executable test code

New directory, as authorized: `reviews/C15_RERUN005_ARENA_ENG_001/tests/`

| Module | Methods | Covers |
| --- | --- | --- |
| `test_signed_response_binding.py` | 26 | The new signed no-TTY authorization contract |
| `test_test_only_grant_fail_closed.py` | 45 | TEST_ONLY enrollment gate + crypto primitives |
| `test_rejected_remote_authority_no_marker.py` | 15 | Rejected remote authority ⇒ no completion/ACK |
| `test_ttyless_disclosure_refusal.py` | 15 | Genuine TTY-less refusal; no stdout-token fallback |
| `test_enrollment_scope_gate.py` | 7 | **RED** defect-acceptance for the finding in §5 |
| **Total** | **108** | |

Plus `tests/synthetic_fixtures.py` (shared fixtures, deliberately not `test_*.py`
so discovery never collects it) and `run_engineering_tests.py`.

### These drive REAL production code, not mocks

Real and unmodified: `ExchangeBridge` (durable request artifact + ledger +
durable response publication on a temp dir), `RunnerRegistrationAuthority` and
`validate_registration` (real `/proc` start-time identity for this process acting
as Runner), `SignedResponseAuthority.register` and `.dispatch`, `load_grant`,
`trusted_bytes`, `key_fingerprint`, `verify_signature` (**real `openssl` Ed25519
verification**), `registration_ipc.receive_message` (real bounded single-newline
JSON framer), `completion`, `remote_completion`, and
`tools.c15_persistence.remote_backend` against a real bare Git remote.

Synthetic only where a privileged Operator host facility is required: the
enrollment grant, the Resident kernel peer tuple, the AF_UNIX transport, and
throwaway Ed25519 keypairs created per test in a temp directory.
`SignedResponseAuthority.__init__` is entered via `object.__new__` in the binding
suite because it hard-requires `os.getuid() == 999`; this exercises the
authorization **logic** without claiming any real UID999 execution.

Every negative case asserts a five-part "nothing was credited" invariant:
no `publish` call, no durable response artifact, no `response_published` ledger
record, no completion/ACK marker, and no `resident_authorization_sha256` digest.
Each rejection family has a **positive control** proving the same harness *can*
succeed, so the negatives are not vacuous.

### PM priority cases → where they are covered

* **"Wrong request/operation/context or changed raw-response hash can never
  satisfy a matching signed-response request; no Publisher/Core-proof or
  completion marker may be credited."** → `test_signed_response_binding.py`:
  `test_every_issued_envelope_binding_is_individually_enforced` (22 bindings, each
  mutated individually and re-signed with the legitimate key),
  `test_extra_or_removed_envelope_keys_are_rejected`,
  `test_raw_bytes_that_disagree_with_the_signed_response_hash_are_rejected`,
  `test_response_hash_claimed_without_a_matching_signature_is_rejected`,
  `test_signature_from_an_unapproved_key_is_refused`,
  `test_changed_durable_registration_is_refused`,
  `test_changed_enrollment_during_an_operation_is_refused`.
* **"Replayed/double-consumed or stale Publisher-epoch request does not authorize
  a second semantic response."** →
  `test_replay_of_an_identical_signed_response_authorizes_nothing_second`,
  `test_replay_with_different_bytes_is_also_refused_after_consumption`,
  `test_a_restarted_publisher_epoch_cannot_honor_a_previous_round`,
  `test_publish_failure_after_verification_never_restores_authority`,
  `test_pending_lists_only_unconsumed_challenges_with_the_live_epoch`.
* **"Missing/wrong-purpose/expired TEST_ONLY grant fails closed before any
  response publication."** → `test_test_only_grant_fail_closed.py`: 24 rejection
  cases through the real `load_grant` chain (missing file, wrong purpose
  including `mechanical.ping`, `test_only` false, wrong domain/version, expired,
  not-yet-valid, >3600 s lifetime, non-integer time, wrong Resident id/uid/key,
  wrong issuer id, unpinned root, embedded key ≠ pinned trust copy, bad
  enrollment-id/instance-id shapes, empty and >16 `operation_ids`, bad and empty
  `request_kinds`, revoked, revocation-epoch mismatch, noncanonical bytes,
  non-issuer signature, signature over different bytes) **plus**
  `ConstructorGateTests`, which proves the refusal happens at construction —
  before any endpoint, challenge table or publication can exist.
  No real Window68 grant was used anywhere.
* **"A rejected remote authority cannot produce a local completed/ACK marker."**
  → `test_rejected_remote_authority_no_marker.py`, including a **genuine**
  rejection produced by the unmodified
  `remote_backend.verify_local_remote_authority` when a real competing writer
  advances the ref behind the cache's back
  (`test_genuine_remote_head_divergence_is_refused_by_the_real_authority`), and
  `test_rejected_authority_is_consulted_before_any_local_confirmation`, which
  spies on `finalize_local` — the only writer of `state == 'completed'` — and
  proves it is never reached.

---

## 4. Commands and actual results

All runs used `PYTHONDONTWRITEBYTECODE=1` and `python -B`. That matters: running
the Window55 runner directly with `python3` instead of the blessed
`run_development_tests.sh` (which uses `python3 -B`) writes `__pycache__` into the
identity-pinned harness tree and makes `launch.scan_identity` fail with
`BLOCKED / UNAPPROVED_OR_REPLACED_DIRECTORY: harness/__pycache__`. This was
reproduced, and the polluted tree was removed and re-verified against
`f9adc59f53f9599bc5ee9d4f3a7448d0b0f0bbe4`. `run_engineering_tests.py` sets
`sys.dont_write_bytecode` for that reason, and writes evidence only under
`reviews/C15_RERUN005_ARENA_ENG_001/`.

### New Arena suite

```
cd reviews/C15_RERUN005_ARENA_ENG_001
PYTHONDONTWRITEBYTECODE=1 /tmp/c15venv/bin/python -B run_engineering_tests.py --record
```

| Run | Methods | Outcomes | Fail | Err | Exit | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| `RED-before-patch` | 108 | 112 | **8** | 0 | **1** | 5.644 |
| `GREEN-after-patch` | 108 | 108 | 0 | 0 | **0** | 5.606 |
| `FINAL-full-suite` (delivered head, patch reverted) | 108 | 112 | **8** | 0 | **1** | 6.887 |
| `FINAL-conformance` (4 modules) | 101 | 101 | 0 | 0 | **0** | 5.820 |
| `FINAL-defect-acceptance-RED` (1 module) | 7 | 11 | **8** | 0 | **1** | 0.733 |

"Outcomes" exceeds "methods" because `subTest` cases are recorded individually.

**The delivered branch head is intentionally 100 PASS / 8 FAIL.** The 8 failures
are all in `test_enrollment_scope_gate.py` and are the RED receipt for the
confirmed defect in §5. They are reported, not skipped, not xfailed, not marked
green — exactly as Issue #388 §3 requires ("A test failure must be reported, not
silently marked green"; "No skipping/xfail"). The other 100 pass against the
unmodified frozen candidate.

### Preserved existing suites (nonprivileged, re-run at the delivered head)

```
sh reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW55/run_development_tests.sh
PYTHONDONTWRITEBYTECODE=1 /tmp/c15venv/bin/python -B -m pytest -p no:cacheprovider \
  --tb=no -q --junitxml=… reviews/C15_RERUN005_FORMAL_GATE_CORRECTIVE_WINDOW57/
```

| Suite | Frozen candidate baseline | With candidate patch |
| --- | --- | --- |
| Window55 | 33 tests, **OK**, exit 0, 1.298 s | 33 tests, 5 failures + 3 errors, exit 1 |
| Window57 | 29 tests, 5 failures, exit 1, 2.586 s | 29 tests, **6** failures, exit 1 |
| original38 | **not executable here** (sources absent) | not executable here |

Window55 = 33/33 PASS at the delivered head, matching the recorded historical
`WINDOW55: 33 PASS`.

The 5 Window57 failures are **environment-bound, not candidate defects**. All are
in `test_delivery.py` and all fail because the frozen delivery packet records a
host-absolute materialization command:
`/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python`,
which does not exist in this sandbox, so the child shell exits **127**
(`assert [127, 127] == [0, 1]`). Failing tests:
`test_independent_full_source_materialization_and_pinned_verify`,
`test_transport_tampering_fails_before_destination[append|truncate|flip]`,
`test_parallel_materialization_has_one_winner`.
`test_publisher_contract.py` — the Publisher import-inertness contract, which is
what the seventh original38 failure `test_signer_not_importable_in_recovery_caller`
is about — **passes in full here**, including
`test_import_exposes_no_existing_private_key_or_sign_closure` and
`test_private_key_and_sign_definition_are_local_to_main`. That is real, if
partial, isolation evidence; it is **not** the actual isolation equivalence the PM
requires, which needs the approved runtime and the real recovery caller.

Evidence for every row above is committed under `development-test-runs/`.

---

## 5. Finding, RED/GREEN receipt, and why the patch was reverted

### Finding

`load_grant` is the single "this TEST_ONLY enrollment is approved" gate. It
validates the domain, version, purpose, `test_only` flag, issuer identity,
Resident identity/UID/key, the embedded public key against the pinned trust copy,
the whole time window, the enrollment-id shape, the instance-id shape, the bounded
exact `operation_ids`, the bounded `request_kinds`, and the revocation record.

It does **not** validate `run_id` or `session_id` — yet two production call sites
treat them as authoritative scope bindings:

* `response_authorization.SignedResponseAuthority.register`:
  `require(identity['run_id'] == grant['run_id'] and identity['session_id'] == grant['session_id'] …)`
* `safe_runner` pre-launch:
  `require(grant['run_id']==run_id and grant['session_id']==session_id and opid in grant['operation_ids'], …)`

Reproduced: an enrollment omitting those fields **passes the approval gate**
(`load_grant` returns it; 18 keys instead of 20) and is only stopped later by a
bare `KeyError: 'run_id'` raised inside the Publisher dispatch loop — after the
Runner's durable request registration has already succeeded. The request can then
never be answered in signed mode, and the failure surfaces as an uncontrolled
`KeyError` two layers below the gate rather than as an enrollment refusal.

**Severity: fail-closed hardening, not an authorization bypass.** No test
demonstrates a response being published that should have been refused; the
security property holds both before and after the patch. What changes is *where*
the refusal happens and in what vocabulary.

### Candidate patch (2 lines, confined to the authorized path)

`CANDIDATE_FIX_enrollment_scope_gate.patch`, in
`harness/r005/response_authorization.py::load_grant`, immediately after the
`request_kinds` scope check and using the file's existing `type(...) is` style:

```python
    require(all(type(grant.get(k)) is str and grant[k] for k in ('run_id','session_id')),
            'enrollment run/session scope required')
```

The real Operator-issued grants recorded in
`reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66/reproduction/issue-finalcandidate.py`
always carry non-blank string `run_id`/`session_id`, so this cannot reject any
enrollment that could ever have worked. No frozen repo test pins the old
acceptance behaviour.

### RED → GREEN receipt

* **RED** (`development-test-runs/RED-before-patch/`): 8 failures, exit 1 —
  `test_gate_rejects_a_grant_that_omits_the_run_and_session_scope`,
  `test_gate_rejects_a_blank_run_or_session_scope[run_id|session_id]`,
  `test_gate_rejects_a_non_string_run_or_session_scope[int|NoneType|list|dict]`,
  `test_refusal_is_a_clean_gate_error_not_a_late_key_error`.
* **GREEN** (`development-test-runs/GREEN-after-patch/`): 108/108, exit 0.

### Why the patch was nevertheless REVERTED — BLOCKED

Applying it regresses the **preserved** Window55/Window57 evidence suites
(`development-test-runs/BLOCKER-post-patch-identity-regression/`): Window55 goes
33/33 OK → 5 failures + 3 errors; Window57 gains
`test_exact_identity_and_closed_members`.

Root cause: `harness/r005/response_authorization.py` is **identity-pinned twice**.

* `harness/IDENTITY.json` → `harness_files["r005/response_authorization.py"] =
  abc30a28661f22390a9f4a34df5d9764fe27e155f7c285c9e2008c16448defa6`, plus
  `accepted_baseline = 703a8967878d8eaee70a8a8fce9df068204f5f76`.
* `RESIDENT_SAFE_LAUNCH_PACKET.json` → the same `abc30a28…` member digest, bound
  to the frozen `artifacts/resident-harness.tar.gz` delivery packet.

The patched file hashes to
`5ec8cc012fadfdc98d59e0566fb513bc9a6a234c48dafaba4722601485f69a28`, breaking both
pins. Regenerating them would create **new official evidence and a new candidate
identity**, which Issue #388 forbids ("do not … edit … archived evidence"; "Do not
change … official evidence") and which would require a fresh PM freeze before any
Window69 formal validation.

So the authorization to patch `harness/**` and the prohibition on touching frozen
identity evidence are mutually exclusive for this file. Per Issue #388 §2 — "If only
test-gap/contract mismatch is identified, deliver **tests-only code PR** with
honest limits and candidate-fix follow-up instead of speculative code modification"
— the patch was reverted and is delivered as a follow-up.

**Delivered head: every protected tree is byte-identical to `6fb7254…`.**
Verified with `git diff --stat 6fb7254… -- reviews/internal_habitation src tools`
(empty) and by re-hashing the file to the pinned `abc30a28…`.

**Decision needed from PM:** either (a) accept the tests-only delivery and schedule
the 2-line fix together with an authorized `IDENTITY.json` + delivery-packet
regeneration and a new freeze, or (b) authorize that regeneration now.

---

## 6. Scope compliance

Unchanged and byte-identical to the frozen candidate: `src/aios_core/**`,
`tools/c15_persistence/**`, `harness/**` (including
`response_authorization.py`, `publisher_service.py`, `safe_runner.py`),
`harness/IDENTITY.json`, `RESIDENT_SAFE_LAUNCH_PACKET.json`, all Window55/57/66
archived evidence, and the original38 assertions (which are not even present in
this repository). PR #370 / #367 / #371 / `main` were never pushed to, rebased,
reset or edited.

Added files live **only** under `reviews/C15_RERUN005_ARENA_ENG_001/`. The
Window55 runner writes a new timestamped directory into its own archived
`development-test-runs/` on every invocation; the directory this task generated
was deleted so archived Window55 evidence stays pristine, and the same output was
re-homed under this task's own directory.

No skipping, no xfail, no fake stdout-token fallback, no environment bypass, no
broad permission grant, no `sudo`, no privilege escalation. No secret or
credential is included: all keys are throwaway Ed25519 pairs generated per test in
temp directories, and the pinned issuer/Resident fingerprints appear only as the
existing public constants already in the frozen source.

**`git diff --check`:** clean on all code —
`git diff --cached --check -- '*.py' '*.md' '*.patch'` reports nothing. It does
report trailing whitespace in exactly six files, all of them **verbatim captured
tool output** under `development-test-runs/`:

```
BASELINE-window57/test-results.xml
BLOCKER-post-patch-identity-regression/window55-stderr.txt
BLOCKER-post-patch-identity-regression/window57-results.xml
FINAL-defect-acceptance-RED/stderr.txt
FINAL-full-suite/stderr.txt
RED-before-patch/stderr.txt
```

The whitespace is unittest's own `... ` separator before a result token and
pytest's XML indentation. Those bytes are evidence and were deliberately **not**
normalised, following the Window66 precedent recorded in its README: "Raw logs
retain their original whitespace; source-code diff checks exclude these immutable
log bytes."

---

## 7. Unresolved / out of scope

1. **The 8 RED tests remain red at the delivered head** by design (§5). Fixing
   them requires a PM decision on frozen-identity regeneration.
2. **`open_endpoint()` is not failure-atomic** — *inspection only, not reproduced.*
   If the final ownership assertion (`st_uid == 999 and st_gid == 985`) fails after
   `bind()`, the bound socket inode and the listening descriptor leak: `open_endpoint()`
   is called **outside** `publisher_service.main()`'s `try/finally`, so `signed.close()`
   never runs. `close()` itself would also raise `AttributeError` on an authority
   whose endpoint was never opened (`socket_path` unset, `server is None` guard only).
   This matches Window66's own note that retirement diagnostics "required socket
   inode deletion" and that "a separate followup verifies actual endpoint
   retirement". Reproducing it needs a root-owned `/run/aios-w66-responses` and a
   `999:985` `02750` directory, which this sandbox cannot create (`chown` denied),
   so **no patch was attempted** — asserting it via source structure alone would
   have been speculative.
3. **Seventh original38 failure** (`test_signer_not_importable_in_recovery_caller`):
   actual isolation equivalence still **not** established. `test_publisher_contract.py`
   passing here is supporting evidence only; the real test needs the approved
   3.12.14 runtime and the real recovery caller.
4. **Six historical stdout/TTY-transport failures**: not re-examined; their crash,
   timeout and Core/C15 remote-persistence semantics remain binding and were not
   re-litigated.
5. **original38 was never executed in this session** (sources absent from the repo).
6. **Window69 independent formal validation remains NOT PERFORMED** and must stay
   on the frozen PR #370 candidate `6fb7254…` unless PM expressly freezes a new
   formal target. This engineering head is **not** a formal target.
7. **No cross-platform fault campaign**; Linux-only primitives (`SO_PEERCRED`,
   `pidfd_open`, `O_NOFOLLOW`) were assumed present and verified present.

---

## 8. Reproduce

```sh
git fetch origin c15-rerun005-signed-ttyless-window66
git checkout 6fb725407569bc719c049587f67fe65e797eb734
python3 -m venv /tmp/c15venv
/tmp/c15venv/bin/pip install 'pytest>=8,<9' 'pydantic>=2.10,<3'
cd reviews/C15_RERUN005_ARENA_ENG_001

# full suite (expect 100 PASS / 8 RED, exit 1)
PYTHONDONTWRITEBYTECODE=1 /tmp/c15venv/bin/python -B run_engineering_tests.py --record

# conformance only (expect 101/101, exit 0)
PYTHONDONTWRITEBYTECODE=1 /tmp/c15venv/bin/python -B run_engineering_tests.py --record \
  test_signed_response_binding test_test_only_grant_fail_closed \
  test_rejected_remote_authority_no_marker test_ttyless_disclosure_refusal

# defect acceptance only (expect 8 RED, exit 1)
PYTHONDONTWRITEBYTECODE=1 /tmp/c15venv/bin/python -B run_engineering_tests.py --record \
  test_enrollment_scope_gate

# preserved suites
cd ../../.. && sh reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW55/run_development_tests.sh
PYTHONDONTWRITEBYTECODE=1 /tmp/c15venv/bin/python -B -m pytest -p no:cacheprovider \
  reviews/C15_RERUN005_FORMAL_GATE_CORRECTIVE_WINDOW57/

# apply the candidate fix and observe GREEN, then the identity blocker
git apply reviews/C15_RERUN005_ARENA_ENG_001/CANDIDATE_FIX_enrollment_scope_gate.patch
```

**`ARENA_C15_ENGINEERING_PR` — real Python test code delivered and executed;
1 confirmed reproducible defect with RED/GREEN receipt; the fix is BLOCKED by
frozen identity-pinned evidence and is delivered as a candidate patch.
`DEVELOPMENT_ONLY` / `FORMAL_VALIDATION_NOT_PERFORMED` / `DO_NOT_MERGE`.**
