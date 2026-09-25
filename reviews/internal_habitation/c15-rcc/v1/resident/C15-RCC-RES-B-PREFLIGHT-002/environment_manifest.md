# C15-RCC-RES-B-PREFLIGHT-002 — Environment Manifest (CORRECTIVE-003 frozen)

This manifest freezes the exact environment the Resident B process will run under.
The probe E2E proves that no probe variable leaks into the Resident via unsanitized `env`.

## Frozen allowed env (operator pass-through, verified at sandbox entry)

| Variable | Value / Pattern | How set | Verified |
| --- | --- | --- | --- |
| `PYTHONPATH` | `/repo/src` (forced, not inherited) | `resident_jail` sets | `env | grep PYTHONPATH` inside jail shows only `/repo/src` |
| `HOME` | `/home/nobody` | jail sets | `echo $HOME` → `/home/nobody` |
| `TMPDIR` | `/tmp` | jail sets | `echo $TMPDIR` → `/tmp` |
| `PATH` | `/usr/local/bin:/usr/bin:/bin` (host minimal) | inherited but scrubbed of `LD_*` | `env | grep -E LD_/` none |
| `AIOS_B_SESSION_ID` | `b-session-XYZ` (runtime) | operator args `--run-root` / env | handler reads, not leaked to provider beyond envelope |
| `AIOS_MAILBOX_ROOT` | `$RUN_ROOT/mailbox` | operator env | handler reads |
| `AIOS_CONTRACT_SHA256` | `28d3262f…` (contract) | operator env | envelope field |
| `AIOS_PHASE` | `B` | operator env | envelope `phase B` |
| `FAKE_PROVIDER`/`FAKE_MODEL` | `fake-provider`/`fake-model-v1` (preflight only) | operator env | FakeProvider constructs provenance |

## Explicitly stripped (never reaches Resident)

These are removed by `resident_jail` before `drop privs + chroot`:

- `LD_LIBRARY_PATH`, `LD_PRELOAD`, `LD_AUDIT`, `LD_DEBUG` (all `LD_*`)
- `PYTHONPATH` (re-set, not inherited), `PYTHONHOME`, `PYTHONINSERTPATH`, `PYTHONSTARTUP`, `PYTHONDEBUG`, `PYTHONINSPECT`
- `SUDO_*`, `SUDO_COMMAND`, `SUDO_USER`, `SUDO_UID`, `SUDO_GID`
- `SSH_*`, `http_proxy`, `https_proxy`, `HTTP_PROXY`, `HTTPS_PROXY`, `no_proxy`
- `GIT_*`, `GITHUB_*`, `GH_`
- `_RESIDENT_JAIL_INJECT_*` (test seams stripped, not propagated)
- `PROBE_MODE`, `PROBE_ROUNDS` **unless** `AIOS_ALLOW_PROBE_ENV=1` explicitly (see below)

## Probe env handling (BLOCKER: must not leak via unsanitized env)

- Probe E2E originally set `PROBE_MODE`/`PROBE_ROUNDS` in host env and they were inherited unsanitized → **violation**.
- Corrective-003: `resident_jail` **drops** `PROBE_MODE`/`PROBE_ROUNDS` by default. Only when `AIOS_ALLOW_PROBE_ENV=1` is exported by the operator **explicitly** for the probe are they allowlisted and passed as `{"PROBE_MODE": ..., "PROBE_ROUNDS": ...}` into the sandbox. The E2E proves both paths:
  - `without AIOS_ALLOW_PROBE_ENV` → `env | grep PROBE` inside jail is empty.
  - `with AIOS_ALLOW_PROBE_ENV=1 PROBE_MODE=e2e PROBE_ROUNDS=2` → inside `PROBE_MODE=e2e` (same value operator set) — no blind unsanitized pass.
- Production B **never** sets `AIOS_ALLOW_PROBE_ENV`; so probe vars never leak into B.

## Provider-visible env

The provider side (`FakeProviderClient`/`RealProviderClient`) receives **only**:
```
{ system: <contract bytes>, messages: [{role:"user", content: envelope_json}], metadata: {phase, round} }
```
No host env, no `PROBE_*`, no `/repo/*` path, no leak.

## File manifest for re-verification

- `harness/resident_jail.py` — env allowlist at line ~309 (span including stripped list).
- `isolation/probe_e2e.sh` — sets `AIOS_ALLOW_PROBE_ENV` for the two PROBE leak checks (steps 7a/b).
