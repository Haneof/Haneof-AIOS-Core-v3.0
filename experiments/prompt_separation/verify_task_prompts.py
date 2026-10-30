#!/usr/bin/env python3
"""真实模型验证：按契约分离的任务提示词（src/aios_core/prompts）是否不劣于实验层临时提示词。

只新增 experiments/prompt_separation/ 下的文件；不修改 src/、不修改既有实验脚本、不 git commit。

三段：
  A annotate  —— 用 TaskKind.ANNOTATE 跑 sim_realtime 的采集日，与 sim 自带标签比
                 删除纯度 / 误删 / 召回，并单列「社交邀约」「玩笑夸张」两类易错样本。
  B summarize —— 用 TaskKind.SUMMARIZE 跑两个事实最密的维度，用关键词命中打分。
  C contract  —— 不调模型，只渲染六个任务提示词量字符数，并与老的 grok_provider
                 常驻提示词（53 能力 + 纪律 + 规则）做量级对比。

用法（每步可单独跑，也可续跑）：
  python3 verify_task_prompts.py --task annotate
  python3 verify_task_prompts.py --task summarize
  python3 verify_task_prompts.py --task contract   # 不调模型
  python3 verify_task_prompts.py --task all

每一步结束立刻把结果合并写进 result.json：跑崩了也不会丢已完成的部分。
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import io
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CLEANING_AB = REPO / "experiments" / "cleaning_ab"

sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(CLEANING_AB))

from aios_core.prompts import (  # noqa: E402
    DimensionProfile,
    PromptRenderParams,
    TaskKind,
    render_task_prompt,
    task_runtime,
)

import harness  # noqa: E402
from aios_core.runtime.resilient_handler import SECONDARY_MODEL  # noqa: E402
from sim_realtime import DATES, DAYS  # noqa: E402

BACKUP_MODEL = SECONDARY_MODEL          # z-ai/glm-5.3-flash，同端点备用
RESULT_PATH = HERE / "result.json"

# 甜点值来自实测：推理模型把预算耗在思考上会返回空正文；8000 会触发网关 504。
#
# ANNOTATE 的 task_runtime 声明 max_output_tokens=1200，但同一端点同一模型在 20 条批次上
# 连续返回「空正文 finish_reason=length」（思考把 1200 全吃掉了），所以首个 attempt 用
# max(声明值, 实测地板)。声明值与实测值都记进结果，不掩盖这个偏差。
MIN_EFFECTIVE_TOKENS = {
    TaskKind.ANNOTATE: 2500,
    TaskKind.SUMMARIZE: 4000,
}
ESCALATE_TOKENS = {
    TaskKind.ANNOTATE: 4000,
    TaskKind.SUMMARIZE: 6000,
}

# 维度档案是「参数」而不是提示词文本——这正是新提示词与老提示词的分界。
DIM_PROFILES: dict[str, DimensionProfile] = {
    "dim:mic_audio": DimensionProfile(
        dimension_key="dim:mic_audio",
        name="麦克风转写",
        data_shape="断续的人声转写片段，含环境背景声与无意义发声",
        keep_criteria=("承诺与截止期", "健康信号", "关系变化", "目标与待办", "金额"),
        drop_criteria=("无意义发声", "电视与环境背景声", "纯重复"),
        requires_dedicated_cleaning=True,
    ),
    "dim:app_usage": DimensionProfile(
        dimension_key="dim:app_usage",
        name="App 行为",
        data_shape="通知推送与使用时长记录",
        keep_criteria=("自身行为遥测（阅读/运动/使用时长）", "真实银行或系统通知"),
        drop_criteria=("广告推送", "无关新闻推送", "形似银行的钓鱼短信"),
    ),
    "dim:calendar": DimensionProfile(
        dimension_key="dim:calendar",
        name="日历",
        data_shape="日程条目（时间点 + 标题）",
        keep_criteria=("未来节点", "截止期", "约定"),
        drop_criteria=(),
    ),
    "dim:external_chat": DimensionProfile(
        dimension_key="dim:external_chat",
        name="外部聊天",
        data_shape="他人发来的消息",
        keep_criteria=("他人邀约与寒暄（关系维系信号）", "外部压力与截止期"),
        drop_criteria=("群发广告", "钓鱼短信", "重复催促"),
    ),
}

INVITE_RE = re.compile(r"去不去|去吗|钓鱼|喝咖啡|一起|有空|约个|聚一下")
JOKE_RE = re.compile(r"世界末日|就辞职|不干了|辞职不干")

RUN_KEY = time.strftime("%Y-%m-%d %H:%M:%S")
CURRENT_TASK = "all"

STATS: dict[str, int] = {
    "calls": 0, "ok": 0, "failed": 0,
    "gateway_504": 0, "rate_429": 0, "empty_body": 0, "truncated": 0,
    "internal_retry_attempts": 0, "model_fallback_used": 0, "token_escalation_used": 0,
}
CALLS: list[dict] = []


# ---------------------------------------------------------------------------
# 基础设施：进度打印 / 结果落盘 / 带统计的模型调用
# ---------------------------------------------------------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


def load_result() -> dict:
    if RESULT_PATH.exists():
        try:
            return json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            log(f"  [warn] 已有 result.json 无法解析（{exc}），从头开始")
    return {}


def save_result(result: dict) -> None:
    """落盘。每次进程覆盖自己那一条 run，跨进程累计 504/空正文等计数。"""
    previous: dict = {}
    if RESULT_PATH.exists():
        try:
            previous = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            previous = {}
    prev_meta = previous.get("_meta") or {}
    runs = [r for r in prev_meta.get("runs", []) if r.get("run_key") != RUN_KEY]
    runs.append({"run_key": RUN_KEY, "task": CURRENT_TASK, "stats": dict(STATS),
                 "calls": list(CALLS)})
    cumulative: dict[str, int] = {}
    for run in runs:
        for key, value in run["stats"].items():
            cumulative[key] = cumulative.get(key, 0) + value
    result["_meta"] = {
        "script": "experiments/prompt_separation/verify_task_prompts.py",
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "endpoint": harness.PRIMARY_BASE_URL,
        "primary_model": "minimaxai/minimax-m3.1-flash",
        "backup_model": BACKUP_MODEL,
        "call_wrapper": "experiments/cleaning_ab/harness.py::_call_model（内部 504/空正文退避重试）",
        "usage_note": "harness._call_model 只返回正文，不返回 usage；token 用字符数估算（中文约 1.6 字符/token）",
        "cumulative_stats": cumulative,
        "runs": runs,
        "calls": [c for run in runs for c in run["calls"]],
        "known_issue": (
            "task_runtime(ANNOTATE).max_output_tokens=1200 在这个思考型模型上不够：20 条批次连续"
            "返回「空正文 finish_reason=length」（≥2 次），思考把 1200 全吃掉。故首个 attempt 抬到"
            "实测地板 2500，声明值与实测值都记在每批的 max_tokens_declared / max_tokens 里。"
        ),
    }
    RESULT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class _Tee(io.TextIOBase):
    """把 harness 的退避日志抄一份下来，用来数 504 / 空正文到底发生了几次。"""

    def __init__(self, stream, sink: list[str]) -> None:
        self._stream = stream
        self._sink = sink

    def write(self, s: str) -> int:
        self._sink.append(s)
        return self._stream.write(s)

    def flush(self) -> None:
        self._stream.flush()


@contextlib.contextmanager
def capture_harness_log():
    sink: list[str] = []
    old = sys.stdout
    sys.stdout = _Tee(old, sink)
    try:
        yield sink
    finally:
        sys.stdout = old


def _classify(log_text: str) -> None:
    STATS["internal_retry_attempts"] += log_text.count("次失败")
    STATS["gateway_504"] += len(re.findall(r"504|Gateway|gateway", log_text))
    STATS["rate_429"] += len(re.findall(r"429|rate", log_text))
    STATS["empty_body"] += log_text.count("空正文")
    STATS["truncated"] += log_text.count("输出被截断")


def call_model(messages: list[dict], max_tokens: int, tag: str, task: TaskKind) -> dict:
    """调真实模型。策略：任务自带 max_tokens → 加大预算 → 换备用模型。

    完全串行，绝不并发；每一步都由 harness 内部做指数退避（8/16/32/64/128/180/240s）。
    """
    escalate = ESCALATE_TOKENS.get(task, 4000)
    floor = MIN_EFFECTIVE_TOKENS.get(task, max_tokens)
    effective = max(max_tokens, floor)
    plan = [(harness.PRIMARY_MODEL, effective)]
    if escalate > effective:
        plan.append((harness.PRIMARY_MODEL, escalate))
    plan.append((BACKUP_MODEL, max(escalate, effective)))

    original = harness.PRIMARY_MODEL
    record = {
        "tag": tag, "task": str(task), "ok": False,
        "max_tokens_declared": max_tokens,
        "max_tokens_effective": effective,
        "prompt_chars": sum(len(m["content"]) for m in messages),
    }
    try:
        for round_no, (model, tokens) in enumerate(plan, start=1):
            if round_no > 1:
                log(f"  [{tag}] 第 {round_no} 轮：model={model} max_tokens={tokens}")
                if model == BACKUP_MODEL:
                    STATS["model_fallback_used"] += 1
                if tokens != max_tokens:
                    STATS["token_escalation_used"] += 1
            harness.PRIMARY_MODEL = model
            t0 = time.time()
            log_sink: list[str] = []
            try:
                with capture_harness_log() as sink:
                    try:
                        text = harness._call_model(messages, tokens, f"{tag}#{round_no}")
                    finally:
                        log_sink.extend(sink)
                _classify("".join(log_sink))
                STATS["calls"] += 1
                STATS["ok"] += 1
                record.update({
                    "ok": True, "model": model, "max_tokens": tokens,
                    "rounds": round_no, "elapsed_s": round(time.time() - t0, 1),
                    "output_chars": len(text),
                    "est_output_tokens": round(len(text) / 1.6),
                    "est_prompt_tokens": round(record["prompt_chars"] / 1.6),
                    "text": text,
                })
                CALLS.append({k: v for k, v in record.items() if k != "text"})
                log(f"  [{tag}] 成功：{record['elapsed_s']}s，{len(text)} 字符，"
                    f"model={model}，max_tokens={tokens}")
                return record
            except Exception as exc:  # noqa: BLE001 - 失败必须如实记录，不静默
                _classify("".join(log_sink))
                msg = f"{type(exc).__name__}: {exc}"
                if "空正文" in msg:
                    STATS["empty_body"] += 1
                elif "截断" in msg:
                    STATS["truncated"] += 1
                STATS["calls"] += 1
                STATS["failed"] += 1
                record["last_error"] = msg[:200]
                record["rounds"] = round_no
                log(f"  [{tag}] 第 {round_no} 轮失败：{msg[:120]}")
    finally:
        harness.PRIMARY_MODEL = original
    record["elapsed_s"] = round(record.get("elapsed_s", 0.0), 1)
    CALLS.append({k: v for k, v in record.items() if k != "text"})
    return record


# ---------------------------------------------------------------------------
# A. ANNOTATE
# ---------------------------------------------------------------------------
def day_scope(day_idx: int) -> tuple[dict, list[dict]]:
    """返回 (sim 的 day, 参与标注的记录)。数值流 hr 由机制侧压缩，不进标注。"""
    day = DAYS[day_idx]
    records = [r for r in day["records"] if r["kind"] != "numeric"]
    return day, records


def annotate_records(records: list[dict]) -> list[dict]:
    return [
        {
            "id": r["id"],
            "t": r["t"].strftime("%Y-%m-%d %H:%M"),
            "dimension": r["dim"],
            "text": r["text"],
        }
        for r in records
    ]


def hard_case_of(text: str, dim: str) -> str | None:
    if dim == "dim:external_chat" and INVITE_RE.search(text):
        return "社交邀约"
    if JOKE_RE.search(text):
        return "玩笑夸张"
    return None


def run_annotate(args) -> dict:
    out: dict = {"batches": [], "days": {}}
    rt = task_runtime(TaskKind.ANNOTATE)
    log(f"A. ANNOTATE  task_runtime.max_output_tokens={rt.max_output_tokens}，"
        f"实测地板={MIN_EFFECTIVE_TOKENS[TaskKind.ANNOTATE]}（1200 在这批数据上返回空正文），"
        f"批次大小={args.batch_size}")

    for day_idx in args.days:
        day, records = day_scope(day_idx)
        date = DATES[day_idx].strftime("%Y-%m-%d")
        log(f"  —— {day['name']}（{date}）共 {len(records)} 条非数值记录，"
            f"分 {max(1, -(-len(records) // args.batch_size))} 批串行跑 ——")
        decisions: dict[str, dict] = {}
        batch_meta: list[dict] = []

        for bstart in range(0, len(records), args.batch_size):
            chunk = records[bstart:bstart + args.batch_size]
            bno = bstart // args.batch_size + 1
            log(f"  [{day['name']} 批次{bno}] {len(chunk)} 条，渲染提示词…")
            profiles = tuple(
                DIM_PROFILES[d] for d in sorted({r["dim"] for r in chunk})
                if d in DIM_PROFILES
            )
            prompt = render_task_prompt(
                TaskKind.ANNOTATE,
                params=PromptRenderParams(
                    records=tuple(annotate_records(chunk)),
                    dimensions=profiles,
                    window_start=date, window_end=date,
                ),
            )
            log(f"  [{day['name']} 批次{bno}] 提示词 {len(prompt)} 字符，调用模型…")
            res = call_model(
                [{"role": "system", "content": prompt},
                 {"role": "user", "content": "请按上面的契约逐条标注，只输出 JSON 数组。"}],
                rt.max_output_tokens, f"annotate-{day['name']}-b{bno}", TaskKind.ANNOTATE,
            )
            entry = {
                "day": day["name"], "batch": bno, "n_records": len(chunk),
                "prompt_chars": len(prompt),
                "dimensions_injected": [p.dimension_key for p in profiles],
                "model": res.get("model"), "max_tokens": res.get("max_tokens"),
                "max_tokens_declared": res.get("max_tokens_declared"),
                "rounds": res.get("rounds"), "elapsed_s": res.get("elapsed_s"),
                "ok": res["ok"],
            }
            if not res["ok"]:
                entry["error"] = res.get("last_error")
                batch_meta.append(entry)
                log(f"  [{day['name']} 批次{bno}] 失败：{res.get('last_error')}")
                continue

            # JSON 解析失败要重试一次，并如实记录，不静默吞掉
            parsed = None
            parse_error = None
            for attempt in (1, 2):
                try:
                    parsed = harness._extract_json(res["text"])
                    break
                except (ValueError, json.JSONDecodeError) as exc:
                    parse_error = f"{type(exc).__name__}: {str(exc)[:160]}"
                    log(f"  [{day['name']} 批次{bno}] JSON 解析第 {attempt} 次失败：{parse_error}")
                    if attempt == 2:
                        break
                    log(f"  [{day['name']} 批次{bno}] 用同一提示词重试一次…")
                    res = call_model(
                        [{"role": "system", "content": prompt},
                         {"role": "user", "content": "请按上面的契约逐条标注，只输出 JSON 数组。再次强调：只输出 JSON 数组，不要任何解释文字。"}],
                        rt.max_output_tokens,
                        f"annotate-{day['name']}-b{bno}-retry", TaskKind.ANNOTATE,
                    )
                    if not res["ok"]:
                        break

            entry["json_parse_error"] = parse_error
            entry["raw_output_chars"] = len(res.get("text", ""))
            if parsed is None:
                entry["parsed"] = False
                entry["raw_excerpt"] = (res.get("text") or "")[:400]
                batch_meta.append(entry)
                log(f"  [{day['name']} 批次{bno}] 两次都没拿到合法 JSON，记入结果（不伪造）")
                continue

            entry["parsed"] = True
            entry["n_decisions"] = len(parsed)
            entry["raw_excerpt"] = (res.get("text") or "")[:400]
            for item in parsed:
                rid = str(item.get("id") or item.get("object_id") or "")
                if rid:
                    decisions[rid] = {
                        "decision": str(item.get("decision", "")).lower(),
                        "relevance": str(item.get("relevance", "")).lower(),
                        "reason": str(item.get("reason", "")),
                    }
            batch_meta.append(entry)
            log(f"  [{day['name']} 批次{bno}] 解析到 {len(parsed)} 条判定，累计 {len(decisions)}")

        out["batches"].extend(batch_meta)
        out["days"][day["name"]] = score_annotate(day, records, decisions)
        log(f"  {day['name']} 打分完成：{out['days'][day['name']]['metrics']}")
        save_result({"annotate": out})   # 每天落盘一次

    return out


def score_annotate(day: dict, records: list[dict], decisions: dict[str, dict]) -> dict:
    labels = day["labels"]
    in_scope = {r["id"] for r in records}
    gt_drop = {rid for rid, (lab, _) in labels.items()
               if lab == "DROP" and rid in in_scope}
    gt_keep = {rid for rid, (lab, _) in labels.items()
               if lab == "KEEP" and rid in in_scope}

    ai_drop = {rid for rid, d in decisions.items()
               if d["decision"] == "drop" and rid in in_scope}
    unlabeled = sorted(in_scope - set(decisions))

    hit = ai_drop & gt_drop
    false_drop = sorted(ai_drop & gt_keep)          # 被标 drop 但实际该留 —— 危险
    missed = sorted(gt_drop - ai_drop)              # 真噪声没标出来 —— 无害

    purity = round(len(hit) / len(ai_drop), 3) if ai_drop else 1.0
    recall = round(len(hit) / len(gt_drop), 3) if gt_drop else 1.0

    by_id = {r["id"]: r for r in records}
    hard_cases = []
    for rid in in_scope:
        rec = by_id[rid]
        kind = hard_case_of(rec["text"], rec["dim"])
        if kind is None:
            continue
        gt = labels.get(rid, ("?", ""))[0]
        got = decisions.get(rid, {}).get("decision", "(未标注)")
        if kind == "社交邀约":
            good = got != "drop"
        else:
            good = got == "drop"
        hard_cases.append({
            "id": rid, "class": kind, "dim": rec["dim"],
            "text": rec["text"][:60], "gt": gt,
            "model_decision": got,
            "expected": "keep" if kind == "社交邀约" else "drop",
            "verdict": "PASS" if good else "FAIL",
            "reason": decisions.get(rid, {}).get("reason", ""),
        })

    detail = []
    for rid in sorted(ai_drop):
        rec = by_id.get(rid, {})
        detail.append({
            "id": rid, "dim": rec.get("dim", "?"),
            "text": (rec.get("text") or "")[:60],
            "gt": labels.get(rid, ("?", ""))[0],
            "verdict": "删得对" if rid in gt_drop else "误删(该留)",
            "reason": decisions.get(rid, {}).get("reason", ""),
        })

    return {
        "n_scope": len(in_scope),
        "metrics": {
            "drop_purity": purity,          # 被标 drop 里真是噪声的比例（基线 1.0）
            "false_drop_count": len(false_drop),   # 误删（基线 0）
            "drop_recall": recall,
            "n_true_noise": len(gt_drop),
            "n_ai_drop": len(ai_drop),
            "n_correct_drop": len(hit),
        },
        "false_dropped_ids": false_drop,
        "missed_noise_ids": missed,
        "unlabeled_ids": unlabeled,
        "planned_drops": detail,
        "hard_cases": hard_cases,
        "unlabeled_policy": "未标注的按 keep 处理（保守方向），不影响纯度/误删统计",
    }


# ---------------------------------------------------------------------------
# B. SUMMARIZE
# ---------------------------------------------------------------------------
def run_summarize(args) -> dict:
    rt = task_runtime(TaskKind.SUMMARIZE)
    log(f"B. SUMMARIZE  max_output_tokens={rt.max_output_tokens}（来自 task_runtime）")
    day_idx = args.summarize_day      # B 段固定用第 1 天（与 A 段主口径同一天）
    day = DAYS[day_idx]
    date = DATES[day_idx].strftime("%Y-%m-%d")
    out: dict = {"day": day["name"], "dimensions": {}, "fact_hits": [], "hit_total": 0,
                 "fact_total": 0}

    for dim in args.summarize_dims:
        records = [r for r in day["records"] if r["dim"] == dim and r["kind"] != "numeric"]
        if not records:
            log(f"  [{dim}] 无记录，跳过")
            continue
        log(f"  [{dim}] {len(records)} 条源记录，渲染提示词…")
        sources = tuple(
            {"occurred_at": r["t"].strftime("%Y-%m-%d %H:%M"),
             "dimension": r["dim"], "text": r["text"]}
            for r in records
        )
        prompt = render_task_prompt(
            TaskKind.SUMMARIZE,
            params=PromptRenderParams(
                sources=sources,
                dimension=DIM_PROFILES.get(dim, DimensionProfile(dimension_key=dim)),
                granularity="day",
                window_start=date, window_end=date,
            ),
        )
        log(f"  [{dim}] 提示词 {len(prompt)} 字符，调用模型…")
        res = call_model(
            [{"role": "system", "content": prompt},
             {"role": "user", "content": "请按上面的契约输出这段总结正文。"}],
            rt.max_output_tokens, f"summarize-{dim}", TaskKind.SUMMARIZE,
        )
        block: dict = {
            "dim": dim, "n_sources": len(records), "prompt_chars": len(prompt),
            "model": res.get("model"), "max_tokens": res.get("max_tokens"),
            "rounds": res.get("rounds"), "elapsed_s": res.get("elapsed_s"),
            "ok": res["ok"],
        }
        if not res["ok"]:
            block["error"] = res.get("last_error")
            out["dimensions"][dim] = block
            log(f"  [{dim}] 调用失败：{res.get('last_error')}")
            save_result({"summarize": out})
            continue

        text = res["text"]
        block.update({"summary": text, "summary_chars": len(text),
                      "est_output_tokens": round(len(text) / 1.6)})

        dim_ids = {r["id"] for r in records}
        hits = []
        for label, ids in day["checks"]:
            if not (set(ids) & dim_ids):
                continue           # 这条事实不属于本维度，不参与本维度打分
            kws = day["keywords"].get(label, ())
            matched = [k for k in kws if k in text]
            hits.append({
                "dim": dim, "fact": label, "supporting_ids": list(ids),
                "keywords": list(kws), "matched_keywords": matched,
                "hit": bool(matched),
            })
        block["fact_hits"] = hits
        block["hit_count"] = sum(1 for h in hits if h["hit"])
        block["fact_count"] = len(hits)
        out["dimensions"][dim] = block
        out["fact_hits"].extend(hits)
        out["hit_total"] = sum(1 for h in out["fact_hits"] if h["hit"])
        out["fact_total"] = len(out["fact_hits"])
        log(f"  [{dim}] 总结 {len(text)} 字符，事实命中 {block['hit_count']}/{block['fact_count']}")
        save_result({"summarize": out})

    return out


# ---------------------------------------------------------------------------
# C. 契约与成本对照（不调模型）
# ---------------------------------------------------------------------------
def _old_static_blocks() -> tuple[int, int]:
    """从 grok_provider 源码里量出老提示词的常驻块（纪律 + 规则）。

    用 AST 取字面量而不是硬编码一个数字：老提示词改了，这个数会跟着变。
    返回 (块数, 字符数)。
    """
    src = (REPO / "src" / "aios_core" / "runtime" / "grok_provider.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    best: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.List) or len(node.elts) < 10:
            continue
        if not all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.elts):
            continue
        block = [e.value for e in node.elts]
        joined = "\n\n".join(block)
        if "CONSTITUTIONAL RULES" in joined and "DURABLE MEMORY DISCIPLINE" in joined:
            if len(joined) > len(best):
                best = [joined]
    text = best[0] if best else ""
    plus = ("You are the AIOS 3.0 symbiotic mind on an ultra-compact wearable band."
            "\n\nSTANDING CONSTRAINTS (invariant — these do not change with topic, "
            "session, model or context length):")
    return len(text.splitlines()), len(text) + len(plus)


def _old_capability_catalog() -> dict:
    """用真实注册的能力名（AST 抽取）走 grok 自己的渲染函数，量出老提示词的能力块。"""
    from aios_core.runtime.grok_provider import _render_capabilities

    src = (REPO / "src" / "aios_core" / "runtime" / "turn_runtime.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    names: list[str] = []
    desc_chars = 0
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "register"):
            continue
        for arg in node.args:
            if not (isinstance(arg, ast.Call) and getattr(arg.func, "id", "") == "CapabilitySpec"):
                continue
            for kw in arg.keywords:
                if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                    names.append(kw.value.value)
                elif kw.arg == "description" and isinstance(kw.value, ast.Constant):
                    desc_chars += len(kw.value.value)

    from aios_core.runtime.capabilities import CONTINUITY_WRITE_CAPABILITIES
    catalog = [
        {"name": n,
         "required_args": ({"statement": "string", "domain": "string", "confidence": "number"}
                           if n in CONTINUITY_WRITE_CAPABILITIES else {})}
        for n in names
    ]
    rendered = _render_capabilities(catalog)
    return {
        "capability_count": len(names),
        "catalog_chars": len(rendered),
        "description_chars_total": desc_chars,
        "note": "catalog 由 grok_provider._render_capabilities 用 53 个真实能力名实测渲染；"
                "能力描述（description）不进这个块，但老提示词的其他路径会带上它",
    }


def run_contract() -> dict:
    log("C. 契约与成本对照（只渲染，不调模型）")
    day, records = day_scope(0)
    sample_records = tuple(annotate_records(records[:20]))
    samples: dict[TaskKind, PromptRenderParams] = {
        TaskKind.ANNOTATE: PromptRenderParams(
            records=sample_records,
            dimensions=(DIM_PROFILES["dim:mic_audio"], DIM_PROFILES["dim:app_usage"]),
            window_start="2026-10-28", window_end="2026-10-28"),
        TaskKind.GATE: PromptRenderParams(records=sample_records[:8]),
        TaskKind.EXTRACT: PromptRenderParams(
            extra={"user_input": "我姓王，做柔性屏手环研发的。",
                   "assistant_reply": "记下了，王工。"}),
        TaskKind.SUMMARIZE: PromptRenderParams(
            sources=tuple({"occurred_at": "2026-10-28 07:12", "dimension": "dim:mic_audio",
                           "text": r["text"]} for r in records[:12]),
            dimension=DIM_PROFILES["dim:mic_audio"], granularity="day",
            window_start="2026-10-28", window_end="2026-10-28"),
        TaskKind.DIGEST: PromptRenderParams(
            sources=tuple({"occurred_at": "2026-10-28", "dimension": d,
                           "text": f"{d} 的当日总结示例"}
                          for d in ("dim:mic_audio", "dim:payment", "dim:calendar",
                                    "dim:note", "dim:external_chat", "dim:app_usage",
                                    "dim:camera_visual", "dim:order", "dim:heart_rate")),
            granularity="day"),
        TaskKind.DIALOGUE: PromptRenderParams(
            extra={"user_input": "今天有什么要紧事？",
                   "capability_catalog": ({"name": "search_world", "description": "检索世界对象",
                                           "input_schema": {"properties": {"query": "string"}}},)}),
    }

    per_task = {}
    for kind in TaskKind:
        rt = task_runtime(kind)
        prompt = render_task_prompt(kind, params=samples[kind])
        per_task[str(kind)] = {
            "prompt_chars": len(prompt),
            "est_tokens": round(len(prompt) / 1.6),
            "max_output_tokens": rt.max_output_tokens,
            "model_tier": str(rt.model_tier),
            "temperature": rt.temperature,
            "failure_policy": str(rt.failure_policy),
        }

    blocks, static_chars = _old_static_blocks()
    caps = _old_capability_catalog()
    old_total = static_chars + caps["catalog_chars"]

    new_annotate = per_task["annotate"]["prompt_chars"]
    new_summarize = per_task["summarize"]["prompt_chars"]
    comparison = {
        "old_static_prompt_chars": static_chars,
        "old_static_prompt_lines": blocks,
        "old_capability_catalog": caps,
        "old_total_chars_lower_bound": old_total,
        "old_total_est_tokens": round(old_total / 1.6),
        "old_total_chars_with_descriptions": old_total + caps["description_chars_total"],
        "annotate_shrink_ratio_with_descriptions": round(
            (old_total + caps["description_chars_total"]) / new_annotate, 1),
        "new_annotate_chars": new_annotate,
        "new_summarize_chars": new_summarize,
        "annotate_shrink_ratio": round(old_total / new_annotate, 1),
        "annotate_smaller_by_chars": old_total - new_annotate,
        "conclusion": (
            f"老对话提示词常驻 {old_total} 字符（{caps['capability_count']} 条能力 + 纪律 + 规则，"
            f"还不含随会话增长的 cockpit/近期对话/记忆卡），约 {round(old_total / 1.6)} token；"
            f"新的 ANNOTATE 提示词 {new_annotate} 字符（约 {round(new_annotate / 1.6)} token），"
            f"小到约 1/{round(old_total / new_annotate, 1)}；SUMMARIZE {new_summarize} 字符。"
            "且新提示词只带本任务契约，不带 53 条能力——模型没有多余的表面去自造字段名。"
        ),
        "caveat": "老提示词的实际长度随会话增长（cockpit/对话/记忆卡为动态段），这里是常驻部分的下界。",
    }
    log(f"  老常驻提示词 {old_total} 字符 / 新 ANNOTATE {new_annotate} 字符 / "
        f"新 SUMMARIZE {new_summarize} 字符")
    return {"per_task_prompt_chars": per_task, "comparison": comparison}


# ---------------------------------------------------------------------------
def main() -> None:
    global CURRENT_TASK
    ap = argparse.ArgumentParser(description="验证按契约分离的任务提示词（真实模型）")
    ap.add_argument("--task", choices=["annotate", "summarize", "contract", "all"],
                    default="all", help="分步跑，便于续跑")
    ap.add_argument("--days", default="0,1",
                    help="参与标注的 sim 天索引，默认 0,1（0=主口径，1=易错样本补充）")
    ap.add_argument("--summarize-dims", default="dim:mic_audio,dim:calendar",
                    help="B 段要总结的维度")
    ap.add_argument("--summarize-day", type=int, default=0, help="B 段用哪一天（默认 0）")
    ap.add_argument("--batch-size", type=int, default=20, help="ANNOTATE 每批条数（防 504）")
    args = ap.parse_args()
    args.days = [int(x) for x in args.days.split(",") if x.strip()]
    args.summarize_dims = [x.strip() for x in args.summarize_dims.split(",") if x.strip()]
    CURRENT_TASK = args.task

    result = load_result()
    log(f"=== prompt separation 验证 | task={args.task} | "
        f"endpoint={harness.PRIMARY_BASE_URL} | model={harness.PRIMARY_MODEL} ===")

    if args.task in ("annotate", "all"):
        t0 = time.time()
        merged = dict(result.get("annotate") or {})
        fresh = run_annotate(args)
        merged.setdefault("batches", [])
        merged["batches"] = fresh["batches"] + [
            b for b in merged["batches"]
            if (b["day"], b["batch"]) not in {(x["day"], x["batch"]) for x in fresh["batches"]}
        ]
        merged.setdefault("days", {}).update(fresh["days"])
        merged["elapsed_s"] = round(time.time() - t0, 1)
        result["annotate"] = merged
        save_result(result)
        log(f"A 段完成，用时 {merged['elapsed_s']}s")

    if args.task in ("summarize", "all"):
        t0 = time.time()
        out = run_summarize(args)
        out["elapsed_s"] = round(time.time() - t0, 1)
        result["summarize"] = out
        save_result(result)
        log(f"B 段完成，用时 {out['elapsed_s']}s")

    if args.task in ("contract", "all"):
        out = run_contract()
        result["contract_cost"] = out
        save_result(result)
        log("C 段完成")

    save_result(result)
    log(f"结果已写入 {RESULT_PATH}")
    log(f"调用统计：{dict(STATS)}")


if __name__ == "__main__":
    main()
