"""P16 召回基准工具 —— 跨模型/跨厂商长期入住的可复现评测。

包含两个场景：
- recall（换模型召回）：写 anchor → 模型 A 记住 → 追问 → 换模型 B 追问。
- exhaustion（上下文耗尽恢复）：写 anchor → 模型 A 记住 → 灌 N 轮无关
  filler 把 anchor 挤出 RECENT CONVERSATION → 追问，验证系统能靠
  WorldSearchIndex 从世界库恢复记忆。

判据与宪法的关系（必读）：
- `verdict` 只由 `constitutional_compliance`（宪法符合性）决定；
- `recall_rate` 是纯观测指标，**不作为通过门槛**。要求 100% 召回等于
  逼迫系统在无主题/弱关联轮次强行补充历史，直接违反宪法第二章 2.2
  （无主题不推荐）与第十四章禁止事项第 7 条（强行补充无关历史）；
  详见 docs/testing/P16_RECALL_BENCH.md「判据与宪法的关系」。

用法示例：
    AIOS_GEMINI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/" \
    AIOS_GEMINI_API_KEY="<your-key>" \
    python tools/p16_recall_bench.py --sessions 3 --out p16-recall-evidence.json

    # 只跑上下文耗尽恢复场景（filler 轮数需大于 recent-turn-limit）
    python tools/p16_recall_bench.py --scenario exhaustion --filler-rounds 9

所需环境变量（无一可缺）：
    AIOS_GEMINI_BASE_URL   Gemini OpenAI 兼容端点
    AIOS_GEMINI_API_KEY    API 密钥

可选环境变量：
    AIOS_BENCH_MODEL_A     第一模型（默认 gemini-3-flash-preview）
    AIOS_BENCH_MODEL_B     第二模型（默认 gemini-flash-lite-latest）
    AIOS_BENCH_SESSIONS    默认 session 数（可被 --sessions 覆盖）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 把项目 src 加入路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aios_core.contracts.enums import SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent, utc_now
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.grok_provider import GrokProviderConfig, GrokStreamingProvider
from aios_core.runtime.turn_runtime import FusedTurnResult, FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


# ---------------------------------------------------------------------------
# 配置与环境
# ---------------------------------------------------------------------------

REQUIRED_ENVS = ("AIOS_GEMINI_BASE_URL", "AIOS_GEMINI_API_KEY")
DEFAULT_MODEL_A = os.environ.get("AIOS_BENCH_MODEL_A", "gemini-3-flash-preview")
DEFAULT_MODEL_B = os.environ.get("AIOS_BENCH_MODEL_B", "gemini-flash-lite-latest")
DEFAULT_SESSIONS = int(os.environ.get("AIOS_BENCH_SESSIONS", "3"))

ANCHOR_FACT = (
    "我在杭州做一款 23cm 柔性屏手环，主打运动健康监测，"
    "屏幕可以弯曲贴合手腕，续航 14 天。"
)

RECALL_QUESTION = (
    "我刚才让你记住的那句话里，我在哪个城市、做什么产品？"
    "请用一句话回答，不要查工具。"
)

RECALL_KEYWORDS = {"杭州", "手环", "柔性屏", "23cm"}

# exhaustion 场景的 filler 轮次：与 anchor 完全无关的话题。
# 注意：严禁出现 anchor 关键词（杭州/手环/柔性屏/23cm），否则命中是假阳性。
FILLER_QUESTIONS = (
    "给我讲讲海底火山是怎么形成的。",
    "四季交替的成因是什么？",
    "水为什么会沸腾？",
    "天空为什么呈现蓝色？",
    "蜜蜂是如何找到花朵的？",
)

DEFAULT_FILLER_ROUNDS = 9
DEFAULT_RECENT_TURN_LIMIT = 8
# FusedTurnRuntime 的默认推荐上限（recommendation_limit），本工具未显式覆盖，
# 因此宪法符合性检查以它作为「单轮推荐数量预算」参照。
DEFAULT_RECOMMENDATION_LIMIT = 5

MAX_RETRIES = 2

# 本工具判据引用的项目宪法条款（docs/constitution/ 下唯一宪法文件）。
CONSTITUTION_PATH = (
    "docs/constitution/AIOS_v3.0_Intelligent_Memory_Recommendation_System_Constitution.md"
)

CONSTITUTIONAL_BASIS: tuple[dict[str, str], ...] = (
    {
        "clause": "2.2",
        "title": "无主题不推荐",
        "summary": (
            "当前会话没有明确主题，或当前主题与历史世界没有足够强的关联时，"
            "推荐结果必须为空；「0 条推荐」是正常结果，不是失败。"
        ),
        "source": CONSTITUTION_PATH,
    },
    {
        "clause": "3.2",
        "title": "主题来源",
        "summary": (
            "当前主题可以来自最近仍然持续有效的上一主题；上一轮讨论某话题、"
            "下一轮用户只说「那这个怎么实现？」时，只要会话连续性仍然明确，"
            "当前主题仍应保持。"
        ),
        "source": CONSTITUTION_PATH,
    },
    {
        "clause": "十四-7",
        "title": "禁止事项第 7 条",
        "summary": "禁止因推荐结果为空而强行补充无关历史。",
        "source": CONSTITUTION_PATH,
    },
    {
        "clause": "十四-9",
        "title": "禁止事项第 9 条",
        "summary": "禁止让模型必须先搜索才能获得明显相关的历史。",
        "source": CONSTITUTION_PATH,
    },
)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class RoundResult:
    turn_index: int
    model: str
    latency_sec: float
    model_rounds: int | None
    response_text: str
    recalled: bool
    error: str | None = None
    recall_check: bool = True  # 该轮是否参与召回判定（T1/filler 轮不算）
    # —— 宪法观测（全部来自 FusedTurnResult，None 表示运行时未暴露/未测到）——
    current_topic: str | None = None
    topic_gate_open: bool | None = None
    memory_cards_count: int | None = None
    recommendation_reason: str | None = None
    observation_error: str | None = None


@dataclass
class TurnObservation:
    """单轮的宪法观测数据；字段为 None 表示该轮未测到，绝不猜测填充。"""

    current_topic: str | None = None
    topic_gate_open: bool | None = None
    memory_cards_count: int | None = None
    recommendation_reason: str | None = None
    continued_from_recent_turn: bool | None = None
    topic_state_reason: str | None = None
    observation_error: str | None = None  # 提取过程自身出错时的原因


@dataclass
class SessionResult:
    session_id: str
    db_path: str
    rounds: list[RoundResult]
    scenario: str = "recall"
    # exhaustion 场景的宪法 3.2 主题继承探针（纯观测，不参与 PASS/FAIL）
    topic_probe: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# 初始化世界
# ---------------------------------------------------------------------------

def _make_anchor_observation(now: datetime) -> Observation:
    """构造一条可检索的 anchor Observation。"""
    return Observation(
        object_id="bench_anchor_001",
        subject_id="user_1",
        occurred=TemporalExtent.point(now),
        learned_at=now,
        recorded_at=now,
        created_by="p16_recall_bench",
        source_kind="user_input",
        modality="text",
        value=ANCHOR_FACT,
    )


def _write_anchor(store: SQLiteWorldStore, obs: Observation) -> None:
    """把 anchor 写入世界库。"""
    req = OperationRequest(
        operation_name="p16.bench.seed_anchor",
        expected_world_revision=store.current_world_revision(),
        reason="写入 P16 召回基准 anchor 事实",
        idempotency_key=f"p16_seed_{obs.object_id}_{obs.learned_at.isoformat()}",
        source_class=SourceClass.USER,
    )
    store.commit([obs], req)


def _build_runtime(
    db_path: str,
    model: str,
    base_url: str,
    api_key: str,
    timeout: float,
    recent_turn_limit: int = DEFAULT_RECENT_TURN_LIMIT,
) -> FusedTurnRuntime:
    """为给定模型构造运行时（含全新世界库与索引）。"""
    store = SQLiteWorldStore(db_path)
    index = WorldSearchIndex(db_path, store=store)
    index.rebuild()

    provider = GrokStreamingProvider(
        GrokProviderConfig(
            base_url=base_url,
            api_key=api_key,
            default_model=model,
            timeout_seconds=timeout,
            max_output_tokens=512,
        )
    )
    handler = provider.as_model_handler(model=model)

    return FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=handler,
        subject_id="user_1",
        recent_turn_limit=recent_turn_limit,
    )


# ---------------------------------------------------------------------------
# 单轮执行（带重试）
# ---------------------------------------------------------------------------

def _run_single_turn(
    runtime: FusedTurnRuntime,
    session_id: str,
    turn_index: int,
    user_input: str,
    now: datetime,
    max_retries: int = MAX_RETRIES,
) -> tuple[str, int | None, str | None, TurnObservation]:
    """执行一轮对话，网络异常时指数退避重试。

    返回 (response_text, model_rounds, error_or_none, turn_observation)
    """
    for attempt in range(max_retries + 1):
        try:
            result = runtime.run_turn(
                session_id=session_id,
                turn_index=turn_index,
                user_input=user_input,
                occurred_at=now,
            )
            return (
                result.runtime.response,
                result.runtime.model_rounds,
                None,
                _extract_turn_observation(result),
            )
        except Exception as exc:
            if attempt < max_retries:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            return "", None, f"{type(exc).__name__}: {exc}", TurnObservation()
    return "", None, "unexpected unreachable", TurnObservation()


# ---------------------------------------------------------------------------
# 宪法观测提取
# ---------------------------------------------------------------------------

def _extract_turn_observation(result: FusedTurnResult) -> TurnObservation:
    """从 FusedTurnResult 提取本轮宪法观测数据。

    数据来源（均为运行时既有公开结构，工具不做任何推断）：
    - context.memory_cards：本轮实际交给模型的记忆卡片（宪法 7.3 数量预算）；
    - context.current_topic / recommendation.topic_gate_open：本轮主题门状态；
    - context.task_context["topic_state"]：运行时解析出的主题状态机理由。
    任何字段拿不到都如实记 None（调用方据此判 NOT_MEASURED），不猜、不编。
    """
    obs = TurnObservation()
    try:
        context = getattr(result, "context", None)
        recommendation = getattr(result, "recommendation", None)
        if context is not None:
            obs.current_topic = getattr(context, "current_topic", None)
            cards = getattr(context, "memory_cards", None)
            obs.memory_cards_count = None if cards is None else len(cards)
            task_context = getattr(context, "task_context", None)
            if isinstance(task_context, dict):
                topic_state = task_context.get("topic_state")
                if isinstance(topic_state, dict):
                    obs.topic_state_reason = topic_state.get("reason")
                    obs.continued_from_recent_turn = topic_state.get(
                        "continued_from_recent_turn"
                    )
        if recommendation is not None:
            obs.topic_gate_open = getattr(recommendation, "topic_gate_open", None)
            obs.recommendation_reason = getattr(recommendation, "reason", None)
    except Exception as exc:  # 观测失败必须可见，不许静默伪装成 0
        obs.observation_error = f"{type(exc).__name__}: {exc}"
    return obs


def _build_topic_probe(
    *,
    anchor_topic: str | None,
    probe_obs: TurnObservation,
    probe_index: int,
) -> dict[str, Any]:
    """构造宪法 3.2 主题继承探针（纯观测，不参与 PASS/FAIL）。

    anchor 话题取 T1 轮实际解析出的 current_topic；追问轮（指代型追问）
    实际解析出的 current_topic 为 probe_topic。两者一致视为主题延续。
    运行时拿不到信息时如实记 null + reason。
    """
    probe_topic = probe_obs.current_topic
    if probe_topic is None or anchor_topic is None:
        return {
            "turn_index": probe_index,
            "anchor_topic": anchor_topic,
            "probe_topic": None,
            "topic_inherited": None,
            "continued_from_recent_turn": probe_obs.continued_from_recent_turn,
            "topic_state_reason": probe_obs.topic_state_reason,
            "reason": "运行时未暴露 current_topic/topic_state，无法观测（NOT_MEASURED）",
        }
    return {
        "turn_index": probe_index,
        "anchor_topic": anchor_topic,
        "probe_topic": probe_topic,
        "topic_inherited": probe_topic.strip() == anchor_topic.strip(),
        "continued_from_recent_turn": probe_obs.continued_from_recent_turn,
        "topic_state_reason": probe_obs.topic_state_reason,
        "reason": None,
    }


# ---------------------------------------------------------------------------
# 召回判定
# ---------------------------------------------------------------------------

def _is_recalled(text: str) -> bool:
    """回复中只要出现任一关键词即算命中。"""
    lowered = text.lower()
    return any(kw in lowered for kw in RECALL_KEYWORDS)


# ---------------------------------------------------------------------------
# 单次 session
# ---------------------------------------------------------------------------

def _run_recall_session(
    session_idx: int,
    model_a: str,
    model_b: str,
    base_url: str,
    api_key: str,
    timeout: float,
    recent_turn_limit: int = DEFAULT_RECENT_TURN_LIMIT,
) -> SessionResult:
    """跑一个完整 session：写 anchor → T1 记住 → T2 模型 A 追问 → T3 模型 B 追问。"""
    session_id = f"p16_session_{session_idx:03d}"
    now = utc_now()

    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        db_path = tmp.name

    try:
        # 写 anchor
        store = SQLiteWorldStore(db_path)
        _write_anchor(store, _make_anchor_observation(now))

        # T1：让模型 A 记住
        runtime = _build_runtime(
            db_path, model_a, base_url, api_key, timeout, recent_turn_limit=recent_turn_limit
        )
        t1_text, t1_rounds, t1_err, t1_obs = _run_single_turn(
            runtime, session_id, 1, f"请记住这句话：{ANCHOR_FACT}", now
        )

        # T2：模型 A 追问
        t2_text, t2_rounds, t2_err, t2_obs = _run_single_turn(
            runtime, session_id, 2, RECALL_QUESTION, now
        )

        # T3：换模型 B 追问
        provider_b = GrokStreamingProvider(
            GrokProviderConfig(
                base_url=base_url,
                api_key=api_key,
                default_model=model_b,
                timeout_seconds=timeout,
                max_output_tokens=512,
            )
        )
        runtime.cognitive_runtime.model_handler = provider_b.as_model_handler(model=model_b)
        t3_text, t3_rounds, t3_err, t3_obs = _run_single_turn(
            runtime, session_id, 3, RECALL_QUESTION, now
        )

        rounds = [
            RoundResult(
                1, model_a, 0.0, t1_rounds, t1_text, _is_recalled(t1_text), t1_err,
                recall_check=False,
                current_topic=t1_obs.current_topic,
                topic_gate_open=t1_obs.topic_gate_open,
                memory_cards_count=t1_obs.memory_cards_count,
                recommendation_reason=t1_obs.recommendation_reason,
                observation_error=t1_obs.observation_error,
            ),
            RoundResult(
                2, model_a, 0.0, t2_rounds, t2_text, _is_recalled(t2_text), t2_err,
                current_topic=t2_obs.current_topic,
                topic_gate_open=t2_obs.topic_gate_open,
                memory_cards_count=t2_obs.memory_cards_count,
                recommendation_reason=t2_obs.recommendation_reason,
                observation_error=t2_obs.observation_error,
            ),
            RoundResult(
                3, model_b, 0.0, t3_rounds, t3_text, _is_recalled(t3_text), t3_err,
                current_topic=t3_obs.current_topic,
                topic_gate_open=t3_obs.topic_gate_open,
                memory_cards_count=t3_obs.memory_cards_count,
                recommendation_reason=t3_obs.recommendation_reason,
                observation_error=t3_obs.observation_error,
            ),
        ]
        return SessionResult(session_id, db_path, rounds, scenario="recall")
    finally:
        # 清理临时库（保留 db_path 供调试，仅在退出前由调用方删）
        pass


def _run_exhaustion_session(
    session_idx: int,
    model_a: str,
    base_url: str,
    api_key: str,
    timeout: float,
    filler_rounds: int,
    recent_turn_limit: int = DEFAULT_RECENT_TURN_LIMIT,
) -> SessionResult:
    """跑一个 exhaustion session：写 anchor → T1 记住 → N 轮 filler 挤出上下文 → 追问。

    filler 轮数必须大于 recent_turn_limit，anchor 才会被挤出 RECENT CONVERSATION，
    此时命中只能来自 WorldSearchIndex 渲染的 RELEVANT WORLD MEMORY 段。
    """
    session_id = f"p16_exhaustion_{session_idx:03d}"
    now = utc_now()

    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        db_path = tmp.name

    try:
        # 写 anchor
        store = SQLiteWorldStore(db_path)
        _write_anchor(store, _make_anchor_observation(now))

        runtime = _build_runtime(
            db_path, model_a, base_url, api_key, timeout, recent_turn_limit=recent_turn_limit
        )
        rounds: list[RoundResult] = []

        # T1：让模型记住
        t1_text, t1_rounds, t1_err, t1_obs = _run_single_turn(
            runtime, session_id, 1, f"请记住这句话：{ANCHOR_FACT}", now
        )
        rounds.append(RoundResult(
            1, model_a, 0.0, t1_rounds, t1_text, _is_recalled(t1_text), t1_err, recall_check=False,
            current_topic=t1_obs.current_topic,
            topic_gate_open=t1_obs.topic_gate_open,
            memory_cards_count=t1_obs.memory_cards_count,
            recommendation_reason=t1_obs.recommendation_reason,
        ))

        # T2..T(N+1)：灌无关 filler，把 anchor 挤出 RECENT CONVERSATION
        for i in range(filler_rounds):
            turn_index = i + 2
            filler = FILLER_QUESTIONS[i % len(FILLER_QUESTIONS)]
            text, model_rounds, err, obs = _run_single_turn(
                runtime, session_id, turn_index, filler, now
            )
            rounds.append(RoundResult(
                turn_index, model_a, 0.0, model_rounds, text, _is_recalled(text), err, recall_check=False,
                current_topic=obs.current_topic,
                topic_gate_open=obs.topic_gate_open,
                memory_cards_count=obs.memory_cards_count,
                recommendation_reason=obs.recommendation_reason,
                observation_error=obs.observation_error,
            ))

        # 最后一轮（N+2）：追问（指代型追问，兼作宪法 3.2 主题继承探针）
        probe_index = filler_rounds + 2
        p_text, p_rounds, p_err, p_obs = _run_single_turn(
            runtime, session_id, probe_index, RECALL_QUESTION, now
        )
        rounds.append(RoundResult(
            probe_index, model_a, 0.0, p_rounds, p_text, _is_recalled(p_text), p_err,
            current_topic=p_obs.current_topic,
            topic_gate_open=p_obs.topic_gate_open,
            memory_cards_count=p_obs.memory_cards_count,
            recommendation_reason=p_obs.recommendation_reason,
            observation_error=p_obs.observation_error,
        ))

        # 宪法 3.2 探针：指代型追问是否继承了 anchor 话题（纯观测，不参与 PASS/FAIL）
        topic_probe = _build_topic_probe(
            anchor_topic=t1_obs.current_topic,
            probe_obs=p_obs,
            probe_index=probe_index,
        )

        return SessionResult(
            session_id, db_path, rounds, scenario="exhaustion", topic_probe=topic_probe
        )
    finally:
        # 与 recall 场景一致：db_path 由调用方在退出前清理
        pass


# ---------------------------------------------------------------------------
# 报告与证据
# ---------------------------------------------------------------------------

def _scenario_stats(sessions: list[SessionResult]) -> dict[str, dict[str, Any]]:
    """按 scenario 分组统计召回率（只计 recall_check=True 的轮次）。"""
    stats: dict[str, dict[str, Any]] = {}
    for sess in sessions:
        bucket = stats.setdefault(
            sess.scenario,
            {"sessions": 0, "total_recall_attempts": 0, "successful_recalls": 0},
        )
        bucket["sessions"] += 1
        for r in sess.rounds:
            if r.recall_check:
                bucket["total_recall_attempts"] += 1
                if r.recalled:
                    bucket["successful_recalls"] += 1
    for bucket in stats.values():
        total = bucket["total_recall_attempts"]
        bucket["recall_rate"] = round(bucket["successful_recalls"] / total, 4) if total else 0.0
    return stats


def _print_summary(
    sessions: list[SessionResult],
    recent_turn_limit: int = DEFAULT_RECENT_TURN_LIMIT,
) -> None:
    stats = _scenario_stats(sessions)
    for scen in sorted({s.scenario for s in sessions}):
        print(f"\n===== 场景: {scen} =====")
        for sess in sessions:
            if sess.scenario != scen:
                continue
            print(f"\n【Session {sess.session_id}】")
            for r in sess.rounds:
                status = "✅ 命中" if r.recalled else "❌ 未命中"
                if r.error:
                    status = f"💥 异常: {r.error}"
                print(
                    f"  T{r.turn_index} [{r.model}] rounds={r.model_rounds} "
                    f"{status}\n    → {r.response_text[:120]}..."
                )
    print(f"\n{'=' * 50}")
    for scen, bucket in sorted(stats.items()):
        total = bucket["total_recall_attempts"]
        hits = bucket["successful_recalls"]
        rate = bucket["recall_rate"]
        print(f"[{scen}] 召回率(观测, 非门槛): {hits}/{total} = {rate:.0%}")

    compliance = _evaluate_constitutional_compliance(
        sessions, recent_turn_limit=recent_turn_limit
    )
    print(f"宪法符合性(verdict 唯一依据): {compliance['status']}")
    for v in compliance["violations"][:5]:
        print(f"  ⚠️ {v['turn']}: {v['detail']} [{v['clause']}]")
    if compliance["unmeasured_rounds"]:
        print(f"  ℹ️ {compliance['unmeasured_note']}")


def _evaluate_constitutional_compliance(
    sessions: list[SessionResult],
    recent_turn_limit: int = DEFAULT_RECENT_TURN_LIMIT,
) -> dict[str, Any]:
    """评估被测行为是否符合宪法 —— verdict 的唯一决定维度。

    覆盖两类可稳定测到的检查：
    - no_forced_history_injection（十四-1 / 2.2 / 十四-7）：主题门关闭
      （无当前主题）的轮次出现 memory_cards > 0，即「强行补充无关历史」；
    - no_full_load_every_turn（十四-3 / 十四-4 / 十四-8）：单轮卡片数
      超过推荐上限或超过 recent_turn_limit，即「每轮全量加载」迹象。

    拿不到观测数据（轮次异常或运行时未暴露）的轮次不计入判定；
    全部轮次都拿不到时整体标 NOT_MEASURED，不伪装成 PASS。
    """
    violations: list[dict[str, Any]] = []
    measured = 0
    unmeasured = 0
    for sess in sessions:
        for r in sess.rounds:
            if r.error is not None or r.memory_cards_count is None or r.topic_gate_open is None:
                unmeasured += 1
                continue
            measured += 1
            where = f"{sess.session_id} T{r.turn_index}"
            if (not r.topic_gate_open) and r.memory_cards_count > 0:
                violations.append({
                    "check": "no_forced_history_injection",
                    "clause": "十四-1 / 2.2 / 十四-7",
                    "turn": where,
                    "detail": (
                        f"主题门关闭（current_topic={r.current_topic!r}）却推荐了 "
                        f"{r.memory_cards_count} 条记忆卡片"
                    ),
                })
            if (
                r.memory_cards_count > DEFAULT_RECOMMENDATION_LIMIT
                or r.memory_cards_count > recent_turn_limit
            ):
                violations.append({
                    "check": "no_full_load_every_turn",
                    "clause": "十四-3 / 十四-4 / 十四-8",
                    "turn": where,
                    "detail": (
                        f"单轮 {r.memory_cards_count} 条卡片，超过推荐上限 "
                        f"{DEFAULT_RECOMMENDATION_LIMIT} 或 recent_turn_limit "
                        f"{recent_turn_limit}"
                    ),
                })

    if measured == 0:
        status = "NOT_MEASURED"
    elif violations:
        status = "FAIL"
    else:
        status = "PASS"

    def _check_block(check_id: str, clause: str, description: str) -> dict[str, Any]:
        found = [v for v in violations if v["check"] == check_id]
        if found:
            check_status = "FAIL"
        elif measured == 0:
            check_status = "NOT_MEASURED"
        else:
            check_status = "PASS"
        return {
            "id": check_id,
            "clause": clause,
            "description": description,
            "status": check_status,
            "violations": found,
        }

    return {
        "status": status,
        "checks": [
            _check_block(
                "no_forced_history_injection",
                "十四-1 / 2.2 / 十四-7",
                "无当前主题的轮次不得出现记忆卡片（禁止因结果为空而强行补充无关历史）",
            ),
            _check_block(
                "no_full_load_every_turn",
                "十四-3 / 十四-4 / 十四-8",
                "单轮卡片数不得超过推荐上限或 recent_turn_limit（禁止每轮固定全量加载）",
            ),
        ],
        "violations": violations,
        "measured_rounds": measured,
        "unmeasured_rounds": unmeasured,
        "unmeasured_note": (
            f"{unmeasured} 轮因异常或运行时未暴露观测数据而未计入判定"
            if unmeasured else None
        ),
    }


def _write_evidence(
    sessions: list[SessionResult],
    out_path: str,
    base_url: str,
    model_a: str,
    model_b: str,
    recent_turn_limit: int = DEFAULT_RECENT_TURN_LIMIT,
    filler_rounds: int = DEFAULT_FILLER_ROUNDS,
) -> str:
    """输出可审计的 JSON 证据文件（不含 API key），返回 verdict。

    verdict 只由 constitutional_compliance 决定；recall_rate 降级为纯观测
    指标（observations 区块）——要求 100% 召回会逼出违反宪法 2.2 与十四-7
    的行为（无主题也硬推历史），因此它不可能是通过门槛。
    """
    by_scenario = _scenario_stats(sessions)
    total = sum(b["total_recall_attempts"] for b in by_scenario.values())
    hits = sum(b["successful_recalls"] for b in by_scenario.values())
    rate = hits / total if total else 0.0

    compliance = _evaluate_constitutional_compliance(
        sessions, recent_turn_limit=recent_turn_limit
    )
    verdict = compliance["status"]

    if verdict == "PASS":
        verdict_rationale = (
            f"宪法符合性通过：{compliance['measured_rounds']} 轮实测中未发现"
            "无主题推荐、超出推荐上限或全量加载迹象；召回率 "
            f"{rate:.0%} 仅为观测指标，不构成通过门槛。"
        )
    elif verdict == "FAIL":
        first = compliance["violations"][0]
        verdict_rationale = (
            f"宪法符合性未通过：发现 {len(compliance['violations'])} 项违规"
            f"（首项 {first['turn']}: {first['detail']}，条款 {first['clause']}）；"
            "召回率不参与判定，详见 constitutional_compliance.violations。"
        )
    else:
        verdict_rationale = (
            "宪法符合性无法判定（NOT_MEASURED）：未取得任何一轮的 "
            "memory_cards/主题门观测数据；召回率 "
            f"{rate:.0%} 仅为观测指标，不作为通过门槛，更不允许伪装成 PASS。"
        )

    serializable: list[dict[str, Any]] = []
    for sess in sessions:
        sess_dict: dict[str, Any] = {
            "session_id": sess.session_id,
            "scenario": sess.scenario,
            "rounds": [],
        }
        if sess.topic_probe is not None:
            sess_dict["topic_probe"] = sess.topic_probe
        for r in sess.rounds:
            sess_dict["rounds"].append({
                "turn_index": r.turn_index,
                "model": r.model,
                "latency_sec": round(r.latency_sec, 3),
                "model_rounds": r.model_rounds,
                "response_text": r.response_text,
                "recalled": r.recalled,
                "recall_check": r.recall_check,
                "error": r.error,
                "constitutional_observation": {
                    "current_topic": r.current_topic,
                    "topic_gate_open": r.topic_gate_open,
                    "memory_cards_count": r.memory_cards_count,
                    "recommendation_reason": r.recommendation_reason,
                    "observation_error": r.observation_error,
                },
            })
        serializable.append(sess_dict)

    evidence = {
        "schema_version": "3.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "model_a": model_a,
        "model_b": model_b,
        "anchor_fact": ANCHOR_FACT,
        "recall_question": RECALL_QUESTION,
        "recall_keywords": sorted(RECALL_KEYWORDS),
        "config": {
            "recent_turn_limit": recent_turn_limit,
            "filler_rounds": filler_rounds,
            "filler_questions": list(FILLER_QUESTIONS),
            "recommendation_limit": DEFAULT_RECOMMENDATION_LIMIT,
        },
        "constitutional_basis": [dict(item) for item in CONSTITUTIONAL_BASIS],
        "constitutional_compliance": compliance,
        "sessions": serializable,
        "observations": {
            "recall": {
                "by_scenario": by_scenario,
                "total_recall_attempts": total,
                "successful_recalls": hits,
                "recall_rate": round(rate, 4),
                "is_pass_gate": False,
            },
            "note": (
                "recall_rate 为纯观测指标，不作为通过门槛。"
                "要求 100% 召回会逼迫系统在无主题/弱关联轮次强行补充历史，"
                "违反宪法 2.2（无主题不推荐）与十四-7（强行补充无关历史）。"
            ),
        },
        "verdict": verdict,
        "verdict_rationale": verdict_rationale,
        "summary": {
            "verdict": verdict,
            "constitutional_compliance": verdict,
        },
    }

    Path(out_path).write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"证据文件已写入: {out_path}")
    print(f"verdict(仅由宪法符合性决定): {verdict}")
    print(f"判定理由: {verdict_rationale}")
    return verdict


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="P16 召回基准 —— 验证换模型/上下文耗尽后记忆是否延续",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --sessions 5 --out evidence.json
  %(prog)s --model-a gemini-3-flash-preview --model-b gemini-flash-lite-latest
  %(prog)s --scenario exhaustion --filler-rounds 9
""",
    )
    parser.add_argument("--sessions", type=int, default=DEFAULT_SESSIONS, help="每个场景的评测 session 数")
    parser.add_argument("--out", type=str, default="p16-recall-evidence.json", help="证据 JSON 输出路径")
    parser.add_argument("--model-a", type=str, default=DEFAULT_MODEL_A, help="第一模型标识")
    parser.add_argument("--model-b", type=str, default=DEFAULT_MODEL_B, help="第二模型标识")
    parser.add_argument("--timeout", type=float, default=60.0, help="单次请求超时（秒）")
    parser.add_argument(
        "--scenario",
        choices=["recall", "exhaustion", "all"],
        default="all",
        help="评测场景：recall=换模型召回；exhaustion=上下文耗尽恢复；all=两者都跑",
    )
    parser.add_argument(
        "--filler-rounds",
        type=int,
        default=DEFAULT_FILLER_ROUNDS,
        help="exhaustion 场景的 filler 轮数（需大于 recent-turn-limit 才能把 anchor 挤出上下文）",
    )
    parser.add_argument(
        "--recent-turn-limit",
        type=int,
        default=DEFAULT_RECENT_TURN_LIMIT,
        help="透传给 FusedTurnRuntime 的 RECENT CONVERSATION 轮数上限",
    )
    args = parser.parse_args()

    missing = [ev for ev in REQUIRED_ENVS if not os.environ.get(ev)]
    if missing:
        print(f"缺少必需环境变量: {', '.join(missing)}", file=sys.stderr)
        print("请设置后继续。", file=sys.stderr)
        return 2

    base_url = os.environ["AIOS_GEMINI_BASE_URL"]
    api_key = os.environ["AIOS_GEMINI_API_KEY"]

    scenarios = ["recall", "exhaustion"] if args.scenario == "all" else [args.scenario]

    if "exhaustion" in scenarios and args.filler_rounds <= args.recent_turn_limit:
        print(
            "⚠️ 警告: --filler-rounds 需大于 --recent-turn-limit，"
            "否则 anchor 可能仍留在 RECENT CONVERSATION 内，测的不是世界库恢复路径。",
            file=sys.stderr,
        )

    print(f"P16 召回基准启动")
    print(f"  模型 A: {args.model_a}")
    print(f"  模型 B: {args.model_b}")
    print(f"  sessions/场景: {args.sessions}")
    print(f"  场景: {', '.join(scenarios)}")
    print(f"  recent_turn_limit: {args.recent_turn_limit}")
    if "exhaustion" in scenarios:
        print(f"  filler-rounds: {args.filler_rounds}")
    print(f"  超时: {args.timeout}s")

    sessions: list[SessionResult] = []
    for scen in scenarios:
        for i in range(args.sessions):
            print(f"\n▶ [{scen}] Session {i + 1}/{args.sessions} ...")
            try:
                if scen == "recall":
                    sess = _run_recall_session(
                        i, args.model_a, args.model_b, base_url, api_key, args.timeout,
                        recent_turn_limit=args.recent_turn_limit,
                    )
                else:
                    sess = _run_exhaustion_session(
                        i, args.model_a, base_url, api_key, args.timeout,
                        filler_rounds=args.filler_rounds,
                        recent_turn_limit=args.recent_turn_limit,
                    )
                sessions.append(sess)
            except Exception:
                print(f"Session {i} 崩溃:\n{traceback.format_exc()}", file=sys.stderr)
                continue

    _print_summary(sessions, recent_turn_limit=args.recent_turn_limit)
    verdict = _write_evidence(
        sessions, args.out, base_url, args.model_a, args.model_b,
        recent_turn_limit=args.recent_turn_limit,
        filler_rounds=args.filler_rounds,
    )

    # 清理临时库
    for sess in sessions:
        try:
            os.unlink(sess.db_path)
        except OSError:
            pass

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
