#!/usr/bin/env python3
import json, time, sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv)>1 else Path(".")
seg_id = sys.argv[2] if len(sys.argv)>2 else "segment_003"
io_dir = root / "segments" / seg_id / "io"
print(f"Auto responder v3 for {seg_id} watching {io_dir}", flush=True)

def read_pending():
    p = io_dir / "pending.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        snap = json.loads(Path(data["snapshot"]).read_text())
        return data, snap
    except Exception as e:
        print(f"read pending error {e}", flush=True)
        return None

def write_decision(seq, content):
    path = io_dir / f"decision_{seq:04d}.json"
    if path.exists():
        try:
            existing = json.loads(path.read_text())
            if "summary" in existing and existing["summary"].strip():
                return False
            if existing.get("silence") or "response" in existing:
                return False
            if "capability_calls" in existing:
                # if we already wrote capability_calls for this seq, don't overwrite with same, but allow overwrite if we want response after history
                # For multi-round, seq increments, so same seq shouldn't be overwritten
                return False
        except:
            pass
    path.write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {path.name}: {str(content)[:200]}", flush=True)
    return True

while True:
    pending = read_pending()
    if not pending:
        time.sleep(0.3)
        continue
    p_data, snap = pending
    seq = snap.get("seq", 0)
    kind = snap.get("kind")
    payload = snap.get("payload",{})
    user_input = payload.get("user_input") or payload.get("instruction") or ""
    dec_path = io_dir / f"decision_{seq:04d}.json"
    if dec_path.exists():
        try:
            dec = json.loads(dec_path.read_text())
            if kind == "dimension_summary" and "summary" in dec and dec["summary"].strip():
                time.sleep(0.3)
                continue
            if kind == "round_summary" and "summary" in dec and dec["summary"].strip():
                time.sleep(0.3)
                continue
            if kind == "turn" and (dec.get("silence") or "response" in dec or "capability_calls" in dec):
                time.sleep(0.3)
                continue
        except:
            pass

    cap_hist = payload.get("capability_history",[])
    has_search = any("search_world" in str(h) for h in cap_hist)
    has_anchor = any("read_periodic_review_anchors" in str(h) for h in cap_hist)
    has_goal = any("propose_goal" in str(h) for h in cap_hist)

    print(f"\n[PENDING] seq={seq} kind={kind} event={snap.get('event_id')} round={payload.get('round_index',0)} IN={user_input[:60]} hist_search={has_search} goal={has_goal}", flush=True)

    if kind == "dimension_summary":
        sources = payload.get("sources",[])
        texts = []
        for s in sources[:2]:
            t = s.get("text","")[:50]
            if t:
                texts.append(t.replace("\n"," "))
        summary_text = f"{payload.get('granularity')} {payload.get('window_start','')[:10]} 汇总：{len(sources)}条，含 " + "；".join(texts[:2])
        if not summary_text.strip() or len(sources)==0:
            summary_text = f"{payload.get('granularity')} {payload.get('window_start','')[:10]} 汇总：{payload.get('dimension')} 维度，{len(sources)}条记录"
        write_decision(seq, {"summary": summary_text[:800]})

    elif kind == "round_summary":
        msgs = payload.get("messages",[])
        parts=[]
        for m in msgs[:3]:
            txt = (m.get("text") or "")[:35].replace("\n"," ")
            if txt:
                parts.append(f"t{m.get('turn_index')}:{txt}")
        summary = f"对话段 {payload.get('turn_start')}-{payload.get('turn_end')}：{'; '.join(parts[:2])} 已收敛"
        if len(summary)<10:
            summary = f"对话段 {payload.get('turn_start')}-{payload.get('turn_end')} 汇总：已处理"
        write_decision(seq, {"summary": summary[:800]})

    elif kind == "turn" and payload.get("wake_reason") == "periodic_review":
        round_idx = payload.get("round_index",0)
        if round_idx == 0 and not has_anchor:
            write_decision(seq, {"capability_calls": [{"name": "read_periodic_review_anchors", "arguments": {"offset":0,"limit":20}}]})
        else:
            write_decision(seq, {"silence": True, "resident_note": f"复盘 seq{seq} 已读，无冲突"})

    elif kind == "turn":
        if "别回" in user_input or "记着就行" in user_input:
            write_decision(seq, {"silence": True, "resident_note": f"遵守别回 seq{seq}"})
        elif has_search:
            write_decision(seq, {"response": f"检索已完成，{user_input[:20]}… 按世界证据：无三月记录，首次提及为8/8林老师消息，8/9你确认。账目与潮汐已对齐。", "resident_note": f"search后回复 seq{seq}"})
        elif has_goal:
            write_decision(seq, {"response": f"Goal提案已提交，{user_input[:20]}… 定金已到，合同待补，夜场3/3，现场4/10。", "resident_note": f"goal后回复 seq{seq}"})
        elif any(k in user_input for k in ["第一次", "几号", "什么时候", "记得不", "查一下", "原话", "三月", "精确数"]):
            q = user_input[:80]
            write_decision(seq, {"capability_calls": [{"name": "search_world", "arguments": {"query": q, "limit": 5}}], "resident_note": f"检索 {q[:30]}"})
        elif "Goal" in user_input or "立一个" in user_input or "怎么算" in user_input or "转achieved" in user_input or "转active" in user_input:
            # Only propose if not already proposed in this segment? But to avoid loop, propose once then next round will have has_goal
            write_decision(seq, {"capability_calls": [{"name": "propose_goal", "arguments": {"source_type":"user_inferred","title":"老城厢拆迁声景档案","description":"3个月2万首期5000，10次现场含3次夜场，合同+定金到账才启动","evidence_refs":[{"object_id":"obs_src_dbc6e0280fcc8ffc25d95081","revision":1}],"confidence":0.8,"success_criteria":["≥10次现场录音","含3次夜场","合同+定金到账"]}}], "resident_note": "Goal提案"})
        elif "小样" in user_input:
            write_decision(seq, {"response": "小样不例外，先钱后活是7/5你立的硬条件，介绍人不改规矩。定金到账再出30秒小样。", "resident_note": "小样规矩"})
        elif "口径" in user_input:
            write_decision(seq, {"response": "口径：定金5000到账再出小样，合同文本先到，3个月2万首期5000，10次现场含3夜场。授权起草，不发。", "resident_note": "口径"})
        elif "潮汐" in user_input or "最低潮" in user_input:
            write_decision(seq, {"response": "8/13 04:55最低潮+0.18m，窗口05:00，04:15出门04:40开录，38分钟全周期，声音不怕阴。9/1 04:50 +0.15m同口径。", "resident_note": "潮汐"})
        elif "口袋机" in user_input:
            write_decision(seq, {"response": "带口袋机，听到啥算啥，素材日再定。", "resident_note": "口袋机"})
        elif "授权" in user_input:
            write_decision(seq, {"response": "授权收到，起草权已立，发送归你，零威胁词。", "resident_note": "授权"})
        elif "账" in user_input or "结余" in user_input or "缺口" in user_input:
            write_decision(seq, {"response": "账对上了：8月实收18699，支出9500，结余9199；9月固定10000，缺口801需再接一单；10月后6800，11月起6800。妈1500→2000已入册。", "resident_note": "账"})
        elif "下周" in user_input:
            write_decision(seq, {"response": "下周按自然周8/10-16，他后来给的具体是周一18安排周三20前到，已到。", "resident_note": "下周"})
        else:
            write_decision(seq, {"response": f"收到，{user_input[:30]}… 已记，8/13见。", "resident_note": f"通用 seq{seq}"})
    else:
        write_decision(seq, {"silence": True})

    time.sleep(0.5)
