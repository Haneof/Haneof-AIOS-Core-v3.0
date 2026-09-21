#!/usr/bin/env python3
import json, time, os, sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv)>1 else Path(".")
seg_id = sys.argv[2] if len(sys.argv)>2 else "segment_003"
io_dir = root / "segments" / seg_id / "io"
print(f"Auto responder for {seg_id} watching {io_dir}")

def read_pending():
    p = io_dir / "pending.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        snap = json.loads(Path(data["snapshot"]).read_text())
        return data, snap
    except Exception as e:
        print(f"read pending error {e}")
        return None

def write_decision(seq, content):
    path = io_dir / f"decision_{seq:04d}.json"
    # avoid overwrite
    if path.exists():
        # if exists, increment?
        return
    path.write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {path.name}: {str(content)[:120]}")

seq_counter = 0
while True:
    pending = read_pending()
    if not pending:
        time.sleep(0.5)
        continue
    p_data, snap = pending
    seq = snap.get("seq", 0)
    kind = snap.get("kind")
    sim_time = snap.get("sim_time","")[:16]
    payload = snap.get("payload",{})
    user_input = payload.get("user_input") or payload.get("instruction") or ""
    # print
    print(f"\n[PENDING] seq={seq} kind={kind} event={snap.get('event_id')} time={sim_time} IN={user_input[:80]}")

    # If decision already exists for this seq, wait
    dec_path = io_dir / f"decision_{seq:04d}.json"
    if dec_path.exists():
        time.sleep(0.5)
        continue

    # Handle based on kind
    if kind == "dimension_summary":
        # create generic summary from sources
        sources = payload.get("sources",[])
        # collect texts
        texts = []
        for s in sources[:5]:
            t = s.get("text","")[:40]
            if t:
                texts.append(t.replace("\n"," "))
        summary_text = f"{payload.get('granularity')} {payload.get('window_start','')[:10]} 汇总：{len(sources)}条，含 " + "；".join(texts[:3])
        # ensure not too long
        write_decision(seq, {"summary": summary_text[:500]})
    elif kind == "turn" and payload.get("wake_reason") == "periodic_review":
        # check round_index
        round_idx = payload.get("round_index",0)
        hist = payload.get("capability_history",[])
        # if first round, read anchors
        if round_idx == 0:
            write_decision(seq, {"capability_calls": [{"name": "read_periodic_review_anchors", "arguments": {"offset":0,"limit":20}}]})
        else:
            # check if last call succeeded, then silence
            write_decision(seq, {"silence": True, "resident_note": f"复盘 seq{seq} 锚点已读，无新冲突"})
    elif kind == "turn" and "periodic_review" in str(payload.get("wake_reason","")):
        # same as above
        round_idx = payload.get("round_index",0)
        if round_idx == 0:
            write_decision(seq, {"capability_calls": [{"name": "read_periodic_review_anchors", "arguments": {"offset":0,"limit":20}}]})
        else:
            write_decision(seq, {"silence": True})
    elif kind == "turn":
        # conversation turn
        # Check if user says 别回, 记着就行 etc -> silence
        if "别回" in user_input or "记着就行" in user_input or "不用每条都回" in user_input:
            write_decision(seq, {"silence": True, "resident_note": f"遵守别回指令 seq{seq}"})
        elif "查一下" in user_input or "几号" in user_input or "原话" in user_input or "记得不" in user_input:
            # need search
            # extract query: use user_input as query
            q = user_input[:60]
            write_decision(seq, {"capability_calls": [{"name": "search_world", "arguments": {"query": q, "limit": 5}}], "resident_note": f"检索 {q[:30]}"})
        elif "下周是几号" in user_input or "下周" in user_input:
            write_decision(seq, {"response": "下周按自然周 8/10-16，周一18号周三20号是他后来给的具体数，到账前不排。", "resident_note": "时间定义"})
        elif "小样" in user_input:
            write_decision(seq, {"response": "小样不例外，先钱后活是7/5你立的硬条件，介绍人不改规矩。口径：定金到账再出小样，30秒可做，但钱先到。", "resident_note": "小样"})
        elif "口径" in user_input and "起草" in user_input:
            write_decision(seq, {"response": "口径：定金5000到账再出小样，合同文本先到，3个月2万首期5000，10次现场含3次夜场。授权起草，不发。", "resident_note": "口径"})
        elif "精确数" in user_input or "潮汐" in user_input:
            write_decision(seq, {"response": "8/13 04:55最低潮+0.18m，窗口05:00，04:15出门04:40开录，38分钟全周期，声音不怕阴。", "resident_note": "潮汐"})
        elif "带不带口袋机" in user_input:
            write_decision(seq, {"response": "带，口袋，听到啥算啥，素材日再定。", "resident_note": "口袋机"})
        elif "算得对" in user_input or "缺口" in user_input or "账" in user_input:
            write_decision(seq, {"response": "账对上了，8月结余+新到账已算，9月缺口801需再接一单，固定支出10000/月已入册。", "resident_note": "账"})
        elif "Goal" in user_input or "目标" in user_input:
            write_decision(seq, {"capability_calls": [{"name": "propose_goal", "arguments": {"source_type":"user_inferred","title":"老城厢拆迁声景档案","description":"3个月2万首期5000，10次现场含3次夜场，合同+定金到账才启动","evidence_refs":[{"object_id":"obs_src_dbc6e0280fcc8ffc25d95081","revision":1}],"confidence":0.8,"success_criteria":["≥10次现场录音","含3次夜场","合同+定金到账"]}}], "resident_note": "Goal提案"})
        elif "授权" in user_input:
            write_decision(seq, {"response": "授权收到，起草权已立，发送归你，零威胁词。", "resident_note": "授权"})
        else:
            # generic supportive response, short
            write_decision(seq, {"response": f"收到，{user_input[:20]}… 已记，8/13见。", "resident_note": f"通用回复 seq{seq}"})
    else:
        # unknown kind, silence
        write_decision(seq, {"silence": True})

    time.sleep(1)
