# C15-RCC-HARDEN-DECISION-001 — Cognition Hardening Sequencing Ruling

> Status: PROPOSED — awaiting PM review
> Date: 2026-09-23
> Task ID: `C15-RCC-HARDEN-DECISION-001`
> Scope: sequencing only. No Core modification. No merge.
> Subject PR: #113 (`C15-RCC-EVIDENCE-POLICY-001`, review-remediated; supersedes #110)

---

## 0. What this document decides

One question:

> **Must `C15-RCC-EVIDENCE-POLICY-001` land on `main` BEFORE `C15-RCC-RES-A-RERUN-001` runs, or after?**

This document proposes: **BEFORE**.

This document does **not** authorize merge by itself. It is the sequencing
argument the independent review flagged as missing and left explicitly open. A PM
must accept or reject it.

---

## 1. Background

### 1.1 Current board state

| Row | Task | Status |
|---|---|---|
| 29.3 | `C15-RCC-RES-A-REPAIR-DECISION-001` | DONE — `PATH A = REJECTED`, `PATH B = REQUIRED` |
| 29.4 | `C15-RCC-RES-A-RERUN-001` | **READY** |
| 30 | `C15-RCC-RES-B-001` | BLOCKED |
| 31 | `C15-RCC-RES-C-001` | BLOCKED |

`C15-RCC-EVIDENCE-POLICY-001` has **no board row**. It exists only as
`Status: PLANNED` in `governance/C15_RCC_COGNITION_HARDENING_ROADMAP_2026-09-22.md`,
which states: *"This document records planned improvements. It does not authorize
implementation by itself."*

The roadmap's frozen execution order reads:

```
C15-RCC-COG-FIX-001 (DONE)
  -> C15-RCC-HARDEN-001
  -> C15-RCC-RES-A-RERUN-001
  -> C15-RCC-RES-B-001
  -> C15-RCC-RES-C-001
  -> C15-RCC-EVAL-001
```

Note that the roadmap **already places a hardening step before the A rerun**. The
board, written earlier, does not. This document reconciles the two and identifies
`C15-RCC-EVIDENCE-POLICY-001` as the concrete content of that hardening slot.

### 1.2 What PR #113 changes semantically

Before: the leaf-grounded evidence check ran **only** under
`WakeSource.COGNITIVE_DERIVATION`. Ordinary user turns, Periodic Review, and
direct service invocation had **no** such gate.

After: all four entrypoints pass the same mechanical resolver, and the resolver
cannot be bypassed by construction.

This is a change to what cognition a Resident is *able to form*. It is
Resident-visible.

---

## 2. Why hardening must precede the Resident A rerun

### 2.1 Reason 1 — Running A first guarantees a re-run

This is the decisive argument.

`C15-RCC-RES-A-RERUN-001` produces the **canonical** Resident A durable World.
Rows 30 and 31 consume it: B recovers from it, C takes it over. Per the board,
B "may start only after `C15-RCC-RES-A-RERUN-001` completes and the new A evidence
is independently accepted."

If A runs on current `main` and the evidence policy merges afterwards, then B and
C execute against a Core whose cognition-formation rules differ from the ones that
produced A's World. Concretely, A could legally form Claims that the post-merge
Core would reject. B and C would then inherit cognition that their own Core
considers ungrounded. Under `C15-RCC-RULE-001` §17, C15 PASS requires R1–R9 all
VALID, and an R8/R9 auditor examining that World would be entitled to ask why
durable cognition exists that the running Core would refuse to create.

The A rerun would then have to be discarded and repeated — the exact outcome
`C15-RCC-RES-A-REPAIR-DECISION-001` already forced once.

Merging first costs one window. Merging after risks the entire A/B/C chain.

### 2.2 Reason 2 — The defect is in the path C15 is designed to measure

C15's four RCC families are User Understanding, Relationship/Role,
Self/Calibration, and Strategy/Experience. Every one of them is formed through
`commit_claim` / `commit_ai_world_claim` / `revise_claim` / `retract_claim` on an
**ordinary user turn** or during **Periodic Review**.

Those are precisely the two entrypoints that had no grounding gate.

The `C15-RCC-RULE-001` matrix makes R9 (anti-self-proof) a required VALID axis,
with listed failure modes including "self-summary as proof" and "user fact
asserted from assistant speech". The remediation work produced a concrete,
executable demonstration that assistant-role speech could ground a durable
AI-world Claim on the unhardened path
(`tests/habitation/test_current_core_target.py`, now asserting the rejection).

Running A on a Core where R9 is not mechanically enforced, and then asking an
evaluator to rule R9 VALID, is not a sound gate. The evaluator would be grading
the model's restraint rather than the system's guarantee.

### 2.3 Reason 3 — The roadmap already ordered it this way

The hardening roadmap was written immediately after `C15-RCC-COG-FIX-001` and
placed `C15-RCC-HARDEN-001` **before** `C15-RCC-RES-A-RERUN-001`. The board's
row 29.4 `READY` status predates that roadmap.

Treating the board as authoritative here would execute the A rerun in a slot the
roadmap deliberately reserved for hardening. This document does not invent a new
ordering; it applies the one already frozen.

### 2.4 Reason 4 — Cost asymmetry

| Option | Cost if right | Cost if wrong |
|---|---|---|
| Harden first | one window of delay | A rerun starts one window later |
| Run A first | one window saved | A rerun invalidated; A+B+C repeated; C15 closure slips |

The downside is not symmetric.

---

## 3. Why this does not repeat the PR #101 problem

This is the objection that must be answered directly, because superficially both
cases are "a Core change landed near a Resident run".

### 3.1 What actually went wrong with PR #101

Per `reviews/C15_RCC_RES_A_REPAIR_DECISION_2026-09-22.md` and board row 29.3:

Resident A ran to cursor 13. **Afterwards**, `C15-RCC-WAKE-DELIVERY-FIX-001`
changed Wake assistant-output persistence. That fix altered **Phase A
Resident-visible inputs retroactively**: `sum0011` went from 6 to 8 sources, and
Periodic Review went from 18 to 20 anchors.

The ruling was `PATH A = REJECTED` / `PATH B = REQUIRED` because *"corrected
history changes actual summary/review source sets during Phase A, so old semantic
outputs are not historical-equivalent."*

The failure mode was: **a Resident run was already complete, and a later Core
change retroactively invalidated the inputs that run had seen.**

### 3.2 Why the present situation is structurally different

| Dimension | PR #101 failure | PR #113 proposal |
|---|---|---|
| Ordering | Core change landed **after** the Resident run | Core change lands **before** any Resident run |
| Retroactivity | Existing A World's inputs changed under it | No A World exists yet; nothing to invalidate |
| Affected artifact | A completed run's evidence became non-equivalent | No run, no evidence, no equivalence claim |
| Fixture | untouched in both cases | untouched — frozen C15 fixture SHA256 `7ccb309d...` not modified |
| Remedy required | discard and rerun | none |

The PR #101 problem was **retroactive input mutation**. The proposal here is
**prospective rule stabilization**. Landing a change before the run is the
*remedy* for the #101 failure mode, not a repetition of it.

### 3.3 The symmetric risk, stated honestly

There is a real risk on this side too, and it should be recorded rather than
argued away:

> If `C15-RCC-EVIDENCE-POLICY-001` merges and **another** cognition-semantics
> change is later found necessary, the A rerun is exposed to the #101 failure mode
> all over again.

This is why the proposal is not merely "merge #113". It is:

1. merge `C15-RCC-EVIDENCE-POLICY-001`;
2. **declare a cognition-semantics freeze** across the A/B/C window (§5);
3. only then start `C15-RCC-RES-A-RERUN-001`.

Without the freeze, the sequencing argument is incomplete.

### 3.4 What this change does not touch

Verified on the PR #113 candidate:

- frozen C15 fixture — **unmodified** (0 files under any fixture path)
- PR #101 — **untouched**, remains OPEN / UNMERGED / PINNED diagnostic evidence
- constitution and Fused Baseline Registry — **unmodified**
- `Claim` model, unified `WorldStore` — **unmodified**; no second cognition DB
- no Resident was run in the implementation or review windows

---

## 4. Evidence that the change is safe to land

| Gate | Result |
|---|---|
| `tests/integration/test_v3_c15_cognition_evidence_policy.py` | 16 passed |
| Full suite `pytest tests` | 452 passed, 0 failed |
| PR #113 CI | **42/42 checks pass** |
| Before-reproduction of the EventAnchor regression | recorded, executable |
| After-fix verification | recorded, executable |

Completion evidence: `reviews/C15_RCC_EVIDENCE_POLICY_001_COMPLETION_EVIDENCE.md`.

Specifically confirmed **not** regressed: P9 revision, C14 scheduler / runtime /
loop, P15 Periodic Review, P10 AI-world, P16 convergence, habitation harness.

---

## 5. Proposed ruling

**`C15-RCC-EVIDENCE-POLICY-001` SHOULD merge before `C15-RCC-RES-A-RERUN-001`,
subject to a cognition-semantics freeze.**

Conditions:

1. **Merge window.** `C15-RCC-EVIDENCE-POLICY-001` merges to `main` while row 29.4
   is still un-started. No Resident run may be in flight.

2. **Cognition-semantics freeze.** From that merge until `C15-RCC-EVAL-001`
   completes, no further change to cognition-formation semantics may land on
   `main`. Frozen surface:
   - `src/aios_core/policy/evidence.py`
   - `src/aios_core/writeback/**`, `src/aios_core/revision/**`,
     `src/aios_core/ai_world/**`
   - the four Claim capabilities in `src/aios_core/runtime/turn_runtime.py`
   - `src/aios_core/summaries/cognitive_derivation.py`

   A defect discovered inside this surface during A/B/C does **not** get a silent
   patch. It goes to a fresh PM decision window under the
   `C15-RCC-RES-A-REPAIR-DECISION-001` precedent, which must explicitly choose
   between accepting the defect for the current run or discarding and rerunning.

3. **Anchor recorded.** The A rerun records the exact post-merge `main` SHA as its
   Core anchor, so B, C, and the evaluator can prove all three ran on identical
   cognition semantics.

4. **Remaining roadmap items stay deferred.** `C15-RCC-COGNITION-FIELDS-001` and
   `C15-RCC-SCALE-BENCH-001` remain PLANNED and must not be folded into this
   window. They are inside the frozen surface and are therefore post-`C15-RCC-EVAL-001`.

5. **No merge on reviewer authority.** PR #113 stays OPEN pending PM acceptance of
   this ruling.

### 5.1 If the PM rejects this ruling

If the PM instead sequences the A rerun first, that is a legitimate call, but the
following must be recorded at the same time:

- `C15-RCC-EVIDENCE-POLICY-001` is deferred to **after** `C15-RCC-EVAL-001`, not
  to "some point during A/B/C" — landing it mid-chain is the #101 failure mode;
- the A/B/C chain will run on a Core where R9 anti-self-proof is **not**
  mechanically enforced on ordinary turns or Periodic Review, and the
  `C15-RCC-EVAL-001` evaluator must be told this explicitly so R9 is judged
  against the actual guarantee rather than an assumed one.

---

## 6. Proposed task board amendment

Insert as row **29.35**, between `C15-RCC-RES-A-REPAIR-DECISION-001` (29.3) and
`C15-RCC-RES-A-RERUN-001` (29.4):

| 顺序 | Task ID | 单窗口任务 | 状态 | Dependencies | 当前现场 / 证据 | 完成定义 |
|---:|---|---|---|---|---|---|
| 29.35 | `C15-RCC-EVIDENCE-POLICY-001` | 统一 ordinary turn / Periodic Review / Cognitive Derivation / direct service 四个入口的 cognition evidence 闭包规则；单一 policy 层，结构化不可绕过 | **GATE** | C15-RCC-COG-FIX-001 | PR #110 `REQUEST_CHANGES`（superseded）；PR #113 candidate `dc4f3de20efbf69d82ec6a88744793e7b35d9571`；`reviews/C15_RCC_EVIDENCE_POLICY_001_COMPLETION_EVIDENCE.md`；`governance/C15_RCC_HARDEN_DECISION_001_2026-09-23.md`；42/42 CI GREEN；full suite 452 passed | 四入口共用同一机械 resolver；`evidence_policy=None` 绕过已封闭；EventAnchor grounding 语义已裁决并双向测试；Observation/Action/Outcome/EventAnchor 合法路径正向测试齐全；Claim→Claim 与 Claim→Summary→Claim 仍拒绝；无 constitution/registry/fixture 改动；merge 需 PM 接受本 sequencing 裁决 |

Required amendment to row **29.4** `C15-RCC-RES-A-RERUN-001`:

- Dependencies: `C15-RCC-RES-A-REPAIR-DECISION-001` **+ `C15-RCC-EVIDENCE-POLICY-001`**
- Status: `READY` → **`BLOCKED`** until 29.35 is DONE
- 当前现场: add *"Core anchor = post-`C15-RCC-EVIDENCE-POLICY-001` main SHA; cognition-semantics freeze in effect through `C15-RCC-EVAL-001`."*

Rows 30 / 31 / 32 inherit the same Core anchor and freeze; no status change.

These amendments are **proposed**, not applied. Editing the board is a PM act.

---

## 7. Open items for PM

1. Accept or reject the BEFORE sequencing (§5).
2. Accept or reject the cognition-semantics freeze (§5.2) — the sequencing
   argument is incomplete without it.
3. Apply or decline the board amendment (§6).
4. Independently confirm the six adapted pre-existing tests
   (`reviews/C15_RCC_EVIDENCE_POLICY_001_TEST_ADAPTATION_REVIEW_2026-09-23.md`)
   are fixture repairs and not semantic weakening.

Until items 1–3 are ruled, PR #113 remains OPEN and unmerged.
