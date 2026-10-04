# TIGHTEN_AUDIT — historical `tests/**` modified under TIGHTEN_ONLY

Window `22-RERUN-001` · Task `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003`
Branch `arena/01a101e0-haneof-aios-core-v3-0` · Baseline for every diff: live main
`1541b1ec1a8b40bdc67debd52af986c2869ee00e`

## 0. Authority for this audit

Task section 8 permits historical `tests/**` that encode now-unsafe live self-trust to be
modified **only TIGHTEN_ONLY**, per file, recording seven items:

1. the old expectation;
2. the old authority mechanism;
3. why it is unsafe per `BLK-W20-001`;
4. the replacement external-verifier route;
5. which assertions were deleted;
6. which new or retained assertions are equal-or-stronger;
7. how exactly-once, provenance, crash and truthfulness guarantees are preserved.

Changing an expectation merely in order to reach GREEN is forbidden. Every one of the 13
files below carries the same seven items in a `TIGHTEN_ONLY history` block at the top of
the file or on the rewritten test, so the audit is readable from the diff alone and not
only from this document.

**`BLK-W20-001`** = `RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW`,
root cause `TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE`.

The removed authority, in every case, was the same three-part mechanism:

```python
with open_live_provider_return_window(attempt_id=...) as window:   # public function
    register_handler_return(window, attacker_directive)            # public function
    store.record_live_provider_return(..., live_window=window)     # public store method
```

Because *issuance* was an ordinary public function, any process-local recovery caller could
issue its own window, declare its own bytes "handler-returned", and mint a durable trusted
receipt + exact handoff. Route B deletes the writer and the issuance classmethod entirely.

## 1. Scope of test modification

13 historical test files were modified; 0 were deleted; 0 were weakened. 7 test files are
added relative to main, of which 6 are the byte-exact carry-forward from `fec30bd1…` and 1
is new (`…corrective_003_c3_matrix.py`, the section-16 author matrix).

| # | file | +/- | cases | status |
|---|---|---|---|---|
| 1 | `tests/runtime/test_cognitive_runtime_trusted_return.py` | +196 / −21 | 5 | TIGHTEN_ONLY |
| 2 | `tests/integration/test_core_background_trusted_return_recovery_001.py` | +183 / −9 | 3 | TIGHTEN_ONLY |
| 3 | `tests/integration/test_core_background_trusted_return_adversarial_001.py` | +359 / −29 | 27 | TIGHTEN_ONLY |
| 4 | `tests/integration/test_core_background_trusted_return_r5_001.py` | +146 / −26 | 11 | TIGHTEN_ONLY |
| 5 | `tests/integration/test_core_background_trusted_return_r5_conflicts_001.py` | +46 / −6 | 13 | TIGHTEN_ONLY |
| 6 | `tests/integration/test_core_background_response_recovery_001.py` | +201 / −64 | 25 | TIGHTEN_ONLY |
| 7 | `tests/integration/test_core_background_response_recovery_001_corrective_001.py` | +100 / −18 | 18 | TIGHTEN_ONLY |
| 8 | `tests/integration/test_core_background_response_recovery_001_corrective_002_recovery.py` | +109 / −19 | 9 | TIGHTEN_ONLY |
| 9 | `tests/runtime/test_background_model_attempt.py` | +241 / −45 | 7 | TIGHTEN_ONLY |
| 10 | `tests/runtime/test_turn_execution_recovery.py` | +149 / −37 | 12 | TIGHTEN_ONLY |
| 11 | `tests/integration/test_core_gap_fix_002_background_attempts.py` | +115 / −28 | 9 | TIGHTEN_ONLY |
| 12 | `tests/integration/test_core_background_trusted_return_corrective_001_process_loss.py` | +42 / −10 | 3 | TIGHTEN_ONLY |
| 13 | `tests/integration/test_core_background_late_trusted_return_corrective_002.py` | +1216 / −0 (file is carried forward; 2 of 20 cases rewritten) | 20 | TIGHTEN_ONLY |

The Route B replacement harness is defined once, in file 2, and imported by files 3, 4, 5,
7, 8, 11 and 12 so that all of them exercise one identical external authority:
`route_b_verifier()`, `RouteBExternalSigner`, `trust_row_counts()`,
`crash_before_local_completion()`, `crash_at_return_with_signer()`.
File 9 duplicates the RSA key material locally instead of importing it, because
`tests/runtime` must stay runnable without `tests/integration` on `sys.path`.

---

## 2. Per-file audit

### File 1 — `tests/runtime/test_cognitive_runtime_trusted_return.py` (5 cases)

1. **Old expectation.** A live handler return inside the cognitive runtime's
   `_live_provider_return_window` produced a durable trusted receipt and handoff, and
   `ModelResponseAuthenticator` could be supplied as a constructor hook to "authenticate" a
   live response. `LiveProviderReturnWindow` was treated as a capability object.
2. **Old authority mechanism.** `CognitiveRuntime(model_response_authenticator=…)` plus the
   `_live_provider_return_window` context manager wrapping the handler frame, plus
   `BackgroundModelAttemptStore.record_live_provider_return`.
3. **Why unsafe (`BLK-W20-001`).** The window was armed by an ordinary public function, so
   the "the handler really returned this" claim was self-assertable by any caller in the
   process; the authenticator hook was an injectable object and therefore also
   caller-manufacturable.
4. **Replacement route.** The runtime no longer has an authenticator hook and no longer arms
   a window. The file now asserts the tombstone's *properties*: `LiveProviderReturnWindow`
   is never constructible (`TypeError`), never copyable and never serializable; the module
   exposes no issuance machinery for reflection; a live return creates zero trusted rows.
   Genuine trusted return is exercised through
   `BackgroundModelAttemptStore.attach_late_trusted_return` with a bound external verifier.
5. **Deleted assertions.** "a receipt exists after a live return"; "the authenticator hook
   is invoked"; "the window is armed on the handler frame"; "handler-return identity binds
   the bytes".
6. **Equal-or-stronger replacements.** "no receipt, handoff or staged response exists after
   a live return" (strictly stronger: it pins the *absence* of any local mint, which the old
   assertion could not express); "ctor / copy / pickle all refuse"; "no issuance symbol is
   reachable by reflection from the module"; "the decommission marker is permanently true".
7. **Preserved guarantees.** Exactly-once and provenance are unaffected (this file never
   metered); crash behaviour is covered by files 2, 3, 8 and 12; truthfulness is strengthened
   because the only way to make bytes durable-trusted is now an external signature.

### File 2 — `tests/integration/test_core_background_trusted_return_recovery_001.py` (3 cases)

1. **Old expectation.** After a simulated crash, a recovery caller could obtain a trusted
   receipt through the live window and then replay exact bytes.
2. **Old authority mechanism.** `open_live_provider_return_window` +
   `register_handler_return` + `record_live_provider_return`.
3. **Why unsafe.** Same as above; this file was the primary recovery-reachable path.
4. **Replacement route.** This file now *defines* the shared Route B harness: a durable
   external verifier (`route_b_verifier()`), a simulated external signer
   (`RouteBExternalSigner`) that holds the private exponent outside Core, and
   `attach_genuine_return(...)`. `crash_at_return` was split into
   `crash_before_local_completion` (crash with no proof ⇒ permanently in doubt) and
   `crash_at_return_with_signer` (crash, then a genuine external proof), so the two Route B
   outcomes are separately and explicitly covered.
5. **Deleted assertions.** "the window arms authority"; "the receipt exists because the live
   return happened".
6. **Equal-or-stronger.** `trust_row_counts()` is asserted to be `(0, 0, 0)` before any
   external proof and `(1, 1, 1)` after; the verifier-less crash is asserted to be
   permanently non-recovery-eligible; the genuine-proof crash is asserted to recover with
   exactly the signed bytes.
7. **Preserved.** Exactly-once replay, provenance binding to the durable pre-dispatch
   request binding, real crash semantics (the crash is raised from inside the recorder
   callback, and file 12 covers real `SIGKILL`), truthfulness (only signed bytes are
   durable-trusted).

### File 3 — `tests/integration/test_core_background_trusted_return_adversarial_001.py` (27 cases)

1. **Old expectation.** Cross-world, cloned-DB, cloned-store, detached-ContextVar,
   copied-context, other-thread, other-task, stale, reused, nested, reentrant, exception,
   cancellation and fork attacks were each refused *by the window's guards*.
2. **Old authority mechanism.** The window guards (seal, registry, stack scope,
   handler-return identity map).
3. **Why unsafe.** Every one of those guards was satisfiable by a caller who issued its own
   window, so the refusals proved guard plumbing rather than authenticity.
4. **Replacement route.** `attach_genuine_external_return()`; each mutation is now verified
   *property-based* (the mutated object really differs from the genuine one) before being
   presented, and every attack is asserted to leave `trust_row_counts() == (0, 0, 0)`.
   A new case,
   `test_forged_local_return_cannot_poison_a_later_genuine_external_return`, was added: a
   forged local return must not prevent or corrupt a later genuine external return.
5. **Deleted assertions.** "the window refused because the seal mismatched / the registry
   entry was gone / the stack did not match".
6. **Equal-or-stronger.** The whole hygiene-closure list is retained and now ends in a
   durable-state property rather than an exception type; the new poisoning case is strictly
   additional coverage; `copied_handoff_from_round` was strengthened from a NULL copy into a
   genuine **cross-round transplant** of a valid signed handoff built in an independent
   World, with an assertion that the transplanted payload differs from the genuine one.
7. **Preserved.** Exactly-once (row counts asserted before and after every attack),
   provenance (transplanted handoffs rejected), crash (fork-based attacks retained),
   truthfulness (no residual armed state denies a genuine return — asserted explicitly at
   the end of the hygiene sequence).

### File 4 — `tests/integration/test_core_background_trusted_return_r5_001.py` (11 cases)

1. **Old expectation.** R5-A / R5-B / R5-C rounds could be recovered from a receipt minted
   by the live return of the crashed round.
2. **Old authority mechanism.** `record_live_provider_return` via the window.
3. **Why unsafe.** Same root cause.
4. **Replacement route.** `new_runtime(db, handler)` now binds
   `late_return_verifier=route_b_verifier()` and
   `external_return_observer=RouteBExternalSigner()`; `signer_for(runtime)` and
   `attach_genuine_return(runtime, kind, work_id, returned, round_index=0, *, seconds=1)`
   produce the genuine external proof after the crash. `evidence(..., proven=False/True)`
   was made two-sided: when unproven it asserts the **absence** of receipt, handoff and
   staged rows plus `verifier_rows == 1`; when proven it asserts the full old
   receipt/handoff consistency **plus** staged-row equality.
5. **Deleted assertions.** "receipt exists after the crashed round"; "handoff exists".
6. **Equal-or-stronger.** The unproven branch is new and strictly stronger (it pins that no
   local authority produced anything); the proven branch keeps every old field comparison
   and adds the staged bytes. R5-D (terminal receipt path) is verifier-independent and was
   left untouched.
7. **Preserved.** Exactly-once (`assert_same_evidence` before/after), provenance (verifier
   scope equality), crash (`ProcessDeath` raised from inside the round), truthfulness.

   One over-strong assertion (`response_fingerprint ==
   sha256(encode_model_directive(reconstructed_directive))`) was added and then removed
   during this window: the reconstruction was wrong because handlers differ per test, so the
   assertion was not a property of Core. Its removal is recorded here for completeness; it
   never shipped in a committed state as a passing expectation.

### File 5 — `tests/integration/test_core_background_trusted_return_r5_conflicts_001.py` (13 cases)

1. **Old expectation.** The eight R5-C conflict mutations were refused while a
   locally-minted receipt/handoff/staged triple existed as the baseline.
2. **Old authority mechanism.** As file 4.
3. **Why unsafe.** As file 4.
4. **Replacement route.** Imports `attach_genuine_return`; `metered_task_crash` attaches a
   genuine proof and compares `proven=True` evidence;
   `test_r5_a_terminal_ack_operation_identity_is_stable` attaches a genuine proof. The eight
   mutations are kept **byte-for-byte**.
5. **Deleted assertions.** `staged_response(...) is None` as the post-attack baseline.
6. **Equal-or-stronger.** Replaced by capturing `genuine_handoff = before[3]` *before* the
   attack and asserting afterwards that the staged bytes are still exactly the genuine
   pre-attack payload, digest and proof. That is stronger: it proves the attack did not
   merely fail to create state, it failed to *disturb* genuine state.
7. **Preserved.** Exactly-once, provenance, crash, truthfulness — unchanged mutations,
   unchanged conflict expectations.

### File 6 — `tests/integration/test_core_background_response_recovery_001.py` (25 cases)

1. **Old expectation.** `_stage(...)` obtained an `authenticity_proof` from
   `capture_live_provider_return` and then staged exact bytes; `test_case_04c` asserted a
   receipt existed purely because the live completion had happened.
2. **Old authority mechanism.** `capture_live_provider_return` (window + writer).
3. **Why unsafe.** The recovery caller in these fault-matrix tests *was* the attacker
   `BLK-W20-001` describes.
4. **Replacement route.** A module-level `_route_b_runtime(**kwargs)` factory binds
   `late_return_verifier` + `external_return_observer` and registers the signer per World
   path; `_external_signing_context(runtime, attempt_id)` rebuilds the public signing scope
   from Core's **durable** rows (`late_return_signing_context` + `outbound_request_binding`);
   `attach_external_trusted_return(...)` produces the receipt.
5. **Deleted assertions.** "a receipt exists because the live completion happened"
   (`test_case_04c`).
6. **Equal-or-stronger.** `test_case_04c` now asserts the live completion minted **no**
   receipt and **no** staged response, so the "different bytes must never overwrite durable
   provenance" refusal holds against *every* local caller — there is no local proof to copy —
   and that the exact bytes can only be staged from genuine external proof; it additionally
   asserts that restaging identical genuinely-proven bytes is effect-free.
7. **Preserved.** Every crash boundary, every "provider must never be re-dispatched for a
   recovered round", every exactly-once metering / capability / assistant-output assertion,
   the missing/mismatched/unverifiable fail-closed cases, and the post-binding
   `not_submitted` closure case are unchanged.

### File 7 — `tests/integration/test_core_background_response_recovery_001_corrective_001.py` (18 cases)

1. **Old expectation.** Same `_stage(trusted_return=True)` route to an `authenticity_proof`.
2. **Old authority mechanism.** `capture_live_provider_return`.
3. **Why unsafe.** Same root cause; this file also contained real-`SIGKILL` cases whose child
   process minted the receipt before dying.
4. **Replacement route.** Identical `_route_b_runtime` / `attach_external_trusted_return`
   harness. Because the durable request binding survives `SIGKILL`, the genuine external
   proof is obtainable by the surviving process — no channel from the dead child is needed.
5. **Deleted assertions.** None beyond the receipt-from-live-return premise.
6. **Equal-or-stronger.** The `SIGKILL` cases still assert `exitcode == -SIGKILL` and still
   recover with zero provider calls; the receipt they recover from is now externally proven.
7. **Preserved.** Same-attempt correct-binding recovery, post-`SIGKILL` exact-response
   staging, post-capability-side-effect exactly-once replay, `BackgroundModelResponseConflict`
   on mismatched bindings.

### File 8 — `tests/integration/test_core_background_response_recovery_001_corrective_002_recovery.py` (9 cases)

1. **Old expectation.** `die_before_response_recording` asserted a receipt was **already
   present** at the moment the ordinary response recorder was entered — i.e. the live return
   had minted its own trusted receipt ahead of response provenance.
2. **Old authority mechanism.** The live capture path (historically the private
   `_capture_trusted_response_return`, then the window).
3. **Why unsafe.** This is the clearest statement of the unsafe premise: authenticity was
   established by the local return itself.
4. **Replacement route.** The recorder callback now asserts the receipt is **absent** at that
   boundary; the receipt is created afterwards by `attach_external_trusted_return`, so the
   "durable ahead of application" property is preserved but anchored on real external proof.
5. **Deleted assertions.** `receipt is not None` at the crash point; `after.state ==
   "dispatching"` / `provider is None` as the post-tamper baseline.
6. **Equal-or-stronger.** "no receipt exists until a genuine external proof is verified" is
   asserted at the crash point *and* again after a real `SIGKILL`; the tamper cases now assert
   that durable state is still exactly the genuinely-proven return (payload, digest, proof,
   provider identity) rather than merely empty — strictly stronger, because it proves the
   tampered bundle neither created nor disturbed state.
7. **Preserved.** Restart recovery with zero redispatch, exactly-once metering, exact-byte
   replay, all five tamper mutations, both durable-proof re-verification tamper targets, the
   real multi-process `SIGKILL`, and every World-revision / no-metering fail-closed assertion.

### File 9 — `tests/runtime/test_background_model_attempt.py` (7 cases)

1. **Old expectation.** `_trusted_attempt(...)` produced a receipt via
   `capture_live_provider_return`; the pre-submission retry test called the same helper
   incidentally before `record_response`.
2. **Old authority mechanism.** Window + writer, at store level.
3. **Why unsafe.** Same root cause.
4. **Replacement route.** Verifiers are bound through the ordinary public
   `mark_dispatching(late_return_verifier=...)` path and the public signing scope is read back
   with `late_return_signing_context`; the receipt comes from
   `attach_late_trusted_return` with a genuine signature. The RSA material is duplicated
   locally so `tests/runtime` stays independently runnable.
5. **Deleted assertions.** The incidental live-mint call in the pre-submission retry test (it
   asserted nothing).
6. **Equal-or-stronger.** Replaced by explicit assertions that the live completion minted no
   receipt, no handoff and no staged response. All four cross-identity receipt-replay
   refusals keep the exact `proof is invalid` match and are now proved against a **valid**
   receipt belonging to a different identity rather than a locally self-minted one; the
   post-refusal assertions were upgraded from "target still empty" to "target still exactly
   its own genuine bytes and identity, and never the source's".
7. **Preserved.** Pre-submission retry identity, non-World-revision, the metadata-only
   reconciliation refusal, and the post-binding `not_submitted` refusal.

### File 10 — `tests/runtime/test_turn_execution_recovery.py` (12 cases)

1. **Old expectation.** `test_cg003_assistant_output_persistence_failure_remains_in_doubt`
   crashed at assistant persistence and then had a **fresh process** replay the turn and
   reproduce `"SYNTHETIC recovered response"` with `calls == ["called"]`.
2. **Old authority mechanism.** The live return's self-minted receipt.
3. **Why unsafe.** A fresh process could adopt bytes that nothing external had proven.
4. **Replacement route.** The case was split into the two Route B halves. (a) The original
   case now asserts contract `C3-3`: a verifier-less attempt whose exact bytes were never
   externally preserved is **permanently** in doubt — a fresh process raises
   `TurnExecutionInDoubt`, never redispatches, never fabricates a response, never adopts
   caller bytes. (b) A new case,
   `test_cg003_same_crash_recovers_exactly_once_from_genuine_external_proof`, performs the
   *identical* crash with an external verifier bound and proves exact recovery from genuine
   external proof.
5. **Deleted assertions.** "a fresh process reproduces the response with no external proof".
6. **Equal-or-stronger.** The recovery property is preserved verbatim in (b) — same crash
   point, same directive, same zero-redispatch requirement, same exact response — plus
   `recovered_response_attempts`, exactly one meter row bound to the attempt, and
   `TurnAlreadyCompleted` on a second replay. (a) adds a property the old suite did not have.
7. **Preserved.** Exactly-once, provenance, crash point, truthfulness; all other cg003 cases
   in the file are untouched.

### File 11 — `tests/integration/test_core_gap_fix_002_background_attempts.py` (9 cases)

1. **Old expectation.** Three tests crashed a Wake / periodic review *after* the live response
   was recorded (`response_returned` or `metered`) and asserted a restarted process completed
   the work from durable state with zero provider reinvocation.
2. **Old authority mechanism.** The live return's self-minted receipt + handoff.
3. **Why unsafe.** Same root cause.
4. **Replacement route.** Those three tests bind an external verifier before the provider
   boundary and preserve the crashed round's exact bytes with a genuine external signature
   over the durable pre-dispatch binding. The other six tests are verifier-independent
   fail-closed cases and were left untouched.
5. **Deleted assertions.** None.
6. **Equal-or-stronger.** Every crash point, every "provider must not be reinvoked",
   every exactly-once metering assertion and every completion assertion is unchanged; the
   three tests additionally assert that the live completion minted **no** trusted state before
   the external proof created it.
7. **Preserved.** In-doubt-on-ambiguous-failure, crash-before-dispatch retry safety, typed
   `not_submitted` after durable dispatch, budget rollover not erasing in-doubt.

### File 12 — `tests/integration/test_core_background_trusted_return_corrective_001_process_loss.py` (3 cases)

1. **Old expectation.** After a real `SIGKILL` the parent could replay the identical recovered
   directive because the child's live return had already minted a durable receipt.
2. **Old authority mechanism.** The shared `_stage(trusted_return=True)` helper.
3. **Why unsafe.** Same root cause, under real process loss.
4. **Replacement route.** Every runtime in the file — parent and forked child — is built by
   `_route_b_runtime`, which binds an external verifier before the provider boundary. The
   exact bytes cross the real `SIGKILL` on the strength of the durable request binding, which
   survives the kill, plus a genuine external signature.
5. **Deleted assertions.** None.
6. **Equal-or-stronger.** `exitcode == -SIGKILL`, the three capability families
   (`revise_claim`, `transition_goal`, `form_event`), the three runtime modes (`wake`,
   `user_turn`, `periodic_review`), zero provider redispatch, one meter row, exactly one
   durable capability effect, one operation identity, converging logical turn and every
   revision assertion are all unchanged. No probe was downgraded to a simulated crash.
7. **Preserved.** This file *is* the real-crash evidence; it is fully preserved.

### File 13 — `tests/integration/test_core_background_late_trusted_return_corrective_002.py` (20 cases; 2 rewritten)

1. **Old expectation.** `CA2-002` asserted the writer and the issuance classmethod *refused*
   (`LiveReturnAuthorityError`) for five forged-window shapes. `CA2-004` asserted that after
   one ordinary live turn a durable receipt existed (`provider == "provider-ca2"`) plus a
   handoff, and that this authority was stack-scoped and vanished with the frame.
2. **Old authority mechanism.** The ephemeral live provider-return window.
3. **Why unsafe.** The refusals `CA2-002` verified were all satisfiable by a caller who simply
   issued its own window — which is precisely what `BLK-W20-001` did. `CA2-004`'s
   "ephemeral, stack-scoped, non-persisted" properties never established authenticity.
4. **Replacement route.** `CA2-002` restates all five cases **structurally**: the writer and
   the issuance classmethod do not exist on the instance or on the class, so `__globals__`
   reflection over the store class exposes no live-return symbol; case 5 is strengthened from
   "bytes the handler did not return are refused" to "no self-asserted bytes are accepted at
   all, whether or not the handler returned them", plus a bogus-signature refusal.
   `CA2-004` keeps every ephemerality assertion and adds the stronger invariant that a
   genuine live local return creates **zero** trusted rows, so a live turn can never make its
   own bytes recovery-eligible.
5. **Deleted assertions.** The five `LiveReturnAuthorityError` expectations; `receipt is not
   None` / `trust_rows(db) in {(1,1,0), (1,1,1)}` after a live turn; `window.state ==
   "closed"`.
6. **Equal-or-stronger.** Structural absence is strictly stronger than a bypassable refusal.
   `CA2-004`'s new `trust_rows(db) == (0, 0, 0)` plus "no verifier bound" plus "a bogus
   external proof is still refused" is strictly stronger than "a receipt existed but the
   window was gone".
7. **Preserved.** All 18 other cases are byte-for-byte untouched, including the legacy keyed
   authenticator migration suite (`CA2-005` … `CA2-009`: verify-before-convert, atomicity,
   no partial rewrite, secret retained on failure), cross-attempt proof rejection
   (`CA2-014`), concurrent-attach first-writer-wins (`CA2-015`) and the real-`SIGKILL` case.

---

## 3. Cross-file invariants that the audit verifies

* **No expectation was changed in order to reach GREEN.** In all 13 files the *behavioural*
  expectations (crash points, conflict types, exactly-once counts, completion states,
  `SIGKILL` exit codes, migration outcomes) are unchanged. What changed is only the
  *authority* that a test uses to make bytes durable-trusted, plus new assertions that pin the
  absence of the old authority.
* **Every deleted assertion is paired with a stronger one.** The recurring strengthening is
  the two-sided form: where the old suite asserted "trusted state exists after a local
  return", the new suite asserts "trusted state does **not** exist after a local return, and
  **does** exist, byte-identically, after a genuine external proof".
* **Truthfulness / no-residual-armed-state closure.** Files 3 and 13 assert explicitly that
  after the full hygiene sequence a genuine external return is still accepted, i.e. no
  residual state denies genuine returns.
* **Frozen reviewer probes were not touched.** All three probe suites are extracted from the
  canonical review commits at run time; see `PROBE_MANIFEST.md` and `C3_ATTACK_MATRIX.md`.

## 4. Result

Full Core gate on the candidate tree (`tests/unit` + `tests/integration` + `tests/runtime` +
`tests/habitation`): **928 passed, 0 failed, 0 errors**. Raw preflight output:
`raw/PREFLIGHT_FULL_CORE_GATE_ON_CANDIDATE_v4.txt`.
