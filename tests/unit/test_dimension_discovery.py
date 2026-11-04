"""新维度发现（DISCOVER_DIMENSION）—— 单元守护栏。

对应《维度注册宪法》十四 + 周期复盘 §2 的落地：

  * 发现与注册归「总结 / 周期复盘 AI」（DimensionDiscoveryService），不在实时对话；
  * 注册门（注册门）是**认知门槛**——必须核对已有维度、证明模式「反复出现且连贯、
    而非孤立事件」、给出用户价值与维护成本；系统只做结构校验，**不设固定数字阈值**
    （宪法二/五，P16 ``recurrence_gated_not_single_event``）；
  * 证据 id 必须来自真实信号，不得伪造；
  * 噪声（无复发模式）应得到**空数组**，而不是硬凑一个新轴；
  * 同一提案幂等：重复 commit 不写第二份维度定义。

这些断言把「漏登记 / 绕过注册门 / 伪造证据 / 噪声却立轴」当场变红，而不是在真实
运行里悄悄发生。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import ClaimType, KnowledgeState, ObjectType, SourceClass
from aios_core.contracts.models import Claim
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.dimensions import (
    DimensionProposalGate,
    DimensionProposalRequest,
    DimensionRegistryService,
)
from aios_core.dimensions.registry import (
    DimensionDefinition,
)
from aios_core.prompts.contracts import TaskKind
from aios_core.prompts.registry import PROMPT_REGISTRY, get_prompt, render_task_prompt
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries.dimension_discovery import (
    DimensionDiscoveryInput,
    DimensionDiscoveryItem,
    DimensionDiscoveryService,
    DiscoveryGate,
    EvidenceRef,
)

UTC = timezone.utc
NOW = datetime(2026, 9, 28, 12, tzinfo=UTC)
SUBJECT = "user_1"
EXISTING_KEY = "dim:user_ai_interaction"


def _store(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _claim(object_id: str, text: str, *, at: datetime, dimension: str = EXISTING_KEY) -> Claim:
    return Claim(
        object_id=object_id,
        subject_id=SUBJECT,
        occurred=TemporalExtent.point(at),
        learned_at=at,
        recorded_at=at,
        created_by="discovery-test",
        claimant_id=SUBJECT,
        claim_type=ClaimType.INFERENCE,
        content=text,
        asserted_at=at,
        knowledge_state=KnowledgeState.REPORTED,
        confidence=0.7,
        metadata={"dimension": dimension},
    )


def _seed_claim(store: SQLiteWorldStore, claim: Claim) -> None:
    store.commit(
        [claim],
        OperationRequest(
            operation_name="discovery.seed",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed discovery signal",
            idempotency_key=f"discovery-seed-{claim.object_id}",
            source_class=SourceClass.USER,
        ),
    )


def _seed_dimension(store: SQLiteWorldStore, *, dimension_key: str, name: str) -> None:
    """File an existing axis through the constitutional registry path.

    The proposal needs a real, existing evidence object (the registry checks the
    ref resolves to a payload in this subject's scope), so one is seeded first —
    deliberately outside the discovery window so it never pollutes the signal set.
    """
    seed_evidence = _claim(
        "seed_evidence", "seed evidence for dimension collision tests",
        at=NOW - timedelta(days=30),
    )
    store.commit(
        [seed_evidence],
        OperationRequest(
            operation_name="discovery.seed",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed dimension evidence",
            idempotency_key="discovery-seed-evidence",
            source_class=SourceClass.USER,
        ),
    )
    service = DimensionRegistryService(store=store)
    service.propose(
        DimensionProposalRequest(
            dimension_key=dimension_key,
            name=name,
            description="seed axis for discovery collision tests",
            data_shape="scalar",
            evidence_refs=(ObjectRef(object_id="seed_evidence", revision=1),),
            why_existing_dimensions_are_insufficient="seeded",
            continuity_rationale="seeded recurring observation",
            user_value_rationale="seeded value",
            maintenance_cost_rationale="seeded cost",
            confidence=0.5,
            registration_gate=DimensionProposalGate(
                duplicate_checked_keys=(),
                recurrence_rationale="seeded recurring observation across turns",
                is_novel_axis_reason="seeded novel axis not covered by existing dimensions",
            ),
        ),
        proposed_at=NOW - timedelta(days=30),
    )


def _service(store, index):
    return DimensionDiscoveryService(
        store=store,
        index=index,
        dimension_registry=DimensionRegistryService(store=store),
        subject_id=SUBJECT,
        signal_lookback_days=14,
    )


def _window():
    return NOW - timedelta(days=7), NOW + timedelta(hours=1)


def _gate() -> dict:
    return {
        "duplicate_checked_keys": [EXISTING_KEY],
        "recurrence_rationale": "该身体信号在两周内反复出现 4 次且未自行缓解。",
        "is_novel_axis_reason": "现有通道型维度会把跨通道的身体信号拆散，看不到整体趋势。",
    }


def _proposal(dimension_key: str, *, evidence_ids, name="身体状态") -> dict:
    return {
        "dimension_key": dimension_key,
        "name": name,
        "description": "持续出现的身体信号及其触发与进展，作为独立观察轴。",
        "data_shape": "time series of {symptom, trigger, severity}",
        "evidence_record_ids": [{"object_id": oid, "revision": 1} for oid in evidence_ids],
        "why_existing_dimensions_are_insufficient": "现有轴都是来源通道，无法承载跨通道的连续身体信号。",
        "continuity_rationale": "该信号在两周内反复出现 4 次。",
        "user_value_rationale": "让后续复盘把身体信号当趋势看，而非孤立抱怨。",
        "maintenance_cost_rationale": "每周一次总结即可。",
        "confidence": 0.7,
        "gate": _gate(),
    }


# --------------------------------------------------------------------------
# 1. prepare：目录与信号
# --------------------------------------------------------------------------


def test_prepare_collects_catalogue_and_recent_signals(tmp_path):
    store, index = _store(tmp_path)
    _seed_dimension(store, dimension_key=EXISTING_KEY, name="人机互动")
    _seed_claim(store, _claim("clm_a", "反酸烧心，饭后躺下更明显", at=NOW - timedelta(days=1)))
    _seed_claim(store, _claim("clm_b", "今早又反酸了", at=NOW))

    prepared = _service(store, index).prepare(window_start=NOW - timedelta(days=7),
                                              window_end=NOW + timedelta(hours=1))

    assert isinstance(prepared, DimensionDiscoveryInput)
    keys = {p.dimension_key for p in prepared.catalogue}
    assert EXISTING_KEY in keys
    signal_ids = {s.object_id for s in prepared.signals}
    assert {"clm_a", "clm_b"} <= signal_ids
    # 信号类型被限为 claim / summary，observation 不会混进来
    assert all(s.object_type in {"claim", "summary"} for s in prepared.signals)


# --------------------------------------------------------------------------
# 2. parse_items：注册门是硬门槛
# --------------------------------------------------------------------------


def _prepared_with_signals(tmp_path, *claim_ids):
    store, index = _store(tmp_path)
    for i, cid in enumerate(claim_ids):
        _seed_claim(store, _claim(cid, f"信号 {i}", at=NOW - timedelta(days=i)))
    svc = _service(store, index)
    return svc, svc.prepare(window_start=NOW - timedelta(days=7),
                            window_end=NOW + timedelta(hours=1))


def test_parse_accepts_gate_complete_proposal_citing_real_evidence(tmp_path):
    svc, prepared = _prepared_with_signals(tmp_path, "clm_a", "clm_b")

    items = svc.parse_items(prepared, [_proposal("dim:physical_condition",
                                                 evidence_ids=["clm_a", "clm_b"])])

    assert len(items) == 1
    item = items[0]
    assert isinstance(item, DimensionDiscoveryItem)
    assert item.dimension_key == "dim:physical_condition"
    assert item.gate.recurrence_rationale  # 注册门被完整保留，可被审计
    assert {r.object_id for r in item.evidence_record_ids} == {"clm_a", "clm_b"}


def test_parse_rejects_proposal_without_gate(tmp_path):
    svc, prepared = _prepared_with_signals(tmp_path, "clm_a")
    bad = _proposal("dim:physical_condition", evidence_ids=["clm_a"])
    del bad["gate"]  # 绕过注册门：缺 gate 块

    with pytest.raises(ValueError):
        svc.parse_items(prepared, [bad])


def test_parse_rejects_proposal_with_empty_recurrence_rationale(tmp_path):
    svc, prepared = _prepared_with_signals(tmp_path, "clm_a")
    bad = _proposal("dim:physical_condition", evidence_ids=["clm_a"])
    bad["gate"] = {"duplicate_checked_keys": [], "recurrence_rationale": "",
                   "is_novel_axis_reason": "x"}

    with pytest.raises(ValueError):
        svc.parse_items(prepared, [bad])


def test_parse_rejects_key_collision_with_existing_catalogue(tmp_path):
    store, index = _store(tmp_path)
    _seed_dimension(store, dimension_key=EXISTING_KEY, name="人机互动")
    # 一条真实信号，让证据校验先过、再触达 key 冲突检查。
    _seed_claim(store, _claim("clm_x", "任意信号", at=NOW - timedelta(days=1)))
    svc = _service(store, index)
    prepared = svc.prepare(window_start=NOW - timedelta(days=7),
                           window_end=NOW + timedelta(hours=1))

    # 想用已存在的 key 立轴 —— 系统只做精确 key 冲突检查，语义相似不否决。
    with pytest.raises(ValueError, match="already exists"):
        svc.parse_items(prepared, [_proposal(EXISTING_KEY, evidence_ids=["clm_x"])])


def test_parse_rejects_fabricated_evidence_id(tmp_path):
    svc, prepared = _prepared_with_signals(tmp_path, "clm_real")

    # 引用一个不在信号批次里的 id —— 等于凭空造证据。
    with pytest.raises(ValueError, match="not in this batch"):
        svc.parse_items(prepared, [_proposal("dim:physical_condition",
                                             evidence_ids=["clm_real", "clm_fake"])])


def test_parse_rejects_dimension_key_without_dim_prefix(tmp_path):
    svc, prepared = _prepared_with_signals(tmp_path, "clm_a")
    bad = _proposal("physical_condition", evidence_ids=["clm_a"])  # 缺 dim: 前缀

    with pytest.raises(ValueError, match="dim:"):
        svc.parse_items(prepared, [bad])


# --------------------------------------------------------------------------
# 3. commit：立为 Candidate，且注册门耐久写入
# --------------------------------------------------------------------------


def test_commit_writes_candidate_with_recorded_gate(tmp_path):
    store, index = _store(tmp_path)
    _seed_dimension(store, dimension_key=EXISTING_KEY, name="人机互动")
    _seed_claim(store, _claim("clm_a", "反酸烧心", at=NOW - timedelta(days=2)))
    _seed_claim(store, _claim("clm_b", "今早又反酸", at=NOW))
    svc = _service(store, index)
    prepared = svc.prepare(window_start=NOW - timedelta(days=7),
                           window_end=NOW + timedelta(hours=1))
    items = svc.parse_items(prepared, [_proposal("dim:physical_condition",
                                                 evidence_ids=["clm_a", "clm_b"])])

    commit = svc.commit(prepared, items, generated_at=NOW)

    assert len(commit.proposal_receipts) == 1
    receipt = commit.proposal_receipts[0]
    assert receipt["dimension_key"] == "dim:physical_condition"
    assert receipt["lifecycle"] == "candidate"

    definition = store.get_payload(receipt["dimension_id"])
    assert definition["lifecycle"] == "candidate"
    # 注册门被耐久写入，决策可审计（宪法四/十四）。
    gate = definition["metadata"]["proposal"]["registration_gate"]
    assert gate["recurrence_rationale"]
    assert gate["is_novel_axis_reason"]


def test_commit_is_idempotent_no_duplicate_dimension(tmp_path):
    """重复提案同一个 key（即使在不同时刻）必须失败关闭，绝不能写出第二份维度定义。"""
    store, index = _store(tmp_path)
    _seed_claim(store, _claim("clm_a", "反酸烧心", at=NOW - timedelta(days=2)))
    svc = _service(store, index)
    prepared = svc.prepare(window_start=NOW - timedelta(days=7),
                           window_end=NOW + timedelta(hours=1))
    items = svc.parse_items(prepared, [_proposal("dim:physical_condition",
                                                 evidence_ids=["clm_a"])])

    first = svc.commit(prepared, items, generated_at=NOW)
    assert len(first.proposal_receipts) == 1
    dimension_id = first.proposal_receipts[0]["dimension_id"]

    second = svc.commit(prepared, items, generated_at=NOW + timedelta(minutes=5))
    # 重复 key 被拒（不写第二份维度定义），而非复用或重复落库。
    assert second.proposal_receipts == ()
    assert any(key == "dim:physical_condition" for key, _ in second.failed)

    # 世界上始终只有一份该 key 的维度定义。
    definitions = [
        p for p in store.list_payloads(object_type=ObjectType.DIMENSION_DEFINITION,
                                       subject_id=SUBJECT)
        if (p.get("metadata") or {}).get("dimension_key") == "dim:physical_condition"
    ]
    assert len(definitions) == 1
    assert definitions[0]["object_id"] == dimension_id


def test_commit_empty_array_is_valid_answer_not_failure(tmp_path):
    store, index = _store(tmp_path)
    _seed_claim(store, _claim("noise_1", "今天天气不错", at=NOW))
    svc = _service(store, index)
    prepared = svc.prepare(window_start=NOW - timedelta(days=7),
                           window_end=NOW + timedelta(hours=1))

    # 噪声场景：模型诚实返回空数组 —— 这是正确的结果，不是失败。
    items = svc.parse_items(prepared, [])
    commit = svc.commit(prepared, items, generated_at=NOW)
    assert commit.proposal_receipts == ()
    assert commit.failed == ()
    assert commit.reused_dimension_keys == ()


def test_parse_rejects_empty_response_not_false_positive(tmp_path):
    store, index = _store(tmp_path)
    svc = _service(store, index)
    prepared = svc.prepare(window_start=NOW - timedelta(days=7),
                           window_end=NOW + timedelta(hours=1))

    # None（解析彻底失败）必须被显式拒绝，绝不能假装成「没有新轴」。
    with pytest.raises(ValueError, match="empty"):
        svc.parse_items(prepared, None)


# --------------------------------------------------------------------------
# 4. 提示词注册
# --------------------------------------------------------------------------


def test_discover_dimension_prompt_is_registered_and_renders():
    assert TaskKind.DISCOVER_DIMENSION in PROMPT_REGISTRY
    spec = get_prompt(TaskKind.DISCOVER_DIMENSION)
    assert spec.task == TaskKind.DISCOVER_DIMENSION

    rendered = render_task_prompt(
        TaskKind.DISCOVER_DIMENSION,
        params=DimensionDiscoveryInput(
            subject_id=SUBJECT,
            window_start=NOW - timedelta(days=7),
            window_end=NOW,
            source_world_revision=0,
            catalogue=(),
            signals=(),
            max_proposals=8,
        ).to_render_params(),
    )
    assert rendered.strip()
    # 宪法硬约束（注册门 / 门槛）出现在提示词里；空数组是被允许且鼓励的正确答案。
    assert "【注册门" in rendered
    assert "门槛" in rendered
    assert "宁缺毋滥" in rendered
