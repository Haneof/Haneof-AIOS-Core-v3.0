# Window57 exact candidate handoff — TRANSPORT ONLY

This is a delivery wrapper, not a replacement engineering candidate. Its GitHub branch/commit must never be substituted for the frozen engineering HEAD below. Do not run gates on the transport wrapper. An independently authorized Operator must import the bundle's **original commit object** and push that same SHA to the candidate branch, then open its Draft PR. No cherry-pick, recommit, rebuild, amend, rebase or merge.

| Identity | Value |
| --- | --- |
| WINDOW / mode | 57 / FORMAL_GATE_CORRECTIVE_003 |
| Fresh main | 271fa28d695efaeb1c888d93024eeddac9c8aa9f |
| Failed candidate / required bundle prerequisite | adf391178d7494ed17e1db802a31f001fb3b5f3b |
| Original new corrective HEAD | 9d3b19b0e7bf090e5d472d9781b9156f73ea2088 |
| Original new corrective tree | ba3d75c309e144e5e93a32de5582f9b26da925ed |
| Target candidate branch | c15-rerun005-formal-gate-corrective-003-window57 |
| Bundle SHA256 | 9476eaf609b5f419017dfd57f12dc3f579ae64dca2d0cbac7161fec6525e1094 |
| Bundle Git blob SHA | 3726fb13f41a47c6299a01eac30a3eea6d029807 |
| New Artifact SHA256 | e3afa5bcf5f55667767fecac5151f3cf53c69950fabeb11c47c7cded4cc4f222 |
| Final packet SHA256 | 04123169ec305273bd971f6254acb66f4bfdccf9bcce29d52e3d93d9fadf5e0c |

The incremental bundle requires the already-published PR364 failed commit. It contains original commit 9d3b19b0 with that direct parent, retaining all ancestry in the repository. `git bundle verify` passed. Independent import into a new Git directory with the prerequisite installed recovered exactly the HEAD/tree above; ancestor verification passed.

Direct HTTPS push failed because this environment lacks a GitHub write credential (`could not read Username`). Connected commit creation cannot preserve the frozen commit's explicit author/committer metadata; attempts to pass those parameters were rejected before execution. It was not used to regenerate a replacement candidate. The connected tools can publish this explicitly identified **transport wrapper** containing the original bundle bytes.

## Authorized Operator import

Use a fresh private repository checkout with approved GitHub write access. Download the raw bundle from this transport branch (do not save a GitHub HTML view), verify SHA256 first and then:

```bash
git fetch --all --prune
git cat-file -e adf391178d7494ed17e1db802a31f001fb3b5f3b^{commit}
git bundle verify "$BUNDLE"
git fetch "$BUNDLE" HEAD
test "$(git rev-parse FETCH_HEAD)" = 9d3b19b0e7bf090e5d472d9781b9156f73ea2088
test "$(git rev-parse FETCH_HEAD^{tree})" = ba3d75c309e144e5e93a32de5582f9b26da925ed
git merge-base --is-ancestor adf391178d7494ed17e1db802a31f001fb3b5f3b FETCH_HEAD
git push origin 9d3b19b0e7bf090e5d472d9781b9156f73ea2088:refs/heads/c15-rerun005-formal-gate-corrective-003-window57
```

Then open a **Draft** PR to main from that exact candidate branch. If the branch already exists at a different SHA, stop and report rather than force-push. Verify exact remote HEAD/tree and unchanged Core/C15/old evidence. The bundle already contains all engineering source, full delivery tar/member inventory/packet and original logs under Window57; this transfer needs no reconstruction.

## Disposition

RED_FIRST=PASS. W56_DELIVERY_001=CLOSED for engineering packaging mechanics. ARTIFACT_IDENTITY=PASS; 22 closed members, stable deterministic builds. Independent-directory materialization/pinned verify PASS; genuine different-environment delivery PENDING. W56_REG_001=PM_ADJUDICATION_REQUIRED; historical import assertion remains FAIL. The route-B equivalence claim is **not proved**; proposal includes both routes, executable partial attacks and outstanding real-process positives/attacks. TTY versus historical stdout-token compatibility also needs adjudication.

Development: new 29 PASS; unchanged Window55 31 PASS / 2 AF_UNIX ERROR; unchanged historical38 compatibility 31 PASS / 7 FAIL. These are not formal validation. ENV001/ENV002=ENVIRONMENT_GATE_PENDING; FORMAL38/REAL_CORE_C15_INTEGRATION=PENDING; INDEPENDENT_ACCEPTANCE=NOT_STARTED; REAL_RESIDENT_STARTED=NO; CURSOR1_REVEALED=NO. No source security checks weakened; no Core/C15/product test/old evidence edits.

Engineering disposition remains PM_ADJUDICATION_REQUIRED. **Canonical candidate branch and candidate Draft PR publication are pending authorized Operator import.** This transport Draft PR proves durable delivery of the original exact commit, not successful canonical publication, validation or launch authorization.
