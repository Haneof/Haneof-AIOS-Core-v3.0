# C14-RES-A-001 — Resident A session facts

- Run id: `resident-a-restart-20260921`
- Task: `C14-RES-A-001` (status read from `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`: READY;
  dependency `C14-RES-FIX-003` DONE)
- Started from live `origin/main`: `87e52bceea4ee94b823200388a4f79b1b94eb1f3`
  ("review: accept FIX-003 and bind Resident A to blind execution contract", 2026-09-21 12:34:25Z)
- Session repository branch: `arena/01a0c473-haneof-aios-core-v3-0`
- Contract: `reviews/internal_habitation/c14-resident/v2/release/RESIDENT_A_RUN_CONTRACT.md`
- Release contract: `.../v2/release/release_contract.md`
- Fixture: `c14-resident-fixture-v2`,
  SHA256 `1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253` (never opened by the Resident)

## Resident model identity

| Field | Value |
|---|---|
| Declared Resident identity | `GPT-5.6 Sol` |
| Platform-exposed provider id | `unknown/not exposed` |
| Platform-exposed session id | `unknown/not exposed` |
| Provider token usage | not exposed to this window → `ModelUsage`/`ModelCallProvenance` omitted rather than fabricated |

No provider/model identifier is invented. Metering rows for Resident model rounds are therefore
recorded with `usage_complete=false`, which is the honest state for a same-window checkpoint bridge.

## Environment

- Repository root: `/home/user/Haneof-AIOS-Core-v3.0` (shallow/grafted checkout of `main`)
- Interpreter: `/home/user/.venv/bin/python` (Python 3.11.2, pydantic 2.10.6, pytest 9.1.1)
- `pyproject.toml` declares `requires-python >= 3.12`; only Python 3.11.2 is available in this
  environment. All required Core modules import and run on 3.11.2 (verified). This is an
  environment fact, recorded here rather than silently ignored.
- System `pip install` is PEP 668 blocked; a dedicated venv is used instead.

## Prior attempts explicitly not inherited

`c14/resident-a-sol-20260921-2036`, `c14/resident-a-sol-run-20260921`,
`c14/resident-a-sol-ci-20260921`, draft PR #74. No session, World, release state, cognition or
semantic trace from those attempts is used here. This run starts from a fresh private World.
