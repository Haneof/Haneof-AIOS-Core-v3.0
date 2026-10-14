"""OPERATOR ONLY: isolated synthetic protocol probes, never Resident behavior."""
import json
import sqlite3
import threading
import time
from pathlib import Path

import pytest
from aios_core.headless.core import HeadlessConfig, HeadlessCore
from aios_core.runtime.background_attempt import BackgroundModelAttemptStore
from aios_core.runtime.live_return import live_return_authority_snapshot
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.contracts.enums import WakeSource
from aios_core.wake.service import WakeSignalRequest
from datetime import datetime,timezone
from r005.bridge import ExchangeBridge, ExchangeContractError
from draft_runner import run,publish
from r005.responses import ResponsePublishError
from r005.schema import SchemaContractError,parse_model_directive


def envelope(b, rid, directive=None):
    return json.dumps({'response_version':1,'request_id':rid,
        'request_sha256':b.request_sha256(rid),
        'authored_by':'EXTERNAL_CURRENT_RESIDENT_SESSION',
        'directive':directive if directive is not None else {'response':'synthetic-protocol-byte'}}).encode()


def request(tmp_path):
    b=ExchangeBridge(tmp_path/'exchange')
    r=b.publish_request(kind='model_directive',body={'synthetic':True})
    return b,r['request_id']


def test_durable_request_and_response_consumption(tmp_path):
    from r005.atomic import reset_counters,COUNTERS
    reset_counters()
    b,rid=request(tmp_path)
    raw=envelope(b,rid)
    publish(b.root,rid,raw)
    assert b.responses.path_for(rid).read_bytes()==raw
    assert b.consume_response(rid)==raw
    assert b.recovery_state()['complete']==[rid]
    assert COUNTERS['file_fsync']>0 and COUNTERS['dir_fsync']>0


def test_duplicate_response_exact_idempotence_and_conflict(tmp_path):
    b,rid=request(tmp_path);raw=envelope(b,rid)
    publish(b.root,rid,raw)
    assert publish(b.root,rid,raw)['idempotent_replay']
    with pytest.raises(ResponsePublishError):
        publish(b.root,rid,envelope(b,rid,{'silence':True}))
    assert b.responses.path_for(rid).read_bytes()==raw


def test_stale_response_rejected(tmp_path):
    b,rid=request(tmp_path);raw=envelope(b,rid)
    publish(b.root,rid,raw);b.consume_response(rid)
    with pytest.raises(ExchangeContractError):publish(b.root,rid,raw)


@pytest.mark.parametrize('field',['request_id','request_sha256'])
def test_hash_identity_mismatch(tmp_path,field):
    b,rid=request(tmp_path);e=json.loads(envelope(b,rid));e[field]='0'*64
    with pytest.raises(ResponsePublishError):publish(b.root,rid,json.dumps(e).encode())
    assert b.published_response_record(rid) is None


def test_invalid_directive_rejected_before_publication(tmp_path):
    b,rid=request(tmp_path)
    with pytest.raises((ValueError,SchemaContractError)):
        publish(b.root,rid,envelope(b,rid,{'response':'x','silence':True}))
    assert b.published_response_record(rid) is None


def test_missing_response_no_default_or_fallback(tmp_path):
    b,rid=request(tmp_path)
    with pytest.raises(Exception):b.await_response_bytes(rid,timeout_s=.02)
    assert b.published_response_record(rid) is None
    assert b.recovery_state()['not_submitted_allowed'] is False


@pytest.mark.parametrize('target',['request','response','ledger'])
def test_tampering_fail_closed(tmp_path,target):
    b,rid=request(tmp_path);raw=envelope(b,rid);publish(b.root,rid,raw)
    if target=='request':
        b.requests.path_for(rid).write_bytes(b'{}')
        with pytest.raises(Exception):b.requests.payload(rid)
    elif target=='response':
        b.responses.path_for(rid).write_bytes(b'{}')
        with pytest.raises(Exception):b.consume_response(rid)
    else:
        (b.root/'ledger.jsonl').write_bytes(b'{bad}\n')
        with pytest.raises(Exception):b.recovery_state()


def test_restart_reopens_same_outstanding_request(tmp_path):
    b,rid=request(tmp_path)
    reopened=ExchangeBridge(b.root)
    assert reopened.recovery_state()['open_dispatched']==[rid]
    assert reopened.request_sha256(rid)==b.request_sha256(rid)
    assert len(reopened.ledger.request_ids())==1


def test_core_zero_local_minting_authority():
    s=live_return_authority_snapshot()
    assert s['trust_conferred'] is False
    assert not hasattr(BackgroundModelAttemptStore,'record_live_provider_return')


def test_actual_user_runner_waits_for_external_bytes(tmp_path):
    spec={'world':str(tmp_path/'world.sqlite'),'index':str(tmp_path/'index.sqlite'),
        'exchange':str(tmp_path/'exchange'),'run_id':'synthetic-protocol-run',
        'session_id':'synthetic-protocol-session','subject_id':'user_1','mode':'user',
        'at':'2026-10-13T00:00:00+00:00','timeout':5,'turn_index':1,
        'user_input':'synthetic transport only'}
    outputs=[];errors=[]
    def worker():
        try:outputs.append(run(spec))
        except BaseException as exc:errors.append(exc)
    t=threading.Thread(target=worker);t.start()
    deadline=time.monotonic()+4
    root=Path(spec['exchange'])
    while time.monotonic()<deadline:
        files=list((root/'requests').glob('*.json'))
        if files:break
        time.sleep(.01)
    assert files,'actual Core never published request'
    b=ExchangeBridge(root);rid=files[0].stem
    payload=b.request_body(rid)
    assert payload['snapshot']['user_input']==spec['user_input']
    assert payload['snapshot']['capability_catalog']
    assert t.is_alive() and not outputs
    assert b.published_response_record(rid) is None
    publish(root,rid,envelope(b,rid))
    t.join(6)
    assert not t.is_alive() and not errors,repr(errors)
    assert outputs[0].runtime.response=='synthetic-protocol-byte'
    with pytest.raises(ExchangeContractError):run(spec)


def test_actual_due_work_empty_entry(tmp_path):
    spec={'world':str(tmp_path/'world.sqlite'),'index':str(tmp_path/'index.sqlite'),
        'exchange':str(tmp_path/'exchange'),'run_id':'synthetic-due-run',
        'session_id':'synthetic-due-session','subject_id':'user_1','mode':'due',
        'at':'2026-10-13T00:00:00+00:00','timeout':.1}
    result=run(spec)
    assert result.wakes==()


def test_actual_due_work_live_return_has_no_core_authenticity(tmp_path):
    world=tmp_path/'world.sqlite'; index=tmp_path/'index.sqlite'
    moment=datetime(2026,10,13,tzinfo=timezone.utc)
    def never_called(_snapshot):
        raise AssertionError('setup must not call a model')
    core=HeadlessCore(config=HeadlessConfig(world_path=world,index_path=index),
        model_handler=never_called).start()
    core.runtime.wake_bus.emit(WakeSignalRequest(wake_source=WakeSource.SAFETY,
        rule_id='synthetic-transport-only',observed_at=moment,priority=100,
        dedupe_key='synthetic-transport-only'))
    core.stop()
    spec={'world':str(world),'index':str(index),'exchange':str(tmp_path/'exchange'),
        'run_id':'synthetic-background-run','session_id':'synthetic-background-session',
        'subject_id':'user_1','mode':'due','at':moment.isoformat(),'timeout':5}
    errors=[];outputs=[]
    def worker():
        try:outputs.append(run(spec))
        except BaseException as e:errors.append(e)
    t=threading.Thread(target=worker);t.start()
    root=Path(spec['exchange']);deadline=time.monotonic()+4;files=[]
    while time.monotonic()<deadline:
        files=list((root/'requests').glob('*.json'))
        if files:break
        time.sleep(.01)
    assert files
    b=ExchangeBridge(root)
    # Normal due-work also includes genuinely due periodic review. Each actual
    # request gets separate explicit synthetic bytes, only in this probe.
    answered=set();deadline=time.monotonic()+8
    while t.is_alive() and time.monotonic()<deadline:
        for rid in b.ledger.request_ids():
            if rid not in answered:
                publish(root,rid,envelope(b,rid,{'silence':True}))
                answered.add(rid)
        time.sleep(.01)
    t.join(6)
    assert not t.is_alive() and not errors,repr(errors)
    assert outputs[0].wakes
    db=sqlite3.connect(world)
    try:
        assert db.execute('SELECT COUNT(*) FROM background_model_attempts').fetchone()[0]>0
        assert db.execute('SELECT COUNT(*) FROM background_model_response_receipts').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM background_model_return_handoffs').fetchone()[0]==0
    finally:db.close()


def test_historical_publisher_envelope_is_not_schema_proof(tmp_path):
    b,rid=request(tmp_path)
    invalid=envelope(b,rid,{'response':'x','silence':True})
    # RED compatibility evidence: historical publisher commits invalid directive.
    b.responses.publish_bytes(request_id=rid,response_bytes=invalid)
    assert b.published_response_record(rid) is not None
    with pytest.raises(ValueError):parse_model_directive(json.loads(invalid))


def test_accepted_relay_requires_authentication_before_application(tmp_path,monkeypatch):
    from tools.c15_persistence import backend
    from tools.c15_persistence.relay import RelayJournal,REQUEST_FIELDS
    monkeypatch.setattr(backend,'WORKSPACE',tmp_path)
    b=backend.RunBackend.create(tmp_path/'synthetic-run',run_id='synthetic-run',
        session_id='synthetic-session',subject_id='user_1',phase='SYNTHETIC')
    try:
        j=RelayJournal(b,create=True)
        md={k:'synthetic-'+k for k in REQUEST_FIELDS}
        md.update(run_id='synthetic-run',session_id='synthetic-session',cursor=1,round=0)
        j.stage(md,b'outbound',generation=0)
        rid=md['model_request_id'];j.expose(rid);j.stage_reply(rid,b'external bytes')
        with pytest.raises(backend.BackendError):j.begin_applying(rid)
        assert j.recovery(rid)['state']=='reply-staged'
    finally:b.release()


@pytest.mark.parametrize('raw',[b'{"response_version":1,"response_version":1}',b'{"x":NaN}'])
def test_ambiguous_response_json_fails_closed(raw):
    from r005.payload import parse
    with pytest.raises(ValueError):parse('model_directive',raw)


@pytest.mark.parametrize('point',['request','response','response_replay'])
def test_durability_error_never_becomes_publication_success(tmp_path,monkeypatch,point):
    from r005 import atomic
    b,rid=request(tmp_path);raw=envelope(b,rid)
    if point=='response_replay':publish(b.root,rid,raw)
    original=b.responses.path_for(rid).read_bytes() if point=='response_replay' else None
    def fail_fsync(_fd):raise OSError('synthetic durability barrier unavailable')
    from r005.ledger import LedgerError
    before=list(b.ledger.request_ids())
    with monkeypatch.context() as fault:
        fault.setattr(atomic.os,'fsync',fail_fsync)
        with pytest.raises(LedgerError,match='durability failed'):
            if point=='request':b.publish_request(kind='model_directive',body={'synthetic':True})
            else:publish(b.root,rid,raw)
    assert b.ledger.request_ids()==before
    if point=='response':assert b.published_response_record(rid) is None
    elif point=='response_replay':assert b.responses.path_for(rid).read_bytes()==original


def test_live_wal_busy_checkpoint_cannot_be_archived(tmp_path,monkeypatch):
    from tools.c15_persistence import backend
    from r005.safe_runner import artifacts
    monkeypatch.setattr(backend,'WORKSPACE',tmp_path)
    b=backend.RunBackend.create(tmp_path/'wal-run',run_id='wal-run',session_id='wal-session',subject_id='user_1',phase='SYNTHETIC')
    path=b.state_dir/'world.sqlite'
    writer=sqlite3.connect(path);writer.execute('PRAGMA journal_mode=WAL')
    writer.execute('CREATE TABLE synthetic(x)');writer.commit()
    reader=sqlite3.connect(path);reader.execute('BEGIN');reader.execute('SELECT * FROM synthetic').fetchall()
    writer.execute('INSERT INTO synthetic VALUES (1)');writer.commit()
    try:
        with pytest.raises(backend.BackendError,match='checkpoint busy or uncertain'):artifacts(b)
        assert (Path(str(path)+'-wal')).stat().st_size>0
    finally:reader.close();writer.close();b.release()
