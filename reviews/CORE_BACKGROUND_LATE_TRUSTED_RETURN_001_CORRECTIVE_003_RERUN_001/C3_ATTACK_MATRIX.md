# C3_ATTACK_MATRIX — section 16 author matrix (27 enumerated cases)

Executable form: `tests/integration/test_core_background_late_trusted_return_corrective_003_c3_matrix.py`
It runs inside the ordinary Core gate and in dedicated CI jobs
(`c3-author-matrix-green-27-cases`, `c3-author-matrix-red-on-failed-candidate`).

| result | value |
|---|---|
| cases enumerated | **27** = 13 (`C3-1`) + 13 (`C3-2`) + 1 (`C3-3`) |
| pytest cases in the file | **28** = 27 attack cases + 1 mechanical completeness check |
| on this candidate | **28 passed** |
| on the frozen failed candidate `fec30bd1…` (same file, byte-identical) | **17 failed, 11 passed** |
| raw evidence | `raw/GREEN_C3_AUTHOR_MATRIX_ON_CANDIDATE.txt`, `raw/RED_C3_AUTHOR_MATRIX_ON_FAILED_CANDIDATE_fec30bd.txt` |

---

## 1. Why the matrix asserts properties, not names

Section 16 requires property checks and explicitly discourages "function name absent"
assertions. The reason is historical and concrete: `BLK-W20-001` was possible *precisely
because* the previous design satisfied "the writer refuses when the window is forged" while the
**issuance** helper stayed public. A matrix built from "function X is absent" or "the writer
raises" assertions would have reported GREEN on that candidate.

Every case here therefore drives a real attack against a real durable World and then asserts on
**durable state**:

| property | statement |
|---|---|
| **P1** | zero trusted rows anywhere in the World — `background_model_response_receipts`, `background_model_return_handoffs`, `background_model_responses` all count 0 |
| **P2** | the attacked attempt never left the state it was in (`dispatching`, or `in_doubt` for the C3-3 case) and owns no receipt, no handoff and no staged exact response — so caller-supplied bytes are never recovery-eligible |
| **P3** | the attack was either refused by Core or inert, and *inert still means nothing durable was produced* |

Core refusals (`AttributeError`, `TypeError`, `BackgroundModelResponseConflict`,
`LiveReturnAuthorityError`) are recorded as the case **outcome**, not as failures.
`AssertionError` is treated differently and is **re-raised**: it means the matrix itself detected
a still-reachable forbidden authority, so it must fail the case. Without that distinction the
matrix could report green while a mint writer was still present — which is exactly what happened
on the first draft of this file, where every structural assertion was silently swallowed and only
2 of 27 cases went RED on the failed candidate. After the fix, 17 do.

## 2. The attack context is the state the real oracle abused

`AttackContext` crashes a user turn past the provider boundary and then leaves the attempt
durably in **`dispatching`** — with no provider provenance and no trusted row. That is exactly
the state the frozen `BLK-W20-001` oracle was able to abuse.

An earlier draft called `move_to_in_doubt(...)` first. That was a mistake: the removed writer had
its own `state='dispatching'` check, so forcing `in_doubt` made the old writer refuse for an
unrelated reason and **masked the vulnerability** — only 1 of 27 cases went RED. Only the C3-3
case (which is about `in_doubt` permanence) forces `in_doubt`.

## 3. `C3-1` — the 13 candidate trust roots the contract declares invalid

| case id | trust root attacked | what the case does | RED on `fec30bd1`? |
|---|---|---|---|
| `C3-1-01-public-function` | public function | drives the historical attack verbatim: `open_live_provider_return_window` → `register_handler_return` → `record_live_provider_return` | **YES** — minted a receipt + handoff |
| `C3-1-02-exported-symbol` | exported symbol | drives every name in `live_return.__all__` as authority, then asserts none of them is a mint writer | **YES** — `consume_live_provider_return_window` was exported |
| `C3-1-03-store-method` | store method | enumerates `dir(store)` and `dir(type(store))` for any forbidden mint name, then calls the writer | **YES** |
| `C3-1-04-classmethod` | classmethod | enumerates every `classmethod` on `LiveProviderReturnWindow` and the store, drives each with attacker bytes, then calls `_issue` | **YES** — `_issue` existed |
| `C3-1-05-registry` | registry | snapshots every module-level `dict`/`list`/`set` in the five Core runtime modules, opens three windows, and requires the snapshot to be unchanged | **YES** — `_OPEN_WINDOWS` accumulated |
| `C3-1-06-contextvar` | ContextVar | sets `_ACTIVE_WINDOW` by hand to a fabricated marker and then attacks | no |
| `C3-1-07-sentinel` | sentinel | asserts the tombstone holds no identity sentinel, and that any sentinel elsewhere in Core is never referenced by the two modules that own trusted-return authorization | **YES** — `_ISSUE_SENTINEL` existed |
| `C3-1-08-object-identity` | object identity | runs a real live turn whose handler returns the exact object, then asserts zero trusted rows for that round | **YES** — the live turn minted a receipt |
| `C3-1-09-test-secret` | test secret | presents a well-formed proof labelled with a **different** external key id than the durably bound verifier | no |
| `C3-1-10-underscore-naming` | underscore naming | enumerates every private callable in the five Core runtime modules, then calls `_capture_trusted_response_return` | **YES** |
| `C3-1-11-stack-naming` | stack naming | attacks from caller frames deliberately named `_mark_background_model_dispatch` / `run_turn` / `model_handler` | **YES** |
| `C3-1-12-docstring` | docstring | asserts no authorization function in Core reads `__doc__`, then attacks with a docstring claiming pre-authorization | no |
| `C3-1-13-bool-flag` | bool flag | requires the public decommission marker to be `True`, the schema to end in `decommissioned`, and a caller-flipped copy of the snapshot to authorize nothing | **YES** — no marker existed |

## 4. `C3-2` — the 13 enumerated reflection paths

| case id | reflection path | what the case does | RED on `fec30bd1`? |
|---|---|---|---|
| `C3-2-01-globals` | `__globals__` | walks every function in the five Core runtime modules (including class methods, classmethods, staticmethods and properties) and asserts no forbidden mint name is in its `__globals__` | **YES** |
| `C3-2-02-sys-modules` | `sys.modules` | re-enters through `sys.modules`, reaches the store class from the module object, and calls the writer as an unbound method | **YES** |
| `C3-2-03-dict` | `__dict__` | walks module, class, instance, runtime and window `__dict__`/`vars()` for forbidden names and for window instances | **YES** |
| `C3-2-04-bound-methods` | bound methods | enumerates every `inspect.ismethod` attribute of the store and the runtime, then drives the historical bound-method mint shape | **YES** |
| `C3-2-05-closure-cells` | closure cells | opens every `__closure__` cell, follows functions inside cells into their `__globals__` | **YES** |
| `C3-2-06-defaults` | defaults | inspects `__defaults__` and `__kwdefaults__` of every reachable callable for an authority object | no |
| `C3-2-07-descriptors` | descriptors | enumerates properties and non-function descriptors on the store, window and runtime types, accesses each on a live instance, and requires nothing to become armed | no |
| `C3-2-08-object-new` | `object.__new__` | fabricates a window with `object.__new__` + `object.__setattr__`, arms the ContextVar with it, and drives the writer; resets the ContextVar in a `finally` so no armed-looking state leaks into the rest of the suite | no |
| `C3-2-09-ctor` | ctor | calls the window ctor with zero, one and two attacker arguments; each must raise `TypeError` | **YES** |
| `C3-2-10-import` | import | re-imports the module, then executes an **isolated fresh copy** of its source via `spec_from_file_location` / `module_from_spec` / `exec_module` and asserts the copy is inert, is a different class object, and that `sys.modules` was not touched | **YES** |
| `C3-2-11-callbacks` | callbacks | installs attacker callbacks (`model_handler`, `model_response_recorder`) that open a window from inside the production frame, runs a real turn, and asserts zero trusted rows | **YES** |
| `C3-2-12-exception-objects` | exception objects | collects `f_globals` and `f_locals` from every traceback frame of four refused attacks and asserts no forbidden name and no window instance leaks; separately asserts no exception path ever hands back a window | **YES** |
| `C3-2-13-store-runtime-graph` | store/runtime graph | full BFS over the runtime + store object graph (dicts, sequences, `vars()`), collecting any window instance and any function whose name or `__globals__` holds a forbidden mint name | **YES** |

`C3-2-10` deliberately does **not** use `importlib.reload`. `reload()` re-executes a module inside
its existing `sys.modules` entry and therefore rebinds every class object it defines; in the
full-suite run that broke `isinstance` identity for
`tests/runtime/test_cognitive_runtime_trusted_return.py`, which imported the tombstone type
earlier, and two unrelated cases failed. A matrix case must never be able to corrupt the rest of
the suite. The isolated-copy form proves the same property twice (the already-imported module and
a freshly executed copy of its source are both inert) and additionally proves that a caller who
manufactures its own module copy holds a class Core never consults.

## 5. `C3-3` — verifier-less permanence

`C3-3-01-verifier-less-in-doubt`: with **no** bound verifier, `late_return_verifier()` and
`late_return_signing_context()` both return `None`, and every durable writer is driven in
sequence — `record_response`, `stage_exact_response` with no proof, with a shaped-but-bogus
proof, `attach_late_trusted_return` with a bogus signature, and the historical window+writer
attack — then the World is reopened in a fresh runtime and `attach_late_trusted_return` is driven
again. The attempt must still be `in_doubt` with zero trusted rows. Not RED on `fec30bd1`,
because `C3-3` already held there; the blocker was `C3-1`/`C3-2`.

## 6. Non-vacuity

`test_c3_matrix_covers_exactly_the_enumerated_cases` asserts mechanically that the matrix has 27
unique case ids, 13 prefixed `C3-1-`, 13 prefixed `C3-2-` and 1 prefixed `C3-3-`. CI job
`c3-author-matrix-green-27-cases` independently counts `PASSED` lines per prefix and requires
exactly 13 / 13 / 1 plus `28 passed`.

CI job `c3-author-matrix-red-on-failed-candidate` copies this file **byte-for-byte** into a
detached worktree at `fec30bd1…` (asserting SHA-256 equality of the copied file), runs it against
the failed candidate's `src/`, and fails the run unless at least 10 cases are RED. Observed: 17.
That is the mechanical proof the matrix is not vacuous.

The 11 cases that are GREEN on the failed candidate are not weaknesses: they attack routes that
were already closed in Corrective-002 (a foreign key id, a bogus signature, a fabricated window
presented to a writer that validates its registry entry, closure cells, defaults, descriptors) or
routes that were already correct (`C3-3`). They are retained because Route B must keep them
closed, and because a future re-introduction of authority through any of them would turn them RED.
