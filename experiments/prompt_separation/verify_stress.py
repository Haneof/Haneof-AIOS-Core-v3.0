#!/usr/bin/env python3
"""压力验证：换了人设 + 加了量的模拟数据下，任务提示词与 token 上限是否还顶得住。

只新增 experiments/prompt_separation/ 下的文件；不改 src/、不改既有实验脚本。

三段（全部打真实 NVIDIA 端点，用 resilient_handler 的默认 key）：
  A annotate_sweep —— 同一压力日，分别按 batch=20/40/80 标注，定位 3000 token 输出上限
                       在多大批次开始截断（空正文 / 需要升级到 4000/6000 才出结果）。
  B summarize       —— 在厚维度（mic_audio 80 源）与几个事实密维度上总结，看 4000 上限是否够。
  C digest         —— 把 B 段产出的 5 个维度日总结合并为跨维总览，看 4000 上限是否够。

每步都如实记录 max_tokens(声明/生效)、output_chars、est_output_tokens、空正文/截断/504/升级，
结果合并写进 stress_result.json。
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CLEANING_AB = REPO / "experiments" / "cleaning_ab"

import verify_task_prompts as VT  # noqa: E402  (复用 call_model / task_runtime / score_annotate / harness)
from verify_task_prompts import (  # noqa: E402
    call_model,
    harness,
    render_task_prompt,
    score_annotate,
    task_runtime,
)
sys_path = __import__("sys")
sys_path.path.insert(0, str(CLEANING_AB))

from sim_stress import DAYS  # noqa: E402
from aios_core.prompts import (  # noqa: E402
    DimensionProfile,
    PromptRenderParams,
    TaskKind,
)

RESULT_PATH = HERE / "stress_result.json"
RUN_KEY = time.strftime("%Y-%m-%d %H:%M:%S")

STRESS_PROFILES: dict[str, DimensionProfile] = {
    "dim:mic_audio": DimensionProfile(
        dimension_key="dim:mic_audio", name="麦克风转写",
        data_shape="断续的人声转写片段，含环境背景声与无意义发声",
        keep_criteria=("承诺与截止期", "健康信号", "关系变化", "目标与待办", "金额", "工作事实"),
        drop_criteria=("无意义发声", "电视与环境背景声", "纯重复"),
        requires_dedicated_cleaning=True),
    "dim:payment": DimensionProfile(
        dimension_key="dim:payment", name="支付",
        data_shape="消费与转账记录",
        keep_criteria=("大额支出", "与事件相关的小额(设备/健康/行程)", "真实银行通知"),
        drop_criteria=("小额日常", "订阅自动续费", "广告")),
    "dim:order": DimensionProfile(
        dimension_key="dim:order", name="订单",
        data_shape="电商/外卖订单",
        keep_criteria=("设备/健康/社交相关待办", "有送达时间的行为事实"),
        drop_criteria=("纯小额无关设备")),
    "dim:calendar": DimensionProfile(
        dimension_key="dim:calendar", name="日历",
        data_shape="日程条目（时间点 + 标题）",
        keep_criteria=("未来节点", "截止期", "约定"), drop_criteria=()),
    "dim:note": DimensionProfile(
        dimension_key="dim:note", name="便签",
        data_shape="用户随手记",
        keep_criteria=("工作条款", "待办", "家庭事项", "出行清单"),
        drop_criteria=("误触乱码")),
    "dim:camera_visual": DimensionProfile(
        dimension_key="dim:camera_visual", name="摄像头视觉",
        data_shape="环境画面描述",
        keep_criteria=("佐证健康/社交/出行的事实画面"), drop_criteria=("纯环境低值")),
    "dim:app_usage": DimensionProfile(
        dimension_key="dim:app_usage", name="App 行为",
        data_shape="通知推送与使用时长",
        keep_criteria=("自身行为遥测", "真实银行通知"),
        drop_criteria=("广告推送", "无关新闻", "系统通知")),
    "dim:external_chat": DimensionProfile(
        dimension_key="dim:external_chat", name="外部聊天",
        data_shape="他人发来的消息",
        keep_criteria=("邀约与寒暄", "外部压力与截止期", "金额", "家庭关系"),
        drop_criteria=("群发广告", "钓鱼", "重复催促", "无指向群聊")),
}

CURRENT_TASK = "all"


def log(msg: str) -> None:
    print(msg, flush=True)


def load_result() -> dict:
    if RESULT_PATH.exists():
        try:
            return json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}
    return {}


def save_result(result: dict) -> None:
    meta = result.get("_meta", {})
    meta.update({
        "script": "experiments/prompt_separation/verify_stress.py",
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "endpoint": harness.PRIMARY_BASE_URL,
        "primary_model": harness.PRIMARY_MODEL,
        "run_key": RUN_KEY,
        "stats": dict(VT.STATS),
        "note": ("token 用字符数估算（中文约 1.6 字符/token）；max_tokens_effective 是声明值与"
                 "实测地板取大，escalate 到 4000/6000 时 token_escalation_used 会计数。"),
    })
    result["_meta"] = meta
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def annotate_records(records: list[dict]) -> list[dict]:
    return [{"id": r["id"], "t": r["t"].strftime("%Y-%m-%d %H:%M"),
             "dimension": r["dim"], "text": r["text"]} for r in records]


def run_annotate_sweep(day_idx: int, batch_sizes: list[int]) -> dict:
    day = DAYS[day_idx]
    records = [r for r in day["records"] if r["kind"] != "numeric"]
    rt = task_runtime(TaskKind.ANNOTATE)
    out: dict = {"caps": {"declared": rt.max_output_tokens,
                          "floor": VT.MIN_EFFECTIVE_TOKENS[TaskKind.ANNOTATE]},
                 "batches_by_size": {}, "metrics_by_size": {}}
    log(f"A. ANNOTATE 压力扫描 | 日={day['name']} | 非数值记录={len(records)} | "
        f"声明上限={rt.max_output_tokens} | 批次={batch_sizes}")

    for B in batch_sizes:
        decisions: dict[str, dict] = {}
        batch_meta: list[dict] = []
        n_batches = max(1, -(-len(records) // B))
        log(f"  —— batch={B}：分 {n_batches} 批 ——")
        for bstart in range(0, len(records), B):
            chunk = records[bstart:bstart + B]
            bno = bstart // B + 1
            profiles = tuple(STRESS_PROFILES[d] for d in sorted({r["dim"] for r in chunk})
                             if d in STRESS_PROFILES)
            prompt = render_task_prompt(
                TaskKind.ANNOTATE,
                params=PromptRenderParams(records=tuple(annotate_records(chunk)),
                                          dimensions=profiles,
                                          window_start="2026-11-03", window_end="2026-11-03"))
            res = call_model(
                [{"role": "system", "content": prompt},
                 {"role": "user", "content": "请按上面的契约逐条标注，只输出 JSON 数组。"}],
                rt.max_output_tokens, f"stress-annotate-B{B}-b{bno}", TaskKind.ANNOTATE)
            entry = {"batch": B, "bno": bno, "n_records": len(chunk),
                     "prompt_chars": len(prompt),
                     "est_in_tokens": round(len(prompt) / 1.6),
                     "max_tokens_declared": res.get("max_tokens_declared"),
                     "max_tokens_effective": res.get("max_tokens_effective"),
                     "max_tokens": res.get("max_tokens"), "rounds": res.get("rounds"),
                     "model": res.get("model"), "ok": res["ok"],
                     "output_chars": res.get("output_chars"),
                     "est_output_tokens": res.get("est_output_tokens"),
                     "token_escalation": res.get("max_tokens") != res.get("max_tokens_declared")}
            if not res["ok"]:
                entry["error"] = res.get("last_error")
                batch_meta.append(entry)
                log(f"  [B{B} 批次{bno}] 失败：{res.get('last_error')}")
                continue
            parsed = None
            for attempt in (1, 2):
                try:
                    parsed = harness._extract_json(res["text"])
                    break
                except (ValueError, json.JSONDecodeError):
                    if attempt == 2:
                        break
                    log(f"  [B{B} 批次{bno}] JSON 解析失败，重试一次")
                    res = call_model(
                        [{"role": "system", "content": prompt},
                         {"role": "user", "content": "请只输出 JSON 数组，不要任何解释。"}],
                        rt.max_output_tokens, f"stress-annotate-B{B}-b{bno}-retry",
                        TaskKind.ANNOTATE)
                    if not res["ok"]:
                        break
            if parsed is None:
                entry["parsed"] = False
                entry["raw_excerpt"] = (res.get("text") or "")[:300]
                batch_meta.append(entry)
                log(f"  [B{B} 批次{bno}] 两次都没拿到合法 JSON")
                continue
            entry["parsed"] = True
            entry["n_decisions"] = len(parsed)
            for item in parsed:
                rid = str(item.get("id") or item.get("object_id") or "")
                if rid:
                    decisions[rid] = {"decision": str(item.get("decision", "")).lower(),
                                      "relevance": str(item.get("relevance", "")).lower(),
                                      "reason": str(item.get("reason", ""))}
            batch_meta.append(entry)
            log(f"  [B{B} 批次{bno}] 解析 {len(parsed)} 条，输出 "
                f"{res.get('output_chars')} 字符 / ~{res.get('est_output_tokens')} token，"
                f"max_tokens={res.get('max_tokens')}，轮次={res.get('rounds')}")
        out["batches_by_size"][str(B)] = batch_meta
        m = score_annotate(day, records, decisions)
        out["metrics_by_size"][str(B)] = m["metrics"]
        log(f"  batch={B} 打分：{m['metrics']}")
    return out


def run_summarize(day_idx: int, dims: list[str]) -> dict:
    rt = task_runtime(TaskKind.SUMMARIZE)
    day = DAYS[day_idx]
    out: dict = {"cap": rt.max_output_tokens, "dimensions": {}, "fact_hits": [],
                 "hit_total": 0, "fact_total": 0}
    summaries: dict[str, str] = {}
    for dim in dims:
        recs = [r for r in day["records"] if r["dim"] == dim and r["kind"] != "numeric"]
        if not recs:
            continue
        sources = tuple({"occurred_at": r["t"].strftime("%Y-%m-%d %H:%M"),
                         "dimension": r["dim"], "text": r["text"]} for r in recs)
        prompt = render_task_prompt(
            TaskKind.SUMMARIZE,
            params=PromptRenderParams(sources=sources,
                                      dimension=STRESS_PROFILES.get(dim, DimensionProfile(dimension_key=dim)),
                                      granularity="day", window_start="2026-11-03",
                                      window_end="2026-11-03"))
        res = call_model(
            [{"role": "system", "content": prompt},
             {"role": "user", "content": "请按上面的契约输出这段总结正文。"}],
            rt.max_output_tokens, f"stress-summarize-{dim}", TaskKind.SUMMARIZE)
        block = {"dim": dim, "n_sources": len(recs), "prompt_chars": len(prompt),
                 "est_in_tokens": round(len(prompt) / 1.6),
                 "max_tokens": res.get("max_tokens"),
                 "rounds": res.get("rounds"), "model": res.get("model"),
                 "ok": res["ok"],
                 "output_chars": res.get("output_chars"),
                 "est_output_tokens": res.get("est_output_tokens")}
        if not res["ok"]:
            block["error"] = res.get("last_error")
            out["dimensions"][dim] = block
            log(f"  [{dim}] 失败：{res.get('last_error')}")
            continue
        text = res["text"]
        summaries[dim] = text
        block.update({"summary": text, "summary_chars": len(text),
                      "est_output_tokens": round(len(text) / 1.6)})
        dim_ids = {r["id"] for r in recs}
        hits = []
        for label, ids in day["checks"]:
            if not (set(ids) & dim_ids):
                continue
            kws = day["keywords"].get(label, ())
            matched = [k for k in kws if k in text]
            hits.append({"dim": dim, "fact": label, "matched_keywords": matched,
                         "hit": bool(matched)})
        block["fact_hits"] = hits
        block["hit_count"] = sum(1 for h in hits if h["hit"])
        block["fact_count"] = len(hits)
        out["dimensions"][dim] = block
        out["fact_hits"].extend(hits)
        out["hit_total"] = sum(1 for h in out["fact_hits"] if h["hit"])
        out["fact_total"] = len(out["fact_hits"])
        log(f"  [{dim}] {len(recs)} 源 → 总结 {len(text)} 字符 / ~{block['est_output_tokens']} token，"
            f"事实命中 {block['hit_count']}/{block['fact_count']}")
    out["summaries"] = summaries
    return out


def run_digest(summary_dims: list[str], summaries: dict[str, str]) -> dict:
    rt = task_runtime(TaskKind.DIGEST)
    sources = tuple({"occurred_at": "2026-11-03", "dimension": d, "text": summaries[d]}
                    for d in summary_dims if d in summaries)
    if not sources:
        return {"ok": False, "error": "no summaries to merge"}
    prompt = render_task_prompt(
        TaskKind.DIGEST,
        params=PromptRenderParams(sources=sources, granularity="day",
                                  window_start="2026-11-03", window_end="2026-11-03"))
    res = call_model(
        [{"role": "system", "content": prompt},
         {"role": "user", "content": "请按上面的契约输出这段跨维度总览正文。"}],
        rt.max_output_tokens, "stress-digest", TaskKind.DIGEST)
    block = {"n_sources": len(sources), "prompt_chars": len(prompt),
             "est_in_tokens": round(len(prompt) / 1.6),
             "max_tokens": res.get("max_tokens"), "rounds": res.get("rounds"),
             "model": res.get("model"), "ok": res["ok"],
             "output_chars": res.get("output_chars"),
             "est_output_tokens": res.get("est_output_tokens")}
    if res["ok"]:
        block["digest"] = res["text"]
        block["digest_chars"] = len(res["text"])
    else:
        block["error"] = res.get("last_error")
    log(f"  DIGEST 合并 {len(sources)} 维 → 输出 {block.get('output_chars')} 字符 / "
        f"~{block.get('est_output_tokens')} token，max_tokens={res.get('max_tokens')}")
    return block


def main() -> None:
    global CURRENT_TASK
    ap = argparse.ArgumentParser(description="压力验证：换人设+加量下的任务提示词与 token 上限")
    ap.add_argument("--task", choices=["annotate", "summarize", "digest", "all"], default="all")
    ap.add_argument("--batch-sizes", default="20,40,80", help="ANNOTATE 扫描的批次大小")
    ap.add_argument("--summarize-dims", default="dim:mic_audio,dim:calendar,dim:payment,dim:external_chat,dim:note")
    ap.add_argument("--day", type=int, default=0)
    args = ap.parse_args()
    batch_sizes = [int(x) for x in args.batch_sizes.split(",") if x.strip()]
    args.summarize_dims = [x.strip() for x in args.summarize_dims.split(",") if x.strip()]
    CURRENT_TASK = args.task

    result = load_result()
    log(f"=== 压力验证 | task={args.task} | endpoint={harness.PRIMARY_BASE_URL} | "
        f"model={harness.PRIMARY_MODEL} ===")

    if args.task in ("annotate", "all"):
        t0 = time.time()
        out = run_annotate_sweep(args.day, batch_sizes)
        out["elapsed_s"] = round(time.time() - t0, 1)
        result["annotate_sweep"] = out
        save_result(result)
        log(f"A 段完成，{out['elapsed_s']}s")

    if args.task in ("summarize", "all"):
        t0 = time.time()
        out = run_summarize(args.day, args.summarize_dims)
        out["elapsed_s"] = round(time.time() - t0, 1)
        result["summarize"] = out
        save_result(result)
        log(f"B 段完成，{out['elapsed_s']}s")

    if args.task in ("digest", "all"):
        t0 = time.time()
        summaries = (result.get("summarize") or {}).get("summaries", {})
        dims = args.summarize_dims
        out = run_digest(dims, summaries)
        out["elapsed_s"] = round(time.time() - t0, 1)
        result["digest"] = out
        save_result(result)
        log("C 段完成")

    save_result(result)
    log(f"结果已写入 {RESULT_PATH}")
    log(f"调用统计：{dict(VT.STATS)}")


if __name__ == "__main__":
    main()
