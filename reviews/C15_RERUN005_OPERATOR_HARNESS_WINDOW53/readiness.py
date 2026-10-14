"""Operator author gate only. PASS never authorizes a Resident launch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import xml.etree.ElementTree as ET


def sha(raw):return hashlib.sha256(raw).hexdigest()


def check(repo):
    evidence=repo/'reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW53'
    base=repo/'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005'
    packet=json.loads((base/'RESIDENT_SAFE_LAUNCH_PACKET.json').read_bytes())
    required=('runner_invocation','publisher_invocation','runtime_module_identity',
        'semantic_router_disabled_verification','current_main_harness_identity','cross_sandbox_harness_materialization',
        'run_state_binding','resident_response_handoff','recovery_failure_behavior')
    assert all(packet.get(k) for k in required),'mandatory packet field missing'
    assert packet['current_main_harness_identity']['approval_state']=='PENDING_FRESH_INDEPENDENT_ACCEPTANCE_AND_PM'
    assert not any(k in packet for k in ('fixture_binding','post_merge_main_gate','habitation_tree','c15_tests_tree'))
    identity=(base/'harness/IDENTITY.json').read_bytes()
    assert sha(identity)==packet['current_main_harness_identity']['identity_sha256']
    manifest=json.loads(identity)
    assert manifest['harness_files']==packet['current_main_harness_identity']['all_harness_files']
    transfer=packet['cross_sandbox_harness_materialization']
    artifact=repo/transfer['artifact_repository_path']
    assert sha(artifact.read_bytes())==transfer['artifact_sha256']
    with tarfile.open(artifact,'r:gz') as t:
        members=t.getmembers()
        assert sorted(m.name for m in members)==sorted(transfer['closed_members'])
        assert all(m.isfile() for m in members)
        for m in members:
            rel=m.name.removeprefix('harness/')
            expected=identity if rel=='IDENTITY.json' else (base/'harness'/rel).read_bytes()
            assert t.extractfile(m).read()==expected,'artifact does not match source'
    xml=evidence/'SYNTHETIC_RESULTS.xml'
    suites=ET.parse(xml).getroot();cases=suites.findall('.//testcase')
    assert len(cases)>=38,'incomplete nonempty test matrix'
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    coverage=json.loads((evidence/'COVERAGE.json').read_bytes())
    for references in coverage['cases'].values():
        for ref in references:
            if '.py::' not in ref:continue
            file,name=ref.split('::',1);module=Path(file).stem
            assert any(c.get('classname','').endswith(module) and
                (c.get('name')==name or c.get('name','').startswith(name+'[')) for c in cases),'missing required case: '+ref
    assert not suites.findall('.//failure') and not suites.findall('.//error') and not suites.findall('.//skipped')
    red=(evidence/'RED.json').read_bytes()
    assert sha(red)==(evidence/'RED.sha256').read_text().split()[0],'frozen RED evidence changed'
    original=subprocess.run(['git','show','271fa28d695efaeb1c888d93024eeddac9c8aa9f:'+str((base/'RESIDENT_SAFE_LAUNCH_PACKET.json').relative_to(repo))],cwd=repo,check=True,capture_output=True).stdout
    assert sha(original)==json.loads(red)['packet_sha256']
    for directory,key in [('src/aios_core','core_tree'),('tools/c15_persistence','c15_tree')]:
        actual=subprocess.run(['git','rev-parse','origin/main:'+directory],cwd=repo,check=True,capture_output=True,text=True).stdout.strip()
        assert actual==manifest[key],'main implementation drift'
    result=subprocess.run(['bash','-c',packet['semantic_router_disabled_verification']['command']],
        env=dict(os.environ,HARNESS=str(base/'harness'),SOURCE_REPO=str(repo)),capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['marker']=='HARNESS_IDENTITY_AND_ROUTER_PASS'
    protected=subprocess.run(['git','diff','--name-only','origin/main','--','src','tools','tests','.github','pyproject.toml'],cwd=repo,check=True,capture_output=True,text=True).stdout
    assert not protected,'protected files modified'
    return {'marker':'WINDOW53_AUTHOR_PREFLIGHT_PASS','tests':len(cases),'failures':0,'errors':0,'skipped':0,
        'junit_sha256':sha(xml.read_bytes()),'identity_sha256':sha(identity),'artifact_sha256':sha(artifact.read_bytes()),
        'packet_sha256':sha((base/'RESIDENT_SAFE_LAUNCH_PACKET.json').read_bytes()),
        'resident_launch_authorized':False,'real_resident_started':False,
        'disposition':'READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE / DO NOT MERGE'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True)
    a=p.parse_args()
    try:print(json.dumps(check(a.repo.resolve()),indent=2))
    except Exception as exc:
        print(json.dumps({'result':'BLOCKED','reason':str(exc)}));raise SystemExit(2)
