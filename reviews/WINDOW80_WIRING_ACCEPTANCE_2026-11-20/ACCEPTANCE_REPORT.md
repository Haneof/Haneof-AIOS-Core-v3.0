# Window80 接线独立验收报告

- **任务**：`PM-WINDOW80-WIRING-ACCEPTANCE-001`
- **验收员**：独立验收窗口（全新窗口，与 Window80 实现、PM 审核、两次复核 RV20261120-001 / RV20261120-002、验收、Operator、Core 修复、合并无任何既往参与）
- **验收对象**：精确冻结树 `8317769`（`Haneof/Haneof-AIOS-Core-v3.0` main）
- **验收执行树**：本地 `3977f42`（2026-11-20 PM 裁决治理提交，本地未推远端）
- **日期**：2026-11-20（UTC）
- **总体出口**：**ACCEPTED_WITH_GAPS**（接线成立，可接受；带 3 项缺口，见 §5）

## 0. 基线确认

`git diff 8317769..HEAD --stat`：6 个文件，68 行新增、2 行删除，全部是治理/文档/复核文件：

- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `governance/C15_RCC_RES_A_RERUN_005_PHASE_B_ACCEPTANCE_RECEIPT_2026-10-19.md`
- `governance/C15_RCC_RES_A_RERUN_005_PHASE_C_ACCEPTANCE_RECEIPT_2026-10-19.md`
- `reviews/PM_REVALIDATION_BASELINE_001/BASELINE.json`

`src/`、`tests/`、`tools/`、`pyproject.toml`、`.github/workflows/` **零改动**（grep 验证）。因此本验收验证的代码与冻结树 `8317769` 完全一致，本地治理提交不影响验收结论。

## 1. 逐项结论

| # | 验收项 | 结论 | 一句话证据 |
|---|--------|------|-----------|
| 1 | 7 个子系统接入 FusedTurnRuntime | **PASS** | 导入 `:34–40`、构造 `:378/442/447/451/455/460/465`、11 个 capability 注册 `:1162–1367`，每个 handler 均委托给对应子系统 |
| 2 | ExperienceTracker 每轮自动调用 | **PASS** | `run_turn` `:4302` 无条件调用 `_record_turn_experience` → `experience_tracker.record_interaction_experience`（`:3022`） |
| 3 | capability 授权链 | **PASS** | 唯一 `registry.invoke` 调用方是 `cognitive_runtime.py:521`，且位于授权门 `:503–520` 之后；6 个 WRITE 能力全在 `_authorize_side_effect` 白名单内；C14 wake 下 6 个全拒 |
| 4 | 索引可见性 | **PASS**（带缺口 G-1） | 全部产物经 `store.commit` 落库，`index.catch_up()` 全量入 `search_occurred`/`search_doc`；但 `narrative_segment` / `dimension_curve_point` / `tool_proposal` 不在关键词白名单内 |
| 5 | 重启恢复 | **PASS**（静态+测试，未做 live 探针） | 7 个子系统零内存缓存、状态全在 SQLite；`HeadlessCore.start()` 重建 runtime（`headless/core.py:238–264`）；reattach 测试通过 |
| 6 | 旧 CommunicationExperienceService 并存 | **PASS**（无冲突，有观察） | 只构造一次（`:378`），capability 与 ExperienceTracker 共用同一实例、同一落库路径；自动记录与模型显式记录是不同记录，无重复写入 |
| 7 | headless 零引用 + L8 | **PASS**（L8 残留 UNKNOWN，非阻塞） | headless/ 内 7 个类名零直接引用；接线不依赖 handler 字符串；L8 部署事实仍不可静态得知 |

## 2. 逐项证据

### 2.1 七个子系统接入（PASS）

导入（`src/aios_core/runtime/turn_runtime.py`）：

- `:34` `CommunicationExperienceService`（`aios_core.communication`）
- `:35` `ExperienceTracker`（`aios_core.communication.experience_tracker`）
- `:36` `AISelfMindTracker`（`aios_core.cognition.ai_self`）
- `:37` `DimensionCurveTracker`（`aios_core.curves.dimension_curve`）
- `:38` `NarrativeSegmenter`（`aios_core.narrative.segmenter`）
- `:39` `DynamicTopicAssociator`（`aios_core.query.topic_associator`）
- `:40` `ToolProposalPipeline`（`aios_core.tools.proposal_pipeline`）

构造（`FusedTurnRuntime.__init__`，同一文件）：

- `:378` `self.communication_experience = CommunicationExperienceService(store, index, subject_id)`
- `:442` `self.narrative_segmenter = NarrativeSegmenter(store, index, subject_id)`
- `:447` `self.dimension_curves = DimensionCurveTracker(store, subject_id)`
- `:451` `self.tool_proposals = ToolProposalPipeline(store, subject_id)`
- `:455` `self.experience_tracker = ExperienceTracker(store, service=self.communication_experience, subject_id)`
- `:460` `self.topic_associator = DynamicTopicAssociator(store, index, subject_id)`
- `:465` `self.ai_self_tracker = AISelfMindTracker(store, ai_subject_id, user_subject_id)`

capability 注册（11 个，与任务书所称“约 10 个”相符，实际清点为 11 个，含 `record_communication_experience`）：

| capability | 注册行 | kind | handler | 委托目标 |
|---|---|---|---|---|
| `record_communication_experience` | `:1162` | WRITE | `_record_communication_experience`（`:2863`） | `communication_experience.record` |
| `associate_topics` | `:1220` | READ | `_associate_topics`（`:2949`） | `topic_associator.associate_topic` |
| `get_effective_communication_style` | `:1235` | READ | `_get_effective_communication_style`（`:2965`） | `experience_tracker.get_effective_style` / `get_avoidance_list` |
| `record_ai_promise` | `:1249` | WRITE | `_record_ai_promise`（`:3032`） | `ai_self_tracker.record_promise` |
| `reconcile_ai_promise` | `:1267` | WRITE | `_reconcile_ai_promise`（`:3053`） | `ai_self_tracker.fulfill/cancel_promise` |
| `inspect_ai_self_mind` | `:1284` | READ | `_inspect_ai_self_mind`（`:3081`） | `ai_self_tracker.get_mind_summary` |
| `open_narrative_segment` | `:1296` | WRITE | `_open_narrative_segment`（`:3084`） | `narrative_segmenter.open_segment` |
| `seal_narrative_segment` | `:1315` | WRITE | `_seal_narrative_segment`（`:3117`） | `narrative_segmenter.seal_segment` |
| `record_dimension_curve_point` | `:1333` | WRITE | `_record_dimension_curve_point`（`:3139`） | `dimension_curves.record_point` |
| `detect_burnout_risk` | `:1352` | READ | `_detect_burnout_risk`（`:3169`） | `dimension_curves.detect_burnout_risk` |
| `propose_tool` | `:1367` | WRITE | `_propose_tool`（`:3189`） | `tool_proposals.draft_proposal` |

动态证据：`tests/runtime/test_fused_turn_cognitive_integration.py` 的 5 个测试用模型 handler 真正发出 capability call、走完整 `run_turn` 链路并断言结果（含 `propose_tool` 返回 `proposal_id` 以 `tlp_` 开头、`get_effective_communication_style` 返回 `recommended_style` 与 `avoidance_blacklist`），全部通过（见 §4）。

### 2.2 ExperienceTracker 每轮自动调用（PASS）

`turn_runtime.py:4302`，`run_turn` 内在 `rolling_window.record_turn` 之后无条件执行：

```python
# DEF-002: Close Bayesian communication adaptation loop automatically
self._record_turn_experience(
    user_input=user_input,
    assistant_text=assistant_text,
    user_obs_ref=ObjectRef(object_id=user_commit.observation_id, revision=1),
    occurred_at=occurred_at,
)
```

`_record_turn_experience`（`:2989–3030`）按启发式判定用户反应（RESISTED / IGNORED / ACCEPTED，见 `:3007–3013`），调用 `self.experience_tracker.record_interaction_experience`（`:3022`），最终经 `CommunicationExperienceService.record` 落库。

观察（不构成 FAIL，记为缺口 G-2）：`:3027–3028` 用裸 `except Exception: pass` 包住整次写入——写入失败时整轮反馈静默丢失，无任何信号。另启发式本身较粗（assistant 文本 ≤60 字符判 concise、含“抱歉”判 supportive，`:3015–3017`），但这是既有设计，不在本验收范围内改判。

### 2.3 capability 授权链（PASS）

- 唯一调用点：`src/aios_core/runtime/cognitive_runtime.py:521` 的 `self.registry.invoke(call)`；全仓 grep 确认 `registry.invoke` 在 `src/` 内无其他调用方。
- 授权门在调用点之前（`cognitive_runtime.py:503–520`）：`spec.side_effecting` 为真时必须经 `side_effect_authorizer(spec, call, snapshot)`，否则返回 `CAPABILITY_NOT_AUTHORIZED` 且不执行。
- authorizer 即 `FusedTurnRuntime._authorize_side_effect`（接线于 `turn_runtime.py:1389`，`side_effect_authorizer=self._authorize_side_effect`）：
  - READ 能力直接放行（`:3300–3301`）。
  - C14 认知推导 wake 下只允许 `_C14_COGNITIVE_SIDE_EFFECT_ALLOWLIST` 的 4 个认知操作（`turn_runtime.py:171–178`：`commit_claim` / `commit_ai_world_claim` / `revise_claim` / `retract_claim`）——6 个 Window80 WRITE 能力在 C14 wake 下**全部被拒**（`:3308`）。
  - 其余 wake 下显式白名单（`:3312–3353`）包含全部 6 个 Window80 WRITE 能力：`record_communication_experience`、`record_ai_promise`、`reconcile_ai_promise`、`open_narrative_segment`、`seal_narrative_segment`、`record_dimension_curve_point`、`propose_tool`。4 个 READ 能力（`associate_topics`、`get_effective_communication_style`、`inspect_ai_self_mind`、`detect_burnout_risk`）无需授权。
- 无绕过路径：全仓 grep 确认 11 个 handler 方法在 `turn_runtime.py` 外零直接调用；在文件内除注册行（`:1180–1382`）外也无直接调用。模型唯一能触达这些 handler 的路径就是经授权的 registry。
- 纵深注记（非绕过）：除 `_record_communication_experience`（`:2875` 在非 active turn 时抛错）外，其余 WRITE handler 在 `_active_turn_time is None` 时回退到 `datetime.now(timezone.utc)` 而不是拒绝。鉴于唯一调用路径已被授权门守住，这只是纵深防御的薄弱点，不构成可利用的绕过。

### 2.4 索引可见性（PASS，带缺口 G-1）

- 全部 7 个子系统的写操作都经 `self.store.commit(...)` 落入世界库：`communication/service.py:197`（`commit_or_replay`）、`narrative/segmenter.py:193`、`curves/dimension_curve.py:242`、`tools/proposal_pipeline.py:172`、`cognition/ai_self.py:233`。
- `WorldSearchIndex._index_row`（`src/aios_core/query/search.py:418–485`）对每一行落库对象都写入 `search_occurred` 与 `search_doc` 投影（`:476–485`），并恒加 subject/ref/dimension id-token；`catch_up` 由 `run_turn`（`turn_runtime.py:4282`，assistant commit 之后）以及 `CommunicationExperienceService.record`（`:214`）、`NarrativeSegmenter._catch_up`（`segmenter.py:52–54`）触发。因此全部产物进索引，可按 object_id / 类型 / 时间 / 维度 / 引用结构化检索；`DynamicTopicAssociator` 经 `store.list_payloads` 直接读取（`topic_associator.py:174/204/224/241`），不受 FTS 白名单限制。
- 缺口 G-1：`_TEXT_FIELDS` 关键词白名单（`search.py:52–71`）只含 `communication_experience`（scenario/style/tone）与 `claim`（content，承诺即 Claim 对象）——叙事段、曲线点、工具提案的文本**不可关键词检索**。`narrative_segment`、`dimension_curve_point`、`tool_proposal` 三类不在白名单内，其标题/内容只进 `search_doc` 的空 haystack，不进 `search_postings`。这不影响结构化检索与 topic 关联，但“搜一句话找到某段叙事/某个提案”目前做不到。

### 2.5 重启恢复（PASS，静态+测试，未做 live 探针）

- 7 个子系统零内存缓存：grep `self._* = {}` / `[]` / `lru_cache` / `@cache` 在 7 个源文件内零命中；`ExperienceTracker._load_experiences`（`experience_tracker.py:111`）每次从 store 读；其余读路径同样经 `store.list_payloads` / `get_payload`。
- 进程重启路径：`HeadlessCore.start()`（`src/aios_core/headless/core.py:238–264`）重新打开同一 SQLite 世界库、`index.catch_up()`、全新构造 `FusedTurnRuntime`（`:245`）——接线状态由 store 重新导出，不依赖进程内存。`stop()`（`:271–279`）在释放单写租约前先 `index.catch_up()`。`headless/recovery.py:1–6` 明言：SQLite 世界是唯一真相库，索引永远是可重建投影。
- 测试证据：`tests/c15_persistence/test_environment_reattach.py`（detach/reattach、远端往返、损坏 manifest 拒绝）在本次 83 项子集中通过。
- 未执行：live kill-and-restart 进程探针（未实际杀进程重起验证端到端恢复）。本验收不启动 Resident、不做进程级探针，故该项记为静态+测试证据充分、动态探针缺失（缺口 G-3）。

### 2.6 旧 CommunicationExperienceService 并存（PASS，无冲突）

- 只构造一次：`turn_runtime.py:378`。两条使用路径共用同一实例：
  - capability `record_communication_experience` → `_record_communication_experience`（`:2863`）→ `self.communication_experience.record`（`:2886`）；
  - `ExperienceTracker` 构造时传入 `service=self.communication_experience`（`:455–459`），其 `record_interaction_experience` 委托给 `self.service.record`（`experience_tracker.py:109`）。
- 同一落库路径、同一幂等域（`idempotency_key=f"communication-experience:{experience_id}"`，`service.py:209`）。自动记录（每轮，scenario=`daily_chat`）与模型显式记录的 stable id 由 scenario/style/reaction/evidence_refs/时间共同决定（`service.py:136–141`），是不同的记录，不会互相覆盖或重复写入。
- 观察：自动路径每轮产生一条记录，以粗启发式判定反应；显式模型记录稀疏。两者共同进入 `get_effective_style` 的贝叶斯统计，自动路径的量可能主导风格推荐。这属于行为观察，不构成冲突或重复写入。

### 2.7 headless 零引用 + L8（PASS，L8 残留 UNKNOWN，非阻塞）

- headless/ 内 7 个类名零直接引用（grep 空）。但 headless 并非与接线无关：`headless/core.py:245` 构造 `FusedTurnRuntime`，接线经该构造可达——属于传递可达，不是“接线在 headless 外”。
- L8：`load_model_handler`（`headless/core.py:48–74`）从 `--model-handler module:attribute` 字符串加载一个 `RuntimeSnapshot -> ModelDirective` 可调用对象。仓内实际取值只有 `aios_core.runtime.live_handler:handler` 与 `aios_core.runtime.siliconflow_handler:handler`（`docs/operations/LOCAL_MODEL.md:39`、`.github/workflows/core-headless.yml:37`、`.github/workflows/core-recovery.yml:87`），均为模型适配器；无任何部署配置指向 Window80 类。
- 关键点：Window80 类不能充当该 handler——其构造签名是 `(store, index, subject_id)`，不是 `RuntimeSnapshot -> ModelDirective`；且接线发生在 `FusedTurnRuntime.__init__` 内，与 handler 字符串无关。L8 作为“实际部署命令是什么”仍严格 UNKNOWN（仓内无真实部署命令可查），与 RV20261120-001 / RV20261120-002 的记录一致；但它**不阻塞本次接线验收**，因为接线成立与否不依赖 handler 取值。

## 3. 执行的验证

### 3.1 跑过的测试

| 验证 | 命令 | 结果 |
|---|---|---|
| 统一健康检查 | `.venv/bin/python tools/check.py --quick`（本地 HEAD `3977f42`） | **PASS**：550 passed，3 skipped，36s 内；治理 PASS；VERDICT: PASS |
| Window80 专项子集 | `pytest` 10 个文件（见下），`--junitxml=/tmp/w80-junit.xml` | **83 passed，0 failed，0 errors，0 skipped**，104.1s |

专项子集文件（10 个）：

- `tests/runtime/test_fused_turn_cognitive_integration.py`（5 项：topic 关联、承诺双分录、叙事+曲线、工具提案+沟通追踪、滚动窗口）
- `tests/communication/test_experience_tracker.py`
- `tests/cognition/test_ai_self.py`
- `tests/curves/test_dimension_curve.py`
- `tests/narrative/test_narrative_segmenter.py`
- `tests/query/test_topic_associator.py`
- `tests/tools/test_proposal_pipeline.py`
- `tests/integration/test_v3_constitutional_cognition_closure.py`
- `tests/integration/test_v3_audit_bugfixes.py`
- `tests/c15_persistence/test_environment_reattach.py`

3 个跳过的是 live provider 测试（`tests/runtime/test_live_multimodel_habitation.py:388/411/434`），需 `AIOS_LIVE_PROVIDER=1` + 可达端点——记为跳过，不算失败也不算通过。

### 3.2 未跑的

- 全量 `pytest tests`：很慢（既往记录 25 分钟只跑约 50%），本次只跑相关子集；`--quick` 的 550 项已覆盖 runtime/unit/audit 三套件。
- live provider 测试（需真实端点与 `AIOS_LIVE_PROVIDER=1`）。
- 模型调用、Resident 启动、live kill-and-restart 进程探针（任务边界禁止 / 未执行）。

## 4. 新发现的问题

本次验收未发现 FAIL 级问题。发现 3 项缺口与 2 项观察，均非接线不成立：

- **G-1（索引关键词缺口）**：`narrative_segment`、`dimension_curve_point`、`tool_proposal` 不在 `src/aios_core/query/search.py:52–71` 的 `_TEXT_FIELDS` 白名单内，标题/内容不可关键词检索，仅结构化检索可达。影响：叙事段与工具提案建成后，无法用一句话关键词搜到。
- **G-2（自动经验写入静默失败）**：`turn_runtime.py:3027–3028`，`_record_turn_experience` 的写入异常被裸 `except Exception: pass` 吞掉；一旦写入失败，该轮反馈永久丢失且无任何信号。
- **G-3（重启动态探针缺失）**：重启恢复只有静态证据（零内存缓存 + store 唯一真相 + `HeadlessCore.start()` 重建）与 reattach 测试，未做真实进程 kill-and-restart 端到端验证。
- **观察 O-1**：自动经验记录每轮一条且启发式较粗（`:3015–3017`），可能主导贝叶斯风格统计，压过模型显式记录；建议后续以统计口径核对，而非本次验收改判。
- **观察 O-2**：除 `_record_communication_experience` 外，其余 WRITE handler 在非 active turn 时回退到当前时间而非拒绝（`_active_turn_time or datetime.now(timezone.utc)`）；唯一调用路径已被授权门守住，不构成绕过，但纵深上弱于显式拒绝。

## 5. 缺口清单

| 缺口 | 内容 | 严重度 | 建议归属 |
|---|---|---|---|
| G-1 | 三类产物（叙事段/曲线点/工具提案）不可关键词检索 | 中 | 另开最小工程任务：补 `_TEXT_FIELDS` 白名单并加回归测试 |
| G-2 | 自动经验写入异常被静默吞掉 | 中 | 另开最小工程任务：改为记日志/计数，至少留痕 |
| G-3 | 无 live 重启探针 | 低 | 审计后另立验证任务时补一次进程级 kill-and-restart 探针 |
| L8 | headless 实际部署命令仍 UNKNOWN | 低（非阻塞） | 部署/运维方提供真实启动命令后核对；不阻塞接线验收 |

## 6. 建议 PM 下一步裁决

1. **接受本次接线验收（ACCEPTED_WITH_GAPS）**：7 项全数 PASS，无 FAIL；冻结树 `8317769` 的 Window80 接线成立。
2. **G-1、G-2 另开最小工程任务**（各带授权 trailer 与独立验收），不要在审计裁决里顺带修——审计阶段只接受证据，不接受新功能。
3. **G-3 与 L8 记入待办**：G-3 待审计后验证任务时补探针；L8 待部署方给出真实启动命令后再核对，两者均不阻塞本次出口。
4. **不建议因此重开审计基线**：本验收只验证接线，不涉及 R1–R9 语义证据；审计出口仍以 RV20261120-001 / RV20261120-002 的裁决为准。

## 7. 方法与边界声明

- 本验收是全新窗口执行，与 Window80 实现、PM 审核、两次复核、验收、Operator、Core 修复、合并无任何既往参与。
- 未改任何代码与已有文件，未提交、未 push、未开 PR，未碰凭证，未调外部模型，未启动 Resident。
- 唯一写入位置：`reviews/WINDOW80_WIRING_ACCEPTANCE_2026-11-20/`（本报告及 SHA256SUMS）。
- 证据定位方式：静态核对给文件:行号；测试给文件名与计数；跳过的 live 测试不计入通过。
