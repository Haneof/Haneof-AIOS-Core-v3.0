"""Only fresh synthetic events/Worlds and explicit TEST DOUBLE model responses.
The real sealed fixture and private A package are never read by this suite.
"""
import importlib.util
import io
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from tools.c15_preflight.audit import AuditError, FIXTURE_HASH, digest
from tools.c15_preflight.driver import Driver, DriverBlocked, ReleasePort, atomic_json
from tools.c15_preflight.freeze import freeze
from tools.c15_preflight.restart import restore_frozen, restart_plan
from tools.c15_preflight.transport import StreamBridge, Trace, TransportError, encode

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)
REPO = Path(__file__).resolve().parents[2]


class Peer:
    """Explicit synthetic test peer. Never installed as a live model adapter."""
    def __init__(self, output, *, fail_kind=None, mutate=None):
        self.output, self.fail_kind, self.mutate = output, fail_kind, mutate
        self.calls = []

    def readline(self, _):
        request = json.loads(self.output.getvalue().splitlines()[-1])
        self.calls.append(request)
        if request["kind"] == self.fail_kind:
            return ""
        value = {k: request[k] for k in ("request_id", "kind", "input_sha256")}
        value["output"] = {"response": "SYNTHETIC TEST RESPONSE"} if request["kind"] == "runtime" else {"text": "SYNTHETIC TEST SUMMARY"}
        if self.mutate:
            self.mutate(value)
        return encode(value) + "\n"


def bindings(tmp_path):
    path = REPO / 'reviews/internal_habitation/c15-rcc/v1/release/bindings.py'
    spec = importlib.util.spec_from_file_location('synthetic_c15_bindings', path)
    b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    root = tmp_path / 'synthetic'; (root / 'fixture').mkdir(parents=True)
    events = []
    for n in range(1, 31):
        user = n % 2 == 1
        events.append(dict(sequence=n, phase='A' if n <= 13 else 'B' if n <= 22 else 'C',
            event_id=f'synthetic-{n}', occurred_at=(NOW + timedelta(hours=n)).isoformat(),
            dimension='dim:conversation' if user else 'dim:synthetic', source_kind='conversation' if user else 'synthetic_sensor',
            source_class='USER' if user else 'PLATFORM', modality='text', resident_visible_payload=f'SYNTHETIC event {n}'))
    fixture = dict(fixture_version=b.FIXTURE_VERSION, schema_version=b.SCHEMA_VERSION,
                   release_contract_version=b.CONTRACT_VERSION, subject_id='user_1', events=events)
    f = root / 'fixture/sealed_fixture.json'; f.write_text(json.dumps(fixture))
    # Configure isolated copies of the frozen adapters, never edit sealed files.
    b.C15_ROOT = root; b.FIXTURE_SHA256 = 'sha256:' + digest(f)
    manifest = dict(fixture_version=b.FIXTURE_VERSION, fixture_sha256=b.FIXTURE_SHA256,
        schema_version=b.SCHEMA_VERSION, release_contract_version=b.CONTRACT_VERSION,
        release_operator_version=b.OPERATOR_VERSION, ingest_adapter_version=b.INGEST_ADAPTER_VERSION,
        fixture_binding_version=b.BINDING_VERSION, canonical_conversation_adapter_version=b.CANONICAL_ADAPTER_VERSION,
        canonical_conversation_binding_version=b.CANONICAL_BINDING_VERSION, subject_id='user_1',
        event_count=30, phase_a_count=13, phase_b_count=9, phase_c_count=8,
        handoffs=dict(a_to_b=dict(phase_a_final_cursor=13,phase_b_first_cursor=14),
                      b_to_c=dict(phase_b_final_cursor=22,phase_c_first_cursor=23)))
    (root / 'fixture/fixture_manifest.json').write_text(json.dumps(manifest))
    return b.load_release_operator(), b.load_canonical_adapter(), b.load_mechanical_adapter()


def setup(tmp_path, *, fail_kind=None, mutate=None, stop=3, modules=None, restore=None):
    modules = modules or bindings(tmp_path)
    run = tmp_path / 'run'
    if restore is None:
        run.mkdir()
    else:
        restore_frozen(restore, run, manifest_sha256=digest(restore / 'manifest.json'))
    store = SQLiteWorldStore(run / 'private_world.sqlite')
    index = WorldSearchIndex(run / 'world_index.sqlite', store=store)
    trace = Trace(run / 'trace.jsonl', store.current_world_revision)
    out = io.StringIO(); peer = Peer(out, fail_kind=fail_kind, mutate=mutate)
    bridge = StreamBridge(peer, out, trace)
    runtime = FusedTurnRuntime(store=store,index=index,model_handler=bridge.model,
                              round_summary_handler=bridge.round_summary,dimension_summary_handler=bridge.dimension_summary)
    port = ReleasePort(*modules, run/'release_state.json',run/'private_world.sqlite','A')
    clock = NOW
    if restore is None:
        port.invoke(modules[0].cmd_init)
    else:
        clock = datetime.fromisoformat(json.loads((run/'driver_state.json').read_text())['clock'])
    driver = Driver(runtime,trace,port,run,session='synthetic-session',clock=clock,stop_sequence=stop)
    return driver, peer, modules


def test_formal_release_canonical_user_sensor_ack_clock_and_stop(tmp_path):
    d, peer, _ = setup(tmp_path)
    assert d.step() and d.step() and d.step() and not d.step()
    state = d.port.read_state()
    assert state['last_acked_sequence'] == 3 and state['pending_reveal'] is None
    assert [r['binding_mode'] for r in state['receipts']] == ['canonical_user_turn','fixture_observation','canonical_user_turn']
    assert d.state['next_turn'] == 3 and d.state['clock'] == (NOW+timedelta(hours=3)).isoformat()
    assert d.runtime.index.watermark() == d.runtime.store.current_world_revision()
    requests = [r for r in peer.calls if r['kind']=='runtime']
    assert not any(r['input']['wake_reason']=='periodic_review' for r in requests)  # first deadline is 24h
    lines = [json.loads(s) for s in Path(d.trace.path).read_text().splitlines()]
    kinds = [r['kind'] for r in lines]
    assert kinds.index('durable_ack') < kinds.index('event_processing_complete') < kinds.index('released_input',1)
    # No semantic result/cockpit/transcript is injected from restart metadata.
    assert 'SYNTHETIC TEST RESPONSE' not in d.state_path.read_text()
    d.close();d.trace.close()


def test_duplicate_ack_and_duplicate_reveal_rejected_by_existing_release(tmp_path):
    d, _, _ = setup(tmp_path)
    event=d.port.reveal()
    with pytest.raises(Exception, match='duplicate reveal'):
        d.port.reveal()
    receipt=d.port.ingest(event,session='synthetic-session',turn=1)
    d.port.ack(event,receipt,session='synthetic-session',turn=1)
    with pytest.raises(Exception, match='pending reveal'):
        d.port.ack(event,receipt,session='synthetic-session',turn=1)
    d.close();d.trace.close()


@pytest.mark.parametrize('field', ['request_id','kind','input_sha256'])
def test_reply_binds_request_kind_and_exact_input(tmp_path, field):
    d, peer, _=setup(tmp_path,mutate=lambda v:v.update({field:'wrong'}))
    with pytest.raises(TransportError): d.step()
    assert d.state['stage']=='FAILED'
    calls=len(peer.calls)
    with pytest.raises(DriverBlocked): d.step()
    assert len(peer.calls)==calls
    # ACK of durable input is allowed, but processing/next release is NOT.
    assert d.port.read_state()['last_acked_sequence']==1
    assert d.state['completed_sequence']==0
    d.close();d.trace.close()


def test_core_caught_round_summary_disconnect_is_not_success(tmp_path):
    d, _, _=setup(tmp_path,fail_kind='round_summary')
    d.runtime.recent_turn_limit=0; d.runtime.summary_chunk_turns=1
    with pytest.raises(TransportError,match='Core caught callback failure'): d.step()
    lines=[json.loads(s) for s in Path(d.trace.path).read_text().splitlines()]
    assert any(r['kind']=='runtime_return_failed' for r in lines)
    assert not any(r['kind']=='event_processing_complete' for r in lines)
    assert d.runtime.metering.list_model_calls(subject_id='user_1')
    assert d.state['stage']=='FAILED'
    d.close();d.trace.close()


def test_single_writer_and_interrupted_ack_never_implicitly_replayed(tmp_path):
    d, _, modules=setup(tmp_path)
    with pytest.raises(BlockingIOError):
        Driver(d.runtime,d.trace,d.port,d.directory,session='synthetic-session',clock=NOW,stop_sequence=3)
    d.transition('ACKING');d.close()
    with pytest.raises(DriverBlocked,match='interrupted'):
        Driver(d.runtime,d.trace,d.port,d.directory,session='synthetic-session',clock=NOW,stop_sequence=3)
    d.trace.close()


def test_clean_freeze_restart_continues_no_transcript_replay(tmp_path):
    d, _, modules=setup(tmp_path)
    d.step()
    final=tmp_path/'frozen'; manifest=freeze(d,final)
    assert manifest['world_revision']==manifest['index_watermark']
    assert d.state['stage']=='FROZEN'
    with pytest.raises(DriverBlocked): d.step()
    d.close();d.trace.close()
    other=tmp_path/'other';other.mkdir()
    resumed,peer,_=setup(other,modules=modules,restore=final)
    assert resumed.step() and resumed.state['completed_sequence']==2
    assert all(r['input'].get('user_input')!='SYNTHETIC event 1' for r in peer.calls)
    assert resumed.state['next_turn']==2
    resumed.close();resumed.trace.close()


def test_wal_commits_and_simultaneous_writer_reservations(tmp_path,monkeypatch):
    import tools.c15_preflight.freeze as module
    d,_,_=setup(tmp_path);d.step()
    # Keep WAL live; no file-copy snapshot can be substituted.
    conn=sqlite3.connect(d.runtime.store.db_path)
    conn.execute('PRAGMA wal_autocheckpoint=0')
    conn.execute('CREATE TABLE synthetic_wal_sentinel(value)');conn.execute("INSERT INTO synthetic_wal_sentinel VALUES('committed')");conn.commit()
    assert Path(str(d.runtime.store.db_path)+'-wal').stat().st_size>0
    original=module.backup;checked=[]
    def check(src,dst):
        for path in (d.runtime.store.db_path,d.runtime.index.db_path):
            with sqlite3.connect(path,timeout=0) as writer:
                with pytest.raises(sqlite3.OperationalError,match='locked'):
                    writer.execute('BEGIN IMMEDIATE')
            checked.append(path)
        original(src,dst)
    monkeypatch.setattr(module,'backup',check)
    final=tmp_path/'frozen';freeze(d,final)
    with sqlite3.connect(final/'private_world.sqlite') as copy:
        assert copy.execute('SELECT value FROM synthetic_wal_sentinel').fetchone()==('committed',)
    assert len(checked)==4
    conn.close();d.close();d.trace.close()


def test_snapshot_failure_never_publishes_success(tmp_path,monkeypatch):
    import tools.c15_preflight.freeze as module
    d,_,_=setup(tmp_path);d.step()
    original=module.backup
    def fail_second(src,dst):
        if dst.name=='world_index.sqlite': raise OSError('synthetic backup interruption')
        original(src,dst)
    monkeypatch.setattr(module,'backup',fail_second)
    final=tmp_path/'frozen'
    with pytest.raises(OSError): freeze(d,final)
    assert not final.exists() and d.state['stage']=='FAILED'
    assert not list(tmp_path.glob('.c15-freeze-*'))
    d.close();d.trace.close()


def test_freeze_detects_noncooperating_release_mutation(tmp_path,monkeypatch):
    import tools.c15_preflight.freeze as module
    d,_,_=setup(tmp_path);d.step();original=module.backup
    def tamper(src,dst):
        original(src,dst)
        d.port.state.write_text(d.port.state.read_text()+' ')
    monkeypatch.setattr(module,'backup',tamper)
    with pytest.raises(DriverBlocked,match='source changed'):
        freeze(d,tmp_path/'frozen')
    assert not (tmp_path/'frozen').exists()
    d.close();d.trace.close()


def test_real_fixture_port_cannot_be_activated():
    with pytest.raises(DriverBlocked,match='real C15'):
        ReleasePort(SimpleNamespace(FIXTURE_SHA256=FIXTURE_HASH),None,None,None,None,'B')


def test_dimension_summary_normal_path_and_batch_deferral(tmp_path):
    d,peer,_=setup(tmp_path);d.step()
    # Independent synthetic clock check, no real cursor or provider.
    due=d.due_work(NOW+timedelta(days=2))
    assert any(r['kind']=='dimension_summary' for r in peer.calls)
    assert due['summary_commits'] and due['pending_wakes']  # Core coalescing window held; no forced clock jump.
    d.close();d.trace.close()


def test_clock_reuses_existing_scheduler_at_intermediate_deadline_without_future_input(tmp_path):
    d,peer,_=setup(tmp_path);d.step()
    clock=d.clock
    old = len(peer.calls)
    # No next event ingested. Existing clock must tick at the 24h boundary, not
    # postpone every Review to the final 49h target or observe future input.
    result=clock.advance_to(NOW+timedelta(hours=49))
    assert result['periodic_reviews'][0]['at']==(NOW+timedelta(hours=24)).isoformat()
    requests=peer.calls[old:]
    assert not any('SYNTHETIC event 2' in encode(r) for r in requests)
    d.close();d.trace.close()


def test_clock_regression_stops_before_ingest(tmp_path):
    d,_,_=setup(tmp_path)
    d.state['clock']=(NOW+timedelta(days=1)).isoformat();d.checkpoint()
    with pytest.raises(DriverBlocked,match='clock regression'):d.step()
    assert d.port.read_state()['last_acked_sequence']==0
    assert d.runtime.store.current_world_revision()==0
    d.close();d.trace.close()


def test_summary_error_stops_scheduler_phase_before_next_release(tmp_path):
    d,_,_=setup(tmp_path,fail_kind='dimension_summary');d.step()
    with pytest.raises(TransportError):d.due_work(NOW+timedelta(days=2))
    with pytest.raises(DriverBlocked):d.step()
    assert d.port.read_state()['last_acked_sequence']==1
    d.close();d.trace.close()


def test_unknown_usage_and_core_budget_result_not_promoted_to_completion(tmp_path):
    d,_,_=setup(tmp_path,mutate=lambda v:v.update(output={"capability_calls":[{"name":"search_world","arguments":{"query":"synthetic"}}]}))
    d.runtime.cognitive_runtime.max_tool_rounds=0
    with pytest.raises(DriverBlocked,match='unfinished'):d.step()
    assert d.state['stage']=='FAILED'
    meter=d.runtime.metering.list_model_calls(subject_id='user_1')
    assert len(meter)==1 and meter[0].total_tokens is None
    with pytest.raises(DriverBlocked):freeze(d,tmp_path/'frozen')
    d.close();d.trace.close()


def test_closed_coordinator_cannot_execute(tmp_path):
    d,_,_=setup(tmp_path);d.close()
    with pytest.raises(DriverBlocked):d.step()
    d.trace.close()


def test_restart_manifest_pin_tamper_fails_before_copy(tmp_path):
    d,_,_=setup(tmp_path);d.step();final=tmp_path/'frozen';freeze(d,final)
    with pytest.raises(AuditError,match='manifest'):
        restore_frozen(final,tmp_path/'copy',manifest_sha256='0'*64)
    assert not (tmp_path/'copy').exists()
    d.close();d.trace.close()


def synthetic_restart():
    return dict(restart_state_format='c15-rcc-resident-a-restart-state-v1',note='SYNTHETIC NOT FOR RESIDENT',
        session_id='synthetic-old',subject_id='user_1',conversation_turn_index=7,
        final_virtual_clock=NOW.isoformat(),next_periodic_review_at=(NOW+timedelta(hours=24)).isoformat(),
        review_interval_hours=24,final_world_revision=88,final_index_watermark=88,done_at_cursor=13,
        release_state_next_sequence=14,process_ended='SYNTHETIC STOP')


def test_restart_routes_fresh_session_and_only_mechanical_state():
    plan=restart_plan(synthetic_restart(),'synthetic-new')
    assert plan['session_id']=='synthetic-new' and plan['next_turn']==1
    assert not plan['launchable']
    assert 'SYNTHETIC NOT FOR RESIDENT' not in encode(plan)
    assert 'synthetic-old' not in encode(plan)


@pytest.mark.parametrize('key,value', [('transcript','forbidden'),('review_interval_hours',True),
    ('review_interval_hours',12),('final_virtual_clock','2030-01-01'),('done_at_cursor',22),
    ('next_periodic_review_at',NOW.isoformat()),('final_index_watermark',87)])
def test_restart_malformed_or_unreviewed_state_rejected(key,value):
    raw=synthetic_restart();raw[key]=value
    with pytest.raises((AuditError,DriverBlocked)):restart_plan(raw,'synthetic-new')


def test_restart_cannot_reuse_a_session():
    with pytest.raises(AuditError,match='reuse'):restart_plan(synthetic_restart(),'synthetic-old')
