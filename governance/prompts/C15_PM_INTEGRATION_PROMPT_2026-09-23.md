# PM 集成检查清单（允许原 PM 自审，无需新窗口）

> **历史检查清单：PR #122 已合入 `2a68df3f8901138fa3126a91063c430f69102049`，本治理任务已完成，勿重复开集成窗口。** 最新任务以 main 的顶部队列为准。

> 2026-09-24 流程纠正：本清单可由原 PM 在同一窗口执行；不再要求另开独立集成窗口。若由作者执行，必须明确称为 PM 自审，不冒称独立评审。真实盲测与明确要求的独立语义评估仍保留隔离。Operator preflight 必须等治理真正合入并写回后才能启动。

---

你是 AIOS v3.0 的治理集成 PM。本窗口只完成 **C15-RCC-RES-B-CORRECTIVE-001 的 GATE 审查与集成**，不做下一任务。

1. 遵守平台给定固定分支，不切换或推送其他分支。用 gh 获取实时 main 和纠偏治理 PR #122（来自 `arena/01a0cee4-haneof-aios-core-v3-0`），检查 exact head 和 diff。若有更新的 PM 裁决或其他窗口已接管，先报告冲突，禁止盲目套用旧指令。
2. 阅读该 PR 中的纠偏裁决、B 独立审查、地图、task board、checkpoint、风险登记及分角色提示词。确认只修改治理/文档/Resident-safe 指令；不改 Core、封存事件、历史 evidence、测试或工作流，不夹带动画 HTML/SQLite/凭据。
3. 复核 #121 @ `b6e5ac939bef83615292bcf9b9099d76737d82b0` 的原始证据与审查结论；可只读下载固定产物并重算 hash/查询 SQLite。无新 Claim 不是失败理由；关注正常 Runtime 运行链、B计量、行为证据、index 88 / World 97 的具体缺口。不要索取模型隐藏思维链。
4. 核查 #117 @ `3e51f728d7959048b75fea01d405bc837b0e8185` 未变；Core tree 与 `bcd6bf353126318f9a97076b52ec1740d43f35a4` 一致；旧 evidence 仍 OPEN/UNMERGED/PINNED。
5. 检查纠偏 PR 自己的 CI/范围证明。不要把 #120 的历史失败当本 PR 的失败，也不能忽略本 PR 的红灯。对红灯先取证：若是 Git/CI 基础设施问题，须有明确独立 scoped disposition 或修复/重跑后再合入；不批准 blanket waiver。不能把 fixture green 当 Resident PASS。
6. 确认 task board 中纠偏 = GATE、preflight = BLOCKED，且待写回前无实验授权。确认角色分离、Core freeze、canonical-A 恢复、无历史补写、可信模型身份和 C15/P16/P17 阻断都明确。
7. 若接受，记录你的实际审查身份和结论（作者执行则为 PM 自审）并按仓库权限/保护规则用 gh 合并**治理 PR**（不是 #117/#121 等证据 PR）。不要绕过保护规则/required checks；没有权限则明确等待维护者。
8. 实际合入后，从 GitHub 获取真实 merge SHA。在本会话平台固定分支上提交一个仅做集成收据和状态写回的治理变更：保存 PR/exact accepted head/merge SHA/CI run IDs；将 `C15-RCC-RES-B-CORRECTIVE-001` 从 GATE 改为 DONE，只有 `C15-RCC-RES-B-PREFLIGHT-001` 从 BLOCKED 改为 READY，同步地图顶部和 checkpoint。该写回按正常 review/CI 合入后才可向下交接。不得把未落 main 的收据写成已完成。
9. 若审查不接受，保留 GATE/后续 BLOCKED，列出具体整改，不自行跑 Resident 验证结论。

保持 #121 evidence immutable，可在 PR comment 中记录诊断处置，不改变证据 head。不能把任何 PM审查材料交给新的 blind Resident。

本窗口完成后停止。最终只交付：治理 PR/merge/CI/收据、main 最新状态、下一唯一 READY（如已释放）。不要执行 operator preflight、盲测、C 或终评。
