"""跨维度归属：宪法 3.2 / 总结宪法二 / 全维投影宪法八 的守护栏。

这一组测试守的不是"功能能用"，而是**边界没被越过**：

- 一条事实可以同时属于多个维度（多维世界宪法 3.2）——但原文不许改写；
- 跨维判断不可以写成事实 Summary（维度总结宪法二 + 全维投影宪法禁止事项 4）
  ——所以它必须是 Claim，且默认不进总结；
- 新维度不许在归属时顺手造（维度注册宪法二）——目标必须来自封闭目录；
- 系统不许用数字阈值替 AI 判断（同上）——低置信度也要照收。
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent, utc_now
from aios_core.prompts import (
    PromptRenderParams,
    TaskKind,
    DimensionProfile,
    get_prompt,
    render_task_prompt,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries.cross_link import CrossLinkService, dimensions_from_index
from aios_core.summaries.dimension_summary import (
    DimensionSummaryService,
    DimensionSummarySource,
)

SUBJECT = "user_1"


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------


def _operation(expected: int) -> OperationRequest:
    return OperationRequest(
        operation_id=str(uuid.uuid4()),
        operation_name="test",
        arguments={},
        expected_world_revision=expected,
        reason="cross-dimension test",
        idempotency_key=str(uuid.uuid4()),
    )


def _observation(object_id: str, text: str, *, dimension: str, when=None, **metadata):
    now = utc_now()
    return Observation(
        object_id=object_id,
        subject_id=SUBJECT,
        learned_at=now,
        recorded_at=now,
        occurred=TemporalExtent.point(when or now - timedelta(hours=2)),
        created_by="test",
        source_kind="chat",
        modality="text",
        value={"text": text},
        metadata={"dimension": dimension, **metadata},
    )


@pytest.fixture()
def env(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    index = WorldSearchIndex(tmp_path / "index.db", store=store)
    observations = [
        _observation("obs_wedding", "阿杰邀请我下周六去参加他的婚礼",
                     dimension="dim:user_ai_interaction"),
        _observation("obs_market", "今天菜市场买排骨花了八十块",
                     dimension="dim:user_ai_interaction"),
    ]
    store.commit(observations, _operation(0))
    index.catch_up()
    service = CrossLinkService(store=store, index=index, subject_id=SUBJECT)
    return store, index, service


def _prepare(service: CrossLinkService, *, targets=("dim:social", "dim:expense")):
    now = utc_now()
    return service.prepare(
        window_start=now - timedelta(days=1),
        window_end=now + timedelta(minutes=1),
        target_dimensions=targets,
    )


def _items(service: CrossLinkService, prepared, raw=None):
    payload = raw or [
        {
            "id": "obs_wedding",
            "target_dimension": "dim:social",
            "statement": "阿杰邀请用户参加下周六的婚礼",
            "confidence": 0.82,
            "reason": "社交邀约",
        }
    ]
    return service.parse_items(prepared, payload)


# --------------------------------------------------------------------------
# 1. 宪法 3.2：一个事件可以同时属于多个维度
# --------------------------------------------------------------------------


def test_a_fact_can_be_found_through_its_additional_axis(env):
    """一条记录带 also_dimensions 时，目标维度必须查得到它。

    宪法 3.2 的原文是"一个事件可以同时属于多个维度"。如果索引按单值切分，
    这句话在实现层就是不成立的。"""

    store, index, _ = env
    store.commit(
        [_observation(
            "obs_shared", "和阿杰吃饭时聊到婚礼安排",
            dimension="dim:user_ai_interaction",
            also_dimensions=["dim:social"],
        )],
        _operation(int(store.current_world_revision())),
    )
    index.catch_up()

    social = index.search_mind(subject=SUBJECT, dimension="dim:social")
    assert [hit.object_id for hit in social.hits] == ["obs_shared"]


def test_additional_axis_does_not_rewrite_the_primary_one(env):
    """多维归属是"多看一眼"，不是搬迁：主维度与原文都必须原样保留。

    《证据宪法》二：Observation 一旦写入，不得因为后来的理解改变而修改其原始含义。"""

    store, index, _ = env
    social = index.search_mind(subject=SUBJECT, dimension="dim:social")
    for hit in social.hits:
        payload = store.get_payload(hit.object_id)
        assert payload["metadata"]["dimension"] == "dim:user_ai_interaction"
        assert payload["value"]["text"].startswith("阿杰邀请")


def test_unrelated_axis_still_misses(env):
    """放宽归属不能变成"什么都能查到"——支付维度没有这两条事实。"""

    _, index, _ = env
    assert index.search_mind(subject=SUBJECT, dimension="dim:payment").hits == []


# --------------------------------------------------------------------------
# 2. 维度注册宪法二：不许在归属时顺手造维度
# --------------------------------------------------------------------------


def test_target_outside_the_catalogue_is_rejected(env):
    """模型自造一个目录外维度，必须当场失败，而不是被容错成新维度。

    宪法要求新维度走 Candidate → … 的生命周期，一条归属语句没有资格跳过它。"""

    _, _, service = env
    prepared = _prepare(service)
    with pytest.raises(ValueError, match="outside the catalogue"):
        service.parse_items(
            prepared,
            [{
                "id": "obs_wedding",
                "target_dimension": "dim:friendship_feelings",
                "statement": "用户很重视这段友谊",
                "confidence": 0.9,
            }],
        )


def test_unknown_source_id_is_rejected(env):
    """指向本批次之外的事实，无法被验证，只能拒绝。"""

    _, _, service = env
    prepared = _prepare(service)
    with pytest.raises(ValueError, match="unknown source"):
        service.parse_items(
            prepared,
            [{
                "id": "obs_does_not_exist",
                "target_dimension": "dim:social",
                "statement": "无来源的判断",
                "confidence": 0.5,
            }],
        )


def test_catalogue_is_what_the_world_actually_contains(env):
    _, index, _ = env
    keys = dimensions_from_index(index, subject=SUBJECT)
    assert "dim:user_ai_interaction" in keys


# --------------------------------------------------------------------------
# 3. 维度注册宪法二：系统不得用数字阈值替 AI 判断
# --------------------------------------------------------------------------


def test_low_confidence_links_are_still_committed(env):
    """0.05 的归属也要照收。

    加一条"低于 0.6 就丢"的规则读起来很合理，但宪法明确禁止系统用固定数字
    回答语义问题（70% 是否等于有效维度）。置信度记录在 Claim 上，由下游权衡，
    机制不替 AI 删答案。"""

    store, index, service = env
    prepared = _prepare(service)
    items = service.parse_items(
        prepared,
        [{
            "id": "obs_market",
            "target_dimension": "dim:expense",
            "statement": "用户当天在菜市场支出 80 元",
            "confidence": 0.05,
            "reason": "金额",
        }],
    )
    result = service.commit(prepared, items, generated_at=utc_now())
    payload = store.get_payload(result.claim_ids[0])
    assert payload["confidence"] == pytest.approx(0.05)


# --------------------------------------------------------------------------
# 4. 全维投影宪法八：跨维意义是认知，不是事实
# --------------------------------------------------------------------------


def test_attribution_is_written_as_an_inference_not_a_fact(env):
    """落库对象必须是 INFERRED 的 Claim，而不是伪装成观测或总结。"""

    store, index, service = env
    prepared = _prepare(service)
    result = service.commit(prepared, _items(service, prepared), generated_at=utc_now())

    claim = store.get_payload(result.claim_ids[0])
    assert claim["object_type"] == "claim"
    assert claim["claim_type"] == "inference"
    assert claim["knowledge_state"] == "inferred"
    assert claim["support_evidence_set_refs"], "认知必须能追溯到证据"

    # 原文一个字节都没动
    original = store.get_payload("obs_wedding")
    assert int(original["revision"]) == 1
    assert original["value"]["text"] == "阿杰邀请我下周六去参加他的婚礼"


def test_claim_lives_in_the_target_axis_and_points_back(env):
    """Claim 住在目标维度，同时保留指回来源的指针。"""

    store, index, service = env
    prepared = _prepare(service)
    result = service.commit(prepared, _items(service, prepared), generated_at=utc_now())

    claim = store.get_payload(result.claim_ids[0])
    meta = claim["metadata"]
    assert meta["dimension"] == "dim:social"
    assert meta["source_dimension"] == "dim:user_ai_interaction"
    assert meta["source_object_id"] == "obs_wedding"
    assert meta["source_revision"] == 1

    social = index.search_mind(subject=SUBJECT, dimension="dim:social")
    assert [hit.object_id for hit in social.hits] == [result.claim_ids[0]]


def test_repeated_commit_is_idempotent(env):
    """同一批归属重复提交：复用，不产生新版本。"""

    store, index, service = env
    prepared = _prepare(service)
    first = service.commit(prepared, _items(service, prepared), generated_at=utc_now())
    second = service.commit(prepared, _items(service, prepared), generated_at=utc_now())

    assert second.claim_ids == first.claim_ids
    assert second.reused_claim_ids == first.claim_ids
    assert second.world_revision == first.world_revision


def test_conflicting_restatement_is_refused(env):
    """同一事实、同一目标，内容却变了：拒绝而不是静默改写认知。

    改写要走 revise/retract，留下旧 revision；否则历史认知会凭空消失。"""

    store, index, service = env
    prepared = _prepare(service)
    service.commit(prepared, _items(service, prepared), generated_at=utc_now())

    changed = [{
        "id": "obs_wedding",
        "target_dimension": "dim:social",
        "statement": "阿杰取消了婚礼邀请",
        "confidence": 0.5,
    }]
    with pytest.raises(ValueError, match="already attributed differently"):
        service.commit(prepared, service.parse_items(prepared, changed),
                       generated_at=utc_now())


# --------------------------------------------------------------------------
# 5. 维度总结宪法二：总结默认不吃认知，开了也必须标清楚
# --------------------------------------------------------------------------


def _summary_service(store, index):
    return DimensionSummaryService(store=store, index=index, subject_id=SUBJECT)


def test_summary_ignores_cognition_by_default(env):
    """默认关闭。否则每个维度的总结都会悄悄开始引用别人的判断。"""

    store, index, service = env
    prepared = _prepare(service)
    service.commit(prepared, _items(service, prepared), generated_at=utc_now())

    now = utc_now()
    summary = _summary_service(store, index).prepare(
        dimension="dim:social", granularity="day",
        window_start=now - timedelta(days=1), window_end=now + timedelta(minutes=1),
    )
    assert summary.sources == ()


def test_summary_can_opt_in_and_labels_cognition(env):
    """开了以后：源里出现该 Claim，且明确标成 cognition。"""

    store, index, service = env
    prepared = _prepare(service)
    service.commit(prepared, _items(service, prepared), generated_at=utc_now())

    now = utc_now()
    summary = _summary_service(store, index).prepare(
        dimension="dim:social", granularity="day",
        window_start=now - timedelta(days=1), window_end=now + timedelta(minutes=1),
        include_cognition_sources=True,
    )
    assert len(summary.sources) == 1
    assert summary.sources[0].source_class == "cognition"
    assert summary.sources[0].text == "阿杰邀请用户参加下周六的婚礼"


def test_summary_counts_facts_and_beliefs_separately(env):
    """总结落库后，覆盖率必须能回答"这条总结几分事实、几分认知"。"""

    store, index, service = env
    prepared = _prepare(service)
    service.commit(prepared, _items(service, prepared), generated_at=utc_now())

    now = utc_now()
    svc = _summary_service(store, index)
    summary = svc.prepare(
        dimension="dim:social", granularity="day",
        window_start=now - timedelta(days=1), window_end=now + timedelta(minutes=1),
        include_cognition_sources=True,
    )
    committed = svc.commit(summary, content="据聊天记录，阿杰邀请用户参加婚礼。",
                           generated_at=now)
    coverage = store.get_payload(committed.object_id)["coverage"]
    assert coverage["cognition_source_count"] == 1
    assert coverage["observation_source_count"] == 0


def test_a_fact_cannot_be_mislabelled_as_cognition():
    """调用方不能把观测标成"认知"来给自己开路。"""

    with pytest.raises(ValueError, match="source_class"):
        DimensionSummarySource(
            object_id="obs_x", revision=1, object_type="observation",
            text="x", source_class="cognition",
        )


def test_summary_rejects_a_tampered_source_at_commit(env):
    """即使绕过 prepare 直接伪造源文本，commit 也会按 pinned revision 对回去。

    这条守的是"总结必须引用真实存在的内容"——否则调用方可以把一句判断写成
    源文本，再让总结把它当成事实复述。"""

    store, index, _ = env
    now = utc_now()
    svc = _summary_service(store, index)
    prepared = svc.prepare(
        dimension="dim:social", granularity="day",
        window_start=now - timedelta(days=1), window_end=now + timedelta(minutes=1),
    )
    forged = prepared.model_copy(
        update={
            "sources": (
                DimensionSummarySource(
                    object_id="obs_wedding", revision=1, object_type="observation",
                    occurred_at=prepared.window_start,
                    text="阿杰已经答应出资办婚礼",
                    metadata={"dimension": "dim:user_ai_interaction"},
                ),
            )
        }
    )
    with pytest.raises(ValueError):
        svc.commit(forged, content="伪造的总结", generated_at=now)


# --------------------------------------------------------------------------
# 6. 提示词契约：跨维任务不是总结任务
# --------------------------------------------------------------------------


def _cross_link_prompt() -> str:
    return render_task_prompt(
        TaskKind.CROSS_LINK,
        params=PromptRenderParams(
            records=(
                {"id": "m01", "text": "阿杰邀请我下周六去婚礼",
                 "dimension": "dim:user_ai_interaction"},
            ),
            dimensions=(
                DimensionProfile(dimension_key="dim:social", name="社交关系"),
            ),
        ),
    )


def test_cross_link_prompt_is_not_a_summary_prompt():
    """防止有人把跨维判断塞回总结任务：两个任务的正文必须不同，且各说各的职责。"""

    prompt = _cross_link_prompt()
    assert "跨维度归属" in prompt
    assert "单维度单尺度总结" not in prompt
    assert get_prompt(TaskKind.CROSS_LINK).output_contract.startswith("json[")


def test_cross_link_prompt_forbids_conclusions_and_invented_axes():
    """提示词必须明说两件不能做的事，否则模型会把归属写成结论、把目标写飞。"""

    prompt = _cross_link_prompt()
    assert "不要评价人" in prompt
    assert "目录里没有的维度一律不许出现" in prompt
    assert "dim:social" in prompt


def test_cross_link_prompt_blocks_empty_catalogue():
    """没有维度目录时，唯一合法的输出是空数组——不给模型造维度的机会。"""

    prompt = render_task_prompt(
        TaskKind.CROSS_LINK,
        params=PromptRenderParams(
            records=({"id": "m01", "text": "随便一句", "dimension": "dim:x"},),
            dimensions=(),
        ),
    )
    assert "只允许输出空数组" in prompt
