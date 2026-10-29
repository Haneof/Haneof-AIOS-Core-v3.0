import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cognition_echo import ask
from sim_day import RECORDS

runs = json.loads(Path("ai_runs.json").read_text(encoding="utf-8"))
valid = [r for r in runs if "error" not in r]
ai_ids = [str(d["id"]) for d in valid[0]["decisions"]
          if str(d.get("decision","")).lower() == "keep"]
print(f"AI 臂保留 {len(ai_ids)} 条，开始回声（最多 4 次重试）", flush=True)
for attempt in range(1, 5):
    try:
        res = ask(ai_ids, "AI清洗后")
        print(f"\n=== {res['tag']} === 输入 {res['input_count']} 条 / {res['input_chars']} 字符 / {res['elapsed']}s")
        print(f"认知还原 {res['hit_count']}/7  finish={res['finish_reason']}")
        for label, ok in res["hits"].items():
            print(f"  {'命中' if ok else '丢失'}  {label}")
        print("--- 总结原文 ---")
        print(res["summary"][:1000])
        Path("echo_ai.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        break
    except Exception as exc:
        print(f"第 {attempt} 次失败：{type(exc).__name__} {str(exc)[:160]}", flush=True)
        time.sleep(10)
