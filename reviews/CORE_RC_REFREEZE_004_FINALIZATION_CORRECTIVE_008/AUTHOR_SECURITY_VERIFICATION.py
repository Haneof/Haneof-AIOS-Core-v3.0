import os, re, json, subprocess, tempfile, hashlib
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
os.chdir(ROOT)
BASE='9eba4710e3cd841650191cb89f2126ca5c5b11c3'
NS=Path('reviews/CORE_RC_REFREEZE_004_FINALIZATION_CORRECTIVE_008')
NS.mkdir(parents=True,exist_ok=True); (NS/'raw').mkdir(exist_ok=True)
WF='.github/workflows/core-rc-refreeze-004-formal-gate.yml'
gold=subprocess.check_output(['git','show','39f4e25a2a0adb339b08421a7fe4b4937d298392:'+WF],text=True)
text=Path(WF).read_text(); data=yaml.safe_load(text); jobs=data['jobs']
def git(*args,input=None,env=None):
    return subprocess.check_output(['git',*args],input=input,text=True,env=env).strip()
def step(name):
    return next(s['run'] for s in jobs['rc004-freeze-gate']['steps'] if s['name']==name)
def execute(script,cwd=ROOT,extra=None):
    return subprocess.run(['bash','-c',script],cwd=cwd,env={**os.environ,**(extra or {})},capture_output=True,text=True)
def record(path,result):
    (NS/path).write_text(result.stdout+result.stderr+f'\nEXIT={result.returncode}\n')
    assert result.returncode==0,(path,result.stdout,result.stderr)

git('add',WF)
tree=git('write-tree'); temp_commit=git('commit-tree',tree,'-p',BASE,input='author temporary control candidate\n')
trust=step('Historical C003 Probe Trust-Root Identity Gate')
scopeblock=step('Exact-head, frozen identity, post-integration drift, and candidate scope')
scope=scopeblock[scopeblock.index('base="'):scopeblock.index('          {') if '          {' in scopeblock else scopeblock.index('\n{\n')]
# Use the exact candidate-scope shell, with only its baseline ref pointing to the accepted commit.
scope=scope.replace('refs/remotes/rc004/main',BASE)
reports=[]
with tempfile.TemporaryDirectory(prefix='w46-author-') as tmp:
    wt=Path(tmp)/'candidate'; git('worktree','add','--detach',str(wt),temp_commit)
    try:
        env={'ACCEPTED_RELEASE_BASELINE':BASE,'GITHUB_WORKSPACE':str(wt),'OUT':str(Path(tmp))}
        green=execute(trust,wt,env); assert green.returncode==0,green.stderr
        source=wt/NS/'ci-output/raw/C003_TRUST_ROOT_BLOBS.txt'
        (NS/'raw/C003_TRUST_ROOT_BLOBS.txt').write_bytes(source.read_bytes())
        sg=execute('set -euo pipefail\n'+scope,wt,env); assert sg.returncode==0,sg.stdout+sg.stderr
        reports += ['GREEN unchanged historical C003 scope exit='+str(sg.returncode),'GREEN trust-root exit='+str(green.returncode),green.stdout]
        probe=wt/'reviews/CORE_RC_REFREEZE_004_CORRECTIVE_003/probes/terminal_protected_drift_guard.sh'
        probe.write_text(probe.read_text()+'\n# local author negative identity control\n')
        git('-C',str(wt),'add',str(probe))
        mt=git('-C',str(wt),'write-tree'); mc=git('commit-tree',mt,'-p',BASE,input='local only C003 identity mutation\n')
        git('-C',str(wt),'reset','--hard',mc)
        red=execute(trust,wt,env); sr=execute('set -euo pipefail\n'+scope,wt,env)
        assert red.returncode!=0 and 'C003_TRUST_ROOT_BLOB_MISMATCH' in red.stderr
        assert sr.returncode!=0 and 'RC004_CANDIDATE_SCOPE_VIOLATION' in sr.stdout
        reports += ['RED scope exit='+str(sr.returncode),sr.stdout,'RED trust-root exit='+str(red.returncode),red.stdout,red.stderr]
    finally:
        git('worktree','remove','--force',str(wt))
first=text.index('bash "$GITHUB_WORKSPACE/reviews/CORE_RC_REFREEZE_004_CORRECTIVE_003/')
assert text.index('      - name: Historical C003 Probe Trust-Root Identity Gate')<first
reports += ['TRUST_ROOT_PRECEDES_FIRST_C003_EXECUTION=PASS','IA45_BLK001_AUTHOR_CONTROLS=PASS']
(NS/'IA45_BLK001_RED_GREEN.txt').write_text('\n'.join(reports)+'\n')

old=yaml.safe_load(gold)['jobs']; checks=[]
oldif=old['rc004-freeze-gate']['if']
assert "github.event_name == 'push'" in oldif and "[W30-FINAL-FORMAL]" in oldif
# Evaluate the exact old expression in an isolated boolean expression interpreter.
def condition(expr,event,message):
    expr=expr.removeprefix('${{').removesuffix('}}').strip()
    expr=expr.replace('github.event_name',repr(event)).replace('github.event.head_commit.message',repr(message))
    expr=expr.replace('||',' or ').replace('&&',' and ')
    return eval(expr,{'__builtins__':{},'startsWith':lambda a,b:a.startswith(b)})
assert condition(oldif,'push','[W30-FINAL-FORMAL] local only')
checks += ['OLD_FREEZE_CONDITION='+oldif,'OLD_PUSH_FORMAL_CONDITION_EVALUATES=TRUE (local expression only)']
oldseal='\n'.join(s.get('run','') for s in old['rc004-whole-run-identity-seal']['steps'])
assert not re.search(r'\.(event)\b',oldseal)
checks += ['OLD_FORMAL_SEAL_RUN_EVENT_CHECK=ABSENT (parsed exact shell)']
gateif=jobs['rc004-freeze-gate']['if']
assert gateif=="${{ github.event_name == 'workflow_dispatch' }}"
for msg in ('[W30-FINAL-FORMAL] local only','[W30-POSTREAD-CONTROL] A','ordinary'):
    assert not condition(gateif,'push',msg)
assert condition(gateif,'workflow_dispatch','')
publisher=jobs['rc004-mandatory-pin-publisher']['steps'][0]['run']
assert 'test "$GITHUB_EVENT_NAME" = "workflow_dispatch"' in publisher
assert 'echo "- event: $GITHUB_EVENT_NAME"' in publisher
# Historical exact-shell mocks, with explicit authoritative event, plus fail-closed push case.
import importlib.util, sys
sys.dont_write_bytecode = True
spec=importlib.util.spec_from_file_location('matrix',ROOT/'reviews/CORE_RC_REFREEZE_004_CORRECTIVE_003/probes/publisher_fault_matrix.py')
matrix=importlib.util.module_from_spec(spec); spec.loader.exec_module(matrix)
for event,expected in [('push',False),('workflow_dispatch',True)]:
    os.environ['GITHUB_EVENT_NAME']=event
    rc,out=matrix.run_case(publisher,'http','201')
    assert (rc==0)==expected,(event,rc,out)
    checks += [f'FORMAL_PUBLISHER_EXACT_SHELL event={event} exit={rc}',out]
os.environ['GITHUB_EVENT_NAME']='workflow_dispatch'
seal=jobs['rc004-whole-run-identity-seal']['steps'][0]['run']
assert '.event // empty' in seal and 'FINAL_SEAL_EVENT_NOT_WORKFLOW_DISPATCH' in seal
assert 'grep -Fxq -- "- event: workflow_dispatch"' in seal
assert 'grep -Fxq -- "- gate_kind: formal"' in seal
checks += ['FORMAL_GATE_WORKFLOW_DISPATCH_ONLY=PASS','FORMAL_PUBLISHER_EVENT_BOUND=PASS','FORMAL_PIN_EVENT_FIELD=PASS','FORMAL_SEAL_RUN_EVENT=PASS','FORMAL_SEAL_PIN_EVENT_AND_KIND=PASS']
# Execute exact run event check and exact pin checks against sandbox fixtures.
event_line=next(l for l in seal.splitlines() if "'.event // empty'" in l)
pin_start=seal.index('grep -Fxq -- "- event:')
pin_end=seal.index('          grep -Fq -- "- run_id:') if '          grep -Fq -- "- run_id:' in seal else seal.index('grep -Fq -- "- run_id:')
pin_checks=seal[pin_start:pin_end]
with tempfile.TemporaryDirectory(prefix='w46-event-') as tmp:
    f=Path(tmp)/'run.json'
    for event in ('push','workflow_dispatch',None):
        f.write_text(json.dumps({'event':event}))
        r=execute('set -euo pipefail\n'+event_line,extra={'run_json':str(f)})
        assert (r.returncode==0)==(event=='workflow_dispatch')
        checks.append(f'EXACT_SEAL_EVENT_CONTROL event={event} exit={r.returncode}')
    for body,expected in [('- event: workflow_dispatch\n- gate_kind: formal',True),('- event: push\n- gate_kind: formal',False),('- gate_kind: formal',False),('- event: workflow_dispatch\n- gate_kind: POSTREAD_CONTROL_ONLY',False)]:
        r=execute('set -euo pipefail\n'+pin_checks,extra={'body':body})
        assert (r.returncode==0)==expected,(body,r.stderr)
        checks.append(f'EXACT_PIN_CONTROL body={body!r} exit={r.returncode}')
    ledger=jobs['rc004-whole-run-identity-seal']['steps'][1]['run']
    query=next(l for l in ledger.splitlines() if l.startswith('self_count='))
    assert '.event == "workflow_dispatch"' in query
    for event,expected in [('push','0'),('workflow_dispatch','1')]:
        f.write_text(json.dumps({'workflow_runs':[{'id':1,'head_sha':'abc','head_branch':'branch','run_attempt':1,'event':event}]}))
        r=execute('set -euo pipefail\n'+query+'\nprintf "%s" "$self_count"',extra={'runs_json':str(f),'GITHUB_RUN_ID':'1','GITHUB_SHA':'abc','CANONICAL_CORRECTIVE_BRANCH':'branch','GITHUB_RUN_ATTEMPT':'1'})
        assert r.returncode==0 and r.stdout==expected
        checks.append(f'EXACT_LEDGER_SELF_MATCH event={event} count={r.stdout}')
checks += ['SUCCESSOR_SELF_MATCH_EVENT_BOUND=PASS','REMOTE_MARKER_PUSH=NONE','IA45_BLK002_AUTHOR_CONTROLS=PASS']
(NS/'IA45_BLK002_RED_GREEN.txt').write_text('\n'.join(checks)+'\n')
for file,args,env in [
    ('WORKFLOW_SECURITY_STATIC.txt',['python','reviews/CORE_RC_REFREEZE_004_CORRECTIVE_003/probes/workflow_security_static_probe.py',WF],{}),
    ('PUBLISHER_FAULT_MATRIX.txt',['python','reviews/CORE_RC_REFREEZE_004_CORRECTIVE_003/probes/publisher_fault_matrix.py',WF],{'GITHUB_EVENT_NAME':'workflow_dispatch'}),
    ('TERMINAL_PROTECTED_DRIFT_CONTROLS.txt',['python','reviews/CORE_RC_REFREEZE_004_CORRECTIVE_003/probes/terminal_protected_drift_controls.py'],{}),
]:
    r=subprocess.run(args,capture_output=True,text=True,env={**os.environ,**env})
    record('raw/'+file,r)
print('AUTHOR_SECURITY_CONTROLS=PASS')
