# C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 — Execution Prompt

Repository: `Haneof/Haneof-AIOS-Core-v3.0`

Role: Release / Runtime Persistence Engineer.

Start by fetching live `main` and reading:
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `governance/C15_RCC_RES_B_RERUN_002_STATE_LOSS_ADJUDICATION_2026-09-26.md`
- the preserved RERUN-002 operator stop report
- accepted B-PREFLIGHT-002 runbooks/harness/environment/final-freeze materials.

Confirm `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 = READY`. If not READY, STOP.

Your only task is to close the operator-state persistence/recovery defect that destroyed RERUN-002.

Hard boundaries:
- no real Resident B;
- no real cursor-14 reveal;
- no Resident semantics;
- no `src/aios_core/**` changes;
- no sealed-fixture changes;
- no PR #205 evidence changes;
- do not reuse the retired RERUN-002 run/session/request identities;
- do not enter RELEASE-003 or RERUN-003.

Use only disposable/synthetic state for probes.

Required implementation/verification:
1. establish an authoritative non-ephemeral run-state location or durable checkpoint backend;
2. prove World/index/release-state/current-event/binding/projection/mailbox/failure evidence survive the relevant process/environment restart boundary;
3. add a durable provider relay journal with exact request/reply bytes and staged/exposed/reply-staged/applied state;
4. enforce a durable barrier before Resident exposure;
5. prove exactly-once recovery for kill points after reveal, after ingest, after request staging, after reply staging, and after model/capability work before ACK;
6. prove no duplicate reveal/ingest/reply application/ACK and no skipped cursor;
7. rerun the frozen 158-check E2E and lifecycle mutation-red probes unchanged, plus the new persistence tests;
8. preserve all red evidence from any failing attempt;
9. produce a narrow candidate and evidence package, then stop at `REVIEW_READY`.

Do not independently accept your own candidate.


---

## Binding PM scope amendment

Before continuing this task, read and obey:

`governance/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_001_PM_SCOPE_AMENDMENT_2026-09-26.md`

This amendment supersedes the original wording that implied every kill point must automatically converge in the same run.

Exactly-once **safety** remains mandatory at every kill point. Same-run forward continuation is required only where the frozen Core and durable evidence mechanically prove replay/continuation safe. Ambiguous post-dispatch or partially-applied semantic work may terminate durably/fail-closed instead of being blindly replayed.

Do not modify Core to weaken `in_doubt`.
Do not mark an ambiguous provider response `not_submitted`.
Resume the existing WIP rather than restarting it.
