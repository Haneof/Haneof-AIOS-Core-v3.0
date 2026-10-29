"""Arm B — AI-judged cleaning. One batch call per run, N runs for variance.

Prompt discipline: the model is never shown the ground-truth labels, and the
instruction is deliberately neutral — it does not push toward deleting more or
keeping more. It states the same boundary the constitution states for cleaning,
plus the judgment the owner wants tested (drop transient noise, keep evidence).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aios_core.runtime.resilient_handler import (  # noqa: E402
    PRIMARY_API_KEY,
    PRIMARY_BASE_URL,
    PRIMARY_MODEL,
)

from sim_day import RECORDS  # noqa: E402

os.environ.setdefault("AIOS_RPM_PACE", "0")

SYSTEM = """你是一个可穿戴 AI 系统的"基础数据清理"环节。

你拿到的是某一天从各个来源采集进来的原始记录。你的任务是对每一条做出判断：

- KEEP：保留。任何可能承载长期价值的事实——身份、承诺、截止期、健康信号、
  关系变化、目标、待办、重要金额、未来节点，或者能佐证上述内容的观察。
- DROP：删除。纯粹的瞬时噪声——无意义发声、客套、重复且无新信息的内容、
  广告与系统推送、乱码误触、已完结的一次性琐事。

两条硬约束：
1. 一条记录里即使大部分是废话，只要夹带了任何重要事实，就必须 KEEP，
   不得整条丢弃。
2. 不要把玩笑、夸张表达误当成真实紧急事件；也不要把客套的口头承诺
   当成真正的承诺。

只输出一个 JSON 数组，不要任何解释文字，格式：
[{"id": "记录id", "decision": "keep|drop", "reason": "不超过15字"}]
"""


def _records_block() -> str:
    lines = []
    for rec in RECORDS:
        if rec["kind"] == "numeric":
            lines.append(
                f"- id={rec['id']} | 来源={rec['dim']} | 数值流："
                f"{rec['text']}（请按保留处理，交由机制压缩）"
            )
            continue
        lines.append(
            f"- id={rec['id']} | 来源={rec['dim']} | 时间={rec['t'].strftime('%H:%M')} | 内容：{rec['text']}"
        )
    return "\n".join(lines)


def _extract_json(text: str):
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1).strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"响应中没有 JSON 数组：{text[:200]}")
    return json.loads(text[start : end + 1])


def call_model(run_index: int) -> dict:
    prompt = (
        f"下面是 2026-10-28 一天采集到的 {len(RECORDS)} 条原始记录。\n\n"
        f"{_records_block()}\n\n"
        "请逐条判断并输出 JSON 数组。"
    )
    body = {
        "model": PRIMARY_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 4000,
    }
    req = urllib.request.Request(
        PRIMARY_BASE_URL + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {PRIMARY_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as resp:
        payload = json.load(resp)
    elapsed = time.time() - t0
    content = payload["choices"][0]["message"]["content"]
    decisions = _extract_json(content)
    return {
        "run": run_index,
        "elapsed": round(elapsed, 1),
        "decisions": decisions,
        "raw_chars": len(content or ""),
    }


def run(times: int = 3) -> list[dict]:
    results = []
    for i in range(1, times + 1):
        for attempt in range(2):
            try:
                result = call_model(i)
                results.append(result)
                print(f"  第 {i} 轮完成：{result['elapsed']}s，{len(result['decisions'])} 条判断", flush=True)
                break
            except (urllib.error.HTTPError, urllib.error.URLError, ValueError, KeyError) as exc:
                print(f"  第 {i} 轮第 {attempt + 1} 次失败：{type(exc).__name__} {str(exc)[:120]}", flush=True)
                if attempt == 1:
                    results.append({"run": i, "error": f"{type(exc).__name__}: {exc}"})
                time.sleep(5)
    return results


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"AI 清洗臂 — 模型 {PRIMARY_MODEL}，共 {n} 轮", flush=True)
    out = run(n)
    Path("ai_runs.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("已写入 ai_runs.json")
