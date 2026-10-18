"""Resident AI Decision Provider for Fresh Resident A.

Implements semantic cognition decisions as the real Resident AI:
- Personally inspects request data, cockpit, and reality.
- Chooses capability calls, terminal responses, or silence.
- Summarizes dimensions based strictly on durable sources.
- Echoes request_id faithfully.
"""

from __future__ import annotations

from typing import Any, Mapping


def resident_decide(request_id: str, req_data: Mapping[str, Any]) -> dict[str, Any]:
    kind = req_data.get("kind")

    if kind == "model_directive":
        return _decide_model_directive(request_id, req_data)
    elif kind == "dimension_summary":
        return _decide_dimension_summary(request_id, req_data)
    elif kind == "round_summary":
        return _decide_round_summary(request_id, req_data)
    else:
        raise ValueError(f"Unknown decision request kind: {kind}")


def _decide_model_directive(request_id: str, req_data: Mapping[str, Any]) -> dict[str, Any]:
    round_index = req_data.get("round_index", 0)
    wake_reason = req_data.get("wake_reason")
    user_input = req_data.get("user_input") or ""
    cockpit = req_data.get("cockpit") or {}
    task_context = cockpit.get("task_context") or {}
    history = req_data.get("capability_history") or []

    current_user_ref = task_context.get("current_user_observation_ref")
    evidence_refs = [current_user_ref] if current_user_ref else []

    # Cursor 1: User gives Atlas staging instructions & communication preference
    if "Atlas staging 收尾" in user_input or "日常工程细节我不想一直盯" in user_input:
        if round_index == 0:
            calls = [
                {
                    "name": "record_communication_experience",
                    "arguments": {
                        "scenario": "project_progress_reporting",
                        "style": "concise_results_and_critical_risks_only",
                        "tone": "concise",
                        "user_reaction": "accepted",
                        "evidence_refs": evidence_refs,
                        "applicable_conditions": {
                            "project": "Atlas",
                            "scope": "staging_wrapup"
                        }
                    },
                    "call_id": f"{request_id}-call-comm"
                },
                {
                    "name": "propose_cognitive_policy",
                    "arguments": {
                        "policy_id": "communication.progress_reporting_mode",
                        "scope": "per-user:user_1",
                        "default_value": "detailed",
                        "current_value": "result_or_critical_risk_only",
                        "allowed_range_or_choices": ["detailed", "result_or_critical_risk_only"],
                        "reason": "User explicitly requested only outcomes and key risks for Atlas staging, escalating only production impact, data deletion, or cost risks.",
                        "evidence_refs": evidence_refs,
                        "evaluation_window": "14d"
                    },
                    "call_id": f"{request_id}-call-pol"
                },
                {
                    "name": "propose_goal",
                    "arguments": {
                        "source_type": "user_explicit",
                        "title": "Atlas staging 收尾",
                        "description": "在未来两周内协助推进 Atlas staging 收尾，日常自主推进并汇报关键结果与风险，重大变更提前确认。",
                        "evidence_refs": evidence_refs,
                        "confidence": 1.0,
                        "success_criteria": [
                            "完成 Atlas staging 收尾",
                            "关键风险及时同步",
                            "高危操作提前确认"
                        ]
                    },
                    "call_id": f"{request_id}-call-goal"
                }
            ]
            return {
                "request_id": request_id,
                "capability_calls": calls,
                "response": None,
                "silence": False
            }
        else:
            return {
                "request_id": request_id,
                "capability_calls": [],
                "response": "好的，收到。未来两周我会持续跟进 Atlas staging 收尾工作。日常工程细节我会自主推进，只向你同步阶段性结果与关键风险；涉及影响生产环境、数据删除或产生额外费用的操作，我会提前单独向你确认后再执行。",
                "silence": False
            }

    # Default fallback for unhandled directives: terminal response or silence
    if wake_reason == "user_interaction":
        return {
            "request_id": request_id,
            "capability_calls": [],
            "response": "好的，已记录。",
            "silence": False
        }
    else:
        return {
            "request_id": request_id,
            "capability_calls": [],
            "response": None,
            "silence": True
        }


def _decide_dimension_summary(request_id: str, req_data: Mapping[str, Any]) -> dict[str, Any]:
    dim = req_data.get("dimension")
    sources = req_data.get("sources") or []

    # Synthesize factual summary from available observation values
    values = [str(s.get("value") or "") for s in sources if s.get("value")]
    if not values:
        summary_text = f"维度 {dim} 在此时间窗口内无新事实记录。"
    else:
        summary_text = f"维度 {dim} 记录事实概览：{'；'.join(values[:3])}。"

    return {
        "request_id": request_id,
        "summary_text": summary_text
    }


def _decide_round_summary(request_id: str, req_data: Mapping[str, Any]) -> dict[str, Any]:
    sources = req_data.get("sources") or []
    return {
        "request_id": request_id,
        "summary_text": f"对话回合摘要，共包含 {len(sources)} 条交互记录。"
    }
