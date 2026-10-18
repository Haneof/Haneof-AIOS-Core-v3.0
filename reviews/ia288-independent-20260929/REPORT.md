# Independent acceptance — exact PR #288

**2026-09-29 · Review-only / evidence-only · DO NOT MERGE**

## Verdict

**ACCEPTANCE_FAIL / blocker=2**

Exact reviewed head: `771b200c33dbd6055b1d209935f8e1552f13090f`.
No acceptance transfers to another SHA. No Resident release or PM integration readiness is granted.

The historical C1–C9 regression checks pass on this candidate, but two additional reviewer-authored attacks defeat its durable exchange guarantees. Author GREEN is not acceptance. No candidate repair was made.

## 1. Identity, authority and scope

Fresh-fetched main at entry and before publication: `75741433112f04f491f4998e2cd3612087c4fe88`. This is an observation, not a permanent baseline. PR head checked at entry and again before publication: exact H2, OPEN.

Read the binding IA prompt, current board/checkpoint control entries, PM review-ready note, PM #283/#284/#286 adjudications, both exact historical IA reports, clean-room contract and canonical Resident A contract. The current task is **READY**. Historical Resident semantics in control-plane documents were not used to construct synthetic tests.

| Identity | Independently observed |
|---|---|
| H2 | `771b200c33dbd6055b1d209935f8e1552f13090f` |
| H2 tree | `071b51c5fb37dc59fc8941dee2182637b9f87daa` |
| H2 sole parent / H1 | `63c972ad7a19671cbdf809177f7a552aa2c2ecc6` |
| H1 tree | `8cd4a2d8b4cdf1f85699c5d78166f774741b420b` |
| H1 sole parent / RED | `8e34fba00edf4fdb5b80f04d7a648f6b5bb8c40e` |
| Candidate task-start main | `b7c9e85014806637f7a01c8fd6695bc9f57672ba` |
| Frozen software | `f20f2edfa7af00d0286493fd15196ca9503bc315` |
| Frozen repository tree | `1ac3a675b884167d3a29aa432e7ef3eaff94d404` |
| Core tree | `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623` |
| Tests tree | `7e33b5ef8432370234965d3ccd61248c703c4019` |

`changed-paths.txt` is the fresh merge-base diff, not the PR description: **372 paths**, consisting of 71 Operator Prep, 36 Corrective-001 and 265 Corrective-002 files. Zero Core, product tests, governance, fixture/evaluator/release source or real database paths. `h2-paths.txt` and `static_audit.json` show no bootstrap/harness/probe-source changes H1→H2; H1 contains the implementation. No replacement SHA, amended commit or force-push is relied upon. This proves the inspected ancestry, not that no remote rewrite ever happened at any point in the repository's history.

The Arena-assigned review branch is `arena/01a0ebb4-haneof-aios-core-v3-0`, separate from #288's branch. Session constraints prohibit creating another branch, so this branch carries only review evidence. No branch switch, candidate modification, merge, tag, release or downstream work was performed.

## 2. Blockers

All candidate paths below use prefix:

`reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/`

### IA288-01 — Concurrent successful appends corrupt the ledger

- **Exact path:** prefix + `harness/aios_exchange/ledger.py`, `ExchangeLedger.append` (validated read through append/fsync).
- **Reproduction:** `probes_v2.py` / inherited `probes_v3.py`, `Probes.test_concurrent_append_preserves_validity`. Two distinct ledger instances share one empty synthetic ledger. A test-only barrier after each instance's genuine validated read forces both writers to observe the same legal prefix. Both append distinct legal `request_published` events. The probe changes no candidate source or ledger bytes; it controls a possible scheduling interleaving.
- **Observed:** both calls return `success`; the resulting chain fails with `non-monotonic sequence at seq 2`. Both computed sequence 1 and the same predecessor. Reproduced on host Python, independently built qualified Python, and the explicit frozen-RC archive run. See `raw_v3_frozen_archive.txt`.
- **Expected:** shared-ledger operations serialize the read/validate/allocate/write transaction, or reject overlapping writers before claiming successful publication. A successful pair of appends must leave a valid monotonic chain.
- **Binding reason:** IA §§12/23 require operational append integrity and adversarial concurrent/repeated-call coverage; PM's C5 correction requires non-monotonic sequence/duplicate/illegal-state failure before state-driving operations. The ledger currently validates a stale private copy, not the current durable prefix it appends to. Detecting the corruption only on the *next* read does not make these two successful durable-publication receipts valid.
- **Minimal corrective scope:** exchange ledger and publication concurrency protocol, including interprocess ownership/locking or an equivalent enforceable single-writer boundary; regression probes for independent writers and duplicate same-request events. Preserve response-byte and snapshot binding. Rerun and refreeze infrastructure evidence; no Core change.
- **Boundary:** this proves a reproducible race and invalid success, not successful silent semantic replay after a later integrity read. The later read correctly blocks.

### IA288-02 — Directory durability errors are swallowed before publication success

- **Exact paths:** prefix + `harness/aios_exchange/atomic.py`, `fsync_dir` and `atomic_write_bytes`; `requests.py`, `RequestPublisher.publish`; `ledger.py`, `ExchangeLedger.append`.
- **Reproduction:** `probes_v4.py`, `Additional.test_directory_fsync_error_blocks_publication`. On the qualified Linux environment, inject an `OSError` only for `os.fsync` on directory file descriptors; regular-file fsync remains real. Publish one legal synthetic request through `ExchangeBridge.publish_request`.
- **Observed:** request publication returns without raising. `fsync_dir` converts the directory fsync error to `False`; the atomic helper returns `fsync_directory=False`, but `RequestPublisher` discards the receipt. The new-ledger directory fsync result is also ignored. See `raw_v4_frozen_archive.txt`.
- **Expected:** an actual directory durability error must block durable-publication success. A byte-visible `os.replace` is not proof that a newly created directory entry is crash-durable.
- **Binding reason:** the approved infrastructure promises atomic publication plus fsynced durable ordering and fail-closed crash boundaries. IA §§8/12/17/23 and the historical Operator Prep durability requirement apply. The qualified platform supports directory fsync; this probe models an actual operation failure, not an unsupported-platform exception. Returning successful semantic-dispatch publication despite that failure defeats the durable boundary.
- **Minimal corrective scope:** propagate durability failures through atomic file publication, ledger creation and publisher receipts, with deterministic syscall-failure tests; regenerate packet/evidence after correction. Do not repair Core or run a Resident.
- **Boundary:** no physical power-loss experiment was performed. The proven failure is false success after a failed required durability primitive, not a claim that every such error necessarily loses data.

## 3. Probe discipline and environment

Reviewer freezes precede their execution:

| Revision | Commit | Purpose |
|---|---|---|
| v1 | `be5f054` | independent ledger concurrency, corruption, tail boundary, request mutation |
| v2 | `c573667` | disclosed envelope correction; replay and snapshot matrices; symlink |
| v3 | `959fe11` | independent due-Wake integration; 11 ledger faults × 4 operations |
| v4 | `34b7459` | directory-fsync failure; locked wheels; enumeration rejection |
| v5 | `501069b` | approved bootstrap verification matrix |

Each has source, collect-only/enumeration, expected outcomes and SHA-256 files. Collection imports no candidate implementation. v3 imports the already frozen v2 suite. v1's host result and qualified result are preserved: initial host execution lacked Core; its response envelope was also defective (missing `authored_by`, invalid `finish`). v2 corrects that probe setup, not the expected outcome. No defective history was overwritten. An accidentally committed generated `.pyc` was removed in the subsequent v4 commit; no probe source was silently rewritten.

Fresh absent build root: `/home/user/.cache/ia288/runtime`. The author's `/home/user/.cache/c002/final-runtime-003` was not used. Full build log, exit status, source/wheel hashes, installed distributions and environment records are in `environment/`.

- CPython **3.12.14**, Pydantic **2.13.5**, pytest **8.4.2**.
- SQLite **3.45.1**, OpenSSL **3.0.13**.
- Debian 12, kernel `6.1.158+`, x86_64, glibc **2.36**.
- Executable: `/home/user/.cache/ia288/runtime/runtime/3.12.14/venv/bin/python`.
- Final Core import: `/home/user/.cache/ia288/frozen-rc/src/aios_core/__init__.py`.
- Eleven exact distributions, including `pydantic_core==2.46.5`; complete set and wheel hashes in the records. `pip check`: no broken requirements.

Initial build verification and first runs used the checkout's source only after its complete Core/tests manifests matched the frozen identities. To remove any live-main provenance ambiguity, the final decisive probes, all 38 gates and all 103 Corrective-002 tests were repeated using **`git archive f20f2edf… src tests pyproject.toml`**, under `frozen-rc`. Copied Git metadata provides frozen object verification; HEAD is the review branch, not falsely represented as the frozen software commit. The source bytes come from the explicit frozen archive, not live-main substitution.

The build reports optional `ctypes`, `readline`, `bz2` and `lzma` unavailable. This is disclosed environment capability information, not an exact-pin failure; required runtime functionality and all supplied integration gates pass. No network/build limitation prevented reproduction.

## 4. Historical regression and full gates

Final complete gate evidence: `frozen_gates/gates/`; initial independent repetition and reconciliation: `gates/`, `gate_reconciliation.json`. All collect commands succeed, IDs are nonempty, result `test_count == len(test_ids) == execution_total`.

| Gate | Collected/executed/passed |
|---|---:|
| A | 24 / 24 / 24 |
| B | 7 / 7 / 7 |
| C | 2 / 2 / 2 |
| D | 5 / 5 / 5 |

Node IDs match the candidate inventory after removing only checkout-location prefixes; raw exact emitted IDs are retained. Malformed/empty/nonzero/mismatched collection is independently rejected by v4. The frozen Corrective-001 v6 rerun is GREEN (`c1_c3_author_rerun.json`); its inspection of author evidence is supplemental, not a substitute for our fresh gate execution.

The unchanged author Corrective-002 suite was independently executed twice: **103 passed**, including actual missing-Git-object and real system SQLite fallback negatives. See `frozen_author_rerun.txt` and `author_rerun.txt`. It is labelled author-authored, not reviewer-authored.

### C1: published-response replay

Independent v2/v3 matrix passes all five cases: intact exact replay is idempotent; tampered on-disk bytes, missing file, changed replay bytes and tampered consume fail closed. Manual inspection confirms existing-record `ResponsePublisher.publish_bytes` reads current bytes and checks both disk and replay hashes before success.

### C2: wheel trust root

Pre-download lock SHA independently matches `6fa2587c98662588e4758ac9b579fee8d800ce4fc2d36e692dbaaabd6f4c8afe`. Eleven-entry project/version/filename/tag/hash closure; downloads are checked against source-controlled values, not self-generated expectations. Installation uses explicit verified local wheel paths with `--no-index --no-deps`; `pip check` confirms the installed dependency set. Independent intact/wrong-bytes/missing/extra wheelhouse matrix passes. Post-download `SHA256SUMS` is evidence, not the trust root.

### C3: enumeration

Fresh A/B/C/D collection, execution and JSON inventory reconcile at 24/7/2/5; malformed/empty collection fails closed. No regression of #283's zero-ID defect.

### C4: recovery binding

Independent matrix passes: legal exact durable snapshot, outstanding S1/current S2, durable S1/current S2, two outstanding, two durable, and mixed distinct identities. Current code validates the full request-file digest, then both canonical-body digest and byte equality; it rejects multiple identities, not arbitrary `[0]` selection. Author's separately rerun detailed cases also pass.

### C5: operational integrity

Independent 44-case matrix covers interior edit/deletion, three duplicate event types, illegal order, sequence, prev-hash, record hash, request digest and response digest discontinuity, across append/recovery/consume/state-driving lookup. All reject. Legal chain remains operational. Author's 70 C5 cases pass. **IA288-01 remains an uncovered concurrent-append defect.**

Complete valid tail deletion was actually tested: removing the final complete response-publication record leaves a valid prefix, and `verify_chain` accepts it. This is **not detected**. PM's #286 adjudication expressly permits that limitation absent another head-anchor requirement. The acceptance boundary assumes no independently authenticated external history length; it does not claim protection against deleting a valid suffix. This is not counted as a blocker.

### C6/C7: frozen RC and exact runtime enforcement

Independent v5: default actual repository-root resolution and explicit root PASS; missing Git, one-byte Core/tests changes, symlink, foreign import, wrong SQLite and wrong OpenSSL BLOCKED. Wrong Core/tests tree checks are tested via disclosed Git-result fault injection, not purported real alternative commits. All 11 expected outcomes match. Actual missing frozen object and system SQLite fallback are covered by the unchanged author suite executed here. Correct exact values pass.

Independent canonical manifests match:

- Core: `220718d6b5a2650b5e4263bbe8b7e661444cb33b486a7ecd7b5ad3d7d3399caa` (77 files).
- Tests: `84b922ba0dfe1e80e0854d5edf94907b785baba851ef4528e669b95cf6526929` (101 files).

Sorted path/hash/size compact JSON is deterministic; bootstrap and tooling use the shared implementation. Symlinks are rejected. Qualification is not a permanent security boundary against replacing an interpreter or import environment *after* verify; this review makes no such claim.

### C8: startup and semantics

Read packet, generator, audit, clean-room wrapper and canonical run contract. Packet encodes exactly four approved startup inputs, with no board/checkpoint/PM/previous-run/source-history allowance. All Resident-readable packet values were inspected: historical entries are opaque mechanical commit IDs, not historical replies, claims, event payloads or expected semantics. Required forbidden-category vocabulary is not itself a semantic leak. No concrete historical semantic leakage found.

### C9 and Gate C/D

`run_due_work` requires aware `now`, constructs the same external handler, and calls frozen `HeadlessCore.process_due_work`; results are mechanical status/handoff/integrity output. Independent v3 emitted a synthetic safety Wake into a disposable World and completed one genuine model boundary: frozen Core → handler → durable request → independent test-only external response → durable consume → completed Wake. Full raw result is in `raw_v3_frozen_archive.txt`; no C15 fixture was used.

Gate C is non-vacuous: round 0 empty history, actual `search_world`, round 1 real nonempty result with exactly `name, ok, data, error_code, error_message, call_id`, followed by durable completion. Legal `CapabilityCall.arguments` was not confused with invalid `CapabilityResult.arguments`.

Manual run-package review found only serialization, schema/digest/sequence validation, file transport, waiting and Core delegation. No keyword/cursor/event semantic routing, prewritten reply, default semantic decision, hidden model callback or test-responder import. The test responder lives outside the real package; D's scanner PASS is corroborating, not sole evidence.

## 5. Freeze and historical probe integrity

`static_audit.json` and `additional_static_audit.json` recompute rather than trust summaries:

- Packet SHA: `f6b61c33dc41d20438ab1b56bd1c8f2e46fcf6593532f3793c3c51ee7fbf7cdc`; status remains **PREP_REVIEW_READY**, never READY_FOR_RESIDENT.
- Harness rows/bytes match; independently recomputed compact-row SHA `e3b9ca6cd502bc27f22bff59a09ff6024bed17ea0865d46018d1ab70a77d7632`.
- Package checksum scope: **70 entries**, zero mismatches, zero uncovered tracked package artifacts except checksum file itself.
- Corrective-002 checksum scope: **264 entries**, zero mismatches, zero uncovered artifacts except checksum file itself.
- Both FREEZE_MANIFEST files, packet, environment record, gate results, C1–C3 and C4–C9 results and canonical manifests are covered; all Corrective-002 manifest cross-scope artifact hashes match.

Chronology is linear: `4b7afc6` initial carry/probe freeze → `95d9da9` retained v1 result plus v2 scanner fix → `8e34fba` genuine #286 H2 RED freeze → H1 repair → H2 final packet/evidence. The only v1→v2 Python-source difference is `core_source` directory changed to `src/aios_core/runtime/turn_runtime.py`; expected outcomes are unchanged. No repaired source appears in H2 after H1 tests.

The two-tier method is non-circular: packet pins candidate-tier evidence; the later final packet audit is outside that packet's pin graph; checksums exclude themselves; H2 Git identity is external. Hash consistency establishes integrity relative to exact Git H2, not independent proof that author results were correct. Our reruns supply that latter evidence where reported.

## 6. Additional observations and limits

- **Non-blocking supplemental observation:** direct `ExchangeBridge.consume_response` accepts a response after the request file is appended with whitespace. v2/v3 request-mutation assertion fails. It uses the durable ledger request digest without rereading the request file. This does not, in this reproduction, apply an S1 answer to S2: the frozen runner recovery path separately validates the request body first. It is recorded as a TOCTOU/integrity hardening concern, not inflated into a third binding blocker without that additional demonstration.
- Valid whole-tail deletion is explicitly unprotected as discussed above.
- No exhaustive schedule search, physical power-loss trial, or independent due-work crash/restart matrix is claimed. The forced append interleaving and directory-fsync failure are sufficient concrete acceptance failures; green normal due work does not prove every restart schedule.
- Evidence-only scan found no real event identifier, cursor-state key, concrete prior Resident-run path or database artifact in the extracted candidate scopes (`additional_static_audit.json`). Combined with scope and synthetic raw evidence, no sign of real C15 execution was found. This is a bounded evidence inspection, not proof about unrecorded activity outside the candidate.
- No sealed fixture payload, evaluator expectation, real release-state or unreleased event was opened. No real Resident, real USER Phase-A turn, cursor reveal, real release initialization, B/C/evaluator/close or persistence continuation occurred.

## 7. Reproduction and publication

Set `PYTHONPATH=<exact H2 package>/harness:<frozen RC archive>/src` and use the independently built qualified Python. Run `probes_v3.py` and `probes_v4.py`; set `IA_PACKAGE` to the H2 package for v4. Expected reviewer assertions remain frozen: concurrency and directory durability are RED, normal replay/snapshot/ledger/wheel/gate checks GREEN. See `verify_v5.py` for the explicit approved-command matrix. Never point these synthetic probes at real Resident state.

`REVIEW_SHA256SUMS` covers the final reviewer evidence files except itself. Exact final review commit and review-only PR identity are published in the PR and #288 comment, outside this document's hash graph. No self-referential commit claim is embedded here.

**Disposition: reject exact #288; keep Resident and downstream work blocked. Stop after durable review publication.**
