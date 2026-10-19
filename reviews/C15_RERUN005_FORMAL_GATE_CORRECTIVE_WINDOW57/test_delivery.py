"""Development attacks against exact closed Artifact and clean-room materializer."""
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import pytest

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = REPO/'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005'
HARN = BASE/'harness'
ART = BASE/'artifacts/resident-harness.tar.gz'
PACKET = json.loads((BASE/'RESIDENT_SAFE_LAUNCH_PACKET.json').read_bytes())
TRANSFER = PACKET['cross_sandbox_harness_materialization']
spec = importlib.util.spec_from_file_location('closed_materializer',HERE/'materialize.py')
materializer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(materializer)
PYTHON = PACKET['approved_runtime']['prepared_venv_python']

def command(artifact, target):
    return subprocess.run(['bash','-c',TRANSFER['materialization_command']],
        env=dict(os.environ,ARTIFACT=str(artifact),DELIVERY_DIR=str(target)),
        capture_output=True,text=True,timeout=20)

def altered_archive(attack):
    buffer = io.BytesIO()
    with tarfile.open(ART,'r:gz') as original, tarfile.open(fileobj=buffer,mode='w',format=tarfile.USTAR_FORMAT) as out:
        members = original.getmembers()
        for index,m in enumerate(members):
            data = original.extractfile(m).read()
            if index == 0:
                if attack == 'duplicate':
                    out.addfile(m,io.BytesIO(data))
                elif attack == 'traversal': m.name = 'harness/../escape'
                elif attack == 'absolute': m.name = '/escape'
                elif attack == 'symlink': m.type = tarfile.SYMTYPE; m.linkname = '/escape'; m.size = 0
                elif attack == 'hardlink': m.type = tarfile.LNKTYPE; m.linkname = members[-1].name; m.size = 0
                elif attack == 'fifo': m.type = tarfile.FIFOTYPE; m.size = 0
                elif attack == 'mode': m.mode = 0o777
                elif attack == 'hash': data = bytes([data[0]^1])+data[1:]
                elif attack == 'missing': continue
                elif attack == 'extra':
                    extra = tarfile.TarInfo('harness/r005/extra.py');extra.size = 1;extra.mode = 0o644
                    out.addfile(extra,io.BytesIO(b'x'))
            out.addfile(m,io.BytesIO(data) if m.isfile() else None)
    return gzip.compress(buffer.getvalue(),mtime=0)

def test_exact_identity_and_closed_members():
    content = materializer.validate(ART.read_bytes(),TRANSFER['artifact_sha256'],TRANSFER['member_identity'])
    identity = json.loads(content['harness/IDENTITY.json'])
    assert set(content) == {'harness/IDENTITY.json'} | {'harness/'+name for name in identity['harness_files']}
    assert len(content) == 22
    for name,data in content.items():
        assert data == (BASE/name).read_bytes()
        if name != 'harness/IDENTITY.json':
            assert hashlib.sha256(data).hexdigest() == identity['harness_files'][name.removeprefix('harness/')]

def test_independent_full_source_materialization_and_pinned_verify(tmp_path):
    target = tmp_path/'independent'
    oldmask = os.umask(0o077)
    try: result = command(ART,target)
    finally: os.umask(oldmask)
    assert result.returncode == 0,result.stderr
    assert result.stdout.strip() == 'HARNESS_MATERIALIZATION_PASS'
    # Independent source directory, no Git history/governance/tests or old worktree.
    source = tmp_path/'source'
    identity = json.loads((target/'harness/IDENTITY.json').read_bytes())
    for name,digest in identity['source_files'].items():
        path = source/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((REPO/name).read_bytes());path.chmod(0o644)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    for path in source.rglob('*'):
        if path.is_dir():path.chmod(0o755)
    source.chmod(0o755)
    result = subprocess.run(['bash','-c',TRANSFER['post_materialization_command']],
        env=dict(os.environ,HARNESS=str(target/'harness'),SOURCE_REPO=str(source),PYTHONPATH='/nonexistent'),
        capture_output=True,text=True,timeout=20)
    assert result.returncode == 0,result.stderr
    status = json.loads(result.stdout)
    assert status['marker'] == 'HARNESS_IDENTITY_AND_ROUTER_PASS'
    assert status['semantic_callback_router_disabled'] == 'PASS'
    repeated = command(ART,target)
    assert repeated.returncode != 0
    assert all(path.stat().st_mode & 0o777 == 0o644 for path in (target/'harness').rglob('*') if path.is_file())

@pytest.mark.parametrize('attack',['append','truncate','flip'])
def test_transport_tampering_fails_before_destination(tmp_path,attack):
    raw = ART.read_bytes()
    raw = raw+b'x' if attack == 'append' else raw[:-1] if attack == 'truncate' else bytes([raw[0]^1])+raw[1:]
    artifact = tmp_path/'tampered.gz';artifact.write_bytes(raw)
    target = tmp_path/'target'
    result = command(artifact,target)
    assert result.returncode != 0 and 'artifact substitution' in result.stderr
    assert not target.exists()

@pytest.mark.parametrize('attack',['duplicate','traversal','absolute','symlink','hardlink','fifo','mode','hash','missing','extra'])
def test_member_validator_rejects_malicious_archive_even_with_rebound_outer_digest(attack):
    # Defense-in-depth unit attack: production packet never permits rebinding this pin.
    raw = altered_archive(attack)
    with pytest.raises(ValueError):
        materializer.validate(raw,hashlib.sha256(raw).hexdigest(),TRANSFER['member_identity'])

@pytest.mark.parametrize('existing',['directory','file','dangling_symlink','directory_symlink'])
def test_every_existing_target_fails_without_changes(tmp_path,existing):
    target = tmp_path/'target';outside = tmp_path/'outside';outside.mkdir()
    sentinel = outside/'sentinel';sentinel.write_bytes(b'untouched')
    if existing == 'directory':target.mkdir()
    elif existing == 'file':target.write_bytes(b'untouched')
    elif existing == 'dangling_symlink':target.symlink_to(tmp_path/'missing')
    else:target.symlink_to(outside,target_is_directory=True)
    result = command(ART,target)
    assert result.returncode != 0
    assert sentinel.read_bytes() == b'untouched' and list(outside.iterdir()) == [sentinel]
    if existing == 'file':assert target.read_bytes() == b'untouched'
    if existing == 'directory':assert list(target.iterdir()) == []

def test_symlink_parent_rejected(tmp_path):
    outside = tmp_path/'outside';outside.mkdir()
    parent = tmp_path/'alias';parent.symlink_to(outside,target_is_directory=True)
    result = command(ART,parent/'target')
    assert result.returncode != 0 and not (outside/'target').exists()

def test_parallel_materialization_has_one_winner(tmp_path):
    target = tmp_path/'target'
    env = dict(os.environ,ARTIFACT=str(ART),DELIVERY_DIR=str(target))
    children = [subprocess.Popen(['bash','-c',TRANSFER['materialization_command']],env=env,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
    logs = [child.communicate(timeout=20) for child in children]
    assert sorted(child.returncode for child in children) == [0,1],logs
    content = materializer.validate(ART.read_bytes(),TRANSFER['artifact_sha256'],TRANSFER['member_identity'])
    assert {str(p.relative_to(target)) for p in target.rglob('*') if p.is_file()} == set(content)
    for name,data in content.items():assert (target/name).read_bytes() == data

def test_packet_is_pending_and_excludes_historical_material():
    assert PACKET['real_resident_use_authorized'] is False
    assert PACKET['self_acceptance'] is False
    assert (PACKET['allowed_cursor_start'],PACKET['allowed_cursor_end'],PACKET['stop_after_ack_cursor'],PACKET['forbidden_next_cursor']) == (1,13,13,14)
    for item in PACKET['startup_inputs'].values():
        blob = subprocess.check_output(['git','hash-object',str(REPO/item['path'])],text=True).strip()
        assert blob == item['git_blob']
    for key in ('fixture_binding','mechanical_release_tools','post_merge_main_gate','accepted_operator_candidate','habitation_tree'):
        assert key not in PACKET
    text = json.dumps(PACKET)
    for forbidden in ('WINDOW54','WINDOW55','WINDOW56','adf391178','test_current_trusted_adapter','sealed_fixture_git_blob'):
        assert forbidden not in text
