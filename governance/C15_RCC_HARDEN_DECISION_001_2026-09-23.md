# C15-RCC-HARDEN-DECISION-001

Status: APPROVED

## Decision

C15 cognition hardening MUST precede C15-RCC-RES-A-RERUN-001.

Execution order:

```
C15-RCC-HARDEN-001
        |
        v
Semantic Freeze
        |
        v
C15-RCC-RES-A-RERUN-001
        |
        v
Resident B
        |
        v
Resident C
        |
        v
C15-RCC-EVAL-001
```

## Rationale

Resident A must run only after cognition formation semantics are stabilized. A later change to evidence policy, Claim semantics, revision semantics, or cognition fields would invalidate Resident-visible evidence in the same class of failure as the PR #101 repair decision.

The hardening integration is a prospective rule freeze, not a historical repair.

## Integration Rule

PR #111 and PR #113 are one hardening unit and must produce one final Core anchor SHA before Resident execution.

## Governance Constraint

This document authorizes sequencing only. Code changes remain governed by their own PR review and gates.
