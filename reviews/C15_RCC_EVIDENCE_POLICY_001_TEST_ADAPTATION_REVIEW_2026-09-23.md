# C15-RCC-EVIDENCE-POLICY-001 — Pre-existing Test Adaptation Review

> Date: 2026-09-23
> Scope: review only. No Core modification. No merge.
> Subject: the six pre-existing tests changed by PR #113 (`dc4f3de`)
> Purpose: prove each change is a **fixture repair**, not a semantic weakening

---

## 0. Why this document exists

Closing the `evidence_policy=None` bypass (independent review, MAJOR 3) caused six
tests that had **never actually enforced** the evidence policy to enforce it for
the first time. Every one of them then failed.

The failure mode the independent review warned about — silencing a real behaviour
change by editing a test — is exactly what must **not** have happened here. This
document examines each of the six individually and states, per test, whether the
semantics changed.

**Summary: 0 of 6 changed test semantics.** Five are fixture repairs that add the
reality leaf the assertion always implied. One was fixed in Core instead, with no
test edit at all.

### Classification key

| Class | Meaning |
|---|---|
| **FIXTURE-REPAIR** | Evidence made legally grounded; assertions untouched; property under test unchanged |
| **CORE-FIX** | Test not edited; Core corrected instead |
| **SEMANTIC-CHANGE** | Test now asserts something different — *none in this set* |

---

## 1. `test_v3_ai_world.py::test_all_ai_domains_share_one_world_store_without_second_ai_database`

**Class: FIXTURE-REPAIR**

### 1.1 Original purpose

Prove that all AI-world cognition domains (User Understanding, Relationship, Self)
persist into **one** unified `WorldStore` — that no second AI-private database is
created. The real assertions are:

```python
assert store.get_payload(user.claim.claim_id)["subject_id"] == "user_1"
assert store.get_payload(relationship.claim.claim_id)["subject_id"] == "user_1"
assert store.get_payload(self_claim.claim.claim_id)["subject_id"] == AI_SELF_SUBJECT_ID
...
assert "runtime_ai_self_memory" not in tables
assert "ai_user_understanding" not in tables
```

The test is about **storage topology and subject routing**, not evidence quality.

### 1.2 Why it triggered the policy

The Self-domain Claim was grounded on **two other Claims and nothing else**:

```python
evidence_refs=(
    ObjectRef(object_id=user.claim.claim_id, revision=1),
    ObjectRef(object_id=relationship.claim.claim_id, revision=1),
)
```

That is a literal `Claim -> Claim` self-proof — one of the three patterns C14/C15
explicitly forbid. It produced
`classification=MIXED; grounding_leaf_count=0`.

The fixture only ever needed *a* Self Claim to exist so its `subject_id` could be
checked. The author reached for the two Claims already in scope. The evidence was
incidental to the test's purpose, and nothing previously enforced it.

### 1.3 Reality grounding added

One real user Observation — `facts[1]`, the seeded
`obs_ai_error_p10` (`"你刚才又把索引和推荐混到一起了。"`, committed
`source_class=USER`) — pinned **alongside** the two Claims:

```python
evidence_refs=(
    ObjectRef(object_id=user.claim.claim_id, revision=1),
    ObjectRef(object_id=relationship.claim.claim_id, revision=1),
    ObjectRef(object_id=facts[1].object_id, revision=1),   # added
),
```

Both Claim refs are **retained**. The lineage is still `MIXED`
(`has_ai_cognition=True`), but now terminates on a `USER` leaf, so
`grounding_leaf_count >= 1`.

### 1.4 Semantic change?

**No.** No assertion added, removed, or altered. The Self Claim is still created,
still routed to `AI_SELF_SUBJECT_ID`, still in the same single store. The
cross-domain single-store property is proven identically.

Worth noting: the cognition modelled here — a Self Claim informed by prior
understanding *and* by a real user correction — is **more** faithful to the C15
Self/Calibration family than the original, which asserted a self-conclusion from
nothing but two earlier self-conclusions.

---

## 2–5. `test_v3_cognition_revision.py` — four tests sharing `_seed_world`

**Class: FIXTURE-REPAIR (shared fixture, single edit)**

Affected:

| # | Test |
|---|---|
| 2 | `test_revise_claim_preserves_history_and_marks_dependents_review_required` |
| 3 | `test_retract_claim_creates_forward_tombstone_semantics_without_deleting_history` |
| 4 | `test_already_advanced_dependent_is_not_overwritten_by_old_dependency_propagation` |
| 5 | `test_claim_revision_stales_dependent_summary_then_summary_can_rebuild` |

**None of these four test bodies was edited.** They inherit one change to the
shared `_seed_world` helper. Verified by diff: the only hunks in this file are in
`_seed_world` and in test #6 (§6 below).

### 2.1 Original purpose

`_seed_world` builds a two-level cognition chain to exercise **P9 revision
propagation**:

- Claim `a` — "用户当前偏好每天喝茶。" grounded on Observation `first`
- Claim `b` — "用户的饮品习惯目前以茶为主。" built **on top of** `a`

The four tests then revise or retract `a` and assert what happens to `b`:
`stale_review_required` marking, `stale_due_to_refs` provenance, tombstone
semantics, already-advanced dependents not being clobbered, and dependent Summary
staleness/rebuild.

The object under test is the **dependency edge `b -> a`** and its propagation
behaviour.

### 2.2 Why it triggered the policy

Claim `b` was grounded **only** on Claim `a`:

```python
evidence_refs=(ObjectRef(object_id=a.claim_id, revision=1),)
```

Again a bare `Claim -> Claim`. `a` itself is properly grounded on a real
Observation, but the policy correctly refuses to let an AI Claim act as the sole
bridge — otherwise any Claim could be laundered into support by wrapping it in
another Claim.

### 2.3 Reality grounding added

The Observation that Claim `a` already rests on, pinned alongside `a`:

```python
evidence_refs=(
    ObjectRef(object_id=a.claim_id, revision=1),
    ObjectRef(object_id=first.object_id, revision=1),   # added
),
```

`first` is `obs_pref_1` — `"我每天都喝茶。"`, `source_class=USER`. This is the
reality that "用户的饮品习惯目前以茶为主" was always conceptually derived from; it
simply was never cited.

### 2.4 Critical check — is the dependency edge preserved?

**Yes.** This is the load-bearing question, since all four tests measure
propagation across `b -> a`.

The ref to `a` is **retained**, so `claim_uses_evidence_set -> a` is still
created, and `b` is still a dependent of `a@1`. Proof from the unedited
assertions, all passing:

```python
assert dependent_claim["status"] == STATUS_REVIEW_REQUIRED
assert {"object_id": a.claim_id, "revision": 1} in dependent_claim["metadata"]["stale_due_to_refs"]
assert (b.claim_id, 1) in receipt.stale_refs
```

Propagation from `a` to `b` still fires, and `stale_due_to_refs` still names
`a@1` specifically. Had the edge been broken, these would fail.

### 2.5 Semantic change?

**No.** Zero assertions touched across all four tests. Claim `b` still depends on
Claim `a`; revision of `a` still stales `b`; retraction still tombstones forward;
already-advanced dependents are still skipped; dependent Summaries still go stale
and rebuild.

---

## 6. `test_v3_cognition_revision.py::test_stale_dependent_can_be_re_evaluated_into_new_active_revision`

**Class: FIXTURE-REPAIR**

### 6.1 Original purpose

Prove the **anti-freeze** property required by `C15-RCC-RULE-001` §15.3 and axis
R8: a dependent Claim marked `stale_review_required` must be revisable back into
an `active` revision. Assertions:

```python
assert latest_b["revision"] == 3
assert latest_b["status"] == "active"
assert latest_b["content"] == "用户的当前饮品习惯以咖啡为主。"
assert second.previous_revision == 2
assert second.new_revision == 3
```

Plus index checks that the stale "以茶" phrasing no longer recalls and the new
"以咖啡为主" does.

### 6.2 Why it triggered the policy

This test has its **own** violation in addition to the `_seed_world` one. The
re-evaluation cited only the revised upstream Claim:

```python
evidence_refs=(ObjectRef(object_id=a.claim_id, revision=2),)
```

`Claim -> Claim` again, this time on the revision path
(`cognition_revision.revise`).

### 6.3 Reality grounding added

The correcting Observation pinned alongside the revised upstream Claim:

```python
evidence_refs=(
    ObjectRef(object_id=a.claim_id, revision=2),
    ObjectRef(object_id=correction.object_id, revision=1),   # added
),
```

`correction` is `obs_pref_correction` — `"之前那段时间是喝茶，现在已经改成每天喝咖啡了。"`,
`source_class=USER`. This is the actual new reality that justifies re-evaluating
the dependent, and it is the same Observation the upstream revision itself used.

### 6.4 Semantic change?

**No.** Assertions untouched; `a@2` still cited so the upstream link is intact.

This one deserves emphasis: it is the **anti-freeze / R8 revisability control**.
Its continued passing is direct evidence that the unified policy does **not**
freeze cognition against later correction — the failure mode `C15-RCC-RULE-001`
§21 calls *"Continuity against Evidence is rigor mortis."*

---

## 7. `test_v3_completeness_closure.py::test_subject_scoped_search_and_cognition_block_cross_user_refs`

**Class: CORE-FIX — test not modified**

### 7.1 Original purpose

Prove cross-user subject isolation (`C15-RCC-MECH-FIX-001`): User B's objects
must not be usable as evidence in User A's cognition, and the error must name the
**subject-scope** violation:

```python
with pytest.raises(ValueError, match="subject scope"):
    writer.commit_claim(...)
```

### 7.2 Why it triggered the policy

Not a grounding problem. An **error-precedence** problem.

The evidence policy ran *before* the subject check, so a cross-user ref raised
`"...leaf-grounded evidence closure rejected..."` instead of
`"...crosses the allowed subject scope..."`. The `match="subject scope"` assertion
therefore failed — correctly. The isolation violation was being masked by a
generic closure error, which would have degraded the diagnostic quality of
`C15-RCC-MECH-FIX-001`.

### 7.3 Resolution — in Core, not in the test

The subject-isolation loop was moved **ahead** of the policy call in both
`CognitionWritebackService.commit_claim` and `CognitionRevisionService.apply`:

```python
# Subject isolation is checked first so cross-user refs keep reporting the
# precise isolation violation rather than a generic closure failure.
for ref in pinned:
    ...
    raise ValueError("cognitive writeback evidence crosses the allowed subject scope: ...")

self.evidence_policy.validate(pinned, operation="cognition_writeback.commit_claim")
```

**The test file was not edited.** Confirmed by diff: `test_v3_completeness_closure.py`
does not appear in the PR #113 changeset.

### 7.4 Semantic change?

**No** — in the strongest sense available: the test is byte-identical to `main`.
Both checks still run and both still reject; only the reporting order changed, and
it changed to preserve the pre-existing, more specific error.

---

## 8. Aggregate assessment

| # | Test | Class | Assertions changed | Semantics changed |
|---|---|---|---|---|
| 1 | `test_all_ai_domains_share_one_world_store...` | FIXTURE-REPAIR | none | **No** |
| 2 | `test_revise_claim_preserves_history...` | FIXTURE-REPAIR | none | **No** |
| 3 | `test_retract_claim_creates_forward_tombstone...` | FIXTURE-REPAIR | none | **No** |
| 4 | `test_already_advanced_dependent_is_not_overwritten...` | FIXTURE-REPAIR | none | **No** |
| 5 | `test_claim_revision_stales_dependent_summary...` | FIXTURE-REPAIR | none | **No** |
| 6 | `test_stale_dependent_can_be_re_evaluated...` | FIXTURE-REPAIR | none | **No** |
| 7 | `test_subject_scoped_search_and_cognition_block_cross_user_refs` | CORE-FIX | none (file untouched) | **No** |

### 8.1 Invariants held across every change

- **No assertion was deleted, weakened, or inverted.** Tests 2–5 and 7 have zero
  edits inside the test bodies.
- **No expected-failure became an expected-pass.** The only `pytest.raises`
  conversion in the whole PR runs the other way — the habitation test now
  *asserts a new rejection* (§8.3).
- **No `Claim -> Claim` dependency edge was removed.** Every pre-existing Claim
  ref is retained; reality refs were *added* alongside. Propagation assertions
  naming `a@1` still pass, proving the edges survive.
- **No test-only relaxation exists in Core.** The policy has no test hook, no
  skip flag, no env switch.
- **Every edit carries an inline `C15-RCC-EVIDENCE-POLICY-001` comment** naming
  why the reality ref is present, so a future reader cannot mistake it for
  incidental fixture noise.

### 8.2 The pattern, stated plainly

In all five fixture repairs the change is the same shape:

> The test asserted a property about **cognition structure** (storage topology,
> dependency propagation, revisability). It needed *a* Claim to exist. The author
> grounded that Claim on whatever object was already in scope — which happened to
> be another Claim. Nothing enforced grounding, so it passed. Closing the bypass
> surfaced that the fixture's evidence was never legal; the fix pins the real
> Observation the Claim was always conceptually derived from.

In each case the added Observation was **already present in the same fixture**.
No new reality was invented to satisfy the policy.

### 8.3 The one deliberate semantic addition — disclosed separately

`tests/habitation/test_current_core_target.py` is **not** in the six. It is a
deliberate, disclosed change and is listed here so the record is complete.

PR #110 had added a `metadata.role != "assistant"` filter that silently re-selected
evidence to dodge a rejection. PR #113 **removes that filter** and instead asserts
the rejection explicitly:

```python
assert first_obs.get("metadata", {}).get("role") == "assistant"
with pytest.raises(ValueError, match="leaf-grounded evidence closure rejected"):
    a.runtime.ai_world.commit(...)   # AI speech cannot prove itself
```

The test's original property — private-world isolation between model-a and
model-b — is then proven with a real `USER` Observation, so it still tests what it
always tested. This **adds** an anti-self-proof assertion (C15 axis R9) rather
than removing one.

---

## 9. Residual risk and what PM should re-derive independently

This review is my own analysis of changes I authored. Two items warrant
independent confirmation rather than acceptance on my word:

1. **The `_seed_world` judgement (tests 2–5).** I assert that pinning `first`
   alongside `a` preserves the `b -> a` dependency edge, and I cite the passing
   `stale_due_to_refs` assertions as proof. A reviewer should confirm those
   assertions genuinely exercise the edge rather than passing incidentally.

2. **Whether "the fixture's evidence was always illegal" is the right frame.** I
   classify these as fixture repairs because the policy is new and the assertions
   are untouched. A reviewer could reasonably take the stricter position that any
   change to a fixture's evidence is a semantic change to the test, and require
   these to be re-derived from scratch instead. That is a legitimate call and it
   is not mine to make.

Both are recorded in `governance/C15_RCC_HARDEN_DECISION_001_2026-09-23.md` §7
item 4 as an open PM item.

---

## 10. Verification

| Check | Result |
|---|---|
| Files with pre-existing tests modified | 3 (`test_v3_ai_world.py`, `test_v3_cognition_revision.py`, `test_current_core_target.py`) |
| `test_v3_completeness_closure.py` modified | **No** — Core fixed instead |
| Assertions deleted anywhere in PR #113 | **0** |
| Test bodies edited in tests 2–5 | **0** (shared fixture only) |
| Full suite | **452 passed, 0 failed** |
| PR #113 CI | **42/42 pass** |

Candidate reviewed: `dc4f3de20efbf69d82ec6a88744793e7b35d9571`.
