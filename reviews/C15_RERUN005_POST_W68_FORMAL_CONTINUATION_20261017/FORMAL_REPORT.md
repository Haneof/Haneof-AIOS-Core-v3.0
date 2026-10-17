# C15 formal validation continuation after Window 68

FORMAL_VALIDATION = FAIL
CODE_FIX_REQUIRED = UNKNOWN
DO_NOT_MERGE = YES

This is actual continuation of Window 67 under PM issue383 comment6231681920, not a new numbered window. Seven binding original regressions still fail; required live signed-path gates are blocked. This result neither replaces the historical Window67 report nor claims a full live signed rerun.

## Authority and frozen target

PM order: https://github.com/Haneof/Haneof-AIOS-Core-v3.0/issues/383#issuecomment-6231681920
Target: PR370, commit6fb725407569bc719c049587f67fe65e797eb734, treef9adc59f53f9599bc5ee9d4f3a7448d0b0f0bbe4, sole parent9d3b19b0e7bf090e5d472d9781b9156f73ea2088.
Reviewer: GPT Work independent formal Reviewer; commands executed via Cloud Browser inside existing verbose space couscous, hostname codespaces-1996ee, shell/process UID1000. Reviewer did not author a candidate repair, invoke the issuer, obtain a private key, or assume the Operator role.

All1484 tracked candidate blobs independently recomputed against the frozen Git tree: PASS. Candidate code and historical assertions were not edited. Historical six test-source files were copied byte-for-byte into a new untracked reviews/POST_W68_ORIGINAL38_UNMODIFIED directory in this reviewer's detached worktree to preserve their existing relative-path contract. Their SHA256 values match the pinned ORIGINAL38_SOURCE_SHA256.json. Only declared IDENTITY.json modes were materialized on this new disposable checkout; every affected file retained its hash.

## Actual execution and results

| Gate | Actual result | Evidence / limit |
|---|---|---|
| Existing Codespace terminal | PASS | platform.json and platform.stdout prove codespaces-1996ee and actual process state |
| Frozen source / loader | PASS |1484 exact blobs; pinned launch verify exit0 |
| Approved runtime | PASS | Python3.12.14, Pydantic2.13.5, pytest8.4.2, SQLite3.45.1, OpenSSL3.0.13 |
| Python executable SHA256 | PASS |09605fdfbe88ca0d45a575ab8179cecd2a7167d95555b7bb8e6f29f29e82d42b |
| No controlling TTY | PASS | new-session process: /dev/tty unavailable; platform.stdout records errno and stdin state |
| AF_UNIX / SO_PEERCRED / pidfd | PASS, host capability only | owned socketpair and self pidfd, exit0; not a cross-UID signer proof |
| Existing trust public pins | PASS | root-owned0444 issuer/resident public keys; both DER fingerprints match frozen pins |
| UID999 / UID996 accounts | EXIST, LIVE LAUNCH BLOCKED | getent exit0; both sudo -n -u probes exit1: a password is required |
| Issuer Operator isolation | PARTIAL / EXPECTED DENIAL | root operator directory0700; Reviewer stat of protected issuer script denied, exit1; no privilege change attempted |
| fuzzy robot | BLOCKED | existing second Codespace UI entered, repository remains Restricted Mode; no terminal/runtime/materialization command executed there this run |
| Fresh TEST_ONLY response authority | BLOCKED | independent Operator handoff not received; no issuance attempted |
| Old Window68 response enrollment | REJECTED, expected | actual frozen native loader rejects existing on-host grant as expired or invalid, exit1 |
| Reviewer-owned or missing grant under writable ancestor | REJECTED, expected | both probes stop at protected-ancestor check, exit1; these do not prove deeper signature or purpose checks |
| Signed USER / DUE / SUMMARY / DELIVERED | BLOCKED | no fresh grant or Operator-arranged UID999/996 execution |
| Signed remote CAS / commit / ACK / restart | BLOCKED | no new signed authoritative completion executed |
| Signed replay / retirement / altered binding matrix | BLOCKED | existing regression components only; not a new full live matrix |
| SIGKILL before proof / before commit / after CAS | BLOCKED for signed lifecycle | no false live claim; relevant component regressions preserved |
| Original38 |31PASS /7FAIL /0ERROR /0SKIP | exit1, full stdout/stderr/JUnit retained |
| Window55 |33PASS /0FAIL | exit0, full stdout/stderr/JUnit retained |
| Window57 |29PASS /0FAIL | exit0, full stdout/stderr/JUnit retained |
| Publisher import equivalence | UNVERIFIED | original import-prohibition assertion actually fails; inert import does not prove signing-authority isolation |

The runtime/loader/platform checks used the approved interpreter. System Python was used only for orchestration, file hashing, report generation and XML parsing. Every regression subprocess started a new session. Exact argv, working directory, PYTHONPATH and approved-interpreter variable are recorded in regression-commands.json. The unchanged pytest run had no skips, xfail, assertion rewrite or test-filter exclusions.

## Seven preserved failures and classification

Six failures contain the actual /dev/tty failure in the Publisher startup path. They are legacy TTY/stdout transport-contract failures under the PM classification, not demonstrations that their crash/timeout/remote semantic obligations passed. Their required signed equivalents remain unexecuted. The seventh is a reproduced import-contract discrepancy: r005.publisher_service imports, while the original test demands ImportError. No unauthorized signing capability was demonstrated in this run.

- `test_sigkill_after_request_never_regenerates_or_redispatches`
- `test_absent_external_response_bounded_fail_closed`
- `test_real_core_external_publisher_with_c15_remote_barriers[due]`
- `test_real_core_external_publisher_with_c15_remote_barriers[user]`
- `test_real_core_external_publisher_with_c15_remote_barriers[summary]`
- `test_real_core_external_publisher_with_c15_remote_barriers[delivered]`
- `test_signer_not_importable_in_recovery_caller`

Full assertion messages and traces remain in regression-summary.json, original38.stdout and original38.xml. W67-VAL-002 remains OPEN. PM54-BLK-001/002/003 have passing existing regression coverage but are not independently closed by those component passes; fresh signed lifecycle and full Publisher authority equivalence are still unverified.

## Reproduction and engineering disposition

Run run-regressions.py from the same approved existing host after preparing a fresh detached checkout of the frozen candidate and the byte-pinned historical source. The file records all exact paths. This run requires the existing approved runtime at its frozen prefix, and never installs or rebuilds it. Each suite's exact command is also in regression-commands.json. Original38 reproduces six Publisher /dev/tty startup failures and DID NOT RAISE ImportError for test_signer_not_importable_in_recovery_caller.

No new minimal code defect is established. CODE_FIX_REQUIRED remains UNKNOWN because the binding compatibility contract and actual dynamic Publisher authority isolation are unresolved. Do not tell an engineer to remove assertions or restore stdout authorization just to turn these tests green. After proper Operator handoff, reprove the six semantic obligations with signed no-TTY execution and dynamically assess signing isolation. Only if a concrete authority-boundary failure is reproduced, or PM requires the original import prohibition, should PM commission a separate bounded corrective; the frozen candidate must remain unchanged.

## Concrete environment / coordination blockers

1. Reviewer UID1000 cannot start the existing UID999 Runner or UID996 external signer through the approved noninteractive command: both attempts exit1, sudo requires a password. An actually authorized independent Operator must arrange these restricted processes through the established mechanism. Reviewer must not supply a password, become root, alter sudoers, read issuer/private keys, or mint a grant.
2. Fresh <=3600s TEST_ONLY aios.r005.test.response.sign.v1 handoff has not been received. Actual old W68 enrollment is expired. A nonsecret planning request is stored on the original host at OPERATOR_COORDINATION_REQUEST.json; it is deliberately NOT published or sent through GitHub. It is marked PREFLIGHT_PARTIAL_DO_NOT_ISSUE_YET; exact operation bytes/hashes and live readiness must be finalized before issuance.
3. The already existing fuzzy robot repository workspace currently requires a trust confirmation in this browser. Reviewer did not change it. Second-host approved-runtime, source, delivery and loader rechecks therefore remain unrun; Window68's historical report is not substituted for this missing execution.

## Evidence integrity and limits

Raw test stdout/stderr, JUnit, exits, executed driver, candidate pins, platform probes, grant denial traces and full failures are included. Disposable runtime/test-state directories and all grant/signature/private-key files are excluded. No actual signing credential was collected. Initial orchestration stopped because rg is absent; that setup failure is preserved as an explicit diagnostic summary and a fallback using pathlib was used. It is not counted as a product defect.

No original test assertion, tracked candidate source, PR370/371/367 branch, main, archived evidence or trust root was changed. No third Codespace, real Resident or release/merge was created or started. This is an evidence-only report.
