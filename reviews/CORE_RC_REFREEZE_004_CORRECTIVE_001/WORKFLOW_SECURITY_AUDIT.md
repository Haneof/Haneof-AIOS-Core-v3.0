# WORKFLOW_SECURITY_AUDIT

Pre-commit static audit = PASS:
- gate read-only;
- checkout credential persistence disabled;
- dispatch pinned;
- rc/JUnit classifier fail-closed;
- terminal immutability after candidate execution;
- old same-job publisher and test||cat bypass absent;
- publisher depends on gate, owns minimum write permission, has no checkout/candidate helper and requires HTTP 201.

The formal run repeats static audit and publisher fault injection in read-only Job A.
