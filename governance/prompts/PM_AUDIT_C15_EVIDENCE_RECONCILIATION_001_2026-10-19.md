# 独立新窗口任务：PM-AUDIT-C15-EVIDENCE-RECONCILIATION-001

## 0. 角色与唯一任务

你是 **Independent AIOS Evidence & Core-Impact Reviewer**。

你不是：本次 PM 审核作者、原 Option B 工程作者、原 Resident A/B/C、原验收/评估结论作者、Operator 签发者、Core 修复工程师或合并所有者。请先声明是否参与这些工作；存在利益/上下文冲突则停止并说明，不能把角色名当独立性证明。

唯一任务是：

> 对已存在的 C15 关闭证据、其原始验收合同、Window 80 新 Core 基线与放行权限做只读独立核证。尝试证伪，而不是复述 PM 报告。可支持、可反驳，也可因材料不足保留 UNKNOWN。

这是 Reviewer 包，**不是 fresh Resident 包**。允许为审核读取已授权的历史 PM/评估材料，但不得由此扮演 Resident 或启动实验。

## 1. 生效与现场核对

先使用仓库正常 GitHub 连接，只读核对：

1. 实时 main 与当前唯一 task board。
2. 本任务的治理发布 PR 是否已正常合入 main。
3. 本任务是否仍为当前任务，是否已有其他 owner/Reviewer 在执行。
4. `governance/PM_AUDIT_C15_EVIDENCE_RECONCILIATION_001_RELEASE_2026-10-19.md`。
5. `reviews/PM_AUDIT_C15_EVIDENCE_RECONCILIATION_001/BASELINE.json`。

尚未合入则 `GOVERNANCE_NOT_EFFECTIVE / STOP`，不能把分支/PR 存在当放行。不要通过修改合同、改授权或换候选解决启动阻塞。

不要求切换到某个特殊分支；平台固定分支时始终留在该会话分支，以允许的新 reviewer 证据路径交付，不能修改他人的冻结分支。

## 2. 精确输入与漂移

主工程基线：`259d035386ea203981c6247eeb4433dbfd8eed3f`。

前一审核基线：`24193afd949e39a112f873218fc98199265df7fa`。

| 对象 | PR | exact HEAD |
|---|---|---|
| Option B 工程 | #390 | `52d169e8fb96248b058ab3685d9dcb1f6cbce204` |
| Phase A | #392 | `2d92328205e16ec8b5317eaca8f3b666656ad09b` |
| Phase B | #393 | `302dab2565f61dd37ca57195bae7ed9337cdfede` |
| Phase C | #394 | `6cd89d6e3761347487946ca95e59bae380a3ae46` |

从 Git 对象核对 BASELINE.json 的 protected trees、pyproject blob、selected contract blobs；对 Candidate 重新读远端 head。main 仅因治理前进且保护对象相同，可以记录后继继续；代码、合同、候选身份漂移必须 STOP / REVALIDATION_REQUIRED，不暗中换 pin。任务已被 supersede 或多 owner 冲突也必须停止。

不能用 PR 总 diff 代替“各候选相对其精确父基线的 delta”；A/B/C 继承了前序候选内容，需要逐段区分。evidence-only 不合 main 本身不是失败。

## 3. 权限与执行边界

本任务是只读证据审阅：
- 可以通过 `git` / `gh` 取得可授权读取的现有文件、元数据、已发布报告、日志和校验清单。
- 可以只读计算哈希、查询冻结数据库、核对元数据和链接；缓存隔离于仓库交付之外。
- 不运行 pytest、原验收/评估脚本、模型、Resident 或其启动器；不导入候选 Python 包执行代码。
- 不读取/签发/导出私钥、可用 enrollment/grant、真实 signing authority、访问令牌或隐藏思维链。
- 不改 Core、产品测试、工作流、包配置、fixture、World/index、exchange、原始响应/账本、原 SHA256SUMS 或前序审查文件。
- 不 force-push 或改写历史；不合并/关闭 PR；不启动硬件/UI/C16 开发。
- 原始真实 World/fixture/敏感完整日志不能复制到新公开 PR 或交给 fresh Resident。只发布最小脱敏证据与精确可验证引用；需要受控存储时登记访问角色和内容哈希，不发布能力本身。

材料不可达就记录 BLOCKED。不要为了完成任务安装、设计、签发或扩权。需要新执行才能确定的事，写出新任务的具体需求交 PM，而不是现在执行。

## 4. 必审工作包

### A. 合同与 R6

原始依据：
- `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_RULING_2026-09-22.md` §13 / §16 / §17。
- `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_TEST_PLAN_2026-09-22.md`。

必须寻找绑定实际 A/B/C run/session 的可信 provider/model 差异证明；different UUID、不同进程、不同窗口、不同自报 model 字符串都不能自动等于可信平台证明。

若找不到，按原规则记录 R6 `PARTIAL`、reason `INSUFFICIENT_EVIDENCE`。若发现有效的后续合同修订，必须证明其授权、精确版本、生效时间和适用范围，而不是单凭角色头衔接受其覆盖原合同。

不能从 provider/model 字段为 NULL 推断没有模型调用；也不能从 47 条 exchange/attempt 推断其作者/底层模型身份已被证明。

### B. R1–R9 要求级语义证据

检查 Evaluator 源码、报告和 A/B/C 精确证据；不把探针通过率当语义结论。

逐轴记录：
`requirement → actual fact/input → cognition object/revision or justified silence → supporting Evidence/Outcome → later retrieval result → later decision/effect → later correction`

矩阵字段至少包括：axis、required claim、candidate/run、cursor、request_id、object/ref/revision、可访问来源与哈希、实际支持范围、反例/局限、verdict、reason。涉及的四类 RCC cognition 必须按合同分别讨论，不用对象数量设 KPI。

重点独立攻击：
- Observation 数量不等于用户理解形成。
- 排除一个字符串不等于 calibration 或 grounded experience 形成。
- 搜过 `search_world` 不等于 prior cognition 对决定产生实质影响。
- 回复出现“生产”不等于发生合法且被消费的认知修正。
- 不同 ID 不证明旧模型上下文被丢弃。
- 样例叙述、断言和真实代码/数据结果之间是否有未证明跳跃。

PM 报告中的发现本身也只是待证伪的输入，不需要预设它一定正确。

### C. 安全、作者与历史失败

取得 Window69 原始脱敏验证材料或其受控持久存储收据，核对 exact #390 candidate、环境、Case、命令、退出码、正负对照和哈希绑定。宿主绝对路径与摘要评论只是导航，不当作已取得原始证据。

对本次真实 Resident 的 author/provenance/授权路径建立明确映射，不用另一组 TEST_ONLY 签名测试的 PASS 代替。

对历史 original38 七项失败逐项给出 `CLOSED_WITH_EVIDENCE / SUPERSEDED_BY_APPROVED_CONTRACT / STILL_BINDING / UNKNOWN`，附授权与事实；既不能自动全部视为当前代码 bug，也不能默认为已关闭。

### D. 运行身份与候选迁移

对账机械 identity、SESSION_END、freeze manifest、账本、completion report、接受收据、PR 正文和任务板：
- Phase B completion report 中的 process/session 与 RUN_IDENTITY 的差异。
- Phase C 旧 run `...bd8446e1205d`、接受 run `...cf585be261f9` 及旧/新 candidate 记载。

区分“叙述笔误”“未接受候选”“另一实际运行”“无法判断”。只提出追加勘误/处置，不改冻结字节。不要仅凭文本差异断言出现非法第二次实验。

### E. Window80 新 Core 影响（本任务的前置内容，不另建队列）

核对 `24193afd… → 259d0353…` 的真实 delta，以及：
- `src/aios_core/narrative/`；
- `src/aios_core/curves/`；
- `src/aios_core/tools/`；
- `src/aios_core/communication/experience_tracker.py` 与导出；
- 四组新产品测试与 Window80 收据。

影响矩阵要求覆盖：World/schema/subject isolation、对象与 evidence 引用、revision/idempotency、索引可见性、重启恢复、模型/机械职责、capability/授权边界、现有 Runtime/headless 调用路径、旧 Resident/RC 的适用范围。

不能仅根据存在独立类或其测试就宣布已经接入主运行链；也不能仅根据字符串搜索未命中就断言完全没有动态接入。需要追踪普通启动、注册、能力目录及读写路径，无法静态确定则 UNKNOWN。

对既有 main CI run `39223062778` 只读查实际最终状态。作者 18/18、新 CI SUCCESS、完整工程独立验收、认知 PASS 是四种不同证据；不互相替代。

给出可沿用/需补验/证据不足的具体范围。此任务不执行新 Gate，不默认所有旧证据无效、不指令全部重跑。

## 5. 交付路径与内容

仅新增：
`reviews/PM_AUDIT_C15_EVIDENCE_RECONCILIATION_001/reviewer/<unique-review-id>/`

至少交付：
1. `REVIEW_IDENTITY.md`：角色、既往参与、独立性限制、观察时间、实时 main 与候选。
2. `SOURCE_MAP.json`：精确 ref/blob/hash、受控来源、获取状态；不含秘密。
3. `AXIS_EVIDENCE_MATRIX.md`：R1–R9 要求级证据与裁决依据。
4. `FINDING_DISPOSITION.md`：PM-AUD-01..06 的 supported / unsupported / unknown，是否发现新的独立问题。
5. `RUN_IDENTITY_RECONCILIATION.md`：单值身份图、差异分类与必要勘误。
6. `CORE_IMPACT_MATRIX.md`：Window80 变更对旧 RC/Resident/新准入的具体影响。
7. `LIMITATIONS.md`：没有取得/没有执行/不能证明的内容及最小下一任务需求。
8. `SHA256SUMS`：本 Reviewer 交付的校验清单，不改前序清单。

新增材料是 REVIEW_ONLY。保留仓库规定的 evidence-only/不可变语义，不将私有 World 合主干。不靠一个自写的“全部 PASS”摘要代替上述内容。

## 6. 停止与移交

合法结果：
- `REVIEW_COMPLETE / EVIDENCE_SUPPORTED`；
- `REVIEW_COMPLETE / GAPS_CONFIRMED`；
- `BLOCKED / EVIDENCE_ACCESS_REQUIRED`；
- `REVALIDATION_REQUIRED`。

材料不足不填 PASS；也不为了满足预期而把全部轴填 INVALID。技术轴只按合同使用 VALID / PARTIAL / INVALID，缺证原因单列。未知或无法获得的文件逐项写明提供角色；不向所有者索取密码、token、私钥或 2FA。

完成后发布新的 Reviewer-owned REVIEW_ONLY PR 或按平台批准方式提供可耐久取得的 evidence-only 提交，记录实际 URL/head；不合并。交回 PM，由 PM 决定下一唯一任务与治理更新，停止，不进入 Resident、C16 或硬件。
