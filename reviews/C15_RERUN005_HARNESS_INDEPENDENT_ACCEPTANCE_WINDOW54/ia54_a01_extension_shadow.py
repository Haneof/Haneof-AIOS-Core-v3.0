#!/usr/bin/env python3
"""IA54-A01 reviewer-owned frozen synthetic attack.
Precondition: same-UID adversary can add a native extension file under the
materialized harness root without modifying any manifest-listed Python file.
Candidate lines: launch.py 20-32, checks.py 41-57 and 67-80.
Expected defense: unlisted executable file aborts BEFORE module import.
Attack success: pinned checks.py SHA and *.py set stay valid, yet the imported
r005.checks comes from an unlisted native extension and returns fake PASS.
This is a CPython import-mechanics proof on a disposable stand-in package; it
is NOT an execution of the full PR #361 pinned CPython-3.12.14 runtime.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

C_SOURCE = r'''
#include <Python.h>
static PyObject* verify(PyObject* self, PyObject* args) {
    return Py_BuildValue("{s:s}", "identity", "ATTACKER_FALSE_PASS");
}
static PyObject* loaded_modules(PyObject* self, PyObject* args) {
    return Py_BuildValue("{s:s}", "semantic_callback_router_disabled", "ATTACKER_FALSE_PASS");
}
static PyMethodDef methods[] = {
    {"verify", verify, METH_VARARGS, NULL},
    {"loaded_modules", loaded_modules, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};
static struct PyModuleDef module = {PyModuleDef_HEAD_INIT,"checks",NULL,-1,methods};
PyMODINIT_FUNC PyInit_checks(void) { return PyModule_Create(&module); }
'''

with tempfile.TemporaryDirectory(prefix='ia54-a01-') as td:
    root=Path(td)
    pkg=root/'r005'
    pkg.mkdir()
    (pkg/'__init__.py').write_text('PACKAGE_NAME="aios_exchange"\n')
    pyfile=pkg/'checks.py'
    pyfile.write_text('def verify(*a): return {"identity":"GENUINE_VERIFIED"}\n'
                      'def loaded_modules(*a): return {"semantic_callback_router_disabled":"GENUINE_VERIFIED"}\n')
    originals={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
               for p in root.rglob('*.py')}
    (root/'evil.c').write_text(C_SOURCE)
    suffix=subprocess.check_output([sys.executable+'-config', '--extension-suffix'],text=True).strip() if Path(sys.executable+'-config').is_file() else subprocess.check_output(['python3-config','--extension-suffix'],text=True).strip()
    includes=subprocess.check_output(['python3-config','--includes'],text=True).split()
    native=pkg/('checks'+suffix)
    build=subprocess.run(['gcc','-shared','-fPIC',*includes,str(root/'evil.c'),'-o',str(native)],capture_output=True,text=True)
    if build.returncode:raise RuntimeError(build.stderr)
    after={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in root.rglob('*.py')}
    assert after==originals, 'attacker modified a pinned Python source'
    payload=r'''
import importlib.util,json,sys
from pathlib import Path
root=Path(sys.argv[1]); sys.path.extend([str(root)])
spec=importlib.util.spec_from_file_location('r005',root/'r005/__init__.py',submodule_search_locations=[str(root/'r005')])
m=importlib.util.module_from_spec(spec);sys.modules['r005']=m;spec.loader.exec_module(m)
from r005.checks import verify,loaded_modules
print(json.dumps({'verify':verify(None,None,None), 'loaded_modules':loaded_modules(None,None), 'loaded_from':sys.modules['r005.checks'].__file__}))
'''
    proc=subprocess.run([sys.executable,'-I','-c',payload,str(root)],capture_output=True,text=True)
    if proc.returncode:raise RuntimeError(proc.stderr)
    result=json.loads(proc.stdout)
    print(json.dumps({'attack':'IA54-A01-import-extension-shadow',
      'exact_candidate_execution':False,'interpreter':sys.version.split()[0],
      'source_file_count_unchanged':len(after), 'checks_py_hash_unchanged':after['r005/checks.py']==originals['r005/checks.py'],
      'native_extension_added_unlisted':str(native.name),
      'extension_ignored_by_python_set':str(native.relative_to(root)) not in after,
      'actual_imported_module':result['loaded_from'],
      'false_verify_return':result['verify']['identity'],
      'false_loaded_modules_return':result['loaded_modules']['semantic_callback_router_disabled'],
      'attack_demonstrated':result['verify']['identity']=='ATTACKER_FALSE_PASS',
    },indent=2))
