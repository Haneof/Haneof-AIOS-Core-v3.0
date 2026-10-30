"""总结机制端到端验证（AIOS Core v3.0）。

两种模式：
  mechanism  —— 本地、stub handler（不联网）：验证"全维度覆盖 + 自动跑 + 幂等 +
               多尺度自底向上 + 清洗协同缺口"。这是总结机制的确定性机械部分。
  echo      —— 真实 NVIDIA 模型：对单天每个维度产出 DAY 总结，并对承载 7 条
               ground-truth 事实的 dim:mic_audio 总结做关键词回声（内容保真）。

数据复用 experiments/cleaning_ab 的 sim_realtime（3 天 × 9 维度 + 心率流），
模型调用复用 harness._call_model（与数据清洗 A/B 实测同一端点，带 504 重试）。

判定口径（你定的）：
  - 全维度：世界里出现过的每个 dimension 都应有对应 DAY 总结。
  - 多尺度：DAY/WEEK/MONTH 窗口边界稳定(UTC)；WEEK 的源必须是 DAY 总结(自底向上)，
    不能直接吃原始 observation。
  - 幂等：同一窗口重跑应 skipped_unchanged、0 新 commit。
  - 内容保真：mic_audio DAY 总结应命中 7 条 ground-truth 事实的关键词。
  - 清洗协同：summary 源是否含噪声(无 relevance 过滤)——这是已知候选缺口，如实记录。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLEANING_AB = HERE.parent / "cleaning_ab"
REPO = HERE.parent.parent
for p in (REPO / "src", CLEANING_AB):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import sim_realtime  # noqa: E402  (来自 cleaning_ab)
import harness  # noqa: E402  (来自 cleaning_ab，含 _call_model / ADAPTERS)

from aios_core.ingest.reality import (  # noqa: E402
    MechanicalSeriesPolicy,
    RealityIngestService,
    RealityRecord,
)
from aios_core.query.search import WorldSearchIndex  # noqa: E402
from aios_core.storage.sqlite_store import SQLiteWorldStore  # noqa: E402
from aios_core.summaries import (  # noqa: E402
    DIGEST_DIMENSION,
    MultiScaleSummaryScheduler,
    SummaryScale,
    window_bounds,
)
from aios_core.summaries.dimension_summary import _SUMMARY_SCALE_RANK  # noqa: E402

UTC = timezone.utc
SUBJECT = "user_1"
DATES = sim_realtime.DATES  # 2026-10-28/29/30

# 高基数维度（heart_rate 每天 288 段 + 变化事件，3 天约 864 源 > 默认 500 上限）：
# 按维度放宽 cap，WEEK/MONTH 聚合才不至于 fail-closed。
DIMENSION_SOURCE_CAPS = {"dim:heart_rate": 1200}


def cleaning_admission(object_id: str, object_type: str, payload: dict) -> bool:
    """清洗协同：把数据清洗管线产出的标签接到总结源准入上。

    provenance 里带 cleaning_decision=DROP 的记录（噪声/无信息/客套）不允许
    进入任何总结的源集合；其余（KEEP 或未标注）放行。
    """
    provenance = (payload.get("metadata") or {}).get("provenance") or {}
    return provenance.get("cleaning_decision") != "DROP"


# --------------------------------------------------------------------------
# 入库
# --------------------------------------------------------------------------
def ingest_day(store, index, day_idx: int) -> dict:
    svc = RealityIngestService(store=store, index=index, subject_id=SUBJECT)
    day = sim_realtime.DAYS[day_idx]
    kept, dropped, failures = [], [], []
    for rec in day["records"]:
        if rec["kind"] == "numeric":
            continue
        spec = harness.ADAPTERS[rec["dim"]]
        label = day["labels"].get(rec["id"])
        provenance = (
            {"cleaning_decision": label[0], "cleaning_relevance": label[1]}
            if label else {}
        )
        try:
            svc.ingest_record(
                spec,
                RealityRecord(
                    # 跨天唯一：sim 的 m01/p01 每天重复，直接复用会触发
                    # "同 id 不同事实" 冲突拒绝，故加天数后缀。
                    external_record_id=f"{rec['id']}@d{day_idx}",
                    occurred_at=rec["t"],
                    received_at=rec["t"],
                    value=rec["text"],
                    source_locator=f"adapter://{spec.adapter_id}/{rec['id']}@d{day_idx}",
                    provenance=provenance,
                ),
            )
            kept.append(rec["id"])
        except Exception as exc:  # noqa: BLE001
            dropped.append(rec["id"])
            failures.append((rec["id"], f"{type(exc).__name__}: {exc}"))
    try:
        receipt = svc.ingest_numeric_series(
            harness.ADAPTERS["dim:heart_rate"],
            series_id=f"hr-{day_idx}",
            samples=sim_realtime.build_hr_samples(day_idx),
            policy=MechanicalSeriesPolicy(tolerance=3.0, change_threshold=15.0, max_gap_seconds=300.0),
            unit="bpm",
            received_at=day["records"][0]["t"],
        )
        numeric_note = (
            f"1000采样 → {len(receipt.segment_observation_ids)}段 "
            f"+ {len(receipt.change_observation_ids)}变化事件"
        )
        kept.append("hr")
    except Exception as exc:  # noqa: BLE001
        dropped.append("hr")
        failures.append(("hr", f"{type(exc).__name__}: {exc}"))
        numeric_note = "FAIL"
    return {"kept": kept, "dropped": dropped, "failures": failures, "numeric_note": numeric_note}


def fresh_store(tag: str):
    db = HERE / f"_tmp_{tag}.db"
    if db.exists():
        db.unlink()
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def summary_handler_real_model(prepared) -> str:
    """真实模型总结 handler：把 DimensionSummaryInput 格式化成提示词调 NVIDIA。"""
    lines = []
    for i, s in enumerate(prepared.sources):
        when = s.occurred_at.strftime("%H:%M") if s.occurred_at else "??:??"
        lines.append(f"- [{when}] ({s.object_type}) {s.text}")
    if prepared.dimension == DIGEST_DIMENSION:
        # 今日总览：源是各维度 DAY 总结，做跨维度的一天全貌。
        # 提示词用"维度标签 + 总结"的紧凑格式（探针实测该格式 + 6000 tokens
        # 稳定产出；带时间戳的长格式会把思考拉长到撞网关 504）。
        dlines = [
            f"- ({s.metadata.get('dimension', '?')}) {s.text}"
            for s in prepared.sources
        ]
        body = (
            f"下面是用户 {prepared.window_start:%Y-%m-%d} 一天里 "
            f"{len(prepared.sources)} 个维度的 DAY 总结。请写一段中文「今日总览」，"
            "把这天跨维度发生过什么整合成一天全貌，保留关键细节，不编造，"
            f"直接输出正文不超过 300 字。\n\n" + "\n".join(dlines)
        )
        # digest 源是 9 个维度的整段总结，跨维整合的推理开销大：实测 2500/4500
        # 会被思考耗尽（finish_reason=length 空正文），6000 会撞网关 504；
        # 紧凑提示词下思考收敛在 ~3400 tokens，4000 是甜点（实测 274s 成功）。
        return harness._call_model(
            [{"role": "user", "content": body}], 4000, "今日总览"
        )
    else:
        body = (
            f"你是一个可穿戴 AI 系统的「维度总结」环节。下面是用户主题维度 "
            f"「{prepared.dimension}」、时间窗 {prepared.window_start:%Y-%m-%d %H:%M} "
            f"至 {prepared.window_end:%Y-%m-%d %H:%M} 内的原始记录（已按时间排序，"
            f"共 {len(prepared.sources)} 条）。\n\n"
            "请写一段中文总结：提炼当天该维度发生的值得记住的事实，按时间或主题组织，"
            "每条尽量回扣原文关键词。不要编造、不要把客套/无信息内容当事实。\n"
            "只输出总结正文，不超过 220 字。\n\n记录：\n" + "\n".join(lines)
        )
    # 推理模型会把预算耗在思考上，给足 max_tokens 避免空正文/finish_reason=length。
    return harness._call_model(
        [{"role": "user", "content": body}], 2500, f"总结[{prepared.dimension}]"
    )


# --------------------------------------------------------------------------
# 机制验证（stub handler，本地联网无关）
# --------------------------------------------------------------------------
def run_mechanism() -> dict:
    store, index = fresh_store("mech_all")
    for di in range(3):
        ingest_day(store, index, di)

    sched = MultiScaleSummaryScheduler(
        store=store, index=index, subject_id=SUBJECT,
        summary_handler=lambda p: "STUB",
        source_admission=cleaning_admission,
        dimension_source_caps=DIMENSION_SOURCE_CAPS,
    )

    # 1) 全维度发现
    dims = sched.active_dimensions()

    # now 必须严格晚于所有目标窗口 end，窗口才会"闭合"。
    # DATES[2]=10-30；+3 天=11-02(周一)：3 个 DAY 窗口全闭合，且上一周(10-26~11-01)
    # 与 10 月(10-01~10-31) 都已闭合，可验证 WEEK/MONTH 自底向上。
    now = DATES[2] + timedelta(days=3)

    # 2) 每维度 DAY 总结（3 天 × 9 维度，预期 27 条）
    res_day = sched.run_due(now=now, scales=(SummaryScale.DAY,), max_jobs=400)
    day_commits: dict[str, int] = {}
    for c in res_day.commits:
        payload = store.get_payload(c.object_id)
        dim = payload["metadata"]["dimension"]
        day_commits[dim] = day_commits.get(dim, 0) + 1

    # 2b) 今日总览（dim:daily_digest）：全量 sweep 在各维度 DAY 之后自动触发
    digest_commits = [
        c for c in res_day.commits
        if store.get_payload(c.object_id)["metadata"]["dimension"] == DIGEST_DIMENSION
    ]
    digest_sources_dims = []
    if digest_commits:
        dp = store.get_payload(digest_commits[0].object_id)
        digest_sources_dims = sorted(dp["coverage"].get("source_dimensions", []))
        digest_source_count = dp["coverage"]["source_count"]
    else:
        digest_source_count = 0

    # 各维度 DAY 提交数（排除 digest 自身）
    dim_only_day_commits = {
        d: n for d, n in day_commits.items() if d != DIGEST_DIMENSION
    }

    # 3) 幂等：同一批窗口重跑 → 应全部 skipped_unchanged、0 新提交
    res_day2 = sched.run_due(now=now, scales=(SummaryScale.DAY,), max_jobs=400)

    # 4) 多尺度自底向上：WEEK 允许"原始 observation + 更低尺度(day)总结"，
    #    但绝不能出现同/更高尺度的总结(否则构成自依赖/跨尺度环)。
    res_week = sched.run_due(now=now, scales=(SummaryScale.WEEK,), max_jobs=400)
    week_commits_per_dimension: dict[str, int] = {}
    for c in res_week.commits:
        payload = store.get_payload(c.object_id)
        d = payload["metadata"]["dimension"]
        week_commits_per_dimension[d] = week_commits_per_dimension.get(d, 0) + 1
    week_rank = _SUMMARY_SCALE_RANK["week"]
    week_checked = 0
    week_includes_day_summary = False
    week_has_equal_or_higher_summary = False
    week_has_raw = False
    week_windows = set()
    for c in res_week.commits:
        payload = store.get_payload(c.object_id)
        st = payload["summary_time"]
        ws = datetime.fromisoformat(st["start"].replace("Z", "+00:00"))
        we = datetime.fromisoformat(st["end"].replace("Z", "+00:00"))
        week_windows.add((ws.isoformat(), we.isoformat()))
        prep = sched.service.prepare(
            dimension=payload["metadata"]["dimension"],
            granularity="week",
            window_start=ws,
            window_end=we,
            include_summary_sources=True,
        )
        week_checked += 1
        for s in prep.sources:
            if s.object_type == "summary":
                sp = store.get_payload(s.object_id)
                g = str(sp.get("granularity") or "")
                if g == "day":
                    week_includes_day_summary = True
                r = _SUMMARY_SCALE_RANK.get(g)
                if r is not None and r >= week_rank:
                    week_has_equal_or_higher_summary = True
            else:
                week_has_raw = True

    # 5) 清洗协同缺口：dim:mic_audio DAY1 总结的源是否含已知噪声 id。
    #    object_id 是哈希，必须读 source.metadata["external_record_id"]（形如 m01@d0）。
    noise_ids = {rid for rid, (lab, _) in sim_realtime.DAY0_LABELS.items() if lab == "DROP"}
    mic_day1 = sched.service.prepare(
        dimension="dim:mic_audio",
        granularity="day",
        window_start=DATES[0],
        window_end=DATES[0] + timedelta(days=1) - timedelta(microseconds=1),
    )

    def _ext(s) -> str:
        md = s.metadata or {}
        rid = str(md.get("external_record_id") or "")
        return rid.split("@")[0]

    mic_ext = {_ext(s) for s in mic_day1.sources}
    noise_in_summary = sorted(mic_ext & noise_ids)
    n_mic = len(mic_day1.sources)

    # 6) 窗口边界稳定（代码层）
    bounds = {}
    for sc in (SummaryScale.DAY, SummaryScale.WEEK, SummaryScale.MONTH):
        s, e = window_bounds(DATES[0] + timedelta(hours=9), sc)
        bounds[sc.value] = (s.isoformat(), e.isoformat())

    return {
        "active_dimensions": dims,
        "n_dimensions": len(dims),
        "day_commits_per_dimension": dim_only_day_commits,
        "n_day_commits": len(res_day.commits) - len(digest_commits),
        "n_day_skipped_empty": len(res_day.skipped_empty),
        "daily_digest": {
            "n_commits": len(digest_commits),
            "source_dimensions_of_first": digest_sources_dims,
            "source_count_of_first": digest_source_count,
        },
        "rerun_commits": len(res_day2.commits),
        "rerun_skipped_unchanged": len(res_day2.skipped_unchanged),
        "week_n_commits": len(res_week.commits),
        "week_commits_per_dimension": week_commits_per_dimension,
        "week_windows": sorted(week_windows),
        "week_checked": week_checked,
        "week_includes_day_summary_source": week_includes_day_summary,
        "week_has_equal_or_higher_summary_source": week_has_equal_or_higher_summary,
        "week_has_raw_observation_source": week_has_raw,
        "mic_day1_source_count": n_mic,
        "noise_ids_in_mic_summary": noise_in_summary,
        "n_noise_in_mic_summary": len(noise_in_summary),
        "window_bounds_utc": bounds,
    }


# --------------------------------------------------------------------------
# 真实模型内容回声（单天，逐维度）
# --------------------------------------------------------------------------
NOISE_TOKENS = ["哈哈哈", "在吗", "烦死了", "随便", "算了", "睡了", "世界末日", "额", "啊行"]


def run_echo(day_idx: int) -> dict:
    store, index = fresh_store(f"echo_{day_idx}")
    ingest_day(store, index, day_idx)
    sched = MultiScaleSummaryScheduler(
        store=store, index=index, subject_id=SUBJECT,
        summary_handler=summary_handler_real_model,
        source_admission=cleaning_admission,
        dimension_source_caps=DIMENSION_SOURCE_CAPS,
    )
    day = sim_realtime.DAYS[day_idx]
    # 必须严格晚于当天窗口 end(即次日 00:00)，否则被当成未闭合窗口排除。
    now = DATES[day_idx] + timedelta(days=1)
    res = sched.run_due(now=now, scales=(SummaryScale.DAY,), max_jobs=200)

    summaries = {}
    for c in res.commits:
        payload = store.get_payload(c.object_id)
        summaries[payload["metadata"]["dimension"]] = {
            "content": payload["content"],
            "source_count": payload["coverage"]["source_count"],
        }

    rec_dim = {rec["id"]: rec["dim"] for rec in day["records"]}

    # A) 按维度归属分摊：每个维度只对"有该维度源记录"的事实负责
    #    （digest 是跨维度总览，不参与单维度口径，只在 B/C 里考察）
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
            "responsible": resp,
            "hit": hit,
            "rate": f"{len(hit)}/{len(resp)}" if resp else "n/a",
        }

    # B) 跨维度覆盖：7 条事实"合起来"是否被所有维度总结抓住（真实"今天发生了什么"口径）
    cross = {}
    covered = 0
    for label, ids in day["checks"]:
        dims = {rec_dim.get(i) for i in ids}
        hit_dims = [d for d in dims if d in summaries
                    and any(k in summaries[d]["content"] for k in day["keywords"][label])]
        cross[label] = {"covered": bool(hit_dims), "hit_in_dims": sorted(hit_dims)}
        if hit_dims:
            covered += 1

    # C) 逐维度噪声污染：总结是否把 DROP 类噪声当事实写入
    pollution = {}
    for dim, info in summaries.items():
        toks = [t for t in NOISE_TOKENS if t in info["content"]]
        if toks:
            pollution[dim] = toks

    return {
        "day": day["name"],
        "n_dimension_summaries": len(summaries),
        "dimensions_summarized": sorted(summaries.keys()),
        "summaries": summaries,
        "per_dimension_echo": per_dim,
        "cross_dimension_covered": f"{covered}/{len(day['checks'])}",
        "cross_dimension_detail": cross,
        "noise_pollution_by_dimension": pollution,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["mechanism", "echo"], required=True)
    ap.add_argument("--day", type=int, default=0, help="echo 模式用：0/1/2")
    args = ap.parse_args()

    t0 = time.time()
    if args.mode == "mechanism":
        out = run_mechanism()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        (HERE / "result_mechanism.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    else:
        out = run_echo(args.day)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        (HERE / f"result_echo_day{args.day + 1}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(f"[{args.mode}] 用时 {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
