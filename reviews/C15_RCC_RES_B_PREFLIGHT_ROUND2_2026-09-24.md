# C15 operator preflight — round 2 evidence (PM/operator only)

Task remains **IN_PROGRESS / BLOCKED, not DONE**. PR #125 stays OPEN.
No real B/C; no frozen Core/fixture change; no merge/close/auto-merge.

## Remote / restored checkout / exact-head CI

Authorized read-only operations succeeded: `git ls-remote origin refs/heads/main`,
`gh pr view 125 --json state,headRefOid,headRefName,baseRefName,url`, and REST
`commits/80576f98f60a904f2db091e2c2a7566d7f486b0f/check-runs` plus
`actions/runs?head_sha=80576f98f60a904f2db091e2c2a7566d7f486b0f`.
Main remains `849bfd41c623fb336b392a3e6e933cfad93620e9`.
Only known permission failure: prior **Issue comment** write returned
`Resource not accessible by integration`. Not retried. No evidence that git/PR
reads or branch push permission were lost.

This turn's local snapshot had reset HEAD to main while retaining the 11
engineering files as untracked. Fetched the existing working-branch head,
byte-compared all 11 with the pushed tree, then restored the local branch pointer
using a mixed reset to that same existing remote head. No source file was
replaced; no new branch; no animation read. This was not a force push.

Old head `80576f98f60a904f2db091e2c2a7566d7f486b0f` checks:
- [c15-operator-preflight / synthetic-mechanics](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/35893213985): SUCCESS.
- [p16-convergence-gate / full-core-regression](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/35893213906): SUCCESS.
- Job API confirms setup-python, Python >=3.12 assertion, synthetic checks and
  required regression steps all executed and succeeded. Pinned workflow specifies
  3.12; no continue-on-error, ignored exit code or skipped key step.
- Old run ZIP log downloads failed at Actions results endpoint with EOF. Therefore
  old exact Python patch version and CI test counts were **not retrieved**, not
  inferred from local results. Do not transfer these successes to the new head.
- Current workflow adds machine-produced count/version/head notices from JUnit,
  allowing audit through check annotations even if ZIP logs remain unavailable.
  It runs all preflight tests, no skips allowed, and the existing 146 regressions.
  No private A or provider is required in public CI.

## Engineering and evidence

Code modules: `audit.py`, `transport.py`, `driver.py`, `clock.py`, `freeze.py`,
`restart.py`, `isolation_probe.py`; corresponding tests and workflow. README gives
exact interfaces and limitations. No shadow Runtime/database/answer rules.

- Request envelope v2 binds UUID, kind and canonical input digest. Synthetic wrong
  UUID/kind/hash, missing Summary, invalid output, EOF all stop. The bridge latches
  failure; recorder checks returned `continuity_summary_error` after Core catches
  a callback exception, retains failed raw result and does NOT mark completion.
- Frozen C15 release modules are exercised against freshly generated synthetic
  fixture files outside the checkout. The executable port rejects the real C15
  fixture hash. Canonical USER ingest and ordinary run_turn share exact routing,
  text/time/turn; non-user input uses the existing mechanical ingest adapter.
  Existing release verifier binds ACK to durable writes and rejects duplicate ACK
  or reveal. ACK != runtime processing completion.
- Driver persists phase intent before effects, holds a lifetime writer flock,
  refuses failed/interrupted phases, enforces monotonic time and stop boundaries.
  Prior deadlines use the existing habitation clock on the *same* Runtime/index;
  earlier Runtime requests cannot see the current event before ingestion.
  Summary/Wake/Review and C13 metering are normal Core paths. No manual budget
  increase, default silence or forced drain. Mechanical source/job caps stop.
  Core queued/deferred/RUNNING metadata is retained without copying old decisions
  into restart. General RUNNING-Wake/process-crash recovery is not yet complete.
- Freeze first rebuilds normal index, then holds BEGIN IMMEDIATE reservations on
  BOTH World/index while measuring and backing up the joint cut. A live WAL test
  proves committed sentinel retention; concurrent writers to either DB are
  actually rejected during both backups. Check watermarks, SQLite integrity,
  receipts, state/release hashes, then publish one private manifest. Interrupted
  second backup and changed release file produce FAILED, not a final package.
  Clean frozen restart validates an externally pinned manifest, copies durable
  state only, and continues without replaying trace. Mid-phase replay is refused.

## Python / tests

Local CPython **3.12.11**, upstream tag v3.12.11 commit
`55fee9cf216abe4ec0d1139f94b1930fbd0c7644`, built outside Git. SQLite **3.40.1**.
Normal standalone binary and apt downloads failed with TLS/EOF; git source fetch
worked. Built zlib 1.3.1 and supplied SQLite 3.40.1 headers against the installed
system library. Wheel-only dependencies installed offline from normal PyPI
fetches. **SSL and some optional stdlib extensions are absent**: suitable for
these executed offline mechanics, not a provider environment acceptance.
No pyproject requirement or gate threshold was lowered.

```sh
PYTHONDONTWRITEBYTECODE=1 /home/user/.cache/c15-python312/bin/python3.12 \
  -m pytest -o addopts='' -q tests/preflight
# 81 passed (final targeted run: 4.58s)
PYTHONDONTWRITEBYTECODE=1 /home/user/.cache/c15-python312/bin/python3.12 \
  -m pytest -o addopts='' -q tests
# 540 passed in 79.81s
```

Earlier round-2 intermediate gate: 66 preflight + 146 related = 212 passed on
3.12.11. Final counts above supersede that intermediate set. New synthetic peers
are explicitly test doubles; no model inference or Resident evidence.

## Private A / legal restart validation

A quartet was already obtained in round 1. Actual snapshot restoration this turn
confirmed `.cache/c15-accepted-a` was NOT retained. Re-fetched only the same five
allowlisted raw files at #117 @ `3e51f728d7959048b75fea01d405bc837b0e8185`,
not missing-source discovery and not reconstruction from B. Each file is mode
0400 in `/home/user/.cache/c15-accepted-a`, parent mode 0700.

On Python 3.12.11: verified all fixed hashes, Core tree, 88/88 and 13 durable refs;
staged an independent mode-0700 copy at `/home/user/.cache/c15-a-restore-check3`;
initialized existing Core/store/index/Review services ONLY on that copy with a
callback that fails any model request. Result:
`COPY_SERVICE_RESTORE_VERIFIED_NOT_RELEASED`, 88/88, **zero model requests**, next
Review deadline equals the durable Core marker plus 24h. Originals re-hashed
unchanged. Only mechanical fields reach the plan, fresh session and turn 1;
old A prose/decisions/transcript are not loaded into model context.

An initially overstrict validator required a COMPLETED marker; the actual latest
A marker is SUPPRESSED. Frozen Core treats terminal suppression as a scheduling
marker, so corrected the OPERATOR validator to match Core (not Core/World). No
suppression→semantic-success promotion. Next due time agrees after that correction.
This is service-level restore evidence, **not** execution of A due work or a B
session, and independent approval of restart/session remains required.

Cache survives processes in the current sandbox but is excluded from restored
session snapshots; no approved durable private store is available. It is not a
persistent handoff. Re-fetch method: authenticated raw Contents API at the fixed
A SHA for only the allowlisted filenames in `audit.HASHES`; verify hashes before
use. No A file, raw trace, credential, binary dependency, or cache is in this PR,
public CI or public artifact. Exact-copy tests are separate from synthetic CI.

## Actual isolation probe and remaining boundary

Unprivileged user namespace and mount/net/PID namespaces are operational. The
new probe executes **only synthetic Python**, not Resident, under a minimal
read-only chroot with no capabilities/no-new-privileges, no proc, no inherited
host directory descriptors, clean environment, and a disconnected net namespace.
Supervisor 3.12.11; minimal child `/usr/bin/python3.11` (OS isolation test only).
Actual open attempts denied: PM decision, operator source, .git/HEAD, private A,
sealed fixture path, standard git/gh credential paths. Credential/fixture bytes
are never read. Packet read works; write fails; chroot capability escalation,
external network and host proc/Git/gh access fail. **13/13 probe checks true.**

This improves on the FAILED plain same-UID subprocess probe; it does not change
that earlier finding. It proves only this minimal process boundary, NOT this
Arena agent's browser/search/Git/PR/tools or an actual Resident client. Missing:
approved host/broker connecting ONLY current request/reply streams, trustworthy
principal/tool restrictions, actual client denial tests and independent release.
Therefore isolation for the real Resident remains BLOCKED and the safe packet
remains `launchable=false`. Trusted model/provider usage remains UNKNOWN.

No task marked DONE; PR remains OPEN, no release granted. Engineering receipt
and public diff are for PM review, never Resident input.
