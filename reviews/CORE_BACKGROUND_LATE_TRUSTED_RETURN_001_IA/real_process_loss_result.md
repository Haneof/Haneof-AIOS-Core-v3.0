# Real process-loss probe (§25) — WINDOW 14

Frozen probe: `reviewer_probes/window14_independent_attack.py` → `IA14-SIGKILL-001`
(SHA-256 in `reviewer_probes/SHA256SUMS`, revision 2). Reviewer-owned; not the
author's test. Raw output:
`raw_candidate_independent_probes_final.txt`.

## Shape

1. **Process A** (real child via `multiprocessing` fork): builds a real
   `FusedTurnRuntime` over a real SQLite world DB, registers a pipe-backed
   `ExternalReturnObserver`, and runs `run_turn`.
2. At the provider boundary the handler calls `os.kill(os.getpid(), SIGKILL)` —
   the process is killed with signal 9 (exit code `-9` verified); no cleanup runs.
3. The observer received the capability at dispatch and **survives** (the capability
   object crossed the process boundary over a synchronous pipe before the kill).
4. The external response is produced **after** process A is dead; the surviving
   side mints the proof with the capability it holds.
5. **Process B** (fresh interpreter state): re-opens the same DB, builds a new
   `FusedTurnRuntime` whose handler is `no_redispatch` (fails the probe if called),
   attaches the exact late response via `attach_late_trusted_return`, and runs the
   turn to completion.

## Result

```
PASS | IA14-SIGKILL-001
  response='reviewer SIGKILL response'
  terminal=TurnAlreadyCompleted:turn execution refused: completed; inspect existing receipts, do not rerun
  provider_calls=[]
  meters=1
  state=completed
  assistant_ref=object_id='obs_conv_ai_f4dd16b856d5fd4ecbe43cf1' revision=1
  attempts=['metered']
```

## Invariant checklist

| requirement | result |
|---|---|
| no provider redispatch | ✓ `provider_calls=[]` (handler would have failed the probe) |
| same attempt identity | ✓ single attempt, state `metered` |
| one meter | ✓ `meters=1` across both invocations |
| one durable side effect / output | ✓ `assistant_ref` committed once |
| one ACK / terminal completion | ✓ `state=completed`; second run short-circuits (`TurnAlreadyCompleted`) |
| late response attaches after real process death | ✓ |

This probe passes — the window's headline recovery promise is real. It does not
excuse BLK-W14-001..004: the same probe's steps 4–5 are exactly what a hostile
recovery caller can fake today via the reachable issuer / plaintext nonce.

## Adjacent accepted guarantees re-confirmed

* R1–R5 exactly-once families: fresh 249/249 accepted regression includes
  `…r5_001.py`, `…r5_conflicts_001.py`, `…capability_replay.py`, `…process_loss.py`.
* Stale/foreign proof families fail closed (IA14-RACE-001 + author R2/R4/R5).
