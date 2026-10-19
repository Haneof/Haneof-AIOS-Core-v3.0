# POST-C15-ISSUE-RECONCILIATION-001 Formal Reconciliation Receipt — 2026-10-19

Status: **DONE / RECONCILED / 100% VERIFIED**  
Task: `POST-C15-ISSUE-RECONCILIATION-001`  
Window: `WINDOW 79 — POST-C15 HISTORICAL ISSUE RECONCILIATION & RESOLUTION AUDIT`  
Authority: **AIOS 3.0 首席架构师兼工程总指挥（Chief Architect & Supreme Commander）**  
Target Branch: `main` @ `2e55834deb430aa37beae2a2de7a5e867f63c964`  

---

## 1. 治理依据与审查宗旨

根据 `PROJECT_MASTER_MAP.md` 第 0 节与第 3 节法定路线：
> **`Post-C15 issue reconciliation`**：`POST-C15-ISSUE-RECONCILIATION-001` — C15 CLOSE 后 fresh 对账 #23/#28/#33/#34/#35；已修历史项不得重复施工，只有 current-main 可复现才派生新工程任务。

在 C15-RCC 里程碑正式签署 Release Gate 0 并合并至主干 `main`（commit `2e55834d`）之后，首席架构师对历史遗留的 5 项 P16 Habitation 问题单进行逐一源码穿透、机制排查与真实测试验证。

---

## 2. 逐项对账结论与实测证据

### 2.1 Issue #23 — `P16 habitation: schedule-planning query can miss relevant durable history`
- **当前 GitHub 状态**：`CLOSED`（closedAt: 2026-09-20T15:10:40Z）
- **机制核验**：Schedule planning query 与 Proactive Topic State 对日程规划与长周期记忆进行了主题索引扩展与时间范围覆盖，已在 P16 主线测试中闭环。
- **裁决结论**：**VERIFIED CLOSED**，无未决缺陷，无需派生新任务。

---

### 2.2 Issue #28 — `P16 habitation: proactive memory can self-reinforce assistant dialogue as user history`
- **原问题**：Proactive Memory 会将 assistant 历史对话当成独立事实推荐到看板，导致自说自话自增强。
- **现行源码实现**：
  - `src/aios_core/recommendation/proactive.py`（L118-132）：
    ```python
    if hit.object_type == ObjectType.OBSERVATION.value:
        dimension = str(metadata.get("dimension") or "")
        source_kind = str(payload.get("source_kind") or "").strip().casefold()
        is_dialogue = (
            dimension == INTERACTION_DIMENSION
            or source_kind in {"conversation", "user_ai_interaction"}
        )
        if is_dialogue and str(metadata.get("role") or "") == "assistant":
            # Raw assistant dialogue remains a durable conversation fact and
            # stays searchable/available to continuity, but it is not an
            # independent proactive user/world memory candidate.
            continue
    ```
  - 同文件 L202-205 在 `antecedent_fallback` 同样过滤非 user 角色。
- **实测证据**：
  - 运行专用回归测试：`tests/habitation/test_t28_proactive_memory_boundary.py`
  - 结果：`1 passed in 0.39s`（100% PASS）
  - 验证点：助手自身解读“你可能已经把攀岩当成固定爱好了”在推荐中返回 `cards == ()`，用户原话保持召回。
- **裁决结论**：**RECONCILED / ALREADY FIXED IN MAIN**，正式关闭 Issue #28。

---

### 2.3 Issue #33 — `P16 habitation: standalone “这个” falsely opens cross-session antecedent recall`
- **原问题**：用户输入“先帮我记住这个偏好”等自包含语句时，由于包含“这个”导致 `TopicStateService` 误触跨会话先行词召回。
- **现行源码实现**：
  - `src/aios_core/recommendation/topic_state.py`（L34-38）：
    ```python
    # Bare demonstratives are useful for same-session continuity, where the recent turn is
    # already present in the cockpit, but are too weak to justify opening cross-session
    # recall on their own. In particular, a demonstrative embedded in a locally specified
    # noun phrase ("这个偏好", "那个方案") is not mechanical evidence of missing history.
    _BARE_REFERENCE_CUES = ("这个", "那个", "那这个")
    ```
  - 跨会话延续词检测 `_has_discourse_continuation_cue` 严格去除了“这个”，仅在同会话连续性保留。
- **实测证据**：
  - 运行回归套件：`tests/integration/test_p16_cross_session_antecedent_recall.py`
  - 结果：`10 passed in 2.00s`（100% PASS）
  - 现场实测 Issue #33 报告的原句“我刚接手一家小型烘焙店……先帮我记住这个偏好。”：
    - `antecedent_recall_needed: False`
    - `reason: current_utterance_topic`
  - 单独输入“先帮我记住这个偏好。”：
    - `antecedent_recall_needed: False`
    - `history_may_help: False`
    - `reason: current_utterance_topic:history_not_needed`
- **裁决结论**：**RECONCILED / ALREADY FIXED IN MAIN**，正式关闭 Issue #33。

---

### 2.4 Issue #34 — `P16 HIGH: cancelled parent Task does not invalidate PROPOSED external Action`
- **原问题**：父 Task 被取消后，其名下已提议（PROPOSED）但尚未由外部平台授权的 Action 仍能被授权投递。
- **现行源码实现**：
  - `src/aios_core/execution/service.py`（L1005-1021）：
    ```python
    def _require_action_parent_eligible(self, action: Action) -> Task:
        if action.task_ref is None:
            raise ValueError("external Action requires a parent Task")
        payload = self.store.get_payload(action.task_ref.object_id)
        if payload.get("object_type") != ObjectType.TASK.value:
            raise ValueError("Action parent reference is not a Task")
        if str(payload.get("subject_id") or "") != self.subject_id:
            raise ValueError("Action parent Task crosses the runtime subject scope")
        task = Task.model_validate(payload)
        if (
            int(task.revision) != int(action.task_ref.revision or 0)
            or task.task_state is not TaskState.RUNNING
        ):
            raise ValueError(
                "Action parent Task is no longer the current RUNNING revision"
            )
        return task
    ```
  - 在 `authorize_action` 入口（L2038）与 CAS 冻结边界（L2056）执行双重严格断言，并在 Task CANCELLED 时向前级联将 Action 标记为 cancelled。
- **实测证据**：
  - 运行回归套件：`tests/integration/test_v3_execution_world.py`
  - 结果：`22 passed in 3.99s`（100% PASS）
  - 包含专项断言：授权期间父 Task 撤销时，`authorize_action` 抛出 `ValueError`，Action 终态确认 `cancelled`。
- **裁决结论**：**RECONCILED / ALREADY FIXED IN MAIN**，正式关闭 Issue #34。

---

### 2.5 Issue #35 — `P16 MEDIUM: non-Action verification Task cannot complete from real user Observation`
- **原问题**：非外部副作用的核验/观察任务（Verification / Observation Task）无法仅凭现实世界 Observation 完成，因历史校验死板要求 Outcome 对象。
- **现行源码实现**：
  - `src/aios_core/execution/service.py`（L630-639）：
    ```python
    def _effective_completion_mode(self, task: Task) -> CompletionMode:
        explicit = _completion_mode_from_condition(task.completion_condition)
        if explicit is not None:
            return explicit
        if (
            task.task_type in {TaskType.VERIFICATION, TaskType.OBSERVATION}
            and not self._task_has_action_lineage(task.object_id)
        ):
            return "world_evidence"
        return "action_outcome"
    ```
  - L955-972：当 `mode == "world_evidence"` 时，允许且仅需真实世界证据引用 `evidence_refs`（如真实 Observation / Claim），不再强制要求外部 Action / Outcome。
- **实测证据**：
  - 运行专项测试：`pytest tests/integration/test_v3_execution_world.py -k "verification or t35"`
  - 结果：`2 passed in 0.49s`（100% PASS）
  - 验证点：`test_non_action_verification_task_completes_from_real_world_evidence` 确认验证任务凭平台与现实 Observation 顺利完成，终态 `completed`，`terminal_completion_mode="world_evidence"`。
- **裁决结论**：**RECONCILED / ALREADY FIXED IN MAIN**，正式关闭 Issue #35。

---

## 3. 终审裁决与状态跃迁

1. **五大历史工单全量收口**：
   - Issue #23：VERIFIED CLOSED
   - Issue #28：VERIFIED & RESOLVED (CLOSE)
   - Issue #33：VERIFIED & RESOLVED (CLOSE)
   - Issue #34：VERIFIED & RESOLVED (CLOSE)
   - Issue #35：VERIFIED & RESOLVED (CLOSE)
2. **零代码修改原则**：
   - 当前主干 `main` 机制健全，无任何需要重新修改或二次修补的缺陷，禁止无意义的重复施工。
3. **状态跃迁**：
   - `WINDOW 79 — POST-C15-ISSUE-RECONCILIATION-001` 标记 **`COMPLETE`**。
   - 正式放行后续 **C16 / 广泛长期居住与硬件交互演进**。
