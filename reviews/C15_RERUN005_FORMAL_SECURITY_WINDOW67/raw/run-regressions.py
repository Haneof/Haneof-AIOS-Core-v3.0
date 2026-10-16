import os,pathlib,shutil,subprocess as sp,json,time
E=pathlib.Path(os.environ['W67']);S=E/'candidate';H=S/os.environ['H67'];P='/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python'
os.umask(0o022)
O=S/'reviews/WINDOW67_ORIGINAL38_UNMODIFIED';shutil.copytree('/workspaces/window61-evidence-BeuoJ6pm/regression-evidence/original38-source',O,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join(map(str,[H,S/'src',S/'tools',O])))
result=[]
for name,paths in [('original38',[str(O)]),('window55',['reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW55/tests']),('window57',['reviews/C15_RERUN005_FORMAL_GATE_CORRECTIVE_WINDOW57/test_delivery.py','reviews/C15_RERUN005_FORMAL_GATE_CORRECTIVE_WINDOW57/test_publisher_contract.py'])]:
 a=[P,'-B','-m','pytest','-vv','-p','no:cacheprovider','--basetemp',str(E/(name+'-tmp')),'--junitxml='+str(E/(name+'.xml')),*paths]; t=time.time()
 with (E/(name+'.stdout')).open('w') as out,(E/(name+'.stderr')).open('w') as err:
  try:r=sp.run(a,cwd=S,env=env,stdout=out,stderr=err,start_new_session=True,timeout=900);rc=r.returncode
  except sp.TimeoutExpired:rc=124
 result.append({'suite':name,'argv':a,'returncode':rc,'seconds':time.time()-t,'controlling_tty':False});(E/(name+'.exit')).write_text(str(rc)+'\n');(E/'regression-commands.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
