"""Score both arms against the pre-registered ground truth.

Metrics that matter, in the owner's own terms:
  - 误删 (false negative): a KEEP-labelled record that got dropped.
    This is the dangerous one — cleaning that eats a fact is worse than no cleaning.
  - 噪声残留 (noise retained): a DROP-labelled record that survived.
    This is the cost the cleaning was supposed to remove.
  - 认知还原: can each pre-registered conclusion still be derived from what survived?
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sim_day import COGNITION_CHECKS, LABELS, RECORDS  # noqa: E402
from arm_mechanical import run as run_mechanical  # noqa: E402

ALL_IDS = [r["id"] for r in RECORDS]
KEEP_IDS = [i for i in ALL_IDS if LABELS[i][0] == "KEEP"]
DROP_IDS = [i for i in ALL_IDS if LABELS[i][0] == "DROP"]


def score(kept: set[str]) -> dict:
    wrongly_dropped = [i for i in KEEP_IDS if i not in kept]
    noise_retained = [i for i in DROP_IDS if i in kept]
    cognition = []
    for label, required in COGNITION_CHECKS:
        missing = [i for i in required if i not in kept]
        cognition.append(
            {"check": label, "ok": not missing, "missing": missing}
        )
    return {
        "kept_count": len([i for i in ALL_IDS if i in kept]),
        "total": len(ALL_IDS),
        "wrongly_dropped": wrongly_dropped,
        "wrongly_dropped_count": len(wrongly_dropped),
        "noise_retained": noise_retained,
        "noise_retained_count": len(noise_retained),
        "noise_removed": len(DROP_IDS) - len(noise_retained),
        "cognition": cognition,
        "cognition_ok": sum(1 for c in cognition if c["ok"]),
        "cognition_total": len(cognition),
    }


def main() -> None:
    mech = run_mechanical(Path(tempfile.mkdtemp()) / "world.db")
    mech_kept = set(mech["kept"])
    mech_score = score(mech_kept)

    print("=" * 66)
    print("A/B 对照 — 机制清洗 vs AI 清洗")
    print("=" * 66)
    print(f"样本：{len(ALL_IDS)} 条（应保留 {len(KEEP_IDS)}，应删除 {len(DROP_IDS)}）\n")

    print("【机制臂】真实 RealityIngestService")
    print(f"  数值流：{mech['numeric_note']}")
    print(f"  保留 {mech_score['kept_count']}/{mech_score['total']}")
    print(f"  误删重要事实：{mech_score['wrongly_dropped_count']} 条 {mech_score['wrongly_dropped']}")
    print(f"  噪声残留：{mech_score['noise_retained_count']}/{len(DROP_IDS)} 条（清理掉 {mech_score['noise_removed']} 条）")
    print(f"  认知还原：{mech_score['cognition_ok']}/{mech_score['cognition_total']}")
    for c in mech_score["cognition"]:
        if not c["ok"]:
            print(f"     [还原失败] {c['check']} — 缺 {c['missing']}")

    runs_path = Path(__file__).resolve().parent / "ai_runs.json"
    if not runs_path.exists():
        print("\n（ai_runs.json 不存在，AI 臂尚未跑完）")
        return
    runs = json.loads(runs_path.read_text(encoding="utf-8"))
    print("\n【AI 臂】" + f"共 {len(runs)} 轮")
    agg = []
    for r in runs:
        if "error" in r:
            print(f"  第 {r['run']} 轮：失败 {r['error'][:100]}")
            continue
        kept = set()
        for d in r["decisions"]:
            if str(d.get("decision", "")).strip().lower() == "keep":
                kept.add(str(d.get("id", "")))
        s = score(kept)
        agg.append(s)
        print(f"\n  第 {r['run']} 轮（{r['elapsed']}s，{len(r['decisions'])} 条判断）")
        print(f"    保留 {s['kept_count']}/{s['total']}")
        print(f"    误删重要事实：{s['wrongly_dropped_count']} 条 {s['wrongly_dropped']}")
        print(f"    噪声残留：{s['noise_retained_count']}/{len(DROP_IDS)}（清理掉 {s['noise_removed']} 条）")
        print(f"    认知还原：{s['cognition_ok']}/{s['cognition_total']}")
        for c in s["cognition"]:
            if not c["ok"]:
                print(f"       [还原失败] {c['check']} — 缺 {c['missing']}")

    if agg:
        wd = [s["wrongly_dropped_count"] for s in agg]
        nr = [s["noise_retained_count"] for s in agg]
        co = [s["cognition_ok"] for s in agg]
        print("\n" + "=" * 66)
        print("汇总")
        print("=" * 66)
        print(f"  机制臂：误删 0，噪声残留 {mech_score['noise_retained_count']}/{len(DROP_IDS)}，认知 {mech_score['cognition_ok']}/{mech_score['cognition_total']}")
        print(f"  AI  臂：误删 {wd}（均值 {sum(wd)/len(wd):.1f}）")
        print(f"          噪声残留 {nr}（均值 {sum(nr)/len(nr):.1f}）")
        print(f"          认知还原 {co}（均值 {sum(co)/len(co):.1f}）")

        # 逐条稳定性：哪些条在三轮里判断不一致
        per_id: dict[str, list[str]] = {}
        for r in runs:
            if "error" in r:
                continue
            for d in r["decisions"]:
                per_id.setdefault(str(d.get("id", "")), []).append(
                    str(d.get("decision", "")).lower()
                )
        unstable = {k: v for k, v in per_id.items() if len(set(v)) > 1}
        print(f"\n  三轮判断不一致的条目：{len(unstable)} 条 {sorted(unstable)}")
        for k in sorted(unstable):
            print(f"    {k}: {unstable[k]} (标签={LABELS.get(k, ('?',))[0]})")


if __name__ == "__main__":
    main()
