"""echo 驱动（可续跑）：9 维 sweep（限定模式跳过 digest）+ digest 单独提交 + 分析。

用法：python3 run_echo_driver.py --day 0
结果落 result_echo_dayN.json（与 verify_summary.py echo 模式同构）。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "cleaning_ab"))
sys.path.insert(0, "src")

import sim_realtime  # noqa: E402

from aios_core.summaries import (  # noqa: E402
    DIGEST_DIMENSION,
    SummaryScale,
)
from verify_summary import (  # noqa: E402
    DIMENSION_SOURCE_CAPS,
    NOISE_TOKENS,
    SUBJECT,
    cleaning_admission,
    fresh_store,
    ingest_day,
    summary_handler_real_model,
)
from aios_core.summaries import MultiScaleSummaryScheduler  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int, default=0)
    args = ap.parse_args()
    day_idx = args.day

    store, index = fresh_store(f"echo_{day_idx}")
    ingest_day(store, index, day_idx)
    sched = MultiScaleSummaryScheduler(
        store=store, index=index, subject_id=SUBJECT,
        summary_handler=summary_handler_real_model,
        source_admission=cleaning_admission,
        dimension_source_caps=DIMENSION_SOURCE_CAPS,
    )
    now = sim_realtime.DATES[day_idx] + timedelta(days=1)

    # 1) 全量 sweep（scheduler 已 fail-soft：digest 撞网关失败不中断其他维度）
    res = sched.run_due(now=now, scales=(SummaryScale.DAY,), max_jobs=200)
    for f in res.failed:
        print(f"[driver] job 失败（下轮重试）: {f.job.dimension} {f.error[:80]}", flush=True)
    dims_done = sorted({
        store.get_payload(c.object_id)["metadata"]["dimension"] for c in res.commits
    })
    print(f"[driver] 维度 DAY 完成: {len(res.commits)} {dims_done}", flush=True)

    # 2) 今日总览（digest）：若 sweep 中因网关失败未提交，再补一次
    digest_content = None
    wins = sched._digest_candidate_windows(now=now)
    for start, end in wins:
        p = sched.digest_service.prepare(window_start=start, window_end=end)
        if not p.sources:
            continue
        try:
            content = summary_handler_real_model(p)
            c = sched.digest_service.commit(p, content=content, generated_at=now)
            digest_content = content
            print(f"[driver] digest 提交 {c.object_id} rev{c.revision}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[driver] digest 仍失败，分析继续（无 digest）："
                  f"{type(exc).__name__}: {str(exc)[:80]}", flush=True)

    # 3) 分析（与 verify_summary.run_echo 同口径）
    day = sim_realtime.DAYS[day_idx]
    summaries = {}
    for payload in store.list_payloads(object_type="summary", subject_id=SUBJECT):
        dim = (payload.get("metadata") or {}).get("dimension")
        st = payload.get("summary_time") or {}
        if st.get("start", "")[:10] != sim_realtime.DATES[day_idx].date().isoformat():
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


if __name__ == "__main__":
    main()
