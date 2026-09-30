# Local full-Core suite result, including one explained non-behavioral failure

## What the final local full-Core run reports

Running the complete Core test tree on the final candidate content (CPython
3.11.2 / Pydantic 2.13.5 / pytest 8.4.2, SQLite 3.40.1, OpenSSL 3.0.20):

```
1 failed, 1058 passed in 306.64s (0:05:06)
FAILED tests/c15_persistence/test_resident_surface.py::test_resident_visible_surface_is_unchanged_by_the_durability_layer
```

This is an honest restatement of the run. An earlier record in this window said
`1059 passed in 300.21s`; that number was taken **before** the candidate was
committed, while `HEAD` still pointed at the baseline commit. See
"Correction of the earlier record" below.

## The single failure is a git-tree tripwire, not a behavioral regression

`tests/c15_persistence/test_resident_surface.py` shells out to
`tools.c15_persistence/resident_surface_check`, whose `ok` verdict is:

```python
ok = all(comparisons.values()) and all(scope["clean"] for scope in (...))
```

Two independent things are ANDed together. The first is the actual
Resident-visible-surface invariant (wired persistence path vs. the same Core run
with no durability layer). The second, `pinned_tree_diff_vs_base`, is computed as:

```python
subprocess.run(["git", "diff", "--stat", f"{base}...HEAD", "--", scope], ...)
... "clean": completed.stdout.strip() == ""
```

`clean` is therefore `False` for **any** commit that modifies `src/aios_core`,
regardless of runtime behavior. Window 13 is precisely a commit that modifies
`src/aios_core`, so the tripwire fires by construction.

## Evidence that the substantive invariant is intact

Running the checker directly against the candidate (`--base main`) and reading
the emitted evidence JSON, all **twelve** behavioral comparisons are `True`:

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

`result` is `RESIDENT_SURFACE_CHANGED` only because of the tree diff. The
Resident and the model observe byte-identical output, catalog, metering, world
revision and provider traffic with and without the durability layer.

Both C15 **pinned review trees** are also clean, so the standing scope
constraint holds:

```
reviews/internal_habitation/c14-resident/v2/release : clean = true
reviews/internal_habitation/c15-rcc/v1                : clean = true
src/aios_core                                         : clean = false  (the intended subject of this window)
```

## Why the same test passes in GitHub CI

`actions/checkout` defaults to `fetch-depth: 1`, so in CI the `main` ref does not
resolve. Reproduced against a fresh shallow clone of the candidate:

```
$ git rev-parse main
fatal: ambiguous argument 'main': unknown revision or path not in the working tree
$ git diff --stat main...HEAD -- src/aios_core
(no output)
```

Empty stdout is read as `clean=True`, so the tripwire silently passes in CI. That
is why the formal workflow's "Complete Core regression" step reports success. The
CI result is not independent confirmation that the tripwire passes; it is the
tripwire being unable to evaluate.

## Scope decision

`tools/c15_persistence/**` is explicitly out of scope for this window, and this
engineer is not a C15 operator. The tripwire was **not** worked around: no C15
tool, test, or evidence file was modified, and no attempt was made to make
`src/aios_core` unchanged, because that would mean not performing the assigned
corrective. The finding is recorded here and surfaced to reviewers instead.

Whichever way it is adjudicated, the decision belongs to the C15 owner. If the
tripwire is intended to be branch-scoped to C15 persistence work, the correct fix
is in the C15 tooling, not in this window's runtime change.

## Correction of the earlier record

The earlier `1059 passed` figure was produced while the implementation lived only
in the working tree and `HEAD` was still the baseline commit. In that state
`git diff main...HEAD -- src/aios_core` is empty, so the tripwire could not fire
and the count was 1059/1059. Once the candidate was committed, the same suite
reports 1058 passed plus this one explained tripwire failure. Both numbers refer
to the same test content; the difference is entirely the tree-diff tripwire.
