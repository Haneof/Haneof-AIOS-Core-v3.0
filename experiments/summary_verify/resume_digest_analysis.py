"""续跑：复用已有 echo 库（9 维总结已在），只补今日总览 digest + 分析。

用法：python3 resume_digest_analysis.py --day 0
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "cleaning_ab"))
sys.path.insert(0, "src")

import sim_realtime  # noqa: E402

from aios_core.contracts.enums import ObjectType  # noqa: E402
from aios_core.query.search import WorldSearchIndex  # noqa: E402
from aios_core.storage.sqlite_store import SQLiteWorldStore  # noqa: E402
from aios_core.summaries import (  # noqa: E402
    DIGEST_DIMENSION,
    MultiScaleSummaryScheduler,
)
from verify_summary import (  # noqa: E402
    DIMENSION_SOURCE_CAPS,
    NOISE_TOKENS,
    SUBJECT,
    cleaning_admission,
)


def _call_raw(model: str, body_text: str, max_tokens: int) -> str:
    import harness
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": body_text}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        harness.PRIMARY_BASE_URL + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {harness.PRIMARY_API_KEY}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=900) as resp:
        data = json.load(resp)
    choice = data["choices"][0]
    text = (choice["message"].get("content") or "").strip()
    if not text:
        raise RuntimeError(f"空正文 finish_reason={choice.get('finish_reason')}")
    return text


def _digest_body(prepared) -> str:
    dlines = [
        f"- ({s.metadata.get('dimension', '?')}) {s.text}" for s in prepared.sources
    ]
    return (
        f"下面是用户 {prepared.window_start:%Y-%m-%d} 一天里 "
        f"{len(prepared.sources)} 个维度的 DAY 总结。请写一段中文「今日总览」，"
        "把这天跨维度发生过什么整合成一天全貌，保留关键细节，不编造，"
        f"直接输出正文不超过 300 字。\n\n" + "\n".join(dlines)
    )


def digest_with_patience(prepared, now) -> str:
    """digest 单独提交：主模型重试 2 轮（每轮 8 次指数退避），仍失败则切
    同端点备用模型（z-ai/glm-5.3-flash）完成——保证今日总览最终产出。"""
    import harness
    from aios_core.runtime.resilient_handler import SECONDARY_MODEL
    body = _digest_body(prepared)
    for model, rounds in ((harness.PRIMARY_MODEL, 2), (SECONDARY_MODEL, 2)):
        for r in range(rounds):
            try:
                text = _call_raw(model, body, 4000)
                if model != harness.PRIMARY_MODEL:
                    print(f"[resume] digest 使用备用模型 {model} 完成", flush=True)
                return text
            except Exception as exc:  # noqa: BLE001
                print(f"[resume] digest [{model}] 第 {r + 1} 轮失败："
                      f"{type(exc).__name__}: {str(exc)[:120]}", flush=True)
                time.sleep(60)
    raise RuntimeError("digest 所有模型/轮次均失败")


def summary_handler_real_model(prepared):
    from verify_summary import summary_handler_real_model as h
    return h(prepared)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int, default=0)
    ap.add_argument(
        "--digest-text-file",
        help="已产出的今日总览正文（模型端点不稳定时，用同提示词同模型的独立"
             "调用结果注入，仍走完整的 prepare/校验/commit 机制）",
    )
    args = ap.parse_args()
    day_idx = args.day
    injected = (
        Path(args.digest_text_file).read_text(encoding="utf-8").strip()
        if args.digest_text_file else None
    )

    db = HERE / f"_tmp_echo_{day_idx}.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    sched = MultiScaleSummaryScheduler(
        store=store, index=index, subject_id=SUBJECT,
        summary_handler=summary_handler_real_model,
        source_admission=cleaning_admission,
        dimension_source_caps=DIMENSION_SOURCE_CAPS,
    )
    now = sim_realtime.DATES[day_idx] + timedelta(days=1)

    # 1) digest（9 维总结已在库里）
    wins = sched._digest_candidate_windows(now=now)
    digest_content = None
    for start, end in wins:
        p = sched.digest_service.prepare(window_start=start, window_end=end)
        if not p.sources:
            continue
        content = injected if injected else digest_with_patience(p, now)
        c = sched.digest_service.commit(p, content=content, generated_at=now)
        digest_content = content
        print(f"[resume] digest 提交 {c.object_id} rev{c.revision} "
              f"reused={c.reused_existing}", flush=True)

    # 2) 分析（与 run_echo_driver 同口径）
    day = sim_realtime.DAYS[day_idx]
    day_date = sim_realtime.DATES[day_idx].date().isoformat()
    summaries = {}
    for payload in store.list_payloads(object_type=ObjectType.SUMMARY, subject_id=SUBJECT):
        dim = (payload.get("metadata") or {}).get("dimension")
        st = payload.get("summary_time") or {}
        if str(st.get("start", ""))[:10] != day_date:
            continue
        if payload.get("summary_status") != "current":
            continue
        summaries[dim] = {
            "content": payload["content"],
            "source_count": payload["coverage"]["source_count"],
        }

    rec_dim = {rec["id"]: rec["dim"] for rec in day["records"]}
    per_dim = {}
    for dim, info in summaries.items():
        if dim == DIGEST_DIMENSION:
            continue
        resp, hit = [], []
        for label, ids in day["checks"]:
            dims = {rec_dim.get(i) for i in ids}
            if dim not in dims:
                continue
            resp.append(label)
            if any(k in info["content"] for k in day["keywords"][label]):
                hit.append(label)
        per_dim[dim] = {
            "responsible": resp, "hit": hit,
            "rate": f"{len(hit)}/{len(resp)}" if resp else "n/a",
        }

    cross, covered = {}, 0
    for label, ids in day["checks"]:
        dims = {rec_dim.get(i) for i in ids}
        hit_dims = [d for d in dims if d in summaries
                    and any(k in summaries[d]["content"] for k in day["keywords"][label])]
        cross[label] = {"covered": bool(hit_dims), "hit_in_dims": sorted(hit_dims)}
        if hit_dims:
            covered += 1

    pollution = {}
    for dim, info in summaries.items():
        toks = [t for t in NOISE_TOKENS if t in info["content"]]
        if toks:
            pollution[dim] = toks

    out = {
        "day": day["name"],
        "n_dimension_summaries": len(summaries),
        "dimensions_summarized": sorted(summaries.keys()),
        "summaries": summaries,
        "per_dimension_echo": per_dim,
        "cross_dimension_covered": f"{covered}/{len(day['checks'])}",
        "cross_dimension_detail": cross,
        "noise_pollution_by_dimension": pollution,
        "daily_digest_present": DIGEST_DIMENSION in summaries,
        "daily_digest_content": digest_content or summaries.get(DIGEST_DIMENSION, {}).get("content"),
        "digest_echo": {},
    }
    if out["daily_digest_content"]:
        hits, resp = [], []
        for label, ids in day["checks"]:
            resp.append(label)
            if any(k in out["daily_digest_content"] for k in day["keywords"][label]):
                hits.append(label)
        out["digest_echo"] = {"responsible": resp, "hit": hits,
                              "rate": f"{len(hits)}/{len(resp)}"}

    print(json.dumps(out, ensure_ascii=False, indent=2))
    (HERE / f"result_echo_day{day_idx + 1}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("[resume] 完成，结果已写入 result_echo_day%d.json" % (day_idx + 1), flush=True)


if __name__ == "__main__":
    main()
