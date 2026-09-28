# C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 — Independent Acceptance Failure Adjudication

- Date: 2026-09-28
- Role: C15 Governance PM / IA Disposition Reviewer
- Scope: source revalidation + governance disposition only. No #216 implementation change, no persistence-state mutation, no corrective implementation, no Resident B, no RELEASE-003.
- Pre-writeback live main: `8bceda2571c07c0e45ce8e11bd99665c75ed56ac`

## 1. Final adjudication

```text
C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE
= DONE / ACCEPTANCE_FAIL / blocker=2

C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-002
= READY
```

Failed tested exact candidate:

`63ca592359c7e3fd71d6cc4ba349949e4f0b80e3`

PR #216 remains OPEN / DRAFT / UNMERGED / PINNED. The exact candidate is permanently recorded as a **FAILED EXACT CANDIDATE** and must not be hash-swapped with any future corrective SHA.

## 2. Reviewer evidence disposition

- Review-only PR #240: CLOSED / DRAFT.
- Remote review head: `152be2406a05a7d4a2014e409d132a4c1126861b`.
- Reviewer workflow: `36337769581 = FAILURE`.
- PR #240 remotely contains reviewer probe source plus preserved rev1 / rev2-dryrun materials.
- Reviewer reported a later local commit `9d87018`, but GitHub credentials expired before push. **That commit is unpublished and is not treated as remote evidence.**
- Reviewer-reported Python 3.11.2 “30 probes / 22 green / 8 red” is **not** promoted to formal CPython 3.12.14 evidence.
- The two blockers below are accepted because PM independently reproduced their root causes directly from the frozen exact candidate source, not because of an unavailable final reviewer artifact.

## 3. IA-BLK-PERSIST-001 — SOURCE-CONFIRMED

**Remote durability is not in the normal production operator path.**

Exact candidate source:

- `tools/c15_persistence/operator_session.py:885-893`: `process_one_cursor()` performs only `reveal -> ingest -> run_turn -> ack`; it contains no `push_to_remote()` or `push_run_state()`.
- `tools/c15_persistence/platform_reattach.py:73-108`: Stage A first completes `session.process_one_cursor()` and requires ACK, then captures a manifest and only afterwards calls `push_run_state()`.
- `tools/c15_persistence/platform_reattach.py:179-201`: Stage B first executes `session.resume()` and requires ACK, then captures the new manifest and only afterwards calls `push_run_state()`.
- `tools/c15_persistence/operator_session.py:254-268` exposes a remote-push method, but the normal cursor loop does not invoke it.

Therefore the Stage A -> Stage B proof demonstrates remote durability at a **completed-cursor boundary**. It does not prove the binding K1-K5 contract: if the entire Arena execution environment disappears at K1/K2/K3/K4/K5, the exact mid-cursor barrier is not shown to have reached the remote authoritative backend before subsequent non-repeatable work.

Local filesystem fsync/process-restart convergence cannot substitute for cross-Arena durability after total environment loss.

Verdict: **BLOCKER CONFIRMED**.

## 4. IA-BLK-PERSIST-002 — SOURCE-CONFIRMED

**Sealed generation history is not validated by reopen / reattach gates.**

Exact candidate source:

- `tools/c15_persistence/backend.py:319-354`: `RunBackend.open()` validates path/owner identity/ownership, but does not invoke `GenerationStore.verify_all()`.
- `tools/c15_persistence/runstate.py:150+`: `verify_reattach()` validates run/session identity, current run-state manifest digest, pinned slot bytes, and SQLite/JSON readability; it does not invoke `GenerationStore.verify_all()`.
- `tools/c15_persistence/backend.py:607-614`: `GenerationStore.verify_all()` exists and recomputes every generation through `verify()`.
- `tools/c15_persistence/operator_session.py:940-950`: the observed production call site is `OperatorSession.report()`, where `generations: self.generations.verify_all()` is added to a report. Reporting after attachment is not the reattach admission barrier.

Thus a missing/modified/incomplete historical sealed generation is not mechanically rejected by the reopen/reattach admission gate solely because current run-state slots still match.

Verdict: **BLOCKER CONFIRMED**.

## 5. Historical author gates remain factual

The following are preserved as genuine historical results for exact candidate `63ca5923...`:

- formal workflow `36334415401 = SUCCESS`
- K1-K5 author suite 5/5 PASS
- production wiring 16/16 PASS
- environment/remote reattach 4/4 PASS
- resident-visible surface PASS
- historical journal PASS
- frozen E2E 158/158 PASS
- `src/aios_core/**` zero diff
- Stage A `914c960cade8830d4d0c80925bcfe03f803c3ceb` -> Stage B `15c75ac3e97c57a5fa1f3085c282a852994d9acf` direct-parent fast-forward proof

The IA verdict does **not** relabel those checks as failed. It establishes that their scope did not exercise two required persistence contracts.

Stage A/B evidence therefore remains valid for **completed-cursor remote materialization / cross-attachment reattach**, but cannot be used as K1-K5 mid-cursor cross-environment durability evidence.

## 6. Corrective-002 frozen scope

`C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-002` is the sole next READY task and may repair only:

### BLK-001
Integrate remote authoritative persistence into the normal operator durability path. At K1/K2/K3/K4/K5, before execution may cross the relevant non-repeatable boundary, the recoverable authoritative state must already be durably committed to remote storage. A genuinely new Arena environment must recover from remote only and converge without duplicate reveal, ingest, prohibited provider redispatch/semantic work, capability effect, assistant output, metering, or ACK.

### BLK-002
Make complete sealed-generation-chain verification part of remote materialization / backend reopen / reattach admission. Missing, modified, unsealed, malformed, incomplete, or hash-invalid generations must fail closed. No silent reconstruction.

All historical #216 red evidence, Stage A/B evidence, gate-integrity correction, and failed exact candidate identity must remain immutable history.

## 7. Downstream disposition

Still BLOCKED:

- `C15-RCC-RES-B-RELEASE-003`
- `C15-RCC-RES-B-RERUN-003`
- `C15-RCC-RES-B-ACCEPT-003`
- Resident C
- C15 semantic evaluator
- closure

No Resident B execution and no release is authorized by this adjudication.
