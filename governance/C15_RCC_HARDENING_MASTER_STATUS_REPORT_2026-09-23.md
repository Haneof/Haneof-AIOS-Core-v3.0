# C15 Cognition Hardening Arc — Master Status Report

> Status: **GOVERNANCE STATUS REPORT**
> Date: 2026-09-23
> Started from main: `e534378572e886f76071ac0dcf59a9a1a4798bb9`
> Scope: end-to-end status of the C15 cognition-hardening arc, merge-readiness
> assessment, and the PM action list. Documents and findings only. No Core
> modification. No merge. No Resident fixture change.
> Evidence standard: every technical claim below is re-derivable from a cited
> command, diff, or executable probe. Author explanations were disregarded
> wherever a mechanical check was possible.

---

## 1. Executive summary

The C15 cognition hardening is **technically complete on both PRs and
governance-anchored**, but it is **not yet mergeable as two independent PRs**:
PR #113 and PR #111 diverge from the same `main` base and modify the **same
four source files**, so neither merge order applies cleanly (verified: both
orders produce content conflicts in all four files). They must land as **one
integrated hardening merge**.

- **Resident A has not started.** Nothing has been invalidated; this is still
  the pre-run window in which the PR #101 failure class is preventable.
- The semantic freeze anchor (`C15-RCC-SEMANTIC-FREEZE-001`) is written and
  committed; it activates at the integrated hardening merge.
- The sequencing ruling (`C15-RCC-HARDEN-DECISION-001`) is proposed; the PM
  ruling and board amendment are outstanding.
- The single new blocker to merge is the **#111/#113 integration** (an
  engineering act) plus its post-integration verification.

**Bottom line for the PM:** rule on sequencing → amend the board → commission
the #111+#113 integration → delta-review the integrated head → merge the
integrated hardening → record the Core anchor → unblock Resident A.

---

## 2. State snapshot (verified 2026-09-23)

| Item | State | Evidence |
|---|---|---|
| `main` | `e534378572e886f76071ac0dcf59a9a1a4798bb9` | `git log origin/main` |
| `C15-RCC-COG-FIX-001` (PR #108) | **merged** at `c146cebbdfa8ac714fc236652a4452c60bcfa0bb` | `compare c146ceb...main` → ahead 1, behind 0 |
| PR #113 `C15-RCC-EVIDENCE-POLICY-001` | OPEN, head `4d421ef`, MERGEABLE, **42/42 CI pass** | `gh pr view 113`, `gh pr checks 113` |
| PR #111 `C15-RCC-COGNITION-FIELDS-001` | OPEN, head `abb85e0`, MERGEABLE, **27/27 CI pass** | `gh pr view 111`, `gh pr checks 111` |
| #111 vs `main` | 1 commit ahead, 0 behind | `compare e534378...abb85e0` |
| #111 vs #113 head | **diverged** (ahead 1 / behind 4) | `compare 4d421ef...abb85e0` |
| `C15-RCC-HARDEN-DECISION-001` | PROPOSED, awaiting PM | doc line 3 |
| Semantic freeze doc | created, committed; **inactive until hardening merge** | `4d421ef` + amendment |
| Board row 29.4 `C15-RCC-RES-A-RERUN-001` | `READY` (stale — should be `BLOCKED` pending gate) | task board |
| Resident A | **not started** | no A-rerun rows in evidence |

Both PRs sit under the `C15-RCC-HARDEN-001` umbrella: the hardening roadmap's
frozen execution order places `C15-RCC-HARDEN-001` between
`C15-RCC-COG-FIX-001` and `C15-RCC-RES-A-RERUN-001`, and the roadmap's deferred
hardening tasks are exactly `C15-RCC-EVIDENCE-POLICY-001` (#113),
`C15-RCC-COGNITION-FIELDS-001` (#111), and `C15-RCC-SCALE-BENCH-001` (no PR yet).

---

## 3. Completed deliverables (this arc)

| Deliverable | Artifact | Commit |
|---|---|---|
| Independent review of PR #110 | verdict REQUEST_CHANGES (2 BLOCKER / 3 MAJOR / 2 MINOR) | (prior session) |
| Remediation of all findings | `C15-RCC-EVIDENCE-POLICY-001` implementation + completion evidence | `368f1ad`, `dc4f3de` |
| Sequencing ruling | `governance/C15_RCC_HARDEN_DECISION_001_2026-09-23.md` (PROPOSED) | `a00e397` |
| Six-test adaptation review | `reviews/C15_RCC_EVIDENCE_POLICY_001_TEST_ADAPTATION_REVIEW_2026-09-23.md` | `a00e397` |
| Independent semantic review of PR #113 | verdict REQUEST_CHANGES (2 BLOCKER: freeze, board; §6 reviewer-independence MAJOR) | (prior turn) |
| Cognition semantic freeze anchor | `governance/C15_RCC_COGNITION_SEMANTIC_FREEZE_2026-09-23.md` | `4d421ef` (+ this report's amendment) |
| **Master status report** | this document | (this commit) |

---

## 4. Technical verification results (PR #113)

All three review-scope areas PASS, re-derived mechanically:

### 4.1 EventAnchor grounding semantics — PASS

- EventAnchor is a **legal grounding container, not a reality leaf**: it is in
  `_CASE_GROUNDING_CONTAINERS`, not `_TRANSPARENT_GROUNDING_CONTAINERS`; it
  stays `AI_COGNITION` and never enters `grounding_leaf_refs`.
- Executable probes on candidate `a00e397`:
  - `Observation → EventAnchor → Claim` → `MIXED, grounding=1,
    event_is_leaf=False` → **ALLOWED** (required-allow holds).
  - `AI Claim → EventAnchor → Claim` → `MIXED, grounding=0` → **BLOCKED**
    (required-deny holds; anti-laundering).
  - Independent probe: Event citing both a real Observation and an AI Claim →
    `MIXED, grounding=1` → allowed. This is pre-existing C14 `MIXED` semantics,
    not an EventAnchor-specific weakening.

### 4.2 Six pre-existing test adaptations — PASS (0/6 semantic change)

- **Assertions removed across the entire PR: 0**
  (`git diff e534378..a00e397 -- tests/ | grep "^-" | grep -E "assert|pytest.raises"`
  → empty).
- Only three pre-existing test files touched;
  `test_v3_completeness_closure.py` is **not in the changeset** (its fix was a
  Core error-precedence change).
- Tests 2–5 (`test_v3_cognition_revision.py`) have **zero edits in their
  bodies**; they inherit one shared `_seed_world` change that adds the real
  Observation `obs_pref_1` alongside the retained Claim ref.
- The `b → a` dependency edge was independently confirmed intact by inspecting
  the committed Dependency graph: `b → evs_47d0dd42… → {claim a, obs_pref_1}`.
- `test_current_core_target.py` (disclosed, not among the six) removes the
  #110 evidence-reselection filter and **adds** an explicit R9
  anti-self-proof `pytest.raises`.

### 4.3 Policy unification — PASS

- **No `evidence_policy=None` bypass remains.**
  `grep -rn "evidence_policy is not None\|evidence_policy is None" src/` → none.
- All service constructors default to an equivalent policy
  (`evidence_policy or CognitionEvidencePolicy(...)`); the runtime injects one
  shared instance into all four collaborators.
- Probe with no policy injected: `CognitionWritebackService`,
  `CognitionRevisionService`, `AIWorldCognitionService` all **BLOCK** an
  ungrounded `Claim → Summary` ref.
- The wake-source early-exit that gated the policy on `main` is gone; all four
  Claim capabilities validate through the single
  `_validate_cognition_evidence` path.
- Full suite on candidate: **452 passed, 0 failed** (re-run locally, 109 s).

### 4.4 Semantic freeze anchor — created

`governance/C15_RCC_COGNITION_SEMANTIC_FREEZE_2026-09-23.md` covers all
required surfaces (Evidence Policy, AI World Cognition Semantics, Revision
Semantics, Cognition Fields, Runtime Cognition Entry Points), the five freeze
rules, the Change Exception (new PM decision required; no direct patch of
`main`; `RES-A-REPAIR-DECISION-001` precedent if found after a run), duration
(hardening merge → `C15-RCC-EVAL-001` closure), and the PR #101 failure-class
context. Status: **ACTIVE AFTER MERGE OF C15 COGNITION HARDENING**.

---

## 5. New finding (this report): the #111/#113 integration requirement

**This is the single new blocker to merge, discovered while preparing this
report.** It is not a defect in either PR; it is a sequencing consequence of
two PRs implementing two tasks of the same hardening umbrella from the same
base.

### 5.1 Facts (all verified)

1. **Both PRs modify the same four source files:**
   - `src/aios_core/ai_world/cognition.py`
   - `src/aios_core/revision/service.py`
   - `src/aios_core/runtime/turn_runtime.py`
   - `src/aios_core/writeback/cognition.py`
2. **Both PRs are based on `main@e534378` and have diverged** (#111: 1 commit;
   #113: 4 commits).
3. **Neither merge order applies cleanly.** Verified in scratch worktrees:
   - merge #113 then #111 → **CONFLICT in all four files**;
   - merge #111 then #113 → **CONFLICT in all four files**.
   - Test files do **not** overlap (#111: `test_v3_c15_cognition_fields.py`,
     new file; #113: four different test files), so all conflicts are in
     source.
4. **PR #111 is additive field exposure**, consistent with its roadmap entry:
   - adds `valid_time`, `unknown_items`, `counter_evidence_refs` to
     `AIWorldClaimRequest` / `ClaimWriteRequest` / `ClaimRevisionRequest` and
     the views;
   - every removed line in its source diff is import/helper refactoring
     (verified line-by-line), not removed behaviour;
   - it adds **no new claim formation entrypoint** — the three fields ride the
     existing commit/revise paths.
5. **The one field with a semantic interaction — `counter_evidence_refs` —
   is benign by construction:** counter evidence is persisted as a **separate**
   `EvidenceSet` (carrying `counter_refs`) referenced from
   `counter_evidence_set_refs`, a claim field distinct from the support
   `evidence_refs`. PR #113's policy validates only the pinned support refs, so
   counter evidence can never be laundered into grounding support. #111 also
   applies the subject-scope isolation check to counter evidence, preserving
   `C15-RCC-MECH-FIX-001`.
6. **PR #111 has NOT received the same independent governance review as
   #113.** #113 was reviewed, remediated, and re-reviewed through this arc.
   #111's last state is the author's own CI (27/27). This is a review gap the
   PM must close before the integrated merge (see §7).

### 5.2 Integration requirement (for the PM to commission)

The hardening must land as **one integrated merge**. Recommended path:

1. **PR #113 is the foundation** (it is the gate; #111's fields flow through
   it; #113 is the already-independently-remediated artifact). Merge #113's
   content into `main` (or, equivalently, rebase #111's single commit onto
   #113's head — one commit rebased onto four is the smaller conflict surface).
2. **Resolve the four-file conflicts** as an explicit integration act. The
   resolution is where the two PRs' constructor and commit-path changes meet;
   it must preserve **both** invariants:
   - the unified `CognitionEvidencePolicy` on every Claim capability (no
     regression from #113);
   - the three new fields on every formation path (no regression from #111).
3. **Re-run the full CI** on the integrated head — including the
   `c15-cognition-evidence-policy` required gate added by #113 and #111's
   `test_v3_c15_cognition_fields.py`.
4. **Delta-review the integration** (not the two PRs again): the four
   conflict-resolved files only, against the two invariants above, plus the
   counter-evidence separation check (§5.3).
5. Only then does the **integrated hardening merge** happen, and **only that
   merge** activates the semantic freeze and earns the Core anchor SHA.

### 5.3 Post-integration verification checklist

| # | Check | Pass condition |
|---|---|---|
| 1 | Policy coverage | all four Claim capabilities still route through `_validate_cognition_evidence`; no `evidence_policy=None`-style bypass reintroduced |
| 2 | Fields on the gated path | a claim carrying `valid_time` / `unknown_items` / `counter_evidence_refs` commits through the same policy-validated path |
| 3 | Counter-evidence separation | `counter_evidence_set_refs` never enters the support lineage; the policy's traversal from pinned support refs cannot reach a counter `EvidenceSet` as grounding |
| 4 | No fixture/constitution/registry change | `git diff main..integrated` touches no fixture, constitution, registry, or PR #101 path |
| 5 | Full gate | evidence-policy CI gate + full suite green on the integrated head |

---

## 6. Freeze anchor amendment (accuracy fix, this commit)

The freeze document's activation anchor originally named only PR #113 as "the
C15 cognition hardening". Since PR #111 is confirmed — by the roadmap umbrella
and by this report — to be part of the hardening gate, the anchor now names
**both PRs and states the integrated-merge requirement**, so that no later
reader can mistake a mid-freeze #111 merge for a hardening-gate merge. Two
lines changed; no semantics of the freeze changed.

---

## 7. Review gap: PR #111

Before the integrated merge, PR #111 should receive an independent review at
the same standard applied to #113. Concretely:

1. **Fixture/semantic review of `test_v3_c15_cognition_fields.py`** (new file,
   409 lines): confirm it tests the fields' semantics and does not encode the
   buggy behaviour as expected output.
2. **Source semantic review of the four shared files' #111 side**: confirm the
   `valid_time` / `unknown_items` / `counter_evidence_refs` handling matches
   the roadmap intent ("conditional cognition instead of
   over-generalized permanent conclusions"; UNKNOWN stays legal) and the
   `C15-RCC-RULE-001` continuity semantics.
3. **Interaction review with #113**: run the §5.3 checklist.

This is an explicitly open task; nothing in this report asserts it passed.

---

## 8. PM action list (ordered)

1. **Rule on `C15-RCC-HARDEN-DECISION-001`** — accept (or reject with record)
   the BEFORE-order: hardening merge → freeze ACTIVE → Resident A rerun.
2. **Amend the task board** (PM act): insert row `29.35`
   `C15-RCC-EVIDENCE-POLICY-001` = `GATE`; change row `29.4`
   `C15-RCC-RES-A-RERUN-001` from `READY` to `BLOCKED` on `29.35`; note on
   rows 30/31/32 that the Core anchor SHA is recorded post-merge.
3. **Commission the #111 + #113 integration** per §5.2 (engineering act —
   rebase/merge, conflict resolution, CI re-run).
4. **Close the #111 review gap** per §7 (independent, before or as part of the
   integration delta-review).
5. **Merge the integrated hardening** into `main` (single integrated merge).
6. **Record the Core anchor SHA** in board rows 30/31/32; the semantic freeze
   becomes ACTIVE at this moment.
7. **Unblock `C15-RCC-RES-A-RERUN-001`**, then Resident B, C, then
   `C15-RCC-EVAL-001`.
8. **After `C15-RCC-EVAL-001` closes**, archive the freeze document as the
   historical anchor and lift the freeze.

If step 1 is rejected (Resident A before hardening), the freeze document does
not apply, and the rejection record must state that axis R9 (anti-self-proof)
was not mechanically enforced during A/B/C — per the rejection branch of
`C15-RCC-HARDEN_DECISION_001` §7.

---

## 9. Risks and open items

| # | Risk / item | Owner | Disposition |
|---|---|---|---|
| 1 | #111/#113 merged sequentially without integration → conflict-resolution done under merge pressure | PM | §5.2 makes integration a pre-condition |
| 2 | #111 merges mid-freeze, after A has run → PR #101 class failure | PM | freeze §2.4 + §4; board `BLOCKED` status |
| 3 | Counter-evidence separation regressed during conflict resolution | integrator + delta reviewer | §5.3 check 3 |
| 4 | Review gap on #111 closes after merge | PM | §7 ordered before/at integration |
| 5 | Reviewer independence (#113 was reviewed by its author in-session) | PM | all §4 results are mechanically re-runnable; PM should commission the #111 review from a non-author |
| 6 | `C15-RCC-SCALE-BENCH-001` (no PR yet) touches the frozen surface | PM | cannot merge while freeze ACTIVE (freeze §2.4) |

---

## 10. Verification appendix (re-run commands)

```bash
# main contains COG-FIX-001
gh api repos/Haneof/Haneof-AIOS-Core-v3.0/compare/c146cebbdfa8ac714fc236652a4452c60bcfa0bb...main

# PR states / CI
gh pr view 113 --json state,headRefOid,mergeable
gh pr checks 113
gh pr view 111 --json state,headRefOid,mergeable
gh pr checks 111

# divergence + shared files
gh api repos/Haneof/Haneof-AIOS-Core-v3.0/compare/4d421efbc35fb538b26613cce6e535f8caf4072a...abb85e050f2f1bd19c5ce4f847b14b54259d6339
git diff --name-only e534378..abb85e0 | grep '^src/'   # #111 source files
git diff --name-only e534378..4d421ef | grep '^src/'   # #113 source files

# conflict proof (scratch worktrees; both orders)
git worktree add /tmp/t origin/main
cd /tmp/t && git merge --no-edit 4d421ef && git merge --no-edit abb85e0   # ORDER A: 4-file conflicts
git merge --abort 2>/dev/null; git reset --hard -q origin/main
git merge --no-edit abb85e0 && git merge --no-edit 4d421ef               # ORDER B: 4-file conflicts

# #113 invariants (on candidate a00e397 or integrated head)
grep -rn "evidence_policy is not None\|evidence_policy is None" src/      # expect: none
git diff e534378..HEAD -- tests/ | grep "^-" | grep -E "assert|pytest.raises"   # expect: none

# full suite (candidate)
PYTHONPATH=src python -m pytest tests            # 452 passed on a00e397
```

---

## 11. Completion

- This report and the freeze-anchor amendment are the only artifacts of this
  turn; **no Core, test, Runtime, or Resident fixture file was modified**.
- No PR was merged. Board was not amended (PM act).
- The arc is now in a state where the PM's next act — the sequencing ruling —
  unblocks everything downstream.
