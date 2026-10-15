# Window 59 — BLOCKED / QUALIFIED_LINUX_CAPABILITY_MISSING

Exact candidate and approved Runtime identity passed. Gate 0 failed in the actually available Work Linux sandbox. This session did not obtain a GitHub Codespaces or separately qualified Linux host. The requested execution-mode label is not proof of a qualified environment. No Harness regression suite, live Publisher attack, legal signing, Resident, or real Core/C15 fault run was started. All affected Gates 2–7 are BLOCKED_NOT_RUN.

## Ground truth

`git fetch --all --prune` succeeded. Git and fresh GitHub REST API independently agree on candidate `9d3b19b0e7bf090e5d472d9781b9156f73ea2088`, tree `ba3d75c309e144e5e93a32de5582f9b26da925ed`, sole parent `adf391178d7494ed17e1db802a31f001fb3b5f3b`, and main `271fa28d695efaeb1c888d93024eeddac9c8aa9f`. PR #367 is OPEN / DRAFT / UNMERGED. The detached candidate checkout has no changes. Core tree `16f1487e291b009c55bee402abfd79fdacbae960`; C15 tree `b8a62370e6ffe80730b2ef4c17d625fab50446d4`.

Fresh PR #361–#367 API responses and #366 PM comments are frozen in `github-ground-truth.json`. Exact raw Git commit API with tree/parents is in `github-exact-commit-api.json`. Required Window57 checklist, migration proposal, report, current delivery contract, packet and identity were read and frozen under `frozen-inputs/` with hashes. The PM adjudication #6182980136 remains binding: Route B is unapproved, original import assertion remains FAIL, and the TTY handoff contract remains open.

Window56 evidence was obtained from PR #365 exact head `c7496adc26b33d2b6b9a3c6fe278c7f185cfb01a`; original evidence ZIP SHA256 `ef624c72ca2577c4b7b59be86f9d089243ad046c3390b0a9cbdb8634853a4261` matched. Historical report, commands, case matrix and raw JUnit/log inventory were inspected. The original full ZIP remains in that separate historical PR and is not duplicated in this evidence package. No historical outcome is rewritten.

## Gate 0 independent capability results

Kernel Linux x86_64 6.18.44. The candidate probe was run unchanged, first with the host bootstrap Python and then with the exact approved Python. Both returned exit 78. A separate independent OS probe was frozen before execution and run under both interpreters. The approved run returned exit 78. See `commands.json`, `candidate-environment-probe.*`, `independent-approved-os.*`, `os-preflight.xml`, and `pty-tool-probe.json`. The JUnit file describes only OS preflight checks; it is not a formal Harness regression report.

| Capability | Actual evidence | Result |
| --- | --- | --- |
| Linux x86_64 | Actual kernel/machine recorded | PASS |
| AF_UNIX private listener + client + peer credentials | `socket(AF_UNIX, SOCK_STREAM)` raises EPERM before bind; actual bind/listen/connect cannot begin | BLOCKED |
| SO_PEERCRED on socketpair | Candidate probe gets matching current PID/UID/GID on socketpair only | Narrow PASS; does not satisfy listener gate |
| Authentic self/child proc and start-time identity | Approved probe sees `os.getpid()=8` while `/proc/self/stat` PID is 785; candidate child stat assertion also fails | BLOCKED |
| Correct-start / PID-reuse protection | No trustworthy PID-to-stat mapping; real reuse not induced or claimed | BLOCKED |
| pidfd lifecycle | Not readable while own child lives; readable after actual SIGKILL, wait exit -9 | PASS for OS smoke check |
| SIGKILL and restart | Own synthetic checkpoint child killed at -9; restarted process reads same checkpoint | PASS for OS smoke check only |
| Disposable Git remote | Separate temporary local bare remote accepts synthetic commit push; head matches | PASS for basic Git facility only |
| Controlling TTY | `/dev/tty` returns ENXIO; separate terminal tool call with tty=true also returns ENXIO and stdin_isatty=false | BLOCKED |
| Authorized OS memory/debug assessment | Proc identity cannot safely bind target to own child; no cross-process memory/ptrace dereference attempted | BLOCKED, no isolation conclusion |

## Three environment blockers (no new security exploit claimed)

1. **W59-ENV-001 — AF_UNIX listener unavailable.** Independently reproduced EPERM under approved Runtime. This reconfirms W56-ENV-001. Cannot assess genuine Publisher registration, RPC authorization, bound live signing or lifecycle service behavior.
2. **W59-ENV-002 — PID/proc identity inconsistent.** Process API PID and proc view disagree; candidate child parent identity assertion fails. This reconfirms W56-ENV-002. Cannot establish process-start identity/PID-reuse or target an authorized memory/debug attack reliably. pidfd smoke success does not repair that mismatch.
3. **W59-ENV-003 — controlling terminal unavailable.** Both ordinary execution and tool-requested PTY cannot open `/dev/tty`. Current capability disclosure cannot be exercised. This is a newly recorded environment blocker; it does not by itself prove the channel unsafe on qualified Linux.

`BLOCKER_COUNT=3` counts the current environmental root blockers only. Inherited open import/Route-B/authorization contract gates and unexecuted formal obligations remain unresolved; none is silently closed. No engineering security bypass or approved-key acquisition was demonstrated. No candidate fix or OS-protection relaxation was attempted.

## Gate 1 — approved Runtime PASS

Artifact 11747444013 was freshly requested through GitHub and its original bytes downloaded, not inferred from an existing local copy. ZIP: 88,511,202 bytes, SHA256 `cc6b72631e000fa161f027c3daf946805d41022a25725ead040d26c5509d155a`. It contains three members: tar, checksum and manifest. Tar: 88,509,303 bytes, SHA256 `ecfe4b4b6e9dee1a08342974e816f739dcd77fcd3f25f3ad7626cc7102e5673e`.

All 4,824 tar members were inventoried and path/type/link targets checked before fresh materialization at `/home/user/.cache/c002/final-runtime-003`. Approved archive symlinks stay within the approved Runtime, including its fixed absolute venv interpreter link. The frozen `runtime_identity.py` then verified all 4,426 materialized regular file bytes and modes. Binary SHA256 `09605fdfbe88ca0d45a575ab8179cecd2a7167d95555b7bb8e6f29f29e82d42b`; actual executable `/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python`. Versions: Python 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1 / OpenSSL 3.0.13. Identity command exit 0. No build or replacement dependency installation.

An initial archive-inspection command incorrectly asserted one ZIP member and stopped before extraction; corrected inspection used the actual three members and preserved the approved bytes. This was operator inspection, not a candidate test failure.

## Gates 2–7 — stopped at hard gate

Current Harness Artifact and packet static byte pins independently match the task. That is not delivery or materialization proof. No second independent environment was available and no same-container copy is presented as cross-sandbox success. `test_delivery.py` and `test_publisher_contract.py` were not executed.

Original historical `test_*.py` and `draft_runner.py` were recovered byte-for-byte from PR #361 exact commit into evidence only, with Git blob and SHA256 inventory. All 38 IDs are retained in the frozen compatibility inventory. None was run in Window59, so this window records **0 PASS / 0 FAIL / 0 ERROR / 38 BLOCKED_NOT_RUN**. No JUnit or test results are invented for the unexecuted formal suites. Window55 33 and Window57 formal regressions are likewise BLOCKED_NOT_RUN. No test/assertion was edited, skipped, xfailed or waived.

`LEGACY_IMPORT_ASSERTION=FAIL` is the preserved known historical contract outcome, not a new Window59 execution. Window57 reported 31 PASS / 7 FAIL as DEVELOPMENT ONLY, while Window56 original run was 27 PASS / 11 FAIL. Those historical counts do not become Window59 results.

B1–B6 actual service attacks/positives, same-UID secret/descriptor/ptrace/process_vm_readv tests, real Core verifier substitution and USER/due/Summary legal signing remain BLOCKED. No Publisher was launched. No private key or one-time capability was generated or copied into these logs.

External authorization delivery/isolation remains BLOCKED, not PASS or a demonstrated security FAIL. Genuine Core/C15 end-to-end and all five crash/CAS schedules remain BLOCKED. Basic SIGKILL/pidfd/local Git preflight does not establish product recovery/CAS. PM54-BLK-001/002/003 stay UNVERIFIED.

## Continuation boundary

The next authorized Operator must use an actual independently qualified Linux environment and rerun Gate0; a Codespaces/Docker name alone is insufficient. Then verify the exact Runtime and unchanged candidate and run all deferred Gates 2–7, including a genuinely separate second environment. Preserve original import/transport failures and request later PM contract adjudication only after complete dynamic evidence. No Fresh IA or Resident launch follows this report.

## Frozen disposition

Publication was pending when this report was frozen; a separate successful publication receipt, if present, supersedes that single field.

```text
WINDOW = 59
MODE = QUALIFIED_LINUX_FORMAL_VALIDATION
CANDIDATE = 9d3b19b0e7bf090e5d472d9781b9156f73ea2088
TREE = ba3d75c309e144e5e93a32de5582f9b26da925ed
QUALIFIED_LINUX_ENV = BLOCKED
APPROVED_RUNTIME = PASS
CROSS_SANDBOX_DELIVERY = BLOCKED
HISTORICAL_38 = 0 PASS / 0 FAIL / 0 ERROR / 38 BLOCKED_NOT_RUN
WINDOW55_SECURITY_REGRESSION = BLOCKED
WINDOW57_DELIVERY_REGRESSION = BLOCKED
PM54_BLK_001 = UNVERIFIED
PM54_BLK_002 = UNVERIFIED
PM54_BLK_003 = UNVERIFIED
ROUTE_B_DYNAMIC_ATTACKS = BLOCKED
ROUTE_B_LEGAL_SIGNING = BLOCKED
PUBLISHER_SIGNING_AUTHORITY_ISOLATION = BLOCKED
RESIDENT_AUTHORIZATION_CHANNEL = BLOCKED
REAL_CORE_C15_INTEGRATION = BLOCKED
REAL_SIGKILL_RECOVERY = BLOCKED
REMOTE_CAS = BLOCKED
LEGACY_IMPORT_ASSERTION = FAIL
PM_CONTRACT_ADJUDICATION = REQUIRED
EVIDENCE_PUBLICATION = PENDING
BLOCKER_COUNT = 3
PR_367_UNCHANGED = YES
REAL_RESIDENT_STARTED = NO
CURSOR_1_REVEALED = NO
INDEPENDENT_ACCEPTANCE = NOT_STARTED
FINAL_DISPOSITION = BLOCKED
BLOCKED_REASON = QUALIFIED_LINUX_CAPABILITY_MISSING
DO NOT MERGE
```
