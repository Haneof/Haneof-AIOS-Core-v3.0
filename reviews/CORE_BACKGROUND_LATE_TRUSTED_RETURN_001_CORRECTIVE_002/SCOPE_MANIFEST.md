# SCOPE_MANIFEST — Corrective-002 changed-file audit (`C2-10`)

Allowed scope for this window: `src/aios_core/runtime/**` (plus minimal directly
related Core source), `tests/**`, the new
`reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002/**`, and minimal
`.github/workflows/core-background-late-trusted-return-001.yml` changes so that the
exact formal gate covers the new tests.

The PR diff versus fresh main `ca47087…` has two layers:

1. `f088ce10` — *carry-forward*: re-materialisation of the 14 accepted Corrective-001
   engineering files (byte-identical blobs, verified against `cb8a6b3c…`) onto fresh
   main.  `git diff --stat main..f088ce10` → 14 files, 2255 insertions, 217 deletions.
2. the Corrective-002 commits — `git diff --stat f088ce10..HEAD` →
   30 files, 3629 insertions, 127 deletions, listed below.

Total PR diff: 37 files, 5801 insertions, 261 deletions.

## Changed by Corrective-002 (vs the carry-forward base `f088ce10`)

| Path | Kind | Why |
| --- | --- | --- |
| `src/aios_core/runtime/background_attempt.py` | modified | C2-1/C2-2 (live-only receipt/handoff writer, removed minting oracle), C2-4 (verify-before-convert migration) |
| `src/aios_core/runtime/late_return.py` | modified | C2-5/C2-6 (canonical proof/key-id grammar, RSA parameter validation) |
| `src/aios_core/runtime/live_return.py` | new | C2-2 ephemeral call-stack-scoped live return authority |
| `src/aios_core/runtime/cognitive_runtime.py` | modified | C2-2 (issue the window only around the provider-handler frame; 3-arg authenticator) |
| `src/aios_core/runtime/turn_runtime.py` | modified | C2-2 (capture wiring; the removed runtime-level mint callback) |
| `src/aios_core/runtime/__init__.py` | modified | export the new authority/error symbols |
| `tests/runtime/test_background_model_attempt.py` | modified | historical tests now drive the real ephemeral window (stricter) |
| `tests/runtime/test_cognitive_runtime_trusted_return.py` | modified | 3-arg authenticator + ephemeral-window invariants (stricter) |
| `tests/runtime/test_late_return_canonical_encoding_002.py` | new | C2-9 CA2-010…CA2-014 |
| `tests/integration/test_core_background_response_recovery_001.py` | modified | historical relay-return simulation moved onto the real live window (stricter) |
| `tests/integration/test_core_background_response_recovery_001_corrective_001.py` | modified | same |
| `tests/integration/test_core_background_trusted_return_adversarial_001.py` | modified | same + asserts the removed mint helper is gone and `live_window=None` is refused |
| `tests/integration/test_core_background_late_trusted_return_corrective_002.py` | new | C2-9 integration matrix |
| `.github/workflows/core-background-late-trusted-return-001.yml` | modified (2 lines) | add the two new test files to the existing formal phases so the exact gate executes them |
| `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002/**` | new | this evidence package (16 mandated files + raw logs) |

## Explicitly untouched (forbidden / out of scope)

`tools/c15_persistence/**`, `tools/c15_preflight/**`, `evidence/w08/**`,
`reviews/internal_habitation/**`, any Resident/evaluator evidence, retired run
state, persistence remote refs, `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_001_IA_WINDOW_17/**`
(Window 17 review evidence), PR #302/#305/#308, review branches
`arena/01a0f231-…` / `arena/01a0fd4d-…`, Window 14 canonical review `84457bad…`.

## Verified mechanically

```
$ git diff --stat f088ce10..HEAD
 .github/workflows/core-background-late-trusted-return-001.yml   |   2 +
 src/aios_core/runtime/__init__.py                              |   9 +
 src/aios_core/runtime/background_attempt.py                    | 520 +++++----
 src/aios_core/runtime/cognitive_runtime.py                     |  85 +-
 src/aios_core/runtime/late_return.py                           | 203 +++-
 src/aios_core/runtime/live_return.py                           | 281 +++++  (new)
 src/aios_core/runtime/turn_runtime.py                          |  24 +-
 tests/integration/test_core_background_late_trusted_return_corrective_002.py | 1098 ++ (new)
 tests/integration/test_core_background_response_recovery_001.py             |   41 +-
 tests/integration/test_core_background_response_recovery_001_corrective_001.py | 40 +-
 tests/integration/test_core_background_trusted_return_adversarial_001.py    |   57 +-
 tests/runtime/test_background_model_attempt.py                              |   41 +-
 tests/runtime/test_cognitive_runtime_trusted_return.py                      |   37 +-
 tests/runtime/test_late_return_canonical_encoding_002.py                    |  333 ++ (new)
 reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002/**           | (evidence)
$ git diff --name-only main..HEAD -- tools/c15_persistence tools/c15_preflight reviews/internal_habitation
(empty)
$ git diff --check
(clean)
```

No architecture expansion was performed: no new storage truth source, no second
cognition state, no runtime/World/cognition/C15/operator/Resident-protocol
refactor, no UI or hardware change.  Non-necessary findings are recorded as
observations only (see `TRUST_MINT_PATH_AUDIT.md` §6 and
`CORRECTIVE_002_ATTACK_MATRIX.md` §D).
