# Reviewer probe freeze v1
Candidate exact H2 771b200c33dbd6055b1d209935f8e1552f13090f.
Frozen before any candidate execution. All six assertions expected to pass.
Concurrent operations must either serialize or fail closed without corrupting the ledger.
Request-file mutation before consume is expected to fail closed (additional attack).
Valid whole-tail deletion is explicitly expected to be undetectable, as permitted by PM.
No real Resident, fixture, evaluator, release source or real state is involved.
Source imports are deferred; collect-only does not import candidate code.
This initial suite is not a claim of exhaustive coverage; additional revisions must be frozen separately.
