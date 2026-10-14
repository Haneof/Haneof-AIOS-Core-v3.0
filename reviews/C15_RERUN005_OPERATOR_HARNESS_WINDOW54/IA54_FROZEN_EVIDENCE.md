# Window 54 — Frozen reviewer probes and raw results

This document carries the actual reviewer-owned probe source and raw execution evidence.
The source files are reproduced verbatim in fenced blocks, including failures.
All tests were run only in disposable synthetic state. The model-only A10 witness is explicitly labeled.
It is not a PASS or a substitute for the author's 38 regressions.

## ATTACK_PLAN.json

SHA256: `64d21ad8fdaf1a16c35843d3bf861c50d052c8bf4475bc9d1b09bc1126609863` · bytes: 725

```json
{
  "window": 54,
  "candidate": "67da1125c4902380dafde98a0ccf01c42e590864",
  "attacks": [
    {
      "id": "IA54-A01/A03-NATIVE-SHADOW",
      "precondition": "Unpinned native module can be added under synthetic Core source path while original Python files retain their approved SHA256",
      "expected_defense": "Current checks.verify or loaded_modules must refuse the unpinned executable extension before any import or execution",
      "failure_criterion": "Exact candidate checks.verify passes; Python loads extension instead of approved .py; candidate loaded_modules reports PASS",
      "environment": "approved CPython 3.12.14, disposable synthetic source/manifest and GCC extension, no real Resident"
    }
  ]
}
```

## ia54_a01_native_shadow.py

SHA256: `63b6a167f78d01f94993161a737592c1eee4335a5db991391e51d0d83b1eb027` · bytes: 3840

```python
"""IA54-A01/A03: native-extension import substitution against exact Window53 checks.py.

Precondition: adversary can add an unpinned native extension to a writable source
checkout while keeping all pinned .py files unchanged.
Expected defense: startup verify or loaded_modules rejects the extra executable.
Failure criterion: both checks return PASS and the extension executes.
No real Resident state or run root is accessed.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile

BASE=Path('/mnt/data/ia54')
EXACT=BASE/'exact_harness/r005/checks.py'
EXPECTED='f5f93a8cf88a3b6b09b38007a231d5d4ba70e521ff2b91aaa7ca1edee9c1cef4'
assert hashlib.sha256(EXACT.read_bytes()).hexdigest()==EXPECTED, 'not the exact source bytes'
assert sys.version_info[:3]==(3,12,14)
spec=importlib.util.spec_from_file_location('reviewed_checks',EXACT)
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
root=Path(tempfile.mkdtemp(prefix='ia54-a01-',dir=str(BASE)))
harness=root/'harness';repo=root/'repo'
(harness/'r005').mkdir(parents=True)
(repo/'src/aios_core/headless').mkdir(parents=True)
(repo/'tools/c15_persistence').mkdir(parents=True)
shutil.copy2(EXACT,harness/'r005/checks.py')
for rel in ['launch.py','r005/__init__.py','r005/cli.py','r005/safe_runner.py',
            'r005/publisher_service.py','r005/payload.py']:
 p=harness/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'# intentionally harmless synthetic stub\n')
for rel in ['src/aios_core/__init__.py','src/aios_core/headless/__init__.py',
 'src/aios_core/headless/core.py','tools/c15_persistence/__init__.py']:
 p=repo/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'SOURCE_IS_PINNED=True\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
hfiles={str(p.relative_to(harness)):sha(p) for p in harness.rglob('*.py')}
sfiles={str(p.relative_to(repo)):sha(p) for p in repo.rglob('*.py')}
identity={'harness_files':hfiles,'source_files':sfiles,
 'python_sha256':sha(Path(sys.executable).resolve())}
(harness/'IDENTITY.json').write_text(json.dumps(identity,sort_keys=True))
identity_sha=sha(harness/'IDENTITY.json')
print('PROBE_EXACT_CHECKS_SHA',sha(EXACT))
checks.verify(harness,repo,identity_sha)
print('BASELINE_VERIFY PASS')
source= r'''#include <Python.h>
static PyObject* injected(PyObject* self,PyObject* args){return PyUnicode_FromString("FAKE_HEADLESS_CORE_EXECUTED");}
static PyMethodDef methods[]={{"unauthorized_entry",injected,METH_NOARGS,"synthetic IA54 probe"},{NULL,NULL,0,NULL}};
static struct PyModuleDef mod={PyModuleDef_HEAD_INIT,"core",NULL,-1,methods};
PyMODINIT_FUNC PyInit_core(void){return PyModule_Create(&mod);}
'''
cfile=root/'attack.c';cfile.write_text(source)
import importlib.machinery
suffix=importlib.machinery.EXTENSION_SUFFIXES[0]
native=repo/'src/aios_core/headless'/('core'+suffix)
cc=['gcc','-shared','-fPIC','-I'+sysconfig.get_path('include'),
 '-o',str(native),str(cfile)]
subprocess.run(cc,check=True,capture_output=True)
assert native.is_file()
# The hashes and .py file sets remain EXACTLY unchanged.
assert {str(p.relative_to(repo)):sha(p) for p in repo.rglob('*.py')}==sfiles
checks.verify(harness,repo,identity_sha)
print('POST_INJECTION_STARTUP_VERIFY PASS (UNEXPECTED)')
sys.path.insert(0,str(repo/'src'))
import aios_core.headless.core as loaded
assert Path(loaded.__file__).resolve()==native.resolve(),loaded.__file__
assert loaded.unauthorized_entry()=='FAKE_HEADLESS_CORE_EXECUTED'
status=checks.loaded_modules(repo,harness)
assert status['module_import_identity']=='PASS'
print('MALICIOUS_SOURCE_LOADED',str(loaded.__file__))
print('POST_INJECTION_MODULE_IDENTITY PASS (UNEXPECTED)')
print('RESULT=FAIL_CLOSED_BYPASS_CONFIRMED')
print('TEMP_SYNTHETIC_ROOT',root)
```

## ATTACK_PLAN_A05.json

SHA256: `848ea17cb4e24269a57448450674f057bdc2827d4b9455372db5207a6d33ad41` · bytes: 788

```json
{
  "window": 54,
  "candidate": "67da1125c4902380dafde98a0ccf01c42e590864",
  "attack_id": "IA54-A05-FORGED-PID-REGISTER",
  "precondition": "Publisher file IPC writable by another local same-UID process; authentic Runner PID remains live; request digest is valid",
  "expected_defense": "Publisher registers only messages authenticated as originating from actual Runner process, rather than trusting caller_pid in attacker-owned JSON",
  "failure_criterion": "Exact publisher source registers a request and arbitrary context despite command arriving from a different process with fake caller_pid",
  "scope_limit": "Core, C15 and durable bridge are synthetic stubs here; the test isolates Publisher process identity authentication and does not prove full trusted-return exploitation"
}
```

## A05_PROBE_CORRECTION.txt

SHA256: `a2d963fe334adb567c608eb1149e8792b7820f605af66763d69f0e9c945f37ce` · bytes: 325

```text
A05 probe v1 SHA e757a84cc166d64835a3947001627205749fe9095311841266d93130da0c2c65 exited 1 before execution due to trailing unmatched triple quote at line 117. Correction v2 removes only trailing unmatched quote; assumptions, assertions, and expected outcome remain identical. Both probe versions and original logs retained.
```

## A05_PROBE_CORRECTION_V3.txt

SHA256: `47c85b0e9cf1f388415a73bae9426b6f8974fd7c2151fda8231dbeee5cef10e9` · bytes: 288

```text
A05 probe v2 exited 1 during disposable fake atomic.py setup: Python open() cannot take O_RDONLY int as mode. v3 only fixes test scaffolding with os.open/os.fsync/os.close. Original acceptance criteria and attack messages unchanged, exact candidate source unchanged, prior logs retained.
```

## ia54_a05_forged_pid_v3.py

SHA256: `0c65141f57c116a8c74fd297ef49ab6bb4fbda0593403be46985c907f39ed33f` · bytes: 5166

```python
"""IA54-A05: spoof caller_pid in exact Window53 publisher_service.py.

Precondition: local unprivileged process (same account) can submit a JSON
command into the Publisher's file IPC, while the real Runner PID is alive.
Expected defense: peer identity cryptographically or kernel-bound; a forged
caller_pid must not register or provide signing context.
Failure criterion: an IPC message not authored by the Runner registers a request
and arbitrary context by naming the Runner's PID.

The real candidate's publisher_service.py is byte-verified. Request-store
responses are synthetic stubs, so this proves the Publisher registration auth
predicate, NOT a full C15/Core end-to-end vulnerability.
"""
from pathlib import Path
import hashlib
import json
import os
import select
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

BASE=Path('/mnt/data/ia54')
SOURCE=BASE/'exact_harness/r005/publisher_service.py'
EXPECTED='37506ee7113acc30c02d3dfced92e92d8e73f1e77eca8c081b0af072534f3ac3'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
assert sys.version_info[:3]==(3,12,14)
root=Path(tempfile.mkdtemp(prefix='ia54-a05-',dir=str(BASE)))
stubs=root/'stubs'
for name in ['r005/__init__.py','aios_core/__init__.py','aios_core/runtime/__init__.py']:
 p=stubs/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('')
(stubs/'r005/atomic.py').write_text('''import os
from pathlib import Path
def atomic_write_bytes(path,data):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 q=p.with_name(p.name+'.tmp')
 with open(q,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(q,p)
 fd=os.open(p.parent,os.O_RDONLY);os.fsync(fd);os.close(fd)
''')
(stubs/'r005/canonical.py').write_text('''import json
def canonical_json_bytes(o):return json.dumps(o,sort_keys=True,separators=(',',':')).encode()
''')
(stubs/'r005/bridge.py').write_text('''class ExchangeBridge:
 def __init__(self,root):self.requests=self
 def payload(self,rid):
  if rid!='req-synthetic-a05':raise ValueError('unrecognized request')
  return {'kind':'model_directive','body':{'provenance_binding':{}}}
 def request_sha256(self,rid):
  self.payload(rid);return 'a'*64
''')
(stubs/'r005/schema.py').write_text('def parse_model_directive(x):raise RuntimeError("not used in register probe")\n')
(stubs/'r005/payload.py').write_text('def parse(kind,raw):raise RuntimeError("not used in register probe")\n')
(stubs/'aios_core/runtime/background_attempt.py').write_text('def encode_model_directive(x):raise RuntimeError("not used in register probe")\n')
(stubs/'aios_core/runtime/late_return.py').write_text('def late_return_message(**x):raise RuntimeError("not used in register probe")\n')
bootstrap=root/'bootstrap.py'
bootstrap.write_text('''import runpy,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
source=sys.argv[2]
sys.argv=[source,*sys.argv[3:]]
runpy.run_path(source,run_name='__main__')
''')
exchange=root/'exchange';exchange.mkdir()
channel=root/'ipc'
runner=subprocess.Popen(['sleep','30'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
readfd,writefd=os.pipe()
cmd=[sys.executable,'-I',str(bootstrap),str(stubs),str(SOURCE),str(exchange),str(channel),str(runner.pid),str(readfd)]
service=subprocess.Popen(cmd,pass_fds=(readfd,),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
os.close(readfd)
try:
 deadline=time.monotonic()+25
 while not (channel/'ready.json').is_file():
  if service.poll() is not None:raise RuntimeError('Publisher exited during startup: '+service.stderr.read())
  if time.monotonic()>deadline:raise RuntimeError('Publisher timeout')
  time.sleep(.04)
 assert runner.poll() is None
 assert os.getpid()!=runner.pid
 attack={
  'command':'register',
  'caller_pid':runner.pid,  # intentionally NOT this process's genuine PID
  'request_id':'req-synthetic-a05',
  'request_sha256':'a'*64,
  'context':{'attempt_id':'FORGED_EXTERNAL_SCOPE','outbound_request_fingerprint':'forged'}
 }
 command_file=channel/(uuid.uuid4().hex+'.command.json')
 command_file.write_text(json.dumps(attack))
 result_file=command_file.with_suffix('.result')
 deadline=time.monotonic()+12
 while not result_file.exists():
  if service.poll() is not None:raise RuntimeError('Publisher unexpectedly exited')
  if time.monotonic()>deadline:raise RuntimeError('registration reply timed out')
  time.sleep(.02)
 answer=json.loads(result_file.read_text())
 print('EXACT_PUBLISHER_SHA',hashlib.sha256(SOURCE.read_bytes()).hexdigest())
 print('RUNNER_PID',runner.pid)
 print('ATTACKER_PID',os.getpid())
 print('REAL_RUNNER_CREATED_REGISTRATION',False)
 print('FORGED_COMMAND_RESULT',json.dumps(answer,sort_keys=True))
 assert answer['ok'] is True,answer
 assert answer['result']['registered']=='req-synthetic-a05'
 print('RESULT=UNAUTHORIZED_REGISTRATION_ACCEPTED')
 print('SYNTHETIC_TEMP_ROOT',root)
finally:
 os.close(writefd)
 if service.poll() is None:
  service.terminate()
  try:service.wait(timeout=3)
  except subprocess.TimeoutExpired:service.kill();service.wait()
 if runner.poll() is None:
  runner.terminate()
  try:runner.wait(timeout=3)
  except subprocess.TimeoutExpired:runner.kill();runner.wait()
```

## ATTACK_PLAN_A10.json

SHA256: `ab742caf71791d3131dc9903816168212f979548f7f0778514111f50295c3519` · bytes: 943

```json
{
  "window":54,
  "candidate":"67da1125c4902380dafde98a0ccf01c42e590864",
  "attack":"IA54-A10/A11-COMPLETION-PRE-BARRIER-CRASH",
  "precondition":"A local completed marker is fsynced after semantic application and before the final remote operation-completed barrier; a process dies at that point",
  "expected_defense":"Recovery must verify the completed operation marker and result are included in an authoritative remote commit or must remain blocked",
  "failure_criterion":"The immutable generation HEAD still equals the last remote commit and cached completed-result fast path allows return without proving final completion barrier",
  "independence":"Synthetic state-machine crash witness plus exact GitHub source-order evidence; does not assert a real Core/C15 executable end-to-end run",
  "source_anchors":{
    "safe_runner.py":[202,210,214,270,271,272],
    "remote_backend.py":[131,149,167,170],
    "backend.py":[340,392]
  }
}
```

## ia54_a10_completion_gap.py

SHA256: `675bc33655cff6ff9bd337b5501581e51b5455d0bbae933b8f3fe37883a509ae` · bytes: 3052

```python
"""IA54 A10/A11 synthetic schedule witness; expected defense is fail-closed.

The source locations anchoring this witness are checked independently from
PR #361 exact head, not generated from the attack outcome. This probe does NOT
exercise the full approved Core/C15 implementation; it models the demonstrable
crash window and should be read together with the source citations.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import os

# State represented by source rules at the exact head:
# safe_runner.py:270 durable local 'completed' -> :271 final remote barrier
# safe_runner.py:202 verify_local_remote_authority -> :210-214 local replay
# remote_backend.py:150-170 checks expected remote ref and GenerationStore.HEAD
# backend.py:392 checks previously sealed generations, not live mailbox marker

def accepted_remote_authority(local_expected_head, remote_head, local_generation_head,
                              remote_generation_head):
    assert local_expected_head == remote_head
    assert local_generation_head == remote_generation_head


def candidate_cached_completion_gate(marker, spec):
    assert marker['spec'] == spec
    if marker['state'] != 'completed':
        raise RuntimeError('blocked')
    return marker['result']


def main():
    with tempfile.TemporaryDirectory(prefix='ia54-a10-',dir='/mnt/data/ia54') as path:
        root=Path(path)
        spec={'mode':'user','cursor':1,'event_id':'SYNTHETIC_ONLY'}
        result={'synthetic_result':'NOT_REMOTE_DURABLE'}
        remote_head='a'*40
        expected_remote_head=remote_head
        generation_head=b'{"generation": 3}\n'
        remote_generation_head=generation_head
        operation=root/'mailbox'/'operations'/'synthetic'/'operation.json'
        operation.parent.mkdir(parents=True)
        operation.write_text(json.dumps({'state':'started','spec':spec}))
        # Exact candidate writes a completed marker durably BEFORE barrier.
        with operation.open('w') as f:
            json.dump({'state':'completed','spec':spec,'result':result},f)
            f.flush();os.fsync(f.fileno())
        fd=os.open(str(operation.parent),os.O_RDONLY);os.fsync(fd);os.close(fd)
        # Simulated SIGKILL: skip final barrier; remote head/generation unchanged.
        completed_remote_barrier_reached=False
        assert not completed_remote_barrier_reached
        accepted_remote_authority(expected_remote_head,remote_head,generation_head,
                                  remote_generation_head)
        returned=candidate_cached_completion_gate(json.loads(operation.read_text()),spec)
        assert returned==result
        print('LOCAL_MARKER=COMPLETED_BEFORE_REMOTE_BARRIER')
        print('REMOTE_GENERATION_HEAD_UNCHANGED=YES')
        print('REMOTE_AUTHORITY_CHECK_MODELED=PASS_UNCHANGED_PRIOR_HEAD')
        print('CACHED_FAST_PATH_RETURNS_UNCOMMITTED_RESULT=YES')
        print('EVIDENCE_TYPE=SYNTHETIC_CRASH_SCHEDULE_PLUS_SOURCE_ORDER')
        print('RESULT=COMPLETION_AUTHORITY_GAP_WITNESS')

if __name__=='__main__':main()
```

## test_ia54_fail_closed.py

SHA256: `fa63019a94bfd3046cff4a21e9de98a2233c422ae8affcc28202054f8f4a416e` · bytes: 1061

```python
"""Independent Window54 RED assertions. No author regressions imported.

These tests assert the SECURITY CONTRACT (not the exploit outcome).
A passing attacker script therefore makes the corresponding security test RED.
"""
import subprocess
import sys
from pathlib import Path

BASE=Path('/mnt/data/ia54/reviewer_probes')


def execute_probe(name):
    completed=subprocess.run([sys.executable,'-I',str(BASE/name)],
                             stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                             text=True,timeout=90)
    assert completed.returncode==0, f'Probe execution incomplete: {completed.stdout}'
    return completed.stdout


def test_ia54_a01_native_module_cannot_bypass_frozen_identity():
    observed=execute_probe('ia54_a01_native_shadow.py')
    assert 'RESULT=FAIL_CLOSED_BYPASS_CONFIRMED' not in observed, observed


def test_ia54_a05_non_runner_cannot_register_publisher_scope():
    observed=execute_probe('ia54_a05_forged_pid_v3.py')
    assert 'RESULT=UNAUTHORIZED_REGISTRATION_ACCEPTED' not in observed, observed
```

## IA54_PYTEST_FRESH_RAW.log

SHA256: `339d459be0badf77b3849d1c39f839d75a37e5f9269d2811b42d48655a7092da` · bytes: 4221

```text
FF                                                                       [100%]
=================================== FAILURES ===================================
__________ test_ia54_a01_native_module_cannot_bypass_frozen_identity ___________

    def test_ia54_a01_native_module_cannot_bypass_frozen_identity():
        observed=execute_probe('ia54_a01_native_shadow.py')
>       assert 'RESULT=FAIL_CLOSED_BYPASS_CONFIRMED' not in observed, observed
E       AssertionError: PROBE_EXACT_CHECKS_SHA f5f93a8cf88a3b6b09b38007a231d5d4ba70e521ff2b91aaa7ca1edee9c1cef4
E         BASELINE_VERIFY PASS
E         POST_INJECTION_STARTUP_VERIFY PASS (UNEXPECTED)
E         MALICIOUS_SOURCE_LOADED /mnt/data/ia54/ia54-a01-s1t86fbf/repo/src/aios_core/headless/core.cpython-312-x86_64-linux-gnu.so
E         POST_INJECTION_MODULE_IDENTITY PASS (UNEXPECTED)
E         RESULT=FAIL_CLOSED_BYPASS_CONFIRMED
E         TEMP_SYNTHETIC_ROOT /mnt/data/ia54/ia54-a01-s1t86fbf
E         
E       assert 'RESULT=FAIL...SS_CONFIRMED' not in 'PROBE_EXACT...1-s1t86fbf\n'
E         
E         'RESULT=FAIL_CLOSED_BYPASS_CONFIRMED' is contained here:
E           EXPECTED)
E           RESULT=FAIL_CLOSED_BYPASS_CONFIRMED
E           TEMP_SYNTHETIC_ROOT /mnt/data/ia54/ia54-a01-s1t86fbf

mnt/data/ia54/reviewer_probes/test_ia54_fail_closed.py:23: AssertionError
___________ test_ia54_a05_non_runner_cannot_register_publisher_scope ___________

    def test_ia54_a05_non_runner_cannot_register_publisher_scope():
        observed=execute_probe('ia54_a05_forged_pid_v3.py')
>       assert 'RESULT=UNAUTHORIZED_REGISTRATION_ACCEPTED' not in observed, observed
E       AssertionError: EXACT_PUBLISHER_SHA 37506ee7113acc30c02d3dfced92e92d8e73f1e77eca8c081b0af072534f3ac3
E         RUNNER_PID 1080
E         ATTACKER_PID 1079
E         REAL_RUNNER_CREATED_REGISTRATION False
E         FORGED_COMMAND_RESULT {"ok": true, "result": {"publisher_pid": 1081, "registered": "req-synthetic-a05"}}
E         RESULT=UNAUTHORIZED_REGISTRATION_ACCEPTED
E         SYNTHETIC_TEMP_ROOT /mnt/data/ia54/ia54-a05-mewjqlv8
E         
E       assert 'RESULT=UNAU...ION_ACCEPTED' not in 'EXACT_PUBLI...5-mewjqlv8\n'
E         
E         'RESULT=UNAUTHORIZE...GISTRATION_ACCEPTED' is contained here:
E           ic-a05"}}
E           RESULT=UNAUTHORIZED_REGISTRATION_ACCEPTED
E           SYNTHETIC_TEMP_ROOT /mnt/data/ia54/ia54-a05-mewjqlv8

mnt/data/ia54/reviewer_probes/test_ia54_fail_closed.py:28: AssertionError
---- generated xml file: /mnt/data/ia54/reviewer_probes/IA54_RED_FRESH.xml -----
=========================== short test summary info ============================
FAILED mnt/data/ia54/reviewer_probes/test_ia54_fail_closed.py::test_ia54_a01_native_module_cannot_bypass_frozen_identity - AssertionError: PROBE_EXACT_CHECKS_SHA f5f93a8cf88a3b6b09b38007a231d5d4ba70e521ff2b91aaa7ca1edee9c1cef4
  BASELINE_VERIFY PASS
  POST_INJECTION_STARTUP_VERIFY PASS (UNEXPECTED)
  MALICIOUS_SOURCE_LOADED /mnt/data/ia54/ia54-a01-s1t86fbf/repo/src/aios_core/headless/core.cpython-312-x86_64-linux-gnu.so
  POST_INJECTION_MODULE_IDENTITY PASS (UNEXPECTED)
  RESULT=FAIL_CLOSED_BYPASS_CONFIRMED
  TEMP_SYNTHETIC_ROOT /mnt/data/ia54/ia54-a01-s1t86fbf
  
assert 'RESULT=FAIL...SS_CONFIRMED' not in 'PROBE_EXACT...1-s1t86fbf\n'
  
  'RESULT=FAIL_CLOSED_BYPASS_CONFIRMED' is contained here:
    EXPECTED)
    RESULT=FAIL_CLOSED_BYPASS_CONFIRMED
    TEMP_SYNTHETIC_ROOT /mnt/data/ia54/ia54-a01-s1t86fbf
FAILED mnt/data/ia54/reviewer_probes/test_ia54_fail_closed.py::test_ia54_a05_non_runner_cannot_register_publisher_scope - AssertionError: EXACT_PUBLISHER_SHA 37506ee7113acc30c02d3dfced92e92d8e73f1e77eca8c081b0af072534f3ac3
  RUNNER_PID 1080
  ATTACKER_PID 1079
  REAL_RUNNER_CREATED_REGISTRATION False
  FORGED_COMMAND_RESULT {"ok": true, "result": {"publisher_pid": 1081, "registered": "req-synthetic-a05"}}
  RESULT=UNAUTHORIZED_REGISTRATION_ACCEPTED
  SYNTHETIC_TEMP_ROOT /mnt/data/ia54/ia54-a05-mewjqlv8
  
assert 'RESULT=UNAU...ION_ACCEPTED' not in 'EXACT_PUBLI...5-mewjqlv8\n'
  
  'RESULT=UNAUTHORIZE...GISTRATION_ACCEPTED' is contained here:
    ic-a05"}}
    RESULT=UNAUTHORIZED_REGISTRATION_ACCEPTED
    SYNTHETIC_TEMP_ROOT /mnt/data/ia54/ia54-a05-mewjqlv8
2 failed in 0.79s
```

## IA54_RED_FRESH.xml

SHA256: `7f4cae6da2ae9c518791ef26ea48487f49566755ce4c45c0c456b554b0bf9452` · bytes: 4197

```xml
<?xml version="1.0" encoding="utf-8"?><testsuites name="pytest tests"><testsuite name="pytest" errors="0" failures="2" skipped="0" tests="2" time="0.794" timestamp="2026-10-14T01:05:07.020989+00:00" hostname="8dc49c8a8cb2"><testcase classname="test_ia54_fail_closed" name="test_ia54_a01_native_module_cannot_bypass_frozen_identity" time="0.378"><failure message="AssertionError: PROBE_EXACT_CHECKS_SHA f5f93a8cf88a3b6b09b38007a231d5d4ba70e521ff2b91aaa7ca1edee9c1cef4&#10;  BASELINE_VERIFY PASS&#10;  POST_INJECTION_STARTUP_VERIFY PASS (UNEXPECTED)&#10;  MALICIOUS_SOURCE_LOADED /mnt/data/ia54/ia54-a01-s1t86fbf/repo/src/aios_core/headless/core.cpython-312-x86_64-linux-gnu.so&#10;  POST_INJECTION_MODULE_IDENTITY PASS (UNEXPECTED)&#10;  RESULT=FAIL_CLOSED_BYPASS_CONFIRMED&#10;  TEMP_SYNTHETIC_ROOT /mnt/data/ia54/ia54-a01-s1t86fbf&#10;  &#10;assert 'RESULT=FAIL...SS_CONFIRMED' not in 'PROBE_EXACT...1-s1t86fbf\n'&#10;  &#10;  'RESULT=FAIL_CLOSED_BYPASS_CONFIRMED' is contained here:&#10;    EXPECTED)&#10;    RESULT=FAIL_CLOSED_BYPASS_CONFIRMED&#10;    TEMP_SYNTHETIC_ROOT /mnt/data/ia54/ia54-a01-s1t86fbf">def test_ia54_a01_native_module_cannot_bypass_frozen_identity():
        observed=execute_probe('ia54_a01_native_shadow.py')
&gt;       assert 'RESULT=FAIL_CLOSED_BYPASS_CONFIRMED' not in observed, observed
E       AssertionError: PROBE_EXACT_CHECKS_SHA f5f93a8cf88a3b6b09b38007a231d5d4ba70e521ff2b91aaa7ca1edee9c1cef4
E         BASELINE_VERIFY PASS
E         POST_INJECTION_STARTUP_VERIFY PASS (UNEXPECTED)
E         MALICIOUS_SOURCE_LOADED /mnt/data/ia54/ia54-a01-s1t86fbf/repo/src/aios_core/headless/core.cpython-312-x86_64-linux-gnu.so
E         POST_INJECTION_MODULE_IDENTITY PASS (UNEXPECTED)
E         RESULT=FAIL_CLOSED_BYPASS_CONFIRMED
E         TEMP_SYNTHETIC_ROOT /mnt/data/ia54/ia54-a01-s1t86fbf
E         
E       assert 'RESULT=FAIL...SS_CONFIRMED' not in 'PROBE_EXACT...1-s1t86fbf\n'
E         
E         'RESULT=FAIL_CLOSED_BYPASS_CONFIRMED' is contained here:
E           EXPECTED)
E           RESULT=FAIL_CLOSED_BYPASS_CONFIRMED
E           TEMP_SYNTHETIC_ROOT /mnt/data/ia54/ia54-a01-s1t86fbf

mnt/data/ia54/reviewer_probes/test_ia54_fail_closed.py:23: AssertionError</failure></testcase><testcase classname="test_ia54_fail_closed" name="test_ia54_a05_non_runner_cannot_register_publisher_scope" time="0.390"><failure message="AssertionError: EXACT_PUBLISHER_SHA 37506ee7113acc30c02d3dfced92e92d8e73f1e77eca8c081b0af072534f3ac3&#10;  RUNNER_PID 1080&#10;  ATTACKER_PID 1079&#10;  REAL_RUNNER_CREATED_REGISTRATION False&#10;  FORGED_COMMAND_RESULT {&quot;ok&quot;: true, &quot;result&quot;: {&quot;publisher_pid&quot;: 1081, &quot;registered&quot;: &quot;req-synthetic-a05&quot;}}&#10;  RESULT=UNAUTHORIZED_REGISTRATION_ACCEPTED&#10;  SYNTHETIC_TEMP_ROOT /mnt/data/ia54/ia54-a05-mewjqlv8&#10;  &#10;assert 'RESULT=UNAU...ION_ACCEPTED' not in 'EXACT_PUBLI...5-mewjqlv8\n'&#10;  &#10;  'RESULT=UNAUTHORIZE...GISTRATION_ACCEPTED' is contained here:&#10;    ic-a05&quot;}}&#10;    RESULT=UNAUTHORIZED_REGISTRATION_ACCEPTED&#10;    SYNTHETIC_TEMP_ROOT /mnt/data/ia54/ia54-a05-mewjqlv8">def test_ia54_a05_non_runner_cannot_register_publisher_scope():
        observed=execute_probe('ia54_a05_forged_pid_v3.py')
&gt;       assert 'RESULT=UNAUTHORIZED_REGISTRATION_ACCEPTED' not in observed, observed
E       AssertionError: EXACT_PUBLISHER_SHA 37506ee7113acc30c02d3dfced92e92d8e73f1e77eca8c081b0af072534f3ac3
E         RUNNER_PID 1080
E         ATTACKER_PID 1079
E         REAL_RUNNER_CREATED_REGISTRATION False
E         FORGED_COMMAND_RESULT {"ok": true, "result": {"publisher_pid": 1081, "registered": "req-synthetic-a05"}}
E         RESULT=UNAUTHORIZED_REGISTRATION_ACCEPTED
E         SYNTHETIC_TEMP_ROOT /mnt/data/ia54/ia54-a05-mewjqlv8
E         
E       assert 'RESULT=UNAU...ION_ACCEPTED' not in 'EXACT_PUBLI...5-mewjqlv8\n'
E         
E         'RESULT=UNAUTHORIZE...GISTRATION_ACCEPTED' is contained here:
E           ic-a05"}}
E           RESULT=UNAUTHORIZED_REGISTRATION_ACCEPTED
E           SYNTHETIC_TEMP_ROOT /mnt/data/ia54/ia54-a05-mewjqlv8

mnt/data/ia54/reviewer_probes/test_ia54_fail_closed.py:28: AssertionError</failure></testcase></testsuite></testsuites>
```

## IA54_A10_RAW.log

SHA256: `a8e8861f1b64c7320e691e6ce4f1b1acdd104521da70b82e57fb42609565f0d6` · bytes: 284

```text
LOCAL_MARKER=COMPLETED_BEFORE_REMOTE_BARRIER
REMOTE_GENERATION_HEAD_UNCHANGED=YES
REMOTE_AUTHORITY_CHECK_MODELED=PASS_UNCHANGED_PRIOR_HEAD
CACHED_FAST_PATH_RETURNS_UNCOMMITTED_RESULT=YES
EVIDENCE_TYPE=SYNTHETIC_CRASH_SCHEDULE_PLUS_SOURCE_ORDER
RESULT=COMPLETION_AUTHORITY_GAP_WITNESS
```

## AUTHOR_RERUN_ATTEMPT.log

SHA256: `9efae02bfd9badeabbb412204ec0d42437af350101900d54c4f5c2dca8fb8c53` · bytes: 208

```text
ERROR: file or directory not found: /mnt/data/ia54/repo/reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW53


- generated xml file: /mnt/data/ia54/reviewer_probes/AUTHOR_RERUN_ATTEMPT.xml --
no tests ran in 0.00s
```

## GIT_FETCH_RAW.log

SHA256: `bea85628f72150b94191f6be161a60143996b4cc18fae78239ec1e89320edfff` · bytes: 115

```text
fatal: unable to access 'https://github.com/Haneof/Haneof-AIOS-Core-v3.0.git/': Could not resolve host: github.com
```

## FROZEN_SHA256.txt

SHA256: `3c83c0e1fa7d6a026650810520b4773ae060a227d86a460aa515a5a732664a93` · bytes: 1321

```text
63b6a167f78d01f94993161a737592c1eee4335a5db991391e51d0d83b1eb027  /mnt/data/ia54/reviewer_probes/ia54_a01_native_shadow.py
64d21ad8fdaf1a16c35843d3bf861c50d052c8bf4475bc9d1b09bc1126609863  /mnt/data/ia54/reviewer_probes/ATTACK_PLAN.json
f5f93a8cf88a3b6b09b38007a231d5d4ba70e521ff2b91aaa7ca1edee9c1cef4  /mnt/data/ia54/exact_harness/r005/checks.py
e757a84cc166d64835a3947001627205749fe9095311841266d93130da0c2c65  /mnt/data/ia54/reviewer_probes/ia54_a05_forged_pid.py
848ea17cb4e24269a57448450674f057bdc2827d4b9455372db5207a6d33ad41  /mnt/data/ia54/reviewer_probes/ATTACK_PLAN_A05.json
37506ee7113acc30c02d3dfced92e92d8e73f1e77eca8c081b0af072534f3ac3  /mnt/data/ia54/exact_harness/r005/publisher_service.py
64624f3bbc29032f36d70cca3b1b2b0118bd8e8b508cfa7d88cbb4c2b938df4a  /mnt/data/ia54/reviewer_probes/ia54_a05_forged_pid_v2.py
a2d963fe334adb567c608eb1149e8792b7820f605af66763d69f0e9c945f37ce  /mnt/data/ia54/reviewer_probes/A05_PROBE_CORRECTION.txt
0c65141f57c116a8c74fd297ef49ab6bb4fbda0593403be46985c907f39ed33f  /mnt/data/ia54/reviewer_probes/ia54_a05_forged_pid_v3.py
47c85b0e9cf1f388415a73bae9426b6f8974fd7c2151fda8231dbeee5cef10e9  /mnt/data/ia54/reviewer_probes/A05_PROBE_CORRECTION_V3.txt
fa63019a94bfd3046cff4a21e9de98a2233c422ae8affcc28202054f8f4a416e  /mnt/data/ia54/reviewer_probes/test_ia54_fail_closed.py
```

## A10_FROZEN_SHA256.txt

SHA256: `e595ef347af65cd33230eed9dc95e1b24ca96240f8c901928179ef4943e844fe` · bytes: 242

```text
ab742caf71791d3131dc9903816168212f979548f7f0778514111f50295c3519  /mnt/data/ia54/reviewer_probes/ATTACK_PLAN_A10.json
675bc33655cff6ff9bd337b5501581e51b5455d0bbae933b8f3fe37883a509ae  /mnt/data/ia54/reviewer_probes/ia54_a10_completion_gap.py
```
