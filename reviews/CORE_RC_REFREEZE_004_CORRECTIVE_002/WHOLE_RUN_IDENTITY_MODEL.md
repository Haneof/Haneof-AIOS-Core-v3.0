# Whole-run identity model

Corrective-002 closes the race with layered mechanics rather than one extra branch check.

1. Same-ref server-side concurrency uses cancel-in-progress: true.
2. Job A is read-only and ends with local HEAD, canonical remote head, frozen object, tracked-mutation, credential, and protected-drift checks.
3. The write-capable publisher has no checkout and no candidate executable.
4. Publisher performs fresh canonical equality before POST.
5. The exact-pin comment is PROVISIONAL_PENDING_FINAL_IDENTITY_SEAL.
6. Only HTTP 201 succeeds; transport and every non-201 response fail.
7. Publisher performs fresh canonical equality after POST.
8. A final read-only seal validates exact run/head/branch/attempt and provisional-comment binding, waits through a cancellation-propagation guard, then performs another fresh branch/run/comment seal.
9. A provisional pin is authoritative only when overall run SUCCESS, final seal SUCCESS, and canonical branch equality all hold.

Thus drift before publication, between check and POST, after POST, between jobs, or between pre-seal and final seal cannot leave the stale run authoritative SUCCESS.
