"""Independent approved-command environment matrix; source frozen before execution."""
import pathlib,shutil,subprocess,os,sys,tempfile,json
REPO=pathlib.Path('/home/user/Haneof-AIOS-Core-v3.0')
PACKAGE=pathlib.Path('/home/user/.cache/ia288/candidate/reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP')
MODES=['default','explicit','missing_git','core_byte','tests_byte','symlink','wrong_core_tree','wrong_tests_tree','foreign_import','wrong_sqlite','wrong_openssl']
if '--collect-only' in sys.argv:
    print('\n'.join(MODES)); sys.exit()
results=[]
for mode in MODES:
    with tempfile.TemporaryDirectory(prefix='ia288-verify-') as tmp:
        root=pathlib.Path(tmp); repo=root/'repo'; repo.mkdir()
        for name in ('.git','src','tests'):
            shutil.copytree(REPO/name,repo/name,ignore=shutil.ignore_patterns('__pycache__'))
        package=repo/'package'; shutil.copytree(PACKAGE,package,ignore=shutil.ignore_patterns('__pycache__'))
        env=dict(os.environ,AIOS_RUNTIME_ROOT='/home/user/.cache/ia288/runtime',PYTHONDONTWRITEBYTECODE='1')
        env.pop('AIOS_REPO_ROOT',None); env.pop('PYTHONPATH',None)
        if mode!='default':env['AIOS_REPO_ROOT']=str(repo)
        if mode=='missing_git':shutil.rmtree(repo/'.git')
        if mode in ('core_byte','tests_byte'):
            path=sorted((repo/('src/aios_core' if mode=='core_byte' else 'tests')).rglob('*.py'))[0]
            path.write_bytes(path.read_bytes()+b'\n')
        if mode=='symlink':
            path=repo/'src/aios_core/__init__.py'; other=root/'original.py'; shutil.copy2(path,other); path.unlink();path.symlink_to(other)
        hook=root/'hook';hook.mkdir()
        injection={'foreign_import':"import sys,types\nm=types.ModuleType('aios_core');m.__file__='/synthetic/foreign/__init__.py';sys.modules['aios_core']=m\n",
            'wrong_sqlite':"import sqlite3\nsqlite3.sqlite_version='0.0.0'\n",'wrong_openssl':"import ssl\nssl.OPENSSL_VERSION='OpenSSL 0.0.0 synthetic'\n"}.get(mode,'')
        if injection:
            (hook/'sitecustomize.py').write_text(injection);env['PYTHONPATH']=str(hook)
        if mode in ('wrong_core_tree','wrong_tests_tree'):
            # Fault injection at Git's tree-query boundary; does not forge an actual commit.
            target='HEAD:src/aios_core' if mode=='wrong_core_tree' else 'HEAD:tests'
            git=shutil.which('git'); wrapper=hook/'git'
            wrapper.write_text('#!/bin/sh\nfor arg in "$@"; do\n if [ "$arg" = "'+target+'" ]; then echo 0000000000000000000000000000000000000000; exit 0; fi\ndone\nexec '+git+' "$@"\n');wrapper.chmod(0o755)
            env['PATH']=str(hook)+':'+env['PATH']
        run=subprocess.run(['bash',str(package/'bootstrap/bootstrap_runtime.sh'),'--verify'],env=env,capture_output=True,text=True,timeout=120)
        expected=mode in ('default','explicit')
        results.append(dict(mode=mode,returncode=run.returncode,expected_success=expected,ok=(run.returncode==0)==expected,stdout=run.stdout,stderr=run.stderr))
print(json.dumps(results,indent=2))
sys.exit(0 if all(r['ok'] for r in results) else 1)
