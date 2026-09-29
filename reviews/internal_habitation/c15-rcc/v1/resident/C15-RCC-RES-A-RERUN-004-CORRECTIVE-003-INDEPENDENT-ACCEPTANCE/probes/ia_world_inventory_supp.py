# World inventory + provenance probe (frozen before first run, see PROBE_FREEZE_supp2.sha256)
import json,subprocess,sqlite3,tempfile,os,re,collections
E="reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003/run"
b=lambda p: subprocess.check_output(['git','-C',os.path.expanduser('~/repo'),'show','317316299c332d82e0cbd0431b5c7d50f391bc17:'+E+'/'+p])
td=tempfile.mkdtemp();w=td+'/w';open(w,'wb').write(b('world/c15-res-a-c003.world.sqlite'));c=sqlite3.connect(w)
rows=c.execute('select object_id,revision,object_type,world_revision,learned_at,recorded_at,payload_json,revision_kind from object_revisions order by world_revision').fetchall()
have={(r[0],r[1]):r for r in rows}; inv=collections.Counter(r[2] for r in rows); errs=[]; LIMIT="2026-11-06T19:10:00"
for r in rows:
    if r[4] and str(r[4])[:19]>LIMIT and not str(r[4]).endswith('-08:00'): errs.append(['learned_after_cursor13',r[0],r[4]])
    p=json.loads(r[6])
    for m in re.finditer(r'"object_id":\s*"([^"]+)",\s*"revision":\s*(\d+)',json.dumps(p,sort_keys=True)):
        ref=(m.group(1),int(m.group(2)))
        if ref not in have: errs.append(['dangling',r[0],ref])
        elif have[ref][3]>r[3]: errs.append(['ref_to_later_revision',r[0],ref])
out={'inventory':inv,'revisions':len(rows),'errors':errs,'objects':[[r[0],r[1],r[2],r[3],r[4],r[7],r[6][:700]] for r in rows if not r[0].startswith('obs_')]}
print(json.dumps(out,ensure_ascii=False,indent=0,default=str))
