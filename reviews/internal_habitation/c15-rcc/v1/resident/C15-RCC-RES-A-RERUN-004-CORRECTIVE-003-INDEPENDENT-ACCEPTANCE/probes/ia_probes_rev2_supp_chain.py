# Supplementary chain probe (written after rev2 freeze; frozen separately in PROBE_FREEZE_supp.sha256 before its first run)
import json,subprocess,sqlite3,tempfile,os,sys
E="reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003/run"
def b(p): return subprocess.check_output(['git','-C',os.path.expanduser('~/repo'),'show','317316299c332d82e0cbd0431b5c7d50f391bc17:'+E+'/'+p])
fx=[e for e in json.loads(subprocess.check_output(['git','-C',os.path.expanduser('~/repo'),'show','origin/main:reviews/internal_habitation/c15-rcc/v1/fixture/sealed_fixture.json']))['events'] if e['phase']=='A']
rs=json.loads(b('release-state.json'));rc=rs['receipts']
td=tempfile.mkdtemp();w=td+'/w';open(w,'wb').write(b('world/c15-res-a-c003.world.sqlite'))
c=sqlite3.connect(w);cols={t:[r[1] for r in c.execute(f'pragma table_info("{t}")')] for (t,) in c.execute("select name from sqlite_master where type='table'")}
print(json.dumps({t:cols[t] for t in ('object_revisions','world_commits','world_meta','runtime_turn_executions')}))
errs=[];prevwr=0;turn=0
for k in range(1,14):
    ing=json.loads(b(f'evidence/cursor_{k:02d}.ingest_receipt.json'));ack=json.loads(b(f'evidence/cursor_{k:02d}.ack_receipt.json'));r=rc[k-1];e=fx[k-1]
    if r['sequence']!=k or r['event_id']!=e['event_id'] or r['occurred_at']!=e['occurred_at']: errs.append(f'{k} receipt id')
    if ack['ingest_ref']!=ing['ingest_ref'] or r['ingest_ref']!=ing['ingest_ref']: errs.append(f'{k} ackref')
    if ack['ingest_world_revision']!=ing['world_revision'] or ing['world_revision']<=prevwr: errs.append(f'{k} wr')
    prevwr=ing['world_revision']
    oid,rev=ing['ingest_ref'].split('@')
    row=c.execute('select * from object_revisions where object_id=? and revision=?',(oid,int(rev))).fetchone()
    if not row: errs.append(f'{k} ref unresolved')
    else:
        s=json.dumps(row,ensure_ascii=False,default=str)
        if e['resident_visible_payload'] not in s and e['resident_visible_payload'].replace('"','\\"') not in s: errs.append(f'{k} payload not in observation')
    want='user' if e['source_class']=='USER' else 'platform'
    if r['ingest_source_class']!=want: errs.append(f'{k} class')
    if e['source_class']=='USER':
        turn+=1
        if r.get('turn_index')!=turn or r.get('session_id')!='sess-resident-a-c003-7089564bdf1d' or r['binding_mode']!='canonical_user_turn': errs.append(f'{k} user binding')
        tr=b(f'evidence/cursor_{k:02d}.turn_result.json').decode()
        if oid not in tr: errs.append(f'{k} turn does not reference canonical obs')
print('receipts',len(rc),'last',rs['last_acked_sequence'],rs['next_sequence'],rs['pending_reveal'])
print('world_commits',c.execute('select count(*),max(rowid) from world_commits').fetchone())
print('meta',c.execute('select * from world_meta').fetchall())
# user observations count
n=c.execute("select count(distinct object_id) from object_revisions where object_id like 'obs_conv_user%'").fetchone()
print('distinct user obs',n)
print('ERRORS',errs)
