# C14-RES-A-001 — run progress ledger (append-only)

Run id: `resident-a-restart-20260921`
Started from main: `87e52bceea4ee94b823200388a4f79b1b94eb1f3` (verified live main at window start)
Session branch: `arena/01a0c473-haneof-aios-core-v3-0`
Resident model (as declared): `GPT-5.6 Sol`; platform provider/session id: `unknown/not exposed`

## Stage table

| Stage | Scope | Status | Evidence |
|---|---|---|---|
| S0 | Recon, READY proof, plan, ledger, bridge, bridge self-test | DONE | `PLAN.md`, `SESSION.md`, `bridge/resident_checkpoint.py` |
| S1 | Fresh World, Phase A init, cursor 1 end-to-end | DONE | `receipts/{reveal,ingest,ack}/cursor-001.json`, `SEMANTIC_TRACE.md` |
| S2..S4 | Cursor 2..4, one stage each | DONE | `receipts/{reveal,ingest,ack}/cursor-00{2,3,4}.json`, `SEMANTIC_TRACE.md` |
| S5 | Cursor 5 end-to-end, incl. all due work after the 10-01→10-05 jump | DONE | `receipts/*/cursor-005.json`, `receipts/process-due-20261005T140600Z.json`, `checkpoints/{snapshots,decisions,results}/*` |
| S6..S14 | Cursor 6..14, one stage each | DONE | `receipts/{reveal,ingest,ack}/cursor-0{06..14}.json`, `receipts/process-due-*.json`, `SEMANTIC_TRACE.md` |
| S15 | Cursor 15 end-to-end, incl. due work after the 10-09/10-11 closed windows | DONE | `receipts/*/cursor-015.json`, `receipts/process-due-20261011T124800Z.json`, `SEMANTIC_TRACE.md` |
| S16..S24 | Cursor 16..24, one stage each | NOT_STARTED | — |
| S25 | Handoff freeze | NOT_STARTED | — |

### S0 notes

- READY proof: `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md` row 17 `C14-RES-A-001 = READY`
  (dependency `C14-RES-FIX-003 = DONE`); live `origin/main` re-fetched at window start.
- Forbidden material was not opened (fixture / manifest / evaluator / FIX completion evidence /
  PM reviews / validation protocol). `FIXTURE_SHA256` above is the digest published in the
  Resident-visible release contract, not read from the sealed fixture.
- Bridge self-test (throwaway world under `/tmp`, no fixture bytes, not evidence):
  - empty-world `init-world` + `process-due` → clean no-op;
  - synthetic Observation in a `/tmp` world → day Summary paused for Resident text → committed
    `sum_...@1` → C14 `cognitive_derivation` Wake scheduled (REALITY lineage, leaf = the synthetic
    Observation) → Wake dispatched → paused for Resident decision → `silence` → Wake COMPLETED
    (`termination_reason=silence`);
  - Periodic Review mechanically became due (3 anchors) → separate checkpoint unit → completed.
  - Confirms: pause/resume, exact-snapshot persistence, capability execution path, wake
    completion, review path and unit separation all work before any real cursor is released.
- Deliberately NOT built: HTTP server, GitHub polling, daemon, RPC, multi-stage bridge.

## Cursor ledger

| Cursor | Event id | Occurred at | Ingest ref | Acked | Due work processed at that time | World rev | Notes |
|---:|---|---|---|---|---|---|---|
| 1 | `c14resv2-001` | 2026-10-01T07:12:00-07:00 | `obs_c14_fixture_b32d3cded992194438f114a9@1` | yes (`next=2`) | Periodic Review due → Resident inspected anchor → **silence**; no Summary window closed yet; no C14 wake | 4 | dim:sleep wearable fact; 0 Claims (silence is valid) |
| 2 | `c14resv2-002` | 2026-10-01T07:48:00-07:00 | `obs_c14_fixture_3195efa3abad26d259380073@1` | yes (`next=3`) | none due (day window open; review not due until 2026-10-02T14:13Z) | 5 | dim:schedule calendar fact |
| 3 | `c14resv2-003` | 2026-10-01T10:22:00-07:00 | `obs_c14_fixture_7422eaba53dc07eb87572e67@1` | yes (`next=4`) | none due | 6 | dim:device_activity focus-mode fact |
| 4 | `c14resv2-004` | 2026-10-01T10:28:00-07:00 | `obs_c14_fixture_660bfde404b5e63e3c52db43@1` | yes (`next=5`) | none due | 7 | dim:work_outcome memo v1 submitted |
| 5 | `c14resv2-005` | 2026-10-05T07:06:00-07:00 | `obs_c14_fixture_27ab6246ef0865debe1b49af@1` | yes (`next=6`) | 16 Summaries (4 dims × day/week/month/quarter) authored by me; C14 bundle `wake_bundle_b730ca1a7fefcee2ec36e955` (16 members, REALITY) → inspect round → **silence**; Periodic Review `wake_review_6504931e301a63a3e7f5ef9e` → inspect anchors → **silence** | 46 | dim:sleep wearable fact; 0 Claims (silence is valid); pending_wakes 0, index_lag 0 |
| 6 | `c14resv2-006` | 2026-10-05T08:18:00-07:00 | `obs_c14_fixture_8a41a59c20d2aac5789bf0f1@1` | yes (`next=7`) | none due (day/week windows open; C14 reconcile idempotent; review not due) | 47 | dim:schedule 计划被插入会议打断、写作时间重排 |
| 7 | `c14resv2-007` | 2026-10-05T15:12:00-07:00 | `obs_c14_fixture_35f8ca5c3abafa4ba5c8650a@1` | yes (`next=8`) | none due（10-05 日窗未闭合；C14 幂等；review 未到期） | 48 | dim:work_outcome 定价说明 65%，余量移至次日上午 |
| 8 | `c14resv2-008` | 2026-10-05T18:35:00-07:00 | `obs_c14_fixture_0ca259ffc10ff4a9218561d0@1` | yes (`next=9`) | 3 day Summaries (schedule/sleep/work_outcome) authored; C14 bundle `wake_bundle_cf33cc336ac0040cebfee9d9` (3 REALITY members) → read_ai_world(0) → **silence**; review not invoked | 58 | 首个 USER 类事件（会话）；0 Claims（sleep n=2 未达 ≥3 门槛） |
| 9 | `c14resv2-009` | 2026-10-08T06:52:00-07:00 | `obs_c14_fixture_056dddd04850d813437e8532@1` | yes (`next=10`) | 1 Summary（conversation 10-06）由我撰写；C14 `wake_400ea8877e999e1c3902995d` → **silence**；Periodic Review `wake_review_e1002d5562f2ae6d74007e1e` → anchors 复盘 → **silence** | 66 | 短睡 5h48m/60 使睡眠样本发散；0 Claims（拒绝过早“稳定模式”） |
| 10 | `c14resv2-010` | 2026-10-08T08:08:00-07:00 | `obs_c14_fixture_6e081d5c46196e1781165d5c@1` | yes (`next=11`) | none due（日窗未闭合；C14 幂等；review 刚跑过） | 67 | dim:schedule 短睡次日的 08:15–10:35 设计评审稿块 |
| 11 | `c14resv2-011` | 2026-10-08T10:38:00-07:00 | `obs_c14_fixture_522a6cbeb84ced83b62def58@1` | yes (`next=12`) | none due | 68 | 第二次晨间专注块记录（2 次解锁/29 条静音）；bridge 审计日志降噪（stdout 摘要，文件保留全量） |
| 12 | `c14resv2-012` | 2026-10-08T10:43:00-07:00 | `obs_c14_fixture_96ba14d7f113e478b8a8bae8@1` | yes (`next=13`) | none due；bridge stdout 降噪 bug 修复后重跑 | 69 | 第二次按时交付（设计评审稿 10:31 / 计划止 10:35） |
| 13 | `c14resv2-013` | 2026-10-08T18:10:00-07:00 | `obs_c14_fixture_f3557413048807b17b9487bc@1` | yes (`next=14`) | 4 条 10-08 日摘要由我撰写；C14 bundle → 跨日 search_timeline 取证 → **commit_claim** `clm_79df61916b8bb4c10cb3faa3`（9 REALITY refs, hypothesis 0.5）→ silence | 82 | **首条 Claim**：写作块交付与日程保护相关（3 次观察的结构）；1 Claim |
| 14 | `c14resv2-014` | 2026-10-11T05:43:00-07:00 | `obs_c14_fixture_36306372faac84bd3a098bd6@1` | yes (`next=15`) | 2 摘要（10-09 conversation + work_outcome(AI 认知记录)）；C14 bundle → **revise_claim rev2**（证据 10 条，含 10-09 会话；stale: 10-09 摘要）；Periodic Review → **silence** | 94 | 睡眠第 4 样本 ~6h42m；Claim 首次修订（疲劳—交付区分） |
| 15 | `c14resv2-015` | 2026-10-11T05:48:00-07:00 | `obs_c14_fixture_979fd7bab5a31f3239b61e0b@1` | yes (`next=16`) | 1 摘要（10-09 work_outcome 因 S14 的 Claim 修订被重算 → rev3，文本沿用我 S14 亲笔）；C14 `wake_7a5808cbfef6321783bf0cb3`（单成员 = 该摘要 rev3，MIXED/has_ai）→ read_ai_world + inspect + 2×search_timeline → **silence** | 99 | dim:schedule 10-11 出行（06:25 航班、05:52 出门）；摘要 rev3 括注仍为 rev1 时期措辞（导航锚点，不作结论） |

## Blockers / contamination

- none
