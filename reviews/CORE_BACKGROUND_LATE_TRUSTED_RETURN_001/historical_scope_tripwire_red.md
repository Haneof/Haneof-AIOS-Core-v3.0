# PRESERVED RED — HISTORICAL_SCOPE_TRIPWIRE_RED

**Classification: `HISTORICAL_SCOPE_TRIPWIRE_RED`**
**Explicitly NOT: `RESIDENT_BEHAVIOR_RED`**

This artifact exists to preserve a real failing test result. It must not be
deleted, re-labelled as green, or quietly made to disappear.

## The preserved RED

Full Core suite, full-history checkout, CPython 3.11.2 development runtime
(SQLite 3.40.1, OpenSSL 3.0.20), at candidate pin `dd88dca17d1927225015bf82b2180d114e9e29f7`:

```
1 failed, 1058 passed in 306.64s (0:05:06)
FAILED tests/c15_persistence/test_resident_surface.py::test_resident_visible_surface_is_unchanged_by_the_durability_layer
```

Raw assertion from that run:

```
AssertionError: resident surface check failed:
stdout: {
  "result": "RESIDENT_SURFACE_CHANGED",
  "evidence": ".../resident-surface-no-change.json"
}
```

## Why it is a scope tripwire and not a behaviour regression

`tools/c15_persistence/resident_surface_check.py` computes its overall `result`
as a conjunction:

```python
ok = all(comparisons.values()) and all(
    scope["clean"] for scope in (v for k, v in pinned.items() if isinstance(v, dict))
)
```

The first term is the genuine Resident-visible behaviour contract. The second
term is a git-diff emptiness check on `src/aios_core`, whose purpose is to show
that `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003` did not itself modify Core.

Measured on this candidate, the first term is fully satisfied:

| comparison | value |
| --- | --- |
| `resident_visible_payload` | True |
| `projection` | True |
| `ingest_receipt` | True |
| `capability_catalog` | True |
| `model_round_ordering` | True |
| `provider_request_bytes` | True |
| `provider_reply_bytes` | True |
| `directive_semantics` | True |
| `capability_side_effect_count` | True |
| `assistant_output` | True |
| `metering_rows` | True |
| `world_revision` | True |

**12/12 = TRUE.** The RED comes solely from the second term, which is `False`
because `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001` is an authorised Core change
and therefore necessarily has a non-empty `src/aios_core` diff against the
current base. `current Core diff != Resident-visible behaviour failure`.

Both frozen Resident review trees were clean at this pin:

```
reviews/internal_habitation/c14-resident/v2/release : clean = true
reviews/internal_habitation/c15-rcc/v1                : clean = true
```

## The shallow-clone false green that hid the scope question

CI reported green, but that green was not evidence. `actions/checkout` defaults
to `fetch-depth: 1`, so `main` does not resolve, `git diff main...HEAD` returns
empty output, and the tripwire reads `clean = true`. Reproduced directly against
a `git clone --depth 1` of the candidate:

```
$ git rev-parse main
fatal: ambiguous argument 'main': unknown revision or path not in the working tree
$ git diff --stat main...HEAD -- src/aios_core
(no output)
```

Consequence: the CI full-regression step did not prove the tripwire passed; the
tripwire could not evaluate at all. The old test was verified to pass in exactly
that shallow clone.

## Disposition

`tests/c15_persistence/test_resident_surface.py` was corrected (test-only) to
adjudicate the two constraints separately. `tools/c15_persistence/**` and the
committed historical evidence
`reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003/evidence/resident-surface-no-change.json`
were **not** modified. The `src/aios_core` zero-diff requirement was re-bound to
the Persistence Corrective-003 construction range it was actually written for:

```
016a2f7db5ed01b41fc614701079c507d2c2c02e  (base)
19476641be95e666068e6299f42df9a411f4c0ba  (accepted candidate)

git diff --stat 016a2f7d...19476641... -- src/aios_core   ->  empty
```

while that same range changed 56 files / 12,433 insertions elsewhere, so the
invariant is a real, non-vacuous assertion that Persistence C003 left Core alone.

The corrected gate was then proven to reject each failure mode by mutation:

| injected fault | result |
| --- | --- |
| `assistant_output` comparison forced False | **FAILED** — `resident-visible surface differs: assistant_output` |
| shallow clone, base ref unresolvable | **FAILED** — explicit "checkout is shallow" / ref-does-not-resolve message |
| historical range pointed at a Core-touching commit | **FAILED** — `Persistence Corrective-003 modified Core` |

The gate is therefore neither a rubber stamp nor a false green.
