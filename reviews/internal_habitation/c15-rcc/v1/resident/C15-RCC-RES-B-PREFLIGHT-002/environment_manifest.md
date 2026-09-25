# C15-RCC-RES-B-PREFLIGHT-002 — Environment Manifest (CORRECTIVE-004 exact, frozen)

This manifest freezes the exact environment the Resident B process will run under.
Any deviation MUST STOP before B start (no pip install, no upgrade).

## Frozen runtime (exact, verified at probe)

| Component | Exact Version / Hash | Verification |
| --- | --- | --- |
| Python | `Python 3.11.2` (3.11.2) | `python3 --version` |
| Pydantic | `2.13.5` | `python3 -c "import pydantic; print(pydantic.__version__)"` |
| OS | `Debian GNU/Linux 12 (bookworm)` | `/etc/os-release` |
| Kernel | `Linux e2b.local 6.1.158+ #1 SMP PREEMPT_DYNAMIC Mon May 11 18:48:24 UTC 2026 x86_64 GNU/Linux` | `uname -a` |
| Wire protocol | `5067701b003f99c141ecef1874ae8195ea2faf1ef5caa87cae092b57cad38b38` | `sha256sum harness/resident_wire_protocol.json` |
| Contract | `28d3262f…` (exact bytes of RESIDENT_B_RUN_CONTRACT.md) | `sha256sum reviews/.../RESIDENT_B_RUN_CONTRACT.md` |
| Core tree | `fe77f8a0706acfaf369041d0882b6d0e6de39f22` | `git ls-tree` |
| Frozen software | `773876f92d5f8e53422f8f5a68cc651953d93052` | `git rev-parse` |

## Dependency freeze

`pip freeze` SHA-256: `bd7a76d1171c137f...` (full `bd7a76d1171c137f9daee9c0a3dbff029b8cbbccef88f0a1aff7907710a82375`)

Relevant pinned packages:
```
pydantic==2.13.5
pydantic_core==2.46.5
```

Full freeze is stored as `harness/requirements.freeze.txt` (hash `bd7a76d1171c137f9daee9c0a3dbff029b8cbbccef88f0a1aff7907710a82375`).

## Allowed env (operator pass-through)

| Variable | Value | How set |
| --- | --- | --- |
| `PYTHONPATH` | `src:reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/harness` (operator must set) | operator |
| `HOME` | `/home/nobody` | jail |
| `TMPDIR` | `/tmp` | jail |
| `PATH` | `/usr/local/bin:/usr/bin:/bin` | sanitized |
| `AIOS_B_SESSION_ID` | `b-session-XYZ` | operator |
| `AIOS_MAILBOX_ROOT` | `$RUN_ROOT/mailbox` | operator |
| `AIOS_CONTRACT_SHA256` | `28d3262f…` | operator |
| `AIOS_WIRE_PROTOCOL_SHA256` | `5067701b003f99c141ecef1874ae8195ea2faf1ef5caa87cae092b57cad38b38` | operator |
| `AIOS_REAL_PROVIDER_API_KEY` | `<redacted>` | operator (required for prod) |
| `AIOS_REAL_PROVIDER_ENDPOINT` | `https://broker.example/...` | operator (required) |
| `AIOS_PROVIDER_ADAPTER` | `bridged_model_handler:RealProviderClient` | operator (pinned) |
| `AIOS_RELEASE_STATE_PATH` | `$RUN_ROOT/runtime/release_state.json` | operator |
| `AIOS_CURRENT_EVENT_PATH` | `$RUN_ROOT/current-event.json` | operator per cursor |
| `AIOS_EXPECTED_EVENT_PATH` | (same as current for binding) | operator |

## Explicitly stripped

`LD_*`, `PYTHON*`, `SUDO*`, `SSH_*`, `http_proxy`, `GIT_*`, `GH_*`, `_RESIDENT_JAIL_*`, `PROBE_*` unless `AIOS_ALLOW_PROBE_ENV=1`.

## Provider-visible

Only `{ system: contract, wire_protocol: schema, wire_protocol_sha256: hash, messages: [{role:user, content: envelope_json}] }` — no env, no path.

## Probe asserts (must pass before B)

- `python3 --version` must equal `Python 3.11.2`
- `python3 -c "import pydantic; print(pydantic.__version__)"` must equal `2.13.5`
- `sha256sum harness/resident_wire_protocol.json` must equal `5067701b003f99c141ecef1874ae8195ea2faf1ef5caa87cae092b57cad38b38`
- `sha256sum RESIDENT_B_RUN_CONTRACT.md` must equal `28d3262f…`
- `pip freeze` must contain `pydantic==2.13.5` (or hash must match)
- Mismatch → STOP, do not run B (no `pip install` at release).

## File manifest

- `harness/resident_wire_protocol.json` + `.md` (pinned)
- `harness/requirements.freeze.txt` (full freeze)
- `harness/resident_jail.py` env allowlist
- `isolation/probe_e2e.sh` asserts exact versions (step 0)
