# C15-RCC-RES-A-RERUN-005 — OPERATOR-ONLY Environment Handoff

> Access class: OPERATOR_ONLY / NOT_RESIDENT_VISIBLE

Window 51 stopped before cursor 1 because the Resident-safe packet omitted the approved runtime path and mechanical verification command. This is a preflight packaging gap, not Resident contamination and not a Phase-A failure.

## Approved environment identity

The previously accepted operator-prep environment contract pins:

- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2
- SQLite 3.45.1
- OpenSSL 3.0.13

Prepared runtime path:

`/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python`

## Operator action

First test whether the prepared runtime already exists:

```bash
test -x /home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python
```

If it exists, do not rebuild it. Emit only mechanical environment status to the Resident and let the Resident run the packet-pinned verification command.

If it does not exist, the Resident must remain BLOCKED. Environment construction is OPERATOR-ONLY. Use the previously independently accepted resident-safe bootstrap artifact in an isolated operator worktree; do not expose historical control-plane or Resident semantics to Window 51.

Accepted bootstrap provenance (operator-only):
- historical accepted operator-prep candidate: `77dac70e0cf054c3f0fb7d94a66dba221fe7d5de`
- bootstrap path: `reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/bootstrap/bootstrap_runtime.sh`
- bootstrap SHA-256: `e98965d8b55f5e8202c9470af2a3ca175ccde9f93427de5d6cf717921c3ea497`
- wheel lock SHA-256: `6fa2587c98662588e4758ac9b579fee8d800ce4fc2d36e692dbaaabd6f4c8afe`
- accepted verify form: `bash <bootstrap_path> --verify`

The operator may mechanically materialize that exact accepted bootstrap privately to provision the runtime. Window 51 must never read this file, the historical candidate identifier, or historical operator-prep contents.

After the runtime is prepared, provide Window 51 only:
- prepared runtime path;
- version/status output;
- `RUNTIME_ENV_OK` verification result.

Do not provide bootstrap provenance/history to the Resident.


## Exact approved materialization procedure

Use a separate temporary Operator worktree so the historical bootstrap verifies against the exact historical identity it was independently accepted with. Do **not** run its internal RC-identity verification against current main.

Historical bootstrap worktree commit:

`77dac70e0cf054c3f0fb7d94a66dba221fe7d5de`

Example mechanical procedure from the current repository root:

```bash
set -euo pipefail

CURRENT_REPO="$(git rev-parse --show-toplevel)"
CURRENT_MAIN="$(git -C "$CURRENT_REPO" rev-parse origin/main)"
EXPECTED_CURRENT_MAIN="6f6982b23c45ed5ae8b3a56a412c605d2220694d"
HISTORICAL_BOOTSTRAP_COMMIT="77dac70e0cf054c3f0fb7d94a66dba221fe7d5de"
HISTORICAL_WORKTREE="/tmp/aios-c15-rerun005-bootstrap-operator"
RUNTIME_ROOT="/home/user/.cache/c002/final-runtime-003"
BOOTSTRAP_REL="reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/bootstrap/bootstrap_runtime.sh"
EXPECTED_BOOTSTRAP_SHA256="e98965d8b55f5e8202c9470af2a3ca175ccde9f93427de5d6cf717921c3ea497"

test "$CURRENT_MAIN" = "$EXPECTED_CURRENT_MAIN"
git fetch --all --prune
git cat-file -e "$HISTORICAL_BOOTSTRAP_COMMIT^{commit}"

rm -rf "$HISTORICAL_WORKTREE"
git worktree add --detach "$HISTORICAL_WORKTREE" "$HISTORICAL_BOOTSTRAP_COMMIT"

BOOTSTRAP="$HISTORICAL_WORKTREE/$BOOTSTRAP_REL"
test -f "$BOOTSTRAP"
printf '%s  %s\n' "$EXPECTED_BOOTSTRAP_SHA256" "$BOOTSTRAP" | sha256sum -c -

AIOS_REPO_ROOT="$HISTORICAL_WORKTREE" \
AIOS_RUNTIME_ROOT="$RUNTIME_ROOT" \
bash "$BOOTSTRAP" --build

AIOS_REPO_ROOT="$HISTORICAL_WORKTREE" \
AIOS_RUNTIME_ROOT="$RUNTIME_ROOT" \
bash "$BOOTSTRAP" --verify

git worktree remove --force "$HISTORICAL_WORKTREE"
```

The historical worktree is used **only** to construct and self-verify the already-accepted runtime toolchain. It is not a Resident state source and must never be exposed to Resident A.

After construction, return to fresh current main and run the exact `approved_runtime.resident_verify_command` from:

`reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/RESIDENT_SAFE_LAUNCH_PACKET.json`

Only if that current-main verification prints `RUNTIME_ENV_OK` may the Operator hand back mechanical environment status to Window 51.

If current main has moved from the value above, do not blindly continue. Verify that the move is governance/Resident-safe launch material only and that the accepted integration baseline/pinned C15 implementation identities remain unchanged. Otherwise stop for PM adjudication.
