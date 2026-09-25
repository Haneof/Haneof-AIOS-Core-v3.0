# C15-RCC-RES-B-PREFLIGHT-002 — Mechanical Check Results

All checks were run against disposable copies of the freeze artifacts. The canonical #205 evidence was read but not modified.

## 1. Frozen Core tree identity

**PASS.** `src/aios_core` tree hash = `fe77f8a0706acfaf369041d0882b6d0e6de39f22` at:
- frozen software `773876f9...`
- #205 head `d17ae972...`
- publication base `4d9f0471...`
- current main HEAD `811ae85...`

Command:
```
git ls-tree <commit> src/aios_core
```

## 2. Accepted A freeze digests

**PASS.** All three recomputed SHA-256 values match the acceptance receipt:

| File | Expected | Recomputed |
| --- | --- | --- |
| private_world.sqlite | `626c6bb3...01f6aa` | `626c6bb3...01f6aa` |
| world_index.sqlite | `ecfabf4...1e5f1` | `ecfabf4...1e5f1` |
| release_state.json | `eada20a...391c8` | `eada20a...391c8` |

## 3. World SQLite quick_check

**PASS.** `PRAGMA quick_check;` → `ok`.

## 4. World revision = 98

**PASS.** `SELECT value FROM world_meta WHERE key='world_revision';` → `98`. Last world_commit rowid at revision 98 is the C14 fixture ingest for cursor 13 (sequence 13).

## 5. Index quick_check

**PASS.** `PRAGMA quick_check;` → `ok`.

## 6. Index watermark = 98

**PASS.** `SELECT value FROM search_meta WHERE key='search_watermark_world_revision';` → `98`.

## 7. Index lag = 0

**PASS.** Confirmed via `aios-core-headless recovery-status` on a disposable copy: `index_lag: 0`.

## 8. Release-state fields

**PASS.** All values match the expected Phase-A terminal boundary:

- active_phase = "A"
- last_acked_sequence = 13
- next_sequence = 14
- pending_reveal = null
- last_acked_event_id = "c15rcc-013"
- 13 contiguous receipts for sequences 1..13
- receipt fixture_sha256 is consistent `sha256:7ccb309d...`
- final receipt (seq 13) is bound to world revision 98

## 9. No cursor 14 material consumed

**PASS.** The preflight did NOT call `reveal` for any phase. It called ONLY `init --phase B` on disposable copies to verify the state transition is accepted. The init command validates phase/receipt-chain integrity and transitions `active_phase` from A to B; it does NOT read or emit the cursor-14 event payload (the reveal subcommand does that — and it was not called). Therefore cursor 14's resident-visible payload has not been inspected or revealed in any form.

Verification:

- `receipts` array in release_state.json contains exactly 13 entries (sequences 1..13).
- No `pending_reveal` is set before init.
- After `init --phase B`, `active_phase` transitions to `"B"`, `pending_reveal` remains `null`, `next_sequence` remains 14, and `receipts` is unchanged (init does not add a receipt).
- No `release_operator.py reveal` call was issued in this preflight (grep of operator logs confirms).

## 10. Legal Phase-B init accepts exact boundary

**PASS.** On a fresh disposable copy of the exact A-freeze release_state.json:

```
$ PYTHONPATH=src python3 reviews/internal_habitation/c15-rcc/v1/release/release_operator.py init --phase B --state <copy>/release_state.json
{"fixture_sha256":"sha256:7ccb309d...","next_sequence":14,"phase":"B","status":"initialized"}
exit=0
```

(Confirmed both on host filesystem AND inside the sandbox at `/work/release_state.json`.)

## 11. Malformed/skipped/dirty boundary fails closed

**PASS.** Three malformed boundary states were constructed from a disposable copy:

| Test case | Mutation | Result |
| --- | --- | --- |
| skip_seq12 | last_acked_sequence=12, next_sequence=13, last_acked_event_id=c15rcc-012 (simulates missing receipt) | `release-operator-error: release receipt chain mismatch` exit=2 |
| dirty_pending | pending_reveal={sequence:14} (simulates unresolved reveal) | `release-operator-error: pending reveal event mismatch` exit=2 |
| seq14_already | active_phase=B, last_acked_sequence=14, next_sequence=15 (simulates already-started B) | `release-operator-error: release receipt chain mismatch` exit=2 |
| double_init | init already-initialized state | `release-operator-error: Phase B initialization requires active Phase A handoff state` exit=2 |

All fail closed with non-zero exit; no state is written.

## 12. Same-World durable restart

**PASS.** Opening the copied World with `aios-core-headless recovery-status`:

```json
{
  "index_lag": 0,
  "index_status": "ready",
  "index_watermark": 98,
  "recovery_disposition": "AUTO_RECOVERABLE",
  "schema_version": 1,
  "status": "recovery_status",
  "world_quick_check": ["ok"],
  "world_revision": 98
}
```

Additionally `aios-core-headless rebuild-index` from the World alone (without the supplied index) successfully reconstructs the index:

```json
{
  "index_watermark": 98,
  "indexed_rows": 245,
  "recovery_disposition": "REBUILD_FROM_WORLD",
  "status": "index_rebuilt",
  "world_revision": 98
}
```

This proves the World is self-contained truth; the index is a rebuildable projection, and same-World restart across phases is a supported operation (consistent with CORE-RECOVERY-001 acceptance).

## 13. Resident isolation (no sealed material in sandbox)

**PASS.** See isolation/isolation_report.md for full results. Summary: 11 sealed-path categories are absent from the sandbox, privilege drop to nobody works, /proc/1/root is unreadable, mount() is denied, Core code imports cleanly.

## 14. Mailbox/request bridge transport-only (no semantic default)

**PASS by design and inspection.** `harness/mailbox_bridge.py`:

- Sends RuntimeSnapshot + 8-field projection into the sandbox inbox as JSON.
- Blocks for the Resident's reply; validates only that the reply is a JSON object with an `action` field.
- NO keyword matching, NO default answer, NO suggestion, NO retry with hints. If the reply is structurally invalid, the same snapshot/projection is re-presented (Resident repairs its own output in a fresh round).
- Operator-side archive preserves the raw reply for evidence; it is not injected back into the Resident context across rounds.
- Does not expose A mailbox history; the first B round starts with empty B-session capability history.

This satisfies preflight §7: "Infrastructure may transport bytes and execute Resident-selected capabilities. It may not decide semantics."

## 15. B freeze/evidence procedure defined BEFORE B runs

**PASS.** See procedure/final_freeze_procedure.md. It enumerates the exact commands and hashes to capture at B completion; it is a document in this preflight PR, authored before any B run can start.

## 16. Cursor 14 not revealed

**VERIFIED.** `grep -r 'reveal' checks/ harness/ procedure/` returns no invocation of the `reveal` subcommand in any preflight-executed code. The startup procedure (b_startup_procedure.md) reserves the first `reveal` for the B release task, not for preflight.
