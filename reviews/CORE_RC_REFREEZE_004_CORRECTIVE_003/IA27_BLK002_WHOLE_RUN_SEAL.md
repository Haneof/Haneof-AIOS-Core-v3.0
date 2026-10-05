# IA27-BLK-002 — whole-run seal correction

## RED-first record

`raw/RED_FIRST_POSTREAD_LOCAL_MOCK.txt` re-executes the exact final-seal shell from #336 head `5a5d384f16798bfff46ffe03f87310b0eafb2321` before workflow edits. Its mocked canonical ref returns A, advances to B immediately after that response, and then returns run/comment metadata still bound to A. The old shell exits zero and prints `WHOLE_RUN_IDENTITY_SEAL=PASS` while the ref is B.

This is only a local mocked-shell reproduction. It is not presented as hosted Actions evidence; the required hosted A→B barrier control is separately recorded in `HOSTED_POSTREAD_CONTROL.md` after it runs.

## Corrective mechanics

1. **Ref-scoped server cancellation request:** every push to the canonical session branch enters the same workflow-level concurrency group with `cancel-in-progress: true`. This requests cancellation of the in-flight older run; the hosted control does not rely on this alone.
2. **No early authority:** the publisher remains fixed inline logic, with no checkout and no candidate executable. It can publish only a provisional commit comment. The comment is never edited into an authoritative success state.
3. **Exact whole-run binding:** the read-only seal validates the exact run id, attempt, event SHA, branch, and provisional comment. It performs the canonical ref read only after the run/comment metadata checks, making it the last canonical-branch read in the job.
4. **Post-read settle plus independent successor exclusion:** only after that final read does the job wait through a settle barrier and query the Actions workflow-run ledger. A newer run number on the canonical branch fails the stale seal even if cancellation has not yet completed. The seal can print `WHOLE_RUN_IDENTITY_SEAL=PASS` only after its own run is still present and no successor is present.
5. **Live authority predicate:** a pin is never self-authorizing. Acceptance requires the overall run, exact-run seal, no newer workflow run, and the canonical branch still pointing to the exact candidate SHA at the time of acceptance. Any later A→B movement invalidates A's provisional pin even if an old Actions status remains visible.

The hosted control holds run A after its last canonical read, pushes B, and observes the real same-ref workflow concurrency plus the explicit successor ledger. In the recorded run A remained active through the barrier; the ledger step failed after B's newer run existed, and A's overall conclusion was `cancelled`. Thus the explicit post-read check—not an unsupported assumption that cancellation always wins—prevented a stale success. The B successor completed its control seal. Raw run/job ids and conclusions are recorded in `HOSTED_POSTREAD_CONTROL.md` after execution.

## Security/carry-forward contract

- Job A remains read-only and checkout keeps `persist-credentials: false`.
- Candidate tests and controls do not receive write permission.
- The publisher is the only job with `contents: write`; it has no checkout and no candidate script and makes exactly one POST to the commit-comments endpoint.
- The publisher treats transport failure and every status other than HTTP 201 as failure.
- The whole-run seal and post-read control seal are read-only and do not checkout candidate code.
