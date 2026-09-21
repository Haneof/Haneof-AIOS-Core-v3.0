# C14-RES-FIX-001 Completion Evidence

> Date: 2026-09-21  
> Task: `C14-RES-FIX-001`  
> Role: Life Director / Sealed Fixture Designer  
> Started from main: `01ad300bfd8a102e8b2fd5fc9bfbfb6fd5e4ff29`  
> Work branch: `c14/res-fixture-20260921-sol`

## Scope

This task creates only sealed Resident life input, sequential-release rules, schema, evaluator-only design notes, and mechanical validation evidence.

It does **not**:

- modify `src/aios_core/**`;
- repair Runtime behavior;
- run a Resident model;
- create/revise/retract Resident cognition;
- execute `C14-RES-A-001`, `C14-RES-B-001`, `C14-RES-EVAL-001`, or P16.

## Frozen fixture

- fixture version: `c14-resident-fixture-v1`
- event count: **36**
- Phase A: **24**
- Phase B: **12**
- Phase-A ratio: **66.7%**
- simulated span: **2026-10-01T07:15:00-07:00 → 2026-10-29T18:40:00-07:00**
- timezone: `America/Los_Angeles`
- handoff: cursor **24** completes Phase A; cursor **25** remains unreleased for Resident B
- sealed fixture SHA256: `sha256:a0f9dfd0985560ce80f568b6cd11d46b13f5dc352a664c005fcb165ea5a67485`

The event volume is intentionally bounded: long enough to create multi-day/multi-week temporal context, but small enough that two real Resident windows can process every event sequentially without bulk semantic automation.

## Artifacts

- `reviews/internal_habitation/c14-resident/fixture/sealed_fixture.json`
- `reviews/internal_habitation/c14-resident/fixture/fixture_manifest.json`
- `reviews/internal_habitation/c14-resident/release/release_contract.md`
- `reviews/internal_habitation/c14-resident/release/event_schema.json`
- `reviews/internal_habitation/c14-resident/evaluator/EVALUATOR_ONLY_design_notes.md`

## Mechanical validation

The fixture was mechanically checked before write:

1. JSON serializes/parses — **PASS**
2. 36 event ids are unique — **PASS**
3. sequence is exactly 1..36 — **PASS**
4. timestamps are strictly increasing — **PASS**
5. all timestamps carry explicit `-07:00` offset and root timezone is `America/Los_Angeles` — **PASS**
6. exactly one Phase-A/B boundary exists between 24 and 25 — **PASS**
7. Phase A count 24 / Phase B count 12 — **PASS**
8. manifest SHA256 equals exact UTF-8 sealed fixture bytes including trailing LF — **PASS**
9. cursor simulation releases exactly one current event and advances 1→36 without reorder/skip — **PASS**
10. Resident-visible payload scan contains no evaluator labels or expected-Claim fields — **PASS**
11. sealed event objects contain no `expected_cognition`, `expected_claim`, `expected_preference`, `expected_personality`, `correct_answer`, or equivalent answer field — **PASS**
12. no file under `src/aios_core/**` is part of this task — **PASS**

Mechanical validation checks structure and isolation only. It does not decide what cognition a Resident should form.

## Future isolation

Resident A/B are forbidden from reading the sealed fixture, manifest, evaluator-only notes, or unreleased entries. A trusted mechanical release operator may reveal only the current cursor's public event projection.

Resident A must stop permanently after cursor 24. Resident B must start in a completely fresh model window and resume at cursor 25 from durable AIOS state only.

## Deferred

Semantic proof belongs exclusively to:

`C14-RES-A-001 -> C14-RES-B-001 -> C14-RES-EVAL-001`.

This task provides no semantic PASS verdict and does not start those tasks.
