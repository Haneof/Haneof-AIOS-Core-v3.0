# Window 67 independent formal security report

FORMAL_VALIDATION_FAIL / DO NOT MERGE. This is formal validation only, not independent acceptance.

## Exact candidate and environment

Fresh fetch succeeded. PR370 HEAD/tree/single parent match the frozen identity. PR367 remains unchanged. All candidate changed paths are within the approved review/harness-delivery scope; Core/C15 product paths are unchanged. Artifact members and source files were independently compared against final candidate bytes, not inferred from source_head_at_build. Three requested SHA256 values match.

Actual browser-connected Codespace: verbose space couscous. Python 3.12.14 executable hash matches the pinned manifest. Current AF_UNIX/SO_PEERCRED, PID/proc/pidfd, dedicated-child SIGKILL and a new-session process without /dev/tty all passed. SIGKILL capability is not a crash-recovery PASS.

UID999/GID984 and UID996/GID983 were separately executed after a privileged parent dropped all supplemental groups. Both were denied the other protected account directory and Operator directory; both denied sudo. Metadata only was inspected in private-key directories; no private bytes were read. This proves the checked filesystem isolation, not the complete live Publisher signing boundary. Direct sudo -u attempts first required a password; those diagnostics remain.

## Gate results

| Gate | Independent result | Limits |
|---|---|---|
| A | Final-byte identity PASS; fresh-directory materialization PASS, repeat refused, materialized loader verify PASS | Cross-environment delivery BLOCKED |
| B | Fixed-root public checks and filesystem isolation; mechanical.ping purpose rejected | Fresh response enrollment/expiry/revocation matrix BLOCKED |
| C | Source review and applicable old regressions recorded | No newly scoped live signed Publisher operation; actual endpoint adversarial matrix BLOCKED |
| D | USER/DUE/SUMMARY/DELIVERED BLOCKED | No newly issued Window67 enrollment; no real Resident started |
| E | Signed lifecycle/CAS/crash recovery BLOCKED | No authorized fresh signed run; capability probe is not recovery proof |
| F | Original38 31/7; Window55 33/33; Window57 29/29 | Historical failures remain FAIL; W54 issues not closed |
| G | Author evidence hash inventory matches; limited public secret scan found no PEM private-key block or top-level usable enrollment | This is a bounded scan, not universal credential-detection proof |

## Original regressions

All six copied original source files match the frozen original-source hash inventory. All38 tests executed, zero skip/xfail. stdout/stderr/JUnit/exit codes retained. Tests were copied unchanged into a reviewer-only untracked directory at the required two-level repo layout so source-relative tests execute this exact candidate.

Frozen parent: 31 PASS / 7 FAIL; failure-name set equal: True.

Failures:
- test_sigkill_after_request_never_regenerates_or_redispatches
- test_absent_external_response_bounded_fail_closed
- test_real_core_external_publisher_with_c15_remote_barriers[due]
- test_real_core_external_publisher_with_c15_remote_barriers[user]
- test_real_core_external_publisher_with_c15_remote_barriers[summary]
- test_real_core_external_publisher_with_c15_remote_barriers[delivered]
- test_signer_not_importable_in_recovery_caller


## Evidence and execution limitations

Initial checkout files had 666/777 permissions and the inherited shell umask was000. A second checkout also had broad permissions. Reviewer provisioned only declared manifest metadata (644/755) with byte-digest equality checks. Engineering bytes and tests were not fixed. The initial 24/14 and25/8 environment-diagnostic results are preserved under regression-attempt1. A second diagnostic repeat had the same counts; an archive-command syntax error prevented keeping its separate files before overwrite, so it is not claimed as separately preserved evidence. Final qualified run used APPROVED53_PYTHON and declared modes. An auxiliary Reviewer delivery script had a quoting SyntaxError; that source/error is retained. No such tooling failure is reclassified as a product defect.

First materialization logs were superseded by a repeat against an existing reviewer target; the clearly named materialize-fresh-first/fresh-repeat/fresh-verify records supply a clean first/repeat proof. All previously retained files are kept. Old negative grants reject at purpose before expiration/key-binding checks; tampered enrollment has no matching signature file. These are not credited as expiration/revocation/invalid-response-signature tests.

TEST_ONLY packet metadata forbids real launch and signed loader requires the response-purpose test grant. Without a new valid enrollment no formal claim is made that every alternate invocation is closed. Cross-environment test was not executed in fuzzy robot Restricted Mode; no trust setting was changed. Local bare Git authority was not exercised independently in a new signed run and is never claimed as hosted/production authority.

No new confirmed code vulnerability was established; blocked work is not a security PASS. W54 native-import, forged-registration and premature-completion issues remain UNVERIFIED under the new architecture. Publisher ImportError assertion still fails; equivalence remains UNVERIFIED without PM replacement adjudication.

## Required status

~~~text
WINDOW = 67
ROLE = INDEPENDENT_FORMAL_SECURITY_VALIDATION
CANDIDATE_HEAD = 6fb725407569bc719c049587f67fe65e797eb734
CANDIDATE_TREE = f9adc59f53f9599bc5ee9d4f3a7448d0b0f0bbe4
PR_370_UNCHANGED = YES
PR_367_UNCHANGED = YES
QUALIFIED_LINUX = PASS
APPROVED_RUNTIME = PASS
ARTIFACT_IDENTITY = PASS
ENROLLMENT_AUTHORITY = BLOCKED
RESIDENT_PRIVATE_KEY_ISOLATION = PASS
PUBLISHER_SIGNING_ISOLATION = BLOCKED
SIGNED_RESPONSE_AUTHORIZATION = BLOCKED
AF_UNIX_IDENTITY_BOUNDARY = BLOCKED
UNATTENDED_USER = BLOCKED
UNATTENDED_DUE = BLOCKED
UNATTENDED_SUMMARY = BLOCKED
UNATTENDED_DELIVERED = BLOCKED
NEGATIVE_SIGNATURE_TESTS = BLOCKED
REPLAY_AND_RETIREMENT = BLOCKED
REAL_CORE_C15_REMOTE_CAS = BLOCKED
SIGKILL_RECOVERY = BLOCKED
CROSS_ENVIRONMENT_DELIVERY = BLOCKED
ORIGINAL_38 = 31 PASS / 7 FAIL / 0 SKIP
WINDOW55_REGRESSION = 33 PASS / 0 FAIL
WINDOW57_REGRESSION = 29 PASS / 0 FAIL
PM54_BLK_001 = UNVERIFIED
PM54_BLK_002 = UNVERIFIED
PM54_BLK_003 = UNVERIFIED
PUBLISHER_IMPORT_EQUIVALENCE = UNVERIFIED
NEW_SECURITY_BLOCKERS = 0 confirmed new code defects; 3 validation blockers; 7 binding historical regression failures
EVIDENCE_PUBLICATION = PASS
FORMAL_DISPOSITION = FORMAL_VALIDATION_FAIL
INDEPENDENT_ACCEPTANCE = NOT_STARTED
REAL_RESIDENT_STARTED = NO
CURSOR_1_REVEALED = NO
DO_NOT_MERGE = YES
~~~

Evidence-only Draft PR: https://github.com/Haneof/Haneof-AIOS-Core-v3.0/pull/371
