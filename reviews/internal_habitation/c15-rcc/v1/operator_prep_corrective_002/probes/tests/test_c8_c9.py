import copy
import datetime as dt
import json
import pathlib
import pytest

PREFIX = 'reviews/internal_habitation/c15-rcc/v1/resident/'
APPROVED = [PREFIX + 'RESIDENT_A_CORRECTIVE_003_CLEAN_ROOM_CONTRACT.md',
    PREFIX + 'RESIDENT_A_RUN_CONTRACT.md', 'RESIDENT_SAFE_LAUNCH_PACKET.json (this file)',
    'mechanical environment/harness status emitted by the approved launch tools']


def test_c8_packet_exact_startup(package):
    packet = json.loads((package / 'RESIDENT_SAFE_LAUNCH_PACKET.json').read_text())
    assert len(packet['allowed_startup_inputs']) == 4
    assert set(packet['allowed_startup_inputs']) == set(APPROVED)


@pytest.mark.parametrize('mutation', ['none', 'omit_clean', 'omit_canonical', 'board', 'adjudication', 'history'])
def test_c8_audit_startup(package, mutation):
    from operator_tools.packet_audit import audit_packet
    packet = json.loads((package / 'RESIDENT_SAFE_LAUNCH_PACKET.json').read_text())
    packet['allowed_startup_inputs'] = list(APPROVED)
    if mutation == 'omit_clean':
        packet['allowed_startup_inputs'].remove(APPROVED[0])
    elif mutation == 'omit_canonical':
        packet['allowed_startup_inputs'].remove(APPROVED[1])
    elif mutation != 'none':
        packet['allowed_startup_inputs'].append({'board':'governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md',
            'adjudication':'governance/adjudication.md', 'history':'https://github.com/Haneof/Haneof-AIOS-Core-v3.0/pull/286'}[mutation])
    report = audit_packet(packet)
    assert report['ok'] == (mutation == 'none'), report


def test_c9_due_work_entrypoint(package):
    from aios_exchange import runner
    import inspect
    assert callable(getattr(runner, 'run_due_work', None)), 'approved due-work entrypoint missing'
    assert {'world_path','index_path','subject_id','exchange_root','now','response_timeout_s','poll_interval_s'} <= set(inspect.signature(runner.run_due_work).parameters)


def test_c9_due_requires_aware_time(package, tmp_path):
    from aios_exchange import runner
    assert hasattr(runner, 'run_due_work')
    with pytest.raises(ValueError, match='timezone-aware'):
        runner.run_due_work(world_path=tmp_path/'world.sqlite', index_path=tmp_path/'index.sqlite',
            subject_id='synthetic', exchange_root=tmp_path/'exchange', now=dt.datetime(2026,9,28))
    assert not (tmp_path/'world.sqlite').exists()


def test_c9_synthetic_due_wake_exchange(package, tmp_path):
    from aios_exchange import runner
    from aios_exchange.bridge import ExchangeBridge
    from aios_core.headless import HeadlessCore, HeadlessConfig
    from aios_core.contracts.enums import WakeSource
    from aios_core.wake.service import WakeSignalRequest
    from synthetic.support import forbidden_model_call, BackgroundResponder
    assert hasattr(runner, 'run_due_work'), 'approved due-work entrypoint missing'
    now = dt.datetime(2026,9,28,12,tzinfo=dt.timezone.utc)
    world, index, exchange = tmp_path/'synthetic.sqlite', tmp_path/'synthetic.index.sqlite', tmp_path/'exchange'
    with HeadlessCore(config=HeadlessConfig(world_path=world,index_path=index,subject_id='synthetic-c002'),
            model_handler=forbidden_model_call) as core:
        receipt = core.runtime.wake_bus.emit(WakeSignalRequest(wake_source=WakeSource.SAFETY,
            rule_id='synthetic-c002-due', observed_at=now, priority=100, dedupe_key='synthetic-c002-due'))
    responder = BackgroundResponder(exchange).start()
    try:
        result = runner.run_due_work(world_path=world, index_path=index, subject_id='synthetic-c002',
            exchange_root=exchange, now=now, max_wakes=1, include_periodic_review=False,
            response_timeout_s=10, poll_interval_s=.005)
    finally:
        responder.stop()
    assert not responder.errors, responder.errors
    assert result['response_mode'] == 'EXTERNAL_CURRENT_RESIDENT_SESSION'
    assert result['status_before'] and result['status_after']
    due = result['due_work_result']
    assert len(due['wakes']) == 1
    assert due['wakes'][0]['wake']['wake_id'] == receipt.wake_id
    assert due['wakes'][0]['wake']['state'] == 'completed'
    assert due['wakes'][0]['runtime']['response'] == 'SYNTHETIC C002 TERMINAL'
    assert len(result['handoffs']) == 1
    assert result['exchange']['integrity']['ok']
    bridge = ExchangeBridge(exchange)
    assert [r['event'] for r in bridge.ledger.read_records()] == ['request_published','response_published','response_consumed']
    rid = bridge.ledger.request_ids()[0]
    assert bridge.request_body(rid)['wake_reason']
    assert bridge.recovery_state()['complete'] == [rid]
    evidence = pathlib.Path(__import__('os').environ['C002_RAW'])
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence/'due_work_result.json').write_text(json.dumps(result, indent=2, default=str)+'\n')
    (evidence/'due_work_ledger.jsonl').write_bytes(bridge.ledger.path.read_bytes())
    (evidence/'due_work_request.json').write_text(json.dumps(bridge.request_payload(rid), indent=2)+'\n')


def test_c9_no_semantic_callback(package):
    from operator_tools.no_semantic_scan import scan_run_package
    # Same frozen scanner used by Gate D, not a responder enable switch.
    report = scan_run_package(package / 'harness/aios_exchange', core_source=pathlib.Path(__import__('os').environ['C002_REPO'])/'src/aios_core')
    assert report['pass'], report
