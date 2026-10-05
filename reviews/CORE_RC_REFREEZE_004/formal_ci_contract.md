# CORE-RC-REFREEZE-004 - Formal exact-head CI contract

Workflow: `.github/workflows/core-rc-refreeze-004-formal-gate.yml`.

The final candidate run must:
- start with `git fetch --all --prune`;
- assert the event SHA equals the remote branch head;
- materialize exact frozen software `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`;
- assert frozen root/Core/tests/workflow/package Git object identities;
- reject protected implementation drift from frozen software to fresh live main;
- use CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2;
- run all binding regression, reviewer-probe, Route B security, real SIGKILL, clean-wheel, backup/restore, writer/restart/FIX, C15 debt, and open-PR inventory gates;
- emit raw evidence plus runtime SHA256SUMS as an Actions artifact and commit comment.

Once the final candidate head is created, no additional evidence-only commit is permitted. Any explanatory addition after the final run goes only in the PR body/comment.
