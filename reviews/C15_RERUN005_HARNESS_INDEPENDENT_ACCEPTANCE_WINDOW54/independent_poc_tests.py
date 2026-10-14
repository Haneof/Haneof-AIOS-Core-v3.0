"""Window54 reviewer-owned independent synthetic PoC wrapper only.
Expected protective invariant for each test: attacker cannot bypass identity.
The assertions deliberately demonstrate actual violation (attack success),
not an approval gate for the PR under review. No real Resident, Core or remote.
"""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent

def _run(name):
    proc=subprocess.run([sys.executable,str(ROOT/name)],capture_output=True,text=True,timeout=20)
    assert proc.returncode==0,proc.stderr
    return json.loads(proc.stdout)

def test_ia54_a01_import_shadow_attack_demonstrated():
    a=_run('ia54_a01_extension_shadow.py')
    assert a['checks_py_hash_unchanged'] is True
    assert a['extension_ignored_by_python_set'] is True
    assert a['attack_demonstrated'] is True
    assert a['false_verify_return']=='ATTACKER_FALSE_PASS'

def test_ia54_a05_pid_spoof_predicate_attack_demonstrated():
    a=_run('ia54_a05_pid_spoof.py')
    assert a['actual_attacker_pid']!=a['actual_runner_pid']
    assert a['json_claimed_caller_pid']==a['actual_runner_pid']
    assert a['live_identity_predicate_accepts_attacker'] is True
    assert a['core_semantic_application_demonstrated'] is False
