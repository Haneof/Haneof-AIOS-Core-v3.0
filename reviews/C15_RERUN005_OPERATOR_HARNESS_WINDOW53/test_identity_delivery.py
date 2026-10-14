import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from r005.checks import static_scan

SOURCE=Path(__file__).resolve().parents[2]
HARN=SOURCE/'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness'


def command(harn,executable=None):
    return [executable or os.environ['APPROVED53_PYTHON'],'-I',str(harn/'launch.py'),
        '--source-repo',str(SOURCE),'--identity-sha256',hashlib.sha256((HARN/'IDENTITY.json').read_bytes()).hexdigest(),'verify']


def test_independent_location_exact_bytes_import_resolution(tmp_path):
    copy=tmp_path/'independent-sandbox-harness';shutil.copytree(HARN,copy,ignore=shutil.ignore_patterns('__pycache__'))
    fake=tmp_path/'fake';fake.mkdir();(fake/'aios_core.py').write_text('raise RuntimeError("substitution linked")')
    completed=subprocess.run(command(copy),env=dict(os.environ,PYTHONPATH=str(fake)),capture_output=True,text=True)
    assert completed.returncode==0,completed.stderr
    status=json.loads(completed.stdout)
    assert status['marker']=='HARNESS_IDENTITY_AND_ROUTER_PASS'
    assert status['semantic_callback_router_disabled']=='PASS'


@pytest.mark.parametrize('attack',['source','manifest','added_file','scripted_router'])
def test_identity_substitution_fails_before_start(tmp_path,attack):
    copy=tmp_path/'harness';shutil.copytree(HARN,copy,ignore=shutil.ignore_patterns('__pycache__'))
    if attack=='manifest':(copy/'IDENTITY.json').write_text('{}')
    elif attack=='added_file':(copy/'r005/synthetic_resident.py').write_text('def decide():return "prewritten"')
    elif attack=='scripted_router':
        with (copy/'r005/safe_runner.py').open('a') as f:
            f.write('\ndef malicious(snapshot):\n    if snapshot.user_input == "keyword":\n        return ModelDirective(response="prewritten")\n')
        with pytest.raises(ValueError):static_scan(copy)
    else:
        with (copy/'r005/safe_runner.py').open('a') as f:f.write('\nSUBSTITUTED=True\n')
    completed=subprocess.run(command(copy),capture_output=True,text=True)
    assert completed.returncode!=0
    assert 'BLOCKED' in completed.stderr


def test_executable_substitution_rejected(tmp_path):
    alias=tmp_path/'substituted-python'
    shutil.copyfile(Path(os.environ['APPROVED53_PYTHON']).resolve(),alias);alias.chmod(0o700)
    completed=subprocess.run(command(HARN,str(alias)),capture_output=True,text=True)
    assert completed.returncode!=0
    assert 'executable path substitution' in completed.stderr


def test_signer_not_importable_in_recovery_caller():
    with pytest.raises(ImportError):__import__('r005.publisher_service')
