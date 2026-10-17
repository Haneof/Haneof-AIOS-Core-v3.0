# AIOS Gateway v0.4 — owner-authored PR task inbox for Arena Agent Mode

**EXPERIMENTAL DRAFT PR; NOT LIVE ON main.**
Requires separate PM security approval and actual production event validation before
any agent may treat it as an activated task route.

## Why PR rather than Actions or Issue API?

Arena Agent Mode's official coding/GitHub feature supports connecting an account,
pushing a branch and creating a PR. The actual Arena session previously reported
that its managed GitHub Actions connector was unsupported and its sandbox gh token
did not demonstrate Actions/Issues write operations. These are different paths:
the GitHub-backed PR workflow *may* be available even without a GitHub Actions
dispatch tool. This proposal must be tested as a real event to know.

**No write privilege is granted by this code.** If Arena cannot create a PR
in this repo as authenticated GitHub owner Haneof, the route remains BLOCKED;
never give Arena a PAT, private key, Operator signing capability or production
Codespaces access.

## Exact authorized PR request format (after activation)

In the Arena **Agent Mode coding workspace**, use the official GitHub connection,
select repository Haneof/Haneof-AIOS-Core-v3.0, and create a new same-repository
branch based on main. Create *only one* file:

    agent-tasks/gateway-request.json

File content (no other text, exactly three JSON fields):

~~~json
{
  "schema": "aios.agent.gateway.pr.request.v0.4",
  "task": "pr370-artifact-audit",
  "candidate_head": "6fb725407569bc719c049587f67fe65e797eb734"
}
~~~

Exact PR title:

    [AIOS-GW-V04] pr370-artifact-audit

Base branch: main. PR author: **Haneof** (authenticated GitHub user);
head repository: the same Haneof/Haneof-AIOS-Core-v3.0 repository, **not a fork**.
The PR must contain only **one ADDED file**, the task JSON path above:
no changed code, workflows, tests, README, lock files, or other files.

Current active task choices on main (v0.2):
- gateway-selftest
- pr370-source-boundary
- pr370-artifact-audit

Optional v0.3 *proposed* choices become available only if v0.3 is separately
approved/merged first:
- pr371-evidence-integrity
- r005-binding-ledger

The task in JSON and the suffix in the PR title must be identical.
The JSON candidate commit is fixed for all tasks (PR370 HEAD above).

**Never merge a task-request PR into main.** It exists solely as a one-shot
nonsecret request; review the resulting run, freeze evidence, and close the
request PR without merging. New tasks require a newly opened one-file PR.

## How the public Linux runner is isolated

The trusted default-branch workflow uses pull_request_target **only** on opened
PRs where path agent-tasks/gateway-request.json was added. This event type
requires exceptional care: it must **never** checkout or run untrusted head code.

Implemented guards:

1. Before running, verify the PR author really is Haneof; repository head and
   base are identical approved owner repo, not a fork; base is main.
2. Checkout **the exact trusted base commit SHA**, never head, with
   persist-credentials:false and a read-only contents:read GitHub token.
3. Load the trusted fixed parser from base. Treat PR commits only as immutable
   Git blobs (git fetch/diff/show/cat-file/ls-tree); **never checkout PR head**.
4. Require the net diff from the base to head be *exactly one added regular
   100644 JSON file* with the fixed name. Any other PR file, symlink,
   executable, renamed file or source code edit is rejected.
5. Parse at most 512 bytes of strict UTF-8 JSON, reject duplicate keys and
   any added fields or unrecognized task; pin the PR370 candidate identity.
6. Emit a literal allowlisted task name to GITHUB_OUTPUT and invoke only the
   existing default-branch Gateway static byte auditor with Python -I.
7. Upload sanitized JUnit, JSON, SHA256 receipts, with seven-day retention.
   No network callbacks, production private keys, signed enrollment,
   persistent self-hosted daemon, SSH, arbitrary shell, or real Resident.

The pull_request policy-test workflow uses PR code, but runs only in an
ephemeral GitHub-hosted runner, with no secrets and read-only permissions. That
test **does not run in the pull_request_target privileged job**.

## Acceptance and operational stages

1. v0.4 Draft PR CI: synthetic tests must prove owner-only authorization,
   fork/other-user rejection, exact diff shape, valid JSON, no arbitrary
   command/ref and trusted-base command sequencing.
2. Independently review GitHub Actions permissions, PR-target runner checkout
   and the exact-file policy. **Do not merge until fresh PM authorization**.
3. After approval, activate only v0.4 workflow on main, keeping frozen PR
   #370/#371/#367 and Window69 security review entirely untouched.
4. Try *one actual* Arena-created owner PR as above, if Arena GitHub Connector
   supports this. Verify a real pull_request_target Actions run with the
   correct task, SHA, JUnit and uploaded evidence.
5. If Arena PR author is a bot account, fork, only has read access, or its
   connector cannot create PRs in this repository, **STOP/BLOCKED**. Do not
   relax allowlist or impersonate the owner automatically.
6. Close the one-shot task PR after evidence inspection, **without merging**.

## Formal validation disclaimer

A PR inbox task PASS means only NON_FORMAL_PUBLIC_CI_EVIDENCE. It does NOT:
- resolve seven binding Window67 original38 failures;
- verify live TTY-less Ed25519 Response Authorization or remote CAS;
- close PM54-BLK-001/002/003 or Publisher Import equivalence;
- count as Window69 independent qualified Linux formal validation;
- authorize PR370/371/367 merges, real Resident A/B/C, or Cursor1 reveal.

No new Codespaces or cloud secrets are needed; the runner is an ephemeral GitHub
Actions Linux environment, not a public always-on machine.
