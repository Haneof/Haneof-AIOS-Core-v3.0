"""参数化单日编排（A/B 实测 v2）。

每个子 agent 跑 `python harness.py --day N --rounds R`，产出 dayN_result.json：
  - 机制臂：真实 RealityIngestService 入库（本地，无网络）
  - AI 臂：整批分类（带重试退避，应对 504），rounds 轮测稳定性
  - 认知回声：同一模型对同一天，仅输入集不同（机制全量 vs AI 保留集），数命中几条
  - 打分：对照预注册 ground truth

绝不把 LABELS 泄露给模型。每条调用失败后指数退避重试。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))   # repo/src
sys.path.insert(0, str(HERE))                       # 同目录 sim_realtime

os.environ.setdefault("AIOS_RPM_PACE", "0")  # 直连 urllib，不走 resilient limiter

from aios_core.runtime.resilient_handler import (  # noqa: E402
    PRIMARY_API_KEY, PRIMARY_BASE_URL, PRIMARY_MODEL,
)
from aios_core.contracts.enums import SourceClass  # noqa: E402
from aios_core.ingest import (  # noqa: E402
    MechanicalSeriesPolicy, RealityIngestService, RealityRecord, SourceAdapterSpec,
)
from aios_core.query.search import WorldSearchIndex  # noqa: E402
from aios_core.storage.sqlite_store import SQLiteWorldStore  # noqa: E402

from sim_realtime import DAYS, build_hr_samples  # noqa: E402


ADAPTERS: dict[str, SourceAdapterSpec] = {
    "dim:mic_audio": SourceAdapterSpec(adapter_id="wearable.mic.v1", source_kind="mic_transcript", dimension="dim:mic_audio", source_class=SourceClass.USER, default_modality="transcript"),
    "dim:payment": SourceAdapterSpec(adapter_id="phone.payment.v1", source_kind="payment", dimension="dim:payment", source_class=SourceClass.USER, default_modality="structured_record"),
    "dim:order": SourceAdapterSpec(adapter_id="phone.order.v1", source_kind="order", dimension="dim:order", source_class=SourceClass.USER, default_modality="structured_record"),
    "dim:calendar": SourceAdapterSpec(adapter_id="phone.calendar.v1", source_kind="calendar", dimension="dim:calendar", source_class=SourceClass.USER, default_modality="structured_record"),
    "dim:note": SourceAdapterSpec(adapter_id="phone.note.v1", source_kind="note", dimension="dim:note", source_class=SourceClass.USER, default_modality="text"),
    "dim:camera_visual": SourceAdapterSpec(adapter_id="glass.camera.v1", source_kind="camera", dimension="dim:camera_visual", source_class=SourceClass.SENSOR, default_modality="caption"),
    "dim:app_usage": SourceAdapterSpec(adapter_id="phone.appusage.v1", source_kind="app_event", dimension="dim:app_usage", source_class=SourceClass.USER, default_modality="notification"),
    "dim:external_chat": SourceAdapterSpec(adapter_id="phone.chat.v1", source_kind="chat", dimension="dim:external_chat", source_class=SourceClass.USER, default_modality="message"),
    "dim:heart_rate": SourceAdapterSpec(adapter_id="wearable.hr.v1", source_kind="heart_rate", dimension="dim:heart_rate", source_class=SourceClass.SENSOR, default_modality="numeric"),
}

AI_SYSTEM = """你是一个可穿戴 AI 系统的"基础数据清理"环节。

你拿到的是某一天从各个来源采集进来的原始记录。对每一条做判断：
- KEEP：保留。任何可能承载长期价值的事实——身份、承诺、截止期、健康信号、关系变化、目标、待办、重要金额、未来节点，或能佐证上述内容的观察。
- DROP：删除。纯粹的瞬时噪声——无意义发声、客套、重复且无新信息的内容、广告与系统推送、乱码误触、已完结的一次性琐事、环境背景噪声（如电视声、杂音）。

两条硬约束：
1. 一条记录里即使大部分是废话，只要夹带了任何重要事实，就必须 KEEP，不得整条丢弃。
2. 不要把玩笑、夸张表达误当成真实紧急事件（如"明天辞职""世界末日"）；也不要把客套的口头承诺当成真正承诺；不要把形似银行/系统的广告或钓鱼短信当成真实通知。

只输出一个 JSON 数组，不要任何解释文字，格式：
[{"id": "记录id", "decision": "keep|drop", "reason": "不超过15字"}]
"""

AI_SYSTEM_TAG = """你是一个可穿戴 AI 系统的"数据标注"环节——注意：你不是删除环节。

无论你怎么标，原始数据都会被原样保留在系统里，绝不会被删除。你的输出只用于给下游一个"降权/垃圾"标记，帮助总结时把噪声压低、但不抹掉任何事实。

这是一个"个人记忆系统"：目标是保留对本人有意义的内容，既包括硬事实，也包括软事实（关系、日常行为）。判断"有没有价值"以"对用户本人是否有意义"为准，而不是以"是否像新闻"为准。

对每一条记录打两个标签：
- decision：
  keep（满足任一即保留）：
    · 硬事实：身份、承诺、截止期、健康信号、关系变化、目标、待办、重要金额、未来节点；
    · 关系维系信号：他人发来的邀约、寒暄、持续互动（如"周末钓鱼去不去""喝咖啡去不去"）——即使没有承诺，也是社交节点，必须保留；
    · 自身常规活动/行为遥测：阅读、运动、作息、App 使用时长等当日行为（如"阅读App 32分钟"）——即使 routine，也是行为日志，必须保留；
    · 一条记录里夹带了上述任何内容，就必须 keep。
  drop（仅以下才删）：无意义发声、纯重复且无新信息、广告与系统推送、乱码误触、电视/环境背景噪声、已完结且与用户无关的一次性琐事。
- relevance：user（用户自己的对话/行为） / other（他人或群聊中与用户无关的内容） / media（电视/音视频里的虚构内容） / unknown（无法判断）。

两条硬约束：
1. 一条记录里即使大部分是废话，只要夹带了任何保留内容，decision 必须 keep。
2. 区分"玩笑夸张"与"真实社交"：明显的玩笑（"明天世界末日""明天就辞职"）才 drop；真实的社交邀约（去钓鱼吗/喝咖啡吗）即使无承诺也要 keep，它是关系信号，不得当噪声丢弃。形似银行/系统的广告或钓鱼短信仍按 drop 处理。

只输出一个 JSON 数组，不要任何解释文字，格式：
[{"id": "记录id", "decision": "keep|drop", "relevance": "user|other|media|unknown", "reason": "不超过15字"}]
"""

ECHO_PROMPT = """下面是某位用户一天里进入系统的记录。

请回答：今天发生了哪些值得记住的事？只列事实，不要编造，每条一行，不超过 15 字。

记录：
{records}
"""

# ----------------------------- 二次审核门禁（第二遍 AI） -----------------------------
SECOND_PASS_SYSTEM = """你是一个可穿戴 AI 记忆系统的"删除审核门禁"（第二遍 AI）。

第一遍 AI 已经给每条记录打了 keep/drop。下面是你收到的【待删除候选清单】——这些是第一遍标为 drop（建议删除）的记录。它们即将被永久删除、不可恢复。

你的工作：逐条"二次认知"，独立判断这条到底是不是真垃圾、该不该删。
- confirm（确认删除）：确认它是无价值的噪声——广告、乱码、纯填充词/客套招呼、系统推送、电视/环境背景声、已完结且与用户无关的一次性琐事，且整条不含任何对用户有意义的内容。
- cancel（取消删除、保留）：只要它含有任何对用户有意义的内容——硬事实（身份、承诺、截止期、健康信号、关系变化、目标、待办、金额、未来节点）或软事实（他人邀约/寒暄、自身日常行为/时长、任何值得记住的信息）。

你比第一遍更严格、更保守：宁可漏删垃圾，绝不错删有用内容。每条都给理由（不超过20字）。

只输出一个 JSON 数组，不要任何解释文字，格式：
[{"id": "记录id", "action": "confirm|cancel", "reason": "不超过20字"}]
"""


# ----------------------------- 模型调用（带重试退避） -----------------------------
def _call_model(messages: list, max_tokens: int, tag: str) -> str:
    body = {"model": PRIMARY_MODEL, "messages": messages,
            "temperature": 0.2, "max_tokens": max_tokens}
    req = urllib.request.Request(
        PRIMARY_BASE_URL + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {PRIMARY_API_KEY}",
                 "Content-Type": "application/json"},
    )
    backoff = [8, 16, 32, 64, 128, 180]
    for attempt in range(len(backoff) + 1):
        try:
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=900) as resp:
                payload = json.load(resp)
            choice = payload["choices"][0]
            finish = choice.get("finish_reason")
            text = choice["message"].get("content") or ""
            if not text.strip():
                raise RuntimeError(f"空正文 finish_reason={finish}")
            if finish == "length":
                raise RuntimeError(f"输出被截断 finish_reason=length")
            return text
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, KeyError, ValueError) as exc:
            wait = backoff[attempt] if attempt < len(backoff) else 240
            print(f"  [{tag}] 第 {attempt+1} 次失败：{type(exc).__name__} {str(exc)[:90]} → {wait}s 后重试", flush=True)
            if attempt == len(backoff):
                raise
            time.sleep(wait)
    raise RuntimeError("unreachable")


def _extract_json(text: str):
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1).strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"响应中无 JSON 数组：{text[:200]}")
    return json.loads(text[start:end + 1])


# ----------------------------- 机制臂 -----------------------------
def run_mechanical(day_idx: int) -> dict:
    day = DAYS[day_idx]
    store = SQLiteWorldStore(HERE / f"_tmp_mech_{day_idx}.db")
    index = WorldSearchIndex(HERE / f"_tmp_mech_{day_idx}.db", store=store)
    index.rebuild()
    service = RealityIngestService(store=store, index=index)
    kept, dropped, failures = [], [], []
    for rec in day["records"]:
        if rec["kind"] == "numeric":
            continue
        spec = ADAPTERS[rec["dim"]]
        try:
            service.ingest_record(spec, RealityRecord(
                external_record_id=rec["id"], occurred_at=rec["t"], received_at=rec["t"],
                value=rec["text"], source_locator=f"adapter://{spec.adapter_id}/{rec['id']}"))
            kept.append(rec["id"])
        except Exception as exc:  # noqa: BLE001
            dropped.append(rec["id"]); failures.append((rec["id"], f"{type(exc).__name__}: {exc}"))
    numeric_note = ""
    try:
        receipt = service.ingest_numeric_series(
            ADAPTERS["dim:heart_rate"], series_id=f"hr-{day_idx}",
            samples=build_hr_samples(day_idx),
            policy=MechanicalSeriesPolicy(tolerance=3.0, change_threshold=15.0, max_gap_seconds=300.0),
            unit="bpm", received_at=day["records"][0]["t"])
        numeric_note = f"1000采样 → {len(receipt.segment_observation_ids)}段 + {len(receipt.change_observation_ids)}变化事件"
        kept.append("hr")
    except Exception as exc:  # noqa: BLE001
        dropped.append("hr"); failures.append(("hr", f"{type(exc).__name__}: {exc}"))
    return {"kept": kept, "dropped": dropped, "failures": failures, "numeric_note": numeric_note}


# ----------------------------- AI 臂 -----------------------------
def _records_block(day_idx: int) -> str:
    day = DAYS[day_idx]
    lines = []
    for rec in day["records"]:
        if rec["kind"] == "numeric":
            lines.append(f"- id={rec['id']} | 来源={rec['dim']} | 数值流：{rec['text']}（按保留处理，交由机制压缩）")
            continue
        lines.append(f"- id={rec['id']} | 来源={rec['dim']} | 时间={rec['t'].strftime('%H:%M')} | 内容：{rec['text']}")
    return "\n".join(lines)


def run_ai(day_idx: int, rounds: int, mode: str = "ab") -> list[dict]:
    day = DAYS[day_idx]
    block = _records_block(day_idx)
    system = AI_SYSTEM_TAG if mode == "tag" else AI_SYSTEM
    prompt = f"下面是 {day['name']} 一天采集到的 {len(day['records'])} 条原始记录。\n\n{block}\n\n请逐条判断并输出 JSON 数组。"
    results = []
    for i in range(1, rounds + 1):
        t0 = time.time()
        try:
            text = _call_model([{"role": "system", "content": system},
                                {"role": "user", "content": prompt}], 4000, f"AI分类 D{day_idx+1} R{i}")
            decisions = _extract_json(text)
            results.append({"run": i, "elapsed": round(time.time() - t0, 1),
                            "decisions": decisions, "n": len(decisions)})
            print(f"  AI分类 D{day_idx+1} 第{i}轮：{results[-1]['elapsed']}s，{len(decisions)} 条", flush=True)
        except Exception as exc:  # noqa: BLE001
            results.append({"run": i, "error": f"{type(exc).__name__}: {exc}"})
            print(f"  AI分类 D{day_idx+1} 第{i}轮最终失败", flush=True)
        time.sleep(2)
    return results


# ----------------------------- 确定性护栏（根因 3/4 修复） -----------------------------
def apply_guardrails(day_idx: int, decisions: list[dict]) -> tuple[list[dict], list[str]]:
    """模型之外的硬安全网：白名单类记录即使模型标 drop 也强制 keep。

    覆盖 v3 暴露的误删 pattern：
      - 关系维系（外部聊天里的邀约/寒暄）→ 社交节点
      - 自身行为遥测（app_usage 的阅读/运动/时长）→ 行为日志
    返回 (修正后的 decisions, 被护栏强制保留的 id 列表)。
    """
    day = DAYS[day_idx]
    by_id = {r["id"]: r for r in day["records"]}
    overrides = []
    for d in decisions:
        rid = str(d["id"])
        rec = by_id.get(rid, {})
        dim = rec.get("dim", "")
        text = rec.get("text", "") or ""
        forced = False
        if dim == "dim:external_chat" and re.search(r"去不去|去吗|要不要|约|一起|有空|周末|喝|钓|吃饭", text):
            forced = True
        elif dim == "dim:app_usage" and re.search(r"使用|分钟|阅读|运动|时长|App", text):
            forced = True
        if forced and str(d.get("decision", "")).lower() == "drop":
            d["decision"] = "keep"
            d["reason"] = "(护栏)白名单强制保留"
            overrides.append(rid)
    return decisions, overrides


# ----------------------------- 认知回声 -----------------------------
def _echo_block(day_idx: int, kept_ids: list[str]) -> str:
    day = DAYS[day_idx]
    by_id = {r["id"]: r for r in day["records"]}
    lines = []
    for rid in kept_ids:
        rec = by_id.get(rid)
        if rec is None:
            lines.append(f"- [心率] 全天 1000 点采样（含真实飙升段，已由机制压缩为段+变化事件）")
            continue
        if rec["kind"] == "numeric":
            lines.append(f"- [心率] 全天 1000 点采样（含真实飙升段，已由机制压缩为段+变化事件）")
            continue
        lines.append(f"- [{rec['dim']} {rec['t'].strftime('%H:%M')}] {rec['text']}")
    return "\n".join(lines)


def run_echo(day_idx: int, kept_ids: list[str], tag: str) -> dict:
    day = DAYS[day_idx]
    block = _echo_block(day_idx, kept_ids)
    t0 = time.time()
    text = _call_model([{"role": "user", "content": ECHO_PROMPT.format(records=block)}],
                       6000, f"回声 {tag}")
    hits = {}
    for label, _ in day["checks"]:
        kws = day["keywords"].get(label, ())
        hits[label] = any(k in text for k in kws)
    return {"tag": tag, "input_count": len(kept_ids), "input_chars": len(block),
            "elapsed": round(time.time() - t0, 1), "summary": text,
            "hits": hits, "hit_count": sum(1 for v in hits.values() if v)}


# ----------------------------- 打分 -----------------------------
def score(day_idx: int, ai_runs: list[dict]) -> dict:
    day = DAYS[day_idx]
    labels = day["labels"]
    drop_ids = {rid for rid, (lab, _) in labels.items() if lab == "DROP"}
    keep_ids = {rid for rid, (lab, _) in labels.items() if lab == "KEEP"}
    valid = [r for r in ai_runs if "error" not in r]
    if not valid:
        return {"error": "AI 臂全失败，无法打分"}
    d0 = {str(d["id"]): str(d.get("decision", "")).lower()
          for d in valid[0]["decisions"]}
    # 噪声清理率（在应删集合里真的删了的比例）
    correctly_dropped = sum(1 for rid in drop_ids if d0.get(rid) == "drop")
    noise_removal = round(correctly_dropped / len(drop_ids), 3) if drop_ids else 1.0
    # 误删重要事实
    false_dropped = [rid for rid in keep_ids if d0.get(rid) == "drop"]
    # 边界项漂移：跨轮判断不一致的重要项
    drift = []
    if len(valid) > 1:
        for rid in labels:
            decs = [str(d.get("decision", "")).lower()
                    for r in valid for d in r["decisions"] if str(d["id"]) == rid]
            if decs and len(set(decs)) > 1:
                drift.append(rid)
    return {"noise_removal": noise_removal, "n_drop": len(drop_ids),
            "correctly_dropped": correctly_dropped, "false_dropped": false_dropped,
            "n_keep": len(keep_ids), "round_agreement_drift": drift}


# ----------------------------- 打分（tagging-only 口径） -----------------------------
def score_tag(day_idx: int, ai_runs: list[dict]) -> dict:
    """AI 只标注不删除：测标注准度，并硬校验删除数=0（机制全量存真）。"""
    day = DAYS[day_idx]
    labels = day["labels"]
    drop_ids = {rid for rid, (lab, _) in labels.items() if lab == "DROP"}
    keep_ids = {rid for rid, (lab, _) in labels.items() if lab == "KEEP"}
    valid = [r for r in ai_runs if "error" not in r]
    if not valid:
        return {"error": "AI 臂全失败，无法打分"}
    d0 = {str(d["id"]): d for d in valid[0]["decisions"]}
    ai_drop = {rid for rid, d in d0.items() if str(d.get("decision", "")).lower() == "drop"}
    correctly = ai_drop & drop_ids
    # 垃圾类 precision / recall
    precision = round(len(correctly) / len(ai_drop), 3) if ai_drop else 1.0
    recall = round(len(correctly) / len(drop_ids), 3) if drop_ids else 1.0
    # 标签误删：把真事标成垃圾（危险，下游若降权会丢认知）
    label_false_drop = sorted(keep_ids & ai_drop)
    # 漏标：真垃圾没标出来（无害，只是留在原处）
    missed_garbage = sorted(drop_ids - ai_drop)
    # 跨轮漂移（针对重要项）
    drift = []
    if len(valid) > 1:
        for rid in labels:
            decs = [str(x.get("decision", "")).lower()
                    for r in valid for x in r["decisions"] if str(x["id"]) == rid]
            if decs and len(set(decs)) > 1:
                drift.append(rid)
    # 相关性分布（描述性，无 ground truth）
    rel_dist = {}
    for rid, d in d0.items():
        rel = str(d.get("relevance", "unknown")).lower()
        rel_dist[rel] = rel_dist.get(rel, 0) + 1
    # 认知标签威胁：7 条结论里，哪些的支撑记录被误标成垃圾
    cog_threat = []
    for label, cids in day["checks"]:
        if any(c in label_false_drop for c in cids):
            cog_threat.append(label)
    # —— 人工裁定表：AI 计划删除的每条 + 理由 + ground truth 判决 ——
    by_id = {r["id"]: r for r in day["records"]}
    planned_drops = []
    for rid in sorted(ai_drop):
        rec = by_id.get(rid, {})
        planned_drops.append({
            "id": rid,
            "source": rec.get("dim", "?"),
            "content": (rec.get("text", "") or "")[:60],
            "ai_reason": d0[rid].get("reason", ""),
            "relevance": d0[rid].get("relevance", ""),
            "gt": labels.get(rid, ("?", ""))[0],   # KEEP / DROP
            "verdict": "删得对" if rid in drop_ids else "误删(该留)",
        })
    kept_but_garbage = []
    for rid in missed_garbage:
        rec = by_id.get(rid, {})
        kept_but_garbage.append({
            "id": rid, "source": rec.get("dim", "?"),
            "content": (rec.get("text", "") or "")[:60],
            "ai_reason": d0[rid].get("reason", ""),
            "verdict": "漏标(仍保留，无害)",
        })
    return {"drop_class_precision": precision, "drop_class_recall": recall,
            "n_true_garbage": len(drop_ids), "n_ai_garbage": len(ai_drop),
            "correctly_tagged": len(correctly), "label_false_drop": label_false_drop,
            "missed_garbage": missed_garbage, "round_agreement_drift": drift,
            "relevance_dist": rel_dist, "cognition_label_threat": cog_threat,
            "deletion_count": 0,
            "planned_drops": planned_drops, "kept_but_garbage": kept_but_garbage}


# ----------------------------- 二次审核门禁（运行 + 打分 + 对抗） -----------------------------
def _audit_block(day_idx: int, candidates: list[dict]) -> str:
    lines = []
    for c in candidates:
        lines.append(f"- id={c['id']} | 来源={c['source']} | 第一遍标记=drop | 第一遍理由={c.get('first_reason','')} | 内容：{c['content']}")
    return "\n".join(lines)


def run_second_pass(day_idx: int, candidates: list[dict]) -> dict:
    """对第一遍的 drop 候选做二次认知审核门禁。

    candidates: [{id, source, content, first_reason}]
    返回 {decisions:[{id, action(confirm|cancel), reason}], elapsed, error?}
    """
    if not candidates:
        return {"decisions": [], "elapsed": 0.0, "note": "无候选（第一遍未标任何 drop）"}
    block = _audit_block(day_idx, candidates)
    prompt = (f"下面是待删除候选清单（共 {len(candidates)} 条），请逐条二次审核并输出 JSON 数组。\n\n{block}\n")
    t0 = time.time()
    try:
        text = _call_model([{"role": "system", "content": SECOND_PASS_SYSTEM},
                            {"role": "user", "content": prompt}], 4000, f"二次审核 D{day_idx+1}")
        decisions = _extract_json(text)
        return {"decisions": decisions, "elapsed": round(time.time() - t0, 1)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}", "elapsed": round(time.time() - t0, 1)}


def score_second_pass(day_idx: int, audit: dict, first_drop_ids: set) -> dict:
    """验收二次审核：删除纯度（最关键安全指标）+ 误删数 + 漏删（无害）。"""
    day = DAYS[day_idx]
    labels = day["labels"]
    drop_ids = {rid for rid, (lab, _) in labels.items() if lab == "DROP"}
    keep_ids = {rid for rid, (lab, _) in labels.items() if lab == "KEEP"}
    if "error" in audit or not audit.get("decisions"):
        return {"error": "二次审核失败", "details": audit.get("error")}
    by_id = {str(d["id"]): d for d in audit["decisions"]}
    confirmed = {rid for rid, d in by_id.items() if str(d.get("action", "")).lower() == "confirm"}
    canceled = {rid for rid, d in by_id.items() if str(d.get("action", "")).lower() == "cancel"}
    confirmed_true_garbage = confirmed & drop_ids
    false_deletion = confirmed & keep_ids            # 确认删了真事 → 危险
    deletion_precision = round(len(confirmed_true_garbage) / len(confirmed), 3) if confirmed else 1.0
    canceled_true_garbage = canceled & drop_ids     # 无害，只是留垃圾
    # 候选集覆盖率（第一遍 drop 里被第二遍覆盖到的）
    covered = set(by_id) & first_drop_ids
    deletion_recall = round(len(confirmed_true_garbage) / len(covered & drop_ids), 3) if (covered & drop_ids) else 1.0
    rec_by_id = {r["id"]: r for r in day["records"]}
    table = []
    for rid in sorted(by_id):
        gt = labels.get(rid, ("?", ""))[0]
        act = by_id[rid].get("action", "")
        rec = rec_by_id.get(rid, {})
        if act == "confirm" and gt == "DROP":
            verdict = "删得对"
        elif act == "confirm" and gt == "KEEP":
            verdict = "误删(该留)"          # 安全门禁失败
        elif act == "cancel" and gt == "KEEP":
            verdict = "保留正确"
        else:
            verdict = "漏删(仍留，无害)"
        table.append({"id": rid, "source": rec.get("dim", "?"),
                      "content": (rec.get("text", "") or "")[:60],
                      "action": act, "gt": gt, "verdict": verdict,
                      "reason": by_id[rid].get("reason", "")})
    return {"deletion_precision": deletion_precision, "false_deletion": sorted(false_deletion),
            "n_candidates": len(by_id), "n_confirmed": len(confirmed), "n_canceled": len(canceled),
            "confirmed_true_garbage": sorted(confirmed_true_garbage),
            "canceled_true_garbage": sorted(canceled_true_garbage),
            "deletion_recall": deletion_recall, "deletion_table": table}


def run_adversarial(day_idx: int) -> dict:
    """对抗注入：把若干'真事'混入待删除候选，验证门禁不会错删。

    模拟"第一遍万一误标了真事"的极端情形，看第二遍能不能把它们救回来（cancel）。
    """
    day = DAYS[day_idx]
    rec_by_id = {r["id"]: r for r in day["records"]}
    keep_ids = [rid for rid, (lab, _) in day["labels"].items()
                if lab == "KEEP" and rec_by_id[rid].get("kind") != "numeric"]
    injected = keep_ids[: min(8, len(keep_ids))]
    candidates = [{"id": rid, "source": rec_by_id[rid].get("dim", ""),
                   "content": (rec_by_id[rid].get("text", "") or "")[:60],
                   "first_reason": "(对抗注入)假设第一遍误标为drop"} for rid in injected]
    audit = run_second_pass(day_idx, candidates)
    if "error" in audit:
        return {"error": audit["error"], "injected": injected}
    by_a = {str(d["id"]): d for d in audit["decisions"]}
    saved = [rid for rid in injected if str(by_a.get(rid, {}).get("action", "")).lower() == "cancel"]
    return {"injected_keep": injected, "saved_by_gate": saved,
            "save_rate": round(len(saved) / len(injected), 3) if injected else 1.0,
            "audit": audit}


# ----------------------------- 实操演示：二次门禁 confirm → 真实 retract -----------------------------
def run_execute(day_idx: int, audit: dict) -> list[dict]:
    """对第二遍门禁 confirm 的候选，真正执行认知层 retract（演示端到端闭环）。

    独立临时 store：把每条 confirm 候选重新入库（作证据）→ commit 一条 Claim →
    调 GarbageRetractionService.retract → 断言 Claim 变 retracted。证明「confirm
    接真实删除接口」在流水线里真实生效，而非只打标签。
    """
    from datetime import datetime, timezone
    from aios_core.cleaning import GarbageRetractionService
    from aios_core.contracts.refs import ObjectRef
    from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService
    day = DAYS[day_idx]
    rec_by_id = {r["id"]: r for r in day["records"]}
    if "error" in audit or not audit.get("decisions"):
        return []
    db = HERE / f"_tmp_exec_{day_idx}.db"
    if db.exists():
        db.unlink()
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    svc = RealityIngestService(store=store, index=index, subject_id="user_1")
    wb = CognitionWritebackService(store=store, index=index, subject_id="user_1")
    rs = GarbageRetractionService(store=store, index=index, subject_id="user_1")
    out = []
    for d in audit["decisions"]:
        if str(d.get("action", "")).lower() != "confirm":
            continue
        rid = str(d["id"])
        rec = rec_by_id.get(rid, {})
        if rec.get("kind") == "numeric":
            continue
        spec = ADAPTERS.get(rec.get("dim"))
        if spec is None:
            continue
        rrec = RealityRecord(
            external_record_id=rid, occurred_at=rec["t"], received_at=rec["t"],
            value=rec["text"], source_locator=f"adapter://{spec.adapter_id}/{rid}",
        )
        receipt = svc.ingest_record(spec, rrec)
        rec_ref = ObjectRef(object_id=receipt.observation_id, revision=1)
        claim = wb.commit_claim(
            ClaimWriteRequest(
                content=f"曾抽取认知：{rec['text'][:20]}", evidence_refs=(rec_ref,),
                confidence=1.0, dimension=rec.get("dim", "dim:note"),
            ), learned_at=rec["t"],
        )
        claim_ref = ObjectRef(object_id=claim.claim_id, revision=1)
        rcp = rs.retract(
            claim_ref=claim_ref, record_ref=rec_ref,
            reason=d.get("reason", "二次门禁确认删除"), changed_at=datetime.now(timezone.utc),
        )
        status = store.get_payload(claim.claim_id)["status"]
        assert status == "retracted", status
        out.append({"id": rid, "claim": claim.claim_id,
                    "new_revision": rcp.new_revision, "status": status})
    return out


# ----------------------------- 主流程 -----------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int, required=True, help="0/1/2")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--mode", choices=["ab", "tag", "audit"], default="ab",
                    help="ab=删/留口径(旧)  tag=只标注不删除(新)  audit=第一遍标注+二次审核门禁")
    ap.add_argument("--execute", action="store_true",
                    help="audit 模式下，对二次门禁 confirm 的候选真实执行认知层 retract（演示）")
    args = ap.parse_args()
    di = args.day
    day = DAYS[di]
    print(f"=== {day['name']} (mode={args.mode}) ===", flush=True)

    mech = run_mechanical(di)
    print(f"  机制臂：保留 {len(mech['kept'])} 条 / 丢弃 {mech['dropped']} / 数值流 {mech['numeric_note']}", flush=True)

    ai_runs = run_ai(di, args.rounds, args.mode if args.mode in ("ab", "tag") else "tag")
    guardrail_overrides = []
    if args.mode in ("tag", "audit"):
        for run in ai_runs:
            if "error" not in run:
                run["decisions"], ov = apply_guardrails(di, run["decisions"])
                guardrail_overrides.extend(ov)
    sc = score_tag(di, ai_runs) if args.mode in ("tag", "audit") else score(di, ai_runs)
    print(f"  第一遍打分：{sc}", flush=True)
    if guardrail_overrides:
        print(f"  护栏强制保留：{sorted(set(guardrail_overrides))}", flush=True)

    # 回声（仅 ab 模式有意义：tag/audit 模式机制全量=认知输入，回声恒等）
    echo_mech = echo_ai = None
    if args.mode == "ab":
        ai_kept = [str(d["id"]) for d in ai_runs[0]["decisions"]
                   if str(d.get("decision", "")).lower() == "keep"] if "error" not in ai_runs[0] else []
        echo_mech = run_echo(di, mech["kept"], "机制清洗后")
        print(f"  回声-机制：{echo_mech['hit_count']}/{len(day['checks'])} 输入 {echo_mech['input_count']} 条", flush=True)
        time.sleep(2)
        if ai_kept:
            echo_ai = run_echo(di, ai_kept, "AI清洗后")
            print(f"  回声-AI：{echo_ai['hit_count']}/{len(day['checks'])} 输入 {echo_ai['input_count']} 条", flush=True)
    else:
        echo_mech = run_echo(di, mech["kept"], "全量(只标注不删除)")
        print(f"  回声-全量：{echo_mech['hit_count']}/{len(day['checks'])} 输入 {echo_mech['input_count']} 条", flush=True)

    # —— 二次审核门禁（audit 模式）——
    audit = adversarial = sc2 = None
    if args.mode == "audit":
        # 取第一遍（含护栏后）的 drop 候选
        first_drop = []
        if "error" not in ai_runs[0]:
            rec_by_id = {r["id"]: r for r in day["records"]}
            for d in ai_runs[0]["decisions"]:
                if str(d.get("decision", "")).lower() == "drop":
                    rid = str(d["id"])
                    rec = rec_by_id.get(rid, {})
                    first_drop.append({"id": rid, "source": rec.get("dim", "?"),
                                       "content": (rec.get("text", "") or "")[:60],
                                       "first_reason": d.get("reason", "")})
        print(f"  待删除候选（第一遍 drop）：{len(first_drop)} 条，进入二次审核门禁…", flush=True)
        audit = run_second_pass(di, first_drop)
        first_drop_ids = {c["id"] for c in first_drop}
        sc2 = score_second_pass(di, audit, first_drop_ids)
        print(f"  二次审核打分：{sc2}", flush=True)
        # 对抗注入：把真事混入候选，验证门禁不会错删
        print(f"  对抗注入测试：把真事混入候选，验证门禁…", flush=True)
        adversarial = run_adversarial(di)
        print(f"  对抗 save_rate={adversarial.get('save_rate')} saved={adversarial.get('saved_by_gate')}", flush=True)
        # 实操演示：对 confirm 候选真实 retract（若 --execute）
        executed = None
        if args.execute and audit and "error" not in audit:
            print(f"  实操演示：对 confirm 候选真实 retract…", flush=True)
            executed = run_execute(di, audit)
            print(f"  真实删除 {len(executed)} 条（Claim 状态均 retracted）", flush=True)

    result = {"day": day["name"], "mode": args.mode, "mechanical": mech, "ai_runs": ai_runs,
              "guardrail_overrides": sorted(set(guardrail_overrides)),
              "score": sc, "echo_mechanical": echo_mech, "echo_ai": echo_ai,
              "second_pass_audit": audit, "second_pass_score": sc2,
              "adversarial": adversarial, "executed_deletions": executed}
    out = HERE / f"day{di + 1}_result_{args.mode}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 {out.name}", flush=True)


if __name__ == "__main__":
    main()
