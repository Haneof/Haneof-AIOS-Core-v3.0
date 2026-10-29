"""The owner's actual decision criterion, measured directly.

"如果机制清洗后的数据和 AI 整理后的数据产生的认知差不多，那就可以采用机制清洗。"

So: take each arm's surviving records, feed them to the model as if it were the
day-summary step, and count how many of the pre-registered conclusions actually
come back out. Same model, same prompt, only the input set differs.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aios_core.runtime.resilient_handler import (  # noqa: E402
    PRIMARY_API_KEY,
    PRIMARY_BASE_URL,
    PRIMARY_MODEL,
)

from sim_day import COGNITION_CHECKS, RECORDS  # noqa: E402

os.environ.setdefault("AIOS_RPM_PACE", "0")

BY_ID = {r["id"]: r for r in RECORDS}

PROMPT = """下面是某位用户 2026-10-28 一天里进入系统的记录。

请回答：今天发生了哪些值得记住的事？只列事实，不要编造，每条一行，不超过 15 字。

记录：
{records}
"""

# 每条认知结论的"命中关键词"——只要总结里出现任意一组就认为还原出来了。
CHECK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "母亲住院（市二院心内科）": ("妈", "母亲", "住院", "二院", "第二人民"),
    "承诺周三前给张总合同": ("合同", "张总", "周三"),
    "头晕加重（两次递进）": ("头晕", "晕"),
    "与小李的工作冲突": ("小李", "吵", "冲突"),
    "减重五斤目标": ("减", "体重", "斤"),
    "周五体检 / 周四周会": ("体检", "周会", "周五", "周四"),
    "需带医保卡身份证": ("医保卡", "身份证", "带"),
}


def build_block(kept_ids: list[str]) -> str:
    lines = []
    for rid in kept_ids:
        rec = BY_ID[rid]
        if rec["kind"] == "numeric":
            lines.append(f"- [心率] 全天 1000 点采样，15:35-15:50 出现一次明显升高（约 128 bpm）")
            continue
        lines.append(f"- [{rec['dim']} {rec['t'].strftime('%H:%M')}] {rec['text']}")
    return "\n".join(lines)


def ask(kept_ids: list[str], tag: str) -> dict:
    block = build_block(kept_ids)
    body = {
        "model": PRIMARY_MODEL,
        "messages": [
            {"role": "user", "content": PROMPT.format(records=block)},
        ],
        "temperature": 0.2,
        # 这是推理模型：思考 token 会占用同一份预算。给得太少会吞掉正文，
        # 表现为 content 为空 + finish_reason=length，看起来像"总结不出来"。
        "max_tokens": 6000,
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
    with urllib.request.urlopen(req, timeout=900) as resp:
        payload = json.load(resp)
    choice = payload["choices"][0]
    finish = choice.get("finish_reason")
    usage = payload.get("usage") or {}
    text = choice["message"].get("content") or ""
    if not text.strip():
        raise RuntimeError(
            f"空正文（finish_reason={finish}, usage={usage}）— 视为测量失败，不计分"
        )
    if finish == "length":
        raise RuntimeError(f"输出被截断（finish_reason=length, usage={usage}）— 测量失败")
    hits = {}
    for label, required in COGNITION_CHECKS:
        kws = CHECK_KEYWORDS.get(label, ())
        hits[label] = any(k in text for k in kws)
    return {
        "tag": tag,
        "input_count": len(kept_ids),
        "input_chars": len(block),
        "elapsed": round(time.time() - t0, 1),
        "summary": text,
        "hits": hits,
        "hit_count": sum(1 for v in hits.values() if v),
        "finish_reason": finish,
        "usage": usage,
    }


def main() -> None:
    runs_path = Path(__file__).resolve().parent / "ai_runs.json"
    if not runs_path.exists():
        print("缺少 ai_runs.json")
        return
    runs = json.loads(runs_path.read_text(encoding="utf-8"))
    valid = [r for r in runs if "error" not in r]
    if not valid:
        print("AI 臂全部失败，无法做认知回声对比")
        return

    # 机制臂：全部保留
    mech_ids = [r["id"] for r in RECORDS]
    # AI 臂：取第一轮的判断（并报告各轮一致性）
    ai_ids = [
        str(d["id"])
        for d in valid[0]["decisions"]
        if str(d.get("decision", "")).lower() == "keep"
    ]

    results = []
    for ids, tag in ((mech_ids, "机制清洗后"), (ai_ids, "AI清洗后")):
        for attempt in range(2):
            try:
                res = ask(ids, tag)
                results.append(res)
                print(f"\n=== {tag} === 输入 {res['input_count']} 条 / {res['input_chars']} 字符 / {res['elapsed']}s")
                print(f"认知还原 {res['hit_count']}/{len(CHECK_KEYWORDS)}")
                for label, ok in res["hits"].items():
                    print(f"  {'命中' if ok else '丢失'}  {label}")
                print("--- 总结原文 ---")
                print(res["summary"][:900])
                break
            except Exception as exc:  # noqa: BLE001
                print(f"{tag} 第 {attempt+1} 次失败：{type(exc).__name__} {str(exc)[:100]}")
                if attempt == 1:
                    results.append({"tag": tag, "error": str(exc)})

    Path(__file__).resolve().parent.joinpath("cognition_echo.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
