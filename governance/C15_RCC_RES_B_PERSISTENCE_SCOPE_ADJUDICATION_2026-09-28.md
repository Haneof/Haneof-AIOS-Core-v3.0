# C15 Resident B Persistence — PM Scope Adjudication

Date: 2026-09-28

Repository: `Haneof/Haneof-AIOS-Core-v3.0`

Pre-ruling live main: `b667928a34b479eb326d6de14f4ae78e2c1b284f`

## Decision

The persistence corrective has been over-scoped by the latest adversarial review.

This ruling does **not** erase the Independent Acceptance result against failed exact candidate:

`7b2556e738d9c9386ec21c13fec39400c87d0916`

and does not relabel its RED probes as green.

It separates:

1. findings that violate the originally frozen C15 state-loss corrective contract; and
2. useful hardening findings that would turn a synthetic C15 harness into a broader production/distributed-storage security system.

Binding disposition:

```text
historical reviewer verdict = ACCEPTANCE_FAIL / blocker=6
PM frozen-contract blockers = 3
PM non-blocking hardening findings = 3

C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003
= READY / NARROWED_SCOPE
```

## Architectural classification

Fresh repository inspection establishes:

- live `main` does not contain `tools/c15_persistence/**`;
- the failed candidate PR #251 introduced that harness on an unmerged branch;
- `pyproject.toml` packages only modules under `src/`;
- the project console entrypoint is `aios-core-headless = aios_core.headless.cli:main`;
- the real C15 B operator already present on main is `tools/c15_preflight/arena_resident_operator.py`, which connects restored accepted-A state to real `FusedTurnRuntime`, real C15 release bindings and the Resident file bridge;
- the original persistence task prompt explicitly required `no src/aios_core/** changes` and `Use only disposable/synthetic state for probes`;
- the state-loss PM adjudication explicitly says `Scope is operator/release persistence only`.

Therefore `tools/c15_persistence/**` is a C15 habitation/release test-and-operator persistence harness. It is not AIOS Core product implementation and is not presently shipped by the `aios-core` package.

Its purpose is narrow: prevent a repeat of RERUN-002, where a real B cursor had been revealed, bound, ingested and provider-dispatched, then the platform destroyed the canonical `/tmp` run root before Resident reply/ACK.

Corrective-003 must not use this task as a vehicle to introduce a new production persistence subsystem.

## Frozen contract that still binds

The original state-loss adjudication requires, using disposable/synthetic probes:

- non-ephemeral authoritative run state;
- durable cursor checkpoint before model exposure;
- durable exact provider relay journal;
- crash/restart coverage at reveal, ingest, provider-staged, reply/application, and model/capability-before-ACK boundaries;
- recovery to the same durable cursor without duplicate reveal/ingest/semantic application/ACK or skipped cursor;
- projection/binding/mailbox/failure evidence survival;
- no semantic reconstruction shortcut;
- frozen regression unchanged.

Those requirements remain binding.

## Finding classification

### Binding blocker — IA-BLK-PERSIST-C002-001

K4 remote persistence failure is called inside the registered capability handler after local capability ledger/counter mutation. Core `CapabilityRegistry.invoke()` converts ordinary handler exceptions into structured `CAPABILITY_EXECUTION_ERROR`.

If the authoritative durability checkpoint fails yet the turn can continue, the harness violates the frozen durability/exactly-once contract.

**Disposition: BLOCKING.**

Corrective-003 must make a failed authoritative checkpoint a hard operator stop that cannot be swallowed by capability-result wrapping.

### Binding blocker — IA-BLK-PERSIST-C002-002

Reviewer formal probes report later-round K3 remote-only recovery failing to converge, with K5 pre-push crash falling back to the same unresolved authoritative snapshot.

The original frozen contract explicitly requires kill/restart recovery after provider request staging and after model/capability work before ACK. Multi-round capability/model execution is part of the real runtime path.

**Disposition: BLOCKING.**

Corrective-003 must prove later-round remote-only convergence without redispatch/duplicate semantic work/output/metering/ACK.

### Non-blocking hardening — IA-BLK-PERSIST-C002-003

The reviewer found that the synthetic generation layer can accept some coordinated storage tampering, including lowering the mutable generation ledger while deleting history tail, and does not authenticate seal-file contents or reject every unexpected generation-directory file.

The original failure model is platform loss/restart, not an attacker with write access to the authoritative stored bytes. The frozen contract requires durable/digested recovery evidence; it does not require a Byzantine or tamper-evident append-only ledger against a party capable of coordinated storage rewriting.

Existing ordinary corruption checks for missing/modified/incomplete generations remain useful and must not be weakened.

**Disposition: NON-BLOCKING HARDENING / OUT OF C15 RELEASE GATE.**

No new immutable-history security architecture is required by Corrective-003.

### Binding blocker — IA-BLK-PERSIST-C002-004

A remote-authoritative run can lose `remote-durability.json`; candidate `_load_remote_durability()` then returns false and attach/resume may continue local-only.

This recreates the exact class of failure the corrective exists to prevent: a consumed B run can again make authoritative progress that exists only in an ephemeral local environment.

**Disposition: BLOCKING.**

Corrective-003 must durably distinguish local-only synthetic backends from runs declared remote-authoritative, and remote-authoritative attach/resume must fail closed if binding metadata is missing/corrupt/unavailable.

### Non-blocking hardening — IA-BLK-PERSIST-C002-005

Copying another run's internal remote config plus its expected-head marker can redirect a synthetic backend to another run's ref.

The frozen workflow already requires RELEASE to mint one fresh exact run/session identity, prohibits identity reuse and operates one controlled run. It does not define an adversary allowed to transplant internal harness metadata between valid runs.

This is worthwhile defensive hardening but not part of the RERUN-002 platform-state-loss acceptance contract.

**Disposition: NON-BLOCKING HARDENING / OUT OF C15 RELEASE GATE.**

A simple low-risk identity assertion may be kept if already present, but no cross-run security architecture is required.

### Non-blocking hardening — IA-BLK-PERSIST-C002-006

The candidate performs an expected-head read followed later by a normal Git ref push. The reviewer attacked concurrent rollback/delete between those operations and requested a server-side lease.

The C15 persistence task has a single controlled operator ownership model. The accepted Core separately enforces same-World single-writer exclusion via a canonical World OS lease. The original persistence failure was environment destruction, not concurrent or hostile Git-ref mutation.

Requiring a general distributed multi-writer atomic CAS service is therefore outside this task's frozen failure model.

**Disposition: NON-BLOCKING HARDENING / OUT OF C15 RELEASE GATE.**

Corrective-003 still must prove ordinary single-writer crash semantics, including push-success/local-cache-loss recovery, but concurrent hostile ref mutation is not a release gate.

## Corrective-003 exact scope

Corrective-003 is READY and may fix only:

1. `C002-001` — authoritative remote checkpoint failure hard-stops the normal operator path;
2. `C002-002` — later-round K3/K5 remote-only crash recovery converges exactly once;
3. `C002-004` — remote-authoritative binding loss/corruption cannot silently downgrade to local-only.

It must preserve ordinary generation corruption checks already implemented.

It must not:

- modify `src/aios_core/**`;
- change product packaging to install `tools/c15_persistence`;
- introduce a second product truth store;
- build a generic distributed Git transaction subsystem;
- turn malicious coordinated storage mutation or concurrent hostile ref rewrites into new C15 release gates;
- run real Resident B;
- enter RELEASE-003.

## Historical preservation

Preserve without rewriting:

- RERUN-002 infrastructure-loss incident and retired identity;
- PR #216 / failed `63ca5923...`;
- PR #251 / failed `7b2556e7...`;
- historical author greens;
- historical reviewer `ACCEPTANCE_FAIL / 6`;
- local-only reviewer commit `fe881094fe13ee4420ffdf64a038e6aef77e85fe` as NOT PUSHED;
- all red attempt evidence that actually exists.

## Downstream

`C15-RCC-RES-B-RELEASE-003` remains BLOCKED until a fresh Independent Acceptance passes the narrowed Corrective-003 frozen-contract scope.

Resident B/C and semantic evaluation remain blocked.
