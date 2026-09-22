# C15 RCC Cognition Hardening Roadmap

Date: 2026-09-22

## Purpose

Record deferred Resident Cognitive Continuity hardening work after `C15-RCC-COG-FIX-001`, so future windows do not lose identified optimization items.

This document records planned improvements. It does not authorize implementation by itself.

---

## Completed baseline

### C15-RCC-COG-FIX-001 — DONE

Main merge:

- SHA: `c146cebbdfa8ac714fc236652a4452c60bcfa0bb`
- PR: #108

Delivered:

1. AI-world cognition revision routing

`revise_claim` and `retract_claim` now route AI-world Claims through the existing typed `AIWorldCognitionService` path.

Affected continuity families:

- Self
- Calibration
- Intent
- Cognitive Boundary
- Personality

2. Core cognition recovery protection

`core_context()` now filters `core_context` tagged cognition before applying limits.

This prevents active long-term cognition from being silently excluded by later ordinary cognition accumulation.

---

# Deferred hardening tasks

## C15-RCC-EVIDENCE-POLICY-001

Status: PLANNED

Goal:

Unify evidence support rules for durable cognition creation across:

- ordinary user turns
- Periodic Review
- Cognitive Derivation

Current concern:

Different entry paths currently apply different levels of evidence closure.

Target:

Create one cognition evidence validation policy layer while preserving legitimate differences between cognition opportunities.

Required properties:

- prevent Claim -> Summary -> Claim self-confirmation loops
- preserve reality leaf grounding requirements
- keep AI Claim revisable
- keep UNKNOWN legal

---

## C15-RCC-COGNITION-FIELDS-001

Status: PLANNED

Goal:

Expose existing Claim temporal and uncertainty fields through the AI cognition capability path.

Fields:

- `valid_time`
- `counter_evidence_set_refs`
- `unknown_items`

Affected paths:

- commit_ai_world_claim
- revise_claim
- retract_claim
- read_ai_world
- snapshot/context views

Purpose:

Allow conditional cognition instead of over-generalized permanent conclusions.

Example:

Instead of:

> User prefers short replies.

Support:

> During high-pressure project periods, user tends to prefer shorter replies; other contexts remain uncertain.

---

## C15-RCC-SCALE-BENCH-001

Status: PLANNED

Goal:

Measure cognition retrieval performance before architectural changes.

Benchmark sizes:

- 10k world records
- 100k world records
- 1M world records

Measure:

- core_context latency
- snapshot latency
- recall candidate query count
- P95 runtime overhead
- context token growth

Only after measurements should retrieval/index/cache architecture changes be considered.

---

# Frozen execution order

```
C15-RCC-COG-FIX-001
        DONE
          |
          v
C15-RCC-HARDEN-001
        |
        v
C15-RCC-RES-A-RERUN-001
        |
        v
C15-RCC-RES-B-001
        |
        v
C15-RCC-RES-C-001
        |
        v
C15-RCC-EVAL-001
```

Resident execution should only use the fixed Core baseline after required hardening decisions are complete.
