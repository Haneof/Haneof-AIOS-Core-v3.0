#!/usr/bin/env python3
"""Read the newest pending RuntimeSnapshot and print a compact Resident-facing digest.

Mechanical rendering helper only: truncates JSON formatting of the exact snapshot
Core produced (the full-fidelity file remains io/snapshot_XXXX.json). It does not
select, interpret or rank anything.
"""
import json, sys
from pathlib import Path

io_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
pending = json.loads((io_dir / 'pending.json').read_text(encoding='utf-8'))
snap = json.loads(Path(pending['snapshot']).read_text(encoding='utf-8'))
p = snap['payload']

def t(x, n=180):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + '…'

print(f"seq={snap['seq']} kind={snap['kind']} sim={snap['sim_time']} event={snap['event_id']}")
if snap['kind'] == 'turn':
    print(f"wake={p['wake_reason']} round={p['round_index']} left_tools={p['remaining_tool_rounds']}")
    print(f"USER: {t(p['user_input'], 500)}")
    ck = p['cockpit']
    cards = ck.get('memory_cards') or []
    print(f"memory_cards({len(cards)}):")
    for c in cards:
        print(f"  - [{c.get('kind','')}] ref={t(c.get('source_refs') or c.get('object_ref'),90)} text={t(c.get('excerpt') or c.get('content') or c, 200)}")
    rt = ck.get('recent_turns') or []
    print(f"recent_turns({len(rt)}):")
    for r in rt:
        print(f"  {t(r,150)}")
    ssum = ck.get('conversation_summaries') or []
    print(f"conversation_summaries({len(ssum)}):")
    for s_ in ssum:
        print(f"  turns {s_.get('turn_start')}-{s_.get('turn_end')}: {t(s_.get('content'),220)}")
    tc = ck.get('task_context') or {}
    for k in ('topic_state','wake','periodic_review','conversation_continuity'):
        if tc.get(k): print(f"ctx.{k}: {t(tc[k], 400)}")
    pol = tc.get('cognitive_policy_context') or {}
    recs = pol.get('_policy_records') or []
    print(f"policies({pol.get('_meta',{}).get('total',0)}): " + (t(recs, 300) if recs else '(none)'))
    if tc.get('related_execution_anchors'):
        print("exec_anchors: " + t(tc['related_execution_anchors'], 400))
    if tc.get('current_user_observation_ref'):
        print("current_obs: " + t(tc['current_user_observation_ref'], 120))
    aiw = ck.get('ai_identity') or {}
    if aiw: print("ai_identity: " + t(aiw, 500))
else:
    print(json.dumps(p, ensure_ascii=False, default=str)[:4000])
hist = p.get('capability_history') or []
if hist:
    print("history:")
    for h in hist:
        tag = 'ok' if h['ok'] else 'ERR'
        print(f"  [{tag}] {h['name']}: {t(h.get('data') if h['ok'] else h.get('error_message'), 480)}")
