# C14-RES-FIX-002 Completion Evidence

> Status: **DONE / MERGED / LIFE-DIRECTOR MECHANICAL GATES PASS**  
> Date: 2026-09-21  
> Task: `C14-RES-FIX-002`  
> Role: Life Director / Sealed Fixture Designer  
> Started from main: `075685b5b9b632988baa4e2de61c6d05aa469d32`  
> Work branch: `c14/res-fixture-v2-hardening-20260921-sol`  
> Exact candidate: `aacee04cfa5390f2a63d0a5606acb909291849b6`  
> PR: #70  
> Squash merge: `510290d3b9578cd9425079a22050eb679ddb528a`  
> Task-board closure: `490aa747b8d9a0dc9365d58ae58bfff1e71faf2c`  
> Checkpoint closure: `2043d4d498447312c0851468e971c950c23836e3`

## 1. Scope and hard boundary

This task hardens the C14 Resident test design only.

It does **not**:

- modify `src/aios_core/**`;
- run a real Resident;
- run a pseudo-LLM or semantic oracle;
- generate, select, revise, or retract cognition;
- prescribe one correct Claim sentence;
- prescribe one mandatory Phase-B decision;
- start `C14-RES-A-001`, `C14-RES-B-001`, `C14-RES-EVAL-001`, or P16.

Fixture v1 remains preserved as historical evidence. Formal C14 Resident validation must use v2.

## 2. Frozen fixture v2

- fixture version: `c14-resident-fixture-v2`
- supersedes: `c14-resident-fixture-v1`
- predecessor v1 SHA256: `sha256:a0f9dfd0985560ce80f568b6cd11d46b13f5dc352a664c005fcb165ea5a67485`
- v2 fixture SHA256: `sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253`
- event count: **36**
- Phase A: **24**
- Phase B: **12**
- timezone: `America/Los_Angeles`
- first event: `2026-10-01T07:12:00-07:00`
- Phase-A final event: cursor `24`, `c14resv2-024`, `2026-10-21T11:53:00-07:00`
- Phase-B first unreleased event: cursor `25`, `c14resv2-025`, `2026-10-23T07:08:00-07:00`
- final event: cursor `36`, `c14resv2-036`, `2026-10-31T12:03:00-07:00`

Formal v2 artifacts:

- `reviews/internal_habitation/c14-resident/v2/fixture/sealed_fixture.json`
- `reviews/internal_habitation/c14-resident/v2/fixture/fixture_manifest.json`
- `reviews/internal_habitation/c14-resident/v2/release/event_schema.json`
- `reviews/internal_habitation/c14-resident/v2/release/release_contract.md`
- `reviews/internal_habitation/c14-resident/v2/release/release_operator.py`
- `reviews/internal_habitation/c14-resident/v2/release/test_release_operator.py`
- `reviews/internal_habitation/c14-resident/v2/evaluator/EVALUATOR_ONLY_design_notes.md`

## 3. Blocker A closure — single-dimension leakage audit

**Result: PASS.**

The hidden positive design before handoff uses non-identical solo-work episodes whose meaning is distributed across schedule, work outcome, sleep/current condition, device attention, and bounded local user remarks.

Each individual Resident-visible dimension is insufficient to independently support the high-level longitudinal synthesis:

| Dimension | Audit | Why insufficient alone |
|---|---|---|
| `dim:schedule` | PASS | Shows continuous vs fragmented blocks but not resulting work completion/quality or user experience. |
| `dim:sleep` | PASS | Shows varying current condition but no task result or work-block structure; the short-sleep successful episode prevents a simple sleep explanation. |
| `dim:work_outcome` | PASS | Shows completed vs incomplete work but not the surrounding schedule/device/current-condition context. |
| `dim:device_activity` | PASS | Shows focus-mode/device state in selected episodes but cannot establish a durable user strategy or explain outcomes by itself. |
| `dim:conversation` | PASS | Contains only bounded same-day facts: reconnection cost after one interruption and one tired-day observation. It never states a general preference, trait, or longitudinal strategy. |

The Phase-A qualification episode at cursors 22–24 shows that an early collaborative workshop can resolve ambiguity and be followed by successful revision. It challenges an overbroad interpretation without directly stating how solo work should generally be arranged.

No exact expected Claim wording is present in Resident-visible files.

## 4. Matched negative control

Phase A contains three early-wake observations, comparable to the three principal positive work episodes.

The early wakes have distinct external causes:

- flight;
- building-service access requirement;
- international-team meeting.

A later unconstrained morning shows a substantially later wake with no early calendar requirement.

This control does not force silence. Silence, uncertainty, or a tightly bounded contextual cognition can all be valid; unsupported conversion into a stable trait is what the later evaluator must detect.

## 5. Blocker B closure — Phase-B underdetermination audit

**Result: PASS.**

The fresh-window planning situation intentionally leaves at least two reasonable options under Phase-B current facts alone:

1. **09:00 synchronization remains reasonable.** It can resolve two visual hierarchy questions early and reduce the chance of later rework.
2. **11:00 synchronization remains reasonable.** It can protect a longer early drafting interval and let the designer react to an initial structure.

Current facts do not mechanically eliminate either option:

- first drafting pass is estimated at 90–120 minutes;
- first draft target is 13:30;
- calendar is open 08:00–14:00 before a 14:30 review;
- the two visual questions matter but do not block drafting;
- the designer explicitly states both 09:00 and 11:00 are workable and gives a genuine benefit for each.

Therefore a later correct-looking plan cannot be explained solely by deadline arithmetic. The evaluator can inspect whether a durable Phase-A cognition was actually retrieved and materially participated in observable response/strategy/sequencing/planning.

No fixture-side expected action is encoded.

## 6. Blocker C closure — executable blind release operator

**Result: PASS.**

Executable helper:

`reviews/internal_habitation/c14-resident/v2/release/release_operator.py`

Operator version: `c14-blind-release-operator-v2`.

It implements only:

`cursor -> exact current event projection -> durable ingest acknowledgement -> next cursor`.

Supported commands:

- `init`
- `reveal`
- `ack`

`reveal` outputs exactly:

- `event_id`
- `sequence`
- `occurred_at`
- `dimension`
- `source_kind`
- `source_class`
- `modality`
- `resident_visible_payload`

It does not output hidden `phase`, manifest contents, evaluator notes, future payload, remaining-event semantics, or future content.

`reveal` records a pending reveal but **does not advance the cursor**.

`ack` requires:

- the exact current pending sequence;
- the exact current event id;
- a non-empty durable `object_id@revision` ingest reference.

Only then is a release receipt persisted and the cursor advanced.

The operator contains no NLP, keyword inference, semantic ranking, search-target selection, Claim selection, cognition generation, or revise/retract/silence logic.

## 7. Blind-release executable audit

The v2 fixture/operator was executed in an isolated local test environment.

Because the execution container had no GitHub DNS access, the branch could not be cloned directly. To avoid testing a merely similar copy, the test inputs were byte-anchored to the already-written GitHub candidate:

- fixture SHA256 matched `1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253`;
- fixture Git blob matched remote blob `7bd1935c9855ee5a71cd74b45bc693e01d21ca1b`;
- manifest Git blob matched remote blob `bc4da0c11274cafa47688f57bd3850cf92763957`;
- release operator Git blob matched remote blob `5a352b2268e67f0b260f80b330ea8ac6055a3f55`.

The exact-byte operator/fixture mechanical audit completed **19/19 PASS**:

1. Phase A init succeeds at cursor 1;
2. reveal cursor 1 emits exactly current Resident projection;
3. reveal does not advance cursor;
4. exact ack advances cursor to 2;
5. skip acknowledgement rejected;
6. repeated acknowledgement rejected;
7. acknowledgement without valid durable ingest ref rejected;
8. fixture digest mismatch rejected;
9. Phase-A cursor 24 reveal succeeds;
10. ack 24 advances state to next cursor 25;
11. Phase A reveal 25 rejected;
12. Phase B wrong-state start rejected;
13. Phase B exact handoff start succeeds;
14. Phase B reveal 25 succeeds;
15. Phase B cannot re-release Phase-A event;
16. hidden `phase` is absent from reveal stdout;
17. evaluator-only content cannot be emitted by release command;
18. future/N+1 payload is absent from reveal stdout;
19. fixture/state/operator version and mechanical shape/digest checks fail closed or pass as applicable.

The repository also contains a stdlib `unittest` suite encoding the same boundary cases. Its long boundary setup was made bounded by mechanically seeding a valid receipt chain for prior already-acknowledged cursors, while the actual cursor-24 reveal/ack and cursor-25 A/B boundary are still exercised through the real operator.

## 8. GitHub Actions note

A reproducible PR workflow was added:

`.github/workflows/c14-resident-fixture-v2.yml`

GitHub's workflow/status API reported **no run/status record** for the app-authored PR head during this task. This is not represented as CI GREEN.

The completion Gate for this Life Director task is therefore the explicit exact-byte mechanical execution above plus repository diff/digest verification. No CI result is fabricated.

## 9. Repository-scope audit

Before completion evidence was added, GitHub compare from started main showed only:

- the v2 fixture/evaluator/release/test files; and
- the dedicated v2 mechanical workflow.

Results:

- `src/aios_core/**` changes: **0**
- fixture-v1 mutations: **0**
- v1 remains historical evidence: **PASS**
- no Resident semantic execution: **PASS**

A final main-to-candidate diff must again be checked before merge.

## 10. Deferred work

Semantic habitation belongs exclusively to later windows:

`C14-RES-A-001 -> C14-RES-B-001 -> C14-RES-EVAL-001`.

This task issues no semantic cognition PASS verdict and does not start any of those tasks.
