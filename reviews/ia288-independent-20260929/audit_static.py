import pathlib, hashlib,json,subprocess,sys
root=pathlib.Path('/home/user/.cache/ia288/candidate')
repo=pathlib.Path('/home/user/Haneof-AIOS-Core-v3.0')
prefix=pathlib.Path('reviews/internal_habitation/c15-rcc/v1')
p=root/prefix/'operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP'
q=root/prefix/'operator_prep_corrective_002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
out={'head':git('show','-s','--format=%H %T %P','771b200'),'h1':git('show','-s','--format=%H %T %P','63c972a'),
'lineage':git('log','--format=%H %P %s','b7c9e850..771b200').splitlines(), 'checksums':{}}
for base, sums in ((p,p/'evidence/SHA256SUMS'),(q,q/'SHA256SUMS')):
    rows=[]; covered=set()
    for line in sums.read_text().splitlines():
        digest,name=line.split('  ',1); covered.add(name)
        rows.append({'path':name,'expected':digest,'actual':sha(base/name),'ok':sha(base/name)==digest})
    allfiles={str(f.relative_to(base)) for f in base.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
    out['checksums'][base.name]={'rows':rows,'uncovered':sorted(allfiles-covered-{str(sums.relative_to(base))})}
out['packet_sha256']=sha(p/'RESIDENT_SAFE_LAUNCH_PACKET.json')
out['wheel_lock_sha256']=sha(p/'bootstrap/PYTHON_WHEEL_LOCK.json')
out['manifests']={}
for scope in ('src/aios_core','tests'):
    rows=[]
    for path in sorted((repo/scope).rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            data=path.read_bytes(); rows.append({'path':path.relative_to(repo/scope).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)})
    digest=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    out['manifests'][scope]={'file_count':len(rows),'sha256':digest}
out['source_changes_h2']=[x for x in git('diff','--name-only','63c972a','771b200').splitlines() if '/harness/' in x or '/bootstrap/' in x or '/probes' in x]
out['author_probe_source_diff']=subprocess.run(['diff','-ru',str(q/'probes/tests'),str(q/'probes_v2/tests')],capture_output=True,text=True).stdout
out['q_manifest_artifacts']={name:sha(root/name)==digest for name,digest in json.loads((q/'FREEZE_MANIFEST.json').read_text())['artifacts'].items()}
print(json.dumps(out,indent=2))
