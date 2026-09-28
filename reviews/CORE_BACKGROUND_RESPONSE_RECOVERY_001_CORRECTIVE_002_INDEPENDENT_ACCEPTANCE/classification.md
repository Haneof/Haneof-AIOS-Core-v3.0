IA-ADV probe revision 1 -- executed 2026-09-27 -- 49 collected, 40 passed, 9 failed.

Protocol note: rev1 is PRESERVED VERBATIM under /home/user/ia-probes-history/rev1.
No expected outcome is changed to chase GREEN; all 9 failures are classified as
PROBE-HARNESS DEFECTS (setup/signature/assertion-scope errors), not implementation
findings. Source revalidation was performed before each classification.

1. test_adv_c6  -- probe setup bug: inspected the attempt BEFORE run_wake admits
   it (inspect returns None pre-admission). Fix: inspect after the crash run.
2. test_adv_d6  -- probe scenario bug: fresh-schema background_model_responses
   declares authenticity_proof NOT NULL, so UPDATE..SET NULL raises IntegrityError
   before the probe runs. The NULL-proof state is the HISTORICAL migration shape
   (ALTER-added nullable column). Fix: rebuild as an old-schema migration test.
3. test_adv_e1  -- probe setup bug: queried the authority table before any
   BackgroundModelAttemptStore/FusedTurnRuntime ran _initialize (no such table).
4. test_adv_f2  -- probe assertion-scope bug: captured world revision BEFORE
   run_wake, which includes the legitimate pre-dispatch wake->running bookkeeping
   commit. Source: turn_runtime run_wake wraps cognitive run in try/finally only
   (no post-failure commit); delivery/completion commits occur only after success.
   Fix: scope the revision snapshot to the authentication-failure boundary.
5. test_adv_g1  -- probe assertion bug: terminal recorded state after ordinary
   completion is 'metered' (metering.py atomically closes the attempt), not
   'response_returned'. Fix: assert state in {'response_returned','metered'}.
6-8. test_adv_i1/i2/i3 -- probe API-signature bug: called ia_helpers.stage() with
   model_round_index= but the helper takes round_index= (TypeError). i2's child
   died of the same TypeError (exit 1) instead of SIGKILL. Fix call sites.
9. test_adv_j3  -- probe introspection bug: dir(instance) includes instance
   attribute 'store' which getattr on the class rejects. Fix: introspect the
   instance.

Implementation-side checks that PASSED in rev1 include: forged-HMAC rejection,
complete Corrective-001 bundle + proof forgery, payload substitution, nested
substitution, silence substitution, cross-attempt/work-kind/subject/round/provider
replay rejection, duplicate-returns conflict, not_submitted blocks after receipt,
durable tamper (receipt proof/identity/binding/payload-sha/staged rows/attempt
provenance) fail-closed after restart, authority single-key + restart stability +
shared-instance verification + deleted/invalid authority fail-closed +
backup/restore verification, failed-staging atomicity, receipt-before-provenance
ordering, identity-less local boundary (g2/g3/g4), historical cross-work
transplant rejection, recursive duplicate-JSON-key rejection, secret-leak scan.
