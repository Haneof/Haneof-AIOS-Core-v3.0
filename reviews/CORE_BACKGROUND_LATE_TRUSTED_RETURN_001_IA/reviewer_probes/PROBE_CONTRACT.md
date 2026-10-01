# WINDOW 14 independent reviewer probes — frozen contract

**Candidate under test:** `5ad0524c425592210ff184e00ad52abb2c14e366`  
**Baseline:** `25591825d88e98f30dfd3de1c7e7cbc6e53267dd`  
**Freeze rule:** `window14_independent_attack.py` is hashed in `SHA256SUMS` before its first candidate execution. Its acceptance expectations below are not changed in response to candidate behavior.

| ID | Fixed expectation | Attack boundary |
|---|---|---|
| `IA14-ORACLE-001` | A fresh recovery process holding normal Core objects cannot issue/retrieve a late-return capability and cannot attach arbitrary bytes. | `BackgroundModelAttemptStore` reached through an ordinary reopened `SQLiteWorldStore`; no observer is registered in process B. |
| `IA14-NONCE-001` | An ordinary recovery object cannot read the nonce and use it to turn arbitrary bytes into a trusted return. | Read-only SQLite open through public `SQLiteWorldStore.db_path`, then public late-proof verifier path. |
| `IA14-ID-001` | Any conflict between `ModelDirective.provenance` and `.usage` provider/model/request id is rejected. | A legitimate capability holder supplies one directive with all three pairs conflicting. |
| `IA14-NS-001` | No post-dispatch write site can turn a durable-bound attempt into `not_submitted`, including the typed failure route. | Public `mark_failure(... definitely_not_submitted=True ...)` after `mark_dispatching` commits its binding. |
| `IA14-JSON-001` | Duplicate nested JSON keys are rejected before semantic construction. | Duplicate `usage.provider` key. |
| `IA14-RACE-001` | Concurrent conflicting proofs produce one canonical staged response and one fail-closed conflict. | Two independent stores race response A/B against one issued capability. |
| `IA14-SIGKILL-001` | After real process death, a surviving observer can attach the one observed exact reply; fresh Core completes once without redispatch, with one meter, one durable output/terminal completion, and one metered attempt. | A child process runs `FusedTurnRuntime`, sends the observer-held capability over a pipe, then calls `SIGKILL`; process B reopens Core and resumes. |

The script does **not** monkeypatch runtime methods, fabricate database rows, alter source, or revise expected outcomes after execution. Private-by-convention names are intentionally reachable in the signing-oracle probe because Python `_name` is not access control, and the acceptance contract explicitly requires this question to be tested.
