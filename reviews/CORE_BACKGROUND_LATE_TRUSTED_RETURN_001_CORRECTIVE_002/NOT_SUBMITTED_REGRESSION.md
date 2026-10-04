# NOT_SUBMITTED_REGRESSION — C2-7 preservation evidence

Corrective-002 removes exactly one capability (recovery-reachable receipt/handoff
minting) and adds exactly one authority (ephemeral live window).  Everything the
Window 16/17 rulings accepted must still hold, and the Route-B `not_submitted`
contract must be unchanged.

## Route-B truthfulness (`not_submitted`)

| Property | Test |
| --- | --- |
| A post-binding caller claim of `not_submitted` is refused at every write site | `tests/runtime/test_background_model_attempt.py`, `tests/integration/test_core_background_response_recovery_001.py` (Route-B cases), frozen probe `IA17-NS-ROUTE-B-001` |
| A genuinely pre-submission attempt may be retried, and a late trusted return still applies afterwards | frozen probe `IA17-NS-ROUTE-B-001` (`pre_sub_response='completed after pre-submission retry + late return'`) |
| `not_submitted` rows carrying any durable dispatch/verifier/receipt artifact are never re-admitted | `reconcile_not_submitted`, `_durable_submission_artifacts` (unchanged), `tests/integration/test_core_background_response_recovery_001.py` |

## Exactly-once application, metering, effects

| Property | Test |
| --- | --- |
| Concurrent valid proofs → one canonical winner, one refusal, one metered completion | `IA17-RACE-CRASH-001` (PASS), `CA2-015` |
| Real process loss → recovery completes exactly once, provider never re-dispatched | `IA17-SIGKILL-001` (PASS), `CA2-004` real-fork variant |
| Meter ledger, assistant output and capability side effects stay exactly-once on recovery | `tests/integration/test_core_background_response_recovery_001.py`, `…_corrective_001.py`, `tests/integration/test_core_background_trusted_return_recovery_001.py` |
| Provider identity / duplicate-JSON / non-canonical byte conflicts fail closed | `IA17-ID-JSON-001` (PASS) |
| Verifier substitution or rebinding is impossible | `IA17-VERIFIER-SUB-001` (PASS) |
| No private key material at rest in DB/WAL/SHM/dump/backup | `IA17-DB-AT-REST-001` (PASS) |

## Historical tests updated (allowed, stricter only)

Per the test-modification discipline, three historical integration tests and two
historical runtime tests were updated because they simulated the trusted relay
return by calling the removed minting helper.  Each update:

1. preserves the historical rationale in a comment (see the history note in
   `tests/integration/test_core_background_response_recovery_001.py`),
2. states the superseding invariant — the receipt may now only exist because a live
   provider return happened inside the ephemeral window or because a genuine
   external RSA proof was verified,
3. is strictly stronger: the new helper opens the real ephemeral window and
   registers the real handler-returned object, and the tests additionally assert
   the absence of the removed helper, that `live_window=None` is refused with
   `LiveReturnAuthorityError`, and that no receipt/handoff row exists afterwards.

The RED evidence for the removed fallback is the unfixed probe run
(`BASELINE_RED.md`): the removed helper is exactly what `IA17-MINT-001`,
`IA17-MINT-002` and `IA17-OBJGRAPH-001` exercised.

## Known non-regression noise (explicitly NOT a Corrective-002 regression)

`tests/c15_persistence/test_resident_surface.py` fails **locally** on any branch
that changes `src/aios_core`, because the checker additionally diffs the pinned
tree against the local `main` ref (`_pinned_tree_digest`) and reports
`RESIDENT_SURFACE_CHANGED` whenever that diff is non-empty.  All twelve behavioural
comparisons in its own evidence are `true`:

```
comparisons_all_true = True  comparisons_false = []
pinned src/aios_core clean= False  (diff: src/aios_core/runtime/__init__.py +9, background_attempt.py, late_return.py, turn_runtime.py, cognitive_runtime.py)
pinned reviews/internal_habitation/c14-resident/v2/release clean= True
pinned reviews/internal_habitation/c15-rcc/v1 clean= True
```

Independent confirmation that this is an artifact of the local refs, not a
Corrective-002 regression:

* the same test failed identically for the Window 17 reviewer on the *unmodified*
  candidate (`reviews/…IA_WINDOW_17/raw/candidate_resident_surface_1.txt`) while
  passing at the base head (`…/raw/candidate_resident_surface_base_head_1.txt`:
  `1 passed`);
* the candidate's formal CI job `110903891101` ran the identical step
  ("Resident-visible behavioural gate") to `success` with a `src/aios_core`-changing
  PR;
* the file and its tooling are outside the allowed Corrective-002 scope and were
  not modified (`SCOPE_MANIFEST.md`).

The formal core regression scope (`tests/unit tests/integration tests/runtime
tests/habitation`) does not include this file; the workflow's separate resident gate
step is exercised by CI at the exact head (`FORMAL_CI_RESULTS.md`).
