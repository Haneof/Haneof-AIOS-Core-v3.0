from datetime import datetime, timedelta

from aios_core.contracts.enums import SourceClass
from aios_core.ingest import RealityIngestService, RealityRecord, SourceAdapterSpec
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


EVENTS = (
    ("e01", "2026-09-01T16:15:00+00:00", "calendar", {"title": "陪家人复诊", "duration_minutes": 90}),
    ("e02", "2026-09-06T12:30:00+00:00", "conversation", "等家里恢复得差不多，我想把自己的运动和做饭节奏重新捡起来。"),
    ("n01", "2026-09-09T11:00:00+00:00", "conversation", "今天午饭一般般。"),
    ("e03", "2026-09-12T13:45:00+00:00", "order", {"item": "外卖", "price": 34}),
    ("e04", "2026-09-19T17:00:00+00:00", "conversation", "这阵子晚上经常得去家里帮忙，自己的安排有点乱。"),
    ("n02", "2026-09-23T10:00:00+00:00", "order", {"item": "洗衣液", "price": 17}),
    ("e05", "2026-09-27T11:45:00+00:00", "conversation", "今天真的什么都不想安排。"),
    ("e06", "2026-10-06T12:30:00+00:00", "note", "这周晚饭提前准备好，回去帮忙时就不用点外卖。"),
    ("e07", "2026-10-15T13:00:00+00:00", "conversation", "医生说恢复得不错，接下来需要我过去的次数可以慢慢减少。"),
    ("e08", "2026-10-24T14:30:00+00:00", "sensor", {"steps": 3100}),
    ("e09", "2026-11-03T14:45:00+00:00", "conversation", "最近少见朋友主要是时间被占了，不是我不想社交。"),
    ("e10", "2026-11-14T14:30:00+00:00", "calendar", {"title": "短时训练", "duration_minutes": 30}),
    ("e11", "2026-11-26T10:30:00+00:00", "note", "下个月如果情况稳定，恢复周三晚上的固定活动。"),
)


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


# Frozen resident semantic commit: 958a343bbdf585f1247049efdbcca579a7072777672a49b4c6cb0b56159bf264\n# This experiment intentionally remains non-production and oracle-free at runtime.\ndef test_frozen_self_resident_blind_replay_reaches_real_world_and_exposes_wake_gap(tmp_path):
    """Replay the already-frozen blind resident decisions through current Core.

    The semantic decisions in this test were fixed before the hidden oracle was
    opened. This test does not re-judge the life. It only verifies whether current
    AIOS Core can carry those frozen decisions through real WorldStore/Runtime
    mechanics.

    Expected architectural finding: non-conversation reality facts are persisted,
    but they do not independently wake the Resident Runtime yet. Therefore the
    final e11 note is present in WorldStore but cannot create the frozen task
    candidate until a later user turn or future periodic/event review stage.
    """

    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    subject_id = "synthetic-user-001"
    reality = RealityIngestService(store=store, index=index, subject_id=subject_id)

    adapters = {
        "calendar": SourceAdapterSpec(
            adapter_id="blind.calendar.v1",
            source_kind="calendar",
            dimension="dim:calendar",
            source_class=SourceClass.USER,
            default_modality="structured_record",
        ),
        "order": SourceAdapterSpec(
            adapter_id="blind.order.v1",
            source_kind="order",
            dimension="dim:order",
            source_class=SourceClass.USER,
            default_modality="structured_record",
        ),
        "note": SourceAdapterSpec(
            adapter_id="blind.note.v1",
            source_kind="note",
            dimension="dim:notes",
            source_class=SourceClass.USER,
            default_modality="text",
        ),
        "sensor": SourceAdapterSpec(
            adapter_id="blind.activity.v1",
            source_kind="activity",
            dimension="dim:activity",
            source_class=SourceClass.SENSOR,
            default_modality="structured_record",
        ),
    }

    reality_refs: dict[str, dict[str, object]] = {}
    conversation_refs: dict[str, dict[str, object]] = {}
    state: dict[str, object] = {}
    plan = {"event_id": ""}

    def current_ref(snapshot):
        return dict(snapshot.cockpit["task_context"]["current_user_observation_ref"])

    def model(snapshot):
        event_id = plan["event_id"]
        history = snapshot.capability_history
        now_ref = current_ref(snapshot)

        if event_id == "e02":
            if not history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="commit_claim",
                            arguments={
                                "content": "当前家庭恢复支持可能正在暂时打乱用户自己的日常节奏。",
                                "evidence_refs": [reality_refs["e01"], now_ref],
                                "confidence": 0.76,
                                "dimension": "dim:ai_user_understanding",
                            },
                        ),
                    )
                )
            if len(history) == 1:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="propose_goal",
                            arguments={
                                "source_type": "user_explicit",
                                "title": "恢复运动和做饭节奏",
                                "description": "等家庭恢复支持负载下降后，逐步恢复用户自己的运动和做饭节奏。",
                                "evidence_refs": [now_ref],
                                "confidence": 0.83,
                                "success_criteria": ["运动和做饭节奏重新稳定出现"],
                            },
                        ),
                    )
                )
            if len(history) == 2:
                goal = history[-1].data
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="transition_goal",
                            arguments={
                                "goal_ref": {
                                    "object_id": goal["goal_id"],
                                    "revision": goal["revision"],
                                },
                                "new_status": "active",
                                "reason": "用户明确表达想在家里恢复后把自己的运动和做饭节奏重新捡起来。",
                                "evidence_refs": [now_ref],
                            },
                        ),
                    )
                )
            return ModelDirective(response="先保留这个恢复目标，不替你自动安排外部动作。")

        if event_id == "e04":
            if not history:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="propose_dimension",
                            arguments={
                                "dimension_key": "dim:family_recovery_support_load",
                                "name": "家庭恢复支持负载",
                                "description": "观察家庭恢复期间对用户时间和个人日常节奏的持续占用变化。",
                                "data_shape": "evidence_grounded_context_over_time",
                                "evidence_refs": [
                                    reality_refs["e01"],
                                    conversation_refs["e02"],
                                    now_ref,
                                ],
                                "why_existing_dimensions_are_insufficient": "日历、对话和消费事实能记录单次事件，但不能单独表达跨来源、跨周持续变化的家庭支持负载。",
                                "continuity_rationale": "后续复诊、帮忙频率和个人活动恢复情况可以持续更新这一观察轴。",
                                "user_value_rationale": "有助于避免把临时生活扰动误判为长期偏好变化。",
                                "maintenance_cost_rationale": "只记录有证据的负载变化，不复制原始事实；恢复结束后应进入低活动、休眠或归档。",
                                "confidence": 0.90,
                            },
                        ),
                    )
                )
            if len(history) == 1:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="commit_claim",
                            arguments={
                                "content": "用户当前多周家庭恢复支持负载正在打乱自己的晚间安排。",
                                "evidence_refs": [
                                    reality_refs["e01"],
                                    conversation_refs["e02"],
                                    now_ref,
                                ],
                                "confidence": 0.90,
                                "dimension": "dim:ai_user_understanding",
                            },
                        ),
                    )
                )
            return ModelDirective(response="这个负载先作为候选观察轴继续验证。")

        if event_id in {"n01", "e05"}:
            return ModelDirective(response="记录当前事实，不把单次状态扩张成长期结论。")

        if event_id == "e07":
            if not history:
                # All world facts in this experiment must belong to one resident subject.\n    assert {item.get("subject_id") for item in store.list_payloads() if item.get("subject_id")} == {subject_id}\n\n    dim_ref = state["dimension_ref"]
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="transition_dimension",
                            arguments={
                                "dimension_ref": dim_ref,
                                "new_lifecycle": "trial",
                                "reason": "该观察轴已跨多周、多来源出现，且仍需要继续观察恢复过程。",
                                "evidence_refs": [reality_refs["e06"], now_ref],
                            },
                        ),
                    )
                )
            if len(history) == 1:
                claim_ref = state["load_claim_ref"]
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="revise_claim",
                            arguments={
                                "target_ref": claim_ref,
                                "reason": "医生反馈恢复良好，用户需要过去帮忙的次数将逐步减少。",
                                "evidence_refs": [reality_refs["e06"], now_ref],
                                "replacement_content": "家庭恢复支持负载仍然存在，但正在随着恢复进展开始下降。",
                                "confidence": 0.97,
                            },
                        ),
                    )
                )
            return ModelDirective(response="旧的高负载历史保留，但当前状态已经修正为逐步下降。")

        if event_id == "e09":
            if not history:
                dim_ref = state["dimension_ref"]
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="transition_dimension",
                            arguments={
                                "dimension_ref": dim_ref,
                                "new_lifecycle": "active",
                                "reason": "这一负载轴已经解释并串联了多周时间占用、做饭、运动和社交可用性变化，同时仍处于恢复期。",
                                "evidence_refs": [now_ref],
                            },
                        ),
                    )
                )
            if len(history) == 1:
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="commit_claim",
                            arguments={
                                "content": "用户最近减少社交主要是可用时间被占用，而不是社交意愿下降。",
                                "evidence_refs": [now_ref],
                                "confidence": 0.97,
                                "dimension": "dim:ai_user_understanding",
                            },
                        ),
                    )
                )
            return ModelDirective(response="不把临时没时间见朋友误判成社交兴趣下降。")

        raise AssertionError(f"unexpected resident wake for {event_id}")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        subject_id=subject_id,
        max_tool_rounds=6,
    )

    turn_index = 0
    for event_id, occurred_raw, channel, payload in EVENTS:
        occurred_at = _dt(occurred_raw)
        if channel != "conversation":
            receipt = reality.ingest_record(
                adapters[channel],
                RealityRecord(
                    external_record_id=event_id,
                    occurred_at=occurred_at,
                    received_at=occurred_at + timedelta(minutes=1),
                    value=payload,
                    source_locator=f"blind://{channel}/{event_id}",
                    provenance={"fixture": "strict-sequential-self-resident"},
                ),
            )
            reality_refs[event_id] = {
                "object_id": receipt.observation_id,
                "revision": 1,
            }
            continue

        turn_index += 1
        plan["event_id"] = event_id
        result = runtime.run_turn(
            session_id="blind-self-resident",
            turn_index=turn_index,
            user_input=str(payload),
            current_topic=None,
            occurred_at=occurred_at,
        )
        conversation_refs[event_id] = {
            "object_id": result.conversation_commit.user_observation_id,
            "revision": 1,
        }

        names = [item.name for item in result.runtime.capability_history]
        if event_id == "e02":
            assert names == ["commit_claim", "propose_goal", "transition_goal"]
            state["early_claim_ref"] = {
                "object_id": result.runtime.capability_history[0].data["claim_id"],
                "revision": 1,
            }
            goal_transition = result.runtime.capability_history[2].data
            state["goal_ref"] = {
                "object_id": goal_transition["goal_id"],
                "revision": goal_transition["revision"],
            }
        elif event_id == "e04":
            assert names == ["propose_dimension", "commit_claim"]
            dimension = result.runtime.capability_history[0].data
            state["dimension_ref"] = {
                "object_id": dimension["dimension_id"],
                "revision": 1,
            }
            load_claim = result.runtime.capability_history[1].data
            state["load_claim_ref"] = {
                "object_id": load_claim["claim_id"],
                "revision": 1,
            }
        elif event_id == "e07":
            assert names == ["transition_dimension", "revise_claim"]
            dimension = result.runtime.capability_history[0].data
            state["dimension_ref"] = {
                "object_id": dimension["dimension_id"],
                "revision": dimension["new_revision"],
            }
            revised = result.runtime.capability_history[1].data
            state["load_claim_ref"] = {
                "object_id": revised["claim_id"],
                "revision": revised["new_revision"],
            }
        elif event_id == "e09":
            assert names == ["transition_dimension", "commit_claim"]
            dimension = result.runtime.capability_history[0].data
            state["dimension_ref"] = {
                "object_id": dimension["dimension_id"],
                "revision": dimension["new_revision"],
            }
            social = result.runtime.capability_history[1].data
            state["social_claim_ref"] = {
                "object_id": social["claim_id"],
                "revision": 1,
            }
        else:
            assert names == []

    dim_ref = state["dimension_ref"]
    assert store.get_payload(dim_ref["object_id"], revision=1)["lifecycle"] == "candidate"
    assert store.get_payload(dim_ref["object_id"], revision=2)["lifecycle"] == "trial"
    assert store.get_payload(dim_ref["object_id"], revision=3)["lifecycle"] == "active"

    load_ref = state["load_claim_ref"]
    assert "正在打乱自己的晚间安排" in store.get_payload(
        load_ref["object_id"], revision=1
    )["content"]
    assert "开始下降" in store.get_payload(
        load_ref["object_id"], revision=2
    )["content"]

    social_ref = state["social_claim_ref"]
    assert "不是社交意愿下降" in store.get_payload(
        social_ref["object_id"], revision=1
    )["content"]

    goal_ref = state["goal_ref"]
    assert store.get_payload(goal_ref["object_id"], revision=1)["goal_status"] == "proposed"
    assert store.get_payload(goal_ref["object_id"], revision=2)["goal_status"] == "active"

    # Final calendar + note facts really are in the same unified world.
    assert store.get_payload(reality_refs["e10"]["object_id"])["source_kind"] == "calendar"
    assert "恢复周三晚上的固定活动" in store.get_payload(
        reality_refs["e11"]["object_id"]
    )["value"]

    objects = store.list_payloads()
    assert not any(item.get("object_type") == "action" for item in objects)

    # Architectural finding from this self-test:
    # e11 is a non-conversation reality fact and no later user turn occurs.
    # Current Core persists it, but does not autonomously wake resident cognition
    # to create the frozen conditional task candidate. P15 periodic/event review
    # (or an equivalent resident wake path) is still required for that closure.
    assert not any(item.get("object_type") == "task" for item in objects)
