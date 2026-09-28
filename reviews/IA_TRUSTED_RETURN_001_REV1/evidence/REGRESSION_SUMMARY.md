# Reviewer-Executed Regression Summary

Environment: CPython **3.12.14** / pytest **8.4.2** / pydantic **2.13.5** / SQLite **3.51.1**
Target: exact candidate `1ebf51c4cb905e2a2578a09b64007b50bca0d4ac`

## Complete run — `evidence/full_regression.txt`

```
5 failed, 867 passed, 3 xfailed in 237.95s (0:03:57)
```

## Split

| group | collected | passed | failed | xfailed |
|---|---|---|---|---|
| candidate-owned suite (`tests/`, excluding reviewer probes) | **816** | **816** | **0** | 0 |
| reviewer adversarial suite (`tests/independent_acceptance/`) | 59 | 51 | **5** | 3 |
| **total** | 875 | 867 | 5 | 3 |

The 816 candidate-owned tests reproduce the author's reported 816/816 exactly, on a
**freshly built reviewer environment**, with no reliance on author workflow
`36384741145`.

**Zero candidate-owned tests failed.** All 5 failures are reviewer probes, and all 5
are the same defect class (IA-BLK-TRUSTED-RETURN-001).

## Per-suite results (reviewer-executed)

| suite | result |
|---|---|
| candidate trusted-return recovery + adversarial + R5 + R5-conflicts + response-recovery | **78 passed** in 12.03s |
| candidate R5 suite alone | 11 passed |
| reviewer adversarial suite (rev7, binding) | 51 passed / 5 failed / 3 xfailed |
| complete pytest regression | 867 passed / 5 failed / 3 xfailed in 237.95s |

## Failing node ids (all reviewer, all one defect class)

```
tests/independent_acceptance/test_ia_capability_breadth.py::test_ia_capability_family_r5c_exactly_once[form_event]
tests/independent_acceptance/test_ia_capability_breadth.py::test_ia_capability_family_r5c_exactly_once[propose_cognitive_policy]
tests/independent_acceptance/test_ia_capability_breadth.py::test_ia_capability_family_r5c_exactly_once[propose_dimension]
tests/independent_acceptance/test_ia_capability_breadth.py::test_ia_capability_family_r5c_exactly_once[propose_entity]
tests/independent_acceptance/test_ia_capability_breadth.py::test_ia_capability_family_r5c_exactly_once[propose_goal]
```

## Skips and xfails — explained

* **0 candidate-owned skips.**
* **3 reviewer `xfail`** — `test_ia_auth04/05/06`. These mutate durable SQLite rows
  directly (attempt/provider, attempt/model, attempt/provider_request_id). Direct
  durable-state tampering by trusted code is inside the **accepted trust-root
  limitation** frozen by the historical lineage and explicitly preserved by task §22.
  They are recorded as informational, not as blockers, and are not counted in the
  blocker total.

## Durations

See the `--durations=15` block in `evidence/full_regression.txt`.
