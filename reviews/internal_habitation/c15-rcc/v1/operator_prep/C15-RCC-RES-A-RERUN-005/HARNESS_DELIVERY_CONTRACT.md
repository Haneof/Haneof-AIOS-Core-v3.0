# Current RERUN-005 delivery — Operator only

Status: candidate delivery engineering only. Independent acceptance and PM launch authorization are outstanding. This handoff authorizes no real Resident, cursor reveal, or state initialization. The older environment-build instructions are superseded; reuse only the exact approved portable runtime and do not rebuild/install a replacement.

The current source manifest is `harness/IDENTITY.json`, SHA256 `ef8cb44913c50fad7f5da8b3dcc8c20a510ea66d15af14c090e147e037e682cd`. It covers 21 Harness Python files, 79 Core files and 18 C15 files, with closed file/directory modes. This candidate keeps those bytes unchanged. The new `artifacts/resident-harness.tar.gz` contains the 21 Harness files plus `IDENTITY.json`; it is not the old 17-member artifact.

Exact Artifact SHA256: `e3afa5bcf5f55667767fecac5151f3cf53c69950fabeb11c47c7cded4cc4f222`. `artifacts/MEMBERS.json` is the closed 22-member byte/size/mode inventory. Runtime tar SHA256: `ecfe4b4b6e9dee1a08342974e816f739dcd77fcd3f25f3ad7626cc7102e5673e`. Approved interpreter: `/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python`.

Qualified Linux must support real AF_UNIX listener sockets, kernel SO_PEERCRED, Runner PID/UID/GID and start-time identity, pidfd, parent lifetime pipe, and a genuine controlling TTY. A socketpair or general `/proc` availability is insufficient. Work container errors are not permission to remove those checks.

Export Artifact and packet from the same frozen candidate commit. Check their pins before use. Do not export a prior Harness tar, the full repository/history, Operator evidence, test sources, governance or sealed fixtures into the Resident room.

For engineering verification, set `ARTIFACT` to the exact tar and `DELIVERY_DIR` to a canonical absolute **absent** destination under an existing real parent. Execute only the `cross_sandbox_harness_materialization.materialization_command` in the candidate packet. It validates the complete archive snapshot, closed members, regular types, metadata and per-file hashes before creating the target. It uses descriptor-relative no-follow writes, exact modes and fsync. Existing targets, including empty directories and dangling symlinks, are rejected. Interrupted partial targets remain blocked and are never silently overwritten.

Set `HARNESS=$DELIVERY_DIR/harness` and `SOURCE_REPO` to an independently prepared source directory containing the exact approved Core/C15 files and modes. Preserve the closed source layout `src/aios_core/**` and `tools/c15_persistence/**`; do not add modules/caches to those protected roots. Run the packet's `post_materialization_command` under the approved interpreter. The verification marker proves byte/import/router identity only; it is not launch permission or a full process-security gate.

Resident-visible material is limited to the pending safe packet, exact Harness tar, approved runtime and already authorized clean-room startup contracts/current input. Keep this file, the Window57 evidence directory, historical tests, source-provenance reviews and PM proposal private to the Operator. Nothing in this candidate permits revealing a future event.

Publisher authorization now uses an ephemeral **per-request** capability disclosed by the separate Publisher to a validated controlling TTY. It is not the historical Runner stdout/pipe token. Match REQUEST_ID and OPERATION_ID; never log/save the capability, place it in argv/environment, or deliver it to Core/recovery. The `publish` CLI takes its token via stdin. Proper TTY handling must be validated in the next qualified environment; do not emulate it by weakening authority checks.

Further engineering evidence, the unchanged 38-case compatibility matrix, raw commands/logs and the Publisher route-B migration proposal are in `reviews/C15_RERUN005_FORMAL_GATE_CORRECTIVE_WINDOW57/`. Route B is pending PM adjudication and complete system attacks. Historical import isolation remains FAIL. All formal 38, real Core/C15, crash/CAS integration and independent acceptance remain outstanding.
