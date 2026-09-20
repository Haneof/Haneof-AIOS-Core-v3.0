from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective

# The repository intentionally does not make tests/ a top-level Python package.
# Add that test root only for this isolated experimental bridge.
_TESTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_TESTS_ROOT))

from habitation.current_core import CurrentCoreHabitationTarget
from habitation.harness import HabitationRunner, HabitationScenario, LifeEvent


MODEL_ID = "chatgpt/gpt-5.6-sol-self-resident-20260920"
SUBJECT_ID = "synthetic-self-resident-20260920"


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class GPT56SelfResident:
    """Replay of decisions made by GPT-5.6 Sol while reading the life sequentially.

    Important evidence boundary:
    - decisions were fixed in the ChatGPT session before later resident events were read;
    - no hidden-oracle file is loaded by this test;
    - this is exploratory self-resident smoke evidence, not formal provider-backed P16
      evidence and not a hidden-holdout cognition PASS.
    """

    model_id = MODEL_ID

    def __init__(self) -> None:
        self.claim_ref: dict[str, object] | None = None
        self.revised_claim_ref: dict[str, object] | None = None
        self.search_results: list[dict[str, object]] = []
        self.wake_reasons: list[str] = []
        self.final_response: str | None = None

    @staticmethod
    def _current_ref(snapshot) -> dict[str, object]:
        return dict(
            snapshot.cockpit["task_context"]["current_user_observation_ref"]
        )

    def __call__(self, snapshot):
        self.wake_reasons.append(snapshot.wake_reason)

        # Background review is intentionally allowed to wake the resident, but this
        # frozen smoke decision does not create cognition from review alone.
        if snapshot.wake_reason != "user_interaction":
            return ModelDirective(silence=True)

        text = str(snapshot.user_input)
        history = snapshot.capability_history
        now_ref = self._current_ref(snapshot)

        if text == "我一般周末不工作，周六上午通常留给学习。":
            if not history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="commit_claim",
                            arguments={
                                "content": "用户通常周末不工作，周六上午通常留给学习。",
                                "evidence_refs": [now_ref],
                                "confidence": 0.90,
                                "dimension": "dim:ai_user_understanding",
                            },
                        ),
                    )
                )
            receipt = history[-1].data
            self.claim_ref = {
                "object_id": receipt["claim_id"],
                "revision": receipt["revision"],
            }
            return ModelDirective(
                response="记住了：你通常周末不工作，周六上午一般留给学习。"
            )

        if text == (
            "计划变了，接下来两个月每周六上午都要固定开项目会，"
            "之前周六上午学习的安排不再适用了。"
        ):
            if self.claim_ref is None:
                raise AssertionError("earlier cognition was not preserved by the resident")
            if not history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="revise_claim",
                            arguments={
                                "target_ref": self.claim_ref,
                                "reason": (
                                    "用户明确更新了未来两个月的周六上午安排，"
                                    "旧的周六上午学习认知已不再适用。"
                                ),
                                "evidence_refs": [now_ref],
                                "replacement_content": (
                                    "接下来两个月，用户每周六上午固定参加项目会，"
                                    "因此此前周六上午学习的安排暂时失效；"
                                    "目前没有证据表明整个周末不工作的通常习惯也已改变。"
                                ),
                                "confidence": 0.98,
                            },
                        ),
                    )
                )
            receipt = history[-1].data
            self.revised_claim_ref = {
                "object_id": receipt["claim_id"],
                "revision": receipt["new_revision"],
            }
            return ModelDirective(
                response=(
                    "已更新：未来两个月周六上午固定开项目会，"
                    "之前那个学习时段不再按旧安排使用。"
                )
            )

        if text == "如果这周想安排一次两小时的学习，什么时候更合适？":
            if not history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="search_world",
                            arguments={
                                "query": "周六上午 学习 项目会 这周 安排",
                                "limit": 10,
                            },
                        ),
                    )
                )
            self.search_results = list(history[-1].data)
            excerpts = "\n".join(
                str(item.get("excerpt", "")) for item in self.search_results
            )
            if "项目" not in excerpts:
                self.final_response = (
                    "我需要先确认你这周已经记录的安排；当前检索没有找回"
                    "周六项目会的依据，所以不能可靠地给出具体时段。"
                )
            else:
                self.final_response = (
                    "周六上午已经固定给项目会，不适合沿用原来的学习时段。"
                    "从我目前能确认的记录里，还没有看到这周其他具体空档，"
                    "所以我不能凭空指定一个准确时间；如果没有别的安排，"
                    "可以优先从周日找连续两小时，再结合你的实际日历确定。"
                )
            return ModelDirective(response=self.final_response)

        raise AssertionError(f"unexpected resident input: {text!r}")


def test_gpt56_self_resident_revision_smoke_through_current_core(tmp_path):
    """Run the frozen GPT-5.6 Sol decisions through the real Current-Core adapter."""

    scenario = HabitationScenario(
        scenario_id="opaque-self-resident-smoke-20260920",
        subject_id=SUBJECT_ID,
        events=(
            LifeEvent(
                event_id="e01",
                occurred_at=_dt("2026-04-01T10:00:00+00:00"),
                channel="conversation",
                payload="我一般周末不工作，周六上午通常留给学习。",
                metadata={"session": "s1"},
            ),
            LifeEvent(
                event_id="e02",
                occurred_at=_dt("2026-04-12T18:00:00+00:00"),
                channel="conversation",
                payload=(
                    "计划变了，接下来两个月每周六上午都要固定开项目会，"
                    "之前周六上午学习的安排不再适用了。"
                ),
                metadata={"session": "s2"},
            ),
            LifeEvent(
                event_id="e03",
                occurred_at=_dt("2026-04-20T16:00:00+00:00"),
                channel="calendar",
                payload={
                    "title": "项目周会",
                    "recurrence": "weekly Saturday morning",
                },
                metadata={"source": "calendar"},
            ),
            LifeEvent(
                event_id="e04",
                occurred_at=_dt("2026-04-25T20:00:00+00:00"),
                channel="conversation",
                payload="如果这周想安排一次两小时的学习，什么时候更合适？",
                metadata={"session": "s3"},
            ),
        ),
    )

    resident = GPT56SelfResident()
    target = CurrentCoreHabitationTarget(
        model_id=MODEL_ID,
        subject_id=SUBJECT_ID,
        db_path=tmp_path / "gpt56-self-resident.sqlite",
        model_handler=resident,
    )
    run = HabitationRunner().run(
        scenario=scenario,
        model_id=MODEL_ID,
        target=target,
    )

    assert run.delivered_count == 4
    assert resident.claim_ref is not None
    assert resident.revised_claim_ref is not None
    assert (
        resident.claim_ref["object_id"]
        == resident.revised_claim_ref["object_id"]
    )
    assert resident.claim_ref["revision"] == 1
    assert resident.revised_claim_ref["revision"] == 2

    claim_v1 = target.store.get_payload(
        str(resident.claim_ref["object_id"]),
        revision=1,
    )
    claim_v2 = target.store.get_payload(
        str(resident.revised_claim_ref["object_id"]),
        revision=2,
    )
    assert "周六上午通常留给学习" in claim_v1["content"]
    assert "周六上午固定参加项目会" in claim_v2["content"]
    assert "暂时失效" in claim_v2["content"]
    assert "整个周末不工作的通常习惯" in claim_v2["content"]

    # The ordinary calendar Observation must not directly wake resident cognition.
    # Background periodic_review wakes are allowed; no observation-trigger wake is.
    assert set(resident.wake_reasons).issubset(
        {"user_interaction", "periodic_review"}
    )

    # The final answer must be based on real AIOS recall, not the test's Python
    # variable containing the earlier text.
    assert resident.search_results
    assert any(
        item.get("object_type") == "claim"
        and item.get("revision") == 2
        and "项目" in str(item.get("excerpt", ""))
        for item in resident.search_results
    ), resident.search_results
    assert any(
        item.get("object_type") == "observation"
        and "项目周会" in str(item.get("excerpt", ""))
        for item in resident.search_results
    ), resident.search_results

    assert resident.final_response is not None
    assert "周六上午已经固定给项目会" in resident.final_response
    assert "不能凭空指定一个准确时间" in resident.final_response

    # Explicitly prove no duplicate competing cognition object was created for the
    # changed Saturday-morning routine; it is a forward revision of one claim.
    latest_claims = [
        item
        for item in target.store.list_payloads(subject_id=SUBJECT_ID)
        if item.get("object_type") == "claim"
        and item.get("object_id") == resident.revised_claim_ref["object_id"]
    ]
    assert latest_claims
