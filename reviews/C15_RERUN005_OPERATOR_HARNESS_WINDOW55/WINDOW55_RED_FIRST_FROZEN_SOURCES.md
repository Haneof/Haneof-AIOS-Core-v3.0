# Window 55 — Frozen RED-first source and stdout (operator only)

**NOT AN ACCEPTED FIX.** The three RED attacks are isolated synthetic targets; BLK003 actual approved Core/C15 integration not run. No live Resident.

Source SHA-256 digests computed on the standalone source file bytes.

## `RED_FIRST/attack_exact_check_imports.py`
SHA256: `dce6edc458eb5250b20f073c808899ccb66a98dd3a369d71a955c6afb37aad3c` · bytes: 4967

```python
"""Window55 RED-first — frozen exact PR361 checks.py behavior, synthetic throwaway tree.

The security test is a negative defense proof: native shadow is added without any
manifest-listed .py bytes changing; exact source checks return PASS even after
an unauthorized native extension is executed. This is NOT full Core/C15.
"""
import hashlib, importlib.util, importlib.machinery, json, os
from pathlib import Path
import shutil, subprocess, sys, sysconfig, tempfile

source=Path('/mnt/data/window55/exact_harness/r005/checks.py')
assert sys.version_info[:3]==(3,12,14)
assert hashlib.sha256(source.read_bytes()).hexdigest()=='f5f93a8cf88a3b6b09b38007a231d5d4ba70e521ff2b91aaa7ca1edee9c1cef4'
spec=importlib.util.spec_from_file_location('reviewed_checks',source)
checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def run_one(target):
    with tempfile.TemporaryDirectory(prefix='window55-red-'+target+'-') as temp:
        root=Path(temp);harness=root/'harness';repo=root/'repo'
        (harness/'r005').mkdir(parents=True)
        (repo/'src/aios_core/headless').mkdir(parents=True)
        (repo/'tools/c15_persistence').mkdir(parents=True)
        shutil.copy2(source,harness/'r005/checks.py')
        for rel in ['launch.py','r005/__init__.py','r005/cli.py','r005/safe_runner.py','r005/publisher_service.py','r005/payload.py']:
            p=harness/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'# inert source for synthetic RED\n')
        for rel in ['src/aios_core/__init__.py','src/aios_core/headless/__init__.py','src/aios_core/headless/core.py','tools/c15_persistence/__init__.py']:
            p=repo/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'SOURCE_IS_PINNED=True\n')
        hfiles={str(p.relative_to(harness)):sha(p) for p in harness.rglob('*.py')}
        sfiles={str(p.relative_to(repo)):sha(p) for p in repo.rglob('*.py')}
        identity={'harness_files':hfiles,'source_files':sfiles,'python_sha256':sha(Path(sys.executable).resolve())}
        (harness/'IDENTITY.json').write_text(json.dumps(identity,sort_keys=True))
        identity_sha=sha(harness/'IDENTITY.json')
        checks.verify(harness,repo,identity_sha)
        if target=='harness_checks':
            pkg=harness/'r005';modname='checks';fspath=harness
            csource=r'''#include <Python.h>
static PyObject* verify(PyObject*s,PyObject*a){return PyUnicode_FromString("MALICIOUS_FALSE_PASS");}
static PyObject* loaded_modules(PyObject*s,PyObject*a){return PyUnicode_FromString("MALICIOUS_FALSE_PASS");}
static PyMethodDef methods[]={{"verify",verify,METH_VARARGS,NULL},{"loaded_modules",loaded_modules,METH_VARARGS,NULL},{NULL,NULL,0,NULL}};
static struct PyModuleDef md={PyModuleDef_HEAD_INIT,"checks",NULL,-1,methods};
PyMODINIT_FUNC PyInit_checks(void){return PyModule_Create(&md);}'''
        else:
            pkg=repo/'src/aios_core/headless';modname='core';fspath=repo/'src'
            csource=r'''#include <Python.h>
static PyObject* evil(PyObject*s,PyObject*a){return PyUnicode_FromString("UNAPPROVED_CORE_EXECUTION");}
static PyMethodDef methods[]={{"evil",evil,METH_NOARGS,NULL},{NULL,NULL,0,NULL}};
static struct PyModuleDef md={PyModuleDef_HEAD_INIT,"core",NULL,-1,methods};
PyMODINIT_FUNC PyInit_core(void){return PyModule_Create(&md);}'''
        c=root/'injected.c';c.write_text(csource)
        native=pkg/(modname+importlib.machinery.EXTENSION_SUFFIXES[0])
        subprocess.run(['gcc','-shared','-fPIC','-I'+sysconfig.get_path('include'),'-o',str(native),str(c)],check=True,capture_output=True)
        assert {str(p.relative_to(harness)):sha(p) for p in harness.rglob('*.py')}==hfiles
        assert {str(p.relative_to(repo)):sha(p) for p in repo.rglob('*.py')}==sfiles
        checks.verify(harness,repo,identity_sha)
        for mod in list(sys.modules):
            if mod=='r005' or mod.startswith('r005.') or mod=='aios_core' or mod.startswith('aios_core.'):
                del sys.modules[mod]
        sys.path.insert(0,str(fspath))
        if target=='harness_checks':
            import r005.checks as loaded
            assert loaded.verify(None,None,None)=='MALICIOUS_FALSE_PASS'
        else:
            import aios_core.headless.core as loaded
            assert loaded.evil()=='UNAPPROVED_CORE_EXECUTION'
        assert Path(loaded.__file__).resolve()==native.resolve()
        status=checks.loaded_modules(repo,harness)
        assert status['module_import_identity']=='PASS'
        sys.path.remove(str(fspath))
        return {'attack_target':target,'manifest_py_bytes_unchanged':True,
                'native_imported_and_executed':True,'exact_checks_verify_after_injection':'PASS',
                'exact_checks_loaded_modules_after_native_execution':status['module_import_identity'],
                'result':'SECURITY_DEFENSE_FAIL'}
print(json.dumps([run_one('harness_checks'),run_one('core')],indent=2))
```

## `RED_FIRST/attack_exact_publisher.py`
SHA256: `dbb09302e9a912cf8acfba4e201b71faed1c47d88967a20abd8684ec773935aa` · bytes: 4826

```python
"""Window55 RED-first: run byte-verified exact PR361 Publisher with synthetic stubs.

Tests the real publisher_service.py subprocess IPC registration gate. The Runner
is a separate idle process and does not register; this attacker is same UID.
This does not demonstrate unauthorized semantic response signing or full Core.
"""
import hashlib,json,os
from pathlib import Path
import subprocess,sys,tempfile,time,uuid

APPROVED='/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python'
SOURCE=Path('/mnt/data/window55/exact_harness/r005/publisher_service.py')
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='37506ee7113acc30c02d3dfced92e92d8e73f1e77eca8c081b0af072534f3ac3'
assert sys.version_info[:3]==(3,12,14)

with tempfile.TemporaryDirectory(prefix='window55-exact-publisher-') as d:
    root=Path(d);stubs=root/'stubs';exchange=root/'exchange';channel=root/'channel'
    exchange.mkdir()
    stub_files={
        'r005/__init__.py':'',
        'r005/atomic.py':'''import os
from pathlib import Path
def atomic_write_bytes(path,data):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 q=p.with_name(p.name+'.tmp')
 with open(q,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(q,p)
 fd=os.open(p.parent,os.O_RDONLY);os.fsync(fd);os.close(fd)
''',
        'r005/canonical.py':'''import json
def canonical_json_bytes(o):return json.dumps(o,sort_keys=True,separators=(',',':')).encode()
''',
        'r005/bridge.py':'''class ExchangeBridge:
 def __init__(self,root):self.requests=self
 def payload(self,rid):
  if rid!='req-synthetic-window55':raise ValueError('unexpected id')
  return {'kind':'model_directive','body':{'provenance_binding':{}}}
 def request_sha256(self,rid):
  self.payload(rid);return 'a'*64
''',
        'r005/schema.py':'def parse_model_directive(*a):raise AssertionError("no publish expected")\n',
        'r005/payload.py':'def parse(*a):raise AssertionError("no publish expected")\n',
        'aios_core/__init__.py':'',
        'aios_core/runtime/__init__.py':'',
        'aios_core/runtime/background_attempt.py':'def encode_model_directive(*a):raise AssertionError("no signing expected")\n',
        'aios_core/runtime/late_return.py':'def late_return_message(*a):raise AssertionError("no signing expected")\n',
    }
    for name,contents in stub_files.items():
        path=stubs/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(contents)
    runner=subprocess.Popen(['sleep','20'])
    parent_read,parent_write=os.pipe()
    launch='''import runpy,sys
source,stubs,root,channel,runner,fd=sys.argv[1:]
sys.path.insert(0,stubs)
sys.argv=[source,root,channel,runner,fd]
runpy.run_path(source,run_name='__main__')
'''
    service=subprocess.Popen([APPROVED,'-I','-c',launch,str(SOURCE),str(stubs),str(exchange),str(channel),str(runner.pid),str(parent_read)],pass_fds=(parent_read,),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    os.close(parent_read)
    try:
        limit=time.monotonic()+15
        while not (channel/'ready.json').exists():
            assert service.poll() is None,service.stderr.read()
            assert time.monotonic()<limit,'Publisher startup timeout'
            time.sleep(.03)
        assert runner.poll() is None
        assert runner.pid!=os.getpid()!=service.pid
        cmd={'command':'register','caller_pid':runner.pid,'request_id':'req-synthetic-window55',
             'request_sha256':'a'*64,'context':{'attempt_id':'ATTACKER-ORIGIN-ATTEMPT','relay_id':'ATTACKER-ORIGIN-RELAY'}}
        infile=channel/(uuid.uuid4().hex+'.command.json')
        infile.write_text(json.dumps(cmd,sort_keys=True))
        outfile=infile.with_suffix('.result')
        while not outfile.exists():
            assert service.poll() is None,'Publisher crashed'
            assert time.monotonic()<limit,'Publisher did not respond'
            time.sleep(.01)
        result=json.loads(outfile.read_text())
        assert result['ok'] is True,result
        assert result['result']['registered']=='req-synthetic-window55'
        assert os.geteuid()==os.stat(f'/proc/{runner.pid}').st_uid
        print(json.dumps({'verified_exact_publisher_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'python':sys.version.split()[0], 'attacker_pid':os.getpid(),'runner_pid':runner.pid,
          'service_pid':service.pid,'same_uid':True,'runner_did_not_register':True,
          'forged_context_was_accepted':True,'real_publisher_registration_reply':result,
          'semantic_publishing_tested':False,'result':'SECURITY_DEFENSE_FAIL'},indent=2))
    finally:
        os.close(parent_write)
        service.terminate()
        try:service.communicate(timeout=5)
        except subprocess.TimeoutExpired:service.kill();service.communicate()
        runner.terminate();runner.wait(timeout=5)
```

## `RED_FIRST/attack_completion_sigkill_git.py`
SHA256: `b14b5f66bb896248e6f2a4fd299f12f39c85af801dcfb1587bc5368f51849b9f` · bytes: 5127

```python
"""Window55 PM54-BLK-003 RED: executable SIGKILL + real Git remote witness.

IMPORTANT: not the approved RunBackend/GenerationStore; this replays byte-equivalent
candidate safe_runner completion/recovery ordering with disposable filesystem/Git
state. It is strictly a source-order operational witness, not full C15 acceptance.

Direct reviewed source path:
 reviews/.../harness/r005/safe_runner.py PR361@67da1125... lines 202-214, 269-272.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


def call(*argv, cwd=None):
    return subprocess.run(argv, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name+'.pending')
    with pending.open('wb') as f:
        f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(pending,path)
    fd = os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def main():
    root=Path(tempfile.mkdtemp(prefix='w55-blk003-',dir='/mnt/data/window55'))
    remote=root/'remote.git'; repo=root/'writer'; local=root/'backend';opid='exact-operation-55';marker=local/'mailbox/operations'/opid/'operation.json'
    call('git','init','--bare',str(remote))
    call('git','init',str(repo))
    call('git','-C',str(repo),'config','user.email','w55@invalid')
    call('git','-C',str(repo),'config','user.name','Window55 RED')
    call('git','-C',str(repo),'remote','add','origin',str(remote))
    (repo/'generation-head.json').write_text('{"generation":1,"head_sha256":"prior"}\n')
    call('git','-C',str(repo),'add','.')
    call('git','-C',str(repo),'commit','-m','previous-authoritative-generation')
    ref='refs/heads/persistence/synthetic-window55'
    call('git','-C',str(repo),'push','origin','HEAD:'+ref)
    remote_head=call('git','-C',str(repo),'rev-parse','HEAD')
    expected=local/'.remote-head'; atomic_write(expected,(remote_head+'\n').encode())
    atomic_write(local/'generation-head.json',(repo/'generation-head.json').read_bytes())
    spec={'event_id':'synthetic-do-not-run-resident','cursor':1}
    result={'status':'SUCCESS','semantic_reply':'synthetic-only','operation_id':opid}
    stop= root/'marker-ready.flag'
    proc_code='''import os,signal,sys,time,json\nfrom pathlib import Path\nroot=Path(sys.argv[1]);marker=Path(sys.argv[2]);spec=json.loads(sys.argv[3]);result=json.loads(sys.argv[4]);sys.path.insert(0,sys.argv[5]);from attack_completion_sigkill_git import atomic_write,canonical\n# PR361 safe_runner.py lines 270-271 critical ordering: local completed BEFORE final remote CAS.\natomic_write(marker,canonical({'state':'completed','spec':spec,'result':result}))\natomic_write(root/'marker-ready.flag',b'ready')\n# Simulate kill between atomic_write_bytes(...completed) and barrier(...operation-completed)\nwhile True:time.sleep(1)\n'''
    proc=subprocess.Popen([sys.executable,'-c',proc_code,str(root),str(marker),json.dumps(spec),json.dumps(result),str(Path(__file__).parent)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    for _ in range(500):
        if stop.is_file():break
        assert proc.poll() is None,proc.communicate()[1].decode()
        time.sleep(.01)
    assert stop.is_file(),'failure to reach kill window'
    os.kill(proc.pid,signal.SIGKILL)
    rc=proc.wait(timeout=5)
    assert rc == -signal.SIGKILL,rc
    # Source-level preflight matches C15's prior-remote-generation HEAD check.
    current=call('git','-C',str(repo),'ls-remote','origin',ref).split()[0]
    assert current==expected.read_text().strip()==remote_head
    old_remote_gen=call('git','-C',str(repo),'show',current+':generation-head.json').encode()+b'\n'
    assert old_remote_gen==(local/'generation-head.json').read_bytes()
    # This exact operation has not been committed remotely.
    absent=subprocess.run(['git','-C',str(repo),'show',current+':mailbox/operations/'+opid+'/operation.json'],capture_output=True)
    assert absent.returncode !=0
    # PR361 fast path lines 202-214: previous local completed marker is returned.
    previous=json.loads(marker.read_bytes())
    assert previous['spec']==spec and previous['state']=='completed'
    replay=previous['result']
    assert replay['status']=='SUCCESS'
    print('EVIDENCE_KIND=REAL_FILESYSTEM_SIGKILL_DISPOSABLE_GIT_REMOTE_WITH_EXACT_SOURCE_ORDER')
    print('APPROVED_C15_IMPORTED=NO')
    print('FAILED_CANDIDATE_SAFE_RUNNER_IMPORTED=NO')
    print('SIGKILL_RETURN_CODE='+str(rc))
    print('REMOTE_PRIOR_COMMIT='+remote_head)
    print('REMOTE_HEAD_UNCHANGED=YES')
    print('PRIOR_GENERATION_HEAD_MATCH=YES')
    print('REMOTE_COMMIT_LACKS_OPERATION_COMPLETION=YES')
    print('LOCAL_COMPLETED_FAST_PATH_RETURNS='+replay['status'])
    print('PM54_BLK_003_SOURCE_ORDER_WITNESS=REPRODUCED')
    print('FULL_HARNESS_C15_DYNAMIC_REPRODUCTION=NOT_RUN')
    print('DISPOSABLE_ROOT='+str(root))


if __name__=='__main__':main()
```

## `RED_FIRST/green_candidate_identity.py`
SHA256: `a810f141ac42b43f2c9b4cb7387876eb58ca3e6486b96a6c26237c2b42b28067` · bytes: 4432

```python
"""Window55 synthetic GREEN test for proposed strict module inventory and loader.

Not full Core/C15; only synthetic approved package imports vs substitution matrix.
"""
import hashlib,json,os,shutil,subprocess,sys,sysconfig,tempfile,importlib.machinery
from pathlib import Path

PY='/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python'
BASE=Path('/mnt/data/window55/corrective_worktree')
assert sys.version_info[:3]==(3,12,14)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def prep(root):
    harness=root/'harness';repo=root/'repo'
    (harness/'r005').mkdir(parents=True)
    (repo/'src/aios_core/headless').mkdir(parents=True)
    (repo/'tools/c15_persistence').mkdir(parents=True)
    for rel in ['launch.py','r005/checks.py']:
        dst=harness/rel;dst.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(BASE/rel,dst)
    extra={'r005/__init__.py':'',
       'r005/cli.py':'''import json,os
from pathlib import Path
from aios_core.headless import core
from r005.checks import loaded_modules
def main():
 status=loaded_modules(Path(os.environ['AIOS53_SOURCE_REPO']),Path(os.environ['AIOS53_LAUNCH']).parent)
 print(json.dumps({'marker':'GREEN','core_marker':core.marker(),'checks_loader':__import__('r005.checks',fromlist=['verify']).__loader__.__class__.__name__,'status':status},sort_keys=True))
''',
       'r005/payload.py':'# inert stub\n','r005/safe_runner.py':'# inert stub\n','r005/publisher_service.py':'# inert stub\n',
       'src/aios_core/__init__.py':'',
       'src/aios_core/headless/__init__.py':'',
       'src/aios_core/headless/core.py':'''def marker():return "GENUINE_PINNED_CORE"\n''',
       'tools/c15_persistence/__init__.py':''}
    for rel,content in extra.items():
        base=harness if rel.startswith('r005/') else repo
        p=base/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
    h={str(p.relative_to(harness)):sha(p) for p in harness.rglob('*.py')}
    s={str(p.relative_to(repo)):sha(p) for p in repo.rglob('*.py')}
    manifest={'harness_files':h,'source_files':s,'python_sha256':sha(Path(PY).resolve())}
    (harness/'IDENTITY.json').write_text(json.dumps(manifest,sort_keys=True))
    return harness,repo,sha(harness/'IDENTITY.json')

def execute(h,r,digest):
    return subprocess.run([PY,'-I',str(h/'launch.py'),'--source-repo',str(r),'--identity-sha256',digest,'verify'],capture_output=True,text=True,timeout=20)

def scenario(name,mutation,should_pass=False):
    with tempfile.TemporaryDirectory(prefix='w55-green-') as td:
        h,r,d=prep(Path(td));mutation(h,r)
        proc=execute(h,r,d)
        if should_pass:
            assert proc.returncode==0,(name,proc.stderr)
            result=json.loads(proc.stdout)
            assert result['core_marker']=='GENUINE_PINNED_CORE'
            assert result['checks_loader']=='PinnedSourceLoader'
            assert result['status']['module_import_identity']=='PASS'
        else:
            assert proc.returncode!=0,(name,proc.stdout)
            assert 'BLOCKED' in proc.stderr,(name,proc.stderr)
        return {'scenario':name,'pass':True,'exit_code':proc.returncode,'stdout':proc.stdout.strip() if should_pass else '',
            'stderr':proc.stderr.strip() if not should_pass else ''}

def build_extension(h,r,name):
    p=(h/'r005' if name=='checks' else r/'src/aios_core/headless')
    output=p/(name+importlib.machinery.EXTENSION_SUFFIXES[0])
    code='''#include <Python.h>
static struct PyModuleDef mod={PyModuleDef_HEAD_INIT,"'''+name+'''",NULL,-1,NULL};
PyMODINIT_FUNC PyInit_'''+name+'''(void){return PyModule_Create(&mod);}
'''
    c=(h/'..'/'evil.c');c.write_text(code)
    subprocess.run(['gcc','-shared','-fPIC','-I'+sysconfig.get_path('include'),'-o',str(output),str(c)],check=True,capture_output=True)

cases=[
('baseline',lambda h,r:None,True),
('extension_shadow_checks',lambda h,r:build_extension(h,r,'checks'),False),
('extension_shadow_core',lambda h,r:build_extension(h,r,'core'),False),
('unlisted_pyc',lambda h,r:(h/'r005/evil.pyc').write_bytes(b'pyc'),False),
('symlink_package_overlay',lambda h,r:(h/'r005/evil.py').symlink_to('checks.py'),False),
('byte_swapped_source',lambda h,r:(r/'src/aios_core/headless/core.py').write_text('def marker():return "ATTACKED"\n'),False),
('hardlink_duplicate',lambda h,r:os.link(h/'r005/checks.py',h/'r005/duplicate.py'),False),
]
print(json.dumps([scenario(*c) for c in cases],indent=2))
```

## `RED_FIRST/socket_peercred_feasibility.py`
SHA256: `8e820104483802c9d6d179763a9b825ecb552e8d4ff04807b1e871d0a4a82df0` · bytes: 1948

```python
"""Window55 BLK002 *transport feasibility*, not integrated harness closure.
Proof: Linux kernel SO_PEERCRED identifies connecting non-Runner process, regardless of forged JSON caller_pid.
"""
import json,os,socket,struct,subprocess,sys,tempfile,time
from pathlib import Path
assert sys.version_info[:3]==(3,12,14)
assert hasattr(socket,'SO_PEERCRED')
with tempfile.TemporaryDirectory(prefix='window55-peercred-',dir='/mnt/data/window55') as d:
    sock_path=str(Path(d)/'register.sock');runner=subprocess.Popen(['sleep','20']);
    server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    server.bind(sock_path);server.listen(1)
    try:
        attacker=subprocess.Popen([sys.executable,'-c',"import socket,sys,json,os;s=socket.socket(socket.AF_UNIX);s.connect(sys.argv[1]);s.sendall(json.dumps({'caller_pid':int(sys.argv[2]),'command':'register','context':{'attempt_id':'forged'}}).encode());s.close()",sock_path,str(runner.pid)])
        conn,_=server.accept()
        with conn:
            data=json.loads(conn.recv(2048));creds=conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,struct.calcsize('3i'))
            kernel_pid,uid,gid=struct.unpack('3i',creds)
        attacker.wait(timeout=5)
        assert attacker.returncode==0
        assert data['caller_pid']==runner.pid
        assert kernel_pid==attacker.pid!=runner.pid
        assert uid==os.geteuid() and uid==os.stat('/proc/'+str(runner.pid)).st_uid
        rejected=(kernel_pid!=runner.pid)
        assert rejected
        print(json.dumps({'mechanism':'AF_UNIX/SO_PEERCRED','python':sys.version.split()[0],
            'claimed_runner_pid':data['caller_pid'],'real_peer_pid_from_kernel':kernel_pid,
            'runner_pid':runner.pid,'uid_same':True,'spoofed_registration_rejected':rejected,
            'deployment_sandbox_support':'UNVERIFIED','full_harness_integration':'NOT_RUN'},indent=2))
    finally:
        server.close();runner.terminate();runner.wait(timeout=5)
```

## `RED_FIRST/exact_source_A01_core_and_checks.log`
SHA256: `52fadddbd180e416689657b382d2897b212b434d982388eb5f3163ccb5baa893` · bytes: 565

```text
[
  {
    "attack_target": "harness_checks",
    "manifest_py_bytes_unchanged": true,
    "native_imported_and_executed": true,
    "exact_checks_verify_after_injection": "PASS",
    "exact_checks_loaded_modules_after_native_execution": "PASS",
    "result": "SECURITY_DEFENSE_FAIL"
  },
  {
    "attack_target": "core",
    "manifest_py_bytes_unchanged": true,
    "native_imported_and_executed": true,
    "exact_checks_verify_after_injection": "PASS",
    "exact_checks_loaded_modules_after_native_execution": "PASS",
    "result": "SECURITY_DEFENSE_FAIL"
  }
]
```

## `RED_FIRST/exact_source_A05_service.log`
SHA256: `81b162baa5b67f4cbf0c74e352b8f6bffeb1589d58d5843795b8514c4056240d` · bytes: 524

```text
{
  "verified_exact_publisher_sha256": "37506ee7113acc30c02d3dfced92e92d8e73f1e77eca8c081b0af072534f3ac3",
  "python": "3.12.14",
  "attacker_pid": 926,
  "runner_pid": 927,
  "service_pid": 928,
  "same_uid": true,
  "runner_did_not_register": true,
  "forged_context_was_accepted": true,
  "real_publisher_registration_reply": {
    "ok": true,
    "result": {
      "publisher_pid": 928,
      "registered": "req-synthetic-window55"
    }
  },
  "semantic_publishing_tested": false,
  "result": "SECURITY_DEFENSE_FAIL"
}
```

## `RED_FIRST/exact_order_A10_git_sigkill.log`
SHA256: `db74de5960cb85618f52c51b5571ff9c025b4ee74c1bdb9f8865c213cb0eae76` · bytes: 525

```text
EVIDENCE_KIND=REAL_FILESYSTEM_SIGKILL_DISPOSABLE_GIT_REMOTE_WITH_EXACT_SOURCE_ORDER
APPROVED_C15_IMPORTED=NO
FAILED_CANDIDATE_SAFE_RUNNER_IMPORTED=NO
SIGKILL_RETURN_CODE=-9
REMOTE_PRIOR_COMMIT=529f8ee28f919e46e7f2a8b5d0271ea47af60f0c
REMOTE_HEAD_UNCHANGED=YES
PRIOR_GENERATION_HEAD_MATCH=YES
REMOTE_COMMIT_LACKS_OPERATION_COMPLETION=YES
LOCAL_COMPLETED_FAST_PATH_RETURNS=SUCCESS
PM54_BLK_003_SOURCE_ORDER_WITNESS=REPRODUCED
FULL_HARNESS_C15_DYNAMIC_REPRODUCTION=NOT_RUN
DISPOSABLE_ROOT=/mnt/data/window55/w55-blk003-a4ltgkoc
```

## `RED_FIRST/GREEN_prototype_identity.log`
SHA256: `ed4af096e8ba5fb563dda24b4809d70ea4a1dcf208a79f310f3349cda481ee6f` · bytes: 1567

```text
[
  {
    "scenario": "baseline",
    "pass": true,
    "exit_code": 0,
    "stdout": "{\"checks_loader\": \"PinnedSourceLoader\", \"core_marker\": \"GENUINE_PINNED_CORE\", \"marker\": \"GREEN\", \"status\": {\"loaded_modules\": [\"aios_core\", \"aios_core.headless\", \"aios_core.headless.core\", \"r005\", \"r005.checks\", \"r005.cli\"], \"module_import_identity\": \"PASS\", \"semantic_callback_router_disabled\": \"PASS\"}}",
    "stderr": ""
  },
  {
    "scenario": "extension_shadow_checks",
    "pass": true,
    "exit_code": 1,
    "stdout": "",
    "stderr": "BLOCKED / CLOSED_IMPORT_SET_DRIFT: ['r005/checks.cpython-312-x86_64-linux-gnu.so'] []"
  },
  {
    "scenario": "extension_shadow_core",
    "pass": true,
    "exit_code": 1,
    "stdout": "",
    "stderr": "BLOCKED / CLOSED_IMPORT_SET_DRIFT: ['headless/core.cpython-312-x86_64-linux-gnu.so'] []"
  },
  {
    "scenario": "unlisted_pyc",
    "pass": true,
    "exit_code": 1,
    "stdout": "",
    "stderr": "BLOCKED / CLOSED_IMPORT_SET_DRIFT: ['r005/evil.pyc'] []"
  },
  {
    "scenario": "symlink_package_overlay",
    "pass": true,
    "exit_code": 1,
    "stdout": "",
    "stderr": "BLOCKED / PROTECTED_SYMLINK: r005/evil.py"
  },
  {
    "scenario": "byte_swapped_source",
    "pass": true,
    "exit_code": 1,
    "stdout": "",
    "stderr": "BLOCKED / BYTE_IDENTITY_DRIFT: SOURCE/src/aios_core/headless/core.py"
  },
  {
    "scenario": "hardlink_duplicate",
    "pass": true,
    "exit_code": 1,
    "stdout": "",
    "stderr": "BLOCKED / PROTECTED_UNSAFE_NODE: r005/duplicate.py"
  }
]
```

## `RED_FIRST/BLK002_peercred_feasibility.log`
SHA256: `dedc98679810ac7933038a36aa187d64371ea71eea9c3c9d828d0eb404abfbc6` · bytes: 301

```text
{
  "mechanism": "AF_UNIX/SO_PEERCRED",
  "python": "3.12.14",
  "claimed_runner_pid": 1172,
  "real_peer_pid_from_kernel": 1173,
  "runner_pid": 1172,
  "uid_same": true,
  "spoofed_registration_rejected": true,
  "deployment_sandbox_support": "UNVERIFIED",
  "full_harness_integration": "NOT_RUN"
}
```

## `RED_FIRST/PR363_POC_3.12.14.log`
SHA256: `ba2bec28705bd8e262e130aaa524b50deb6917e93da937cdefd9a004c9c26d55` · bytes: 102

```text
..
---- generated xml file: /mnt/data/window55/RED_FIRST/PR363_POC_3.12.14.xml ----
2 passed in 0.18s
```
