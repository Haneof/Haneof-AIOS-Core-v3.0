# C15-RCC-RES-A-RERUN-004-CORRECTIVE-001 Failure Adjudication

## Status

```text
Run ID: c15-rcc-res-a-rerun-004-corrective-001
Task: C15-RCC-RES-A-RERUN-004-CORRECTIVE-001
Role: Real Resident AI — Fresh Corrective Resident A
Disposition: BLOCKED
Cause: Post-reveal harness defect in runner.py serialization of CapabilityResult (Rule 14 enforced)
Mid-run harness patch: REFUSED (strict compliance with Rule 14 & Rule 24)
```

---

## 1. Summary of Execution

This corrective run was initialized with completely fresh state per prompt governance:
- Frozen RC: `f20f2edfa7af00d0286493fd15196ca9503bc315`
  - Core tree: `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
  - Tests tree: `7e33b5ef8432370234965d3ccd61248c703c4019`
- Fresh run directory: `reviews/internal_habitation/c15-rcc/v1/resident/runs/c15-rcc-res-a-rerun-004-corrective-001`
- Fresh World database: `world.db`
- Fresh release state: `release-state.json`
- Monotonic, hash-chained exchange ledger: `exchange_ledger.jsonl`
- Pre-run harness freeze verified: 14/14 synthetic plumbing tests passed before cursor 1 reveal.

---

## 2. Cursor 1 Chronology & Exchange Evidence

1. **Cursor 1 Reveal**:
   - Event `c15rcc-001` revealed (USER conversation utterance regarding Atlas staging).
   - Saved to `events/cursor_01_event.json`.
2. **Canonical Ingest**:
   - Ingested via `canonical_conversation_ingest.py`.
   - Ingest ref: `obs_conv_user_14e34586d49f26417bc0528f@1`.
   - Saved to `receipts/cursor_01_ingest_stdout.json`.
3. **Durable ACK**:
   - Acknowledged via `release_operator.py ack`.
   - Saved to `receipts/cursor_01_ack_stdout.json`.
   - `release-state.json` advanced to `last_acked_sequence: 1`, `next_sequence: 2`.
4. **Attention Watch Evaluation**:
   - Evaluated `obs_conv_user_14e34586d49f26417bc0528f@1` natively via `runtime.attention_watches.evaluate_observation`.
5. **Time Advance**:
   - Clock moved to `2026-11-02T09:05:00-08:00`.
   - Periodic review at time advance:
     - Decision request `req-0001-model_directive-6510beb0`: published (ledger seq 1).
     - Decision response: published (ledger seq 2, terminal silence).
     - Decision consumed: ledger seq 3.
     - Background attempt `bgattempt_530d45983bf8dec141749a3bd764115d`: `metered`.
6. **User Turn Execution**:
   - User turn 1 dispatched (`turn_index: 1`).
   - Round 0:
     - Decision request `req-0002-model_directive-3c99d45b`: published (ledger seq 4).
     - Decision response: published (ledger seq 5, calling `record_communication_experience`, `propose_cognitive_policy`, `propose_goal`).
     - Decision consumed: ledger seq 6.
     - Background attempt `bgattempt_90a09ab7c3ff37c43c2dc2a9a588b5e7`: `metered`.
     - Core executed all 3 capabilities with zero side-effect regression.
   - Round 1:
     - Core constructed `RuntimeSnapshot` with `capability_history = (CapabilityResult(...), ...)`.
     - In `runner.py` line 266 (`_handle_model_directive`), serialization accessed `c.arguments` on `CapabilityResult`.
     - `CapabilityResult` has attributes `(name, ok, data, error_code, error_message, call_id)` but no `arguments`.
     - Raised `AttributeError: 'CapabilityResult' object has no attribute 'arguments'`.
     - Failure occurred before `publish_request` for round 1.
     - Core recorded attempt `bgattempt_2a0af91813753413f4b1ebf8b210c27a` as `in_doubt` with failure reason `AttributeError`.

---

## 3. Strict Compliance with Binding Rules 14 and 24

The prompt mandates:

> **十四、cursor 1 开始后禁止修改 harness**  
> 这是 binding rule。  
> 一旦真实 cursor 1 reveal：  
> 以下文件禁止再改：  
> - runner  
> - bridge  
> - exchange protocol  
> - ledger implementation  
> - synthetic tests  
> 如果发现 harness bug：  
> 立即：  
> "BLOCKED"  
> 保留现场。  
> 不要像旧 A-004 那样边跑边修 runner 再继续。

> **二十四、如果出问题**  
> 任一 binding failure：  
> 输出：  
> "BLOCKED"  
> 并保留：  
> - current World  
> - index  
> - release-state  
> - exchange ledger  
> - failed request/response files  
> - Core attempt state  
> - harness exact SHA  
> - failure evidence  
> 不要为了完成任务而继续。

In the historical run (#273), mid-run harness patching was committed after cursor 1 reveal, which was adjudicated as an acceptance-failing blocker in Independent Acceptance PR #275.

In this corrective run:
- The harness was frozen with exact SHA-256 before cursor 1 reveal.
- When `AttributeError` occurred during round 1 serialization, the agent strictly refused to modify `runner.py`.
- The run immediately halted at `BLOCKED`.
- All contemporaneous files, ledger sequences, SQLite tables, and raw error states are preserved untouched.

---

## 4. Retained Evidence

| Artifact | Description |
|---|---|
| `world.db` | Exact SQLite database preserving world commits, revision 1, object revisions, and turn attempts |
| `release-state.json` | Exact release state confirming cursor 1 acked, next sequence 2, pending reveal null |
| `exchange_ledger.jsonl` | 6 verifiable, hash-chained records proving exact chronology of requests 1 and 2 |
| `decision_requests/` | Both raw request files (`req-0001`, `req-0002`) |
| `decision_responses/` | Both raw response files (`req-0001`, `req-0002`) |
| `receipts/` | Ingest and ACK stdout JSON for cursor 1 |
| `exports/` | JSONL dumps of `background_model_attempts`, `turn_executions`, `metering_records`, and `world_object_index` |
| `harness/` | Frozen harness files with unchanged SHA-256 matching `harness/harness_freeze.json` |
