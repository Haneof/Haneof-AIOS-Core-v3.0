import os,pathlib,shutil,subprocess as sp,json
E=pathlib.Path(os.environ['W67']);S=E/'frozen-parent';H=S/os.environ['H67'];O=S/'reviews/WINDOW67_ORIGINAL38_UNMODIFIED';shutil.copytree('/workspaces/window61-evidence-BeuoJ6pm/regression-evidence/original38-source',O,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'));os.umask(0o022)
a=[os.environ['PY67'],'-B','-m','pytest','-vv','-p','no:cacheprovider','--basetemp',str(E/'parent-original38-tmp'),'--junitxml='+str(E/'parent-original38.xml'),str(O)]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join(map(str,[H,S/'src',S/'tools',O])))
with (E/'parent-original38.stdout').open('w') as out,(E/'parent-original38.stderr').open('w') as err:p=sp.run(a,cwd=S,env=env,stdout=out,stderr=err,start_new_session=True,timeout=900)
(E/'parent-original38.exit').write_text(str(p.returncode));(E/'parent-command.json').write_text(json.dumps({'argv':a,'returncode':p.returncode,'head':'9d3b19b0e7bf090e5d472d9781b9156f73ea2088'},indent=2))
