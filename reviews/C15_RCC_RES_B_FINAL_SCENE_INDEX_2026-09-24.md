# C15 RCC RES B - 最终现场索引 (PM阶段裁决 2026-09-24)

PR125 暂停扩展，保全现场，转为平台边界阻塞。不再增加功能、模型API适配或一般性测试。不运行真实A/B/C，不手动dispatch真实A工作流。不合并、不关闭PR，不删除历史证据。

## 1. 最终完整head SHA

- **最终头**: `7cd0a12e6677c5ec1565b1c20d4a2e866c70c449` (short 7cd0a12)
  - 内容: 在 f886cd4 基础上最终禁用 real-a-import-312 工作流 (job `if: false`)，明确 workflow_dispatch 不是私有环境也不是新授权，当前禁止继续运行。历史运行记录保留。
  - 变更范围: 仅 `.github/workflows/real-a-import-312.yml` 1文件，9行插入5行删除，无源码变更，无真实A运行。

- **已测源码头**: `4859d2e6141649fcf0e6715e69dff0635c9734dc` (short 4859d2e)
  - 内容: 阻断自动获取私有A后的头，仅 `workflow_dispatch`，`if: github.event_name == 'workflow_dispatch'`，已测 c15 35926209461 SUCCESS 131+146 Python3.12.14 exact-head 4859d2e, p16 35926209477 SUCCESS, real-a 未触发 (符合预期)。
  - 与最终头区别: 4859d2e 仍允许手动 dispatch 获取私有A，最终头 7cd0a12 进一步禁用 `if: false`，彻底禁止任何触发。

- **参考头**: `5b5e2306c39b5b09b260de787403567a31d0efbd` (short 5b5e230)
  - 内容: 真实A导入成功回执 + 缺陷修正 (publication非变异、freeze收据验证、broker结构边界) + 架构纠正 (真实Resident为新Arena窗口AI本人，暂停外部LLM API)
  - 证据: c15 35925311923 SUCCESS, p16 35925311892 SUCCESS, real-a 35925311828 SUCCESS (operator 5b5e230, branch 3e51f728, fixed_A 3e51f728, 88/88, 13→14, model0, cross-process PASS)

- **文档增量头**: `f886cd4446fa63b6120d6e833cad5857ba620f2c` (short f886cd4)
  - 内容: 仅增加3个markdown (A/B/C)，无源码变更，相对 4859d2e。CI: c15/p16 曾触发但 real-a 未触发。不把旧CI冒称最终头CI。

**明确**: 最终头 7cd0a12 仅文档+工作流禁用变更，已测源码为 4859d2e (及参考 5b5e230)。旧CI (如 35925861876 5f78d4b, 35925311828 5b5e230) 不冒称为最终头CI。

## 2. 任务记录

**任务状态**: “已有未合并工程成果，暂停于Arena实际访问边界阻塞”

- 不写DONE，不写尚未施工。
- 已有工程成果: 真实A Python3.12机械导入成功 (88/88, 13→14, model0, cross-process PASS)、缺陷修正 (publication非变异、freeze收据验证非仅exists、broker结构边界非黑名单)、架构纠正 (真实Resident为新Arena窗口AI本人，暂停外部API)、合成机械测试 131+146 PASS、隔离探针 INCONCLUSIVE、真实Resident隔离 BLOCKED、launch_authorized false、PR125 OPEN。
- 暂停原因: 当前已测的仓库连接Arena窗口不满足隔离；其他模式支持情况未核实。
- 分支报告更新: 本分支 `arena/01a0cf25` 已更新上述文档与阻断措施；main任务板尚未同步 (按指令明确)。

## 3. 真实A工作流当前禁止继续运行

- **当前配置** (7cd0a12):
```yaml
on:
  workflow_dispatch:
jobs:
  real-a-312:
    if: false  # FINAL DISABLED: prohibited, workflow_dispatch NOT private env, NOT authorization
```

- **禁止说明**: workflow_dispatch 不是私有环境，也不是新的授权。即使手动触发，runner 仍在 public repo 的 public CI 环境中，日志公开可见，任何有写权限者可触发获取私有A，不符合“私有A不进公开CI”限制。

- **是否仍可能误触发**: 阻断前 (pull_request) 可被普通PR自动触发；阻断中 (仅 workflow_dispatch + if: event_name == workflow_dispatch) 仍可被手动触发；最终禁用 (if: false) 彻底禁止任何触发，包括手动dispatch。

- **最小禁用措施**: 已实施 `if: false`，不实际触发验证，保留历史运行记录 (35924742929, 35924990859, 35925311828, 35925861876)。

- **历史运行保留**: 未删除历史证据或运行记录。

## 4. 平台结论限定

- **当前已测的仓库连接Arena窗口不满足隔离**: 实测 Arena Agent Mode 每个会话固定分支，工作区根含完整仓库，bash/read_file/git/gh 全量可用，`isolation_probe` unshare/mount/chroot 需特权失败返回 INCONCLUSIVE，文件/仓库/历史证据/未来材料/工具/网络均未被阻止，仅提示词自律。
- **其他模式支持情况未核实**: 例如 Arena 是否有其他隔离模式 (如独立容器、无仓库连接、仅安全包可见的窗口类型) 未在本文档核实，不宣称平台所有模式必然不可用。
- **不宣称平台所有模式必然不可用**。

## 5. 公开A分支访问范围与实验影响 (仅记录已确认)

- **公开A分支**: `arena/01a0cca8-haneof-aios-core-v3-0` @ `3e51f728d7959048b75fea01d405bc837b0e8185`，位于 public 仓库 `Haneof/Haneof-AIOS-Core-v3.0` 的 git 历史中。
- **已确认访问范围**: 任何可执行 `git fetch origin refs/heads/arena/01a0cca8...` 或 `git ls-remote` 的人 (包括 public repo 克隆者) 可获取该分支内容，因仓库 public，git 层面已公开可访问。
- **实验影响**: 该分支包含 `reviews/internal_habitation/c15-rcc/v1/runs/resident-a-final-rerun-20260923/` 的 World/index/release/restart 等材料。CI 工作流曾通过 `git archive ... | tar -x` 获取并验证 HASHES，仅输出脱敏收据，未输出私有World内容、trace、敏感上下文，未上传 artifact/cache/可下载副本。阻断后不再自动获取。
- **不复制私有内容**: 本文不复制 private_world.sqlite 内容、trace、driver.log 等。
- **不擅自删除或改写仓库历史**: 保留分支与历史运行记录，未删除。

## 6. 最终现场索引

- 最终头: `7cd0a12e6677c5ec1565b1c20d4a2e866c70c449`
- 已测源码头: `4859d2e6141649fcf0e6715e69dff0635c9734dc` (c15/p16 PASS)
- 参考头: `5b5e2306c39b5b09b260de787403567a31d0efbd` (real-a 88/88 13→14 model0 cross-process PASS)
- PR: #125 OPEN, [BLOCKED / DO NOT MERGE], launch_authorized=false
- 真实A工作流: 最终禁用 `if: false`，禁止继续运行，历史 runs 保留
- 缺陷修正: publication非变异、freeze收据验证、broker结构边界 (见 2528c22, key_sources_2528c22/)
- 架构: 真实Resident为新Arena窗口AI本人，外部API PAUSED，HTTP作为AIOS工具接口可评估但调用外部模型非批准路线
- 合成机械: 131 preflight + 146 regression PASS (4859d2e, 5b5e230)
- 隔离: actual_namespace_probe INCONCLUSIVE, actual_Resident_isolation BLOCKED
- 平台结论: 当前已测仓库连接Arena窗口不满足隔离，其他模式未核实
- 任务: 已有未合并工程成果，暂停于Arena实际访问边界阻塞 (main任务板尚未同步)
- 交付: A (workflow审计)、B (Arena可行性表格)、C (head证据)、本索引

交回最终现场后停止。

PR保持OPEN；launch_authorized=false
