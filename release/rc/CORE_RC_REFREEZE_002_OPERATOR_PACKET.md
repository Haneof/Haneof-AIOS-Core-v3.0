# CORE-RC-REFREEZE-002 Operator Packet

Status: **REVIEW_READY candidate — pending independent acceptance**  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`

## 1. Frozen software boundary

- frozen software commit: `27a21db5b656d441248b9240020910b66a223830`
- repository tree: `a2e6b03b306413a2d82ca4ca8c9fc7099c0dc065`
- `src/aios_core/**` tree: `a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6`
- `tests/**` tree: `92fcbcc5876833735fb3cb7c73a98c4a8a4a3541`
- historical frozen software workflows tree: `8d1ea1cbb9993f9ff29155e4d04833bd53b45272`
- package: `aios-core 0.3.0.dev0`
- required Python: `>=3.12` (formal freeze gate: CPython 3.12.14)

The RC PR may add freeze evidence, governance writeback, and the `core-rc-refreeze-002-formal-gate` workflow. It must not change `src/aios_core/**` or `tests/**`.

Historical CORE-RC-FREEZE-001 (`773876f9...` / Core `fe77f8a0...`) is **superseded**.

## 2. Clean build and install

```bash
git checkout 27a21db5b656d441248b9240020910b66a223830
python3.12 -m pip install --upgrade pip
pip install ".[dev]"
# or wheel:
python -m pip wheel . --no-deps -w dist
```

Formal observed versions: CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2.

## 3. Persistent data-path contract

Authoritative durable truth is the SQLite World (`--world` / `AIOS_WORLD_PATH`).

HMAC authenticity authority lives **in that same World**. Backup/restore must keep it. Index is rebuildable projection only.

Canonical writer lock: `<canonical-world>.writer.lock`. `--lock` / `AIOS_LOCK_PATH` cannot select a second writer.

## 4. Model adapter

`AIOS_MODEL_HANDLER` must be an importable `ModelHandler`. Smoke adapter:

`aios_core.headless.testing:deterministic_model_handler`

Not Resident evidence. No second World / cognition oracle.

## 5. Headless lifecycle

Same commands as CORE-RC-FREEZE-001 operator packet, against frozen software `27a21db5...`.

## 6. What this RC is not

- Not Resident A/B/C
- Not B persistence corrective resume
- Not RELEASE-003
- Not Independent Acceptance (this packet is GATE / REVIEW_READY only)
