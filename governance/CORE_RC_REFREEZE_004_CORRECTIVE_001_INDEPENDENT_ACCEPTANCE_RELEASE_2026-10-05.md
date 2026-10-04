# CORE-RC-REFREEZE-004-CORRECTIVE-001 Fresh Independent Acceptance — PM Release Decision

Date: 2026-10-05

Fresh PM verification:
- live main: `08a0fa1ac77252b85f28afc3723097af217d0254`
- failed predecessor PR #325 remains OPEN / UNMERGED @ `70134269ddfc7c80c4a703a933253bd099746504`
- Window 25 review PR #328 remains REVIEW_ONLY / UNMERGED @ `5b46b70f1b166a28201b3865d455d6ba0e2afec5`
- corrective candidate PR #330: OPEN / non-draft / UNMERGED / DO NOT MERGE
- exact candidate: `2380121639865b1bd29176cf944f5a20afe4112d`
- parent: `04c37f7dd8ba6f20e1c67dad43c0f21087f51eeb`
- tree: `72d3cd0da849fae3b1cbfdfb7ae995528e1cfd71`
- exact failed-candidate delta: 2 commits ahead / 0 behind
- exact delta paths: RC004 formal workflow + `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/**` only
- frozen software remains `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`
- final formal run `37217853558` = SUCCESS
- formal Job A = SUCCESS
- mandatory publisher Job B = SUCCESS
- artifact `11309495093`, digest `sha256:02415a0457af3aec5cb50d5195120202aae2c9cb23d3c81cbefaf867b7d216e0`
- mandatory commit comment `203380647` binds exact run/head/frozen software.

## Decision

`CORE-RC-REFREEZE-004-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE = READY`

`WINDOW 27 = RELEASED`

Window 27 is Fresh Independent Acceptance only.

It must independently attempt to falsify the three closure claims and the corrected formal workflow. Author self-tests, static probes, PR body, and formal GREEN are navigation/claims-to-falsify only.

Specific independent attack priorities:
1. C15 rc/JUnit classifier fail-closed behavior beyond the author 10-case matrix.
2. Credential isolation and terminal immutability, including a TOCTOU analysis between Job A terminal check and Job B / overall workflow completion.
3. Mandatory exact-pin publisher failure semantics and minimal write authority.
4. No scope expansion / no frozen Core mutation.
5. Carry-forward frozen Core/security/recovery guarantees.

No repair, merge, PM Integration, C15 repair, Resident, evaluator, or public release/tag is authorized in Window 27.
