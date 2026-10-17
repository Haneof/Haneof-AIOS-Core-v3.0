# Window57 — delivery engineering complete; Publisher contract pending PM

Task: `C15-RCC-RES-A-RERUN-005-OPERATOR-HARNESS-FORMAL-GATE-CORRECTIVE-003`. Role: C15 Harness Delivery & Security Contract Corrective Engineer. Disposition: **PM_ADJUDICATION_REQUIRED**. This is development evidence, not formal validation or independent acceptance. No real Resident or sealed cursor was accessed.

## Ground truth

Fresh fetch succeeded; main remains `271fa28d695efaeb1c888d93024eeddac9c8aa9f`. Independently queried PR #361/#362/#363/#364/#365 metadata is frozen in `FRESH_GITHUB.json`. PR #364 remains OPEN/DRAFT at `adf391178d7494ed17e1db802a31f001fb3b5f3b`, tree `ee335ae61f340919ac4e6a588f6a7e144e29b28b`. PR #365 evidence head is `c7496adc26b33d2b6b9a3c6fe278c7f185cfb01a`; exact ZIP hash `ef624c72ca2577c4b7b59be86f9d089243ad046c3390b0a9cbdb8634853a4261` verified. Its report and raw JUnit, command/case/source inventories were read. Historical candidate/test source was retrieved from Git, not inferred from chat.

New engineering branch starts directly from failed `adf3911…` with its complete ancestry retained. No amend/rebase or edit of PR #364/#365. Final publication receipt identifies the new exact commit/tree. The manifest/source_commit provenance remains unchanged; it describes the inherited source lineage, not the final evidence-commit SHA. Exact source bytes, tree and artifact pins are independently recorded.

Approved existing Runtime was reverified against exact ZIP/tar SHA256 and **4,426 materialized regular files and modes**. Binary SHA256 `09605fdfbe88ca0d45a575ab8179cecd2a7167d95555b7bb8e6f29f29e82d42b`; versions Python 3.12.14, Pydantic 2.13.5, pytest 8.4.2, SQLite 3.45.1, OpenSSL 3.0.13. Host Python only records/freezes evidence; current tests/build use explicit approved interpreter. No runtime rebuild or dependency installation.

## RED first

Disposable detached checkout at exact failed head ran the **unchanged** two historical delivery cases and historical signer-import case. Result: **3 FAIL / exit 1**. Failures were missing `cross_sandbox_harness_materialization`, missing current Artifact, and DID NOT RAISE ImportError. No AF_UNIX failure was interpreted as successful security exploitation.

`red-first/historical-three/{record.json,stdout,stderr}`, JUnit, `FROZEN_SOURCE_INVENTORY.json` and `frozen-sources.tar.gz` retain actual commands, exits, exact candidate sources/packet and unchanged historical test source. RED_FIRST=PASS means expected failure reproduced, not defense passed. Window56's original 27 PASS / 11 FAIL and its 31 PASS / 2 environment errors remain historical FAIL/BLOCKED; they are not rewritten.

## Delivery change

Inherited Harness code and `IDENTITY.json` stay byte-for-byte unchanged. Old PR361 identity had **16 Python files**; current identity has **21**, including five new completion/registration/IPC/authorization modules, and four changed entry/security files. The old delivery tar would omit or misidentify those modules. `HISTORICAL_DELIVERY_DIFFERENCES.json` records exact differences.

The builder scans the current closed manifest through the actual pinned launcher before reading files; it never creates a permissive glob-based replacement identity. New tar has **22 unique regular members**: all 21 Python files plus identity. Deterministic USTAR and fixed gzip metadata produce stable bytes on repeated approved-runtime builds. Exact Artifact SHA256:

`e3afa5bcf5f55667767fecac5151f3cf53c69950fabeb11c47c7cded4cc4f222`

Current manifest SHA256: `ef8cb44913c50fad7f5da8b3dcc8c20a510ea66d15af14c090e147e037e682cd`. Final packet SHA256: `04123169ec305273bd971f6254acb66f4bfdccf9bcce29d52e3d93d9fadf5e0c`.

Artifact/member/packet paths are under the existing Operator-prep RERUN005 directory. Safe packet embeds a standalone materializer and pins every member's size/hash/mode. It validates a single archive-byte snapshot before destination creation; rejects absolute/traversal paths, duplicates, unlisted files, symlink/hardlink/special/PAX members and metadata/byte drift; uses descriptor-relative no-follow exclusive writes, exact modes and fsync. Every existing destination is rejected, including empty directory, ordinary file, dangling/link directory. A racing creator cannot silently overwrite another result. Partial failure leaves a blocked target for Operator inspection.

The packet restores current entry, run/publish/read commands, state binding, bounded failure/recovery, **per-request controlling-TTY** authorization, clean-room startup contract blob pins and Phase-A cursor bounds. It excludes fixture bindings, prior PR/review/governance/event/test contents and is explicitly pending acceptance/PM, with real use unauthorized. The old Operator build instructions are marked superseded and a current delivery contract supplied. Artifact contains no Operator evidence, tests or semantic answers.

Independent directory materialization with restrictive umask succeeded; independently copied exact Core/C15 source (no Git history/governance) passed pinned verify under approved Runtime. This proves same-container independent-directory mechanics. A genuinely different environment/sandbox has **not** run and remains PENDING. Full delivered Core/C15 process chain remains unverified.

## Actual development results

| Run | Actual result | Boundary |
| --- | --- | --- |
| Final new delivery tests | 22 PASS | Materialization, pins, malicious members/transport, existing/link targets, concurrency, clean-room/cursor contract |
| Final Publisher local/synthetic checks | 7 PASS | Import/local scope, naive role claims, no env-role identity fallback, synthetic unsigned/substituted verifier rejection; no live signing positive |
| Unchanged Window55 suite | 31 PASS / 2 ERROR; exit 1 | Two socket creation EPERM errors; no system-level PASS |
| Final unchanged original38 compatibility | 31 PASS / 7 FAIL; exit 1 | Two delivery tests green; import assertion FAIL; six process/startup cases blocked; formal 38 PENDING |
| Runtime identity | PASS; exit 0 | Exact archive/binary/dependencies and 4,426 regular files/modes |
| Environment facilities | Exit 78 | AF_UNIX listener EPERM; real child `/proc` identity inconsistent; socketpair alone may work |
| Repeated final build | PASS; identical artifact/packet hashes | Current exact inherited source and fixed member closure |

All stdout/stderr and exits are retained in `logs/` with commands, source/packet/Artifact hashes for final runs and JUnit where applicable. `TESTED_SOURCE_IDENTITY.json` pins final executable/test sources. `COMPATIBILITY_38.{json,md}` maps **every one** of the unchanged cases; no skips/xfails/assertion changes. No aggregate of these runs is treated as formal acceptance.

Exploratory evidence is retained: the first new verifier test used an incorrect `verifier.verify` API (6 PASS / 1 test failure), corrected to actual `verify_late_return_proof`. An isolated subprocess import omitted `-B`, creating untracked Python caches; the builder and one development identity scan correctly rejected those caches. Only generated caches were removed and the new probe invocation corrected. Final 29 checks pass, final unchanged Window55 returns its two environment errors. Earlier faulty test sources are retained as non-collectable `.py.txt` snapshots, along with raw failed logs. No source/identity security check was relaxed.

## Publisher contract and remaining gates

Route A and B assessed separately in `PUBLISHER_CONTRACT_MIGRATION_PROPOSAL.md`. **Route B is proposed, not approved or proved equivalent.** Import defines helpers but exposes no existing private key/signing closure through module globals. That is a narrow result; OS memory/debug/descriptor/TTY isolation, actual service registration/signing attacks, unprivileged recovery reachability and legal genuine signing remain unproved here. Existing SO_PEERCRED, PID/UID/GID, pidfd/start/lifetime and real process identity are unchanged.

Historical full-process tests expect a Runner stdout token reused across requests, whereas current Publisher emits per-request capabilities on controlling TTY. Environment failure occurs earlier; this downstream contract discrepancy must be adjudicated, not assumed compatible. Original assertions remain FAIL/binding. If qualified Linux permits actual same-UID secret/signing access or reveals a code defect, report a new engineering blocker to PM.

`FORMAL_RERUN_CHECKLIST.md` lists required qualified-Linux gates including all real USER/due/Summary/delivered positives, live-service attacks and five actual Core/C15 crash/CAS schedules. PM54-BLK-001/002/003 remain formally UNVERIFIED. No real Resident, Cursor1, product code/tests, old evidence or merge was touched.

```text
WINDOW = 57
MODE = FORMAL_GATE_CORRECTIVE_003
FRESH_MAIN = 271fa28d695efaeb1c888d93024eeddac9c8aa9f
FAILED_CANDIDATE = adf391178d7494ed17e1db802a31f001fb3b5f3b
NEW_CORRECTIVE_HEAD = SEE_FINAL_PUBLICATION_RECEIPT
NEW_CORRECTIVE_TREE = SEE_FINAL_PUBLICATION_RECEIPT
NEW_PR = SEE_FINAL_PUBLICATION_RECEIPT
RED_FIRST = PASS
W56_DELIVERY_001 = CLOSED (ENGINEERING_DELIVERY_MECHANICS_ONLY)
W56_REG_001 = PM_ADJUDICATION_REQUIRED
W56_ENV_001 = ENVIRONMENT_GATE_PENDING
W56_ENV_002 = ENVIRONMENT_GATE_PENDING
ARTIFACT_IDENTITY = PASS
CROSS_SANDBOX_MATERIALIZATION = PENDING (INDEPENDENT_DIRECTORY_PASS; DIFFERENT_ENVIRONMENT_NOT_RUN)
DEVELOPMENT_TESTS = 29 PASS; WINDOW55 31 PASS / 2 ENV ERROR; HISTORICAL38 COMPATIBILITY 31 PASS / 7 FAIL
FORMAL_38 = PENDING
REAL_CORE_C15_INTEGRATION = PENDING
INDEPENDENT_ACCEPTANCE = NOT_STARTED
REAL_RESIDENT_STARTED = NO
CURSOR_1_REVEALED = NO
FINAL_DISPOSITION = PM_ADJUDICATION_REQUIRED
```
