# IA27-BLK-002 — whole-run seal correction

## RED-first record

`raw/RED_FIRST_POSTREAD_LOCAL_MOCK.txt` re-executes the exact final-seal shell from #336 head `5a5d384f16798bfff46ffe03f87310b0eafb2321` before workflow edits. Its mocked canonical ref returns A, advances to B immediately after that response, and then returns run/comment metadata still bound to A. The old shell exits zero and prints `WHOLE_RUN_IDENTITY_SEAL=PASS` while the ref is B.

This is only a local mocked-shell reproduction. It is not presented as hosted Actions evidence; the required hosted A→B barrier controls are separately recorded, with raw run/job/comment API snapshots, in `HOSTED_POSTREAD_CONTROL.md`.

## Corrective mechanics

1. **Ref-scoped server cancellation request:** every push to the canonical session branch enters the same workflow-level concurrency group with `cancel-in-progress: true`. This requests cancellation of the in-flight older run; the hosted control does not rely on this alone.
2. **No early authority:** the publisher remains fixed inline logic, with no checkout and no candidate executable. It can publish only a provisional commit comment. The comment is never edited into an authoritative success state.
3. **Exact whole-run binding:** the read-only seal validates the exact run id, attempt, event SHA, branch, and provisional comment. It performs the canonical ref read only after the run/comment metadata checks, making it the last canonical-branch read in the job.
4. **Post-read settle plus independent successor exclusion:** only after that final read does the job wait 180 seconds, then query the Actions workflow-run ledger. A newer run number on the canonical branch fails the stale seal even if cancellation has not yet completed. The seal can print `WHOLE_RUN_IDENTITY_SEAL=PASS` only after its own run is still present and no successor is present.
5. **Live authority predicate:** a pin is never self-authorizing. Acceptance requires the overall run, exact-run seal, no newer workflow run, and the canonical branch still pointing to the exact candidate SHA at the time of acceptance. Any later A→B movement invalidates A's provisional pin even if an old Actions status remains visible.

The two hosted controls hold each A run after its last canonical read, push B during the 180-second barrier, and observe the real same-ref workflow. In both rounds, A's lineage-check step failed after the B successor run was created; each A overall conclusion was `cancelled`, while each B successor completed its control seal with overall `success`. These outcomes establish that the old A did not finish `SUCCESS`; the explicit post-read check is not replaced by an assumption that cancellation always wins. Hosted log ZIP retrieval returned `EOF`, so the precise emitted line is not claimed; raw run/job/step conclusions, pin comments, run identities, and ref snapshots are preserved in `HOSTED_POSTREAD_CONTROL.md` and its `raw/` references. These control runs skipped the formal gate and whole-run formal seal, so they are not acceptance runs.

## Security/carry-forward contract

- Job A remains read-only and checkout keeps `persist-credentials: false`.
- Candidate tests and controls do not receive write permission.
- The publisher is the only job with `contents: write`; it has no checkout and no candidate script and makes exactly one POST to the commit-comments endpoint.
- The publisher treats transport failure and every status other than HTTP 201 as failure.
- The whole-run seal and post-read control seal are read-only and do not checkout candidate code.
