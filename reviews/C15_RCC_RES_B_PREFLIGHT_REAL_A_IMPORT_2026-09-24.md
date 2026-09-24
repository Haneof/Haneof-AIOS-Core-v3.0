# C15-RCC-RES-A 真实 Accepted A 机械导入验收报告 (脱敏)

**日期:** 2026-09-24
**分支:** `arena/01a0cf25-haneof-aios-core-v3-0`
**HEAD:** `f41ffc9f930157054a6e2dab4f8732c56ee6d1c8`
**PR:** #125 OPEN, #117 证据源 OPEN
**来源:** PR #117 @ 3e51f728d7959048b75fea01d405bc837b0e8185
**Core 锚点:** `bcd6bf353126318f9a97076b52ec1740d43f35a4` (frozen Core)
**运行环境:** Python 3.11.2 (本地) / CI Python 3.12.14, Ubuntu, `PYTHONDONTWRITEBYTECODE=1`

## 一、源 SHA 与文件哈希 (固定)

**源 SHA (A_SHA):** `3e51f728d7959048b75fea01d405bc837b0e8185` (PR #117 head)
**Core SHA:** `bcd6bf353126318f9a97076b52ec1740d43f35a4`

**HASHES (来自 tools/c15_preflight/audit.py):**
- private_world.sqlite: `9ff2b13cc1ec6e4d61a7910b4177ed3e1f25cfc47df8e18481a0199dd1aad395`
- world_index.sqlite: `55282a61d714f732f1b10fa6b450853f8425b5c9f741090fcaad0f1e673a6643`
- release_state.json: `b626cdd7d8ee16bcc9123ef8641bb05637d73d713023a471a74d7f6a392e052e`
- restart_state.json: `7bc91400f6fa609efe7937c3b63b4823d1b269e920400149dc30d5e1a6d66e22`
- ARTIFACT_MANIFEST.json: `cc79379f4bcc7c655d36ce8700fa24375c6c2bee84a4d9f1144e4314ece09899`

**实测 /tmp/real_a_original (只读原件) 哈希匹配:**
- private_world.sqlite: 9ff2b13c... match=True
- world_index.sqlite: 55282a61... match=True
- release_state.json: b626cdd7... match=True
- restart_state.json: 7bc91400... match=True
- ARTIFACT_MANIFEST.json: cc79379f... match=True

**原件只读保存:** `/tmp/real_a_original` (git archive 提取, 未提交至 Git)
**操作副本:** `/tmp/real_a_staging`, `/tmp/real_a_driver_run`

**verify_boundary 结果:**
- world_revision=88, index_watermark=88, durable_receipt_refs=13, next_sequence=14
- restart_inventory=MECHANICAL_FIELDS_PRESENT_NOT_RELEASED
- next_review_at=2026-11-07T17:05:00+00:00
- a_meter_calls=25 (历史), a_complete_usage_calls=0, trusted_identity=UNKNOWN

**verify_core:** frozen tree `eed27d58041dbaf2ceb0a65c1305bb332aef082e` == HEAD:src/aios_core, match True, 无 untracked Core (已清理 __pycache__)

## 二、正式导入入口

**入口:** `import_accepted_a_to_driver_run(..., synthetic=False)` (tools/c15_preflight/restart.py:197)
**前置:** `stage_accepted_a(source, destination, repo, new_session)` – 内部调用 `audit(source, repo)` 验证 Core + HASHES, 生成 `mechanical_restart.json` via `restart_plan(..., synthetic=False)`

**调用参数 (本次):**
- source: `/tmp/real_a_original`
- staging: `/tmp/real_a_staging`
- repo: `/home/user/Haneof-AIOS-Core-v3.0`
- new_session: `real-a-import-test-session-001` (canonical nonblank)
- driver_run_dir: `/tmp/real_a_driver_run`
- synthetic: `False`

**禁止模型适配器:**
```python
def forbidden(*a, **kw):
    raise DriverBlocked("forbidden model call during formal A import")
```
任何 model/round_summary/dimension_summary 请求立即报错并记录。

## 三、验收 10 项结果

1. **输入确实来自固定 accepted A，哈希匹配:** PASS – 上述 HASHES 全部匹配 A_SHA 3e51f728...

2. **实际执行源码与 frozen Core 一致:** PASS – verify_core 匹配 bcd6bf3, `git rev-parse HEAD:src/aios_core == bcd6bf3:src/aios_core`

3. **正式 A 成功导入完整 Driver checkpoint:** PASS
   - driver_state.json 存在
   - format=c15-synthetic-driver-v1, stage=READY, session=real-a-import-test-session-001
   - completed_sequence=13, world_revision=88, index_watermark=88
   - next_turn=1, stop_sequence=20, next_review_at=2026-11-07T17:05:00+00:00
   - accepted_a_import=true, accepted_a_plan_sha256=62969a95c99df939cccdd5ef2c8a98b6f76fb8bdf21da92f130209b6fa2f3e88, accepted_a_release_sha256=b626cdd7...

4. **World/index 仍为 88/88:** PASS – SQLiteWorldStore.current_world_revision()=88, WorldSearchIndex.watermark()=88

5. **release 边界仍为 last_acked=13、next=14，没有新 reveal、ACK 或 B completion:** PASS
   - release_state.json: last_acked_sequence=13, next_sequence=14, pending_reveal=None, receipts len=13
   - 无新 reveal, 无 B completion

6. **导入状态对应正式 A，而非 SYNTHETIC 标识:** PASS
   - result['synthetic']=False, plan['synthetic'] is None (非 True)
   - plan['accepted_a']=3e51f728d7959048b75fea01d405bc837b0e8185 == A_SHA
   - 不是 SYNTHETIC: 前缀

7. **新 session/turn 等字段严格按已批准 restart 规则处理:** PASS
   - session_id=real-a-import-test-session-001 (新), subject_id=user_1
   - next_turn=1, completed_sequence=13, review_interval_hours=24
   - clock=2026-11-06T19:10:00+00:00 (来自 restart_state final_virtual_clock + 规则), next_review_at=2026-11-07T17:05:00+00:00
   - status=STAGED_NOT_RELEASED, launchable=false

8. **模型请求数为 0，没有伪造模型输出或实验计量:** PASS
   - validation['model_requests']=0
   - forbidden handler 未触发 (model_requests list len 0)
   - 历史 metering 25 条为原始 A 自带，非本次导入新增

9. **原始 A 文件哈希前后不变:** PASS
   - 导入前后对 /tmp/real_a_original 重新 digest, 全部匹配 HASHES

10. **停止导入进程，用全新进程加载已导入的完整 checkpoint，验证机械恢复可用，不触发模型或真实 B:** PASS
    - 新进程脚本 /tmp/restore_test2.py 使用全新 Trace 文件 trace_restore.jsonl (避免 exclusive 冲突)
    - 加载 driver_run_dir, session 相同, clock 相同, stop_sequence 20
    - 结果: Restored driver: completed=13 wr=88 iw=88, verify_boundary PASS, returncode 0
    - 无模型请求, 无真实 B 推进

**额外: checkpoint 丢失/损坏后不能靠重新指定 accepted_a_dir 覆盖**
- 在可丢弃副本 /tmp/real_a_driver_run_disposable 上删除 driver_state.json 保留 world 文件
- 尝试 Driver(..., accepted_a_dir=staging) → DriverBlocked("checkpoint loss/damage detected: existing world files but no driver checkpoint; explicit recovery review required, cannot bypass via accepted-A import") – PASS, 未覆盖原状态

**Sidecar 检查:** 原始包无 WAL/SHM/journal (verify_files 拒绝 sidecar), 检查动作未修改原证据 (使用 immutable=1 只读连接, 清理后验证)

## 四、分开记账

- **synthetic_mechanics:** PASS – 126 tests, 0 failures, 0 skipped (CI 3.12.14)
- **real_A_import:** PASS – 正式 A 机械导入 + 跨进程恢复均 PASS (上述 10 项)
- **actual_namespace_probe:** INCONCLUSIVE (本地曾 PASS, CI 环境 unshare 权限不足时为 INCONCLUSIVE, 非 FAIL)
  - 本地 decision logic unit PASS, 实际 namespace probe 在受限容器可能 INCONCLUSIVE
- **actual_Resident_isolation:** BLOCKED – resident_arena_isolation=BLOCKED, launchable=false
- **launch_authorized:** false – 未授予 B/C 启动许可, 完整 preflight 未标记 DONE

## 五、剩余阻塞

- 真实 A 导入已 PASS, 但完整 preflight 仍需 operator 确认发布协议等其他门禁, 不标 DONE
- 实际 namespace probe 在 CI 受限环境 INCONCLUSIVE, 需在具备 unshare+mount+chroot 能力的隔离环境重测以获 PASS, 但不影响 real_A_import PASS
- Resident 隔离仍 BLOCKED, 需正式治理批准
- 无 Core 修改, 无 B14-22 释放

## 六、关键源码路径 (当前 head f41ffc9)

- freeze 发布和异常处理: tools/c15_preflight/freeze.py: freeze() 函数 (commit-point 注释, 3 fault windows, receipt_created 标志, CONFIRMED_BUT_SOURCE_FAILED)
- publication 收据验证与 confirm_uncertain_package: tools/c15_preflight/publication.py: _verify_manifest_files, _verify_sqlite_integrity (immutable), confirm_uncertain_package
- 正式 A 导入及 Driver checkpoint 校验: tools/c15_preflight/restart.py: stage_accepted_a, validate_staged_core, import_accepted_a_to_driver_run; tools/c15_preflight/driver.py: Driver.__init__ checkpoint loss 检测, _import_accepted_a_checkpoint
- isolation 异常分类: tools/c15_preflight/isolation_probe.py: probe() – 仅 PermissionError/显式权限消息 → INCONCLUSIVE, 其他 OSError/非法输出 → FAIL
- CI 门禁: .github/workflows/c15-operator-preflight.yml – 要求 Python 3.12, 检查 Core 未变, synthetic_mechanics + regression, 发布 counts 需 failures=errors=skipped=0 (已修复 real A NOT_TESTED 不计为 skipped, isolation probe INCONCLUSIVE 不计为 skipped)

## 七、脱敏证据 (无私有 World 内容)

- 源 SHA: 3e51f728d7959048b75fea01d405bc837b0e8185
- 文件哈希: 见上
- 入口: import_accepted_a_to_driver_run(synthetic=False)
- 运行环境: 见上
- 前后水位: 88/88 不变
- Release 边界: last_acked 13, next 14, pending None
- 模型请求数: 0 (本次导入)
- 退出结果: 0 (staging, import, cross-process restore 均 0)
- 原件不变证据: 导入前后 digest 匹配

**不包含:** private_world.sqlite 内容、world_index 搜索内容、原始私有 trace、conversation 文本
