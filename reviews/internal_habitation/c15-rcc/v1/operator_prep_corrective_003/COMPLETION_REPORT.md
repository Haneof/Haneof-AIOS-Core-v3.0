# Operator Prep Corrective-003 — evidence-only completion (2026-09-29)

**OPERATOR_PREP_CORRECTIVE_003_COMPLETE / REVIEW_READY**

**READY_FOR_INDEPENDENT_ACCEPTANCE** — not self-accepted; **not READY_FOR_RESIDENT**.

This window is launch/test infrastructure engineering only. No real Resident, C15 fixture, cursor reveal, release-state, real World/session, Phase-A cognition, B/C, evaluator, merge, tag or public release was run. PR #288 and review PR #290 remain immutable.

## Exact provenance and scope

| Identity | Pin |
|---|---|
| Fresh task-start main / parent of exact carry | `c8e9e42f8ae6e6724c0c7e9eb9dbb21b100f4487` |
| Exact #288 carry commit (372 files byte-for-byte) | `41de3f6698146661e73f6e43c00143fb63516ef1` |
| C10/C11 **pre-baseline** probe freeze | `4b2ca9fd48da2f1f44789c664de66bd471a39ee9` |
| Genuine exact-H2 baseline RED commit | `083dd9506f01ade04d4cbe805f58bf80d40607b0` |
| Corrected candidate **H1** / sole parent | `77dac70e0cf054c3f0fb7d94a66dba221fe7d5de` / `083dd9506f01ade04d4cbe805f58bf80d40607b0` |
| H1 tree | `52aa366bc6548e86e805585baddbc0470cb69660` |
| Historical failed #288 H2 / H1 | `771b200c33dbd6055b1d209935f8e1552f13090f` / `63c972ad7a19671cbdf809177f7a552aa2c2ecc6` |
| Historical failed review #290 | `39408137edf77976d0c4833fcde551891d5d081a` — `ACCEPTANCE_FAIL / blocker=2` |
| Frozen software / repository | `f20f2edfa7af00d0286493fd15196ca9503bc315` / `1ac3a675b884167d3a29aa432e7ef3eaff94d404` |
| Frozen Core / product tests trees | `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623` / `7e33b5ef8432370234965d3ccd61248c703c4019` |

H1 changes only Operator Prep `harness/aios_exchange` exchange transaction/durability, the mechanically necessary packet/freeze/audit tools, and **test-only** synthetic concurrency integrations. No `src/aios_core/**`, product `tests/**`, governance, fixture, evaluator or release-source edits. The eventual final evidence-only H2 must have **sole parent H1** and contain no harness/bootstrap/probe-source change. Its exact Git SHA/tree is reported externally in the new PR after commit, never substituted into historical evidence.

## C10 / IA288-01: shared mutation transaction

An exclusive Linux `fcntl.flock` on a dedicated persistent `ledger.jsonl.lock` file is shared by independent objects/OS processes. A same-process reentrant mutex only prevents nested self-deadlock; it is **not** the interprocess authority. Request publication holds the transaction from validated prefix, request ordinal and deterministic ID through atomic artifact publication, ledger record and completed durability. Response publication, direct ledger append and consumption use the same boundary. Runner recovery classification plus its possible NEW request publication is atomic, and the lock is released **before** waiting for an external response. Ledger reads also re-prove visible file/directory durability before using a prefix as state. Lock open/flock errors fail closed.

## C11 / IA288-02: required directory durability

On qualified Linux, directory open/fsync errors now propagate; a byte-visible replace alone is not a publication receipt. First ledger creation durably initializes an **empty** entry (file fsync then containing-directory fsync) before any dispatch record is written. Visible orphan requests from failed directory fsync are checked for canonical exact envelope/identity, **replaced** by the retry transaction, file+directory fsynced, then recorded once. Visible exact orphan responses are file+directory re-fsynced under the shared lock before a single response record; mismatched bytes are refused. A still-failing retry cannot adopt unproven bytes or produce a semantic-dispatch receipt. Exact recorded replays are digest-verified against disk and durability re-proven before success.

No second truth store or generic distributed transaction mechanism was added. Complete-valid-tail deletion without an external head anchor remains the previously documented limitation; the optional direct-consume request-file-mutation hardening observation in #290 is **not** claimed closed by this two-blocker corrective.

## Genuine RED, same frozen probes GREEN

Probe source, SHA-256, exact 18-node enumeration and expected PASS outcomes were frozen at `probes/PROBE_FREEZE.json` and `probes/PROBE_SHA256SUMS` **before any baseline run or H1 implementation edit**. The baseline imported a byte-for-byte Git archive of **exact #288 H2** and the frozen Core tree under the qualified runtime. `raw/baseline/` retains all raw logs, JUnit, environment, object identity and failure assertions: **C10 0/8, C11 0/10; 18 genuine FAIL**. No expected outcome changed.

The same frozen suite on H1, first and again under the **final packet**, passed **C10 8/8 and C11 10/10**; `evidence/c10_c11_candidate_green.json`, `raw/final_candidate/`, `raw/final_packet_tier/`. The true subprocess case, two independent ledger instances, distinct request publishers, explicit duplicate request identity, duplicate response and consume, and response/consume races all preserve monotonic chain, exact file digest, deterministic request identity and single event/dispatch. Directory-fsync and directory-open injection faults target actual required syscalls while file fsync succeeds; retry after failed request, response and initial ledger durability converges exactly once. Supplemental synthetic lock open/flock failure likewise raises without dispatch.

A separate disposable `integration/synthetic_concurrent_exchange.py` ran two concurrently published frozen-Core snapshot requests through concurrent external test-only responses and consumes, then a **synthetic due SAFETY Wake** through frozen Core and the real `run_due_work` boundary. The exchange ends with nine valid records and three self-consistent request ordinals. Two simultaneous normal runner handlers for the same synthetic snapshot yielded **one request dispatch / two handoffs**, one response publication and one consume, without deadlock. See `evidence/concurrency_integration.json` and the raw ledgers in `raw/final_candidate/integration/`. No C15 fixture or real state was used.

## Full preserved regressions and environment

- Corrective-001 **C1–C3 GREEN**; Corrective-002 **C4–C9 103/103 GREEN** (9/70/8/5/7/4). Gate A/B/C/D **24/7/2/5 PASS**, exact collected IDs, executed totals and raw results reconciled. The packet-tier reruns independently reproduce **C1–C3 GREEN**, **C4–C9 103 PASS**, **C10/C11 18 PASS**, and **A/B/C/D 24/7/2/5 PASS**.
- One disclosed pre-packet pass was **102 PASS / 1 FAIL**: the carried #288 packet had not yet acquired C10/C11 keys, so its `audit_packet` structural test correctly failed. Preserved in `raw/final_candidate/pre_packet/`. After an explicitly labeled provisional packet was built, the **unchanged** C4–C9 probes passed 103/103; the final packet pins that candidate-tier result. A separate final packet-tier rerun is outside the pin graph. No frozen expectation/source was revised.
- A newly **absent** scratch runtime `/home/user/.cache/c003/final-runtime-001` was independently built (not the author/reviewer predecessor). Explicit and default-root verify PASS. Exact versions: CPython **3.12.14**, Pydantic **2.13.5**, pytest **8.4.2**, SQLite **3.45.1**, OpenSSL **3.0.13**. The source-controlled pre-download wheel trust root and 11-wheel closed set verified; frozen software/Core/tests Git identities, **actual** Core/tests content manifests and import path verified. All four gates ran under this same qualified interpreter.
- The exact four-input clean-room startup set and `aios_exchange.runner:run_due_work` remain pinned; packet status is **`PREP_REVIEW_READY`**. Packet audit: **PASS, 59/59 pin checks**. Runner has no semantic script/callback, only external durable response bytes. No real Resident run was authorized or performed.

## Final mechanical hashes

| Artifact | SHA-256 |
|---|---|
| `P/RESIDENT_SAFE_LAUNCH_PACKET.json` | `3c2d04c2de8557c3cb7329df4350c40b2ccc07520a7d3d51db206174b33266cc` |
| `P/evidence/FREEZE_MANIFEST.json` | `5e79464e7a2cc03dfd33429a64c04b902e0f6d5ff21e42e6c24d9c3674e91b8a` |
| `P/evidence/SHA256SUMS` (73 files, zero uncovered) | `27ab476aae2ec5b26224e708e73b41c76b1d11cbf5e020d1a70e9d035af695e2` |
| Harness content manifest | `f3fbd788e3adb2ee600359e791273f87b444bc1991c7506d2683a643fd55a256` |
| Wheel trust root | `6fa2587c98662588e4758ac9b579fee8d800ce4fc2d36e692dbaaabd6f4c8afe` |
| Frozen Core content manifest | `220718d6b5a2650b5e4263bbe8b7e661444cb33b486a7ecd7b5ad3d7d3399caa` |

`P` = `reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP`. This report, `FINAL_PACKET_AUDIT.json`, Q's own `FREEZE_MANIFEST.json` and `SHA256SUMS` are review evidence only, not Resident startup inputs. The final evidence-only commit and Q's own self-excluding checksum hash are pinned in the new PR. **Stop at REVIEW_READY for fresh role-separated Independent Acceptance and subsequent PM adjudication.**
