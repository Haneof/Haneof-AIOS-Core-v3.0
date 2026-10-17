# AIOS Remote Agent Gateway v0.3 — immutable Window67 evidence audits

**Activation gate:** DRAFT PR. These additional tasks are **not active on main**
until separate PM review and explicit permission. Current v0.1/v0.2 task
dispatch continues unchanged.

## Motivation and precise limits

Window67 preserved an independent FAIL disposition and historical binding failures
that must not disappear from later reports simply because a new signed path is
implemented. v0.3 adds public, read-only Git evidence consistency checks usable by
ChatGPT via owner-authored GitHub Issue (v0.2) or by an authorized Actions-write
client using workflow_dispatch.

No new task performs real signed responses, external Resident calls, isolated
UID/GID testing, crash injection, end-to-end Core/C15 execution or independent
formal security acceptance. A PASS is **not** authority to merge PR370.

## Two new exact allowlisted jobs

- **pr371-evidence-integrity**
  - Freshly verify frozen engineering PR370 ref and public independent Window67
    PR371 branch \`review/window67-formal-security-evidence\` exact HEAD
    \`391c4815ac77ef82cabcf13798de4d8fa8e7c0b0\` and Git tree
    \`d4dc287feb2e59f42bdaadbc15cf4d3406c9845a\`.
  - Require pinned independent SHA256.json digest and its exact closed set of
    **154** entries. Compare repository Git tree against the manifest with no
    extra/missing files. Stream-by-blob hash and size-check all members, including
    raw JUnit, old/new regression stdout and the independent report.
  - Never execute the scripts included as historical evidence. Never load
    untrusted Python code from PR370 or PR371.

- **r005-binding-ledger**
  - Verify frozen Window66 engineering regression claim and Window67
    independent \`WINDOW67_TEST_RESULTS.json\`, both from pinned commits.
  - Assert exact 38 tests = **31 PASS / 7 FAIL / 0 SKIP**, and parent 38 has
    the identical seven FAIL names; Window55 = 33/33 and Window57 = 29/29.
  - Assert PM54 blockers and Publisher import equivalence remain UNVERIFIED,
    and Window67 stays FORMAL_VALIDATION_FAIL / DO_NOT_MERGE.
  - Preserve the exact seven binding case names. Produces a machine-readable
    ledger for a later independent PM adjudication. It cannot close one.

## Dispatch syntax after separate activation

The **existing** owner-only Issue v0.2 schema is unchanged, with additional
fixed allowed tasks. Example, authenticated GitHub author must be \`Haneof\`:

Issue title: \`[AIOS-GW-V02] r005-binding-ledger\`

Body: JSON and nothing else:

~~~json
{
  "schema": "aios.agent.gateway.issue.request.v0.2",
  "task": "r005-binding-ledger",
  "candidate_head": "6fb725407569bc719c049587f67fe65e797eb734"
}
~~~

To validate the full original Window67 evidence set, use exact title
\`[AIOS-GW-V02] pr371-evidence-integrity\` and match its task in the JSON body.

Both are also selectable in the v0.1 Actions workflow_dispatch's choice list
**only if/after** the new v0.3 version is approved and installed on default main.

## Governance and external AI connector limits

- GitHub Actions job: GitHub-hosted ephemeral ubuntu-latest; contents: read;
  no GitHub Secrets, private keys, Enrollment, production tokens, SSH or public
  arbitrary-command endpoints.
- Only the reviewed Gateway code runs. Candidate blobs and Window67 evidence are
  **read as static data**, never invoked.
- PR370, PR371, PR367, Core/C15, frozen original tests and sealed Cursor1
  remain untouched.
- PM Window68 readiness is Operator-reported, not formal validation; Window67
  failure/Window69 independent reviewer obligations remain binding.
- Arena currently has not demonstrated authenticated GitHub Issues-create or
  Actions-write capability; v0.3 does not grant it new privileges.
- New data domains, changing candidate SHAs, launching Python candidate tests,
  credential-bearing Runs or multiple external Agent provider write permissions
  require separate explicit authorization and review.
- GitHub Actions run artifacts have finite retention; if preservation is needed,
  archive sanitized machine-readable evidence under an approved evidence-only PR.
- Do not interpret \`gateway-evidence/*/result.json status:PASS\` as Window69
  security PASS or independent acceptance.

## Required acceptance before activation

1. Exact v0.3 PR diff and immutable commit identities reviewed.
2. Synthetic tests for manifest path traversal, incorrect sha/size, extra files,
   duplicate metadata and falsified historical PASS are green.
3. GitHub Actions \`pull_request\` CI must actually perform both read-only tasks
   on the pinned PR370/371 sources and upload per-task JUnit/JSON/SHA256.
4. Separate PM merge authorization to main required. After approval, use
   an authenticated owner-created Issue to test each actual \`issues: opened\`
   path and verify no dispatch occurs for untrusted submitters.
