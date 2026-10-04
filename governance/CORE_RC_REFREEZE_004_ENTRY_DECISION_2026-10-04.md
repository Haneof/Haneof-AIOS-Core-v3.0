# CORE-RC-REFREEZE-004 — PM Entry Decision

Date: 2026-10-04

Live main at decision:
`5c4cc1b0c72c5fc6e866b07cee1fc46392734d59`

## Decision

`CORE-RC-REFREEZE-004 = READY`

`WINDOW 24 = RELEASED`

Unique next task:

`CORE-RC-REFREEZE-004`

## Rationale

Corrective-003 is PM-integrated and closes BLK-W20-001. The accepted integration merge is
`1cee3c5ad12f4b9098232bae11b51df786c5eb2f`.

The accepted Core change materially changes Resident-visible trusted-return/recovery semantics.
Historical RC-REFREEZE-003 governance establishes the correct ordering for such a change:
freeze the new accepted Core boundary first, independently accept that freeze, then adapt Resident
operator infrastructure against the frozen RC, and only then release a fresh Resident.

The known C15 persistence/operator failures remain downstream compatibility debt. They do not block
freezing the accepted Core boundary unless fresh RC verification demonstrates that they expose a real
Core contract regression.

Therefore the ordered path is:

1. Window 24 — CORE-RC-REFREEZE-004
2. Fresh Independent Acceptance of exact RC-REFREEZE-004 candidate
3. PM integration of accepted freeze
4. dedicated C15 operator/persistence compatibility corrective against the frozen RC
5. Fresh IA of operator corrective
6. Fresh Resident A only after explicit PM release

No Resident, C15 repair, evaluator, public release or hardware/UI work is authorized by this decision.
