#!/usr/bin/env python3
"""Read-only, standard-library adversarial audit of the frozen RERUN-003 archive.

Usage: python3 audit_probe.py --run-root PATH [--output PATH]
The source is frozen by SHA-256 before first execution. It does not modify the run.
"""
from __future__ import annotations
import argparse, hashlib, json, re, sqlite3
from pathlib import Path
from collections import Counter, defaultdict


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def files(root: Path, suffix: str):
    return sorted(root.rglob(suffix))

def flatten(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from flatten(v)
    elif isinstance(obj, list):
        for v in obj: yield from flatten(v)
    elif obj is not None and isinstance(obj, (str, int, float, bool)):
        yield str(obj)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-root', required=True, type=Path)
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    r = a.run_root.resolve()
    report = {"probe": "C15-RCC-RES-B-ACCEPT-003/window10", "run_root": str(r), "checks": {}}
    check = report["checks"]

    owner = load(r/'owner.json')
    head = load(r/'generation-head.json')
    check['owner_identity'] = {
        "remote_authoritative": owner.get('remote_authoritative'), "phase": owner.get('phase'),
        "run_id": owner.get('run_id'), "session_id": owner.get('session_id'),
        "remote_ref": (owner.get('remote_authority') or {}).get('remote_ref'),
        "authority_sha256": owner.get('remote_authority_sha256'),
        "generation_head": head.get('generation')}

    gen_dirs = sorted((r/'generations').glob('[0-9][0-9][0-9][0-9][0-9][0-9]'), key=lambda p: p.name)
    gen_result = {"generation_dirs": len(gen_dirs), "expected_1_to_48": [p.name for p in gen_dirs] == [f'{i:06d}' for i in range(1,49)], "manifest_failures": [], "artifact_mismatches": [], "artifact_count": 0}
    for gd in gen_dirs:
        mp = gd/'manifest.json'
        if not mp.exists():
            gen_result['manifest_failures'].append({"generation":gd.name,"reason":"manifest missing"}); continue
        m = load(mp)
        if m.get('manifest_sha256') != sha(canon(m.get('artifacts', {}))):
            gen_result['manifest_failures'].append({"generation":gd.name,"reason":"manifest self digest"})
        for rel, expected in m.get('artifacts',{}).items():
            gen_result['artifact_count'] += 1
            p = gd/rel
            if not p.exists() or sha(p.read_bytes()) != expected:
                gen_result['artifact_mismatches'].append({"generation":gd.name,"path":rel,"expected":expected,"actual":sha(p.read_bytes()) if p.exists() else None})
    check['generation_chain'] = gen_result

    ledger_path = r/'exchange/ledger.jsonl'
    records = [json.loads(x) for x in ledger_path.read_text().splitlines() if x.strip()]
    events = defaultdict(list)
    for rec in records: events[rec.get('request_id')].append(rec)
    request_files = {p.name: p for p in (r/'exchange/requests').glob('*.json')}
    response_files = {p.name: p for p in (r/'exchange/responses').glob('*.json')}
    ledger_summary = {"records":len(records),"request_published":sum(x.get('event')=='request_published' for x in records),"response_published":sum(x.get('event')=='response_published' for x in records),"response_consumed":sum(x.get('event')=='response_consumed' for x in records),"request_files":len(request_files),"response_files":len(response_files),"request_hash_mismatches":[],"response_hash_mismatches":[],"lifecycle_anomalies":[],"req0039":[]}
    for rid, rs in events.items():
        if [x.get('event') for x in rs] != ['request_published','response_published','response_consumed']:
            ledger_summary['lifecycle_anomalies'].append({"request_id":rid,"events":[x.get('event') for x in rs]})
        for rec in rs:
            ev = rec.get('event')
            if ev == 'request_published':
                matches=[p for p in request_files.values() if rid in p.name]
                if len(matches)!=1 or sha(matches[0].read_bytes()) != rec.get('request_sha256'):
                    ledger_summary['request_hash_mismatches'].append(rid)
            if ev in ('response_published','response_consumed'):
                matches=[p for p in response_files.values() if rid in p.name]
                if len(matches)!=1 or sha(matches[0].read_bytes()) != rec.get('response_sha256'):
                    ledger_summary['response_hash_mismatches'].append(rid+':'+ev)
            if rid == 'req-0039-model_directive-ed097a32': ledger_summary['req0039'].append(rec)
    check['ledger_crosscheck'] = ledger_summary

    # Independent re-hash of sealed final artifacts and release boundary.
    m48 = load(r/'generations/000048/manifest.json')
    release = load(r/'release-state.json')
    final_release = load(r/'evidence/freeze/release_state.json')
    final_digest = load(r/'evidence/freeze/MANIFEST.json')
    check['terminal'] = {
        "live_release_state": release,
        "frozen_release_state": final_release,
        "freeze_boundary": final_digest.get('release_boundary'),
        "generation48_manifest_hash": sha((r/'generations/000048/manifest.json').read_bytes()),
        "generation_head_manifest_hash_matches": head.get('manifest_file_sha256') == sha((r/'generations/000048/manifest.json').read_bytes()),
        "cursor23_reveal_count": sum(1 for line in (r/'audit.jsonl').read_text().splitlines() if 'cursor_revealed' in line and 'c15rcc-023' in line),
        "revealed_events": [json.loads(line).get('detail',{}).get('event_id') for line in (r/'audit.jsonl').read_text().splitlines() if 'cursor_revealed' in line]
    }

    # Future-event exposure: use audit reveal epochs and ledger publication times to map each
    # request/response to the interval after its cursor reveal and before the next reveal. Scan
    # request bytes, response bytes, and the local durable projection/request packet snapshots.
    import datetime
    audit_rows=[json.loads(x) for x in (r/'audit.jsonl').read_text().splitlines() if x.strip()]
    reveal_epoch={x.get('detail',{}).get('sequence'):x.get('at_epoch') for x in audit_rows if x.get('event')=='cursor_revealed'}
    evmap={seq:load(r/f'evidence/cursor_{seq:02d}.event.json') for seq in range(14,23) if (r/f'evidence/cursor_{seq:02d}.event.json').exists()}
    pubrows={x.get('request_id'):x for x in records if x.get('event')=='request_published'}
    def epoch(iso):
        return datetime.datetime.fromisoformat(iso.replace('Z','+00:00')).timestamp()
    future={"cursors":[],"event_files":[]}
    for seq in range(14,23):
        start=reveal_epoch.get(seq)
        end=reveal_epoch.get(seq+1, float('inf'))
        reqs=[]
        for rid,row in pubrows.items():
            t=epoch(row['wall_clock'])
            if start is not None and start <= t < end:
                rq=[p for p in request_files.values() if rid in p.name]
                rp=[p for p in response_files.values() if rid in p.name]
                if len(rq)==1 and len(rp)==1: reqs.append((rid,rq[0],rp[0]))
        hits=[]
        for future_seq in range(seq+1,23):
            fe=evmap.get(future_seq,{})
            tokens=set(flatten(fe))
            tokens={t for t in tokens if len(t)>=5 and not t.isdecimal()}
            for rid,rqp,rsp in reqs:
                req_text=rqp.read_text(errors='replace'); resp_text=rsp.read_text(errors='replace')
                for token in tokens:
                    if token in req_text or token in resp_text:
                        hits.append({"future_cursor":future_seq,"token":token,"request_id":rid,"surface":"request" if token in req_text else "response"})
        future['cursors'].append({"cursor":seq,"event_id":evmap.get(seq,{}).get('event_id') or f'c15rcc-{seq:03d}',"associated_request_ids":[x[0] for x in reqs],"future_token_hits":hits})
        future['event_files'].append({"cursor":seq,"path":str(r/f'evidence/cursor_{seq:02d}.event.json'),"present":(r/f'evidence/cursor_{seq:02d}.event.json').exists()})
    check['future_event_scan'] = future

    # Operator/custody provenance signals and req-0039 exact timeline.
    incident = r/'evidence/incident_2026-09-29_remote_auth_and_indoubt'
    operator_text = ''
    # W08 PR evidence is supplied separately by CLI-adjacent file, if present.
    op_path = r/'operator_log.txt'
    if op_path.exists(): operator_text = op_path.read_text(errors='replace')
    req39 = ledger_summary['req0039']
    check['req0039_custody'] = {
        "request_id":"req-0039-model_directive-ed097a32",
        "ledger_events":[{"seq":x.get('seq'),"event":x.get('event'),"wall_clock":x.get('wall_clock'),"response_sha256":x.get('response_sha256')} for x in req39],
        "response_sha256":sha((r/'exchange/responses/req-0039-model_directive-ed097a32.json').read_bytes()),
        "response_envelope":load(r/'exchange/responses/req-0039-model_directive-ed097a32.json'),
        "trusted_response_receipt_files":len(list(r.rglob('*response*receipt*'))),
        "provider_identity":load(r/'evidence/freeze/provider_identity.json'),
        "incident_logs":[p.name for p in incident.glob('*')] if incident.exists() else [],
        "authorship_provenance_present_in_run_tree":any('provenance' in p.name.lower() or 'invocation' in p.name.lower() for p in r.rglob('*') if p.is_file())
    }

    # SQLite schemas and semantic cardinalities from the sealed canonical world.
    db=r/'evidence/freeze/private_world.sqlite'
    con=sqlite3.connect(f'file:{db}?mode=ro',uri=True)
    tables=[x[0] for x in con.execute("select name from sqlite_master where type='table' order by name")]
    counts={}
    for t in tables:
        try: counts[t]=con.execute('select count(*) from "'+t.replace('"','""')+'"').fetchone()[0]
        except Exception as ex: counts[t]='ERROR:'+str(ex)
    check['world_sqlite']={"tables":tables,"row_counts":counts,"revision":"requires world_meta inspection","indexes":{}}
    if 'world_meta' in tables:
        check['world_sqlite']['world_meta']=[dict(zip([c[1] for c in con.execute('pragma table_info(world_meta)')], row)) for row in con.execute('select * from world_meta')]
    con.close()

    report['summary']={"generation_count":gen_result['generation_dirs'],"artifacts_checked":gen_result['artifact_count'],"ledger_records":len(records),"request_count":len(request_files),"response_count":len(response_files),"future_scan_cursors":len(future['cursors'])}
    out=json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+'\n'
    if a.output: a.output.write_text(out,encoding='utf-8')
    else: print(out)

if __name__ == '__main__': main()
