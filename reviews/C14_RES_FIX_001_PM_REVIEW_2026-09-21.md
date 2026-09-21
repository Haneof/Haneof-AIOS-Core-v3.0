# C14-RES-FIX-001 Independent PM Review

> Date: 2026-09-21  
> Reviewed main: `e503144b84cbaf065ab68dec721e660977553196`  
> PR: #68  
> Fixture v1 digest: `sha256:a0f9dfd0985560ce80f568b6cd11d46b13f5dc352a664c005fcb165ea5a67485`  
> Verdict: **MECHANICAL PASS / SEMANTIC TEST-DESIGN BLOCKER**

## 1. What passed

The v1 fixture correctly provides:

- 36 unique sequential events;
- strict monotonic timestamps;
- Phase A 24 / Phase B 12;
- one sealed handoff boundary at 24 -> 25;
- manifest/digest/version metadata;
- Resident-visible projection rules;
- evaluator-only design notes;
- no Core changes;
- no Resident execution.

These artifacts remain useful historical evidence and must not be deleted or rewritten in place.

## 2. Blocker A — the positive case is not genuinely cross-dimensional enough

The C14 acceptance rule requires at least one case where no single dimension independently supports the durable cognition and the Resident must integrate evidence across dimensions.

In fixture v1, Phase-A conversation events themselves substantially disclose the intended synthesis.

Examples:

- cursor 4: the user explicitly links writing before meetings with feeling mentally clearer;
- cursor 8: the user explicitly links a fragmented morning with difficulty reconnecting in the afternoon;
- cursor 24: the user explicitly states that solo writing is better with quiet time first.

A careful model could form the intended cognition from `dim:conversation` alone without needing schedule, outcome, sleep, or device evidence.

That makes the test unable to prove genuine cross-dimensional cognition.

### Required v2 correction

Before the Phase-A handoff, conversation events may provide local context but must not directly state the hidden longitudinal synthesis.

The intended pattern should only become reasonably supportable by combining multiple dimensions such as:

- schedule structure;
- work outcomes;
- sleep/current condition;
- device/attention state;
- bounded user remarks.

No single dimension should independently establish the high-level cognition.

## 3. Blocker B — Phase B decision is too mechanically obvious from current facts

Fixture v1 asks the fresh Resident to choose between 09:00 and 11:30 synchronization while also stating:

- the writing task needs about 2.5 hours;
- first draft should be ready before noon;
- design review does not block drafting.

Those current facts alone strongly favor preserving the long morning block and synchronizing later.

Therefore Resident B could make the expected-looking choice without retrieving or using any Phase-A cognition.

This weakens the central C14 proof:

> past cognition stored in AIOS materially changes future behavior.

### Required v2 correction

The fresh-window decision must remain meaningfully underdetermined from Phase-B current facts alone.

At least two options should be independently plausible.

Example design shape:

- enough time exists for either sequencing option;
- early collaboration may offer some immediate value;
- later collaboration may preserve a focused solo block;
- no hard deadline arithmetic forces one answer.

The evaluator must then be able to observe that a retrieved Phase-A cognition materially participated in the actual decision together with current evidence.

No predetermined correct option is required.

## 4. Blocker C — no executable blind release operator is committed

The release contract describes a trusted mechanical Release Operator, but fixture v1 does not include an executable operator/helper.

A Resident window must not open `sealed_fixture.json` directly. Merely telling the Resident to "only look at one entry" is weaker than providing a mechanical interface that emits only the current projection.

### Required v2 correction

Add a deterministic release helper outside `src/aios_core/**`, for example:

`reviews/internal_habitation/c14-resident/release/release_operator.py`

It must:

- read and verify the sealed fixture digest internally;
- read a durable cursor state/receipt;
- emit only the current Resident-visible projection;
- enforce Phase-A maximum cursor 24 and Phase-B start 25;
- never print future events, manifest content, evaluator notes, or hidden `phase` metadata;
- support an explicit post-ingest acknowledgement step before advancing the cursor;
- reject skip/repeat/reorder;
- record a mechanical release receipt;
- never choose semantic capability calls or cognition.

Resident A/B may execute this helper but must not open the fixture/manifest/evaluator files directly.

## 5. Required v2 fixture policy

Create a new fixture version rather than silently mutating v1 history.

Recommended:

- `c14-resident-fixture-v2`
- new SHA256;
- new manifest;
- updated release contract/version if needed;
- updated evaluator-only notes;
- updated event schema only if schema changes.

Keep event volume roughly 24-45 and preserve the fresh-window boundary concept.

The v2 evaluator notes may describe the hidden design, but must not prescribe one exact Claim sentence or one exact future action.

## 6. Required validation

Before unlocking Resident A, PM requires mechanical proof that:

1. no Resident-visible single dimension contains a direct statement of the intended high-level positive cognition before handoff;
2. the Phase-B decision has at least two plausible choices from current Phase-B facts;
3. the release helper can reveal cursor N without exposing N+1;
4. the helper cannot advance before explicit ingest acknowledgement;
5. Phase A cannot release cursor 25;
6. Phase B cannot start before cursor 25;
7. digest mismatch fails closed;
8. no `src/aios_core/**` change occurs;
9. no Resident semantic model is run.

## 7. Decision

Do not start `C14-RES-A-001` on fixture v1.

Insert one dedicated test-design hardening task:

`C14-RES-FIX-002`

After v2 passes independent PM review, `C14-RES-A-001` may be unlocked.
