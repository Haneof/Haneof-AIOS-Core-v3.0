# C15 Resident A Corrective-003 — PM Review Ready — 2026-09-29

## Status

```text
C15-RCC-RES-A-RERUN-004-CORRECTIVE-003
= PHASE_A_COMPLETE / REVIEW_READY

C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE
= READY

Persistence Corrective-003 / Resident B / Resident C / evaluator / C15 close
= BLOCKED_ON_FRESH_RESIDENT_A_ACCEPTANCE
```

This is PM readiness only. It is not Independent Acceptance PASS.

## Exact candidate

PR #296

- exact evidence head: `317316299c332d82e0cbd0431b5c7d50f391bc17`
- tree: `a64b60ad1e64bcb930003f030246baafdae3eb8a`
- sole parent / Resident-release main: `f7bcec4e558ebb4c6a11b7b45afe361cc659ef66`
- changed files: 212
- scope: one new Resident evidence package only

Evidence root:

`reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003/`

PR #296 must remain OPEN / UNMERGED / EVIDENCE-ONLY for acceptance.

## Mechanical readiness observed by PM

These are readiness observations, not semantic acceptance conclusions.

### Fresh identities

Run evidence declares:

- run: `c15-rcc-res-a-rerun-004-corrective-003-348cdba74f64`
- process: `231512c3-d418-45ab-b8f9-a81d68213959`
- Resident session: `resident-a-c003-49d55cd93f8341e7`
- conversation session: `sess-resident-a-c003-7089564bdf1d`
- subject: `user_1`

Pre-cursor freshness evidence reports no pre-existing World, index, exchange ledger or release-state.

### Frozen execution identity

Evidence reports exact accepted RC:

- software `f20f2edfa7af00d0286493fd15196ca9503bc315`
- repository tree `1ac3a675b884167d3a29aa432e7ef3eaff94d404`
- Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`
- Core content manifest `220718d6b5a2650b5e4263bbe8b7e661444cb33b486a7ecd7b5ad3d7d3399caa`

Accepted Operator Prep identity:

- exact harness head `77dac70e0cf054c3f0fb7d94a66dba221fe7d5de`
- packet SHA-256 `3c2d04c2de8557c3cb7329df4350c40b2ccc07520a7d3d51db206174b33266cc`
- harness manifest content `f3fbd788e3adb2ee600359e791273f87b444bc1991c7506d2683a643fd55a256`

Run runtime evidence reports:
- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2
- SQLite 3.45.1
- OpenSSL 3.0.13
- `aios_core.__file__` from the frozen RC checkout

### Cursor boundary

The package contains exactly event projections for cursor 1..13 and no cursor-14 event file.

Release-state mechanically reports:
- `last_acked_sequence = 13`
- `next_sequence = 14`
- `pending_reveal = null`
- 13 receipts

Session end states:
- cursor 14 revealed = false
- last acked event = `c15rcc-013`
- Phase-A cursors durably acked = 13

### World/index

Final evidence reports:
- World revision = 38
- index watermark = 38
- index lag = 0

World digest:
`0d6970ed99367a456e4baa29092bde8f15bc7544496095cc87ad9f029e2603b2`

Index digest:
`79c877a4bf75091fa90ae81076a6bdb2e265cf6376b657c3f195e9e91f9844e5`

Release-state digest:
`6b90fc7a09bce7d575dbcb783dcbe838cab81c2e358515adbb5dca9731f57c37`

### Durable model exchange

Evidence contains 21 requests and 21 responses.

Final exchange state reports:
- classification = `COMPLETE`
- requests complete = 21/21
- durable unconsumed = 0
- open dispatched = 0
- ledger records = 63
- chain integrity = PASS
- ledger head = `7f8afff395442a1d926144bfccb51429faf807490660fd95a9df65616ebba691`

Frozen exchange ledger digest:
`3b2b9e902133c31cc583491aae55834ee9cb71a9bea9ca50a36fd7e8b81da021`

### Restart/confirmation evidence

After cursor 13, the package includes a confirmation due-work run from the frozen state. It reports:
- World revision unchanged at 38
- index watermark 38
- exchange recovery classification COMPLETE
- no handoffs
- no further semantic output required

### Package freeze

`SHA256SUMS` lists 211 files, covering every other file in the 212-file evidence package.

PR description reports SHA-256 of the `SHA256SUMS` file:
`1eee5df0650ed03b50bfe0ef558d93076d13ecb32772b036c91b9d8cd8c84bef`

Session end pins freeze-manifest SHA-256:
`bc66ad55e0dc8dbdb483e644f850c4c4753ae6ba45ba400cbda3b28071f89298`

Repository mechanical check on exact candidate:
`c15-rcc-fixture-mechanical-gate = success`.

## What PM has not accepted

PM readiness does not determine:
- whether every semantic decision was genuinely made by the current Resident rather than scripted;
- whether prior-run/governance/future semantic material leaked into any request;
- whether all due Wake/Review/Summary/derivation work is complete;
- whether every cognition object is evidence-grounded and semantically reasonable;
- whether USER replies and durable cognition are free of unsupported completion claims;
- whether event-time causality and temporal isolation are fully correct.

Those are binding Independent Acceptance responsibilities.

## PM readiness disposition

PR #296 is sufficiently complete for fresh role-separated Independent Acceptance.

No Persistence/B/C/evaluator work is released by this note.
