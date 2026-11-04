"""端到端验证：新维度发现（DISCOVER_DIMENSION）接入生产流水线。

对应《维度注册宪法》十四 + 周期复盘 §2：发现与注册归「总结 / 周期复盘 AI」，
不在实时对话；注册门是**认知门槛**（宪法四/八：核对已有轴、论证时间连续性、
说明未来如何更新），不设固定数字阈值（宪法二）；单条证据也可成 Candidate
（宪法五）。P16 ``recurrence_gated_not_single_event`` /
``noise_resilience_no_false_pattern`` 只是隐藏场景的评估标准，不是通用注册规则。

本脚本用 mock discovery handler 复现两个 P16 场景：
  1. 反复身体信号（跨多天、多 claim）→ 立 1 个 Candidate 轴，注册门耐久写入；
  2. 纯噪声（每条互不相关的孤立话题）→ 空数组，绝不硬凑一个新轴。

直接运行：python experiments/dimension_discovery/verify_discovery.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import Claim
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.dimensions import DimensionProposalGate, DimensionProposalRequest, DimensionRegistryService
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries.dimension_discovery import DimensionDiscoveryInput, DimensionDiscoveryService
from aios_core.summaries.scheduler import MultiScaleSummaryScheduler

UTC = timezone.utc
NOW = datetime(2026, 9, 28, 12, tzinfo=UTC)
SUBJECT = "user_1"
EXISTING_KEY = "dim:user_ai_interaction"


def _store() -> tuple[SQLiteWorldStore, WorldSearchIndex]:
    db = Path(tempfile.mkdtemp()) / "world.db"
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
        created_by="verify-discovery",
        claimant_id=SUBJECT,
        claim_type="inference",
        content=text,
        asserted_at=at,
        knowledge_state="reported",
        confidence=0.7,
        metadata={"dimension": dimension},
    )


def _seed_claim(store: SQLiteWorldStore, claim: Claim) -> None:
    store.commit(
        [claim],
        OperationRequest(
            operation_name="verify.seed",
            expected_world_revision=int(store.current_world_revision()),
            reason="verify discovery seed",
            idempotency_key=f"verify-seed-{claim.object_id}",
            source_class=SourceClass.USER,
        ),
    )


def _seed_dimension(store: SQLiteWorldStore, *, dimension_key: str, name: str) -> None:
    seed = _claim("seed_evidence", "seed evidence", at=NOW - timedelta(days=40))
    _seed_claim(store, seed)
    DimensionRegistryService(store=store).propose(
        DimensionProposalRequest(
            dimension_key=dimension_key,
            name=name,
            description="seed axis",
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
        proposed_at=NOW - timedelta(days=40),
    )


def _discovery_handler_factory(mode: str):
    """Mock 模型。recurrent 场景立身体轴，noise 场景返回空数组。"""

    def handler(prepared: DimensionDiscoveryInput) -> str:
        if mode == "noise":
            return "[]"  # 诚实地说：没有值得立的轴
        signals = list(prepared.signals)
        if not signals:
            return "[]"
        # 宪法五：单条证据也能成 Candidate，mock 不设次数门槛，只引用真实信号。
        cited = [{"object_id": s.object_id, "revision": s.revision} for s in signals[:2]]
        proposal = [{
            "dimension_key": "dim:physical_condition",
            "name": "身体状态",
            "description": "持续出现的身体信号及其触发与进展，作为独立观察轴。",
            "data_shape": "time series of {symptom, trigger, severity}",
            "evidence_record_ids": cited,
            "why_existing_dimensions_are_insufficient": "现有轴都是来源通道，无法承载跨通道的连续身体信号。",
            "continuity_rationale": "该信号跨多日持续且未自行缓解，具有长期观察价值。",
            "user_value_rationale": "让后续复盘把身体信号当趋势看，而非孤立抱怨。",
            "maintenance_cost_rationale": "每周一次总结即可。",
            "confidence": 0.7,
            "update_method": "每轮复盘把新出现的身体信号 Claim 追加进该轴，按周聚合，不改写原始事实。",
            "gate": {
                "duplicate_checked_keys": [EXISTING_KEY],
                "recurrence_rationale": "该信号跨多日持续、未自行缓解，是值得长期维护的观察需求而非一次性闲聊。",
                "is_novel_axis_reason": "现有通道型维度会把这个跨通道信号拆散，看不到整体。",
            },
        }]
        return json.dumps(proposal, ensure_ascii=False)

    return handler


def _scheduler(store, index, handler):
    return MultiScaleSummaryScheduler(
        store=store,
        index=index,
        summary_handler=lambda _x: "",
        subject_id=SUBJECT,
        discovery_service=DimensionDiscoveryService(
            store=store,
            index=index,
            dimension_registry=DimensionRegistryService(store=store),
            subject_id=SUBJECT,
        ),
        discovery_handler=handler,
    )


def _run(name: str) -> int:
    store, index = _store()
    _seed_dimension(store, dimension_key=EXISTING_KEY, name="人机互动")

    # 反复身体信号：5 条跨 5 天的 claim，全部落在发现窗口内。
    for i, text in enumerate([
        "反酸烧心，饭后躺下更明显",
        "今早脖子又僵了",
        "又反酸，这周第三次",
        "睡前胸口灼烧感",
        "肩颈酸痛持续一周了",
    ]):
        _seed_claim(store, _claim(f"clm_body_{i}", text, at=NOW - timedelta(days=5 - i)))

    scheduler = _scheduler(store, index, _discovery_handler_factory(name))
    commits = scheduler._run_discovery(now=NOW)
    return commits, store


def main() -> int:
    failures: list[str] = []

    # 场景 1：反复身体信号 → 立 1 个 Candidate 轴，注册门耐久写入。
    commits, store = _run("recurrent")
    assert len(commits) == 1, f"期望恰好 1 次 commit，实际 {len(commits)}"
    commit = commits[0]
    if len(commit.proposal_receipts) != 1:
        failures.append(f"场景1：期望 1 个提案，实际 {len(commit.proposal_receipts)}")
    else:
        receipt = commit.proposal_receipts[0]
        if receipt["dimension_key"] != "dim:physical_condition":
            failures.append(f"场景1：dimension_key 错：{receipt['dimension_key']}")
        if receipt["lifecycle"] != "candidate":
            failures.append(f"场景1：lifecycle 应为 candidate，实际 {receipt['lifecycle']}")
        definition = store.get_payload(receipt["dimension_id"])
        gate = (definition.get("metadata") or {}).get("proposal", {}).get("registration_gate")
        if not gate or not gate.get("recurrence_rationale"):
            failures.append("场景1：注册门未耐久写入（recurrence_rationale 缺失）")
    print(f"[场景1 反复身体信号] proposals={len(commit.proposal_receipts)} "
          f"failed={commit.failed} -> {'OK' if not failures else 'FAIL'}")

    # 场景 2：纯噪声（每条互不相关的孤立话题）→ 空数组，绝不硬凑。
    store2, index2 = _store()
    _seed_dimension(store2, dimension_key=EXISTING_KEY, name="人机互动")
    for i, text in enumerate(["今天天气不错", "楼下新开了面馆", "地铁换线了", "猫把杯子碰倒了"]):
        _seed_claim(store2, _claim(f"noise_{i}", text, at=NOW - timedelta(days=3 - i)))
    scheduler2 = _scheduler(store2, index2, _discovery_handler_factory("noise"))
    commits2 = scheduler2._run_discovery(now=NOW)
    total_proposals = sum(len(c.proposal_receipts) for c in commits2)
    if total_proposals != 0:
        failures.append(f"场景2：噪声却立了 {total_proposals} 个轴（不该发生）")
    print(f"[场景2 纯噪声] proposals={total_proposals} -> {'OK' if total_proposals == 0 else 'FAIL'}")

    # 场景 3：走真实生产流水线 run_due()，证明 discovery 已真正接入调度器，
    # 而不是只有手工调用 _run_discovery 时才生效。
    store3, index3 = _store()
    _seed_dimension(store3, dimension_key=EXISTING_KEY, name="人机互动")
    for i, text in enumerate([
        "反酸烧心，饭后躺下更明显",
        "今早脖子又僵了",
        "又反酸，这周第三次",
        "睡前胸口灼烧感",
        "肩颈酸痛持续一周了",
    ]):
        _seed_claim(store3, _claim(f"clm_sweep_{i}", text, at=NOW - timedelta(days=5 - i)))
    scheduler3 = _scheduler(store3, index3, _discovery_handler_factory("recurrent"))
    sweep = scheduler3.run_due(now=NOW)
    sweep_commits = len(sweep.dimension_discoveries)
    sweep_proposals = sum(len(c.proposal_receipts) for c in sweep.dimension_discoveries)
    sweep_ok = sweep_commits == 1 and sweep_proposals == 1
    if not sweep_ok:
        failures.append(
            f"场景3：run_due 未触发 discovery（commits={sweep_commits}, "
            f"proposals={sweep_proposals}）"
        )
    print(f"[场景3 run_due 全量扫描] discovery_commits={sweep_commits} "
          f"proposals={sweep_proposals} -> {'OK' if sweep_ok else 'FAIL'}")

    # 场景 4：审计锚点（周期复盘宪法四/五）—— 每轮 discovery 必须在世界里落一条
    # Wake 记录，使「这一轮有没有做过新轴判断、结果如何」可被查询。否则发现归
    # 总结 AI 后，这件事只存在于内存返回值里，线上无法审计。
    store4, index4 = _store()
    _seed_dimension(store4, dimension_key=EXISTING_KEY, name="人机互动")
    _seed_claim(store4, _claim("audit_seed", "反酸烧心，今晚又犯了", at=NOW - timedelta(days=1)))
    scheduler4 = _scheduler(store4, index4, _discovery_handler_factory("recurrent"))
    scheduler4._run_discovery(now=NOW)
    wakes = [
        p for p in store4.list_payloads(object_type=ObjectType.WAKE)
        if (p.get("metadata") or {}).get("trigger_kind") == "dimension_discovery_cycle"
    ]
    if not wakes:
        failures.append("场景4：discovery 未在世界里落审计 Wake 记录")
    elif wakes[0].get("wake_source") != "dimension_discovery":
        failures.append(
            f"场景4：审计 Wake 的 wake_source 错：{wakes[0].get('wake_source')}"
        )
    else:
        meta = wakes[0].get("metadata", {})
        if meta.get("proposals") != 1:
            failures.append(f"场景4：审计 Wake 的 proposals 计数错：{meta.get('proposals')}")
    print(f"[场景4 审计锚点] wake_records={len(wakes)} -> {'OK' if not failures else 'FAIL'}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
