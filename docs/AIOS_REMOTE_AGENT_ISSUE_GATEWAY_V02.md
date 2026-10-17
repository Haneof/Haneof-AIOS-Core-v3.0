# AIOS Agent Issue Gateway v0.2 (PUBLIC / OWNER-AUTHORED / NON-FORMAL)

**v0.2 activated on main via PR #373. v0.3 read-only task additions are separate Draft changes requiring PM approval before activation.**

This gateway lets an AI with a legitimate GitHub **Issues-write** connector, including
an authorized ChatGPT GitHub app, request an allowlisted nonsecret GitHub Actions
job by opening a carefully structured repository Issue. It does **not** grant any
privilege to Arena's reported read-only GitHub token. If Arena has no issue-create
authority, Arena still cannot dispatch by this route.

The preexisting v0.1 manual workflow_dispatch continues to work.

## Why this exists

Arena reported its hosted GitHub connector as unsupported, and its available gh
session did not establish authorized Actions-write permissions. Its previous run
did not attempt or complete a new Actions task; it only inspected an old Run.
We do not assume that merely being able to read a public repository allows an
agent to post an Issue, create a PR, or trigger workflow_dispatch.

Technical nuance: a 403 from Actions permission **settings** endpoints and an
empty X-OAuth-Scopes header alone cannot characterize every fine-grained
PAT or GitHub App permission. The relevant practical fact remains: Arena has
**not demonstrated** an authorized dispatch interface. An agent's local
working branch is also irrelevant to workflow_dispatch when the caller
explicitly sends ref=main; our main-only guard is intentional.

## GitHub Issue task protocol

Authenticated Issue owner must be the exact GitHub login: Haneof.
The GitHub Actions workflow also checks author identity before starting a job.
The Issue must be new (issues.opened), not an edited comment or reply.

Issue title (choose ONE exact value):

    [AIOS-GW-V02] gateway-selftest
    [AIOS-GW-V02] pr370-source-boundary
    [AIOS-GW-V02] pr370-artifact-audit
    [AIOS-GW-V02] pr371-evidence-integrity   (v0.3 ONLY, pending merge)
    [AIOS-GW-V02] r005-binding-ledger       (v0.3 ONLY, pending merge)

Issue description must be **only** a JSON object of three fields, e.g.:

~~~json
{
  "schema": "aios.agent.gateway.issue.request.v0.2",
  "task": "pr370-artifact-audit",
  "candidate_head": "6fb725407569bc719c049587f67fe65e797eb734"
}
~~~

Title task and JSON task must match. No extra fields, freeform URLs, code,
shell snippets, token values, unsigned grants, private data, or arbitrary ref.

- Gateway consumes event contents via GITHUB_EVENT_PATH, **not string interpolation
  into a shell command**.
- Strictly parse JSON, reject duplicate keys and payloads over 512 UTF-8 bytes.
- Hard-pin repository, Issue author, action, title, v0.2 schema, approved PR370
  candidate HEAD and the unchanged v0.1 3-task allowlist.
- Only emit a validated fixed task literal to GITHUB_OUTPUT; execute the v0.1
  public read-only runner using the GitHub-hosted ephemeral runner.
- GitHub workflow permissions: contents:read. No Issues, Actions or secrets
  write access is granted to the job. No self-hosted runner or public shell.
- Issue jobs run the workflow checked into default main only, not code from
  the Issue author's branch; Pull Request validation is separate and not
  credentialed for signing.

## Activation and allowed clients

1. This v0.2 protocol has passed its own CI and been merged; any task-catalogue expansion (v0.3) must undergo fresh review and new authorization.
2. Issue dispatch is active for the three existing tasks; the two proposed v0.3 tasks do not exist on main until separately activated.
3. Any ChatGPT agent with authenticated GitHub Issues-write capability for
   repository Haneof/Haneof-AIOS-Core-v3.0 can create a new, exact owner-authored
   Issue with the protocol above (provided its actor is actually Haneof).
4. Observe the automatically triggered GitHub Actions run and verify its
   Run ID, task, source main SHA, unit-test logs, result.json, JUnit.xml
   and SHA256 index. If no run appears, report BLOCKED; do not claim PASS.
5. Arena currently reports a read-only gh token / unsupported managed
   connector: it **cannot** be assumed able to open the required Issue. An
   Arena-connected write integration or a separate, carefully designed
   request endpoint would be a new, separately authorized project.

Only an existing authorized account may create the Issue. Never paste GitHub
PATs, credentials, resident private keys or enrollment data into Issue bodies,
prompts, public repositories or chat.

## Example ChatGPT task request (after approval/activation)

> Use connected GitHub Issues-create capability to create exactly one Issue
> in Haneof/Haneof-AIOS-Core-v3.0, authored as Haneof. Title:
> [AIOS-GW-V02] pr370-artifact-audit. Body: the exact three-field JSON
> specified in docs/AIOS_REMOTE_AGENT_ISSUE_GATEWAY_V02.md. Wait for the
> matching Issues-triggered Actions run, verify the logs and artifact, and
> return the run URL and honest PASS/FAIL/BLOCKED status. No changes to
> engineering, tests, secrets, protected PRs or Real Resident operations.

## Verification separation

This is *NON_FORMAL_PUBLIC_CI_EVIDENCE* only. It does not close:
- Window67 formal security failure
- Window69 independent signed / no-TTY tests
- Original 38 tests' 7 binding historical failures
- PM54-BLK-001/002/003
- Publisher import safety equivalence

Never represent a gateway PASS as permission to merge PR370/371/367 or to
start Real Resident A/B/C or reveal Cursor1.

**Security boundaries:** owner-only Issue author identity, exact task,
pinned PR370 source bytes, no arbitrary shell, no shared sensitive credentials,
no new Codespace, no live external Publisher and no out-of-band security bypass.
