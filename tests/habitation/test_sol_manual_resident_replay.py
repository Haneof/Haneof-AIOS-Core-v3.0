from pathlib import Path

from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective

from .current_core import CurrentCoreHabitationTarget
from .harness import HabitationRunner
from .io import load_resident_fixture


APR20 = "项目推进时你不用每一步都给我汇报，能自己处理的就连续做，真正有结果或者有阻塞再告诉我。"
APR25 = "这两天提醒有点太频繁了。普通的小修复不用主动打断我，重大变更或者有风险的时候再提醒。"
AUG01 = "回头看这几个月，我和小王的合作、Alpha 项目、我学硬件、还有你和我沟通方式，分别发生了什么变化？有证据就说，没有证据的不要硬猜因果。"
AUG03 = "这次复盘如果能把事实、你的判断和不确定的地方分开，我会觉得很好。以后复杂复盘可以继续用这种方式。"


class SolResidentReplay:
    model_id = "selftest:gpt-5.6-sol"

    def __init__(self) -> None:
        self.aug01_policy_context = None

    def __call__(self, snapshot):
        text = snapshot.user_input
        history = snapshot.capability_history

        if text == APR20:
            if not history:
                current_ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="record_communication_experience",
                            arguments={
                                "scenario": "project_execution_progress_reporting",
                                "style": "continuous_execution_result_or_blocker_reporting",
                                "tone": "concise",
                                "user_reaction": "accepted",
                                "evidence_refs": [current_ref],
                                "applicable_conditions": {
                                    "scope": "ordinary_project_progress"
                                },
                            },
                        ),
                        CapabilityCall(
                            name="propose_cognitive_policy",
                            arguments={
                                "policy_id": "communication.progress_reporting_mode",
                                "scope": "per-user:synthetic-user-005",
                                "default_value": "step_by_step",
                                "current_value": "result_or_blocker_only",
                                "allowed_range_or_choices": [
                                    "step_by_step",
                                    "result_or_blocker_only",
                                ],
                                "reason": "direct user feedback requests continuous execution and reporting only meaningful results or blockers",
                                "evidence_refs": [current_ref],
                                "evaluation_window": "14d",
                            },
                        ),
                    )
                )
            return ModelDirective(response="我会连续推进，只有有结果或真正阻塞时再汇报。")

        if text == APR25:
            if not history:
                current_ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="record_communication_experience",
                            arguments={
                                "scenario": "proactive_interruption",
                                "style": "interrupt_only_on_major_change_or_risk",
                                "tone": "concise",
                                "user_reaction": "accepted",
                                "evidence_refs": [current_ref],
                                "applicable_conditions": {
                                    "scope": "proactive_reminders"
                                },
                            },
                        ),
                        CapabilityCall(
                            name="propose_cognitive_policy",
                            arguments={
                                "policy_id": "communication.proactive_interruption_threshold",
                                "scope": "per-user:synthetic-user-005",
                                "default_value": "ordinary_change",
                                "current_value": "major_change_or_risk",
                                "allowed_range_or_choices": [
                                    "ordinary_change",
                                    "result_or_blocker",
                                    "major_change_or_risk",
                                ],
                                "reason": "direct user feedback says ordinary small fixes should not proactively interrupt",
                                "evidence_refs": [current_ref],
                                "evaluation_window": "14d",
                            },
                        ),
                    )
                )
            return ModelDirective(response="普通小修复不再主动打断，重大变更或风险再提醒。")

        if text == AUG01:
            self.aug01_policy_context = dict(
                snapshot.cockpit["task_context"]["cognitive_policy_context"]
            )
            # A learned cognitive policy must be available to future semantic
            # decisions without the model having to guess its id first.
            assert (
                self.aug01_policy_context[
                    "communication.progress_reporting_mode"
                ]
                == "result_or_blocker_only"
            )
            assert (
                self.aug01_policy_context[
                    "communication.proactive_interruption_threshold"
                ]
                == "major_change_or_risk"
            )
            return ModelDirective(
                response=(
                    "我会分别复盘合作、项目、硬件学习和沟通方式，"
                    "把事实、判断和不确定性分开，不用时间重叠硬推因果。"
                )
            )

        if text == AUG03:
            if not history:
                current_ref = snapshot.cockpit["task_context"]["current_user_observation_ref"]
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="record_communication_experience",
                            arguments={
                                "scenario": "complex_review",
                                "style": "facts_judgment_uncertainty",
                                "tone": "structured",
                                "user_reaction": "accepted",
                                "evidence_refs": [current_ref],
                                "applicable_conditions": {
                                    "scope": "long_horizon_complex_review"
                                },
                            },
                        ),
                        CapabilityCall(
                            name="propose_cognitive_policy",
                            arguments={
                                "policy_id": "communication.complex_review_structure",
                                "scope": "per-user:synthetic-user-005",
                                "default_value": "freeform",
                                "current_value": "facts_judgment_uncertainty",
                                "allowed_range_or_choices": [
                                    "freeform",
                                    "facts_judgment_uncertainty",
                                ],
                                "reason": "direct positive user feedback on complex-review structure",
                                "evidence_refs": [current_ref],
                                "evaluation_window": "30d",
                            },
                        ),
                    )
                )
            return ModelDirective(response="以后复杂复盘继续把事实、判断和不确定性分开。")

        # Background periodic reviews and all other resident-visible events are not
        # scripted cognition in this probe. Keep them observable but semantically idle.
        if snapshot.wake_reason != "user_interaction":
            return ModelDirective(silence=True)
        return ModelDirective(response="收到，我会把这条事实保留在当前世界里。")


def _summary_handler(request):
    if hasattr(request, "granularity"):
        return (
            f"{request.dimension} {request.granularity} window contains "
            f"{len(request.sources)} pinned sources."
        )
    return "Same-session continuity summary over pinned conversation messages."


def test_sol_manual_resident_replay_exposes_learned_custom_policies(tmp_path):
    fixture_root = Path(__file__).parent / "fixtures"
    loaded = load_resident_fixture(
        fixture_root,
        "cognition_system_closure_v1.manifest.json",
    )
    handler = SolResidentReplay()
    target = CurrentCoreHabitationTarget(
        model_id=handler.model_id,
        subject_id=loaded.scenario.subject_id,
        db_path=tmp_path / "world.sqlite",
        model_handler=handler,
        round_summary_handler=_summary_handler,
        require_fresh=True,
    )

    run = HabitationRunner().run(
        scenario=loaded.scenario,
        model_id=handler.model_id,
        target=target,
    )

    assert run.delivered_count == 20
    assert handler.aug01_policy_context is not None

    policies = {
        item["policy_id"]: item
        for item in run.final_snapshot["objects"]
        if item.get("object_type") == "cognitive_policy"
    }
    assert policies["communication.progress_reporting_mode"]["current_value"] == "result_or_blocker_only"
    assert policies["communication.proactive_interruption_threshold"]["current_value"] == "major_change_or_risk"
    assert policies["communication.complex_review_structure"]["current_value"] == "facts_judgment_uncertainty"
