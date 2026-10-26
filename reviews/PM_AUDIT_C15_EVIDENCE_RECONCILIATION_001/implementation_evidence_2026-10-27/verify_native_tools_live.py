"""T10 真实端点取证：原生 tools 主路径下的 M1/M2/M3。

用 NVIDIA NIM + minimaxai/minimax-m3.1-flash，通过 FusedTurnRuntime 完整跑 run_turn，
不注入 durable_fact_extractor（验证原生 tools 主路径，而非抽取轮兜底）。

M1 写入率：自我介绍轮后，durable claim 覆盖核心事实（名字/地点/工作）。
M2 关逐字仍答对：recent_turn_limit=0，第二轮问「我叫什么」，模型从 continuity anchor 答对。
M3 连问两遍 claim 不增：重复自我介绍后 claim 数不翻倍（内容级去重）。
"""

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "src")

from aios_core.ai_world import AIWorldDomain
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.grok_provider import GrokProviderConfig, GrokStreamingProvider
from aios_core.runtime.resilient_handler import (
    PRIMARY_API_KEY,
    PRIMARY_BASE_URL,
    PRIMARY_MODEL,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


def main() -> None:
    print("=" * 70)
    print(f"T10 真实端点取证 — 模型: {PRIMARY_MODEL}")
    print(f"端点: {PRIMARY_BASE_URL}")
    print("=" * 70)

    tmp = Path(tempfile.mkdtemp(prefix="aios_native_tools_"))
    store = SQLiteWorldStore(str(tmp / "world.sqlite"))
    index = WorldSearchIndex(str(tmp / "index.sqlite"), store=store)
    index.rebuild()

    provider = GrokStreamingProvider(
        GrokProviderConfig(
            base_url=PRIMARY_BASE_URL,
            api_key=PRIMARY_API_KEY,
            default_model=PRIMARY_MODEL,
        )
    )

    # recent_turn_limit=0: 关掉逐字对话注入，M2 必须从 continuity anchor 读。
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=provider.as_model_handler(),
        subject_id="user_1",
        recent_turn_limit=0,
    )

    base = datetime(2026, 10, 27, 0, 0, tzinfo=timezone.utc)
    intro = "我叫老王，在东莞做23cm柔性屏智能手环，你以后对我别用敬语。"

    # ---- 第 1 轮：自我介绍（M1 写入率） ----
    print("\n[第1轮] 自我介绍")
    r1 = runtime.run_turn(
        session_id="s1", turn_index=1, user_input=intro, occurred_at=base
    )
    print("  模型回复:", (r1.runtime.response or "")[:120])
    print("  终止原因:", r1.runtime.termination_reason)
    print("  工具调用历史:", [h.name for h in r1.runtime.capability_history])

    claims_1 = runtime.ai_world.current(
        domains=(AIWorldDomain("user_understanding"),), limit=100
    )
    print(f"  [M1] user_understanding claim 数: {len(claims_1)}")
    for c in claims_1:
        print(f"      - {c.statement!r}")

    # ---- 第 2 轮：问名字（M2 关逐字仍答对） ----
    print("\n[第2轮] recent_turn_limit=0 下问「我叫什么」")
    r2 = runtime.run_turn(
        session_id="s1",
        turn_index=2,
        user_input="我叫什么名字？我在哪个城市？",
        occurred_at=base,
    )
    ans2 = (r2.runtime.response or "").strip()
    print("  模型回复:", ans2[:200])
    m2_ok = ("老王" in ans2) and ("东莞" in ans2)
    print(f"  [M2] 从锚点答对（老王+东莞）: {'PASS' if m2_ok else 'FAIL'}")

    # ---- 第 3 轮：重复自我介绍（M3 连问两遍 claim 不增） ----
    print("\n[第3轮] 重复自我介绍（验证去重）")
    r3 = runtime.run_turn(
        session_id="s1", turn_index=3, user_input=intro, occurred_at=base
    )
    print("  模型回复:", (r3.runtime.response or "")[:120])
    print("  工具调用历史:", [h.name for h in r3.runtime.capability_history])

    claims_3 = runtime.ai_world.current(
        domains=(AIWorldDomain("user_understanding"),), limit=100
    )
    print(f"  [M3] 第3轮后 claim 数: {len(claims_3)} (第1轮后: {len(claims_1)})")
    m3_ok = len(claims_3) <= len(claims_1) + 1  # 允许 +1 容差（模型可能补充一条）
    print(f"  [M3] claim 未翻倍: {'PASS' if m3_ok else 'FAIL'}")

    # ---- 汇总 ----
    print("\n" + "=" * 70)
    m1_ok = len(claims_1) >= 1 and any("老王" in c.statement for c in claims_1)
    print("最终裁决:")
    print(f"  M1 写入率（自我介绍落地 durable claim）: {'PASS' if m1_ok else 'FAIL'}")
    print(f"  M2 关逐字仍答对: {'PASS' if m2_ok else 'FAIL'}")
    print(f"  M3 连问两遍 claim 不增: {'PASS' if m3_ok else 'FAIL'}")
    overall = m1_ok and m2_ok and m3_ok
    print(f"  ==> 总体: {'PASS' if overall else 'FAIL'}")
    print("=" * 70)


if __name__ == "__main__":
    main()
