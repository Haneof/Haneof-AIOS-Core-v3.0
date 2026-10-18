"""Read-only exact-candidate audit; Python stdlib only. Never executes Resident code."""
import sys,json,hashlib,sqlite3,pathlib,subprocess,re,platform
R=pathlib.Path(sys.argv[1]); H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def emit(k,v): print(json.dumps({'check':k,'result':v},ensure_ascii=False,default=str))
def load(p): return json.loads((R/p).read_text())
def git(*a): return subprocess.check_output(['git',*a],text=True).strip()
emit('environment',{'python':sys.version,'sqlite':sqlite3.sqlite_version,'platform':platform.platform()})
emit('pins',{x:git('rev-parse',x) for x in ['origin/main','HEAD','f251e9c^','f251e9c^{tree}','f20f2edf:src/aios_core','f20f2edf:tests']})
files=git('diff','--name-only','f251e9c^','f251e9c').splitlines(); emit('scope',{'count':len(files),'outside':[f for f in files if not f.startswith('reviews/internal_habitation/c15-rcc/v1/resident/runs/a004-27bb1fb3da404f4d/')]})
manifest=[]
for line in (R/'MANIFEST.sha256').read_text().splitlines():
 digest,name=line.split(None,1); actual=H(R/name); manifest.append({'path':name,'actual':actual,'match':digest==actual})
emit('manifest',manifest)
emit('manifest_coverage',sorted(set(str(p.relative_to(R)) for p in R.rglob('*') if p.is_file())-{x['path'] for x in manifest}))
f=load('FREEZE_MANIFEST.json'); emit('freeze_artifacts',[{'path':v['path'],'match':v['sha256']=='sha256:'+H(R/v['path'])} for v in f['artifacts'].values()])
w=sqlite3.connect(f'file:{R/"world.db"}?mode=ro&immutable=1',uri=True);w.row_factory=sqlite3.Row
i=sqlite3.connect(f'file:{R/"index.db"}?mode=ro&immutable=1',uri=True)
emit('integrity',{'world':w.execute('pragma integrity_check').fetchall()[0][0],'index':i.execute('pragma integrity_check').fetchall()[0][0],'world_revision':w.execute('select max(world_revision) from world_commits').fetchone()[0],'index_meta':i.execute('select * from search_meta').fetchall()})
rows=[dict(x) for x in w.execute('select * from object_revisions order by world_revision')]
objects=[json.loads(x['payload_json']) for x in rows]
emit('world_lineage',[{k:v for k,v in x.items() if k!='payload_json'} for x in rows])
emit('durable_objects',objects)
for table in ['runtime_turn_executions','background_model_attempts','metering_records','background_model_request_bindings','background_model_response_receipts']:
 emit(table,[dict(x) for x in w.execute('select * from '+table)])
s=load('release-state.json');emit('release_boundary',{k:v for k,v in s.items() if k!='receipts'})
acks=[]
for receipt in s['receipts']:
 seq=receipt['sequence']; obj=next((x for x in rows if x['object_id']==receipt['ingest_object_id'] and x['revision']==receipt['ingest_revision']),None)
 event=load(f'events/cursor_{seq:02}_event.json'); cp=load(f'checkpoints/checkpoint_cursor_{seq:02}.json'); fc=f['cursors'][seq-1]
 canonical=lambda x:'sha256:'+hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
 acks.append({'seq':seq,'durable_revision_matches':obj is not None and obj['world_revision']==receipt['ingest_world_revision'],'receipt':receipt,'event':event,'payload_hash':canonical(event.get('payload')),'step_hash_match':fc['step_result_sha256']=='sha256:'+H(R/f'step_{seq:02}_result.json'),'checkpoint_hash_match':fc['checkpoint_sha256']=='sha256:'+H(R/f'checkpoints/checkpoint_cursor_{seq:02}.json')})
 emit('step',cp)
emit('acks',acks)
chain=[json.loads(x) for x in (R/'logs/decision_chain.jsonl').read_text().splitlines()]
starts=[]
for line in (R/'logs/runner.log').read_text().splitlines():
 m=re.search(r'^(\S+) step cursor=(\d+) start',line)
 if m: starts.append((m[1],int(m[2])))
future=[];decisions=[]
for p in sorted((R/'decision_requests').glob('*.json')):
 q=json.loads(p.read_text());resp=load('decision_responses/'+p.name); current=max((seq for t,seq in starts if t<=q['created_at']),default=0)
 found=[]
 for n in range(current+1,14):
  if f'c15rcc-{n:03}' in p.read_text(): found.append(n)
 if found: future.append({'request':p.name,'cursor':current,'later_ids':found})
 records=[x for x in chain if x['request_id']==q['request_id']]
 decisions.append({'request':p.name,'cursor':current,'created_at':q['created_at'],'response':resp,'chain':records,'chain_hash_checks':[(x['event'],x.get('request_sha256',x.get('response_sha256'))=='sha256:'+H(p if x['event']=='request_written' else R/'decision_responses'/p.name)) for x in records]})
emit('decision_audit',decisions);emit('later_event_id_hits',future)
emit('contamination_lexical_hits',[str(p.relative_to(R)) for p in list((R/'decision_requests').glob('*'))+list((R/'decision_responses').glob('*')) if re.search(r'A-00[123]|a00[123]-|evaluator|expected.answer',p.read_text(),re.I)])
rec=load('receipts/cursor_10_turn_recovery.json'); resp=load('decision_responses/req-0032-model_directive-9002a5bb.json');reply=resp['directive']['response']
emit('recovery10',{'response_digest_match':H(R/'decision_responses/req-0032-model_directive-9002a5bb.json')==rec['response_file_sha256'],'reply_digest_match':hashlib.sha256(reply.encode()).hexdigest()==rec['assistant_reply_sha256'],'assistant_objects':[o for o in objects if o.get('object_id')==rec['assistant_observation_id']],'response_chain_entries':[x for x in chain if x['request_id'].startswith('req-0032')]})
emit('canonical_user_counts',[(x['object_id'],sum(o.get('object_id')==x['object_id'] for o in objects)) for x in rows if x['object_id'].startswith('obs_conv_user_')])
emit('all_file_hashes',{str(p.relative_to(R)):H(p) for p in sorted(R.rglob('*')) if p.is_file()})
