# BASELINE_RED — Window 22-RERUN-001

Contract §14 RED-first. Every run below used the frozen probe bytes freshly extracted from the
canonical review commits and hash-verified in `PROBE_MANIFEST.md`. No probe byte was modified
(`C3-6`).

Environment for all local runs (see `PREFLIGHT_ENVIRONMENT` note at the bottom):
CPython 3.11.2, pytest 8.4.2, pydantic 2.13.5, SQLite 3.40.1, OpenSSL 3.0.20 — these probe
suites are standalone scripts and do not use pytest.

---

## 1. Failed candidate materialized

`fec30bd1495017bf13f08b0ef5b1e241dfb0e247` was materialized in a **detached git worktree**
(`/tmp/wt-fec`) so that the frozen failed candidate could be executed without touching this
window's engineering branch, and without committing to / force-pushing / rebasing PR #310:

```
git worktree add --detach /tmp/wt-fec fec30bd1495017bf13f08b0ef5b1e241dfb0e247
```

PR #310's remote head branch `arena/01a10010-haneof-aios-core-v3-0` was **never** pushed to.

## 2. Suite A on the failed candidate — RED REPRODUCED

Command:

```
PYTHONPATH=/tmp/wt-fec/src python window20_independent_attack.py
```

Raw output: `raw/RED_SUITE_A_ON_FAILED_CANDIDATE_fec30bd.txt` (SHA-256
`a138c12d8c1d807280ed38ef534f3de3325f8cb6260173543cfc5e5312a67506`).

```
FAIL | IA20-MINT-003
  actual: FORGED MINT VIA PUBLIC LIVE-WINDOW API: minted=True, state=metered, receipts=1,
          handoffs=1, responses=1, meters=1,
          turn_response='FORGED_VIA_PUBLIC_LIVE_WINDOW_API_NO_PROVIDER_CALL',
          genuine_rsa_return_conflicted=True
FAIL | IA20-MINT-004
  actual: state=metered, receipts=1, handoffs=1, responses=1, meters=1,
          turn_response='FORGED_ON_VERIFIERLESS_ATTEMPT_VIA_PUBLIC_WINDOW', refusal=None
FAIL | IA20-OBJGRAPH-002
  actual: reachable_via=[store.__class__.record_live_provider_return.__globals__,
          LiveProviderReturnWindow._issue.__func__.__globals__], minted=True, state=in_doubt,
          receipts=1, handoffs=1, responses=0
FAIL | IA20-WINDOW-001
  actual: subcases={..., 'g_other_world': 'MINTED', ..., 'j_detached_context': 'MINTED'}
SUMMARY | probes=4 failures=4
```

**`SUMMARY | probes=4 failures=4` — exactly as contract §14 requires**, and the four failing probe
ids are exactly the four required ones:

| required failing probe id | observed |
|---|---|
| `IA20-MINT-003` | FAIL |
| `IA20-MINT-004` | FAIL |
| `IA20-OBJGRAPH-002` | FAIL |
| `IA20-WINDOW-001` | FAIL |

`NO RED_FIRST_NOT_REPRODUCIBLE.`

Note `genuine_rsa_return_conflicted=True` in `IA20-MINT-003` — the frozen candidate exhibits the
full harm chain of `BLK-W20-001` including step 5, poisoning a later genuine RSA trusted return.

## 3. Suite B on the failed candidate — positive baseline preserved

Raw output: `raw/POSITIVE_SUITE_B_ON_FAILED_CANDIDATE_fec30bd.txt`.

```
PASS | IA20-MIGRATE-003
PASS | IA20-MIGRATE-004
PASS | IA20-RSA-ENC-001
PASS | IA20-RSA-PARAM-001
PASS | IA20-RSA-TRANSPLANT-001
PASS | IA20-NOTSUB-002
PASS | IA20-EXACTONCE-001
SUMMARY | probes=7 failures=0
```

**`probes=7 failures=0` — the existing positive baseline required by contract §14.**

## 4. Window 17 on the failed candidate — historical positive baseline

Raw output: `raw/POSITIVE_W17_ON_FAILED_CANDIDATE_fec30bd.txt`.

```
SUMMARY | probes=14 failures=0
```

**`probes=14 failures=0` — the historical requirement of contract §20.**

## 5. Suite A on the byte-exact carry-forward base — RED STILL PRESENT

Commit under test: `50a3e1f85f139a1cd959dbeeb496aba29f2b345b`
(`BYTE_EXACT_CARRY_FORWARD_BASE`, already pushed to the remote engineering branch before this run).

Command:

```
PYTHONPATH=<repo>/src python window20_independent_attack.py
```

Raw output: `raw/RED_SUITE_A_ON_CARRY_FORWARD_BASE.txt`.

```
FAIL | IA20-MINT-003
FAIL | IA20-MINT-004
FAIL | IA20-OBJGRAPH-002
FAIL | IA20-WINDOW-001
SUMMARY | probes=4 failures=4
```

**Still `4 failures`.** The two raw outputs (§2 and §5) are **byte-identical** — same SHA-256
`a138c12d8c1d807280ed38ef534f3de3325f8cb6260173543cfc5e5312a67506` — which mechanically proves
that the byte-exact carry-forward neither silently fixed nor altered the frozen Window 20 failure.

## 6. Full Core gate on the byte-exact carry-forward base (preflight)

Command:

```
PYTHONPATH=src python -m pytest tests/unit tests/integration tests/runtime tests/habitation -q
```

Result on `50a3e1f85f139a1cd959dbeeb496aba29f2b345b`: **all tests passed, exit code 0**
(`failures=0`, `errors=0`). This establishes that the carry-forward base is a green starting point
before any Corrective-003 semantic modification, so every later failure is attributable to
Corrective-003 itself.

## 7. Publication order (contract §14 / §22)

The RED evidence and the `BYTE_EXACT_CARRY_FORWARD_BASE` commit were pushed to the durable remote
engineering branch **before** any Corrective-003 semantic source modification was made:

| order | commit | remote sha verified |
|---|---|---|
| 1 | branch creation at fresh live main | `1541b1ec1a8b40bdc67debd52af986c2869ee00e` |
| 2 | ground truth + publication capability preflight | `f858057961d17d132eace21c29b95fb7d7a87c63` |
| 3 | `BYTE_EXACT_CARRY_FORWARD_BASE` | `50a3e1f85f139a1cd959dbeeb496aba29f2b345b` |
| 4 | RED-first evidence (this file) | see `FINAL_HANDOFF.md` |
| 5+ | Corrective-003 implementation | see `FINAL_HANDOFF.md` |

## 8. PREFLIGHT_ENVIRONMENT disclosure (contract §18)

All runs in this file were executed in the local sandbox, which is **not** the exact formal
environment (formal target is CPython `3.12.14`, Pydantic `2.13.5`, pytest `8.4.2`). Local CPython
is `3.11.2`, so every local result in this window is classified **PREFLIGHT** and does not replace
formal CI. The authoritative RED/GREEN evidence is the exact-head formal GitHub Actions run on
CPython 3.12.14 recorded in `FORMAL_CI_RESULTS.md`.

An attempt was made to obtain CPython 3.12.14 locally (`uv python install 3.12.14`); it failed
because the sandbox cannot verify the certificate chain of the python-build-standalone release
asset host. This is disclosed rather than worked around.
