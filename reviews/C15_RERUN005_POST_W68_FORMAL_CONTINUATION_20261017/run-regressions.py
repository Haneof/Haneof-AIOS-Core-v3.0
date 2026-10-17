import os,pathlib,shutil,subprocess as sp,json,time,hashlib,stat
E=pathlib.Path('/workspaces/c15-w67-continuation-20261017T0830Z');S=E/'candidate';H=S/'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness';P='/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python'
os.umask(0o022)
O=S/'reviews/POST_W68_ORIGINAL38_UNMODIFIED';old=pathlib.Path('/workspaces/window61-evidence-BeuoJ6pm/regression-evidence/original38-source')
pins=json.loads((S/'reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66/ORIGINAL38_SOURCE_SHA256.json').read_text());O.mkdir()
for name,digest in pins.items():
 data=(old/name).read_bytes();assert hashlib.sha256(data).hexdigest()==digest; (O/name).write_bytes(data)
(E/'original38-source-sha256.json').write_text(json.dumps(pins,indent=2))
m=json.loads((H/'IDENTITY.json').read_text());provision=[]
for group,root in [('harness',H),('core',S/'src/aios_core'),('c15',S/'tools/c15_persistence')]:
 for kind,entries in [('directory_modes',m['directory_modes'][group]),('file_modes',m['file_modes'][group])]:
  for rel,mode in entries.items():
   p=root/rel;before=stat.S_IMODE(p.stat().st_mode);digest=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None;p.chmod(mode)
   if digest:assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
   provision.append({'path':str(p.relative_to(S)),'before':before,'after':mode,'bytes_unchanged':True})
(E/'declared-mode-materialization.json').write_text(json.dumps(provision,indent=2))
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',APPROVED53_PYTHON=P,PYTHONPATH=os.pathsep.join(map(str,[H,S/'src',S/'tools',O])))
result=[]
for name,paths in [('original38',[str(O)]),('window55',['reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW55/tests']),('window57',['reviews/C15_RERUN005_FORMAL_GATE_CORRECTIVE_WINDOW57/test_delivery.py','reviews/C15_RERUN005_FORMAL_GATE_CORRECTIVE_WINDOW57/test_publisher_contract.py'])]:
 a=[P,'-B','-m','pytest','-vv','-p','no:cacheprovider','--basetemp',str(E/(name+'-tmp')),'--junitxml='+str(E/(name+'.xml')),*paths];t=time.time()
 with (E/(name+'.stdout')).open('w') as out,(E/(name+'.stderr')).open('w') as err:
  try:r=sp.run(a,cwd=S,env=env,stdout=out,stderr=err,start_new_session=True,timeout=900);rc=r.returncode
  except sp.TimeoutExpired:rc=124
 result.append({'suite':name,'argv':a,'cwd':str(S),'returncode':rc,'seconds':time.time()-t,'start_new_session':True,'APPROVED53_PYTHON':P,'PYTHONPATH':env['PYTHONPATH']});(E/(name+'.exit')).write_text(str(rc)+'\n');(E/'regression-commands.json').write_text(json.dumps(result,indent=2));print(name,rc,flush=True)
(E/'candidate-after.status').write_text(sp.run(['git','status','--porcelain=v1'],cwd=S,capture_output=True,text=True).stdout)
