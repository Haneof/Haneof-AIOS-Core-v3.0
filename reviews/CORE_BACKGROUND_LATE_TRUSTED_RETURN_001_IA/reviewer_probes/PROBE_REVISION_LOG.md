# Reviewer probe revision log

Both revisions below are reviewer **harness** corrections. Neither revision changed
any fixed acceptance expectation in `PROBE_CONTRACT.md`, and no expectation was
rewritten in response to candidate behavior.

## Revision 1 — before any valid candidate result

- **Old SHA-256:** `58e660a3a958e6364c4c91662c2223e96fd844ea93732f24b262f9786cf36b52`
- **Failure observed:** first execution aborted inside `IA14-ID-001` before reporting
  any result. The probe built the deliberately conflicting provenance/usage directive
  outside its refusal handler, so `ModelDirective.__post_init__` raised
  `ValueError("usage provider conflicts with model-call provenance")` as an unhandled
  harness exception.
- **Classification:** reviewer harness bug, not candidate failure. The fixed expectation
  is unchanged: conflicting provenance/usage identity must be rejected, never attached.
- **Changed lines:** `probe_conflicting_provider_identity`, old lines 255–275. Directive
  construction now happens inside the refusal-catching block; the proof/attach path is
  retained as the fall-through branch and must fail closed if the constructor is ever
  weakened.
- **New SHA-256:** `73d4a0b8a14620f72325bd5f0c8f90da0ccaa6d58da3d45d8e87b3d1797610f8`

## Revision 2 — before the complete candidate result published in `raw_candidate_independent_probes.txt`

- **Old SHA-256:** `73d4a0b8a14620f72325bd5f0c8f90da0ccaa6d58da3d45d8e87b3d1797610f8`
- **Failure observed:** `IA14-SIGKILL-001` reported `recovery raised TurnAlreadyCompleted`
  even though the resume had already attached and applied the exact late response with
  one meter and no redispatch. The second `run_turn` was used to probe terminal
  short-circuiting; Core's frozen terminal contract is to **refuse** reruns of a completed
  turn (`TurnAlreadyCompleted`), which is the correct short-circuit. My harness wrongly
  required that second call to return a `FusedTurnResult`.
- **Classification:** reviewer harness bug, not candidate failure. The fixed expectation
  is unchanged: one real process loss attaches exactly one observed return, no provider
  redispatch, one meter, one terminal durable effect.
- **Changed lines:** import of `TurnAlreadyCompleted` (line 33); `probe_real_sigkill_recovery`
  terminal block, old lines 514–537 and 538–555. The second `run_turn` now accepts
  **either** the completed result **or** `TurnAlreadyCompleted` as a safe terminal outcome,
  and the pass condition additionally requires `calls == []` and `len(meters) == 1` to have
  held across both invocations.
- **New SHA-256:** `969112b3a13566e30d7cbd4af4e2ecc3299a1cdd9f0f1a62419ef5688d46f181`

The three genuine product failures (`IA14-ORACLE-001`, `IA14-NONCE-001`, `IA14-NS-001`)
that appeared in the first complete run are preserved unchanged in
`raw_candidate_independent_probes.txt` and are reported in the IA report as blockers.
The final complete run is stored separately as `raw_candidate_independent_probes_final.txt`.
