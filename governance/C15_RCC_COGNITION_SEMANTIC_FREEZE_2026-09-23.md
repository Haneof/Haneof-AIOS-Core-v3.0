# C15 Cognition Semantic Freeze

> Status:
> **ACTIVE AFTER MERGE OF C15 COGNITION HARDENING**
> Task: `C15-RCC-SEMANTIC-FREEZE-001`
> Date: 2026-09-23
> Started from main: `e534378572e886f76071ac0dcf59a9a1a4798bb9`
> Scope: governance anchor only. No Core modification. No merge. No test modification.
> Authority: sequencing control derived from `C15-RCC-RULE-001` (continuity ruling), the `C15-RCC-COGNITION-HARDENING-ROADMAP` frozen execution order, and the `C15-RCC-RES-A-REPAIR-DECISION-001` precedent. This file is **not** a constitution, not an amendment chain, and not a registry.

---

## 0. Purpose

C15 Resident A/B/C must run on **stable cognition semantics**.

The freeze is **not permanent**.

Its target is narrow: prevent the situation in which a Resident has already
formed cognition, and then the Core's cognition semantics change, making the
historical evidence no longer comparable to what the later Resident runs
produce. That is exactly the failure that invalidated the first Resident A
attempt:

- `C15-RCC-WAKE-DELIVERY-FIX-001` (PR #101) landed **after** Resident A had run;
- its source-set changes (`sum0011` 6 → 8 sources; Periodic Review 18 → 20
  anchors) made the completed A World no longer historical-equivalent to the
  Core it was produced on;
- ruling `C15-RCC-RES-A-REPAIR-DECISION-001` closed it as
  `PATH A = REJECTED`, `PATH B = REQUIRED` — the run had to be redone.

The hardening work in PR #113 is the inverse case: it lands **before** any
Resident run exists, so there is nothing to invalidate. This document is what
keeps it that way for the entire A/B/C window.

### Activation anchor

This document exists now, committed alongside the hardening candidate, but it
becomes **ACTIVE** only at the merge of the C15 cognition hardening (PR #113,
candidate `a00e39796f2f34ea6a598653fe274f9354ab4d5b`, subject
`C15-RCC-EVIDENCE-POLICY-001`). At that merge the PM must record the resulting
`main` SHA as the **Core anchor** in board rows 30/31/32 (Resident A/B/C). While
the freeze is ACTIVE, every Resident run and every evaluator comparison must
verify that the Core in use is exactly that anchor, or an explicitly
PM-approved exception (Section 5).

---

## 1. Freeze Status

```
Status:
ACTIVE AFTER MERGE OF C15 COGNITION HARDENING

Purpose:
Protect Resident continuity evaluation from semantic drift.
```

Preconditions recorded at authoring time (2026-09-23):

| Item | State |
|---|---|
| `C15-RCC-COG-FIX-001` (PR #108, `c146cebbdfa8ac714fc236652a4452c60bcfa0bb`) | merged on `main` |
| PR #113 (`C15-RCC-EVIDENCE-POLICY-001`, candidate `a00e397`) | technically passed independent review; **open, unmerged**, awaiting this governance anchor and the PM sequencing ruling |
| `C15-RCC-HARDEN-DECISION-001` (sequencing, BEFORE-order) | PROPOSED, awaiting PM review |
| `C15-RCC-RES-A-RERUN-001` | **not started**; board row 29.4 still reads `READY` (to be amended by PM under the sequencing ruling) |

---

## 2. Freeze Scope

While ACTIVE, the following surfaces are frozen. "Frozen" means: no merge into
`main` that changes the listed semantics, by any path (PR, hotfix, governance
action), except through the Change Exception (Section 5).

### 2.1 Evidence Policy

`src/aios_core/policy/evidence.py`

Frozen:

- grounding rules (how cognition references must terminate);
- reality leaf rules (USER / SENSOR / PLATFORM / SAFETY termination);
- container semantics (transparent containers vs. case containers;
  EventAnchor and Experience objects as containers, never as leaves);
- anti-self-proof rules (AI Claim / Summary / Case objects cannot be the sole
  grounding; `MIXED` lineage still requires a reality leaf).

### 2.2 AI World Cognition Semantics

`src/aios_core/ai_world/**`

Frozen:

- Claim meaning (what an AI-world Claim asserts, and what its `evidence_refs`
  must support);
- AI World domain semantics (`USER_UNDERSTANDING`, `RELATIONSHIP`, `AI_SELF`,
  `USER_GOALS`);
- Self / Calibration / Strategy semantics (subject routing to
  `AI_SELF_SUBJECT_ID`; calibration and strategy Claim behaviour).

### 2.3 Revision Semantics

`src/aios_core/revision/**`
`src/aios_core/writeback/**`

Frozen:

- forward revision (revision creates a new revision, history preserved,
  `stale_due_to_refs` provenance);
- retract semantics (forward tombstone semantics, history never deleted);
- dependency propagation (stale marking of dependents,
  `STATUS_REVIEW_REQUIRED`, skip-already-advanced, Summary staleness and
  rebuild).

### 2.4 Cognition Fields

`valid_time`, `unknown_items`, `counter_evidence`
(`counter_evidence_set_refs`)

These are the fields of the deferred task `C15-RCC-COGNITION-FIELDS-001`.
**After that task merges, these fields are part of the Resident-visible
cognition contract** and are frozen by this document: their meaning, their
formation, and their persistence may not change mid-chain.

Consequence for sequencing (recorded, decided by PM under
`C15-RCC-HARDEN-DECISION-001`): because the fields task modifies
`commit_ai_world_claim` / `revise_claim` / `retract_claim` / `read_ai_world` /
snapshot views, it **cannot merge while the freeze is ACTIVE**. It must either
land as part of the cognition hardening gate **before** the freeze activates, or
wait until after the freeze lifts (post `C15-RCC-EVAL-001`). The same applies
to `C15-RCC-SCALE-BENCH-001`, whose roadmap entry touches the same surfaces.
Either ordering is legitimate; the PM sequencing ruling selects which.

### 2.5 Runtime Cognition Entry Points

`src/aios_core/runtime/turn_runtime.py`
`src/aios_core/summaries/cognitive_derivation.py`

Frozen:

- commit claim (all four Claim capabilities);
- revise claim;
- retract claim;
- evidence validation (the single `CognitionEvidencePolicy.validate` path
  shared by ordinary turns, Periodic Review, and Cognitive Derivation —
  including the absence of any wake-source bypass and any
  `evidence_policy=None` bypass).

### 2.6 Explicitly out of scope of the freeze

To prevent over-freezing, the freeze covers **cognition semantics only**:

- Resident fixtures and sessions (they are already frozen by
  `C15_RESIDENT_COGNITIVE_CONTINUITY_TEST_PLAN`);
- non-cognition Core modules (wake, memory, storage, index) — unless a defect
  in them requires touching a frozen path, in which case Section 5 applies;
- new governance documents, board rows, and evaluation tooling for
  `C15-RCC-EVAL-001`;
- adding **new** tests for the frozen surface is permitted only if they
  neither change nor weaken existing assertions; changing existing test
  expectations for frozen behaviour is a semantic change and is not permitted.

---

## 3. Freeze Rules

While ACTIVE, the following are prohibited without a PM governance decision:

1. Modify cognition evidence closure (any change to what counts as
   leaf-grounded, container, or self-proof).
2. Modify Claim semantics (AI-world Claim meaning, domain semantics, Self /
   Calibration / Strategy semantics).
3. Modify any Resident-visible cognition formation path (ordinary turn,
   Periodic Review, Cognitive Derivation, writeback, revision, or the
   derivation scheduler's delegation).
4. Modify revision meaning (forward revision, retract/tombstone, dependency
   propagation).
5. Modify AI self / calibration semantics (subject routing, calibration and
   strategy Claim behaviour).

A change that only adds observability (logging, metrics) without altering any
of the above is not a semantic change, but it still requires PM acknowledgment
in the exception record if it touches a frozen file.

---

## 4. Change Exception

If, during the freeze, one of the following is found:

- correctness blocker (the frozen surface is provably wrong in a way that
  corrupts Resident cognition);
- security issue;
- data corruption (World/index state that the frozen code produces or
  consumes is unrecoverably damaged);

then:

- a **new PM governance decision** must be created (new task ID under the C15
  RCC series), stating the defect, the minimal semantic delta, and the impact
  on every Resident run already executed or in flight;
- **direct patching of `main` is prohibited.** The decision precedes the
  change; the change never precedes the decision;
- if the defect is found **after** a Resident has already run on the affected
  semantics, the `C15-RCC-RES-A-REPAIR-DECISION-001` precedent applies: the
  PM decides between verified historical persistence and a fresh-World rerun,
  and the affected board rows are re-anchored to the new Core SHA.

The bar is intentionally high: the freeze exists precisely because one
unsequenced change already cost a full Resident A rerun.

---

## 5. Duration

- **Start:** after the merge of the C15 cognition hardening — i.e. the moment
  PR #113 (`C15-RCC-EVIDENCE-POLICY-001`) and any other PM-included hardening
  tasks are merged into `main`, and the PM has recorded the Core anchor SHA.
- **End:** completion of `C15-RCC-EVAL-001` (PM closes the evaluator's
  semantic audit of R1–R9 and issues the final C15 verdict).

Until the end condition is met, no frozen-surface change may land, regardless
of how correct or urgent it appears. After `C15-RCC-EVAL-001` completes, this
document is archived as the historical anchor for that evaluation, and the
frozen surfaces may be changed again through normal PM-governed sequencing.

---

## 6. Sequencing Context

Recorded execution order:

```
C15-RCC-COG-FIX-001
        |
        v
C15-RCC-HARDENING            (PR #113 + PM-included hardening tasks)
        |
        v
Semantic Freeze              (this document — ACTIVE)
        |
        v
C15-RCC-RES-A-RERUN-001
        |
        v
Resident B                   (C15-RCC-RES-B-001)
        |
        v
Resident C                   (C15-RCC-RES-C-001)
        |
        v
C15-RCC-EVAL-001             (independent evaluator; freeze lifts after closure)
```

This ordering exists to avoid the PR #101 class of problem: historical
Residents having already run, then the Core cognition semantics changing under
them. Concretely:

- hardening **before** A: nothing to invalidate;
- freeze **around** A/B/C: nothing can be invalidated, except through a PM
  decision that explicitly re-anchors and, if needed, reruns;
- evaluator **after** C: R1–R9 are judged against one stable, documented
  cognition baseline, so `VALID` is a meaningful verdict rather than a
  comparison between three different Core semantics.

If the PM rules that Resident A must run **before** the hardening merge (i.e.
rejects the BEFORE-order in `C15-RCC-HARDEN-DECISION-001`), this freeze
document does not apply, and the rejection must be recorded together with the
consequence that axis R9 (anti-self-proof) was not mechanically enforced
during A/B/C — per the rejection branch of
`C15-RCC-HARDEN_DECISION_001` §7.

---

## 7. Verification

The evaluator (or any PM audit) may verify the freeze held by:

1. reading the Core anchor SHA recorded in board rows 30/31/32;
2. confirming that no merge between the anchor and the end of
   `C15-RCC-EVAL-001` touched a Section 2 file, or that every such merge
   carries a Section 4 exception document;
3. confirming that no Section 2 file was modified by a change that does not
   cite a `C15-RCC-*` task ID.

Any failure of the three checks is a governance breach: it does not by itself
invalidate the Resident runs, but it must be recorded in the
`C15-RCC-EVAL-001` verdict as a comparison-validity caveat.

---

## 8. Completion

- This document is the **only** artifact of `C15-RCC-SEMANTIC-FREEZE-001`.
- It does not merge anything. It does not amend the task board (board
  amendment is the PM act under `C15-RCC-HARDEN-DECISION-001`).
- It takes no effect until the PM completes the sequencing ruling and the
  hardening merge.
