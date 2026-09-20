# AIOS v3.0 旧代码文件级迁移矩阵

> 源仓：`Haneof/fantonghui@aios-2.0`
>
> 冻结参考提交：`45ee43bbec2b46365d6105155766b9e7c9152af7`
>
> 目标仓：`Haneof/Haneof-AIOS-Core-v3.0`
>
> 依据：`AIOS_v3.0_Fused_Baseline_Registry.md`

## 一、范围

本矩阵覆盖旧仓 `src/` 下全部 **134 个 Python 文件**。它不是“整仓复制清单”，而是融合后第一轮工程迁移裁决。

状态统计：

- **A-直接迁移**：27
- **B-改造迁移**：28
- **C-合并重构**：18
- **D-测试资产保留**：18
- **E-移出Core/后置**：9
- **F-废弃/仅历史**：3
- **G-重新生成**：31

状态解释：

- **A-直接迁移**：确定性底座已与融合理念基本一致，允许先搬再补测试。
- **B-改造迁移**：核心能力有价值，但必须去除旧语义或接入统一世界。
- **C-合并重构**：不保持旧文件边界，抽取逻辑并入新的统一机制。
- **D-测试资产保留**：保留为负载、回归、场景素材或历史诊断，不进入生产认知链。
- **E-移出Core/后置**：硬件/UI/安全产品层，Core跑通后再接。
- **F-废弃/仅历史**：不得迁入生产Runtime。
- **G-重新生成**：包入口按新目录重新生成。

## 二、第一批可直接开工的迁移顺序

1. `contracts` + `storage` + `errors`：先恢复可运行世界内核。
2. `dependency` + `world`：恢复证据、版本、回溯和修正底座。
3. `query`：统一成 Intelligent World Index。
4. `runtime` + `ai_worker` + `cockpit`：统一 Cognitive Runtime 与 Context Controller。
5. `summaries`：拆成单维 Summary 与 ALL_DIMENSIONS World Projection。
6. `ingest/perception`：只保留机械整理和事实提取边界。
7. AI World / Goal / Task / Outcome：接世界写回与学习闭环。
8. 最后才迁硬件、UI、Wake 专属产品逻辑。

## 三、134 文件逐项裁决

| 旧文件 | 裁决 | 融合后去向 | 说明 |
|---|---|---|---|
| `src/ai_worker/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/ai_worker/cockpit_executor.py` | **C-合并重构** | `core/runtime/cognitive_runtime.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/ai_worker/cognitive_executor.py` | **C-合并重构** | `core/runtime/cognitive_runtime.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/ai_worker/context_pipeline.py` | **C-合并重构** | `core/context/controller.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/ai_worker/manifest_optimizer.py` | **C-合并重构** | `core/context/controller.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/ai_worker/stream_pipeline.py` | **C-合并重构** | `core/runtime/conversation_runtime.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/aios_core/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/actions/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/bench/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/bench/adversarial_life_bench.py` | **D-测试资产保留** | `tests/legacy_bench/` | 保留作负载/回归/历史诊断，不作为认知成立的证明。 |
| `src/aios_core/bench/blind_bench_cli.py` | **D-测试资产保留** | `tests/legacy_bench/` | 保留作负载/回归/历史诊断，不作为认知成立的证明。 |
| `src/aios_core/bench/blind_bench_cognition.py` | **D-测试资产保留** | `tests/legacy_bench/` | 保留作负载/回归/历史诊断，不作为认知成立的证明。 |
| `src/aios_core/bench/blind_bench_dialogue.py` | **D-测试资产保留** | `tests/legacy_bench/` | 保留作负载/回归/历史诊断，不作为认知成立的证明。 |
| `src/aios_core/bench/blind_bench_harness.py` | **D-测试资产保留** | `tests/legacy_bench/` | 保留作负载/回归/历史诊断，不作为认知成立的证明。 |
| `src/aios_core/bench/blind_bench_metrics.py` | **D-测试资产保留** | `tests/legacy_bench/` | 保留作负载/回归/历史诊断，不作为认知成立的证明。 |
| `src/aios_core/bench/blind_bench_results.py` | **D-测试资产保留** | `tests/legacy_bench/` | 保留作负载/回归/历史诊断，不作为认知成立的证明。 |
| `src/aios_core/bench/g_m1p.py` | **D-测试资产保留** | `tests/legacy_bench/` | 保留作负载/回归/历史诊断，不作为认知成立的证明。 |
| `src/aios_core/bench/tool_catalog.py` | **D-测试资产保留** | `tests/legacy_bench/` | 保留作负载/回归/历史诊断，不作为认知成立的证明。 |
| `src/aios_core/cockpit/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/cockpit/mind_order_manifest.py` | **C-合并重构** | `core/context/controller.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/aios_core/cockpit/pipeline.py` | **C-合并重构** | `core/context/controller.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/aios_core/cognition/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/cognition/cognitive_dimension_gate.py` | **F-废弃/仅历史** | `—` | 核心语义依赖固定维度/固定认知门槛/关键词模板；不进入正式Runtime。 |
| `src/aios_core/cognition/communication_style_governor.py` | **A-直接迁移** | `core/ai_world/communication_feedback.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/cognition/dependency_isolator.py` | **C-合并重构** | `core/revision/propagation.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/aios_core/cognition/dimension_engine.py` | **F-废弃/仅历史** | `—` | 核心语义依赖固定维度/固定认知门槛/关键词模板；不进入正式Runtime。 |
| `src/aios_core/cognition/event_resonance.py` | **B-改造迁移** | `core/events/candidate_alignment.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/cognition/evidence_grounded_advisor.py` | **C-合并重构** | `core/runtime/cognitive_runtime.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/aios_core/cognition/goal_inference.py` | **B-改造迁移** | `core/goals/inferred_goal_writeback.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/cognition/life_chapter_detector.py` | **B-改造迁移** | `core/cognition/life_phase_candidates.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/cognition/mind_sequence.py` | **C-合并重构** | `core/context/controller.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/aios_core/cognition/model_call_meter.py` | **A-直接迁移** | `core/telemetry/model_call_meter.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/cognition/nightly_review_runner.py` | **B-改造迁移** | `core/review/periodic_review.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/cognition/operation_experience.py` | **B-改造迁移** | `core/ai_world/operation_experience.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/cognition/symbiotic_advisor.py` | **C-合并重构** | `core/runtime/cognitive_runtime.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/aios_core/communication/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/communication/experience_tracker.py` | **A-直接迁移** | `core/ai_world/communication_experience.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/communication/persona_guard.py` | **A-直接迁移** | `core/runtime/output_protocol_guard.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/contracts/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/contracts/base.py` | **A-直接迁移** | `core/contracts/base.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/contracts/enums.py` | **A-直接迁移** | `core/contracts/enums.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/contracts/errors.py` | **A-直接迁移** | `core/contracts/errors.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/contracts/ids.py` | **A-直接迁移** | `core/contracts/ids.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/contracts/models.py` | **B-改造迁移** | `core/contracts/world_objects.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/contracts/operations.py` | **A-直接迁移** | `core/contracts/operations.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/contracts/refs.py` | **A-直接迁移** | `core/contracts/refs.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/contracts/registry.py` | **A-直接迁移** | `core/contracts/registry.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/contracts/safety_bypass.py` | **B-改造迁移** | `platform/safety/contracts.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/contracts/time.py` | **A-直接迁移** | `core/contracts/time.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/curves/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/curves/dimension_curve.py` | **B-改造迁移** | `core/projections/dimension_curve.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/dependency/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/dependency/graph.py` | **A-直接迁移** | `core/dependency/graph.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/dimensions/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/dimensions/evolution_guard.py` | **B-改造迁移** | `core/dimensions/lifecycle.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/errors.py` | **A-直接迁移** | `core/errors.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/ingest/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/ingest/edge_stream_purifier.py` | **B-改造迁移** | `core/ingest/mechanical_cleaner.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/ingest/multimodal_edge.py` | **B-改造迁移** | `core/ingest/multimodal_adapter.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/ingest/universal_edge_purifier.py` | **F-废弃/仅历史** | `—` | 核心语义依赖固定维度/固定认知门槛/关键词模板；不进入正式Runtime。 |
| `src/aios_core/narrative/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/narrative/segmenter.py` | **B-改造迁移** | `core/cognition/life_phase_candidates.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/operations/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/operations/world_operator.py` | **B-改造迁移** | `core/world/writeback_operator.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/perception/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/perception/edge_cleaner.py` | **C-合并重构** | `core/ingest/mechanical_cleaner.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/aios_core/perception/edge_stream_purifier.py` | **C-合并重构** | `core/ingest/mechanical_cleaner.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/aios_core/query/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/query/cjk_inverted_index.py` | **A-直接迁移** | `core/index/lexical.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/query/cooccurrence_recall_bus.py` | **B-改造迁移** | `core/index/cooccurrence.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/query/history.py` | **A-直接迁移** | `core/index/history.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/query/hot_cards.py` | **B-改造迁移** | `core/index/ranking_signals.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/query/hyperlink_traverser.py` | **A-直接迁移** | `core/index/graph_traversal.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/query/search.py` | **A-直接迁移** | `core/index/world_index.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/runtime/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/runtime/ai_self_world.py` | **B-改造迁移** | `core/ai_world/world_objects.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/runtime/capabilities.py` | **A-直接迁移** | `core/runtime/capabilities.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/runtime/cognitive_runtime.py` | **B-改造迁移** | `core/runtime/cognitive_runtime.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/runtime/conversation_state.py` | **A-直接迁移** | `core/runtime/conversation_state.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/runtime/conversation_timeline.py` | **A-直接迁移** | `core/runtime/conversation_timeline.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/runtime/policy_registry.py` | **A-直接迁移** | `core/policy/registry.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/runtime/state_capabilities.py` | **A-直接迁移** | `core/runtime/state_capabilities.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/runtime/world_capabilities.py` | **A-直接迁移** | `core/runtime/world_capabilities.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/scheduler/conditional_engine.py` | **B-改造迁移** | `core/tasks/scheduler.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/services/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/services/state_machines.py` | **A-直接迁移** | `core/state_machines.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/simulation/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/simulation/adversarial_life_bench.py` | **D-测试资产保留** | `tests/habitation/legacy_reference/` | 保留对抗场景/诊断素材，重写为多Agent入住测试后再使用。 |
| `src/aios_core/simulation/blind_bench_diagnostics.py` | **D-测试资产保留** | `tests/habitation/legacy_reference/` | 保留对抗场景/诊断素材，重写为多Agent入住测试后再使用。 |
| `src/aios_core/simulation/blind_bench_harness.py` | **D-测试资产保留** | `tests/habitation/legacy_reference/` | 保留对抗场景/诊断素材，重写为多Agent入住测试后再使用。 |
| `src/aios_core/simulation/cleaning_arena_protocol.py` | **D-测试资产保留** | `tests/habitation/legacy_reference/` | 保留对抗场景/诊断素材，重写为多Agent入住测试后再使用。 |
| `src/aios_core/simulation/cognitive_arena_protocol.py` | **D-测试资产保留** | `tests/habitation/legacy_reference/` | 保留场景Schema参考；固定答案/关键词判卷退出认知Gate。 |
| `src/aios_core/simulation/headless_life_driver.py` | **C-合并重构** | `tests/habitation/load_driver.py` | 保留长期人生流、WorldStore负载与重放；删除PseudoLLM认知证明角色。 |
| `src/aios_core/simulation/massive_life_bench.py` | **D-测试资产保留** | `tests/load/` | 用于世界存储、索引、吞吐与资源压测，不用于认知PASS。 |
| `src/aios_core/simulation/massive_life_store_feeder.py` | **D-测试资产保留** | `tests/load/` | 用于世界存储、索引、吞吐与资源压测，不用于认知PASS。 |
| `src/aios_core/storage/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/storage/idempotency.py` | **A-直接迁移** | `core/storage/idempotency.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/storage/sqlite_store.py` | **A-直接迁移** | `core/storage/sqlite_store.py` | 确定性底座或R5/R6已对齐能力；迁移后补新契约测试。 |
| `src/aios_core/summaries/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/summaries/pyramid_aggregator.py` | **B-改造迁移** | `core/summaries/pyramid.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/summaries/universal_time_summarizer.py` | **B-改造迁移** | `core/summaries/dimension_summary.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/tasks/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/tools/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/tools/adaptive_temporal_compressor.py` | **B-改造迁移** | `core/ingest/temporal_compressor.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/tools/conditional_event_evaluator.py` | **C-合并重构** | `core/tasks/condition_evaluator.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/aios_core/tools/dual_lens_index_projector.py` | **B-改造迁移** | `core/world/temporal_projection.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/tools/dual_lens_projection_index.py` | **B-改造迁移** | `core/world/temporal_projection_index.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/tools/lightweight_condition_evaluator.py` | **C-合并重构** | `core/tasks/condition_evaluator.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/aios_core/tools/multiscale_crystal_index.py` | **B-改造迁移** | `core/index/summary_index.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/tools/proposal_pipeline.py` | **C-合并重构** | `core/dimensions/proposal.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/aios_core/tools/proposed_operators.py` | **C-合并重构** | `core/dimensions/proposal.py` | 不保留一文件一职责的历史形态；抽取有价值逻辑进入融合机制。 |
| `src/aios_core/tools/resonance_synthesizer.py` | **B-改造迁移** | `core/events/candidate_alignment.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/wake/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/wake/cooldown_queue.py` | **E-移出Core/后置** | `platform/attention/cooldown_queue.py` | 有产品/硬件价值，但不应阻塞Core第一版；安全逻辑后续单独审计适配。 |
| `src/aios_core/wake/dispatcher.py` | **E-移出Core/后置** | `platform/wake/dispatcher.py` | 有产品/硬件价值，但不应阻塞Core第一版；安全逻辑后续单独审计适配。 |
| `src/aios_core/wake/emergency_judge.py` | **E-移出Core/后置** | `platform/safety/emergency_flow.py` | 有产品/硬件价值，但不应阻塞Core第一版；安全逻辑后续单独审计适配。 |
| `src/aios_core/wake/v22_hardware_first.py` | **E-移出Core/后置** | `platform/safety/hardware_first.py` | 有产品/硬件价值，但不应阻塞Core第一版；安全逻辑后续单独审计适配。 |
| `src/aios_core/wearable/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/wearable/fsm.py` | **E-移出Core/后置** | `platform/wearable/` | 特定手环硬件实现移出Core，待手机/硬件阶段再适配。 |
| `src/aios_core/wearable/hal_interface.py` | **E-移出Core/后置** | `platform/wearable/` | 特定手环硬件实现移出Core，待手机/硬件阶段再适配。 |
| `src/aios_core/workspace/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/world/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/aios_core/world/epistemic_world_lens.py` | **B-改造迁移** | `core/world/epistemic_views.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/world/retrospective_annotation.py` | **B-改造迁移** | `core/world/retrospective_annotation.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/aios_core/world/view_lens.py` | **B-改造迁移** | `core/world/view_lens.py` | 保留工程能力，删除硬编码认知/平行真相库/越权语义并接入统一世界。 |
| `src/console/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/console/app_manifest.py` | **E-移出Core/后置** | `platform/ui/` | 旧手环/UI产品层，不进入第一版Core跑通链。 |
| `src/console/wearable_ui/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/console/wearable_ui/layout_simulator.py` | **E-移出Core/后置** | `platform/ui/` | 旧手环/UI产品层，不进入第一版Core跑通链。 |
| `src/console/wearable_ui/three_tier_ui.py` | **E-移出Core/后置** | `platform/ui/` | 旧手环/UI产品层，不进入第一版Core跑通链。 |
| `src/evaluator/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/evaluator/audit_evaluator_entry.py` | **D-测试资产保留** | `tests/tools/` | 历史入口保留作工具参考，入住测试框架会重建入口。 |
| `src/simulator/__init__.py` | **G-重新生成** | `对应新包入口` | 不复制历史导出列表；按融合后的目录重新生成。 |
| `src/simulator/life_simulator_entry.py` | **D-测试资产保留** | `tests/tools/` | 历史入口保留作工具参考，入住测试框架会重建入口。 |

## 四、三类高风险迁移

### 4.1 认知越权

任何旧代码若通过关键词、固定标签、固定心理维度、固定阈值或固定人生模板直接得出高阶认知，迁移时必须删除该决策权。程序可生成候选和证据，最终认知交给真实模型。

### 4.2 第二真相库

`ai_self_world.py` 的 identity、relationship、reflection、experience 等内容保留，但不得继续维护独立于统一 WorldStore 的 AI Self 真相库。

### 4.3 伪认知测试

旧 bench/simulation 中的 PseudoLLM、关键词判卷、expected causal chain 等只能保留为机械回归或场景资产。正式认知 Gate 必须使用多Agent长期入住与隐藏人生。

## 五、首个工程 Gate

在迁移任何高阶认知模块之前，必须先跑通：

```text
Observation / Conversation
↓
WorldObject contract
↓
SQLiteWorldStore.commit
↓
world_revision
↓
restart / historical read
↓
WorldSearchIndex catch-up
↓
世界对象可被重新检索
```

这条链通过后，再接真实模型。否则禁止用上层Agent测试掩盖底层世界不稳定。
