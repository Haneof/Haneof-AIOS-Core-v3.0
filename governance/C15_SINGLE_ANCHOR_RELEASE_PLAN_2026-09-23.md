# C15 Single Anchor Release Plan

## Purpose

Establish one canonical Core anchor for C15 Resident evaluation. Prevent multiple execution baselines from entering acceptance.

## Current finding

C15 has multiple historical evidence packages:

- PRE-HARDENING diagnostic Resident evidence: non-canonical.
- Final hardening governance anchor: `bcd6bf353126318f9a97076b52ec1740d43f35a4`.
- Later evidence package reports `anchor_commit=30e0dca1f08c49ed9bacc66b49313ac536d512af`; this requires provenance verification before acceptance.

## Canonical rule

Until provenance is resolved:

- Do not merge evidence-only Resident PRs.
- Do not start Resident B.
- Do not evaluate Resident A as canonical.

## Required audit

1. Verify ancestry:

`bcd6bf3 -> 30e0dca`

2. Verify semantic diff:

No changes allowed under:

- `src/aios_core/ai_world/**`
- `src/aios_core/runtime/**`
- `src/aios_core/revision/**`
- `src/aios_core/writeback/**`
- `src/aios_core/policy/**`

unless explicitly approved by new governance decision.

3. Establish final accepted anchor SHA.

## Development order after anchor lock

1. Anchor provenance audit
2. Resident A acceptance
3. Resident B recovery test
4. Resident C replacement-model test
5. C15 evaluator
6. C15 close

## Prohibited

- Multiple active canonical anchors
- Re-running on undocumented SHA
- Using evidence-only PR as a merge source
- Using previous Resident cognition as handoff
