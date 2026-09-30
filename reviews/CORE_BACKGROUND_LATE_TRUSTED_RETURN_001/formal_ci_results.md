# Formal CI results — CPython 3.12.14 (final candidate)

Candidate pin `dab7af82cd009dbc8ab8838c839e16a2b2a803e1`
parent `30a38c48418b220197213cf412aa6ea1fd977a33`
tree `bbe393c617a0da887391a1dade47272d3dd13947`
branch `arena/01a0f07b-haneof-aios-core-v3-0` → PR #305

## Exact formal environment

Python **3.12.14** / Pydantic **2.13.5** / pytest **8.4.2** /
SQLite **3.45.1** / OpenSSL **OpenSSL 3.0.13 30 Jan 2024**

## Exact JUnit counts (formal gate, run 36678925987)

| suite | tests | failures | errors | skipped | time (s) |
|---|---|---|---|---|---|
| full Core regression | 1059 | 0 | 0 | 0 | 283.370 |
| accepted trusted-return regression | 249 | 0 | 0 | 0 | 34.125 |
| resident-visible behavioural + historical scope gate | 1 | 0 | 0 | 0 | 0.701 |
| late trusted return / not_submitted / adversarial | 61 | 0 | 0 | 0 | 10.636 |

## Step-level result of the formal 3.12.14 gate

`formal-core-gate` — **success**. Notably `ok` (executed and passed, not skipped):

- `Verify required refs resolve (no shallow-clone false green)`
- `Resident-visible behavioural and historical scope gate`
- `Complete Core regression`

Only `Annotate failure identities` is `skipped`, which is its intended
`if: failure()` behaviour.

## All 17 repository workflows on this exact head

| workflow | run | conclusion |
|---|---|---|
| c09-wake-dispatch | 36678925930 | success |
| c14-cognitive-derivation-loop | 36678926052 | success |
| c14-cognitive-derivation-runtime | 36678925955 | success |
| c15-cognition-evidence-policy | 36678925921 | success |
| constitutional-cognition-closure | 36678926047 | success |
| **core-background-late-trusted-return-001** | **36678925987** | success |
| core-background-trusted-return-recovery-001 | 36678925933 | success |
| core-rc-refreeze-002-formal-gate | 36678925993 | success |
| core-scale | 36678926151 | success |
| fused-turn-runtime | 36678925938 | success |
| p10-ai-world-gate | 36678926037 | success |
| p11-dimension-gate | 36678926032 | success |
| p12-execution-gate | 36678925927 | success |
| p14-long-context | 36678925942 | success |
| p15-periodic-review | 36678925906 | success |
| p16-convergence-gate | 36678925948 | success |
| p9-revision-gate | 36678926007 | success |

PR #305: **33/33 checks passing**, state `OPEN`, `mergedAt = null`.

## Provenance of the values above

GitHub's `results-receiver.actions.githubusercontent.com` and
`productionresultssa*.blob.core.windows.net` hosts are unreachable from the
engineering sandbox (both terminate the connection with `EOF`), so neither the
run log nor the uploaded artifact could be downloaded. The values above were
read from the check-run **annotations API** for check run `109769899901`, which
carries the `::notice::` output emitted by the workflow's own environment and
JUnit publishing steps. They are the workflow's self-reported values, retrieved
verbatim, not reconstructed or estimated.

The uploaded artifact `core-late-trusted-return-formal-results` (48,508 bytes)
remains available on the run for a reviewer with normal network access.

## Local development runtime (not the formal gate)

CPython 3.11.2 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.40.1 /
OpenSSL 3.0.20 7 Apr 2026. Full Core suite on a full-history checkout:
**1059 passed, 0 failed, 0 errors, 0 skipped**.
