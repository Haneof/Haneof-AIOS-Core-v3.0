# C15-RCC-COGNITION-SEMANTIC-FREEZE-001

Status: ACTIVE

Activated: 2026-09-23

Frozen Core anchor: `bcd6bf353126318f9a97076b52ec1740d43f35a4`

Activation evidence: `governance/C15_RCC_HARDENING_FINAL_ANCHOR_HANDOFF_2026-09-23.md`

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

Semantic freeze became ACTIVE when integrated C15 hardening created `bcd6bf353126318f9a97076b52ec1740d43f35a4`. The governance-only child `6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb` and the accepted Resident A evidence branch change no frozen Core file.

## Resident Requirement

Resident A, B, C and evaluation must execute against the same frozen Core anchor.
