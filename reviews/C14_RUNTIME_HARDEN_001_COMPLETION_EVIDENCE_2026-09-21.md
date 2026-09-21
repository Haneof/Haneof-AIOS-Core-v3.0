# C14-RUNTIME-HARDEN-001 Completion Evidence

> Status: **DONE / MERGED**  
> Date: 2026-09-21  
> Started main: `646c5a3d0cf22cfa99c70667925ad240ea53f663`  
> Work branch: `c14/runtime-hardening-side-effects-20260921`  
> Candidate: `3accaeebe8ee1b3d420d2dfa3528ecb5e7388d86`  
> PR: #63  
> Core squash merge: `09002ddf8fd1fd4af08f54ac5b190d4c39c9e25b`

## 1. Scope

This task closes only the durable side-effect escape routes from
`WakeSource.COGNITIVE_DERIVATION`.

No C14 Runtime redesign, service-layer provenance duplication, second Runtime,
second provenance system, semantic classifier, keyword rule, occurrence threshold,
confidence threshold, or personality/importance detector was introduced.

Changed implementation/test files:

- `src/aios_core/runtime/turn_runtime.py`
- `tests/integration/test_v3_c14_cognitive_derivation_runtime.py`

## 2. Authorization design

The C14 derivation side-effect allowlist is now exactly:

```text
commit_claim
commit_ai_world_claim
revise_claim
retract_claim
```

For `COGNITIVE_DERIVATION`:

- non-side-effecting/read capabilities remain available;
- the four cognition writes above are authorized;
- every other current or future `spec.side_effecting == True` capability is denied by default;
- the four authorized cognition writes still pass through
  `_validate_c14_cognition_grounding()`;
- ordinary user interaction, Periodic Review, and other Wake sources retain their
  pre-existing authorization behavior.

## 3. Denied capability regression matrix

The C14 targeted suite proves the following all return
`CAPABILITY_NOT_AUTHORIZED` before handler execution and do not advance
`world_revision` during the rejected call:

| Area | Capabilities | Result |
|---|---|---|
| Entity | `propose_entity`, `revise_entity` | DENIED / no world write |
| Relation | `upsert_relation` | DENIED / no world write |
| Dimension | `propose_dimension`, `transition_dimension` | DENIED / no world write |
| Goal | `propose_goal`, `transition_goal` | DENIED / no world write |
| Task | `create_task`, `transition_task` | DENIED / no world write |
| AttentionWatch | `create_attention_watch` | DENIED / no world write |
| Action | `propose_action` | DENIED / no world write |
| Event | `form_event`, `transition_event` | DENIED / no world write |
| Experience | `commit_operation_experience`, `record_communication_experience` | DENIED / no world write |
| CognitivePolicy | `propose_cognitive_policy`, `update_cognitive_policy`, `rollback_cognitive_policy` | DENIED / no world write |

A synthetic future WRITE `CapabilitySpec` not present in today's registry is also
explicitly tested and denied, proving the boundary is default-deny rather than a
blacklist of current function names.

## 4. Allowed cognition and read regressions

Still authorized during `COGNITIVE_DERIVATION`:

- `commit_claim`
- `commit_ai_world_claim`
- `revise_claim`
- `retract_claim`

Existing and extended C14 runtime tests remain GREEN for:

- Summary -> inspect real leaf -> grounded Claim;
- AI-world Claim writeback with qualifying leaf evidence;
- grounded revise/retract;
- Summary-only / old-AI recursive support rejection;
- T28 assistant-only rejection and user-leaf positive control;
- real Outcome/operation-case Strategy grounding;
- valid silence with zero semantic write;
- search/inspect/cross-dimensional read paths;
- background response delivery suppression;
- C13 non-world metering.

All registered non-side-effecting capabilities remain outside the side-effect deny
boundary.

## 5. Normal-runtime regression

The new restriction is bound only to
`WakeSource.COGNITIVE_DERIVATION`.

Targeted controls prove ordinary `USER_INTERACTION` keeps the existing
authorization for Entity/Relation/Dimension/Goal/Task/AttentionWatch/Action/Event
writes.

Periodic Review controls preserve Claim create/revise/retract,
OperationExperience, and CognitivePolicy authorization. The dedicated P15 and
full-suite gates are GREEN.

## 6. Candidate Gate evidence

Candidate `3accaeebe8ee1b3d420d2dfa3528ecb5e7388d86`:

- `c14-cognitive-derivation-runtime` — run `35586168903` — **SUCCESS**
  - `c14-runtime-targeted` — SUCCESS
  - `cognition-closure` — SUCCESS
  - `runtime-wake-turn` — SUCCESS
  - `dimension-index-execution` — SUCCESS
  - `p15-c13-p14-t28` — SUCCESS
  - `p16-habitation-harness` — SUCCESS
  - `p16-convergence` — SUCCESS
- `constitutional-cognition-closure` — run `35586168941` — **SUCCESS**
- `p16-convergence-gate` — run `35586168937` — **SUCCESS**
- `p15-periodic-review` — run `35586168873` — **SUCCESS**
- `fused-turn-runtime` — run `35586168861` — **SUCCESS**
- `c09-wake-dispatch` — run `35586168846` — **SUCCESS**
- `p11-dimension-gate` — run `35586168851` — **SUCCESS**
- `p10-ai-world-gate` — run `35586168898` — **SUCCESS**
- `p9-revision-gate` — run `35586168883` — **SUCCESS**
- `p12-execution-gate` — run `35586168915` — **SUCCESS**
- `p14-long-context` — run `35586168872` — **SUCCESS**

The C14 aggregate workflow directly executes the requested scheduler/runtime,
cognitive-runtime, cognition-writeback, cognition-revision, AI-world,
constitutional cognition closure, fused-turn, C09, P12, P15, C13, P14, T28,
Dimension Summary, World Index, P16 habitation, and P16 convergence suites.

## 7. Merge-tree equivalence

The tested candidate and squash-merged Core tree have identical blobs for both changed
files:

- `turn_runtime.py`: `8c2126f712398105c233c11b09301f84a47c7713`
- C14 runtime test: `ef93d762008754d21031029302e58cb0ec86613f`

Therefore the exact code/test content validated by the candidate Gates is the content
merged at `09002ddf8fd1fd4af08f54ac5b190d4c39c9e25b`.

## 8. PM self-audit

1. COGNITIVE_DERIVATION side effects default-deny? **YES**
2. Only four cognition write capabilities allowed? **YES**
3. All four still pass leaf-grounding? **YES**
4. Event bypass? **NO**
5. Entity/Relation bypass? **NO**
6. Dimension bypass? **NO**
7. Goal/Task/Action bypass? **NO**
8. AttentionWatch bypass? **NO**
9. Experience/Policy still denied? **YES**
10. Read capabilities preserved? **YES**
11. User turn unaffected? **YES**
12. Periodic Review unaffected? **YES**
13. Second Runtime/provenance system introduced? **NO**
14. Silence/background delivery behavior preserved? **YES**

## 9. Bugs / deferred issues

Closed blocker:

- C14 derivation previously denied Experience/Policy but then fell through to the
  ordinary durable-write allowlist, permitting alternate Event/Entity/Relation/
  Dimension/Goal/Task/Action/AttentionWatch writes.

Deferred, unchanged:

- `C14-LOOP-001` retains its existing loop/budget/coalescing/restart/reconcile-scale
  scope and is the next task.
- No LOOP implementation was started in this window.
