# C15-RCC-RES-B-PREFLIGHT-002 — Environment Manifest (CORRECTIVE-006 exact, frozen)

This manifest freezes the exact environment the Resident B process will run under.
Any deviation MUST STOP before B start (no pip install, no upgrade).

## Frozen runtime (exact, verified at probe)

| Component | Exact Version / Hash | Verification |
| --- | --- | --- |
| Python | `Python 3.11.2` (3.11.2) | `python3 --version` |
| Pydantic | `2.13.5` | `python3 -c "import pydantic; print(pydantic.__version__)"` |
| Wire protocol | `a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a` (v1.0.1 mechanical, capability string) | `echo "a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a  harness/resident_wire_protocol.json" | sha256sum -c -` |
| Contract | `28d3262f56b7ef93a32a842f1d4d66f99748f2b07adcece43e815eb9d5cd18ef` (exact bytes of RESIDENT_B_RUN_CONTRACT.md, `RESIDENT_B_RUN_CONTRACT.md` not truncated) | `echo "28d3262f56b7ef93a32a842f1d4d66f99748f2b07adcece43e815eb9d5cd18ef  reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md" | sha256sum -c -` |
| Core tree | `fe77f8a0706acfaf369041d0882b6d0e6de39f22` | `git ls-tree HEAD -- src/aios_core` |
| Frozen software | `773876f92d5f8e53422f8f5a68cc651953d93052` | `git rev-parse HEAD` |
| Adapter | `bridged_model_handler:ExternalBrokerClient` `1.0.0-frozen` `c15-rcc-b-wire-v1` sha `e1053dbd1ff39c4508a37314f6e625290118d6c23209d51375b3c4232f54b538` | `sha256sum harness/bridged_model_handler.py` |

## Dependency freeze

`pip freeze` SHA-256: `bd7a76d1171c137f...` (full `bd7a76d1171c137f9daee9c0a3dbff029b8cbbccef88f0a1aff7907710a82375`)

Relevant pinned packages:
```
pydantic==2.13.5
pydantic_core==2.46.5
```

Full freeze is stored as `harness/requirements.freeze.txt` (hash `bd7a76d1171c137f9daee9c0a3dbff029b8cbbccef88f0a1aff7907710a82375`).

Live `pip freeze` is compared to this file in E2E step 0: `diff <(pip freeze | sort) <(sort harness/requirements.freeze.txt)` must be empty or only allowed drift (e.g., pip version). Mismatch → STOP.

## OS / Kernel

OS `Debian 12 (bookworm)` and kernel `Linux 6.1.158+` are **informational**, not frozen gate, because they are not required for deterministic release. Only Python/Pydantic/wire/adapter/contract/Core are frozen. If a future release needs to freeze OS/kernel, it must be added as exact check.

## Allowed env (operator pass-through)

| Variable | Value | How set |
| --- | --- | --- |
| `PYTHONPATH` | `src:reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/harness` (operator must set) | operator |
| `HOME` | `/home/nobody` | jail |
| `TMPDIR` | `/tmp` | jail |
| `PATH` | `/usr/local/bin:/usr/bin:/bin` | sanitized |
| `AIOS_B_SESSION_ID` | `b-session-XYZ` | operator |
| `AIOS_MAILBOX_ROOT` | `$RUN_ROOT/mailbox` | operator |
| `AIOS_CONTRACT_SHA256` | `28d3262f56b7ef93a32a842f1d4d66f99748f2b07adcece43e815eb9d5cd18ef` | operator |
| `AIOS_WIRE_PROTOCOL_SHA256` | `a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a` | operator |
| `AIOS_ADAPTER_SHA256` | `e1053dbd1ff39c4508a37314f6e625290118d6c23209d51375b3c4232f54b538` | operator |
| `AIOS_REAL_PROVIDER_API_KEY` | `<redacted>` | operator (required for prod) |
| `AIOS_REAL_PROVIDER_ENDPOINT` | `https://broker.example/...` or `http://127.0.0.1:<port>/v1/chat` (FakeBrokerServer for probe) | operator (required) |
| `AIOS_PROVIDER_ADAPTER` | `bridged_model_handler:ExternalBrokerClient` (exact, pinned, no fake) | operator (pinned) |
| `AIOS_RELEASE_STATE_PATH` | `$RUN_ROOT/runtime/release_state.json` | operator |
| `AIOS_CURRENT_EVENT_PATH` | `$RUN_ROOT/current-event.json` | operator per cursor |
| `AIOS_CURRENT_EVENT_BINDING_PATH` | `$RUN_ROOT/binding/current-event-binding.json` (immutable, 0400) | operator per cursor |
| `AIOS_EVIDENCE_DIR` | `$RUN_ROOT/evidence` (durable failure receipts) | operator |

## Explicitly stripped

`LD_*`, `PYTHON*`, `SUDO*`, `SSH_*`, `http_proxy`, `GIT_*`, `GH_*`, `_RESIDENT_JAIL_*`, `PROBE_*` unless `AIOS_ALLOW_PROBE_ENV=1`.

## Provider-visible

Only `{ system: contract, wire_protocol: schema, wire_protocol_sha256: hash, messages: [{role:user, content: envelope_json}] }` — no env, no path. Transport is HTTP POST via `ExternalBrokerClient` (pure transport, no Atlas/silence decision).

## Probe asserts (must pass before B)

- `python3 --version` must equal `Python 3.11.2`
- `python3 -c "import pydantic; print(pydantic.__version__)"` must equal `2.13.5`
- `echo "a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a  harness/resident_wire_protocol.json" | sha256sum -c -`
- `echo "28d3262f56b7ef93a32a842f1d4d66f99748f2b07adcece43e815eb9d5cd18ef  reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md" | sha256sum -c -`
- `echo "e1053dbd1ff39c4508a37314f6e625290118d6c23209d51375b3c4232f54b538  harness/bridged_model_handler.py" | sha256sum -c -` (adapter pinned)
- `diff <(pip freeze | sort) <(sort harness/requirements.freeze.txt)` must be empty (or only pip/setuptools drift)
- `git ls-tree HEAD -- src/aios_core` must equal `fe77f8a0706acfaf369041d0882b6d0e6de39f22`
- Mismatch → STOP, do not run B (no `pip install` at release).

## File manifest

- `harness/resident_wire_protocol.json` + `.md` (pinned `a6bbeaef...` v1.0.1)
- `harness/bridged_model_handler.py` (pinned `e1053dbd1ff39c4508a37314f6e625290118d6c23209d51375b3c4232f54b538
- `harness/requirements.freeze.txt` (full freeze `bd7a76d...`)
- `harness/resident_jail.py` env allowlist
- `isolation/probe_e2e.sh` asserts exact versions (step 0) `EXPECTED_CHECKS=77` (must match executable)
