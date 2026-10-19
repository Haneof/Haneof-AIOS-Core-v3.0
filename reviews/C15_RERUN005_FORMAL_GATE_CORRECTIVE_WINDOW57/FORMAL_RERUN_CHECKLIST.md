# Qualified Linux formal rerun — outstanding gates

Operator-only requirements, no authorization to launch Resident. Use final published candidate exactly; no source edits/identity fallback. Keep Cursor 1 sealed. PM must resolve Publisher contract proposal first. Separate development runs cannot be aggregated into a formal PASS.

1. Fresh fetch/main/PR/head/tree and scope check. Unchanged Core tree `16f1487e291b009c55bee402abfd79fdacbae960`, C15 tree `b8a62370e6ffe80730b2ef4c17d625fab50446d4`; recheck current packet/Artifact/manifest pins.
2. Run `runtime_identity.py` with exact approved Runtime ZIP/tar arguments using explicit approved interpreter. All materialized regular files, binary and dependency versions must verify; no replacement build/install.
3. Run `environment_probe.py`: AF_UNIX listener, SO_PEERCRED, authentic child `/proc` start/parent identity and pidfd lifecycle must pass. Socketpair alone is insufficient. Exit 78 is environment pending, not attack success.
4. Run packet materializer in genuinely independent sandbox and pinned verify with independent exact Core/C15 source. Run `test_delivery.py`, capture raw logs. Same-container independent-directory checks pass; actual cross-environment delivery PENDING.
5. Restore all original `test_*.py` files plus `draft_runner.py` from PR #361 commit `67da1125c4902380dafde98a0ccf01c42e590864`, matching frozen hashes. Use disposable worktree's original `reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW53` path (tests derive repo location). Do not run historical builder/readiness or use its tar. Run all 38 unchanged with JUnit/stdout/stderr/exit; record import/TTY FAIL separately. Assertions remain binding pending explicit PM adjudication.
6. Run unchanged Window55 33 via `run_development_tests.py` with approved interpreter, new logs outside frozen evidence. Run Window57 `test_publisher_contract.py`; seven local/synthetic checks do not close live signing isolation.
7. Every actual service attack/positive in migration proposal. Resolve stdout/per-request controlling-TTY discrepancy before claiming historical compatibility. Supplemental mechanical probes require proper Operator/PM scope; retain all original failures.
8. Real Core/C15 USER/due/Summary/delivered: genuine RuntimeSnapshot, durable exact response/proof, current verifier/receipts, remote authoritative CAS, truthful ACK. No semantic mock/fake backend substitute.
9. Five actual Core/C15 faults: before result write; local candidate before remote commit; CAS race; remote commit before local confirmation; restart after remote commit/local-head uncertainty. Actual SIGKILL where required. No duplicate request/invented response/premature local completed or ACK; exact remote authority on recovery.
10. Independent Acceptance is a separate later window; Resident launch needs further PM authorization. Qualified-Linux code defects must be reported as new PM blockers without weakening checks.

Invocation pattern (private Operator directories must already exist):

```bash
APPROVED_PYTHON=/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export APPROVED53_PYTHON="$APPROVED_PYTHON"
export TMPDIR="$OPERATOR_TMP"
export PYTHONPATH="$HARNESS:$SOURCE_REPO/src:$SOURCE_REPO"
"$APPROVED_PYTHON" -B -m pytest reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW53 --basetemp="$OPERATOR_TMP/formal38" --junitxml="$EVIDENCE/formal38.xml" -vv
"$APPROVED_PYTHON" -B reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW55/run_development_tests.py --junit "$EVIDENCE/window55.xml"
```

No skips, relaxed assertions, workflow substitution, merge or real Resident authorized by this checklist.
