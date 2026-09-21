# C14-LOOP-001 Completion Evidence

> Status: **DONE / MERGED**  
> Date: 2026-09-21  
> Started main: `c4689fd595fc9308e71332e0c0dda17e49cffb95`  
> Work branch: `c14/loop-hardening-20260921-sol`  
> Exact final candidate: `f48c3c9cfa8a24fa2e0e0220d7fe20bcda1be34d`  
> PR: #65  
> Core squash merge: `a385f7b3fcc71982aae0611a382502c9a37ba71e`

## 1. Scope

This task hardens the already-approved continuous cognitive derivation loop. It does
not start C14-RES-001, C14-CLOSE-001, P16 triage, or Resident habitation.

No second Runtime, second queue, second provenance database, semantic keyword
classifier, dimension whitelist, occurrence threshold, Claim conversion target, or
parallel cognition store was introduced.

Changed files:

- `.github/workflows/c14-cognitive-derivation-loop.yml`
- `src/aios_core/runtime/budget_gate.py`
- `src/aios_core/runtime/turn_runtime.py`
- `src/aios_core/summaries/cognitive_derivation.py`
- `src/aios_core/wake/attention.py`
- `src/aios_core/wake/service.py`
- `tests/integration/test_v3_c14_cognitive_derivation_runtime.py`
- `tests/integration/test_v3_c14_cognitive_derivation_scheduler.py`

## 2. Current-main blocker reproductions

Before repair, exact test-only candidate
`04230585f6ae7114a70de49c1df8d23a82bf8eee` reproduced the main C14-LOOP
blockers:

- scheduler run `35587963160`: reconcile rebuilt the support Dependency graph
  **200 times for 200 Summaries**, proving Summary x Dependency repeated full scans;
- runtime run `35587963137`:
  - 12 sibling C14 Wakes did not preserve a C14 bundle cockpit;
  - direct C14 AttentionBundle exposed `attention_bundle` rather than the effective
    `cognitive_derivation` execution contract;
  - tool-round exhaustion incorrectly reached `COMPLETED` rather than durable
    resumable state;
- full P16 convergence run `35587963116` reproduced the same blockers.

Additional red-team cases were then added before final acceptance:

- test-only `fc80087f575d427faa1ad60037294e916b62d3f2` proved a partial successful
  Claim followed by runtime exhaustion could later be re-bundled and create a
  different Claim id;
- test-only `25dc2748b40dc69719a33b2f8c5b2f7be234a1c4` proved an old AI Claim
  summarized into a new Summary was still immediately eligible to manufacture
  another C14 Wake.

## 3. Burst bundling and execution-contract isolation

The existing `AttentionRouter` / `AttentionBundle` path is reused.

C14 bundling is now homogeneous by a mechanical execution contract:

- `COGNITIVE_DERIVATION` -> `c14_cognitive_derivation`;
- other background Wakes -> `background_default`.

A C14 bundle:

- contains only C14 member Wakes;
- pins every member Wake revision;
- carries each member Summary ref, dimension, granularity, window, and scheduler
  lineage as navigation/audit metadata;
- remains mechanically `ATTENTION_BUNDLE` in durable routing state;
- is validated at runtime before its **effective** wake source is restored to
  `COGNITIVE_DERIVATION`.

Therefore a C14 Wake cannot borrow the broader authorization surface of an ordinary
background bundle, and ordinary background Wakes cannot be pulled into a C14 bundle.

## 4. Runtime authorization, grounding, and delivery

For direct or bundled C14 execution, the effective wake source remains
`COGNITIVE_DERIVATION`.

The existing C14 side-effect allowlist therefore remains binding:

```text
commit_claim
commit_ai_world_claim
revise_claim
retract_claim
```

Every other side-effecting capability remains default-deny. The allowed cognition
writers still pass through leaf-grounded provenance validation.

Read/search/inspect/timeline/recall/ALL_DIMENSIONS/AI-world inspection remain
available.

C14 responses remain background-only and are not directly delivered to the user.
Mechanical bundling creates no semantic conclusion.

## 5. Budget exhaustion, partial success, and restart lifecycle

Only semantic `responded` / `silence` outcomes may complete a C14 Wake.

Model-round, tool-round, or capability-call exhaustion now returns semantically
unfinished work to durable `QUEUED` state with runtime-incomplete metadata.

Restart properties proved by regression:

- queued C14 work survives SQLite reopen;
- an unfinished C14 bundle retains all pinned member Wakes and Summaries;
- a partial successful Claim remains durable through exhaustion/restart;
- re-running the same grounded Claim path remains idempotent;
- a runtime-incomplete individual Wake is excluded from formation of a **new**
  AttentionBundle, so its semantic execution identity is not reset;
- preflight budget deferral recovers in the next budget window;
- HARD_DENY remains durable, nonsemantic, and does not create Wake storms.

## 6. C13 metering truth across retries

The non-world C13 Metering Ledger remains the economic/model-call truth.

Hardening added two missing accounting boundaries:

1. `QUEUED + runtime_incomplete` provider calls count against the **global**
   background budget seen by other Wakes in the same window.
2. After an unfinished Wake later completes, budget usage is calculated from all
   durable Metering Ledger rows for that Wake, not only the final attempt's
   `model_rounds` metadata.

Legacy completed Wakes without ledger rows retain a narrow metadata fallback.

Metering still does not create WorldObjects and does not advance `world_revision`.

## 7. Self-excitation boundary

The provenance walker still distinguishes full lineage from direct grounding
lineage.

Immediate C14 scheduling now requires:

- lineage class `REALITY` or `MIXED`; **and**
- at least one `grounding_leaf_ref` reached without relying solely on an
  intervening old AI semantic assertion.

Consequences:

- old AI Claim -> AI Summary does **not** immediately manufacture another C14 Wake;
- assistant-only cognition remains blocked;
- old AI cognition plus a genuinely new direct reality/user leaf remains eligible;
- runtime grounding validation still independently rejects Summary-only / old-AI
  self-proof even for manually constructed C14 Wakes.

This is provenance-mechanical, not a semantic keyword or dimension heuristic.

## 8. Periodic Review and durable cognition retrieval

C14 and Periodic Review remain independent:

- C14 does not consume Review Wakes;
- Review does not absorb C14 Wakes into its lifecycle;
- both keep their existing authorization contracts.

The new-runtime proof now uses:

- a reopened SQLite WorldStore;
- a rebuilt new WorldSearchIndex;
- a newly constructed `FusedTurnRuntime`;
- a fresh session with zero injected prior dialogue.

The fresh session retrieves exact durable cognition through normal runtime
capabilities:

`read_ai_world -> search_world -> inspect_world_object`

and verifies the exact current cognition revision from the durable AIOS World.

This is an engineering retrieval proof only. It does not replace the real-model
semantic behavior acceptance required by C14-RES-001.

## 9. Reconcile scale

`CognitiveDerivationScheduler.reconcile()` now constructs the support Dependency
graph once per reconciliation pass and reuses it for each Summary lineage walk.

The scale regression explicitly proves one support-graph build for 200 Summary
candidates, closing the prior Summary x Dependency repeated full-scan behavior.

## 10. Exact candidate Gates

Exact candidate:
`f48c3c9cfa8a24fa2e0e0220d7fe20bcda1be34d`

All 14 workflows on this exact SHA completed **SUCCESS**:

| Workflow | Run | Result |
|---|---:|---|
| c14-cognitive-derivation-loop | 35591908702 | SUCCESS |
| c14-cognitive-derivation-scheduler | 35591908713 | SUCCESS |
| c14-cognitive-derivation-runtime | 35591908736 | SUCCESS |
| p16-convergence-gate | 35591908701 | SUCCESS |
| constitutional-cognition-closure | 35591908860 | SUCCESS |
| p15-periodic-review | 35591908756 | SUCCESS |
| p14-long-context | 35591908792 | SUCCESS |
| p12-execution-gate | 35591908744 | SUCCESS |
| c09-wake-dispatch | 35591908712 | SUCCESS |
| fused-turn-runtime | 35591908706 | SUCCESS |
| dimension-summary | 35591908763 | SUCCESS |
| p11-dimension-gate | 35591908700 | SUCCESS |
| p10-ai-world-gate | 35591908737 | SUCCESS |
| p9-revision-gate | 35591908842 | SUCCESS |

Within the C14 aggregate workflows, the exact candidate also passed the targeted
C14 loop/runtime/scheduler suites, C13 metering, World Index, T28 memory boundary,
P15, P14, P12, C09, cognition closure, AI-world, P16 habitation harness, and full
P16 convergence suites.

## 11. Merge-tree equivalence

The exact tested candidate and squash-merged Core tree have identical blobs for
all eight changed files:

| File | Blob |
|---|---|
| `.github/workflows/c14-cognitive-derivation-loop.yml` | `067a162e74a2ce32703bc24642912b92d0f4c37e` |
| `src/aios_core/runtime/budget_gate.py` | `e2b198a05b48734317a90b4a1742df4d40a9d195` |
| `src/aios_core/runtime/turn_runtime.py` | `9e309cbf14cf89d325317bbcb904d6ae2bb7d0d4` |
| `src/aios_core/summaries/cognitive_derivation.py` | `75090af7b84c1048e4a417ee71973d9452125668` |
| `src/aios_core/wake/attention.py` | `b06bad12effd872c0f4e1435f96f2769f0f5774e` |
| `src/aios_core/wake/service.py` | `738cc56a297a14aef273d7d9d7aae16935712e4a` |
| `tests/integration/test_v3_c14_cognitive_derivation_runtime.py` | `b81ae54c26101ce692bc2d4ebc80c8c644176fb4` |
| `tests/integration/test_v3_c14_cognitive_derivation_scheduler.py` | `be34e36d11c7ef3caeb682b0a7b998cb45cc2a3f` |

Thus the code/test content validated by the exact candidate Gates is the content
merged at `a385f7b3fcc71982aae0611a382502c9a37ba71e`.

## 12. PM acceptance matrix

1. 10+ sibling C14 opportunities mechanically coalesce? **YES**
2. Bundle preserves C14 cockpit and effective execution contract? **YES**
3. C14 cannot share a broader ordinary-background bundle? **YES**
4. Bundle cannot launder Event/Entity/Goal/Task/Action/etc. writes? **YES**
5. Leaf-grounded cognition writers remain authorized? **YES**
6. Background user delivery remains suppressed? **YES**
7. Model-round exhaustion durable/resumable? **YES**
8. Tool-round exhaustion durable/resumable? **YES**
9. Capability-call exhaustion durable/resumable? **YES**
10. Partial successful Claim survives retry without duplicate semantic write? **YES**
11. Runtime-incomplete work cannot be silently re-bundled under a new execution identity? **YES**
12. Deferred budget work recovers after restart/window rollover? **YES**
13. HARD_DENY remains nonsemantic and storm-free? **YES**
14. Unfinished provider calls count against global C13/background budget? **YES**
15. Completed retry chains retain all prior provider-call spend? **YES**
16. Old AI cognition cannot immediately self-excite via AI Summary -> C14 Wake? **YES**
17. Mixed lineage with new direct reality remains eligible? **YES**
18. Periodic Review and C14 coexist independently? **YES**
19. New Runtime + new session can retrieve exact durable cognition? **YES**
20. Reconcile avoids repeated whole support-graph rebuild per Summary? **YES**
21. Second runtime/queue/provenance DB introduced? **NO**
22. Claim count/conversion rate used as quality policy? **NO**

## 13. Next task

`C14-LOOP-001` is complete.

The next task is `C14-RES-001`: real Resident cognition-formation habitation
validation. That task must use a real model making semantic decisions from successive
AIOS RuntimeSnapshots; pseudo-LLM, keyword-answer programs, precomputed semantic
oracles, or Python-generated cognition answers are not acceptable.

This completion does **not** mark C14 closed. C14-CLOSE-001 remains blocked until
C14-RES-001 produces valid evidence.
