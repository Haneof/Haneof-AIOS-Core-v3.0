"""Synthetic protocol only. A local bare Git remote represents remote durability."""
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import hashlib
import pytest

from r005.safe_runner import init,run
from r005.bridge import ExchangeBridge
from r005.canonical import canonical_json_bytes
from aios_core.headless.core import HeadlessConfig,HeadlessCore
from aios_core.contracts.enums import WakeSource
from aios_core.wake.service import WakeSignalRequest
from datetime import datetime,timezone
from aios_core.runtime.cognitive_runtime import ModelDirective

SOURCE=Path(__file__).resolve().parents[2]
HARN=SOURCE/'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness'


def entry(harn=None):
    harn=harn or HARN
    digest=hashlib.sha256((HARN/'IDENTITY.json').read_bytes()).hexdigest()
    return [os.environ['APPROVED53_PYTHON'],'-I',str(harn/'launch.py'),
        '--source-repo',str(SOURCE),'--identity-sha256',digest]


def setup(tmp_path,monkeypatch):
    from tools.c15_persistence import backend
    monkeypatch.setattr(backend,'WORKSPACE',tmp_path)
    repo=tmp_path/'git';remote=tmp_path/'remote.git';repo.mkdir()
    subprocess.run(['git','init','--bare',str(remote)],check=True,capture_output=True)
    subprocess.run(['git','init',str(repo)],check=True,capture_output=True)
    subprocess.run(['git','remote','add','origin',str(remote)],cwd=repo,check=True)
    root=tmp_path/'synthetic-root'
    init(root,'synthetic-53-run','synthetic-53-session','user_1',repo)
    return root,repo


@pytest.mark.parametrize('scenario',['due','user','summary','delivered'])
def test_real_core_external_publisher_with_c15_remote_barriers(tmp_path,monkeypatch,scenario):
    root,repo=setup(tmp_path,monkeypatch)
    harn=HARN
    if scenario=='delivered':
        from test_artifact_delivery import materialize
        target,result=materialize(tmp_path,HARN.parent/'artifacts/resident-harness.tar.gz')
        assert result.returncode==0,result.stderr
        harn=target/'harness'
    world=root/'state/runtime/world.sqlite';index=root/'state/runtime/index.sqlite'
    core=HeadlessCore(config=HeadlessConfig(world_path=world,index_path=index),
        model_handler=lambda _s: (_ for _ in ()).throw(AssertionError('setup cannot decide'))).start()
    moment=datetime(2026,10,13,tzinfo=timezone.utc)
    if scenario=='due':
        core.runtime.wake_bus.emit(WakeSignalRequest(wake_source=WakeSource.SAFETY,
            rule_id='synthetic-boundary',observed_at=moment,priority=100,dedupe_key='synthetic-boundary'))
    if scenario=='summary':
        from datetime import timedelta
        # Current Core preserves eight recent turns and summarizes closed chunks
        # of twelve older turns. Twenty setup turns exercise the normal trigger.
        for i in range(1,21):
            core.runtime.ingestor.commit_turn(session_id='synthetic-53-session',turn_index=i,
                user_text='synthetic history '+str(i),assistant_text='synthetic setup bytes',
                occurred_at=moment+timedelta(seconds=i))
        assert len(core.runtime.continuity._complete_turns(session_id='synthetic-53-session'))==20
        assert core.runtime.continuity.prepare_next_round_summary(session_id='synthetic-53-session',before_turn=21,recent_turn_limit=8,summary_chunk_turns=12) is not None
        moment=moment+timedelta(seconds=21)
    core.stop()
    # Synthetic setup alters only a private test world; publish its state before running.
    from tools.c15_persistence.backend import RunBackend
    from r005.safe_runner import barrier
    b=RunBackend.open(root,run_id='synthetic-53-run',session_id='synthetic-53-session')
    barrier(b,repo,'synthetic-wake-staged');b.release()
    if scenario=='summary':
        from aios_core.storage.sqlite_store import SQLiteWorldStore
        from aios_core.context.continuity import ConversationContinuityService
        persisted=ConversationContinuityService(store=SQLiteWorldStore(world),index=None,subject_id='user_1')
        assert len(persisted._complete_turns(session_id='synthetic-53-session'))==20
        assert persisted.prepare_next_round_summary(session_id='synthetic-53-session',before_turn=21,recent_turn_limit=8,summary_chunk_turns=12) is not None
    spec={'mode':'due' if scenario=='due' else 'user','at':moment.isoformat(),'cursor':1,
        'event_id':'synthetic-event-1','turn_index':21 if scenario=='summary' else 1,
        'user_input':'' if scenario=='due' else 'synthetic USER bytes','timeout':30}
    specpath=tmp_path/'operation.json';specpath.write_bytes(canonical_json_bytes(spec))
    env=dict(os.environ,C15_PERSISTED_WORKSPACE=str(tmp_path))
    runner=subprocess.Popen(entry(harn)+['run',
        '--root',str(root),'--run-id','synthetic-53-run','--session-id','synthetic-53-session',
        '--operation',str(specpath),'--persistence-repo',str(repo)],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    authorization_line=runner.stdout.readline()
    assert authorization_line.startswith('RESIDENT_PUBLISH_AUTHORIZATION='), runner.stderr.read() if not authorization_line else authorization_line
    authorization=authorization_line.strip().split('=',1)[1]
    answered=set();kinds=set();deadline=time.monotonic()+90
    while runner.poll() is None and time.monotonic()<deadline:
        for ready in (root/'mailbox/operations').glob('*/ready/*.json'):
            exchange=ready.parent.parent;rid=ready.stem
            if rid in answered:continue
            b=ExchangeBridge(exchange);request=b.requests.payload(rid)
            kinds.add(request['kind'])
            if request['kind']=='model_directive':
                binding=request['body']['provenance_binding']
                directive={'silence':True,'provenance':binding} if scenario=='due' else {
                    'response':'synthetic USER return','provenance':binding}
            else:directive={'text':'synthetic Summary transport bytes'}
            response={'response_version':1,'request_id':rid,'request_sha256':b.request_sha256(rid),
                'authored_by':'EXTERNAL_CURRENT_RESIDENT_SESSION',
                'directive':directive}
            path=tmp_path/(rid+'.json');path.write_bytes(canonical_json_bytes(response))
            base=entry(harn)+['publish',
                '--exchange',str(exchange),'--request-id',rid,'--response',str(path),
                '--persistence-repo',str(repo)]
            attack=subprocess.run(base,input='recovery-forged-authorization\n',capture_output=True,text=True,timeout=10)
            assert attack.returncode!=0
            assert 'external Resident authorization required' in attack.stderr
            assert b.published_response_record(rid) is None
            assert not (exchange/'proofs'/f'{rid}.json').exists()
            if not answered:
                for mutation in ('hash','request_id','schema'):
                    broken=dict(response)
                    if mutation=='hash':broken['request_sha256']='0'*64
                    elif mutation=='request_id':broken['request_id']='stale-request'
                    else:broken['directive']={'unrecognized_field':True}
                    path.write_bytes(canonical_json_bytes(broken))
                    rejected=subprocess.run(base,input=authorization+'\n',capture_output=True,text=True,timeout=10)
                    assert rejected.returncode!=0
                    assert b.published_response_record(rid) is None
                    assert not (exchange/'proofs'/f'{rid}.json').exists()
                path.write_bytes(canonical_json_bytes(response))
            completed=subprocess.run(base,
                input=authorization+'\n',capture_output=True,text=True,timeout=40)
            assert completed.returncode==0,completed.stderr
            published=json.loads(completed.stdout)
            assert published['publisher_pid']!=os.getpid()
            assert published['remote_commit']
            assert b.responses.path_for(rid).read_bytes()==path.read_bytes()
            answered.add(rid)
        time.sleep(.02)
    stdout,stderr=runner.communicate(timeout=5)
    assert runner.returncode==0,stderr
    results=[json.loads(stdout)]
    assert answered
    import sqlite3
    db=sqlite3.connect(world)
    signed_core_returns=sum(json.loads(p.read_bytes())['core_proof'] is not None
        for p in (root/'mailbox/operations').glob('*/proofs/*.json'))
    assert signed_core_returns>0
    assert db.execute('SELECT COUNT(*) FROM background_model_response_receipts').fetchone()[0]==signed_core_returns
    db.close()
    reopened=RunBackend.open(root,run_id='synthetic-53-run',session_id='synthetic-53-session')
    from tools.c15_persistence.relay import RelayJournal
    j=RelayJournal(reopened)
    for rid in j.request_ids():assert j.recovery(rid)['state']=='applied'
    reopened.release()
    before=world.read_bytes()
    assert run(root,'synthetic-53-run','synthetic-53-session',repo,spec)==results[0]
    assert world.read_bytes()==before
    replay=subprocess.run(base,input='',capture_output=True,text=True,timeout=10)
    assert replay.returncode==0,replay.stderr
    assert json.loads(replay.stdout)['idempotent_replay'] is True
    assert authorization.encode() not in b''.join(p.read_bytes() for p in root.rglob('*') if p.is_file())
    channel=Path(json.loads((exchange/'service.json').read_bytes())['socket'])
    assert authorization.encode() not in b''.join(p.read_bytes() for p in channel.rglob('*') if p.is_file())
    assert (exchange/'runtime-handler-identity.json').is_file()
    if scenario=='summary':assert 'round_summary' in kinds
