# WINDOW 22 PM Scope / Publication Clarification

Date: 2026-10-03

Task: `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003`

Fresh main at ruling: `32dd012f72fee9ca54d153a6d7ae5fbc3f9044aa`

## Decision

Window 22 remains the unique active corrective.  Its local Route-B experiment is **not**
accepted and is **not** REVIEW_READY, but the two issues reported by the engineer are
classified as follows.

### W22-SCOPE-001 — C15 persistence/operator coupling

**Disposition: NON-BLOCKING FOR THIS CORE CORRECTIVE / OUT OF SCOPE / DOWNSTREAM COMPATIBILITY DEBT.**

The existing binding governance record
`governance/C15_RCC_RES_B_PERSISTENCE_SCOPE_ADJUDICATION_2026-09-28.md` establishes that
`tools/c15_persistence/**` is a habitation/release harness, is not shipped by the
`aios-core` package, and must not drive Core product scope expansion.  Window 21 C3-8
also expressly forbids modifying C15 persistence/operator/Resident evidence in Corrective-003.

Therefore the reported `DurableTrustedReturnMissing` coupling in
`tools/c15_persistence/operator_session.py` does **not** authorize Window 22 to edit that
tool or its persistence suite.  Those failures are recorded as a downstream compatibility
signal for the already-planned operator/provenance corrective after Core re-freeze and fresh A.

The broad `tests/c15_persistence/**` suite is not part of the formal full-Core regression
command.  The historical resident-visible gate remains only the separately governed tooling
check and OBS-W20-002 remains non-blocking tooling debt; Window 22 must not repair it.

### W22-CORE-REGRESSION-001 — 81 integration failures

**Disposition: BLOCKING UNTIL RESOLVED, BUT RESOLUTION IS ALREADY INSIDE WINDOW 22 SCOPE.**

The formal Core gate explicitly runs:
`tests/unit tests/integration tests/runtime tests/habitation`.

Therefore 81 failures under `tests/integration/**` cannot be waived by PM and cannot be
offset by Suite A/B or W17 greens.

However, Window 22 is already authorized to modify directly-related tests.  If an integration
fixture directly encodes the removed self-trusting live-window mechanism, the engineer may
update it to exercise the sanctioned verifier/external-proof route, provided every changed
historical test is documented as `TIGHTEN_ONLY`:

- preserve the old expectation and reason for replacement;
- delete no security assertion without an equal-or-stronger replacement;
- do not turn a privileged helper into an unverified shortcut;
- keep exactly-once, truthfulness, migration, RSA, replay and crash assertions intact.

If any failing integration test represents a still-required product behavior rather than an
obsolete authority fixture, the implementation—not the test—must be corrected.

No candidate may advance until the formal Core regression target is zero-failure.

### W22-DESIGN-001 — Route B and local object identity

**Disposition: ROUTE B REMAINS AUTHORIZED; LOCAL OBJECT IDENTITY IS NOT AUTHORITY.**

C3-1 expressly permits removing the live self-trust fast path in favour of genuine external
verifier/proof authority.

A requirement that `record_response` receive "the exact Core object" is acceptable only as an
internal consistency guard.  It must not itself:

- mint a trusted receipt or handoff;
- establish provider-return authenticity;
- promote a verifier-less post-boundary attempt out of `in_doubt`;
- make caller bytes recovery-eligible;
- create a reflection-recoverable replacement for the removed live window.

If object identity is doing any of those things, BLK-W20-001 remains open.

### W22-PUBLICATION-001 — no GitHub write credential in the engineering sandbox

**Disposition: PUBLICATION BLOCKS REVIEW_READY, NOT LOCAL ENGINEERING COMPLETION.**

Window 22 is authorized to continue locally under this clarification despite the sandbox's
lack of push credentials.  It must finish all in-scope engineering, attack-matrix work,
historical-test audit, workflow strengthening, and local regression.

Its maximum local terminal state is:

`ENGINEERING_COMPLETE_PENDING_PUBLICATION / GITHUB_PUBLICATION_BLOCKED`

It must export an immutable git bundle (preferred) plus patch/evidence/checksums containing the
exact local candidate.  It must not claim `REVIEW_READY` or
`READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE` until a later publication-recovery window pushes the
exact candidate, opens the new PR, and obtains the required exact-head CPython 3.12.14 formal CI.

The publication window must not change the candidate bytes while transporting them.  If a new
commit is required, that new published SHA becomes the candidate and must receive the formal run.

## Remaining mandatory Window 22 work

Before local engineering completion:

1. Resolve all full-Core regression failures under unit/integration/runtime/habitation.
2. Complete the full C3 attack matrix, including the four still-uncovered items.
3. Strengthen the formal workflow so it pins Window 20 failed candidate/review/probe identities
   rather than reusing the historical W14 RED job.
4. Keep Suite A = 0/4 failures, Suite B = 0/7 failures, W17 = 0/14 failures.
5. Preserve migration/RSA/not_submitted/exactly-once/R5 positives.
6. Do not edit `tools/c15_persistence/**`, `tests/c15_persistence/**`, C15 operator state,
   Resident evidence, or review branches.
7. Export the exact local branch/commit as bundle + patch + evidence manifest.

Window 23 remains BLOCKED.
