# Corrective-003 Publication Artifact Loss / Window 22 Rerun Release

Date: 2026-10-03

Task: `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003`

Fresh main: `054d15cd6ac52718c39ec34d388dd3186d6f7929`

## Ground truth

PM fresh remote verification establishes:

- PR #310 remains OPEN / UNMERGED / FROZEN at
  `fec30bd1495017bf13f08b0ef5b1e241dfb0e247`.
- PR #311 remains REVIEW_ONLY / UNMERGED at
  `fd52ea8243970187b439208d7061c04c68b6b8ea`.
- the previously reported Window 22 local final commit
  `39917591f07c2ed1aa679f9098c1fc368c3af42e` is not present in the GitHub
  repository object graph;
- no remote Corrective-003 engineering branch exists;
- the previously reported bundle/evidence artifacts were local-only and are not
  available as durable publication artifacts.

Therefore the released Publication Recovery step has no durable artifact to recover.

## Disposition

The prior Window 22 local result is retained only as:

`HISTORICAL_LOCAL_ONLY / NON_DURABLE / NOT_ACCEPTANCE_EVIDENCE`

Its reported test counts, hashes and candidate identity may be used only as navigation/context.
They must not be treated as proof for the rerun.

`WINDOW 23A PUBLICATION RECOVERY = BLOCKED / ARTIFACT_UNAVAILABLE`

`WINDOW 23 FRESH INDEPENDENT ACCEPTANCE = BLOCKED`

## Unique next READY

`WINDOW 22-RERUN-001`

Formal task remains:

`CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003`

Role: Core Runtime Corrective Engineer.

This is a fresh rerun from current fresh main and the frozen failed candidate/reviewer evidence.
It must not reconstruct from the lost local candidate.

## Mandatory publication-capability preflight

Before any corrective source edit or expensive local test run, the rerun must prove it can
durably publish to GitHub.

At minimum:

1. fresh fetch current main;
2. verify GitHub authentication/write capability without mutating protected refs;
3. prove it can push its new engineering branch (or otherwise create/update that branch through
   an authenticated repository write path);
4. if write capability is absent, stop immediately:
   `GITHUB_PUBLICATION_CAPABILITY_REQUIRED`.

The rerun must not repeat the prior pattern of completing a local-only candidate that cannot be
published.

## Frozen security and scope rules

The rerun inherits all binding Corrective-003 requirements from Window 21 plus the PM Window 22
clarifications:

- C3-1 through C3-8 remain binding.
- Suite A / Suite B / W17 frozen probes must be extracted from canonical remote review commits and
  hash-verified; no probe edits.
- Route B remains permitted.
- local object identity may be an internal consistency guard only, never authenticity authority.
- verifier-less post-boundary attempts remain permanently fail-closed absent genuine external proof.
- `tests/unit tests/integration tests/runtime tests/habitation` must finish with zero failures/errors.
- directly-related stale authority fixtures may change only under per-test TIGHTEN_ONLY audit.
- `tools/c15_persistence/**` and `tests/c15_persistence/**` are out-of-scope downstream debt and
  must not be modified.
- root `.gitignore` is not in scope.
- only the single Corrective-003 workflow may be changed under `.github/workflows/**`.
- historical failed/review PRs/branches remain immutable.
- no Resident, RC-refreeze, evaluator, release or merge activity.

## Construction rule

Start from fresh current main. Since current main after Window 21 contains governance but not the
failed Corrective-002 engineering implementation, the rerun may carry forward only the needed
engineering paths from frozen `fec30bd…`, byte-exact before modification, with a written manifest.

The lost local Window-22 candidate `39917591…` must not be used as a source.

## Durable completion rule

The rerun is not complete until all of the following are durable on GitHub:

- new engineering branch;
- exact candidate head;
- new engineering PR;
- exact-head formal CPython 3.12.14 workflow run;
- formal gates green;
- candidate PR remains OPEN / UNMERGED / DO NOT MERGE.

Local bundles may be retained as backup, but they are not a substitute for durable publication.

Success terminal state:

`REVIEW_READY / READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE / DO_NOT_MERGE`

Only after PM independently verifies the remote exact head and formal CI may Window 23 Fresh IA be
released.
