# Resident A Evidence Package — C15-RCC-RES-A-RERUN-004-CORRECTIVE-001

## Run Identity

- **Task**: `C15-RCC-RES-A-RERUN-004-CORRECTIVE-001`
- **Role**: `Real Resident AI — Fresh Corrective Resident A`
- **Run Directory**: `reviews/internal_habitation/c15-rcc/v1/resident/runs/c15-rcc-res-a-rerun-004-corrective-001`
- **Resident Session ID**: `resident-a-rerun-004-corr-001-session`
- **Conversation Session ID**: `session-user-corr-001`
- **Subject ID**: `user_1`
- **Software Baseline (Frozen RC)**: `f20f2edfa7af00d0286493fd15196ca9503bc315`
  - Core Tree: `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
  - Tests Tree: `7e33b5ef8432370234965d3ccd61248c703c4019`
- **Final Disposition**: `BLOCKED` (Harness defect encountered post-reveal; mid-run harness modification strictly forbidden per Rule 14)

---

## Harness Freeze Summary

Before release-state initialization or cursor 1 reveal, the deterministic exchange bridge and harness were verified with 14/14 synthetic plumbing tests passing and frozen:

| File | SHA-256 Digest |
|---|---|
| `runner.py` | `2fc08f366145f84e7a8b9d607e28fff4f4ad09105ab318147b701bb04a20b7ab` |
| `exchange_bridge.py` | `3a0ed26c1c508462a8581b4be95170230729da2583215ea437cf9a6a443034d9` |
| `test_exchange_bridge.py` | `91eef4091e071e74ff282bc22820d50779005e6366239cd88c06b04e5de5c428` |
| `EXCHANGE_LEDGER_SCHEMA.json` | `68326a38eb22d1810fcb62c72450b583715543101fbebc93b4cbb8c6d89a443f` |
| `SYNTHETIC_TEST_OUTPUT.txt` | `748095a1fbba93f302710fad7c15226a8782f058283ae43df3340a37d1eeac1b` |
| `ENVIRONMENT_RECORD.json` | `676ae27b6a248db83941ef13e788e5b9e1e9414e21776ceb2a8903da7b42ded1` |

These files were verified before cursor 1 reveal and remained completely unchanged throughout.

---

## Contemporaneous Chronology

The exchange ledger `exchange_ledger.jsonl` contains 6 append-only, fsynced, hash-chained records:

1. `sequence: 1` — `request_published` (`req-0001-model_directive-6510beb0`, periodic_review)
2. `sequence: 2` — `response_published` (`req-0001-model_directive-6510beb0`, terminal silence)
3. `sequence: 3` — `response_consumed` (`req-0001-model_directive-6510beb0`)
4. `sequence: 4` — `request_published` (`req-0002-model_directive-3c99d45b`, user_turn round 0)
5. `sequence: 5` — `response_published` (`req-0002-model_directive-3c99d45b`, 3 capability calls)
6. `sequence: 6` — `response_consumed` (`req-0002-model_directive-3c99d45b`)

Ledger verification via `runner.py verify-ledger` confirms:
`Ledger verified: 6 records, unbroken sequence and hash chain.`

---

## Blocked Finding

In round 1 of user turn 1, `runner.py` encountered:
`AttributeError: 'CapabilityResult' object has no attribute 'arguments'`
when serializing `snapshot.capability_history`.

Under Rule 14 ("一旦真实 cursor 1 reveal：以下文件禁止再改：runner, bridge, exchange protocol... 不要像旧 A-004 那样边跑边修 runner 再继续") and Rule 24 ("任一 binding failure：输出：BLOCKED 并保留现场... 不要为了完成任务而继续"), the run immediately ceased execution and locked all evidence.

---

## Core & Repository Invariants

- Core tree (`src/aios_core/**`) drift: ZERO
- Tests tree (`tests/**`) drift: ZERO
- Historical PR #273 / #275: IMMUTABLE / UNTOUCHED
- Cursor 14: NEVER REVEALED
