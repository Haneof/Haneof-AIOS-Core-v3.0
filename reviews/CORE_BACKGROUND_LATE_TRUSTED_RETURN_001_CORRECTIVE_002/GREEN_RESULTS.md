# GREEN_RESULTS — Corrective-002 local verification

Runtime: `/home/user/.local/venv311/bin/python` → CPython **3.11.2**, pydantic
**2.13.5**, pytest **8.4.2**, SQLite **3.40.1**, OpenSSL **3.0.20**.
This is the pre-flight runtime only; the formal runtime evidence is
`FORMAL_CI_RESULTS.md` (CPython 3.12.14 at the exact final head).

Every command was run with `-o addopts=''` and `PYTHONPATH` pointing at this tree.

## 1. Frozen Window 17 probes (unchanged file, `C2-8`)

```
$ PYTHONPATH=<head>/src python /home/user/_w19/cand/reviewer_probes/window17_independent_attack.py
PASS | IA17-MINT-001 … PASS | IA17-SIGKILL-001
SUMMARY | probes=14 failures=0      # exit 0
```

Full raw log: `GREEN_FROZEN_PROBE_RAW.txt`.  RED counterpart: `BASELINE_RED.md`
(`probes=14 failures=6`, exit 1).  Blocker → probe closure:

| Blocker | Probes that failed RED | Status GREEN |
| --- | --- | --- |
| `BLK-W17-001` | `IA17-MINT-001`, `IA17-MINT-002`, `IA17-OBJGRAPH-001` | PASS |
| `BLK-W17-002` | `IA17-DOWNGRADE-001`, `IA17-MIGRATE-002` | PASS |
| `BLK-W17-003` | `IA17-RSA-DELIMITER-001` | PASS |
| W16/W17 positives | other 8 probes | unchanged PASS |

## 2. Formal-workflow phases reproduced locally (same file lists as the YAML)

| Job / step | Files | tests | failures | errors | skipped |
| --- | --- | --- | --- | --- | --- |
| `phase-a-truthfulness` / Focused Route-B truthfulness | 3 | 35 | 0 | 0 | 0 |
| `phase-bc-verifier-only` / Route-B and CA1-CA5 (now incl. `test_late_return_canonical_encoding_002.py`) | 5 | 85 | 0 | 0 | 0 |
| `phase-bc-verifier-only` / Accepted trusted-return regression | 4 | 50 | 0 | 0 | 0 |
| `phase-ef-sigkill-and-focused` / Real SIGKILL recovery | 1 | 1 | 0 | 0 | 0 |
| `phase-ef-sigkill-and-focused` / Trusted-return + recovery focused (now incl. `test_core_background_late_trusted_return_corrective_002.py`) | 20 | 291 | 0 | 0 | 0 |
| `phase-f-full-core-regression` / Full Core regression (`tests/unit tests/integration tests/runtime tests/habitation`) | 896 | 0 | 0 | 0 | 0 |

`phase-f` JUnit: `tests=896 failures=0 errors=0 skipped=0`, wall clock 227.35 s.

## 3. New C2-9 files

| File | tests | result |
| --- | --- | --- |
| `tests/runtime/test_late_return_canonical_encoding_002.py` | 64 | 64 passed |
| `tests/integration/test_core_background_late_trusted_return_corrective_002.py` | 20 | 20 passed (incl. a real `SIGKILL` fork case) |

## 4. Historical tests updated (stricter, see `NOT_SUBMITTED_REGRESSION.md`)

`tests/runtime/test_background_model_attempt.py`,
`tests/runtime/test_cognitive_runtime_trusted_return.py`,
`tests/integration/test_core_background_response_recovery_001.py`,
`tests/integration/test_core_background_response_recovery_001_corrective_001.py`,
`tests/integration/test_core_background_trusted_return_adversarial_001.py` —
all passing locally within the phase counts above.

## 5. Local deviation, disclosed (not a regression, not in the formal core scope)

`tests/c15_persistence/test_resident_surface.py` fails **locally** on any branch
that changes `src/aios_core` because its checker additionally requires the pinned
tree to be unchanged relative to a **local `main` ref**
(`_pinned_tree_digest`, `tools/c15_persistence/**` — explicitly out of scope for
this window).  In its own evidence all twelve behavioural comparisons are `true`;
only `pinned src/aios_core clean=False`, which is precisely the intended
Corrective-002 change.  Evidence that this is an environment artifact:

* the identical failure was observed by the Window 17 reviewer on the unmodified
  candidate (`raw/candidate_resident_surface_1.txt`) while the base head passed
  (`raw/candidate_resident_surface_base_head_1.txt`: `1 passed`);
* the candidate's CI job `110903891101` ran the same step to `success` on a
  `src/aios_core`-changing PR.

`set -e`-style blocking is therefore not expected; the formal run at the exact head
is the authority (`FORMAL_CI_RESULTS.md`).

## 6. What these numbers are not

They are **not** formal-runtime results.  No 3.11.2 number is presented as a formal
gate result, no historical test count was fabricated, and no failing probe was
deleted or relaxed to obtain GREEN.
