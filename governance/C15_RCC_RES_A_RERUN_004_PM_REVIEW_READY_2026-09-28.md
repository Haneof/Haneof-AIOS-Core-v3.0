# C15-RCC-RES-A-RERUN-004 — PM REVIEW_READY Writeback

Date: 2026-09-28

Status:

```text
C15-RCC-RES-A-RERUN-004
= PHASE_A_COMPLETE / REVIEW_READY
= READY_FOR_INDEPENDENT_ACCEPTANCE
```

This is a PM readiness decision only.

It is not:
- an Independent Acceptance verdict;
- permission to merge evidence PR #273;
- permission to resume persistence Corrective-003;
- permission to release Resident B;
- permission to run Resident C;
- permission to enter evaluator / C15 close.

## Fresh identities

- live main at PM readiness: `0b17c7f35697dc4a24b731185868d29967efcf58`
- evidence PR: #273
- exact evidence head: `f251e9c0026a0f97fdee20397936cb5e3b18c61c`
- parent: `0b17c7f35697dc4a24b731185868d29967efcf58`
- evidence tree: `fd312286b7b83cd550ecc49d72b78656e6e91b71`
- frozen software: `f20f2edfa7af00d0286493fd15196ca9503bc315`
- frozen Core tree: `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- frozen tests tree: `7e33b5ef8432370234965d3ccd61248c703c4019`

Run identities:
- run id: `a004-27bb1fb3da404f4d`
- resident session: `resident-a004-3507d8a3bf894090899cf424c4baea07`
- conversation session: `a004-conversation-fef437192f974e55b376a3bbf3e7f0d5`

## Mechanical PM findings

PR #273 is OPEN / UNMERGED and its exact head matches the Resident evidence pin.

The PR contains exactly 189 changed files and every path is under:

`reviews/internal_habitation/c15-rcc/v1/resident/runs/a004-27bb1fb3da404f4d/**`

Therefore PM observed:
- zero `src/**` change;
- zero `tests/**` change;
- zero `tools/**` change;
- zero `governance/**` change;
- zero accepted-RC implementation change.

Mechanical evidence also records:
- release-state phase A;
- sequences 1..13 each acknowledged;
- last ACK = c15rcc-013 / sequence 13;
- next sequence = 14;
- pending reveal = null;
- final world revision = 89;
- final index watermark = 89;
- CPython 3.12.14;
- Pydantic 2.13.5;
- frozen RC pins recorded in identity.json.

These are run-author claims/evidence, not acceptance proof.

## Binding Independent Acceptance attack surface

Fresh IA must independently adjudicate, not inherit, the following:

1. **Freshness / contamination**
   - no A-003/A-002/A-001 semantic reuse;
   - no future fixture/B/C/evaluator material;
   - no hidden expected-answer path;
   - no old transcript/report/checkpoint contamination.

2. **Resident decision authenticity**
   - 50 decision requests/responses represent actual current Resident semantic choices;
   - operator/runner did not decide meaning;
   - no keyword/fixture/script oracle;
   - no decision response was synthesized after observing later state.

3. **Cursor legality**
   - exactly cursor 1..13;
   - canonical USER ingest;
   - mechanical PLATFORM ingest;
   - exact durable ACK chain;
   - cursor 14 not revealed;
   - no future visibility through clock/review/summary/wake paths.

4. **Cursor-1 recovery**
   - first handshake failure truly occurred before submission;
   - `not_submitted` reconciliation is evidence-backed;
   - retry authorization was legal;
   - no duplicate semantic effect.

5. **Cursor-10 recovery**
   - round-0 application, round-1 in_doubt state and durable assistant-output recovery are internally consistent;
   - exact response bytes were preserved before reconciliation;
   - recovery did not fabricate model output after the fact;
   - no duplicate claim/assistant output/turn effect.

6. **Anonymous local handler**
   - actual Resident model decisions were made by this Resident session;
   - `usage=None / provenance=None` is truthfully represented as unknown rather than forged;
   - lack of provider receipt is not being used to make an unsupported provider-identity claim;
   - A-004 does not overclaim R6/replacement-model provenance.

7. **Attention-watch mechanical replay**
   - step-boundary evaluation is legal plumbing rather than semantic substitution;
   - it does not expose future reality;
   - it does not create a second scheduler/truth path;
   - it preserves ordering and normal AttentionWatch semantics;
   - if it compensates for a missing required runtime path, determine whether that makes the run noncanonical.

8. **Wake / Review / Summary / derivation completeness**
   - all due work through cursor 13 time was handled;
   - no forced success;
   - no skipped due work;
   - no future event seen early.

9. **World / index / cognition coherence**
   - final World and index are mutually consistent;
   - cognition writes are evidence-grounded;
   - revision/retraction lineage is legal;
   - no quotas or scripted expected Claims.

10. **Freeze integrity**
    - all artifact hashes independently recompute;
    - evidence package is complete enough to replay/review;
    - final state is frozen and cursor 14 remains unrevealed.

## Current downstream state

Until fresh IA PASS + PM integration:
- PR #273 merge = BLOCKED / evidence-only;
- persistence Corrective-003 resume = BLOCKED;
- Resident B = BLOCKED;
- Resident C = BLOCKED;
- evaluator / C15 close = BLOCKED.
