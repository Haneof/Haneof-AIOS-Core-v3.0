# Stranded commit `22e1053` — disposition

## What happened

`22e1053` was committed locally on 2026-09-30 and **not pushed** because the
session `GH_TOKEN` was invalidated while it was being prepared; `gh` and
`git push` both began returning 401. It was reported as stranded.

## Disposition: LOST to a re-clone, then reproduced byte-faithfully

Immediately after the PM HOLD (comment `5905176583`) restored GitHub access, the
working clone was found to have been **re-created**: the reflog contained only

```
2559182 HEAD@{2026-09-30 06:09:12 +0000}: clone: from https://github.com/Haneof/Haneof-AIOS-Core-v3.0.git
2559182 HEAD@{2026-09-30 06:09:13 +0000}: checkout: moving from main to arena/01a0f07b-haneof-aios-core-v3-0
```

with no prior history, and `22e1053` was an unknown object. The commit had never
been pushed, so no remote copy existed. The `.git` object store therefore no
longer holds `22e1053`, its parent link, or its tree, and the abbreviated identity
recorded in the earlier report is the only surviving identifier.

What survived was the **file content**, via the workspace snapshot. That made
byte-faithful reproduction possible, which is the disposition the PM asked for.

## Recoverable identity

| field | value |
|---|---|
| abbreviated id as reported | `22e1053` |
| full SHA | **not recoverable** (object lost with the old `.git`) |
| parent | `dd88dca17d1927225015bf82b2180d114e9e29f7` (recorded before the re-clone) |
| tree | **not recorded** before the re-clone |
| changed paths | **1** — `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001/pr_body.md` |
| nature | evidence-only: final candidate/pin evidence, PR body evidence, CI run IDs, tripwire disclosure |

The single changed path was established by diffing the working tree against the
pushed head `dd88dca` in a detached worktree, which showed exactly one differing
file, `pr_body.md`. No source, test, or tooling file differed.

## Reproduction

The content was restored verbatim, so its effect is now carried by the linear
history of this branch:

| commit | content |
|---|---|
| `dd88dca` | unused-import removal + `full_suite_local_result.md` (pushed) |
| `30a38c4` | **the reproduced `22e1053` payload** — PR body with final pin, CI run ID, and tripwire disclosure |

No history was rewritten and no commit was amended to hide anything. `dd88dca`
and everything before it are untouched, and the reproduction was appended as a
normal forward commit rather than a fixup of the lost object.

`30a38c4` additionally carries the `CI_VALIDATION_GAP` corrective itself, so the
reproduced evidence and the fix it documents landed in the same commit. This is
recorded plainly rather than dressed up as a faithful one-to-one restore, because
it is not one.

## Why no object was recovered

`22e1053` was unreachable from any ref and had no remote copy, and the reflog
that would have named its full SHA was itself destroyed by the re-clone. Git
cannot manufacture the object: the commit's own hash depends on its exact
metadata, so the full SHA is permanently unknown. Claiming otherwise would be
worse than stating the loss.
