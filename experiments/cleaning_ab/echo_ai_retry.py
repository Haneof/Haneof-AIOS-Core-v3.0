import json, sys, os, time, urllib.request, urllib.error
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aios_core.runtime.resilient_handler import PRIMARY_BASE_URL, PRIMARY_API_KEY, PRIMARY_MODEL
from cognition_echo import build_block, CHECK_KEYWORDS
from sim_day import COGNITION_CHECKS

os.environ.setdefault("AIOS_RPM_PACE", "0")
runs = json.loads(Path("ai_runs.json").read_text(encoding="utf-8"))
valid = [r for r in runs if "error" not in r]
ai_ids = [str(d["id"]) for d in valid[0]["decisions"] if str(d.get("decision","")).lower()=="keep"]
block = build_block(ai_ids)
prompt = ("下面是某位用户 2026-10-28 一天里进入系统的记录。\n"
          "请回答：今天发生了哪些值得记住的事？只列事实，不要编造，每条一行，不超过15字。\n\n记录：\n" + block)
for attempt in range(1, 4):
    body = {"model": PRIMARY_MODEL, "messages":[{"role":"user","content":prompt}],
            "temperature": 0.2, "max_tokens": 2500}
    req = urllib.request.Request(PRIMARY_BASE_URL+"/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization":f"Bearer {PRIMARY_API_KEY}","Content-Type":"application/json"})
    t0=time.time()
    try:
        with urllib.request.urlopen(req, timeout=850) as r:
            d=json.load(r)
        ch=d["choices"][0]; text=ch["message"].get("content") or ""
        print(f"第{attempt}次 OK {time.time()-t0:.0f}s finish={ch.get('finish_reason')} chars={len(text)}", flush=True)
        if not text.strip():
            print("  空正文，视为测量失败", flush=True); time.sleep(15); continue
        hits={l:any(k in text for k in CHECK_KEYWORDS.get(l,())) for l,_ in COGNITION_CHECKS}
        print(f"\n=== AI清洗后 === 输入 {len(ai_ids)} 条 / {len(block)} 字符")
        print(f"认知还原 {sum(1 for v in hits.values() if v)}/7")
        for l,ok in hits.items(): print(f"  {'命中' if ok else '丢失'}  {l}")
        print("--- 总结原文 ---"); print(text[:1000])
        Path("echo_ai.json").write_text(json.dumps({"input_count":len(ai_ids),"summary":text,"hits":hits}, ensure_ascii=False, indent=2), encoding="utf-8")
        break
    except Exception as e:
        print(f"第{attempt}次失败：{type(e).__name__} {str(e)[:150]}", flush=True); time.sleep(20)
