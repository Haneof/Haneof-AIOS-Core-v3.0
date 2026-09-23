# C15 RCC RES B - Arena Resident Architecture Verification (2026-09-24)

Branch: `arena/01a0cf25-haneof-aios-core-v3-0` @ `5b5e2306c39b5b09b260de787403567a31d0efbd` (previous exact-head `2528c22a`)
PR #125 OPEN (BLOCKED / DO NOT MERGE)
Correction: Real Resident must be new Arena window AI itself, not external LLM API. External provider/API adaptation PAUSED.

## 1. Architecture Correction

- Previous iteration implemented `ResidentBroker` for external LLM API via HTTP POST, requiring endpoint/API Key.
- **Corrected**: Real Resident = AI itself in new Arena window, calling normal AIOS interfaces via Driver/Runtime.
- **Paused**: External provider/API adaptation work. Keep existing generic transport and tests, but MUST NOT mark as Arena Resident already connected or isolated.
- **Continue**: Specific defect fixes already done (publication non-mutating, freeze receipt verification via `load_and_verify_receipt`, broker structure boundary).

## 2. Expected Arena Resident Flow

Per `governance/prompts/C15_RES_B_OPERATOR_PREFLIGHT_PROMPT_2026-09-23.md` and corrective decision:

- Operator window (this window) prepares:
  - Exact copy of accepted-A World/index/release-state with hash verification
  - Legal restart state
  - Operator manifest (Core/A pins, input hash, source version, entry commands, isolation checks, mechanical verification, known limits)
  - Resident-safe packet manifest (only approved mechanical identifiers, entry, visible instructions, no cognition checklist, no expected behavior, no PM conclusions, no old run output)
  - Exact startup/step-by-step/freeze instructions, not letting Resident traverse repo to find instructions

- Resident window (new Arena window AI itself):
  - Receives only safe packet manifest, not repo, not PM reports, not sealed fixture/evaluator, not A/B old reports, not operator source
  - When Runtime requests model, operator exposes RuntimeSnapshot/capability schema
  - Resident must submit structured ModelDirective only, operator executes actual capability via Runtime, returns result
  - Logs: current input, Snapshot, actual directive, tool calls/results/errors, visible output, due-work/checkpoint, metering, World revision. Only observable behavior, no hidden chain-of-thought solicitation, unknown token/model identity stays UNKNOWN.
  - Each event: release → ingest → durable ack → normal expiration. USER run_turn and canonical ingest use consistent binding. Respects Core budget/delay semantics.
  - Final freeze: World/index/restart/release-state/trace/hash manifest with WAL-safe, index consistent

- Model judgment must come from Arena AI's real sequential output, not script replacing cognition. Prohibit synthetic script output as Resident cognition.

## 3. How New Arena Resident Window Actually Calls Normal AIOS Interfaces (Verification)

### Current Arena Platform Capabilities (Observed)

- Each session tied to fixed branch `arena/01a0cf25-...`, workspace persists, file changes saved automatically
- Bash tool rooted at repo root `/home/user/Haneof-AIOS-Core-v3.0`, can read any file in workspace
- Process tools `start_process` can bind 0.0.0.0 and expose LIVE PREVIEW via `https://{port}-{sandboxId}.e2b.app`
- `git` and `gh` available, authenticated
- No built-in per-window filesystem view restriction: any window can `read_file`, `bash ls`, `git diff`, `gh pr view`
- No built-in block for `reviews/internal_habitation`, `governance/prompts`, `tests/preflight` etc.

### Required Call Path for Arena Resident

Ideal:

```
Operator: Driver -> RuntimeRecorder -> RuntimeSnapshot (plain) -> Safe Packet File (e.g., /tmp/resident_packet.json)
Resident (new Arena window): reads safe packet file (only allowed file), produces ModelDirective JSON to /tmp/resident_response.json
Operator: validates via directive(), executes capability via Runtime, appends to trace.jsonl, continues
```

This requires:

- Resident window can only read safe packet file, not repo, not history evidence, not future materials
- Resident window can only write response file, not arbitrary repo files
- Resident window cannot call git/gh/bash to explore repo, cannot read `reviews/internal_habitation`, cannot read sealed future
- Resident window tool access limited to approved AIOS capability calls (via operator execution), not arbitrary shell/network

### Actual Verification Attempts

1. **File boundary**:
   - In this sandbox, `bash ls reviews/internal_habitation/c15-rcc/v1/runs/` succeeds, shows resident-a-final-rerun
   - `read_file governance/prompts/C15_RES_B_OPERATOR_PREFLIGHT_PROMPT_2026-09-23.md` succeeds
   - No mechanism to deny file reads for second window - both windows share same workspace root
   - **Result**: File boundary NOT verifiable with current platform, prompt self-discipline insufficient

2. **Repo/GitHub boundary**:
   - `git log --oneline` shows all history
   - `gh pr view 125` shows PR details
   - `gh api repos/...` would work if permitted
   - No per-window git config restriction observed
   - **Result**: Repo boundary NOT verifiable, must report limitation

3. **History evidence / future materials**:
   - `reviews/internal_habitation` contains private World, world_index, release_state, restart_state, ARTIFACT_MANIFEST, REPORT, driver.log, checkpoints, decisions, cursor_events
   - `governance/C15_RCC_COGNITION_SEMANTIC_FREEZE_2026-09-23.md` contains semantic freeze
   - Future C materials would be in `reviews/` or `governance/` if present
   - No mechanism to hide these from second window
   - **Result**: History/future boundary NOT verifiable

4. **Tool access**:
   - Arena provides `bash`, `read_file`, `write_file`, `edit_file`, `start_process`, `stop_process`, `get_process_output`, `web_search`, `fetch_page`, etc.
   - No allowlist to restrict second window to only AIOS capability calls
   - **Result**: Tool boundary NOT verifiable

5. **Isolation probe** (`tools/c15_preflight/isolation_probe.py`):
   - Attempts `unshare --user --map-root-user --mount --net --pid --fork` + `mount --bind` + `chroot` + `setpriv --no-new-privs --bounding-set=-all`
   - In GitHub runner and Arena sandbox, fails with `Operation not permitted` or `Permission denied`
   - Returns `INCONCLUSIVE` with message `unshare failed` or `mount setup failed`
   - Real resources (`pm`, `operator`, `git_metadata`, `private_a`, `sealed_future`, `git_credentials`, `gh_credentials`) remain `NOT_TESTED` by design (never inspect real credentials/private A)
   - Synthetic canary boundary probe can PASS in privileged env, but real isolation remains BLOCKED
   - **Result**: Actual namespace isolation INCONCLUSIVE/BLOCKED, not PASS

## 4. Platform Limitations (Specific)

1. **No per-window filesystem view**: Arena does not provide chroot/namespace per window with only safe packet visible. Both operator and resident windows see full repo. Cannot enforce file boundary without OS-level isolation which requires privileges not available.

2. **No per-window git/gh block**: No config to disable git/gh in resident window. Any window can run `git diff`, `gh pr view`, `gh api`.

3. **No per-window env var filtering**: Resident window inherits same env, can see `GITHUB_TOKEN`, `GH_TOKEN` if present (though Arena says never request/output secrets, but platform does not block).

4. **No per-window tool allowlist**: Arena's tool set is same for all windows, cannot restrict resident to only AIOS capability calls.

5. **Unshare/mount/chroot requires privileges**: `unshare --user --map-root-user` fails in current sandbox (confirmed in CI and local). `mount --make-rprivate`, `mount --bind` require CAP_SYS_ADMIN, not available. `setpriv --no-new-privs --bounding-set=-all` may work but without mount namespace it doesn't isolate filesystem.

6. **Network isolation**: `socket.create_connection(('192.0.2.1',443),timeout=1)` in probe checks external network denied. In Arena, external network is allowed for `web_search`, `fetch_page`, `pip install`, etc., so cannot claim external network denied without additional firewall.

7. **No built-in safe packet transport**: No platform-provided file pipe that is the only allowed file for resident. Would need to implement via operator-owned HTTP broker with explicit packet, but that broker itself runs in operator host with filesystem access, and resident would still need network access to call it.

8. **Model judgment source**: Arena AI's real sequential output comes from the model's actual generation in the window, not from a script. Current synthetic endpoint returns static JSON, not real cognition. Must not use script to replace cognition. Real Resident must be Arena AI itself producing ModelDirective via its own reasoning, observed via trace.

## 5. What Is Retained vs Paused

**Retained (synthetic only, NOT Arena Resident attestation)**:

- `tools/c15_preflight/resident_broker.py` - generic transport with structure boundary, request/reply binding, error propagation, credentials in HTTP auth layer. Marked `EXTERNAL_PROVIDER_PAUSED = True`, `REAL_RESIDENT_IS_ARENA_WINDOW = True`, note "synthetic transport only, NOT Arena Resident connected/isolated".
- `tests/preflight/test_resident_broker.py` - boundary tests: emits only plain snapshot, logs owned by operator, timeout fail-closed, no default silence. Still PASS as synthetic mechanics.
- `tools/c15_preflight/isolation_probe.py` - synthetic canary probe, real resources NOT_TESTED, resident_arena_isolation BLOCKED, launchable False.

**Paused**:

- External LLM API adaptation (no endpoint/API Key required from user)
- Marking broker as Arena Resident connected/isolated - MUST NOT
- Running real B/C (14-22 events, future C) - NOT executed, by design
- Self-release, DONE, B/C/R6 PASS while incomplete - NOT allowed

## 6. Required Execution Environment for Real Arena Resident (Proposal, Not Implemented)

To verifiably isolate Arena Resident window:

- Separate container or VM per resident window, with only `/packet/request.json` (read-only) and `/packet/response.json` (write-only) mounted, no repo, no git, no gh, no `reviews/internal_habitation`, no governance prompts beyond safe packet
- No `bash` with arbitrary file access, only tool that reads packet and writes response via explicit API
- Operator host owns repo, filesystem, GitHub credentials, trace.jsonl, and executes capability calls via Runtime
- Network: only allowed to operator host broker, not arbitrary internet, not GitHub API
- OS-level: user namespace, mount namespace, net namespace, pid namespace with no-new-privs, bounding-set=-all, chroot to empty root with only allowed files
- Audit: before/after canary checks for forbidden labels, positive control for allowed readable, packet readonly, clean environment, no host proc, no git/gh, chroot capability removed, external network denied

Current Arena platform does NOT provide this; would need additional infrastructure outside current Agent Mode.

## 7. Verification of Normal AIOS Interface Calls (How It Would Work)

If platform provided required boundaries, Arena Resident window would:

1. Operator prepares safe packet manifest in `/tmp/resident_packet/<request_id>.json` containing:
   - protocol `c15-resident-broker-v1`
   - request_id, kind runtime, input_sha256, input = plain(RuntimeSnapshot) with only approved keys
   - No operator private checkpoint, no credentials, no governance

2. Resident window (new Arena) reads packet, produces ModelDirective via real cognition (e.g., {"response": "..."} or {"tool_calls": [...]}) and writes to `/tmp/resident_response/<request_id>.json` with binding fields request_id/kind/input_sha256/output

3. Operator validates via `directive()`, executes via Runtime (legal AIOS capability calls retained), records observable behavior, continues

4. Each turn's judgment comes from Arena AI's real sequential output in resident window, not script. Trace shows model_requests increment, tool calls, etc.

5. File/repo/history/future/tool boundaries verified via canary checks before/after, not prompt self-discipline.

## 8. Current Status

- synthetic_mechanics: PASS (131 preflight + 146 regression, Python 3.12.14, exact-head 5b5e230)
- real_A_import: PASS (88/88, 13→14, model 0, cross-process PASS, exact-head 5b5e230)
- actual_namespace_probe: INCONCLUSIVE (unshare operation not permitted, expected)
- actual_Resident_isolation: BLOCKED (real Resident requires new Arena window with verifiable boundaries, platform cannot provide currently, no prompt self-discipline)
- launch_authorized: false
- PR #125: OPEN, no merge

## 9. No B/C Launch

- No real B14-22, no C future, no real Resident semantic experiment executed
- No self-release, no DONE, no B/C/R6 PASS while incomplete
- Model judgment must be from Arena AI real output, not script

## 10. Defect Fixes Continued (from previous round)

- publication.py: no sidecar deletion, immutable-only open, refuse if sidecar present, verify no sidecar created, preserve original bytes
- freeze: use load_and_verify_receipt not exists(), distinguish COMPLETED/UNCERTAIN/OPERATOR_CONFIRMED, parent fsync failure → UNCERTAIN cannot ordinary auto pass
- broker: structure boundary not blacklist, credentials HTTP layer, synthetic endpoint is transport test double, retain legal AIOS capability via Runtime

## 11. Conclusion

Real Resident must be new Arena window AI itself. External API route paused. Current Arena platform cannot provide required file/repo/history/future/tool boundaries verifiably; isolation remains BLOCKED. Specific limitations reported above, not replaced by prompt self-discipline. No API Key required. No real B/C run. PR stays OPEN.
