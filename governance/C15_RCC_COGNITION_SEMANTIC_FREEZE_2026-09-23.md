# C15-RCC-COGNITION-SEMANTIC-FREEZE-001

Status: READY FOR ACTIVATION AFTER C15 HARDENING MERGE

## Purpose

Freeze Resident-visible cognition semantics before Resident A/B/C execution.

## Frozen Scope

- Evidence Policy
- AI World Claim semantics
- Revision semantics
- Cognition fields:
  - valid_time
  - unknown_items
  - counter_evidence
- Runtime cognition entry paths

Affected areas:

- src/aios_core/policy/evidence.py
- src/aios_core/ai_world/**
- src/aios_core/revision/**
- src/aios_core/writeback/**
- cognition capabilities in src/aios_core/runtime/turn_runtime.py
- src/aios_core/summaries/cognitive_derivation.py

## Freeze Rule

After activation, no cognition-semantic change may enter main before C15-RCC-EVAL-001 without a new governance decision.

## Activation Condition

Semantic freeze becomes ACTIVE when the integrated C15-RCC-HARDEN-001 merge creates the final Core anchor SHA.

## Resident Requirement

Resident A, B, C and evaluation must execute against the same frozen Core anchor.
