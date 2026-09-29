# C15 Resident A Corrective-003 — Operator Prep IA PASS and Resident Release Adjudication — 2026-09-29

## Control-plane status

```text
C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003
= ACCEPTANCE_PASS / blocker=0
= ACCEPTED_EXACT / IMMUTABLE

C15-RCC-RES-A-RERUN-004-CORRECTIVE-003
= READY

Persistence Corrective-003
= BLOCKED_ON_FRESH_RESIDENT_A

Resident B / Resident C / evaluator / C15 close
= BLOCKED
```

This file is control-plane governance.

**The Fresh Resident A must not read this file.**
It is intentionally outside the Resident clean-room startup set.

## Accepted Operator Prep candidate

PR #292 remains OPEN / UNMERGED / EVIDENCE-ONLY and immutable.

Accepted exact candidate:

- final evidence freeze H2: `42a63ed4416585fc0a02045e0bd5190f32a01a2b`
- H2 tree: `80440bdd70aa658053bc5bf33a902c46cd7138e0`
- corrected harness candidate H1: `77dac70e0cf054c3f0fb7d94a66dba221fe7d5de`
- H1 tree: `52aa366bc6548e86e805585baddbc0470cb69660`
- H1 parent / genuine RED freeze: `083dd9506f01ade04d4cbe805f58bf80d40607b0`
- pre-baseline C10/C11 probe freeze: `4b2ca9fd48da2f1f44789c664de66bd471a39ee9`

No merge of PR #292 is required or authorized by this adjudication.

## Fresh Independent Acceptance

Review-only PR #294 remains OPEN / UNMERGED / EVIDENCE-ONLY and immutable.

Exact review:

- review head: `30955cc7065d0d66cf4de43f833f1b1f9162b635`
- verdict: `ACCEPTANCE_PASS / blocker=0`
- disposition: `READY_FOR_PM_INTEGRATION`

The review independently reproduced:

- reviewer probes rev3: 50/50 PASS;
- Corrective-003 C10/C11: 18/18 PASS;
- C1-C3: GREEN;
- C4-C9: 103/103 PASS;
- Gates A/B/C/D: 24/7/2/5 PASS;
- exact runtime pins: CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1 / OpenSSL 3.0.13;
- packet/freeze/checksum integrity;
- no real Resident execution;
- no fixture/evaluator/release-state/cursor exposure.

Reviewer revision-1 failures were preserved and transparently triaged as probe/execution defects. Final revisions retained frozen source/hash/enumeration and passed without candidate repair.

## PM-approved Resident-safe launch packet

The exact packet approved for the real Fresh Resident A is:

Path inside the accepted Operator Prep package:

`reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/RESIDENT_SAFE_LAUNCH_PACKET.json`

Exact packet SHA-256:

`3c2d04c2de8557c3cb7329df4350c40b2ccc07520a7d3d51db206174b33266cc`

Packet status remains:

`PREP_REVIEW_READY`

This is intentional.

Do not mutate the accepted packet merely to rename its status. PM approval is external to the accepted artifact and is recorded by this control-plane adjudication.

The packet pins the accepted harness candidate:

`77dac70e0cf054c3f0fb7d94a66dba221fe7d5de`

and frozen RC:

- software `f20f2edfa7af00d0286493fd15196ca9503bc315`
- repository tree `1ac3a675b884167d3a29aa432e7ef3eaff94d404`
- Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`

## Exact Resident startup boundary

The Fresh Resident A may receive only the startup inputs already frozen by the clean-room contract and accepted packet:

1. `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_CORRECTIVE_003_CLEAN_ROOM_CONTRACT.md`;
2. canonical `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_RUN_CONTRACT.md`;
3. the exact PM-approved `RESIDENT_SAFE_LAUNCH_PACKET.json` above;
4. mechanical environment/harness status emitted by the accepted launch tools.

The Resident must not read this adjudication or any other control-plane material.

In particular, the Resident must not open/search/diff:

- task board;
- checkpoint;
- PM adjudications;
- #292 or #294 PR metadata/descriptions/comments;
- historical Resident runs/reviews;
- fixture/evaluator/release source;
- future events;
- Git history concerning prior Resident runs.

The operator may mechanically materialize/verify the exact accepted harness and frozen RC without exposing control-plane history or semantic materials to the Resident.

## Resident execution authorization

The real task now released is:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003`

Role:

`Real Resident AI — Fresh Corrective Resident A`

Allowed cursor range:

`1..13`

The Resident must:

- use a completely fresh private World;
- fresh index;
- fresh release-state;
- fresh Resident process/session identities;
- fresh runtime/checkpoint;
- fresh exchange ledger and request/response directories;
- use only the accepted Operator Prep harness and frozen RC;
- personally make every semantic decision from current legal RuntimeSnapshot/capability results;
- never use scripted cognition;
- process exactly one legally revealed event at a time;
- execute only genuinely due Wake/Review/Summary/derivation work;
- stop after cursor 13 and freeze evidence;
- never reveal cursor 14.

The Resident is not authorized to design or patch the harness.

If accepted harness verification fails before cursor 1:

`BLOCKED`

If any harness defect appears after cursor 1:

preserve state and return:

`BLOCKED`

Do not patch and continue.

## Resident deliverable

The real Resident must publish a new evidence-only Phase-A candidate and stop at:

`PHASE_A_COMPLETE / REVIEW_READY`

then:

`READY_FOR_INDEPENDENT_ACCEPTANCE`

No self-acceptance.

## Downstream remains blocked

This release authorizes only Fresh Resident A Corrective-003.

It does not authorize:

- Persistence Corrective-003;
- Resident B;
- Resident C;
- evaluator;
- C15 close;
- public tag/release.

Those remain blocked until Fresh Resident A completes and receives its own fresh Independent Acceptance plus PM adjudication.
