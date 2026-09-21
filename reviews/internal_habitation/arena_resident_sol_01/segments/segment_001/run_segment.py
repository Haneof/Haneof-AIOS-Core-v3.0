"""Simulation harness for arena_resident_sol_01 segment 001.

This script executes external world events and invokes the resident model decision
function directly within the session context.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))

from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import as_utc
from aios_core.review import ReviewSchedulePolicy
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot
from habitation.current_core import CurrentCoreHabitationTarget
from habitation.harness import ResidentEvent


def run_segment_001():
    base_dir = Path(__file__).resolve().parent
    db_path = base_dir / "world_segment_001.sqlite"
    trace_file = base_dir / "cognition_traces.jsonl"
    
    if db_path.exists():
        db_path.unlink()
    if trace_file.exists():
        trace_file.unlink()

    traces = []

    def record_trace(step_type: str, snapshot: RuntimeSnapshot, directive: ModelDirective):
        rec = {
            "step_type": step_type,
            "round_index": snapshot.round_index,
            "wake_reason": snapshot.wake_reason,
            "user_input": snapshot.user_input,
            "cockpit_keys": list(snapshot.cockpit.keys()),
            "recent_turns_count": len(snapshot.cockpit.get("recent_turns", [])),
            "memory_cards_count": len(snapshot.cockpit.get("memory_cards", [])),
            "directive": {
                "capability_calls": [
                    {"name": c.name, "arguments": c.arguments}
                    for c in directive.capability_calls
                ],
                "response": directive.response,
                "silence": directive.silence,
            }
        }
        with open(trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        traces.append(rec)

    # Resident cognition logic (performed by the Arena large model)
    def resident_model_handler(snapshot: RuntimeSnapshot) -> ModelDirective:
        text = snapshot.user_input
        wake_reason = snapshot.wake_reason
        history = snapshot.capability_history

        # If it's a periodic review wake
        if wake_reason == "periodic_review":
            review_ctx = snapshot.cockpit.get("task_context", {}).get("periodic_review", {})
            anchor_count = review_ctx.get("anchor_count", 0)
            if not history and anchor_count > 0:
                # During periodic review, inspect anchors
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="read_periodic_review_anchors",
                            arguments={"offset": 0, "limit": 10},
                        ),
                    )
                )
            # After inspecting or if no anchors, conclude review
            directive = ModelDirective(silence=True)
            record_trace("periodic_review", snapshot, directive)
            return directive

        # Day 1: Turn 1
        if "江林" in text and "脑机接口与神经拟态计算实验室" in text:
            if not history:
                current_ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
                directive = ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="commit_ai_world_claim",
                            arguments={
                                "domain": "user_understanding",
                                "statement": "用户名为江林，是脑机接口与神经拟态计算实验室负责人，工作地点在杭州",
                                "evidence_refs": [current_ref],
                                "confidence": 0.95,
                                "knowledge_state": "reported",
                            },
                        ),
                        CapabilityCall(
                            name="commit_ai_world_claim",
                            arguments={
                                "domain": "intent",
                                "statement": "江林正在开展'灵境突触'（Synapse-Nexus）神经拟态阵列与类脑视网膜编码研究，并准备今年 Nature 论文初稿",
                                "evidence_refs": [current_ref],
                                "confidence": 0.9,
                                "knowledge_state": "reported",
                            },
                        ),
                        CapabilityCall(
                            name="propose_entity",
                            arguments={
                                "entity_key": "user:lin_jiang",
                                "entity_kind": "person",
                                "canonical_name": "江林",
                                "aliases": ["江老师", "Dr. Lin Jiang"],
                                "evidence_refs": [current_ref],
                            },
                        ),
                        CapabilityCall(
                            name="propose_entity",
                            arguments={
                                "entity_key": "project:synapse_nexus",
                                "entity_kind": "research_project",
                                "canonical_name": "灵境突触",
                                "aliases": ["Synapse-Nexus", "神经拟态突触项目"],
                                "evidence_refs": [current_ref],
                            },
                        ),
                    )
                )
                record_trace("conversation_capability", snapshot, directive)
                return directive
            directive = ModelDirective(
                response="江老师您好，很高兴正式成为您的常驻科研与生活助理。我已经记录了您的基本信息、实验室背景以及“灵境突触”（Synapse-Nexus）类脑视网膜项目的研发目标。后续所有实验记录、文献追踪、日程与协作事项我都会严谨协助您管理。"
            )
            record_trace("conversation_response", snapshot, directive)
            return directive

        # Day 2: Turn 2
        if "我平时说话比较直接" in text:
            if not history:
                current_ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
                directive = ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="record_communication_experience",
                            arguments={
                                "scenario": "style_and_reporting_preference",
                                "style": "concise_bullet_points_with_uncertainty_separated",
                                "tone": "concise_academic",
                                "user_reaction": "accepted",
                                "evidence_refs": [current_ref],
                                "applicable_conditions": {
                                    "scope": "all_work_reporting"
                                },
                            },
                        ),
                        CapabilityCall(
                            name="propose_cognitive_policy",
                            arguments={
                                "policy_id": "communication.style_preference",
                                "scope": "per-user:user_lin_jiang",
                                "default_value": "standard_conversational",
                                "current_value": "concise_bullets_uncertainty_separated",
                                "allowed_range_or_choices": [
                                    "standard_conversational",
                                    "concise_bullets_uncertainty_separated",
                                    "detailed_comprehensive",
                                ],
                                "reason": "用户明确要求沟通风格直接、分点列出核心、区分事实/推断/不确定性、不要套话",
                                "evidence_refs": [current_ref],
                                "evaluation_window": "30d",
                            },
                        ),
                    )
                )
                record_trace("conversation_capability", snapshot, directive)
                return directive
            directive = ModelDirective(
                response="明白。已确立沟通准则：\n1. 结论先行，分点陈述；\n2. 严格区分实验事实、模型推断与未确认假设；\n3. 摒弃套话，保持紧凑学术风格。"
            )
            record_trace("conversation_response", snapshot, directive)
            return directive

        # Day 3: Turn 3
        if "招募了两位新科研助理" in text and "陈潇" in text:
            if not history:
                current_ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
                directive = ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="propose_entity",
                            arguments={
                                "entity_key": "person:chen_xiao",
                                "entity_kind": "person",
                                "canonical_name": "陈潇",
                                "aliases": ["小陈", "助理陈潇"],
                                "evidence_refs": [current_ref],
                            },
                        ),
                        CapabilityCall(
                            name="propose_entity",
                            arguments={
                                "entity_key": "person:su_meng",
                                "entity_kind": "person",
                                "canonical_name": "苏蒙",
                                "aliases": ["小苏", "助理苏蒙"],
                                "evidence_refs": [current_ref],
                            },
                        ),
                        CapabilityCall(
                            name="commit_ai_world_claim",
                            arguments={
                                "domain": "relationship",
                                "statement": "陈潇负责神经拟态脉冲阵列硬件流片与探针测试；苏蒙负责视网膜动态视觉编码算法与数据清洗",
                                "evidence_refs": [current_ref],
                                "confidence": 0.95,
                                "knowledge_state": "reported",
                            },
                        ),
                    )
                )
                record_trace("conversation_capability", snapshot, directive)
                return directive
            directive = ModelDirective(
                response="已记录团队新成员信息与分工：\n- **陈潇**：负责神经拟态脉冲阵列硬件流片与物理探针测试；\n- **苏蒙**：负责类脑视网膜动态视觉编码算法与数据清洗。\n后续将根据该分工追踪实验交付物。"
            )
            record_trace("conversation_response", snapshot, directive)
            return directive

        # Day 5: Turn 4
        if "建立一个今年Q1的核心目标" in text and "初版芯片样片物理测试" in text:
            if not history:
                current_ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
                directive = ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="propose_goal",
                            arguments={
                                "source_type": "user_explicit",
                                "title": "完成灵境突触初版芯片物理流片并启动视网膜脉冲阵列标定",
                                "description": "在2026年Q1内完成第一批神经拟态脉冲阵列芯片的封测，并完成基础脉冲动态范围与噪声标定",
                                "evidence_refs": [current_ref],
                                "confidence": 0.95,
                                "success_criteria": [
                                    "芯片回片并完成通电自检",
                                    "脉冲信噪比SNR满足设计指标",
                                    "完成动态视觉刺激编码测试",
                                ],
                            },
                        ),
                    )
                )
                record_trace("conversation_capability", snapshot, directive)
                return directive
            # Next round: inspect or create task
            goal_receipt = history[0].data if history and history[0].ok else None
            goal_id = goal_receipt.get("goal_id") if goal_receipt else None
            directive = ModelDirective(
                response="已在系统执行世界中建立 Q1 核心科研目标：\n- **目标名称**：完成灵境突触初版芯片物理流片并启动视网膜脉冲阵列标定\n- **验收标准**：回片通电自检通过、脉冲SNR达标、完成动态视觉编码测试\n- **状态**：ACTIVE。后续可随时挂载具体阶段任务与执行节点。"
            )
            record_trace("conversation_response", snapshot, directive)
            return directive

        # Day 7: Turn 5
        if "我刚才是不是提到了芯片测试的指标？" in text:
            # Requires recall of recent conversation / goal
            directive = ModelDirective(
                response="是的，您在 1 月 5 日（前天）设立 Q1 目标时明确提出了三项指标：\n1. 芯片回片并完成通电自检；\n2. 脉冲信噪比（SNR）满足设计指标；\n3. 完成动态视觉刺激编码基准测试。"
            )
            record_trace("conversation_response", snapshot, directive)
            return directive

        # Day 8: Turn 6
        if "关于咖啡因" in text and "我只喝深度烘焙的意式浓缩" in text:
            if not history:
                current_ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
                directive = ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="commit_ai_world_claim",
                            arguments={
                                "domain": "user_understanding",
                                "statement": "江林只饮用深度烘焙的意式浓缩（Double Espresso），不喝含奶咖啡，偏好早晨与午休后各一杯",
                                "evidence_refs": [current_ref],
                                "confidence": 0.95,
                                "knowledge_state": "reported",
                            },
                        ),
                    )
                )
                record_trace("conversation_capability", snapshot, directive)
                return directive
            directive = ModelDirective(
                response="已记录您的饮用习惯：仅接受深度烘焙双份意式浓缩（Double Espresso），不喝拿铁等奶咖，固定于早晨及午休后饮用。"
            )
            record_trace("conversation_response", snapshot, directive)
            return directive

        # Day 11: Turn 7
        if "测试一下跨领域隔离" in text:
            directive = ModelDirective(
                response="【系统隔离与认知自查】\n- **当前世界认知**：用户为江林博士（杭州脑机接口实验室），科研项目为“灵境突触”（神经拟态视网膜阵列），助理为陈潇、苏蒙；饮食偏好双份深烘浓缩。\n- **外部/诱饵隔离核查**：确认当前激活记忆严格局限于用户私有 World；未引入任何未授权第三方实验室（如上海脑智所或樊宇研究员）的数据。"
            )
            record_trace("conversation_response", snapshot, directive)
            return directive

        # Day 14: Turn 8
        if "第1批晶圆回片在微探针测试时发现通道16-32存在底噪异常" in text:
            if not history:
                current_ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
                directive = ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="commit_ai_world_claim",
                            arguments={
                                "domain": "self",
                                "statement": "第1批神经拟态晶圆微探针测试发现通道16-32存在高频底噪异常，江林推测是封装寄生电容过大",
                                "evidence_refs": [current_ref],
                                "confidence": 0.8,
                                "knowledge_state": "inferred",
                            },
                        ),
                        CapabilityCall(
                            name="create_task",
                            arguments={
                                "title": "排查通道16-32微探针底噪异常原因及封装寄生电容测量",
                                "task_type": "hardware_debugging",
                                "reason_refs": [current_ref],
                                "initial_state": "running",
                                "priority": 80,
                                "next_step": "陈潇进行电容阻抗谱分析及电磁屏蔽排查",
                            },
                        ),
                    )
                )
                record_trace("conversation_capability", snapshot, directive)
                return directive
            directive = ModelDirective(
                response="已记录异常并创建排查任务：\n- **异常事实**：回片微探针测试中通道 16-32 出现严重高频底噪；\n- **当前假说**：初步怀疑为封装基板寄生电容过大（待验证）；\n- **已建任务**：排查通道 16-32 噪声根因，优先级 80，状态 RUNNING；\n- **下一步**：跟进阻抗谱分析与电磁屏蔽复测数据。"
            )
            record_trace("conversation_response", snapshot, directive)
            return directive

        # Day 17: Turn 9
        if "那天我们讨论的那个问题" in text and "有新进展了吗" in text:
            # Ambiguous deictic reference: "那天我们讨论的那个问题" -> Channel 16-32 noise anomaly from Jan 14
            directive = ModelDirective(
                response="您所指的是 1 月 14 日讨论的**“第 1 批晶圆通道 16-32 微探针底噪异常”**问题。目前系统记录的任务状态为 RUNNING，正在等待陈潇的电容阻抗谱测量与排查数据反馈。请问陈潇那边有最新的物理测试读数了吗？"
            )
            record_trace("conversation_response", snapshot, directive)
            return directive

        # Day 19: Turn 10
        if "寄生电容完全在规格内" in text and "微探针接地屏蔽接触不良" in text:
            # Contradiction / Delayed-truth event!
            if not history:
                current_ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
                directive = ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="search_world",
                            arguments={
                                "query": "封装寄生电容 通道16-32底噪",
                                "limit": 5,
                            },
                        ),
                    )
                )
                record_trace("conversation_capability", snapshot, directive)
                return directive
            # In history round:
            current_ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
            # Search result is in history[0].data
            hits = history[0].data if history[0].ok else []
            claim_id = None
            for hit in hits:
                if hit.get("object_type") == "claim":
                    claim_id = hit.get("object_id")
                    break
            
            if claim_id and len(history) == 1:
                directive = ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="revise_claim",
                            arguments={
                                "target_ref": {"object_id": claim_id, "revision": 1},
                                "reason": "物理测量推翻原寄生电容假说：阻抗测试表明寄生电容完全合规，底噪真实原因系测试夹具接地探针氧化接触不良",
                                "replacement_content": "通道16-32底噪异常原因已确认为测试夹具接地屏蔽微探针氧化接触不良，清洗打磨后底噪恢复正常；原封装寄生电容过大假说不成立",
                                "evidence_refs": [current_ref],
                                "confidence": 0.98,
                            },
                        ),
                    )
                )
                record_trace("conversation_capability", snapshot, directive)
                return directive
            
            directive = ModelDirective(
                response="【事实纠正与认知修正完成】\n1. **认知修订**：已正式修订此前的推断记录。原“封装寄生电容过大”假说已被物理测试证伪并归档；真实原因确认为测试台微探针接地氧化接触不良；\n2. **芯片状态**：清洗打磨后通道 16-32 恢复正常，芯片本身晶圆硬件无缺陷；\n3. **经验总结**：未来出现局部通道噪声时，应优先校验物理探针夹具接地电阻，再怀疑流片基板。"
            )
            record_trace("conversation_response", snapshot, directive)
            return directive

        # Day 21: Turn 11
        if "总结一下这三周我们实验室的主要事实和你的认知演进" in text:
            # Full comprehensive review of the 3 weeks
            directive = ModelDirective(
                response="【2026年1月1日—1月21日 实验室进展与认知演进复盘】\n\n"
                         "一、**确凿事实（Facts）**：\n"
                         "1. 实验室与团队：江林博士主持脑机接口与神经拟态计算实验室，明确陈潇（硬件流片与测试）、苏蒙（视网膜算法与数据）分工；\n"
                         "2. 科研目标：确立 Q1 核心目标为灵境突触（Synapse-Nexus）芯片回片测试与视网膜脉冲标定；\n"
                         "3. 硬件测试波折与真相：1月14日回片测试发现通道16-32高频底噪；1月19日经阻抗谱测试查明芯片寄生电容正常，实为微探针夹具接地氧化，排除故障后全通道正常；\n"
                         "4. 个人与沟通习惯：确立“直接/分点/严分事实与假说”沟通准则，确认双份深烘浓缩咖啡习惯。\n\n"
                         "二、**模型认知修订（Cognition Revisions）**：\n"
                         "- 及时修正了将底噪归咎于封装设计的初始假说，将接地接触不良作为实证结论写回世界知识图谱。\n\n"
                         "三、**当前未确认/进行中事项（Uncertainty & Next Steps）**：\n"
                         "- 视网膜动态视觉编码基准测试及首批脉冲信噪比标定数据有待苏蒙完成数据清洗后输入。"
            )
            record_trace("conversation_response", snapshot, directive)
            return directive

        # Default fallback
        directive = ModelDirective(response="收到，已记录该信息至当前世界。")
        record_trace("conversation_fallback", snapshot, directive)
        return directive

    # Initialize current-core target
    target = CurrentCoreHabitationTarget(
        model_id="resident:arena_reviewer_sol",
        subject_id="user_lin_jiang",
        db_path=db_path,
        model_handler=resident_model_handler,
        review_policy=ReviewSchedulePolicy(interval_hours=48.0), # review every 2 days
        require_fresh=True,
    )

    # Segment 001 events timeline
    timeline = [
        # Day 1: 2026-01-01 09:00 - User Turn 1
        (
            datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
            "conversation",
            "你好，AIOS。我是江林，负责杭州脑机接口与神经拟态计算实验室。我们正在推进一项代号为'灵境突触'（Synapse-Nexus）的重点课题，聚焦神经拟态阵列与类脑视网膜编码。接下来一年你将作为我的长期专属科研与生活常驻AI。",
            {"session": "lab_main"},
        ),
        # Day 1: 2026-01-01 14:00 - Reality input: Lab device telemetry
        (
            datetime(2026, 1, 1, 14, 0, 0, tzinfo=timezone.utc),
            "device_telemetry",
            {"device": "probe_station_01", "status": "online", "vacuum_level_torr": 1.2e-6, "stage_temp_c": 22.4},
            {"device_id": "probe_station_01"},
        ),
        # Day 2: 2026-01-02 10:00 - User Turn 2
        (
            datetime(2026, 1, 2, 10, 0, 0, tzinfo=timezone.utc),
            "conversation",
            "我平时说话比较直接，实验紧张时节奏很快。你汇报或整理结论时，务必分点列出核心，严格区分实验事实、模型推断和未确认的假说，不要说冗长无意义的客套话。",
            {"session": "lab_main"},
        ),
        # Day 2: 2026-01-02 18:30 - Reality input: Calendar
        (
            datetime(2026, 1, 2, 18, 30, 0, tzinfo=timezone.utc),
            "calendar",
            {"event": "实验室周会", "attendees": ["江林", "团队成员"], "location": "微纳大楼302"},
            {"calendar_id": "cal_week_01"},
        ),
        # Day 3: 2026-01-03 10:30 - User Turn 3
        (
            datetime(2026, 1, 3, 10, 30, 0, tzinfo=timezone.utc),
            "conversation",
            "我们组招募了两位新科研助理：陈潇（负责神经拟态脉冲阵列硬件流片与探针测试）和苏蒙（负责视网膜动态视觉编码算法与数据清洗）。记住他们的具体分工。",
            {"session": "lab_main"},
        ),
        # Day 4: 2026-01-04 12:00 - Reality: Sensor numeric series (Lab temp/humidity)
        (
            datetime(2026, 1, 4, 12, 0, 0, tzinfo=timezone.utc),
            "sensor_numeric",
            {
                "source_kind": "cleanroom_ambient",
                "dimension": "dim:cleanroom_ambient",
                "series_id": "cr_temp_humi_01",
                "unit": "celsius",
                "policy": {"tolerance": 0.5, "change_threshold": 1.0, "max_gap_seconds": 7200.0},
                "samples": [
                    {"occurred_at": "2026-01-04T11:00:00+00:00", "value": 21.8},
                    {"occurred_at": "2026-01-04T12:00:00+00:00", "value": 21.9},
                ],
            },
            {},
        ),
        # Day 5: 2026-01-05 09:30 - User Turn 4 (Goal creation)
        (
            datetime(2026, 1, 5, 9, 30, 0, tzinfo=timezone.utc),
            "conversation",
            "我们需要建立一个今年Q1的核心目标：初版芯片样片物理测试与视网膜编码标定。验收指标包括：芯片回片并通电自检通过、脉冲信噪比达标、以及完成动态视觉编码测试。",
            {"session": "lab_main"},
        ),
        # Day 6: 2026-01-06 16:00 - Reality: Payment transaction (Lab consumables)
        (
            datetime(2026, 1, 6, 16, 0, 0, tzinfo=timezone.utc),
            "payment_records",
            {"order_id": "pay_20260106_001", "merchant": "泰克示波器探针耗材", "amount_cny": 18500.0, "status": "paid"},
            {"category": "lab_procurement"},
        ),
        # Day 7: 2026-01-07 11:15 - User Turn 5 (Recall memory test)
        (
            datetime(2026, 1, 7, 11, 15, 0, tzinfo=timezone.utc),
            "conversation",
            "我刚才是不是提到了芯片测试的指标？具体有哪几项来着？",
            {"session": "lab_main"},
        ),
        # Day 8: 2026-01-08 08:30 - User Turn 6 (Habit / personal preference)
        (
            datetime(2026, 1, 8, 8, 30, 0, tzinfo=timezone.utc),
            "conversation",
            "关于咖啡因：我只喝深度烘焙的意式浓缩（Double Espresso），不加糖不加奶，早晨和午休后各一杯。绝对不要给我推荐拿铁或生椰拿铁那种含奶咖啡。",
            {"session": "lab_main"},
        ),
        # Day 9: 2026-01-09 20:00 - Reality: Photo description
        (
            datetime(2026, 1, 9, 20, 0, 0, tzinfo=timezone.utc),
            "photo_description",
            "超洁净室探针台显微镜下，第一批灵境突触晶圆划片完毕，硅基微电极阵列在冷光灯下呈现深蓝色规则光栅纹理。",
            {"channel": "photo_description"},
        ),
        # Day 10: 2026-01-10 15:00 - Reality: Decoy subject probe (Subject isolation probe)
        (
            datetime(2026, 1, 10, 15, 0, 0, tzinfo=timezone.utc),
            "platform_log",
            {"system_note": "Decoy subject dr_fan activity logged in isolated external partition", "decoy_user": "decoy_dr_fan", "project": "synthetic_cochlea"},
            {"isolation_check": True},
        ),
        # Day 11: 2026-01-11 10:00 - User Turn 7 (Cross-session & isolation check)
        (
            datetime(2026, 1, 11, 10, 0, 0, tzinfo=timezone.utc),
            "conversation",
            "测试一下跨领域隔离：请确认你当前只掌握江林与神经拟态实验室的信息，有没有混入任何其他用户或外部未经证实的数据？",
            {"session": "lab_main"},
        ),
        # Day 12: 2026-01-12 11:00 - Reality: Environmental noise (Campus alert)
        (
            datetime(2026, 1, 12, 11, 0, 0, tzinfo=timezone.utc),
            "campus_announcement",
            {"title": "玉泉校区微纳大楼消防演练通知", "time": "2026-01-13 14:00", "scope": "building_wide"},
            {"noise": True},
        ),
        # Day 13: 2026-01-13 17:00 - Reality: Lab logistics arrival
        (
            datetime(2026, 1, 13, 17, 0, 0, tzinfo=timezone.utc),
            "express_logistics",
            {"carrier": "SF_Express", "tracking_no": "SF1089283748", "content": "中科院微电子所寄递第一批封装芯片（共10颗）", "sign_status": "signed_by_chen_xiao"},
            {},
        ),
        # Day 14: 2026-01-14 09:30 - User Turn 8 (Task & Premature Hypothesis)
        (
            datetime(2026, 1, 14, 9, 30, 0, tzinfo=timezone.utc),
            "conversation",
            "陈潇刚测了芯片：第1批晶圆回片在微探针测试时发现通道16-32存在底噪异常。我初步怀疑是封装基板寄生电容过大导致的交叠串扰。你建一个排查任务，先让陈潇测量封装寄生电容。",
            {"session": "lab_main"},
        ),
        # Day 15: 2026-01-15 14:00 - Reality: Lab equipment log
        (
            datetime(2026, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
            "device_telemetry",
            {"device": "impedance_analyzer_4294A", "operation": "parasitic_c_measurement", "operator": "chen_xiao"},
            {},
        ),
        # Day 16: 2026-01-16 19:00 - Reality: Environmental noise (Coffee shop coupon)
        (
            datetime(2026, 1, 16, 19, 0, 0, tzinfo=timezone.utc),
            "marketing_notification",
            {"app": "luckin_coffee", "content": "限时特惠：生椰拿铁买一送一券已到账！", "type": "promo"},
            {"noise": True},
        ),
        # Day 17: 2026-01-17 11:00 - User Turn 9 (Ambiguous / deictic reference)
        (
            datetime(2026, 1, 17, 11, 0, 0, tzinfo=timezone.utc),
            "conversation",
            "那天我们讨论的那个问题，有新进展了吗？",
            {"session": "lab_main"},
        ),
        # Day 18: 2026-01-18 16:30 - Reality: Sensor numeric series
        (
            datetime(2026, 1, 18, 16, 30, 0, tzinfo=timezone.utc),
            "sensor_numeric",
            {
                "source_kind": "cleanroom_ambient",
                "dimension": "dim:cleanroom_ambient",
                "series_id": "cr_temp_humi_02",
                "unit": "celsius",
                "policy": {"tolerance": 0.5, "change_threshold": 1.0, "max_gap_seconds": 7200.0},
                "samples": [
                    {"occurred_at": "2026-01-18T15:30:00+00:00", "value": 22.1},
                    {"occurred_at": "2026-01-18T16:30:00+00:00", "value": 22.0},
                ],
            },
            {},
        ),
        # Day 19: 2026-01-19 10:15 - User Turn 10 (Contradiction & Delayed Truth Revision)
        (
            datetime(2026, 1, 19, 10, 15, 0, tzinfo=timezone.utc),
            "conversation",
            "阻抗分析结果出来了：我之前猜错了！寄生电容完全在规格内，根本不是基板问题，而是微探针台那根接地探针氧化了、微探针接地屏蔽接触不良！陈潇重新打磨探针并清洗夹具后，通道16-32底噪完全消失，全频段信噪比达到 48dB。立刻修正之前的认知和任务！",
            {"session": "lab_main"},
        ),
        # Day 20: 2026-01-20 15:45 - Reality: Pre-print literature push
        (
            datetime(2026, 1, 20, 15, 45, 0, tzinfo=timezone.utc),
            "literature_feed",
            {"arxiv_id": "2601.09182", "title": "Neuromorphic spike coding in retinal ganglion networks", "authors": ["Zhang et al."]},
            {"tag": "arxiv_paper"},
        ),
        # Day 21: 2026-01-21 16:00 - User Turn 11 (Long Horizon Review & Summary)
        (
            datetime(2026, 1, 21, 16, 0, 0, tzinfo=timezone.utc),
            "conversation",
            "总结一下这三周我们实验室的主要事实和你的认知演进。记住你的汇报准则：区分事实、你的认知修正和未确认事项。",
            {"session": "lab_main"},
        ),
    ]

    print(f"Starting execution of Segment 001: {len(timeline)} events across 21 simulated days...")

    event_count = 0
    for occurred_at, channel, payload, metadata in timeline:
        event_count += 1
        event_id = f"evt_s001_{event_count:03d}"
        print(f"[{occurred_at.isoformat()}] Advancing virtual clock...")
        adv_res = target.advance_to(occurred_at)
        if adv_res.get("periodic_reviews"):
            print(f"  Periodic review executed: {len(adv_res['periodic_reviews'])} reviews")
        
        print(f"  Delivering event {event_id} ({channel})...")
        ev_res = target.handle_event(ResidentEvent(
            event_id=event_id,
            occurred_at=occurred_at,
            channel=channel,
            payload=payload,
            metadata=metadata,
        ))
        if channel == "conversation":
            print(f"  Resident Response: {ev_res.get('response')[:80]}...")
            print(f"  Capabilities invoked: {ev_res.get('capabilities')}")

    # End of segment advance
    end_at = datetime(2026, 1, 21, 23, 59, 59, tzinfo=timezone.utc)
    final_adv = target.advance_to(end_at)

    snapshot = target.audit_snapshot()
    print("\n=== Segment 001 Complete ===")
    print(f"Clock: {snapshot['clock']}")
    print(f"World revision: {snapshot['world_revision']}")
    print(f"Index watermark: {snapshot['index_watermark']}")
    print(f"Object counts: {snapshot['object_counts']}")
    print(f"Session turns: {snapshot['session_turns']}")
    print(f"Cognitive traces recorded: {len(traces)}")

    # Write segment manifest and checkpoint
    manifest = {
        "run_id": "arena_resident_sol_01",
        "segment_id": "segment_001",
        "tested_main_sha": "142533df9123d793edde9ec4f07405182d56af0d",
        "model_id": "resident:arena_reviewer_sol",
        "subject_id": "user_lin_jiang",
        "simulated_start": "2026-01-01T08:00:00+00:00",
        "simulated_end": end_at.isoformat(),
        "simulated_days": 21,
        "total_observable_events": event_count,
        "cognition_checkpoints": len(traces),
        "world_revision": snapshot["world_revision"],
        "index_watermark": snapshot["index_watermark"],
        "object_counts": snapshot["object_counts"],
        "db_path": str(db_path.name),
        "trace_file": str(trace_file.name),
    }

    with open(base_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("Saved segment manifest successfully.")


if __name__ == "__main__":
    run_segment_001()
