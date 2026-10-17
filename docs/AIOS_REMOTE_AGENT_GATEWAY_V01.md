# AIOS Remote Agent Execution Gateway v0.1 (PUBLIC / NON-FORMAL)

**Status:** v0.1 activated on main via PR #372. v0.2 owner-only Issue gateway activated via PR #373. v0.3 extension remains Draft until separately approved.
**Scope:** GitHub-hosted ephemeral Actions for fixed, nonsecret checks.
**Does not create a public shell server, SSH gateway, permanent Codespace, or autonomous Resident.**

## Components

| Component | Role |
|---|---|
| .github/workflows/aios-remote-agent-gateway-v01.yml | GitHub Actions event-to-task gate (read-only token; ubuntu-latest ephemeral VM). |
| tools/agent_gateway/runner.py | Python standard-library allowlist and exact frozen PR370 public-byte audits. |
| tests/agent_gateway/test_runner.py | Public test-policy and malformed-archive rejection tests. |
| gateway-evidence/ Actions artifact | result.json, junit.xml, SHA256.json with short-lived retention. |

No API server is exposed to the Internet. GitHub API authenticates the task submitter; GitHub Actions creates a new sandbox for each approved task. The external AI does **not** obtain a persistent OS session or host credentials.

### Allowed tasks (no arbitrary shell, no freeform Git ref)

- **gateway-selftest**: validates immutable pin and task-selection policy; accompanying CI runs unit/negative tests.
- **pr370-source-boundary**: fetches exact frozen PR370 branch and verifies the sole parent and changed-file allowlist; **does not run candidate code**.
- **pr370-artifact-audit**: reads exact PR370 Git objects, verifies TEST_ONLY launch packet, pinned artifact/manifest SHA256, closed 22-member archive hashes and metadata; **does not extract or execute candidate code**.
- **pr371-evidence-integrity** *(v0.3, pending activation)*: verify all 154 frozen Window67 independent evidence members against pinned SHA256, with no execution.
- **r005-binding-ledger** *(v0.3, pending activation)*: compare frozen Window66 and Window67 original38 failure names/counters and preserve formal FAIL / OPEN blockers.

Pinned PR370: 6fb725407569bc719c049587f67fe65e797eb734; sole parent: 9d3b19b0e7bf090e5d472d9781b9156f73ea2088.

The historical seven original regression failures, Window54 security gates, Window67 failed formal disposition, and Window69 independent validation are **not changed or bypassed** by this gateway.

## Deployment stages

1. **v0.1 active; v0.3 Draft:** existing three allowlisted tasks remain available on main. The v0.3 PR is proposed to test and add two new read-only tasks; do not claim the extensions are live until approved.
2. **Manual security and PM review:** confirm no secrets, no unapproved files, no automatic dispatch and no writable token. Do not merge merely to enable commands.
3. **v0.3 activation review:** the v0.3 workflow revision must be separately authorized for merge to main; no further merge is implied by the previous v0.1/v0.2 approvals.
4. **After approved activation only:** an AI/Operator with explicit GitHub Actions write access can submit one of the fixed workflow inputs. A GitHub agent that can only read PRs cannot start the workflow; use GitHub Actions UI or a properly authorized integration instead.

### Manual invocation after separate merge approval

On GitHub: Actions > aios-remote-agent-gateway-v01 > Run workflow > branch main > choose task.

With installed GitHub CLI and properly authorized Actions permissions:

    gh workflow run aios-remote-agent-gateway-v01.yml \
      --repo Haneof/Haneof-AIOS-Core-v3.0 --ref main \
      -f task=pr370-artifact-audit

    gh run list --repo Haneof/Haneof-AIOS-Core-v3.0 \
      --workflow aios-remote-agent-gateway-v01.yml

Each task produces its own short-lived JSON, JUnit and SHA256 receipt under gateway-evidence/<task>/, alongside CI unit-test logs and a job summary. Downstream AI may read the run and propose an **Evidence-only Draft PR** but cannot transform CI PASS into formal validation.

## AI integration contract

AI agent instruction:

> Read this gateway policy and current frozen PM approval. Choose exactly one allowlisted task. Submit via a GitHub account/app with Actions write permission only after separate activation on main. Do not request private tokens in chat. Read the resulting GitHub Actions run, result.json, JUnit and hash inventory. Summarize PASS/FAIL with exact run ID and log evidence. Do not claim authorization to merge or sign TEST_ONLY enrollment.

If a provider (including Arena) cannot invoke the Actions API, it may review the code/PR and suggest a task, but needs a separate authorized GitHub workflow trigger. Do not assume it has direct Codespaces access.

## Hard boundaries

- Workflow uses pull_request and workflow_dispatch; deliberately no pull_request_target, public callback/webhook execution endpoint, repository_dispatch accepting opaque commands, cron polling, or user-controllable shell.
- GitHub token is restricted to contents: read; checkout discards saved credentials. There are no secrets, id-token, cloud credentials or long-lived tokens in the workflow.
- workflow_dispatch has **one choice-only** input. v0.3 proposes a fixed five-value allowlist, with PR370/Window67 commit SHA pins. User-supplied code, paths, refs, hosts, URLs and shell fragments are **not accepted**.
- Candidate inspections use git show on exact frozen Git commit and tarfile in read-only inspection mode; not extractall, import, unpickle or shell execution.
- Workflow will not run on arbitrary manual-dispatch refs; main-only guard applies.
- GitHub-hosted runner, not a long-running privileged self-hosted runner holding Window65 issuer or Resident credentials. Never put sensitive test roots on a public-repository runner.
- No Window65/66 TEST_ONLY keys or usable enrollment, no real Resident, no sealed Cursor1, no production authority and no handling of sensitive internal data.
- CI uses standard-library Python 3.12 for gateway mechanics **not approved exact Python 3.12.14 / formal signature-and-UID environment**. It must not be labelled Window69 PASS.
- On mismatched Git ref/SHA, packet pin, member/path/mode or source scope: FAIL closed and publish a sanitized failure receipt.

## Review and operations

Review changed files against the isolated default-branch base. Keep PR370/371/367 unchanged. Never run unauthorized code against verbose space couscous or fuzzy robot. Any new task type, new frozen candidate, external endpoint, persistent execution, privileged issuer operation, or non-public credential requires a separately approved gateway version and PR.

**Gate v0.1 disposition:** non-formal public task runner and CI evidence pipeline only. Not a substitute for Window69 independent formal validation or a release authorization.
