# Window 54 — Fresh Independent C15 Real Resident Harness Acceptance

**FORMAL_TASK:** `C15-RCC-RES-A-RERUN-005-OPERATOR-HARNESS-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`  
**ROLE:** Fresh Independent Acceptance Reviewer  
**CANDIDATE:** [PR #361](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/pull/361), OPEN / UNMERGED  
**FROZEN HEAD:** `67da1125c4902380dafde98a0ccf01c42e590864`  
**GIT TREE (independent REST Git object):** `5fe6d60cbea2b0725e7f2f7e37ef85611220b9c5`  
**PARENT / LIVE MAIN:** `271fa28d695efaeb1c888d93024eeddac9c8aa9f`  
**ACCEPTED C15 BASELINE:** `703a8967878d8eaee70a8a8fce9df068204f5f76`  
**CORE TREE:** `16f1487e291b009c55bee402abfd79fdacbae960`  
**C15 TREE:** `b8a62370e6ffe80730b2ef4c17d625fab50446d4`  
**DIFF SCOPE:** 48 changed files, all under `reviews/**`  
**DISPOSITION:** `ACCEPTANCE_FAIL / blocker=2 / DO NOT MERGE`. The complete 38-test candidate rerun is environment-blocked; this verdict is a *rejection* based on independently demonstrated source-level security defects, not an end-to-end acceptance result.

## Exact source evidence and blockers

### IA54-BLK-001 (A05/A07) — Claimed PID is not OS-authenticated sender identity

[Exact candidate `publisher_service.py` lines 78–100](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/blob/67da1125c4902380dafde98a0ccf01c42e590864/reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness/r005/publisher_service.py#L78-L100) uses `peer=int(command['caller_pid'])`, `os.kill(peer,0)` and `if peer != runner_pid`, then trusts `command['context']`. The IPC file can be written by any process with channel directory write access; the process identity field is self-declared. `os.kill(pid,0)` tests liveness/visibility only; it does not prove which process wrote the JSON. `channel.mkdir(mode=0o700)` does not distinguish processes sharing the same UID. There is no kernel-verified peer credential or runner-scoped authentication challenge in the registration path.

**Independent attack precondition:** a separate same-UID process can write the channel and can observe the live Runner PID and an existing request id/digest. **Defense required:** registration from a non-Runner process is rejected. **Observed in frozen synthetic process test:** unrelated process supplied the live Runner PID in JSON; the exact predicate accepted the caller and would trust attacker-selected `context` once the already-published-request digest precondition is met. Probe RC=0, but full Publisher and Core execution were **not** performed. Context controls inputs to the [Core signing branch, lines 127–139](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/blob/67da1125c4902380dafde98a0ccf01c42e590864/reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness/r005/publisher_service.py#L127-L139), so this is an unauthorized signing-context registration surface; no claim is made that a Core receipt was forged in the synthetic test.

**Impact:** non-Runner request reservation/registration and attacker-origin signing context; a malicious racing registration can force the genuine Runner to fail, and the Publisher's identity guarantee is false. **Minimal correction boundary:** replace file-message PID trust with a kernel-identified peer transport (e.g. Unix domain sockets with `SO_PEERCRED`), a private launch-scoped authentication capability inaccessible to request/response readers, and bind the registered signing context to the exact Core attempt. Prove that a same-UID unrelated sender is rejected, independent of its self-declared PID, before signing or acknowledgement.

### IA54-BLK-002 (A01/A03) — Executable import shadow bypasses manifest file-set and verification

[Exact `launch.py` lines 20–35](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/blob/67da1125c4902380dafde98a0ccf01c42e590864/reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness/launch.py#L20-L35) validates only manifest-listed file bytes, adds the writable Harness root to `sys.path`, then imports `r005.checks`. [Exact `checks.py` lines 41–57](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/blob/67da1125c4902380dafde98a0ccf01c42e590864/reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness/r005/checks.py#L41-L57) enumerates only `root.rglob('*.py')`; [lines 67–80](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/blob/67da1125c4902380dafde98a0ccf01c42e590864/reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness/r005/checks.py#L67-L80) inspect module file **path location**, not extension/source/loader or executable bytes.

**Independent attack precondition:** attacker can add a native extension `r005/checks.cpython-312-...so` / `r005/checks.abi3.so` to a materialized directory without altering the pinned `.py` entries. **Defense required:** startup rejects any unlisted executable member before import. **Observed in frozen synthetic import test:** manifest `.py` SHA and set remained unchanged, an added CPython extension shadowed `checks.py` and supplied fake `verify()` and `loaded_modules()` results. Probe RC=0 on CPython 3.13.5; exact candidate CPython 3.12.14 and complete launch were **not** executed. This follows CPython's extension-loader-before-source import resolution, which the exact bootstrap does not constrain.

**Impact:** arbitrary code may run before the integrity verifier from an unlisted executable, allowing a false-green identity/router status and bypass of source checks. **Minimal correction boundary:** authenticate the complete extracted regular-file set (all file extensions, directories, links and modes) **before any import from it**; resolve permitted modules from byte-pinned source paths using controlled import loaders, reject native extension substitution and validate loaded module byte identities. Test a malicious `.so` shadow with all approved `.py` hashes unchanged.

## Independent frozen source/data checks

- Exact Git SHA/head/tree/parent and 48 changed paths: verified using GitHub Git object and PR file-list APIs, independently of author claims.
- `src/aios_core` and `tools/c15_persistence` Git trees: identical across accepted C15 baseline, live main, and candidate.
- Git blob tar.gz SHA-256 computed independently: `689bdc3ea1fe4c7192006f89869fe2280bf92887af78e0ba78e151e175f32a4d` (36,999 bytes).
- `IDENTITY.json` independently computed SHA-256: `63f8e692d5f5121c4afb92d0f25e747b08dca6b764c6d8ef8a04e13654a4a04c`.
- Resident launch packet independently computed SHA-256: `a87fc5cd926f9695cac359a77748903f5bbc48ad484ce630a3d4ff421d1c70c6`.
- Frozen `RED.json` independently computed SHA-256: `9ea5bc3e4a263f195664364eb5f62defb38ed978ccfdd8fb2f6d2cdaadd14c53`. Main packet independently inspected: original lacked Runner/Publisher launch fields.
- Raw gzip/deflate independently decompressed *in memory* from the exact Git blob; gzip CRC32 `3fa45a4d`, inflated tar 153,600 bytes; exactly 17 regular files (16 `.py` plus `IDENTITY.json`), no duplicates, symlinks, hardlinks, traversal or unexpected entries; extracted Python entry SHA-256 match pinned `IDENTITY.json`. This **does not** claim independent filesystem materialization and actual launch.

## Independent test evidence

Frozen reviewer-owned probes (frozen SHA-256 before execution):

| Probe | SHA-256 of source | Execution |
|---|---|---|
| `ia54_a01_extension_shadow.py` | `93260c5d119949485b51810fffdc6341835c799afad1c429bc78428054927c56` | 0; synthetic extension override reproduced |
| `ia54_a05_pid_spoof.py` | `597289ad561f1bb39030c0ad3d1de727d58e98031ca36b70a1eb7dd211604ed3` | 0; synthetic claimed-PID gate accepted unrelated caller |
| `independent_poc_tests.py` | `868df61eb6beab5714d8a32a73ec9acd4fcf11b35501052b2c33ed4551d07eb3` | `pytest -q ...`: exit 0; two PoC assertions passed |

- Reviewer PoC JUnit `IA54_REVIEWER_ATTACK_JUNIT.xml`: two distinct testcases, failures=0, errors=0, skipped=0; SHA-256 `5ea156368bccc18ac019bb1424e0f71c072de4e56acde90df8845ccf8d574aff`.
- Reviewer PoC execution log SHA-256: `41c12ea7581a2bbacde11409f84d4f7313be750e6985d8c1cd385b0846f81fb4`.
- Local test environment: CPython **3.13.5**, pytest **9.0.2**, pydantic **2.13.5**. **Not** the approved CPython 3.12.14.
- Author 38-test regression: **NOT RERUN**, no reviewer-owned JUnit for it, exit code N/A. Container lacks exact checkout and approved CPython 3.12.14; direct git fetch cannot resolve github.com. Never treat author-published XML as independent execution.

## A01–A15 disposition

| ID | Independent result |
|---|---|
| A01 identity/import-substitution | **FAIL — IA54-BLK-002** (synthetic native-import shadow demonstrated; exact launch not run) |
| A02 artifact substitution | In-memory archive audit PASS; filesystem materialization/execution **NOT RUN** |
| A03 Runner/Core authenticity | Source path verified; runtime module loaded-identity bypass **IA54-BLK-002**; full execution not run |
| A04 scripted cognition | Static source review performed; complete dynamic negative tests **NOT RUN** |
| A05 Publisher impersonation | **FAIL — IA54-BLK-001** (caller-PID identity predicate flaw) |
| A06 Resident authorization | HMAC gate inspected; full unauthorized publisher execution **NOT RUN** |
| A07 Core trusted return | Signer input trusts unverified registered context; receipt bypass **NOT DEMONSTRATED** |
| A08 schema/provenance | Static validation code inspected; dynamic malicious response matrix **NOT RUN** |
| A09 durable request boundary | Source sequencing inspected; fsync/CAS kill injections **NOT RUN** |
| A10 exactly-once/recovery | Source replay contract inspected; crash injection **NOT RUN** |
| A11 remote persistence/CAS | Frozen source trees verified; concurrent drift/WAL probes **NOT RUN** |
| A12 real USER/due/Summary | Genuine Core calls visible in source; independent full execution **NOT RUN** |
| A13 cross-sandbox | Exact tar bytes/in-memory integrity PASS; distinct checkout/materialized launch **NOT RUN** |
| A14 resident information | Tar excludes author evidence; packet fields inspected; full runtime information-boundary test **NOT RUN** |
| A15 cursor zero | Reviewer never ran real Resident, never opened sealed fixture, never mutated Window51 state; cannot assert inaccessible runtime counters independently |

## Environment / stop boundary

Direct `git fetch --all --prune` attempted from container, but no `.git` workspace existed; `git ls-remote` failed due DNS resolution. The container's Python 3.13.5 (pytest 9.0.2) is not approved runtime; no current-candidate `38/38` rerun or full synthetic USER/Publisher/Core/C15 flow was claimed. GitHub connector source auditing, independently recalculated hashes and in-memory archive inspection did succeed.

**REAL_RESIDENT_STARTED=NO; CURSOR_1_REVEALED=NO (reviewer actions); PR_361_MODIFIED=NO; DO NOT MERGE.** Evidence publication is REVIEW_ONLY, must remain inaccessible to Window51 Resident and cannot substitute for PM adjudication. Any later full-suite execution must use the exact 3.12.14 binary and pinned artifact and produce its own raw JUnit and run identity.