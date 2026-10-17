import hashlib
import json
import os
from pathlib import Path
import subprocess
import pytest

SOURCE=Path(__file__).resolve().parents[2]
BASE=SOURCE/'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005'
PACKET=json.loads((BASE/'RESIDENT_SAFE_LAUNCH_PACKET.json').read_bytes())


def materialize(tmp_path,artifact):
    target=tmp_path/'delivery'
    env=dict(os.environ,ARTIFACT=str(artifact),DELIVERY_DIR=str(target))
    result=subprocess.run(['bash','-c',PACKET['cross_sandbox_harness_materialization']['materialization_command']],
        env=env,capture_output=True,text=True,timeout=15)
    return target,result


def test_exact_tar_into_independent_sandbox_runs_pinned_entry(tmp_path):
    artifact=BASE/'artifacts/resident-harness.tar.gz'
    target,result=materialize(tmp_path,artifact)
    assert result.returncode==0,result.stderr
    assert 'HARNESS_MATERIALIZATION_PASS' in result.stdout
    identity=PACKET['current_main_harness_identity']['identity_sha256']
    verify=PACKET['semantic_router_disabled_verification']['command']
    env=dict(os.environ,HARNESS=str(target/'harness'),SOURCE_REPO=str(SOURCE))
    completed=subprocess.run(['bash','-c',verify],env=env,capture_output=True,text=True,timeout=15)
    assert completed.returncode==0,completed.stderr
    assert json.loads(completed.stdout)['marker']=='HARNESS_IDENTITY_AND_ROUTER_PASS'
    assert hashlib.sha256((target/'harness/IDENTITY.json').read_bytes()).hexdigest()==identity
    _,repeated=materialize(tmp_path,artifact)
    assert repeated.returncode!=0


def test_artifact_substitution_rejected_before_materialization(tmp_path):
    artifact=tmp_path/'tampered.tar.gz'
    artifact.write_bytes((BASE/'artifacts/resident-harness.tar.gz').read_bytes()+b'replaced')
    target,result=materialize(tmp_path,artifact)
    assert result.returncode!=0 and 'artifact substitution' in result.stderr
    assert not target.exists()
