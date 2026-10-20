"""P16 召回基准工具 —— 跨模型/跨厂商长期入住的可复现评测。

用法示例：
    AIOS_GEMINI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/" \
    AIOS_GEMINI_API_KEY="<your-key>" \
    python tools/p16_recall_bench.py --sessions 3 --out p16-recall-evidence.json

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
from aios_core.contracts.refs import SourceRef
from aios_core.contracts.time import TemporalExtent, utc_now
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.grok_provider import GrokProviderConfig, GrokStreamingProvider
from aios_core.runtime.turn_runtime import FusedTurnRuntime
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

MAX_RETRIES = 2


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


@dataclass
class SessionResult:
    session_id: str
    db_path: str
    rounds: list[RoundResult]


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
        source_refs=[SourceRef(kind="bench", identifier="p16_anchor")],
    )


def _write_anchor(store: SQLiteWorldStore, obs: Observation) -> None:
    """把 anchor 写入世界库。"""
    req = OperationRequest(
        operation_name="p16.bench.seed_anchor",
        expected_world_revision=store.current_world_revision(),
        reason="写入 P16 召回基准 anchor 事实",
        idempotency_key=f"p16_seed_{obs.object_id}_{obs.learned_at.isoformat()}",
        source_class=SourceClass.MAINTENANCE,
        maintenance_class="BENCHMARK",
    )
    store.commit(obs, req)


def _build_runtime(db_path: str, model: str, base_url: str, api_key: str, timeout: float) -> FusedTurnRuntime:
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
) -> tuple[str, int | None, str | None]:
    """执行一轮对话，网络异常时指数退避重试。

    返回 (response_text, model_rounds, error_or_none)
    """
    for attempt in range(max_retries + 1):
        try:
            result = runtime.run_turn(
                session_id=session_id,
                turn_index=turn_index,
                user_input=user_input,
                occurred_at=now,
            )
            return result.runtime.response, result.runtime.model_rounds, None
        except Exception as exc:
            if attempt < max_retries:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            return "", None, f"{type(exc).__name__}: {exc}"
    return "", None, "unexpected unreachable"


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

def _run_session(
    session_idx: int,
    model_a: str,
    model_b: str,
    base_url: str,
    api_key: str,
    timeout: float,
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
        runtime = _build_runtime(db_path, model_a, base_url, api_key, timeout)
        t1_text, t1_rounds, t1_err = _run_single_turn(
            runtime, session_id, 1, f"请记住这句话：{ANCHOR_FACT}", now
        )

        # T2：模型 A 追问
        t2_text, t2_rounds, t2_err = _run_single_turn(
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
        t3_text, t3_rounds, t3_err = _run_single_turn(
            runtime, session_id, 3, RECALL_QUESTION, now
        )

        rounds = [
            RoundResult(1, model_a, 0.0, t1_rounds, t1_text, _is_recalled(t1_text), t1_err),
            RoundResult(2, model_a, 0.0, t2_rounds, t2_text, _is_recalled(t2_text), t2_err),
            RoundResult(3, model_b, 0.0, t3_rounds, t3_text, _is_recalled(t3_text), t3_err),
        ]
        return SessionResult(session_id, db_path, rounds)
    finally:
        # 清理临时库（保留 db_path 供调试，仅在退出前由调用方删）
        pass


# ---------------------------------------------------------------------------
# 报告与证据
# ---------------------------------------------------------------------------

def _print_summary(sessions: list[SessionResult]) -> None:
    total = 0
    hits = 0
    for sess in sessions:
        print(f"\n【Session {sess.session_id}】")
        for r in sess.rounds:
            status = "✅ 命中" if r.recalled else "❌ 未命中"
            if r.error:
                status = f"💥 异常: {r.error}"
            print(
                f"  T{r.turn_index} [{r.model}] rounds={r.model_rounds} "
                f"{status}\n    → {r.response_text[:120]}..."
            )
            if r.turn_index > 1:  # T1 不算召回判定
                total += 1
                if r.recalled:
                    hits += 1
    rate = hits / total if total else 0.0
    print(f"\n{'=' * 50}")
    print(f"召回率: {hits}/{total} = {rate:.0%}")


def _write_evidence(
    sessions: list[SessionResult],
    out_path: str,
    base_url: str,
    model_a: str,
    model_b: str,
) -> None:
    """输出可审计的 JSON 证据文件（不含 API key）。"""
    total = 0
    hits = 0
    serializable: list[dict[str, Any]] = []
    for sess in sessions:
        sess_dict: dict[str, Any] = {
            "session_id": sess.session_id,
            "rounds": [],
        }
        for r in sess.rounds:
            sess_dict["rounds"].append({
                "turn_index": r.turn_index,
                "model": r.model,
                "latency_sec": round(r.latency_sec, 3),
                "model_rounds": r.model_rounds,
                "response_text": r.response_text,
                "recalled": r.recalled,
                "error": r.error,
            })
            if r.turn_index > 1:
                total += 1
                if r.recalled:
                    hits += 1
        serializable.append(sess_dict)

    rate = hits / total if total else 0.0
    verdict = "PASS" if rate >= 1.0 else "FAIL"

    evidence = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "model_a": model_a,
        "model_b": model_b,
        "anchor_fact": ANCHOR_FACT,
        "recall_question": RECALL_QUESTION,
        "recall_keywords": sorted(RECALL_KEYWORDS),
        "sessions": serializable,
        "summary": {
            "total_recall_attempts": total,
            "successful_recalls": hits,
            "recall_rate": round(rate, 4),
            "verdict": verdict,
        },
    }

    Path(out_path).write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"证据文件已写入: {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="P16 召回基准 —— 验证换模型后记忆是否延续",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --sessions 5 --out evidence.json
  %(prog)s --model-a gemini-3-flash-preview --model-b gemini-flash-lite-latest
""",
    )
    parser.add_argument("--sessions", type=int, default=DEFAULT_SESSIONS, help="评测 session 数")
    parser.add_argument("--out", type=str, default="p16-recall-evidence.json", help="证据 JSON 输出路径")
    parser.add_argument("--model-a", type=str, default=DEFAULT_MODEL_A, help="第一模型标识")
    parser.add_argument("--model-b", type=str, default=DEFAULT_MODEL_B, help="第二模型标识")
    parser.add_argument("--timeout", type=float, default=60.0, help="单次请求超时（秒）")
    args = parser.parse_args()

    missing = [ev for ev in REQUIRED_ENVS if not os.environ.get(ev)]
    if missing:
        print(f"缺少必需环境变量: {', '.join(missing)}", file=sys.stderr)
        print("请设置后继续。", file=sys.stderr)
        return 2

    base_url = os.environ["AIOS_GEMINI_BASE_URL"]
    api_key = os.environ["AIOS_GEMINI_API_KEY"]

    print(f"P16 召回基准启动")
    print(f"  模型 A: {args.model_a}")
    print(f"  模型 B: {args.model_b}")
    print(f"  sessions: {args.sessions}")
    print(f"  超时: {args.timeout}s")

    sessions: list[SessionResult] = []
    for i in range(args.sessions):
        print(f"\n▶ Session {i + 1}/{args.sessions} ...")
        try:
            sess = _run_session(i, args.model_a, args.model_b, base_url, api_key, args.timeout)
            sessions.append(sess)
        except Exception:
            print(f"Session {i} 崩溃:\n{traceback.format_exc()}", file=sys.stderr)
            continue

    _print_summary(sessions)
    _write_evidence(sessions, args.out, base_url, args.model_a, args.model_b)

    # 清理临时库
    for sess in sessions:
        try:
            os.unlink(sess.db_path)
        except OSError:
            pass

    return 0 if sessions and all(
        r.recalled for sess in sessions for r in sess.rounds if r.turn_index > 1 and not r.error
    ) else 1


if __name__ == "__main__":
    sys.exit(main())
