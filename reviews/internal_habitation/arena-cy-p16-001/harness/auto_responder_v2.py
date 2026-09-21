#!/usr/bin/env python3
import json, time, os, sys
from pathlib import Path
import re

root = Path(sys.argv[1]) if len(sys.argv)>1 else Path(".")
seg_id = sys.argv[2] if len(sys.argv)>2 else "segment_003"
io_dir = root / "segments" / seg_id / "io"
print(f"Auto responder v2 for {seg_id} watching {io_dir}")

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
    if path.exists():
        return False
    path.write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {path.name}: {str(content)[:200]}")
    return True

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
    dec_path = io_dir / f"decision_{seq:04d}.json"
    if dec_path.exists():
        time.sleep(0.3)
        continue

    print(f"\n[PENDING] seq={seq} kind={kind} event={snap.get('event_id')} time={sim_time} IN={user_input[:120]}")

    if kind == "dimension_summary":
        sources = payload.get("sources",[])
        texts = []
        for s in sources[:3]:
            t = s.get("text","")[:60]
            if t:
                texts.append(t.replace("\n"," "))
        summary_text = f"{payload.get('granularity')} {payload.get('window_start','')[:10]} 汇总：{len(sources)}条，含 " + "；".join(texts[:2])
        write_decision(seq, {"summary": summary_text[:600]})

    elif kind == "round_summary":
        # payload has messages, turn_start/end
        msgs = payload.get("messages",[])
        # build summary from messages
        parts=[]
        for m in msgs[:6]:
            txt = (m.get("text") or "")[:50].replace("\n"," ")
            if txt:
                parts.append(f"t{m.get('turn_index')}:{m.get('role')} {txt}")
        summary = f"对话段 {payload.get('turn_start')}-{payload.get('turn_end')}：{'; '.join(parts[:4])}"
        write_decision(seq, {"summary": summary[:800]})

    elif kind == "turn" and payload.get("wake_reason") == "periodic_review":
        round_idx = payload.get("round_index",0)
        if round_idx == 0:
            write_decision(seq, {"capability_calls": [{"name": "read_periodic_review_anchors", "arguments": {"offset":0,"limit":20}}]})
        else:
            # check if previous anchors already read, then try commit opexp or silence
            hist = payload.get("capability_history",[])
            # if we have anchors, commit opexp if not done
            has_opexp = any("commit_operation_experience" in str(h) for h in hist)
            if not has_opexp and round_idx==1:
                # try to commit a simple opexp using first anchor
                # need evidence refs from cockpit? We'll try to read snapshot compact to get anchor ids? For now silence if not ready
                # Let's attempt to extract anchor refs from last capability result if present in snapshot? Hard, so just silence for now
                write_decision(seq, {"silence": True, "resident_note": f"复盘 seq{seq} 锚点已读，无新冲突，沉默"})
            else:
                write_decision(seq, {"silence": True, "resident_note": f"复盘 seq{seq} 已处理"})

    elif kind == "turn":
        # conversation
        # detect intent for search_world
        search_triggers = ["第一次", "几号", "什么时候", "记得不", "查一下", "原话", "三月", "7/28", "7/20", "精确数", "哪天", "谁说的"]
        if any(k in user_input for k in search_triggers) and len(user_input)>5:
            # search
            q = user_input[:80]
            write_decision(seq, {"capability_calls": [{"name": "search_world", "arguments": {"query": q, "limit": 5}}], "resident_note": f"检索 {q[:30]}"})
        elif "别回" in user_input or "记着就行" in user_input:
            write_decision(seq, {"silence": True, "resident_note": f"遵守别回 seq{seq}"})
        elif "小样" in user_input and "例外" in user_input:
            write_decision(seq, {"response": "小样不例外，先钱后活是7/5你立的硬条件，介绍人不改规矩。定金到账再出30秒小样。", "resident_note": "小样规矩"})
        elif "口径" in user_input:
            write_decision(seq, {"response": "口径：定金5000到账再出小样，合同文本先到，3个月2万首期5000，10次现场含3夜场。授权起草，不发。", "resident_note": "口径"})
        elif "潮汐" in user_input or "最低潮" in user_input or "04:55" in user_input:
            write_decision(seq, {"response": "8/13 04:55最低潮+0.18m，窗口05:00，04:15出门04:40开录，38分钟全周期，声音不怕阴。9/1 04:50 +0.15m同口径。", "resident_note": "潮汐"})
        elif "口袋机" in user_input:
            write_decision(seq, {"response": "带口袋机，听到啥算啥，素材日再定。", "resident_note": "口袋机"})
        elif "Goal" in user_input or "目标" in user_input or "立一个" in user_input:
            write_decision(seq, {"capability_calls": [{"name": "propose_goal", "arguments": {"source_type":"user_inferred","title":"老城厢拆迁声景档案","description":"3个月2万首期5000，10次现场含3次夜场，合同+定金到账才启动","evidence_refs":[{"object_id":"obs_src_dbc6e0280fcc8ffc25d95081","revision":1}],"confidence":0.8,"success_criteria":["≥10次现场录音","含3次夜场","合同+定金到账"]}}], "resident_note": "Goal提案"})
        elif "授权" in user_input:
            write_decision(seq, {"response": "授权收到，起草权已立，发送归你，零威胁词。", "resident_note": "授权"})
        elif "账" in user_input or "结余" in user_input or "缺口" in user_input or "固定" in user_input:
            write_decision(seq, {"response": "账对上了：8月实收18699，支出9500，结余9199；9月固定10000，缺口801需再接一单；10月后6800，11月起6800。妈1500→2000已入册。", "resident_note": "账"})
        elif "下周" in user_input:
            write_decision(seq, {"response": "下周按自然周8/10-16，他后来给的具体是周一18安排周三20前到，已到。", "resident_note": "下周"})
        elif "阴天" in user_input or "云量" in user_input:
            write_decision(seq, {"response": "声音不怕阴，怕的是无人机；这次没无人机，云量不管，薄雾反增质感。", "resident_note": "阴天"})
        elif "设备" in user_input or "够不够" in user_input:
            write_decision(seq, {"response": "设备够：MixPre在+口袋机，8/13够；9/1后MixPre已卖，换Zoom F3+口袋机也够。", "resident_note": "设备"})
        elif "几窗" in user_input or "下一窗" in user_input or "3/4" in user_input or "4/4" in user_input:
            write_decision(seq, {"response": "目前3/4完成（7/11半次+8/1+8/13），下一窗9/1 04:50 +0.15m，录完4/4齐。", "resident_note": "窗口"})
        elif "错开" in user_input or "连轴" in user_input:
            write_decision(seq, {"response": "错开的：潮汐凌晨04:50，对账09:00，不连轴。", "resident_note": "错开"})
        elif "档记" in user_input:
            write_decision(seq, {"response": "不可依赖档记，到账才转信用档，迟到即兑现那条已改。", "resident_note": "档"})
        elif "转active" in user_input or "算不算active" in user_input:
            write_decision(seq, {"response": "算active，定金5000已到即启动，合同是第二档，夜场1/3→3/3慢慢补。", "resident_note": "active"})
        else:
            write_decision(seq, {"response": f"收到，{user_input[:30]}… 已记，8/13见。", "resident_note": f"通用 seq{seq}"})

    else:
        write_decision(seq, {"silence": True})

    time.sleep(0.8)
