# Publisher isolation — proposed route B, PM adjudication required

**Not an approved contract change or security-equivalence conclusion.** The historical `test_signer_not_importable_in_recovery_caller` is retained byte-for-byte and FAILS. No deletion, skip, xfail, assertion change or caller-role guard was introduced. Window56's failed disposition is unchanged.

## The four capabilities

| Capability | Exact current implementation | Evidence boundary |
| --- | --- | --- |
| Import `r005.publisher_service` | Allowed; defines helpers and imports schema/transport modules | Historical RED and current unchanged assertion FAIL |
| Read the existing Publisher RSA private key | `p`, `q`, `n`, `d` and `key_id` are local to `main`; factors deleted after `d` construction; `d` captured by nested `sign` | Local scope/export checks pass; cross-process memory/debug/descriptor isolation NOT proven |
| Call the existing legitimate signing closure | `sign` and `dispatch` nested, not module exports; two sign calls in authorized publish dispatch | AST and import checks pass; real process path pending |
| Recovery acquires authority accepted by current Core | Requires live kernel-authenticated Runner registration, matching attempt/context/key, per-request external capability and pre-bound verifier | Helper attacks partially pass; actual Publisher/Core proof and legal signing positive NOT established |

Anyone may import public helper code or generate an unrelated RSA key. That is distinct from obtaining the key already bound to a genuine current Core attempt. The seven route-B tests do **not** prove arbitrary same-UID Recovery Python cannot modify its own imports, launch its own service/key, inspect another process, steal a terminal capability, or reach existing signing authority. Environment variables and argv are not trusted roles. Rejecting naive calls to `main()` proves only those specific calls fail the verified bootstrap check; that check alone is not an unforgeable trust boundary.

## Route A evaluation

Retain old import failure by making signer code a dedicated pinned subprocess entry and keeping Recovery's import graph free of it. A guard based on environment, argv, `__name__`, caller-supplied PID or mutable Python flag is insufficient. Satisfactory route A needs actual subprocess byte identity, non-importable signer entry, independent capability/lifetime binding and legal signing positives without weakening SO_PEERCRED/Runner checks. Moving/guarding code would change the frozen 21-file identity and require a fresh artifact, attack suite and formal rerun. This window did not implement that route and does not claim CLOSED.

## Route B proposal and rejection criteria

Permit inert module import only if the authoritative approved-key signing boundary is proved equivalent. Retain private key/signing closures solely in an independently verified Publisher process; accept registration exclusively from genuine live Runner kernel credentials, pidfd, lifetime pipe, start time, one operation and one request/attempt; require independent externally held per-request Resident authorization before proof creation. Current Core public-key verification must reject attacker/substituted keys. Import permission must never expose a signer API to Core/recovery.

PM approval should require **all** these dynamic gates on qualified Linux, not just the local seven checks:

1. Against actual pinned Publisher child, a separate same-UID caller sends true Runner PID claims, forged/stale instance/operation/attempt/context/key, duplicate registration and persisted forged receipts. Kernel peer identity must reject before registration/signing. No test doubles for identity/proof.
2. Recovery imports module and enumerates globals, closures, durable files, descriptors and OS-permitted memory/debug interfaces. It must obtain no existing RSA private key/signing callable or Resident capability. Test permitted ptrace, `/proc/<Publisher>/mem`, `process_vm_readv`, inherited descriptors and controlling-terminal access. Implementation does not explicitly set an OS non-dumpable boundary; module globals alone prove insufficient. If permitted OS access reaches secrets on qualified Linux, report a new engineering blocker to PM; do not expand this window's scope to fix it.
3. Actual publish RPC with absent, forged, wrong-request, wrong-operation, stale-instance, changed-byte or retired authorization must create no unauthorized response/proof or durable success. Genuine Runner must not use its registration role to publish responses. Include unsupported commands, oversized/malformed JSON.
4. Attacker-launched independent service/key must not substitute its public key into genuine current Core/recovery binding or replay a proof into a different attempt. Verify real Core rejection and truthful durable state.
5. Positive: genuine pinned Runner publishes real RuntimeSnapshot; an external mechanical test driver supplies exact synthetic response bytes using real controlling TTY per-request token. Actual Publisher signs, Core accepts genuine proof/receipt, accepted C15 commits authoritatively. Cover USER, due/background, Summary; no semantic AI Runner or Resident.
6. Runner/Publisher death, pidfd, stale PID/start time, socket substitution/restart fail closed without reissuing authority. Token retirement and exact remote replay preserve exactly-once properties.

The unchanged Window55 33-test suite is executable: 31 pass, 2 AF_UNIX errors here. It contains peer, context/provenance/operation and request-scoped authorization attacks; helpers do not replace actual service tests. Window57 seven tests establish inert import/local closures, naive role rejection, no environment-role registration fallback and synthetic verifier rejection. Legal live signing remains required and unproved.

## Additional historical transport discrepancy

Original full-process tests read a token from Runner stdout and reuse it. Current Publisher writes a token **per registered request** to `/dev/tty`, with REQUEST_ID/OPERATION_ID on the same line. Current tests fail earlier at `/proc`, so downstream compatibility is not established. Even on qualified Linux those old transport assumptions cannot be presumed green. PM must decide supplemental qualified mechanical-driver handling while preserving every original assertion/result. This window does not alter tests or supply a stdout/pipe fallback.

**PM decision requested:** authorize proposed import-contract migration subject to the six dynamic gates/channel validation, or require route A in a subsequent scoped correction. Until decision and complete proofs: `W56_REG_001=PM_ADJUDICATION_REQUIRED`, old test FAIL, formal 38 PENDING, no launch authority.
