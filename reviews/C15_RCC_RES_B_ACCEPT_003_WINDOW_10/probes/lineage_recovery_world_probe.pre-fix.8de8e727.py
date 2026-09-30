#!/usr/bin/env python3
"""Independent read-only A→B lineage, request/attempt/meter, recovery, world, and freeze probes.

Usage: python3 lineage_recovery_world_probe.py --run-root PATH --fresh-a-root PATH [--output PATH]
All byte corruption testing is performed on a temporary copy; authoritative files are read-only.
"""
from __future__ import annotations
import argparse, hashlib, json, sqlite3, tempfile
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED={
 'world':'0d6970ed99367a456e4baa29092bde8f15bc7544496095cc87ad9f029e2603b2',
 'index':'79c877a4bf75091fa90ae81076a6bdb2e265cf6376b657c3f195e9e91f9844e5',
 'release':'6b90fc7a09bce7d575dbcb783dcbe838cab81c2e358515adbb5dca9731f57c37',
 'ledger':'3b2b9e902133c31cc583491aae55834ee9cb71a9bea9ca50a36fd7e8b81da021'}

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def val(v):
    if isinstance(v,bytes): return {'blob_sha256':sha(v),'len':len(v)}
    return v

def db_signature(path):
    c=sqlite3.connect(f'file:{path}?mode=ro',uri=True)
    tabs=[r[0] for r in c.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")]
    result={}
    for t in tabs:
        q='"'+t.replace('"','""')+'"'
        cols=[x[1] for x in c.execute(f'pragma table_info({q})')]
        rows=[]
        for row in c.execute(f'select * from {q}'):
            rows.append(canonical([val(x) for x in row]).decode())
        rows.sort()
        result[t]={'columns':cols,'rows':len(rows),'logical_sha256':sha('\n'.join(rows).encode())}
    c.close(); return result

def openro(p):
    c=sqlite3.connect(f'file:{p}?mode=ro',uri=True); c.row_factory=sqlite3.Row; return c

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-root',type=Path,required=True); ap.add_argument('--fresh-a-root',type=Path,required=True); ap.add_argument('--operator-evidence',type=Path,required=True); ap.add_argument('--output',type=Path)
    a=ap.parse_args(); r=a.run_root.resolve(); ar=a.fresh_a_root.resolve()
    report={'probe':'C15-RCC-RES-B-ACCEPT-003/window10/lineage-recovery-world','run_root':str(r),'fresh_a_root':str(ar),'checks':{}}
    out=report['checks']
    apaths={'world':ar/'world/c15-res-a-c003.world.sqlite','index':ar/'world/c15-res-a-c003.world.search.sqlite','release':ar/'release-state.json','ledger':ar/'exchange/ledger.jsonl'}
    ah={k:sha(p.read_bytes()) for k,p in apaths.items()}
    gen1=r/'generations/000001'; m1=load(gen1/'manifest.json')
    bpaths={'world':gen1/'world/c15-res-b-003.world.sqlite','index':gen1/'world/c15-res-b-003.world.search.sqlite','release':gen1/'release-state.json','ledger':gen1/'exchange/ledger.jsonl'}
    bh={k:sha(p.read_bytes()) for k,p in bpaths.items()}
    al=load(apaths['release']); bl=load(bpaths['release'])
    # report all differing release-state leaves, excluding the unmodified receipt payloads only by explicit path comparison
    def diff(x,y,prefix=''):
        if isinstance(x,dict) and isinstance(y,dict):
            z=[]
            for k in sorted(set(x)|set(y)): z += diff(x.get(k,'<MISSING>'),y.get(k,'<MISSING>'),prefix+'/'+k)
            return z
        if isinstance(x,list) and isinstance(y,list):
            if len(x)!=len(y): return [{'path':prefix,'a_len':len(x),'b_len':len(y)}]
            z=[]
            for i,(u,v) in enumerate(zip(x,y)): z += diff(u,v,prefix+f'/{i}')
            return z
        return [] if x==y else [{'path':prefix,'a':x,'b':y}]
    logical={}
    for k in ('world','index'):
        logical[k]={'fresh_a':db_signature(apaths[k]),'b_gen1':db_signature(bpaths[k])}
        logical[k]['equal']=logical[k]['fresh_a']==logical[k]['b_gen1']
    out['fresh_a_to_b_gen1']={
      'fresh_a_actual_sha256':ah,'fresh_a_sha_pins_exact':ah==EXPECTED,
      'b_gen1_artifact_sha256':bh,'b_gen1_manifest_artifacts_match':all(m1['artifacts'].get(str(p.relative_to(gen1)))==bh[k] for k,p in bpaths.items()),
      'fresh_a_release_boundary':{k:al.get(k) for k in ('active_phase','last_acked_sequence','last_acked_event_id','next_sequence','pending_reveal')},
      'b_gen1_release_boundary':{k:bl.get(k) for k in ('active_phase','last_acked_sequence','last_acked_event_id','next_sequence','pending_reveal')},
      'release_state_leaf_differences':diff(al,bl),
      'world_index_logical_row_equivalence':logical,
      'a_ledger_records':sum(1 for x in apaths['ledger'].read_text().splitlines() if x.strip()),
      'b_gen1_ledger_records':sum(1 for x in bpaths['ledger'].read_text().splitlines() if x.strip()),
      'ledger_byte_identical':apaths['ledger'].read_bytes()==bpaths['ledger'].read_bytes(),
      'final_ledger_prefix_matches_a':(r/'exchange/ledger.jsonl').read_bytes().startswith(apaths['ledger'].read_bytes())}

    # Recreate the frozen Core fingerprint input and bind each exact request file to one attempt.
    db=openro(r/'evidence/freeze/private_world.sqlite')
    attempts=[dict(x) for x in db.execute('select * from background_model_attempts order by attempt_id')]
    bindings={x['attempt_id']:dict(x) for x in db.execute('select * from background_model_request_bindings')}
    meters=[dict(x) for x in db.execute('select * from metering_records')]
    meters_by_attempt={x['background_attempt_id']:x for x in meters}
    reqs=sorted((r/'exchange/requests').glob('*.json'))
    responses=sorted((r/'exchange/responses').glob('*.json'))
    triple=[]; unmatched=[]; ambiguous=[]; used=set()
    for path in reqs:
        env=load(path); body=env['body']; hits=[]
        for at in attempts:
            if at['wake_reason']!=body.get('wake_reason') or at['model_round_index']!=body.get('round_index'): continue
            hist=[]
            for item in body.get('capability_history',[]):
                hist.append({k:item.get(k) for k in ('call_id','data','error_code','error_message','name')} | {'ok':bool(item.get('ok'))})
            payload={'attempt_id':at['attempt_id'],'capability_catalog':[dict(x) for x in body.get('capability_catalog',[])],
             'capability_history':hist,'cockpit':dict(body.get('cockpit',{})),
             'remaining_tool_rounds':int(body.get('remaining_tool_rounds',0)),'round_index':int(body.get('round_index',0)),
             'subject_id':load(r/'owner.json').get('subject_id'),'user_input':body.get('user_input'),
             'wake_reason':body.get('wake_reason'),'work_id':at['work_id'],'work_kind':at['work_kind']}
            fp=sha(canonical(payload))
            if fp==bindings.get(at['attempt_id'],{}).get('outbound_request_fingerprint'): hits.append((at,fp))
        if len(hits)!=1:
            (ambiguous if len(hits)>1 else unmatched).append({'request_id':env.get('request_id'),'match_count':len(hits)}); continue
        at,fp=hits[0]; used.add(at['attempt_id']); meter=meters_by_attempt.get(at['attempt_id'])
        triple.append({'request_id':env.get('request_id'),'attempt_id':at['attempt_id'],'attempt_state':at['state'],'work_kind':at['work_kind'],'work_id':at['work_id'],'round_index':at['model_round_index'],'fingerprint':fp,'meter_record_id':at['meter_record_id'],'meter_attempt_id':meter.get('background_attempt_id') if meter else None})
    out['attempt_meter_request_triad']={
      'requests':len(reqs),'responses':len(responses),'attempts':len(attempts),'meters':len(meters),
      'attempt_ids_unique':len({x['attempt_id'] for x in attempts})==len(attempts),
      'attempt_meter_record_ids_match':all(x['meter_record_id'] and meters_by_attempt.get(x['attempt_id'],{}).get('record_id')==x['meter_record_id'] for x in attempts),
      'meter_attempt_ids_equal_attempt_ids':{x.get('background_attempt_id') for x in meters}=={x['attempt_id'] for x in attempts},
      'all_attempts_metered':all(x['state']=='metered' for x in attempts),
      'request_fingerprint_exact_matches':len(triple),'unmatched_requests':unmatched,'ambiguous_requests':ambiguous,
      'all_attempts_linked_once':len(used)==len(attempts)==len(triple),'mapping':triple}

    # Reconciliation contradiction across exact request contract, exchange ledger, audit and gen34 durable state.
    rid='req-0039-model_directive-ed097a32'; attempt_id='bgattempt_1d6735f46f05508149948ea5a7de5b01'
    arow=next(x for x in attempts if x['attempt_id']==attempt_id)
    audit=[json.loads(x) for x in (r/'audit.jsonl').read_text().splitlines() if x.strip()]
    reconcile=[x for x in audit if x.get('event')=='operator_reconcile_not_submitted' and x.get('detail',{}).get('attempt_id')==attempt_id]
    logs=r/'evidence/incident_2026-09-29_remote_auth_and_indoubt'
    g34db=next((r/'generations/000034/world').glob('*.sqlite'))
    c34=openro(g34db); row34=c34.execute('select state,reconciliation_evidence from background_model_attempts where attempt_id=?',(attempt_id,)).fetchone(); c34.close()
    ledger=[json.loads(x) for x in (r/'exchange/ledger.jsonl').read_text().splitlines() if x.strip()]
    req39events=[x for x in ledger if x.get('request_id')==rid]
    out['req0039_reconciliation']={
      'attempt_final_state':arow['state'],'attempt_final_reconciliation_evidence':arow['reconciliation_evidence'],
      'generation34_state':dict(row34) if row34 else None,'operator_reconcile_audit':reconcile,
      'exchange_events':[{'seq':x['seq'],'event':x['event'],'wall_clock':x['wall_clock'],'response_sha256':x['response_sha256']} for x in req39events],
      'semantic_dispatch_occurred':any(x['event']=='request_published' for x in req39events),
      'response_sha256':sha((r/'exchange/responses'/f'{rid}.json').read_bytes()),
      'process_death_log_present':(logs/'due20_first_attempt_response_timeout.log').exists() and (logs/'due20_second_attempt_indoubt_crash.log').exists(),
      'operator_evidence_path':str(a.operator_evidence.resolve()),
      'operator_evidence_sha256':sha(a.operator_evidence.read_bytes()),
      'operator_evidence_explicitly_says_operator_published_req0039_round0':('operator published the round-0 resident response' in a.operator_evidence.read_text(errors='replace').lower() and rid in a.operator_evidence.read_text(errors='replace')),
      'operator_evidence_explicitly_says_process_death_preceded_response':('after process death' in a.operator_evidence.read_text(errors='replace').lower() or 'post-mortem' in a.operator_evidence.read_text(errors='replace').lower())}

    # Durable world chronology, unique-operation guards, task/evidence status and wake/review closure.
    revs=[dict(x) for x in db.execute('select object_id,revision,object_type,subject_id,world_revision,learned_at,recorded_at,payload_json,revision_kind from object_revisions order by world_revision,object_id,revision')]
    additions=[]
    for x in revs:
        if x['world_revision']>=39:
            p=json.loads(x['payload_json'])
            if x['object_type'] in ('task','claim','experience','operation_experience','wake','observation','dependency','evidence_set'):
                # Keep evidence payloads compact but preserve semantic content for IA review.
                additions.append({'world_revision':x['world_revision'],'type':x['object_type'],'object_id':x['object_id'],'revision':x['revision'],'revision_kind':x['revision_kind'],'created_by':p.get('created_by'),'status':p.get('status'),'state':p.get('state'),'title':p.get('title'),'name':p.get('name'),'value':p.get('value'),'statement':p.get('statement'),'content':p.get('content'),'result_summary':p.get('result_summary'),'evidence_refs':p.get('evidence_refs'),'source_refs':p.get('source_refs'),'task_state_history':p.get('metadata',{}).get('task_state_history')})
    ops=[dict(x) for x in db.execute('select * from operations')]
    commits=[dict(x) for x in db.execute('select * from world_commits order by world_revision')]
    idem=[dict(x) for x in db.execute('select * from idempotency_records')]
    wakes=defaultdict(list)
    for x in revs:
        if x['object_type']=='wake': wakes[x['object_id']].append(json.loads(x['payload_json']))
    out['world_semantics_and_duplicate_scan']={
      'world_revision':db.execute("select value from world_meta where key='world_revision'").fetchone()[0],
      'world_commit_count':len(commits),'world_commit_revisions_contiguous':[x['world_revision'] for x in commits]==list(range(1,len(commits)+1)),
      'operations_count':len(ops),'operation_status_counts':dict(Counter(x['status'] for x in ops)),'operation_errors':sum(bool(x['error_code'] or x['error_message']) for x in ops),
      'duplicate_operation_ids':len(ops)-len({x['operation_id'] for x in ops}),
      'duplicate_idempotency_keys':len(idem)-len({x['idempotency_key'] for x in idem}),
      'objects_added_world39_66':additions,
      'final_wake_objects':{k:{'revisions':len(v),'latest_state':v[-1].get('state'),'latest_status':v[-1].get('status'),'created_by':v[0].get('created_by')} for k,v in wakes.items()},
      'operation_experience_objects':[x for x in additions if x['type']=='operation_experience'],
      'reconciliation_wake_id':arow['work_id']}

    # Cursor order and the no-reveal freeze; verify per-cursor records are strictly ordered.
    audit_reveals=[x for x in audit if x.get('event')=='cursor_revealed']
    audit_acks=[x for x in audit if x.get('event')=='cursor_acked']
    out['cursor_chronology']={'reveals':[x.get('detail',{}).get('event_id') for x in audit_reveals if 14<=x.get('detail',{}).get('sequence',0)<=22],
      'acks':[x.get('detail',{}).get('event_id') for x in audit_acks if 14<=x.get('detail',{}).get('sequence',0)<=22],
      'cursor23_reveal_count':sum(x.get('detail',{}).get('event_id')=='c15rcc-023' for x in audit_reveals),
      'unique_reveal_ids_14_22':len({x.get('detail',{}).get('event_id') for x in audit_reveals if 14<=x.get('detail',{}).get('sequence',0)<=22})==9}

    # Corruption-detector adversarial self-test modifies only a temporary copy.
    sample=gen1/'exchange/ledger.jsonl'; expected=m1['artifacts']['exchange/ledger.jsonl']; original=sample.read_bytes()
    with tempfile.TemporaryDirectory(prefix='ia-corruption-probe-') as td:
        p=Path(td)/'ledger.jsonl'; mutated=bytearray(original); mutated[len(mutated)//2]^=1; p.write_bytes(mutated)
        actual=sha(p.read_bytes()); out['generation_corruption_probe']={'source_artifact_sha256':sha(original),'manifest_expected_sha256':expected,'temporary_copy_sha256_after_bit_flip':actual,'tampering_detected':actual!=expected,'authoritative_artifact_modified':sha(sample.read_bytes())!=expected}

    db.close()
    text=json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+'\n'
    if a.output: a.output.write_text(text,encoding='utf-8')
    else: print(text)
if __name__=='__main__': main()
