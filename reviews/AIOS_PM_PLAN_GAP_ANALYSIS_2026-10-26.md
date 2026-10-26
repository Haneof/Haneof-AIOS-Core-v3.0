# AIOS PM 任务规划查漏补缺分析（2026-10-26）

状态：`DRAFT / NOT_A_DISPATCH`（本文档是审查记录，不是新的派工表）
审查基线：`main` = `b81635c`
审查对象：上一轮 PM 提出的 T0–T5 任务链（见对话记录，未落盘为文件）

---

## 一、审查结论：规划方向正确，但有 7 处遗漏/冲突

对 T0–T5 逐条对照仓库实况核验后，发现 **3 处方向性错误 + 4 处执行缺口**。

### 方向性错误（会带偏执行）

| # | 问题 | 修正 |
|---|---|---|
| 1 | T0 核心是「轮换密钥 + 移除默认值 + 阻止提交」，但 owner 已拍板**允许密钥提交仓库**，规划未给「允许提交时 T0 怎么办」 | T0 改为**承认例外**：修好扫描盲区后，把 key 登记进 `secret_allowlist` 白名单显式放行，不轮换 |
| 2 | T2 的 A/B 双通道被当成「产品决策」抛给 owner 选，且与 owner「就一个模型测试」冲突 | 直接给**方案 B 简化版**：确定性记忆抽取轮，用当前默认主模型 `minimaxai/minimax-m3.1-flash` |
| 3 | 对「durable claim=0」只转述「提示词修不了『根本不想写』」，未给根因与方案 | 根因 = **依赖主对话模型「顺便」写记忆**（`grok_provider.py` 只在 system prompt 里强调 `commit_ai_world_claim`，但落地依赖模型自主输出 tool call）。方案 = 主对话轮结束后增加独立抽取轮，程序化落地 durable facts |

### 执行缺口（会导致卡住或漏账）

| # | 问题 | 证据 | 修正 |
|---|---|---|---|
| 4 | PM 的两份报告（进度审查 / 任务规划）**未落盘**，只存在于对话 | `find . -name "*PROGRESS_REVIEW*" -o -name "*NEXT_TASK*"` 无结果 | 本文档即补齐物证 |
| 5 | `baseline.json.pinned_sha` 停在 `6ecfb1b9`（10-21），main 已到 `b81635c`，规划未把「更新 pinned_sha + 登记 P17 授权」列为 T1 明确产出 | `governance/baseline.json` | T1 必须更新 |
| 6 | 项目任务板（todo）为空、项目留言板仅 1 条欢迎消息，「统一控制入口」实际存在两套（仓库治理看板 + 项目 todo 板），规划未识别 | `todo_list` total=0 | T1 两套都要对齐 |
| 7 | 本地是 shallow clone，登记 16 提交授权链前必须先 `unshallow` | `git rev-parse --is-shallow-repository` = true，pinned_sha 不可达 | 已触发 `git fetch --unshallow origin main` |

---

## 二、owner 的 4 项决策（本次会话拍板）

1. **治理** → 推进 T1（裁决 STOP + 登记授权链 + 统一控制入口）。
2. **允许密钥提交仓库** → 否决「移除密钥」建议。密钥写死进代码是 owner 明确授权的，登记为显式例外，不轮换、不重写 git 历史。
3. **就一个能用的模型测试** → 不做 A/B 双通道，用默认主模型 `minimaxai/minimax-m3.1-flash` 做真实端点验证。
4. **提出解决方案** → 针对 claim=0 实现「确定性记忆抽取轮」。

---

## 三、修正后的执行顺序

**T0' 安全门修复（允许密钥例外）→ T1 治理对账 → T2' 记忆抽取轮 → T4/T5 收口**

### T0' 安全门修复 —— ✅ 已完成（代码 + 单测）

方向从「阻止密钥」改为「承认例外」：

- `tools/governance/check_baseline.py`：
  - `SECRET_PATTERNS` 新增 `nvidia_nim_key`（`nvapi-` 前缀）—— 修复「不识别 NVIDIA key」盲区。
  - 授权检查从「区间内任意 trailer 放行全部路径」改为**逐提交 + 逐路径**（只有带 `Authorized-Task` trailer 且实际触碰该路径的提交才能授权该路径）。
  - `scan_secrets` 支持 `secret_allowlist` 白名单：命中即放行，把「盲区放行」变成「有据可查的显式例外」。
- `governance/baseline.json`：
  - `secret_scan_paths` 纳入 `src/`（此前只扫 governance/reviews/docs，写死在 src 的 key 永远扫不到）。
  - 新增 `secret_allowlist`，登记 `src/aios_core/runtime/resilient_handler.py` 的 `nvidia_nim_key` 为 **OWNER-AUTHORIZED 例外**，附授权人 / 授权时间 / 说明。
- 新增回归测试 `tests/audit/test_check_baseline.py`（4 passed）：
  - `nvapi-` key 在 src 无白名单 → FAIL（识别盲区已补）
  - `nvapi-` key 登记白名单 → PASS（显式例外放行）
  - 逐路径授权：区间内一个提交带 trailer，另一个提交无 trailer 改别的路径 → 未授权路径 FAIL（绕过漏洞已堵）
  - 正向：带 trailer 且触碰路径 → 正确授权

> 语义要点：把 `src/` 纳入扫描 + 白名单放行，是「有意识的授权」而非「看不见」。这样 owner 的密钥留在仓库是合法的、有留痕的；**未来任何未登记的密钥塞进 src 仍会被 CI 拦截**。

### T1 治理对账 —— 进行中（前置：unshallow）

1. 登记 `6ecfb1b9..b81635c` 区间提交授权链（SHA / Task / CI / 路径 / 对 C15 影响）。
2. 对 Issue #396 的 STOP 做正式裁决。
3. 更新 `baseline.json`（`pinned_sha` → 新基线、`task_id` 登记 P17 授权）。
4. 更新 `AIOS_v3.0_CURRENT_CHECKPOINT.md` 与 `PROJECT_MASTER_MAP.md`。
5. 对齐项目任务板（todo）。

### T2' 记忆抽取轮 —— 待 T1 后

针对 claim=0 根因实现确定性抽取轮，用 `minimaxai/minimax-m3.1-flash` 真实端点验证 `durable claim > 0` 且跨会话可复用。

### T4/T5 阶段裁决与 release verdict —— 待 T2' 证据

裁决 C15 记录、C16 放行、P16 gate（Issue #11）、P17 顺序；产出 release verdict 与 tag（仅授权后）。

---

## 四、已知遗留风险

- 本地当前处于 `fix/token-budget-and-memory-integrity` 分支，其远端已删除（`origin/... [gone]`），后续提交需切换到基于 `origin/main` 的新分支。
- T0' 改造后，真实 `main` 上 `check_baseline.py` 会因 P17 越权提交（无 trailer）而 FAIL —— 这是**正确的暴露**，需 T1 登记授权后才会转绿。
- 密钥仍是写死的 `nvapi-` key，属于 owner 明确授权的例外，但**不排除后续泄露风险**（仓库若公开则该 key 视为公开）。
