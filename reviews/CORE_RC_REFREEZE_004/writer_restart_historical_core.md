# CORE-RC-REFREEZE-004 - Writer / restart / historical Core guarantees

The final exact-head workflow freshly executes:
- `tests/integration/test_core_headless.py`
- `tests/integration/test_core_recovery.py`
- `tests/integration/test_core_gap_fix_002_background_attempts.py`
- `tests/runtime/test_turn_execution_recovery.py`
- `tests/integration/test_v3_fused_turn_runtime.py::test_cg001_current_time_control_keeps_current_fact_visible`
- `tests/integration/test_core_scale_semantics.py`

This gate covers:
- canonical same-World writer exclusion;
- lock override cannot manufacture a second writer;
- clean stop/restart and stale-metadata recovery;
- durable work is not redispatched;
- meter/effect is not duplicated;
- FIX-001 historical cutoff;
- FIX-002 ambiguous background dispatch;
- FIX-003 ambiguous user turn;
- current-time control;
- current recovery semantics and bounded SCALE semantic equivalence.

The backup/restore Route B probe plus World/index recovery checks establish that the SQLite World remains authoritative and the index remains a rebuildable projection; no second cognition truth store is introduced by RC004.

The binding pass/fail record is the final exact-head workflow run.
