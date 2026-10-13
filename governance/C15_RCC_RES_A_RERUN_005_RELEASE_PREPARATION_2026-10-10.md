# C15-RCC-RES-A-RERUN-005 Release Preparation — 2026-10-10

- Window 50 Fresh IA reported ACCEPTANCE_PASS / blocker=0 for PR #352 exact head `39b4f5f02e4331e27e3f66293837497d1a5ec477`.
- PM acceptance comment: `6093769692`.
- PR #352 merged by exact-head guard into main as `703a8967878d8eaee70a8a8fce9df068204f5f76`, tree `d4e1ee2df8a8a4803c09366041c789eadf2a7140`.
- Next dependency order from existing governance: operator/persistence corrective -> fresh IA -> fresh Resident A.
- Prepared task: `WINDOW 51 — C15-RCC-RES-A-RERUN-005`.
- Old RERUN-004/PR #296 state is historical only and must not be reused as live state.
- Resident-safe packet and prompt contain no prior Resident semantics or evaluator expectations.
- Exact post-merge main `p16-convergence-gate` run `38024230362` completed SUCCESS on integration baseline `703a8967878d8eaee70a8a8fce9df068204f5f76`; Resident start authorization is released after governance integration.
- Resident A cursor range = 1..13 only; ACK 13 then freeze/stop; cursor 14 forbidden.
- Resident A must not read this governance record.

## Final release status

`C15-RCC-RES-A-RERUN-005 = READY`

`WINDOW 51 = RELEASED`

Resident B / evaluator / downstream phases remain BLOCKED.

## Window 51 preflight environment unblock

- First Window 51 preflight stopped before cursor 1: `BLOCKED / OPERATOR_ENVIRONMENT_PREP_REQUIRED`.
- No event was revealed and no run state was created; this is not contamination and not a Phase-A failure.
- Cause: the initial RERUN-005 safe packet omitted the already-approved runtime path and mechanical verification command.
- Resident-safe packet now pins the prepared CPython 3.12.14 / Pydantic 2.13.5 runtime path and exact verification command.
- Environment build/provisioning remains OPERATOR_ONLY. Resident may verify/use the prepared runtime but may not build/install/design it.
- After this governance/launch-material correction is integrated, the same Window 51 may restart preflight from cursor 0 with fresh state.

## Portable runtime handoff finalized

- The previous local-path handoff model was invalid across isolated sandboxes; Window 52 and Window 51 do not share a persistent filesystem.
- A durable GitHub Actions artifact was independently built, verified against accepted current-main code, downloaded, hash-verified, extracted to the exact target path, and executed successfully.
- Workflow run: `38249942251` = SUCCESS.
- Artifact ID: `11747444013`.
- Artifact name: `c15-rerun005-approved-runtime-linux-x86_64`.
- Artifact ZIP SHA256: `cc6b72631e000fa161f027c3daf946805d41022a25725ead040d26c5509d155a`.
- Runtime tar SHA256: `ecfe4b4b6e9dee1a08342974e816f739dcd77fcd3f25f3ad7626cc7102e5673e`.
- Runtime tar exact-target execution probe passed: Python 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1 / OpenSSL 3.0.13.
- Window 51 may mechanically materialize this exact pinned artifact if its local runtime path is absent. It may not build or install an environment.

## Offline attachment transport-envelope adjudication

The direct GitHub Actions artifact ZIP digest remains authoritative for direct GitHub downloads. It is not a valid binding identity after a chat/file attachment transport may repackage the ZIP envelope. Offline attachment recovery therefore binds to the inner approved runtime tar SHA256 `ecfe4b4b6e9dee1a08342974e816f739dcd77fcd3f25f3ad7626cc7102e5673e`, plus the matching sidecar and a closed ZIP entry-name set. The operator manifest may be listed by name but must not be read by the Resident.

## Direct runtime tar offline handoff

Because chat/file transport may corrupt or repackage outer ZIP containers, the preferred offline handoff is now the exact inner runtime tarball itself: `aios-c15-resident-runtime-3.12.14.tar.gz`, size 88509303 bytes, SHA256 `ecfe4b4b6e9dee1a08342974e816f739dcd77fcd3f25f3ad7626cc7102e5673e`. The tar bytes themselves are the binding runtime artifact.
