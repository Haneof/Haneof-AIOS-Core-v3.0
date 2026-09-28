# C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-002 — PM REVIEW_READY Writeback

- Date: 2026-09-28
- Role: C15 Governance PM
- Scope: review-ready governance writeback only. No PR #251 implementation change, no Independent Acceptance, no Resident B, no RELEASE-003.
- Pre-writeback live main: `bce933f851740f4d697eacb2519ec53133823f00`

## Exact engineering candidate

- Engineering PR: #251
- State: OPEN / DRAFT / UNMERGED
- Tested exact head: `7b2556e738d9c9386ec21c13fec39400c87d0916`
- Review-ready handoff comment: `5862099546`
- Historical failed candidate remains PR #216 @ `63ca592359c7e3fd71d6cc4ba349949e4f0b80e3`
- `src/aios_core/**` diff versus live main: zero

## Corrective scope

The engineering candidate addresses only the two source-confirmed blockers from Corrective-001 IA:

1. `IA-BLK-PERSIST-001`: remote authoritative persistence is integrated into the normal `OperatorSession` K1-K5 durability path. Before each frozen kill barrier can fire, recoverable state is synchronously published to the configured remote backend. Focused regression destroys the entire local backend after SIGKILL and resumes from a fresh directory using only remote state. ACK is also remotely persisted. Remote writes use expected-head compare-and-swap to reject stale writers.

2. `IA-BLK-PERSIST-002`: `RunBackend.open()` and reattach admission verify the complete sealed-generation chain. Continuity, durable generation high-water mark, seal presence, manifests and artifact hashes are checked. Missing, modified, incomplete or unsealed generations fail closed; silent reconstruction is prohibited.

No Resident semantic logic and no `src/aios_core/**` implementation were changed.

## Exact-head engineering evidence

All results below are on exact candidate `7b2556e738d9c9386ec21c13fec39400c87d0916`:

- Corrective-002 formal run `36368777970 = SUCCESS`
  - CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1
  - Corrective-002 focused suite: 9/9 PASS
  - remote-only K1-K5 total-local-cache-loss recovery: 5/5 PASS
  - stale-writer CAS rejection: PASS
  - deleted / modified / incomplete sealed-generation rejection: PASS
  - historical K1-K5: 5/5 PASS
  - production wiring: 16/16 PASS
  - environment / remote reattach: 4/4 PASS
  - resident-visible surface: 1/1 PASS
  - historical journal under frozen unittest contract: 13/13 PASS
  - frozen Debian 12 E2E: 158/158 PASS
  - lifecycle mutation-red: 82 cases PASS
- Historical persistence formal run `36368778044 = SUCCESS`
- Core RC full-suite `36368777989 = SUCCESS`
  - broad pytest: 798 tests / 0 failures / 0 errors / 0 skipped
  - focused authenticity / recovery / headless / scale / writer: PASS
- P16 convergence `36368778066 = SUCCESS`
- Core scale `36368777955 = SUCCESS`
- Core headless `36368778005 = SUCCESS`
- World-kernel `36368778004 = SUCCESS`

## Preserved red history

No failed attempt is rewritten:

- `29fc503a9dcb88bcd59f428232946c9989289a39`: broad full-suite exposed inherited hard-coded `/home/user` portability.
- `f88776a8d784df23df826b827bdc3c488c574079`: broad Core/P16 exposed sudo HOME drift and pytest collection of the frozen unittest-only journal suite.
- Final exact `7b2556e7...` fixes those execution-environment compatibility issues without modifying the frozen historical journal test bytes.

These author gates are engineering evidence only and do not constitute acceptance.

## Governance disposition

```text
C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-002
= REVIEW_READY / AWAITING_INDEPENDENT_ACCEPTANCE

C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE
= READY
```

This Independent Acceptance is the sole next READY task.

Still BLOCKED:

- `C15-RCC-RES-B-RELEASE-003`
- `C15-RCC-RES-B-RERUN-003`
- `C15-RCC-RES-B-ACCEPT-003`
- Resident C
- C15 semantic evaluator
- closure

PR #251 must remain unmerged until fresh Independent Acceptance and subsequent PM disposition.
