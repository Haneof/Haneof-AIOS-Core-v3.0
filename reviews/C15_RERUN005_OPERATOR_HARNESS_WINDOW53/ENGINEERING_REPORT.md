# Window 53 operator engineering candidate

Formal task: `C15-RCC-RES-A-RERUN-005-OPERATOR-HARNESS-CORRECTIVE-001`.
This directory is **OPERATOR ONLY**. Deliver only the safe packet and its closed
harness artifact to Window 51. These are author tests, not Fresh Independent
Acceptance, PM adjudication, or permission to start Resident A. DO NOT MERGE.

## Ground truth and RED

Required `git fetch --all --prune` succeeded after clone and after reconnection.
Fresh main: `271fa28d695efaeb1c888d93024eeddac9c8aa9f`. Board/checkpoint top entries
confirm Window 50 accepted integration `703a8967878d8eaee70a8a8fce9df068204f5f76`,
accepted candidate `39b4f5f02e4331e27e3f66293837497d1a5ec477`, and Fresh A handoff.
Core tree: `16f1487e291b009c55bee402abfd79fdacbae960`.
C15 tree: `b8a62370e6ffe80730b2ef4c17d625fab50446d4`.
`GROUND_TRUTH.json` records mechanical byte/tree provenance and post-integration
paths. Window 51 cursor-zero/runtime status is user-reported; its independent
sandbox was not inspected, opened or altered.

`RED.json` / `RED.sha256` were frozen before edits. Reproduce all six missing
fields from the packet at that exact main. Original packet SHA256:
`a096b03048e1e0c69e92c715822431bc7a660f72335e820c84a14eaa7b0d6dae`.
The author gate rejects any missing mandatory condition.

## Historical reuse: PARTIAL

Historical `77dac70e0cf054c3f0fb7d94a66dba221fe7d5de` supplied atomic/canonical,
ledger, request/response storage, Core type projection and integrity utilities.
`GROUND_TRUTH.json` records their exact provenance. Historical Runner is excluded.
`draft_runner.py` is operator-only RED evidence: a plain live return does not mint
current Core authenticity; historical Publisher alone accepts an illegal directive.
Neither draft nor historical synthetic semantic code is imported in the artifact.
No old RC identity, acceptance ruling, state or Resident decision is reused.

## Real invocation and trust boundary

The safe JSON packet gives complete executable shell commands, variables,
response schema, verification, recovery and materialization. `launch.py` verifies
an externally packet-pinned manifest digest before imports, closed file sets,
all Core/C15/harness Python bytes, exact approved Python executable and dependency
versions. Python `-I`, explicit package roots and fresh bytecode-cache prefix reject
import aliases and bytecode substitution. New execution requires this bootstrap.

Current `HeadlessCore.submit_user_turn` and `process_due_work` drive actual Core.
The adapter exports a genuine RuntimeSnapshot, actual cockpit/catalog/history,
and bound run/session/subject identity. No directive is chosen by the adapter.
RoundSummary and DimensionSummary hooks also publish external requests. Tests
exercise the normal Core RoundSummary trigger; summary parser rejects invented
fallbacks and ambiguous/nonfinite JSON.

Publisher service runs in a distinct subprocess and refuses module import. RSA
private authority and Resident authorization are memory-only. Public verifier is
bound before Core dispatch. Authorization is emitted once to the external session
pipe/terminal; regular-file stdout is rejected. It never enters Core, environment,
argv, World, ledger or IPC files. External CLI reads it on stdin and sends a
content-bound HMAC over filesystem IPC, never the secret. No generic signing API
exists. Registered request/hash/schema/provenance must match before exact external
bytes are committed and signed. Runner holds the sole parent-lifetime pipe write
end; closure stops the service. PID alone does not authorize publication.
Filesystem IPC replaces AF_UNIX, which this sandbox rejects.

Envelope integrity/HMAC **do not establish Core authenticity**. For admitted
attempts, external service signs Core's exact late-return scope and canonical
payload. Runner calls `attach_late_trusted_return`, requires Core receipt, runs
accepted RelayJournal verification and only then begins applying. Composition
replaces the live-response recorder with a requirement for that existing receipt,
following the accepted OperatorSession composition surface. Its synthetic provider
implementation remains explicitly forbidden. Core/C15 sources are unchanged.

External session must keep its credential and pipe read end outside Core/recovery.
This process boundary does not claim OS administrator memory isolation or model
vendor attestation. Compromised external authorization does not replace the Core
proof. Independent acceptance must review these authority boundaries.

## Durability, exactly once and failure

Exchange fsyncs exact files/directories and append-only hash ledger. Wrapper explicitly
checks live SQLite checkpoint success and empty WAL before omitting WAL from an
archive; a busy checkpoint fails closed. It then seals
accepted GenerationStore, advances its generation ledger and uses accepted remote
CAS persistence. Request ready marker follows the remote request barrier. Response
consumption follows schema/hash/signature checks, Core receipt where applicable,
and remote authenticated-response barrier. Publisher success waits for remote
commit acknowledgment; later semantic application may still fail.

Completed operation replay returns the recorded result without another Core call.
Exact response replay verifies signed original bytes against the immutable recorded
Git commit. Conflicts cannot replace committed responses. Timeout, Summary error,
tampering, unknown/stale request, missing proof, process death, import drift,
remote failure/conflict and uncertain state fail closed. Interrupted operations
block redispatch and changed-spec bypass; no second request or recovery answer.
`reattach` materializes a pinned authoritative prefix into an empty cache, without
authorizing uncertain semantic continuation. Waits are bounded; resources release
on failure. Completion-barrier uncertainty changes the operation marker to failed.

## Verification, corrections and delivery

`SYNTHETIC_RESULTS.xml` and `FINAL_TESTS.log` hold actual nonempty results.
`COVERAGE.json` maps requirements to tests. Synthetic worlds, bare remotes and
responses remain in private temporary directories, outside actual RERUN-005 state.
Explicit synthetic decisions test protocol, never Resident behavior acceptance.
`FAILED_ITERATIONS/` retains nonzero runs. Fixes included generation ledger,
permitted file IPC, normal Summary trigger setup, Python substitution probe and
parent-lifetime portability. Added fsync probes were corrected to require the
actual LedgerError wrapper with its durability-failure reason. Summary setup now
uses canonical synthetic conversation ingestion, asserts 20 complete turns and
a legally pending range before and after its persistence checkpoint, then requires
the real Core to invoke the external Summary hook. An author edit during one running test invalidated
its frozen identity; that run remains failed and was rerun after freezing. Sandbox
reconnection required exact approved runtime rematerialization and archive modes.
No failures were ignored, skipped, or relabeled as passing.

Tar includes only pinned harness sources and IDENTITY.json, excluding operator
reports/tests/history, fixture/evaluator and state. Verify SHA before archive
listing; require absent target, unique closed regular-file set and no traversal
or links. Final suite runs the entire USER/Publisher/Core receipt/remote barrier
chain from an independently materialized exact artifact. Window 51 needs no
Window 53 local path and must never modify harness source.

Reproduce author gate:
`python3 reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW53/readiness.py --repo .`

Reproduce tests with packet-approved Python, `PYTHONDONTWRITEBYTECODE=1`,
`APPROVED53_PYTHON` set to that executable,
`PYTHONPATH=src:.:reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness:reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW53`,
`-m pytest -o addopts= -q -ra reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW53`,
and fresh workspace `--basetemp` (accepted backend rejects generic `/tmp`).

The approved runtime tar SHA256 was verified before extraction; 4,426 materialized
regular files were compared byte-for-byte with that exact tar. No build/install
was performed. Original archive modes were restored after transport.

No protected Core/C15/product-test/workflow/release/fixture files changed. No real
Resident started, cursor 1 revealed, PM state writeback or merge occurred.
Window 51 stays stopped until Fresh Independent Acceptance and PM authorization.
