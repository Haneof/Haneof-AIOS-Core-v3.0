# C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-002 — Independent Acceptance Failure Adjudication

- Date: 2026-09-28
- Role: C15 Governance PM / IA Disposition Reviewer
- Scope: source revalidation + governance disposition only. No PR #251 implementation change, no persistence-state mutation, no corrective implementation, no Resident B, no RELEASE-003.
- Pre-writeback live main: `3d4052b617f392f24b6da12a14c090c39a918442`

## Final adjudication

```text
C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE
= DONE / ACCEPTANCE_FAIL / blocker=6

C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003
= READY
```

Failed tested exact candidate:

`7b2556e738d9c9386ec21c13fec39400c87d0916`

PR #251 remains OPEN / DRAFT / UNMERGED / PINNED. This SHA is permanently recorded as a FAILED EXACT CANDIDATE and must never be replaced in historical acceptance records by a later corrective SHA.

## Reviewer evidence disposition

Reviewer reported a formal independent suite under CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2:

- rev2: 30 RED initially; adjudicated 23 real contract violations + 7 reviewer-harness/non-blocking cases
- rev2 + supplemental rev3/rev4: 147 probes, raw 112 PASS / 35 FAIL
- six root-cause blockers after deduplication
- applicable full regression: 798/798 PASS
- focused regression: 35/35 PASS
- historical journal: 13/13 PASS
- frozen Debian 12 E2E: 158/158 PASS
- lifecycle mutation-red: 82 cases PASS

The reviewer created local-only evidence commit `fe881094fe13ee4420ffdf64a038e6aef77e85fe`, but remote push failed because GitHub write credentials were unavailable. **No remote review branch/PR exists for that final evidence.** The local commit, bundle and local report are therefore not cited as remote evidence.

PM accepts the six blockers because their mechanisms were independently revalidated against exact candidate source, with the runtime-specific recovery failures additionally reported as reproduced in the formal reviewer environment.

## Blockers

### IA-BLK-PERSIST-C002-001 — K4 remote failure is not fail-closed

`OperatorSession._capability_handler()` writes the capability idempotency/result ledger and increments its side-effect counter, then performs the K4 remote persistence barrier. The registered capability is invoked through Core `CapabilityRegistry.invoke()`, which catches ordinary handler exceptions and converts them into `CAPABILITY_EXECUTION_ERROR`. A remote-persistence exception therefore need not terminate the enclosing turn; the required remote barrier can fail while model/provider flow continues.

### IA-BLK-PERSIST-C002-002 — second-round K3 / K5 fallback recovery gap

The K3 barrier is persisted after request stage/expose/outbox bookkeeping and before provider reply collection. Reviewer formal probes reproduced that an authoritative snapshot at a later model round cannot reliably converge after complete local loss. A K5 crash after local Git commit creation but before remote push leaves the prior remote authoritative state and can fall back into the same unresolved later-round recovery condition. The exact candidate therefore does not establish remote-only convergence for every required crash window.

### IA-BLK-PERSIST-C002-003 — generation admission still accepts coordinated/history tampering

`GenerationStore.verify()` requires only that `.sealed` exists; it does not validate the seal contents against generation identity. It verifies manifest-declared artifacts but does not reject unexpected files. `verify_all()` derives expected history high-water from the current mutable relay journal ledger. Coordinated lowering of that ledger together with deletion of tail generations can therefore present a shorter internally-consistent history and pass the current checks. This violates the frozen fail-closed immutable-history requirement.

### IA-BLK-PERSIST-C002-004 — remote durability config can disappear and silently downgrade

`_load_remote_durability()` returns `False` if `remote-durability.json` is missing. Normal `attach()/resume()` can then proceed with `_remote_ref=None`, turning the remote barrier into a no-op and allowing local-only progress/ACK. A run established as remote-authoritative must not silently downgrade when its remote-binding metadata is missing.

### IA-BLK-PERSIST-C002-005 — remote ref is not bound to run identity

The persisted remote config contains `remote_ref` and `remote`, but no immutable binding that proves the ref equals the canonical ref for backend owner `run_id`. `push_run_state()` accepts a supplied ref and uses owner `run_id` only for message/default-ref construction. With a copied config and matching expected-head marker, one run's backend tree can be written to another run's authoritative ref. Cross-run persistence must fail closed.

### IA-BLK-PERSIST-C002-006 — remote CAS is check-then-push, not atomic

`push_run_state()` first reads the ref with `ls-remote`, compares it to the local expected head, creates a commit, and later executes ordinary `git push <commit>:<ref>`. There is no atomic expected-old-value lease. If the ref is deleted or rolled back after the check, the later push can succeed instead of reporting a stale-writer/CAS conflict. The authoritative ref update must use an atomic server-enforced compare-and-swap/lease.

## Preserved green evidence

The following exact-candidate engineering results remain truthful historical evidence and are not relabeled red:

- Corrective-002 formal `36368777970 = SUCCESS`
- historical persistence formal `36368778044 = SUCCESS`
- Core RC full-suite `36368777989 = SUCCESS` (798/0/0/0)
- P16 `36368778066 = SUCCESS`
- Core scale `36368777955 = SUCCESS`
- Core headless `36368778005 = SUCCESS`
- world-kernel `36368778004 = SUCCESS`
- `src/aios_core/**` zero diff

The IA establishes blind spots outside those author gates; it does not falsify the recorded runs.

## Corrective-003 frozen scope

`C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003` is the sole next READY task. It may repair only the six blockers:

1. K4 and every durability barrier must propagate remote persistence failure as a hard operator stop; capability/result wrapping must not swallow durability failures.
2. Every later-round K3 and K5 crash window must be recoverable from remote authoritative state alone with exactly-once convergence.
3. Generation admission must authenticate the complete immutable history, including seal contents, exact artifact set, and a high-water/history commitment that cannot be consistently shortened by mutating the current ledger.
4. Remote-authoritative runs must require durable remote binding metadata; missing/corrupt config must fail closed, never downgrade local-only.
5. Remote binding must bind owner run/session identity to the canonical ref and reject cross-run config/ref transplantation.
6. Ref update must be server-enforced atomic CAS/lease against the exact expected old head, including rollback/delete races.

All historical candidates, red evidence, author greens, and PR #251 must remain preserved. No Resident B execution is authorized.

## Downstream disposition

Still BLOCKED:

- `C15-RCC-RES-B-RELEASE-003`
- `C15-RCC-RES-B-RERUN-003`
- `C15-RCC-RES-B-ACCEPT-003`
- Resident C
- C15 semantic evaluator
- closure
