# `not_submitted` write-site audit (§18) and pre/post-dispatch matrix (§19) — WINDOW 14

Candidate `5ad0524c425592210ff184e00ad52abb2c14e366`.

## Complete write-site matrix for `state='not_submitted'`

Search: `grep -RIn "not_submitted\|SET state" src/aios_core --include='*.py'` plus
source read of every `UPDATE background_model_attempts` statement.

| # | write site | file:line | gate before write | post-dispatch + binding present | verdict |
|---|---|---|---|---|---|
| 1 | `reconcile_not_submitted` | `background_attempt.py:1310-1421` | binding row absent (mechanical), state ∈ {`admitted`,`not_submitted`}, no receipt, evidence non-blank | **refused** — `BackgroundModelResponseConflict` ("binding proves the dispatch boundary was crossed") | fixed ✓ |
| 2 | `FusedTurnRuntime.reconcile_turn_model_not_submitted` | `turn_runtime.py:3375-3410` | delegates to #1 | refused | fixed ✓ |
| 3 | `mark_failure(definitely_not_submitted=True)` | `background_attempt.py:1135-1195` | **receipt-absence only**; `UPDATE … WHERE state IN ('admitted','dispatching')` | **WRITES `not_submitted`** | **BLK-W14-003** |
| 4 | `admit` retry reset `not_submitted→admitted` | `background_attempt.py:925-943` | n/a (leaves `not_submitted`) | n/a | ok |
| 5 | `mark_dispatching` | `:1032-1034` | writes `dispatching` only | n/a | ok |
| 6 | `admit` restart `dispatching→in_doubt` | `:948-970` | writes `in_doubt` only | n/a | ok |
| 7 | `adopt_legacy_in_doubt` | `:1082-1133` | writes `in_doubt` only | n/a | ok |
| 8 | `record_response` / `stage_exact_response` | `:1276-1283`, `:2539-2545` | write `response_returned` | n/a | ok |
| 9 | FIX-003 CHECK-constraint rebuild migration | `:473-533` | copies rows byte-for-byte (S2 verified) | n/a | ok |
| 10 | `reconcile_response` | `:1423-1453` | permanently disabled (raises conflict) | n/a | ok |
| 11 | direct SQL helpers / compatibility paths | — | none exist in `src/aios_core` | — | ok |
| 12 | `ModelDispatchNotSubmitted` typed route | `cognitive_runtime.py:356-358` → `mark_failure(True)` | **the only intended caller**, mapped exclusively from the typed exception type | writes `not_submitted` from `dispatching` | legal by design, but see below |

## The gap (BLK-W14-003)

The frozen semantics require: "`not_submitted` ⇔ Core holds **mechanical,
trustworthy** evidence that this attempt never crossed the dispatch boundary" and
"once `mark_dispatching` has committed … this transition is mechanically impossible"
(design_note.md §4). Site #1 enforces exactly that. Site #3 does not:

* it is a **public** method on the exported store class; `runtime.background_model_attempts`
  is a public attribute;
* it trusts a caller-supplied `definitely_not_submitted: bool`;
* it does not check the error type (any `BaseException` is accepted — confirmed with
  a plain `RuntimeError`, `raw/ns001_confirmation_variant.txt`);
* it does not check the durable binding row (only receipt-absence).

Frozen probe `IA14-NS-001` (dispatching + binding present):

```
mark_failure accepted caller boolean and wrote state=not_submitted
```

Confirmation variant (untyped error):

```
durable row: ('not_submitted', 'RuntimeError')
```

### But isn't the typed route supposed to write from `dispatching`?

Yes — and this is the subtle part. `CognitiveRuntime` calls `mark_dispatching`
*before* `model_handler` (`cognitive_runtime.py:350-353`), so when the handler
raises `ModelDispatchNotSubmitted` the attempt is already `dispatching` **with** a
binding row. The accepted FIX-002/CG003 contract therefore requires `dispatching →
not_submitted` to be reachable *through the typed signal*, and the binding row alone
cannot be the sole gate for site #3. The correct gate is therefore the **typed
signal itself** — `isinstance(error, ModelDispatchNotSubmitted)` enforced at the
write site (or a private runtime-only entry), not a caller boolean. Today the typed
distinction exists only in `cognitive_runtime.py` (mapping) and is absent at the
durable write, so any recovery-facing caller can impersonate it. That is precisely
NS-A/NS-G of the mandated matrix.

### Impact

false `not_submitted` → `admit` resets to `admitted` → `mark_dispatching` issues a
new binding/new request identity → blind redispatch with a second request identity
while the first may still complete — the §12 forbidden outcome, and the same
`IA-B-R003-BLK-002` class the window exists to retire, merely moved from
`reconcile_*` to `mark_failure`.

## Pre-dispatch / post-dispatch matrix (§19)

| case | expected | actual | verdict |
|---|---|---|---|
| NS-A `dispatching` + binding present | refuse `not_submitted` | `reconcile_*` refuses; `mark_failure` writes | **fail** (BLK-W14-003) |
| NS-B `in_doubt` + binding present | refuse | `reconcile_*` refuses (state gate); `mark_failure` UPDATE misses `in_doubt` → `BackgroundModelAttemptBlocked` | pass |
| NS-C `in_doubt` + no receipt | refuse (receipt absence ≠ proof) | refused | pass |
| NS-D binding corrupt/inconsistent | refuse | `_require_origin_binding` conflict | pass |
| NS-E binding missing + `in_doubt` | refuse | refused (state gate) | pass |
| NS-F receipt missing | never proof of non-submission | `reconcile_*` still refuses (guard 1 first) | pass |
| NS-G caller asserts "not submitted" | fail closed | `reconcile_*` requires mechanical pre-dispatch state (evidence is recorded but never sufficient alone); `mark_failure` accepts caller boolean | **fail** (BLK-W14-003) |
| NS-H timeout | never `not_submitted` | ordinary exception → `mark_failure(False)` → `in_doubt` via runtime mapping | pass |
| NS-I provider unreachable | never `not_submitted` | same as NS-H | pass |
| NS-J late proof available | attach path, never `not_submitted` | `reconcile_*` refused; attach used (NS-R6 green) | pass |

## Pre-dispatch legit paths (§20)

* `ModelDispatchNotSubmitted` typed contract preserved and green
  (`test_ns_r1_in_process…`, `test_cg003_known_not_submitted_requires_explicit_retry_authorization`,
  `test_cg003_not_submitted_attempt_can_be_authorized_after_restart` — fresh 249/249).
* The "definitely not submitted" evidence source is the provider handler's typed
  signal raised in-process at the dispatch site; ordinary post-dispatch exceptions
  map to `in_doubt` (never misclassified) — correct at the runtime mapping layer.
* Retry identity preserved (`attempt_id_for` is content-independent; `admit` reuses
  the same attempt identity) — verified in S1.
* Old binding/capability across retry: binding replaced; capability **not** rotated
  → BLK-W14-004 (see lifecycle matrix).
