# C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003 — Frozen-Contract Scope Correction

Date: 2026-09-28  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Pre-writeback live main: `b667928a34b479eb326d6de14f4ae78e2c1b284f`

## Decision

This is a **frozen-contract reconciliation**, not an ex-post-facto relaxation of an observed red gate.

The authoritative state-loss contract was frozen before persistence engineering began in:

`governance/C15_RCC_RES_B_RERUN_002_STATE_LOSS_ADJUDICATION_2026-09-26.md`

That contract defines the concrete failure class as operator process death / execution-environment loss that destroys the ephemeral run root. It requires non-ephemeral authoritative storage, durable cursor/provider evidence, exactly-once recovery at the five frozen kill points, evidence persistence, and no semantic shortcut.

It does **not** define malicious coordinated modification of an otherwise valid authoritative checkpoint, nor a multi-writer / hostile remote-ref race, as the acceptance threat model.

The later Corrective-002 Independent Acceptance prompt expanded adversarial coverage beyond that frozen failure model. The six findings remain preserved as valid engineering observations, but only four are binding blockers for the frozen Resident-B persistence gate.

## Infrastructure classification

`tools/c15_persistence/**` is **C15 release/test runtime operator infrastructure**, not AIOS product Core:

- the original corrective role is explicitly `Release / Runtime Persistence Engineer`;
- the original task says `Scope is operator/release persistence only`;
- the corrective is forbidden to modify `src/aios_core/**`;
- probes are required to use disposable/synthetic state;
- the accepted B preflight operator manifest identifies the role as `Release / Test Infrastructure Engineer`;
- Resident B receives ordinary frozen Core/runtime state and a Resident-safe interface while the operator runs outside the Resident-visible surface;
- PR #251 has zero `src/aios_core/**` changes.

This infrastructure is nevertheless **operationally required for the C15 Resident-B experiment**. It must correctly preserve the run/evidence under the frozen failure class, but it is not being promoted into a general-purpose production distributed-storage subsystem.

## Frozen execution/trust model

The accepted Phase-B runbook uses:

- one exact B run identity;
- one exact B session identity;
- a single authoritative per-cursor lifecycle;
- exactly one reveal per cursor;
- a single operator-side execution path;
- `world.sqlite.writer.lock` for the World writer;
- an operator-trusted model: the accepted known limitations explicitly state `operator-trusted model`.

Therefore Corrective-003 acceptance does **not** require correctness under an untrusted operator that intentionally rewrites checkpoint history, nor under multiple concurrent remote-ref writers that mutate/rollback/delete the same persistence ref behind the active operator.

## Corrective-002 IA finding reconciliation

The Independent Acceptance outcome remains:

`ACCEPTANCE_FAIL`

because binding blockers remain.

However, the gate-relevant count is corrected to:

```text
CONTRACT_BLOCKERS = 4
NON_BLOCKING_HARDENING_FINDINGS = 2
```

The historical reviewer statement of six findings is preserved and is not rewritten.

### Binding blocker — IA-BLK-PERSIST-C002-001

**K4 remote persistence failure is swallowed by capability execution.**

Binding because the frozen contract requires required evidence to be durably persisted before the run crosses the recovery barrier. The release procedure also requires STOP on inability to persist required evidence.

Corrective-003 must make durability failure a hard operator stop. It must not continue semantic/model work or ACK after failure to publish the required authoritative barrier.

### Binding blocker — IA-BLK-PERSIST-C002-002

**Later-round K3 / K5 fallback does not always converge from remote authoritative state alone.**

Directly binding to frozen contract item 4: exactly-once recovery after provider request staging and after model/capability work before ACK must converge without redispatch/duplicate semantic work/skipped ACK.

Real Resident B can execute multiple capability/model rounds, so the proof cannot be round-0-only.

### NON-BLOCKING HARDENING — IA-BLK-PERSIST-C002-003

**Coordinated generation-history tampering / extra artifact / seal-content attacks.**

The frozen contract requires exact recoverable bytes, digests, and survival of the defined platform failure class. It does not require the synthetic persistence harness to resist a trusted operator intentionally coordinating multiple authoritative-file mutations so that a shortened history remains internally consistent.

The remote Git commit is already a content-addressed authoritative snapshot for environment re-materialization. Existing exact-byte / manifest / artifact checks remain useful, but Corrective-003 MUST NOT introduce a new cryptographic history authority, second truth store, or generalized tamper-proof ledger solely to close this finding.

This remains a documented future hardening observation, not a C15 B-release blocker.

### Binding blocker — IA-BLK-PERSIST-C002-004

**Missing remote durability configuration can silently downgrade to local-only execution.**

Binding because the frozen contract requires non-ephemeral authoritative state for this released persistence mode. Once a run is created/materialized as remote-authoritative, loss/corruption of the binding configuration must STOP; it must never silently become ephemeral/local-only and later ACK.

Purely local disposable unit-test backends may remain legal when they were never declared remote-authoritative.

### Binding blocker, narrowed — IA-BLK-PERSIST-C002-005

**Remote binding can be transplanted across run identities.**

This remains binding only as a **minimal identity-consistency invariant**, not as a new security/cryptographic architecture.

Corrective-003 must mechanically prove that a remote-authoritative backend for run A cannot accidentally write to the canonical persistence ref of run B. The required fix is limited to structural binding of the persisted configuration/ref to the backend owner run/session identity and canonical ref derivation.

No cryptographic attestation, credential system, or new authority service is required.

### NON-BLOCKING HARDENING — IA-BLK-PERSIST-C002-006

**Remote expected-head check is not an atomic multi-writer CAS against concurrent rollback/delete races.**

The accepted B execution is single-operator / single-run / single-writer. The frozen state-loss contract does not introduce a second remote writer or a hostile actor that rewrites/deletes the authoritative ref between check and push.

Corrective-003 therefore does not need to turn the Git-backed C15 harness into a general multi-writer distributed transaction system or require force-with-lease solely for this gate.

Ordinary push failure must still fail closed. Fresh recovery after a successful remote push must not depend on disposable local `.remote-head` metadata.

This finding remains optional hardening for any future design that intentionally supports multiple concurrent persistence writers.

## Corrective-003 active scope

The binding Corrective-003 scope is now exactly four items:

1. `C002-001`: hard-stop propagation for remote durability failure, especially K4.
2. `C002-002`: remote-only exactly-once convergence for later-round K3 and K5 fallback/crash windows under the frozen process/environment-loss model.
3. `C002-004`: remote-authoritative mode cannot silently downgrade to local-only when its durable binding/config is missing or invalid.
4. `C002-005`: minimal canonical run/session/ref binding to prevent accidental cross-run persistence.

Do not create a second persistence truth store.  
Do not modify `src/aios_core/**`.  
Do not run Resident B.  
Do not enter RELEASE-003.  
Do not modify PR #251.

## Existing PR #254

At the time of this correction:

- engineering PR: #254
- branch: `arena/c15-rcc-res-b-persistence-corrective-003-sol-20260928`
- observed WIP head: `c9b7db880435e206928cf9d5b7086597b0701235`
- state: OPEN / DRAFT / UNMERGED

PR #254 began under the superseded six-blocker scope. It must reconcile to this correction before REVIEW_READY.

Implementation added solely to satisfy C002-003 or C002-006 must not become required architecture for the final candidate. If a defensive check already added for those findings is strictly local, behavior-preserving, introduces no new authority/state/protocol, and removing it would only churn the branch, it may remain as incidental hardening, but it must be explicitly marked **NON_BLOCKING / OUTSIDE FROZEN ACCEPTANCE REQUIREMENT**.

## Governance effect

After this correction is integrated:

```text
C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE
= DONE / ACCEPTANCE_FAIL
  CONTRACT_BLOCKERS=4
  NON_BLOCKING_HARDENING_FINDINGS=2

C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003
= IN_PROGRESS / SCOPE_CORRECTED
```

Still BLOCKED:

- `C15-RCC-RES-B-RELEASE-003`
- `C15-RCC-RES-B-RERUN-003`
- `C15-RCC-RES-B-ACCEPT-003`
- Resident C
- evaluator
- closure

Corrective-003 must stop at REVIEW_READY and receive fresh Independent Acceptance against this restored frozen contract.
