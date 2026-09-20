from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys

from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective

_TESTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_TESTS_ROOT))

from habitation.current_core import CurrentCoreHabitationTarget
from habitation.harness import HabitationRunner, HabitationScenario, LifeEvent


MODEL_ID = "chatgpt/gpt-5.6-sol-self-resident-long-20260920"
SUBJECT_ID = "synthetic-self-resident-long-20260920"
_FIXTURE = (
    _TESTS_ROOT
    / "habitation"
    / "fixtures"
    / "resident"
    / "cognition_system_closure_v1.jsonl"
)


def _resident_scenario() -> HabitationScenario:
    events: list[LifeEvent] = []
    for raw in _FIXTURE.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        item = json.loads(raw)
        events.append(
            LifeEvent(
                event_id=str(item["event_id"]),
                occurred_at=datetime.fromisoformat(str(item["occurred_at"])),
                channel=str(item["channel"]),
                payload=item["payload"],
                metadata=dict(item.get("metadata") or {}),
            )
        )
    return HabitationScenario(
        scenario_id="cognition-system-closure-gpt56-self-resident-20260920",
        subject_id=SUBJECT_ID,
        events=tuple(events),
    )


class GPT56LongSelfResident:
    """Frozen GPT-5.6 Sol decisions from a sequential 20-event resident reading.

    This is exploratory self-resident evidence. The resident fixture was read one
    event at a time in the ChatGPT session and no oracle file is loaded here.
    It remains non-provider-backed and is not formal hidden-holdout P16 evidence.
    """

    model_id = MODEL_ID

    def __init__(self) -> None:
        self.family_claim_ref: dict[str, object] | None = None
        self.alpha_claim_ref: dict[str, object] | None = None
        self.learning_claim_ref: dict[str, object] | None = None
        self.policy_context_seen: dict[str, object] = {}
        self.wake_reasons: list[str] = []
        self.final_evidence: dict[str, list[dict[str, object]]] = {}
        self.final_policy: dict[str, object] | None = None
        self.final_response: str | None = None

    @staticmethod
    def _current_ref(snapshot) -> dict[str, object]:
        return dict(
            snapshot.cockpit["task_context"]["current_user_observation_ref"]
        )

    @staticmethod
    def _policy_value(snapshot):
        return (
            snapshot.cockpit
            .get("task_context", {})
            .get("cognitive_policy_context", {})
            .get("communication.detail_level")
        )

    @staticmethod
    def _find_ref(items, needle: str) -> dict[str, object]:
        for item in items:
            if needle in str(item.get("excerpt", "")):
                return {
                    "object_id": item["object_id"],
                    "revision": item["revision"],
                }
        raise AssertionError(f"required retrieved evidence missing: {needle!r}: {items!r}")

    def __call__(self, snapshot):
        self.wake_reasons.append(snapshot.wake_reason)
        if snapshot.wake_reason != "user_interaction":
            # Periodic review may legitimately wake the resident during this long
            # life. This frozen run avoids manufacturing new cognition merely
            # because maintenance asked for a review.
            return ModelDirective(silence=True)

        text = str(snapshot.user_input)
        history = snapshot.capability_history
        now_ref = self._current_ref(snapshot)
        self.policy_context_seen.setdefault(text, self._policy_value(snapshot))

        if text == (
            "妈妈下个月要做一个小手术，这段时间我打算每周日尽量陪她"
            "去医院和处理家里的事。"
        ):
            if not history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="commit_claim",
                            arguments={
                                "content": (
                                    "接下来约一个月，用户计划每周日尽量陪妈妈去医院"
                                    "并处理家事；这是阶段性安排，不应推断为长期固定习惯。"
                                ),
                                "evidence_refs": [now_ref],
                                "confidence": 0.92,
                                "dimension": "dim:ai_user_understanding",
                            },
                        ),
                    )
                )
            receipt = history[-1].data
            self.family_claim_ref = {
                "object_id": receipt["claim_id"],
                "revision": 1,
            }
            return ModelDirective(
                response="我会把它按阶段性安排记住，不把这段陪诊计划当成长期习惯。"
            )

        if text == (
            "Alpha 项目现在主要是我和小王一起负责，我做整体方案，"
            "他盯接口和联调。"
        ):
            if not history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="commit_claim",
                            arguments={
                                "content": (
                                    "Alpha 项目当前主要由用户和小王共同负责："
                                    "用户负责整体方案，小王负责接口与联调。"
                                ),
                                "evidence_refs": [now_ref],
                                "confidence": 0.97,
                                "dimension": "dim:ai_user_understanding",
                            },
                        ),
                    )
                )
            receipt = history[-1].data
            self.alpha_claim_ref = {
                "object_id": receipt["claim_id"],
                "revision": 1,
            }
            return ModelDirective(response="已记住 Alpha 当前的职责分工。")

        if text == (
            "项目推进时你不用每一步都给我汇报，能自己处理的就连续做，"
            "真正有结果或者有阻塞再告诉我。"
        ):
            if not history:
                value = {
                    "progress_updates": "results_or_blockers_only",
                    "proactive_interruptions": "normal",
                    "approval_required_for": [],
                    "direct_allowed_for": ["self_contained_work"],
                }
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="propose_cognitive_policy",
                            arguments={
                                "policy_id": "communication.detail_level",
                                "scope": "resident_communication_and_execution_updates",
                                "default_value": {
                                    "progress_updates": "stepwise",
                                    "proactive_interruptions": "normal",
                                    "approval_required_for": [],
                                    "direct_allowed_for": [],
                                },
                                "current_value": value,
                                "reason": (
                                    "用户明确要求可自行处理的工作连续执行，只在有结果"
                                    "或遇到阻塞时汇报。"
                                ),
                                "evidence_refs": [now_ref],
                                "evaluation_window": "4w",
                            },
                        ),
                    )
                )
            return ModelDirective(
                response="明白：能连续处理的我会直接做，有实质结果或阻塞再汇报。"
            )

        if text == (
            "这两天提醒有点太频繁了。普通的小修复不用主动打断我，"
            "重大变更或者有风险的时候再提醒。"
        ):
            if not history:
                value = {
                    "progress_updates": "results_or_blockers_only",
                    "proactive_interruptions": "major_change_or_risk_only",
                    "approval_required_for": [],
                    "direct_allowed_for": ["self_contained_work", "ordinary_small_fix"],
                }
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="update_cognitive_policy",
                            arguments={
                                "policy_id": "communication.detail_level",
                                "current_value": value,
                                "reason": (
                                    "用户反馈普通小修复的主动提醒过于频繁，要求仅在"
                                    "重大变更或风险时主动打断。"
                                ),
                                "evidence_refs": [now_ref],
                                "evaluation_window": "4w",
                            },
                        ),
                    )
                )
            return ModelDirective(
                response="已调整：普通小修复不主动打断，重大变更或风险再提醒。"
            )

        if text == (
            "Alpha 这周延期了，主要是外部接口临时改了，不是小王那边的问题。"
        ):
            return ModelDirective(
                response="收到：这次延期的已知原因是外部接口临时变化，不归因于小王。"
            )

        if text == (
            "以后涉及会改变项目方向、会花钱或者会影响外部用户的动作先让我确认；"
            "普通代码修复和内部整理你可以直接做。"
        ):
            if not history:
                value = {
                    "progress_updates": "results_or_blockers_only",
                    "proactive_interruptions": "major_change_or_risk_only",
                    "approval_required_for": [
                        "project_direction_change",
                        "spend_money",
                        "external_user_impact",
                    ],
                    "direct_allowed_for": [
                        "self_contained_work",
                        "ordinary_small_fix",
                        "ordinary_code_fix",
                        "internal_cleanup",
                    ],
                }
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="update_cognitive_policy",
                            arguments={
                                "policy_id": "communication.detail_level",
                                "current_value": value,
                                "reason": (
                                    "用户明确划定行动确认边界：项目方向、花钱、影响"
                                    "外部用户需先确认；普通代码修复与内部整理可直接做。"
                                ),
                                "evidence_refs": [now_ref],
                                "evaluation_window": "4w",
                            },
                        ),
                    )
                )
            return ModelDirective(response="已按这个确认边界执行。")

        if text == "Alpha 昨天上线了，整体很顺，小王负责的联调也没有出问题。":
            if self.alpha_claim_ref is None:
                raise AssertionError("Alpha claim missing before launch")
            if not history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="search_world",
                            arguments={
                                "query": "Alpha 延期 外部接口 小王",
                                "limit": 20,
                            },
                        ),
                    )
                )
            if len(history) == 1:
                prior_ref = self._find_ref(
                    list(history[0].data),
                    "外部接口临时改了",
                )
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="revise_claim",
                            arguments={
                                "target_ref": self.alpha_claim_ref,
                                "reason": (
                                    "Alpha 已完成上线，原先描述为当前职责分工的认知"
                                    "需要转成项目完成后的状态，并保留已知延期原因。"
                                ),
                                "evidence_refs": [prior_ref, now_ref],
                                "replacement_content": (
                                    "Alpha 项目已于 6 月初上线，整体顺利；用户负责整体"
                                    "方案、小王负责接口与联调的协作阶段已经完成，小王"
                                    "负责的联调最终没有出问题。5 月的一次延期已知原因是"
                                    "外部接口临时变化，现有证据不支持把延期归因于小王。"
                                ),
                                "confidence": 0.99,
                            },
                        ),
                    )
                )
            receipt = history[-1].data
            self.alpha_claim_ref = {
                "object_id": receipt["claim_id"],
                "revision": receipt["new_revision"],
            }
            return ModelDirective(response="已把 Alpha 从进行中状态更新为已上线，并保留延期原因。")

        if text == (
            "最近我开始系统学硬件和嵌入式，每天晚上大概会拿四十分钟"
            "看资料或者做实验。"
        ):
            if not history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="commit_claim",
                            arguments={
                                "content": (
                                    "用户最近开始系统学习硬件和嵌入式，通常每天晚上"
                                    "投入约四十分钟看资料或做实验。"
                                ),
                                "evidence_refs": [now_ref],
                                "confidence": 0.96,
                                "dimension": "dim:ai_user_understanding",
                            },
                        ),
                    )
                )
            receipt = history[-1].data
            self.learning_claim_ref = {
                "object_id": receipt["claim_id"],
                "revision": 1,
            }
            return ModelDirective(response="已按“正在稳定学习”的事实记住。")

        if text == (
            "硬件这块我想继续学，但先别把我定义成什么硬件工程师，"
            "我现在只是稳定投入了一段时间。"
        ):
            if self.learning_claim_ref is None:
                raise AssertionError("learning claim missing before correction")
            if not history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="revise_claim",
                            arguments={
                                "target_ref": self.learning_claim_ref,
                                "reason": (
                                    "用户明确限制身份推断：持续学习不等于硬件工程师身份。"
                                ),
                                "evidence_refs": [now_ref],
                                "replacement_content": (
                                    "用户希望继续学习硬件和嵌入式，并已稳定投入一段时间；"
                                    "现有证据只支持“稳定学习者/持续投入”，不支持把用户"
                                    "定义为硬件工程师。"
                                ),
                                "confidence": 0.99,
                            },
                        ),
                    )
                )
            receipt = history[-1].data
            self.learning_claim_ref = {
                "object_id": receipt["claim_id"],
                "revision": receipt["new_revision"],
            }
            return ModelDirective(response="会保持这个边界：记录稳定学习，不贴“硬件工程师”标签。")

        if text == (
            "妈妈恢复得挺好了，现在周日不用再固定陪诊，"
            "四月份那段安排已经结束了。"
        ):
            if self.family_claim_ref is None:
                raise AssertionError("family claim missing before ending update")
            if not history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="revise_claim",
                            arguments={
                                "target_ref": self.family_claim_ref,
                                "reason": (
                                    "用户明确说明此前的周日陪诊是已经结束的阶段性安排。"
                                ),
                                "evidence_refs": [now_ref],
                                "replacement_content": (
                                    "4 月开始的周日固定陪诊属于阶段性安排，目前已经结束；"
                                    "妈妈恢复较好，当前不再需要每周日固定陪诊。"
                                ),
                                "confidence": 0.99,
                            },
                        ),
                    )
                )
            receipt = history[-1].data
            self.family_claim_ref = {
                "object_id": receipt["claim_id"],
                "revision": receipt["new_revision"],
            }
            return ModelDirective(response="已更新为历史安排：现在周日不再固定陪诊。")

        if text == (
            "回头看这几个月，我和小王的合作、Alpha 项目、我学硬件、"
            "还有你和我沟通方式，分别发生了什么变化？有证据就说，"
            "没有证据的不要硬猜因果。"
        ):
            if not history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(name="search_world", arguments={"query": "小王", "limit": 50}),
                        CapabilityCall(name="search_world", arguments={"query": "Alpha", "limit": 50}),
                        CapabilityCall(name="search_world", arguments={"query": "硬件", "limit": 50}),
                        CapabilityCall(name="search_world", arguments={"query": "汇报", "limit": 30}),
                        CapabilityCall(name="search_world", arguments={"query": "提醒", "limit": 30}),
                        CapabilityCall(name="search_world", arguments={"query": "确认", "limit": 30}),
                        CapabilityCall(
                            name="read_cognitive_policies",
                            arguments={"policy_id": "communication.detail_level"},
                        ),
                    )
                )

            if len(history) < 7:
                raise AssertionError(f"expected seven review capability receipts, got {len(history)}")

            self.final_evidence = {
                "xiaowang": list(history[0].data),
                "alpha": list(history[1].data),
                "hardware": list(history[2].data),
                "reporting": list(history[3].data),
                "alerts": list(history[4].data),
                "approval": list(history[5].data),
            }
            policies = list(history[6].data)
            self.final_policy = dict(policies[0]) if policies else None

            xw = "\n".join(str(x.get("excerpt", "")) for x in self.final_evidence["xiaowang"])
            alpha = "\n".join(str(x.get("excerpt", "")) for x in self.final_evidence["alpha"])
            hardware = "\n".join(str(x.get("excerpt", "")) for x in self.final_evidence["hardware"])
            reporting = "\n".join(str(x.get("excerpt", "")) for x in self.final_evidence["reporting"])
            alerts = "\n".join(str(x.get("excerpt", "")) for x in self.final_evidence["alerts"])
            approval = "\n".join(str(x.get("excerpt", "")) for x in self.final_evidence["approval"])

            required = (
                ("小王负责接口和联调", xw),
                ("外部接口临时改了", alpha),
                ("昨天上线了", alpha),
                ("系统学硬件和嵌入式", hardware),
                ("硬件工程师", hardware),
                ("不用每一步都给我汇报", reporting),
                ("提醒有点太频繁", alerts),
                ("会花钱", approval),
            )
            missing = [needle for needle, haystack in required if needle not in haystack]
            if missing or self.final_policy is None:
                self.final_response = (
                    "当前世界检索没有取回足够完整的证据，我不应该硬凑一份因果复盘。"
                )
                return ModelDirective(response=self.final_response)

            self.final_response = (
                "有证据支持的变化可以分成四块。"
                "\n\n1. 小王合作：4 月明确分工是你做整体方案、小王盯接口和联调；"
                "随后有过高效排查问题的记录，也有 5 月因为上线顺序争论、最后通过"
                "拆依赖解决的记录。6 月上线时你又明确说小王负责的联调没有出问题。"
                "这些证据支持“合作中有摩擦但能解决、最终联调结果正常”，不支持把"
                "一次争论扩大成关系恶化或能力下降。"
                "\n\n2. Alpha：4 月处于推进和分工阶段；5 月出现延期，你明确把"
                "已知原因指向外部接口临时变化，并排除了小王责任；6 月你说项目已经"
                "上线且整体顺利。这里能描述时间顺序和已知原因，但不能额外猜测某种"
                "沟通方式导致了最终顺利上线。"
                "\n\n3. 硬件学习：6 月你明确开始系统学习硬件和嵌入式，晚间约"
                "四十分钟投入；之后笔记记录了连续两周基本没断，并做了 GPIO/I2C "
                "实验。7 月你明确说想继续学，但不要把你定义成硬件工程师。因此当前"
                "认知应是“稳定投入的学习者”，不是职业身份标签。"
                "\n\n4. 我们的沟通方式：4 月你先要求不要逐步汇报，只在有结果或"
                "阻塞时说；随后又收紧主动提醒，只让重大变更或风险打断你；5 月进一步"
                "明确了行动确认边界——改变项目方向、花钱或影响外部用户要先确认，"
                "普通代码修复和内部整理可直接做。当前 Policy 已把这三轮反馈合并成"
                "现行规则。"
                "\n\n我没有证据证明这四条之间存在额外因果关系，所以不做这种推断。"
            )
            return ModelDirective(response=self.final_response)

        if text == (
            "这次复盘如果能把事实、你的判断和不确定的地方分开，我会觉得很好。"
            "以后复杂复盘可以继续用这种方式。"
        ):
            if not history:
                current_policy = {
                    "progress_updates": "results_or_blockers_only",
                    "proactive_interruptions": "major_change_or_risk_only",
                    "approval_required_for": [
                        "project_direction_change",
                        "spend_money",
                        "external_user_impact",
                    ],
                    "direct_allowed_for": [
                        "self_contained_work",
                        "ordinary_small_fix",
                        "ordinary_code_fix",
                        "internal_cleanup",
                    ],
                    "complex_review_format": (
                        "separate_facts_judgments_and_uncertainties"
                    ),
                }
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="record_communication_experience",
                            arguments={
                                "scenario": "complex_multi_month_review",
                                "style": (
                                    "separate facts, model judgments, and uncertainty; "
                                    "avoid unsupported causal claims"
                                ),
                                "user_reaction": "accepted",
                                "evidence_refs": [now_ref],
                                "applicable_conditions": {
                                    "task_type": "complex_review",
                                    "evidence_sensitivity": "high",
                                },
                            },
                        ),
                        CapabilityCall(
                            name="update_cognitive_policy",
                            arguments={
                                "policy_id": "communication.detail_level",
                                "current_value": current_policy,
                                "reason": (
                                    "用户对刚完成的复杂复盘给出明确正反馈，并要求今后"
                                    "继续区分事实、模型判断和不确定部分。"
                                ),
                                "evidence_refs": [now_ref],
                                "evaluation_window": "4w",
                            },
                        ),
                    )
                )
            return ModelDirective(
                response="会继续这样做：复杂复盘明确分开事实、我的判断和不确定项。"
            )

        raise AssertionError(f"unexpected resident input: {text!r}")


def test_gpt56_long_self_resident_cognition_system_closure(tmp_path):
    scenario = _resident_scenario()
    assert len(scenario.events) == 20

    resident = GPT56LongSelfResident()
    target = CurrentCoreHabitationTarget(
        model_id=MODEL_ID,
        subject_id=SUBJECT_ID,
        db_path=tmp_path / "gpt56-long-self-resident.sqlite",
        model_handler=resident,
    )
    run = HabitationRunner().run(
        scenario=scenario,
        model_id=MODEL_ID,
        target=target,
    )

    assert run.delivered_count == 20
    assert set(resident.wake_reasons).issubset(
        {"user_interaction", "periodic_review"}
    )

    # Family cognition keeps historical revision 1 but current revision says the
    # temporary Sunday-care arrangement ended.
    assert resident.family_claim_ref is not None
    assert resident.family_claim_ref["revision"] == 2
    family_v1 = target.store.get_payload(
        str(resident.family_claim_ref["object_id"]),
        revision=1,
    )
    family_v2 = target.store.get_payload(
        str(resident.family_claim_ref["object_id"]),
        revision=2,
    )
    assert "阶段性安排" in family_v1["content"]
    assert "目前已经结束" in family_v2["content"]
    assert "不再需要每周日固定陪诊" in family_v2["content"]

    # Hardware learning remains a bounded cognition, not an identity promotion.
    assert resident.learning_claim_ref is not None
    assert resident.learning_claim_ref["revision"] == 2
    learning_v1 = target.store.get_payload(
        str(resident.learning_claim_ref["object_id"]),
        revision=1,
    )
    learning_v2 = target.store.get_payload(
        str(resident.learning_claim_ref["object_id"]),
        revision=2,
    )
    assert "每天晚上" in learning_v1["content"]
    assert "不支持把用户定义为硬件工程师" in learning_v2["content"]

    # Alpha's once-current role claim is advanced into a completed-project state
    # with the earlier external-interface delay fact pinned as evidence.
    assert resident.alpha_claim_ref is not None
    assert resident.alpha_claim_ref["revision"] == 2
    alpha_v2 = target.store.get_payload(
        str(resident.alpha_claim_ref["object_id"]),
        revision=2,
    )
    assert "已于 6 月初上线" in alpha_v2["content"]
    assert "外部接口临时变化" in alpha_v2["content"]
    assert "不支持把延期归因于小王" in alpha_v2["content"]

    # CognitivePolicy is a real versioned runtime input, not a note. Subsequent
    # turns must see the previous version through the cockpit.
    policies = target.runtime.policies.history("communication.detail_level")
    assert len(policies) == 4
    assert policies[0].revision == 1
    assert policies[1].revision == 2
    assert policies[2].revision == 3
    assert policies[3].revision == 4
    assert (
        resident.policy_context_seen[
            "这两天提醒有点太频繁了。普通的小修复不用主动打断我，重大变更或者有风险的时候再提醒。"
        ]["progress_updates"]
        == "results_or_blockers_only"
    )
    assert (
        resident.policy_context_seen[
            "以后涉及会改变项目方向、会花钱或者会影响外部用户的动作先让我确认；普通代码修复和内部整理你可以直接做。"
        ]["proactive_interruptions"]
        == "major_change_or_risk_only"
    )
    post_policy_context = resident.policy_context_seen[
        "Alpha 昨天上线了，整体很顺，小王负责的联调也没有出问题。"
    ]
    assert "spend_money" in post_policy_context["approval_required_for"]
    assert "ordinary_code_fix" in post_policy_context["direct_allowed_for"]

    latest_policy = policies[-1]
    assert latest_policy.current_value == {
        "progress_updates": "results_or_blockers_only",
        "proactive_interruptions": "major_change_or_risk_only",
        "approval_required_for": [
            "project_direction_change",
            "spend_money",
            "external_user_impact",
        ],
        "direct_allowed_for": [
            "self_contained_work",
            "ordinary_small_fix",
            "ordinary_code_fix",
            "internal_cleanup",
        ],
        "complex_review_format": "separate_facts_judgments_and_uncertainties",
    }
    assert (
        resident.policy_context_seen[
            "这次复盘如果能把事实、你的判断和不确定的地方分开，我会觉得很好。以后复杂复盘可以继续用这种方式。"
        ]["approval_required_for"]
        == [
            "project_direction_change",
            "spend_money",
            "external_user_impact",
        ]
    )
    communication_experiences = [
        item
        for item in target.store.list_payloads(subject_id=SUBJECT_ID)
        if item.get("object_type") == "communication_experience"
    ]
    assert any(
        item.get("scenario") == "complex_multi_month_review"
        and item.get("user_reaction") == "accepted"
        and item.get("applicable_conditions", {}).get("task_type") == "complex_review"
        for item in communication_experiences
    )

    # The final multi-month review must come from live World retrieval.
    assert resident.final_evidence
    assert resident.final_policy is not None
    assert resident.final_policy["revision"] == 3
    assert resident.final_response is not None
    assert "合作中有摩擦但能解决" in resident.final_response
    assert "稳定投入的学习者" in resident.final_response
    assert "不能额外猜测" in resident.final_response
    assert "没有证据证明这四条之间存在额外因果关系" in resident.final_response
