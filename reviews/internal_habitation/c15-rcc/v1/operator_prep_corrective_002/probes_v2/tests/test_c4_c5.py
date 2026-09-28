import json
import pytest
from synthetic.support import snapshot, publish_response


def handler_at(root):
    from aios_exchange.runner import ExternalSessionModelHandler, ExternalSessionConfig
    return ExternalSessionModelHandler(ExternalSessionConfig(root, response_timeout_s=.05, poll_interval_s=.005))


def publish(handler, snap):
    from aios_exchange.schema import serialize_runtime_snapshot
    return handler.bridge.publish_request(kind='model_directive', body=serialize_runtime_snapshot(snap))['request_id']


@pytest.mark.parametrize('state', ['open', 'durable'])
def test_c4_different_snapshot(package, tmp_path, state, monkeypatch):
    from aios_exchange.bridge import ExchangeContractError
    from aios_exchange.schema import serialize_runtime_snapshot
    h = handler_at(tmp_path)
    rid = publish(h, snapshot(1))
    assert serialize_runtime_snapshot(snapshot(1)) != serialize_runtime_snapshot(snapshot(2))
    if state == 'durable':
        publish_response(h.bridge, rid)
    def must_not_wait(*args, **kwargs):
        pytest.fail('mismatched recovery reached response wait instead of immediate fail closed')
    monkeypatch.setattr(h.bridge, 'await_response_bytes', must_not_wait)
    before = h.bridge.ledger.path.read_bytes()
    with pytest.raises(ExchangeContractError, match='binding|snapshot|ambiguous'):
        h(snapshot(2))
    assert before == h.bridge.ledger.path.read_bytes()


@pytest.mark.parametrize('state', ['open', 'durable', 'mixed'])
def test_c4_ambiguous(package, tmp_path, state, monkeypatch):
    from aios_exchange.bridge import ExchangeContractError
    h = handler_at(tmp_path)
    for i in range(2):
        rid = publish(h, snapshot())
        if state == 'durable' or (state == 'mixed' and i == 0):
            publish_response(h.bridge, rid)
    def must_not_wait(*args, **kwargs):
        pytest.fail('ambiguous recovery reached response wait')
    monkeypatch.setattr(h.bridge, 'await_response_bytes', must_not_wait)
    with pytest.raises(ExchangeContractError, match='ambiguous recovery state'):
        h(snapshot())


@pytest.mark.parametrize('state', ['open', 'durable'])
def test_c4_matching_resume(package, tmp_path, state, monkeypatch):
    import aios_exchange.runner as runner
    h = handler_at(tmp_path)
    rid = publish(h, snapshot())
    if state == 'durable':
        publish_response(h.bridge, rid)
    original_wait = h.bridge.await_response_bytes
    def external_publish_then_wait(request_id, **kwargs):
        assert request_id == rid
        if state == 'open':
            publish_response(h.bridge, rid)
        return original_wait(request_id, **kwargs)
    monkeypatch.setattr(h.bridge, 'await_response_bytes', external_publish_then_wait)
    original_serialize = runner.serialize_runtime_snapshot
    calls = []
    def counted(snap):
        calls.append(snap)
        return original_serialize(snap)
    monkeypatch.setattr(runner, 'serialize_runtime_snapshot', counted)
    assert h(snapshot()).response == 'SYNTHETIC C002 TERMINAL'
    assert len(calls) == 1
    assert h.bridge.recovery_state()['complete'] == [rid]
    assert len(h.bridge.ledger.read_records()) == 3


@pytest.mark.parametrize('damage', ['missing', 'tamper'])
def test_c4_durable_request_file_binding(package, tmp_path, damage):
    from aios_exchange.requests import RequestPublishError
    h = handler_at(tmp_path)
    rid = publish(h, snapshot())
    publish_response(h.bridge, rid)
    path = h.bridge.requests.path_for(rid)
    if damage == 'missing':
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises((RequestPublishError, FileNotFoundError)):
        h(snapshot())


def rechain(records):
    from aios_exchange.canonical import canonical_json_bytes, sha256_hex
    prev = '0' * 64
    for i, row in enumerate(records, 1):
        row.update(seq=i, prev_sha256=prev)
        row.pop('record_sha256', None)
        row['record_sha256'] = sha256_hex(canonical_json_bytes(row))
        prev = row['record_sha256']
    return b''.join(canonical_json_bytes(row) + b'\n' for row in records)


@pytest.mark.parametrize('damage', ['mutation', 'deletion', 'duplicate_request', 'duplicate_response',
    'duplicate_consumed', 'illegal_order', 'request_digest', 'response_digest', 'torn', 'invalid_json', 'sequence'])
@pytest.mark.parametrize('operation', ['recovery', 'consume', 'append', 'runner', 'request_lookup', 'response_lookup'])
def test_c5_corrupt_ledger(package, tmp_path, damage, operation):
    from aios_exchange.ledger import LedgerError
    h = handler_at(tmp_path)
    rid = publish(h, snapshot())
    publish_response(h.bridge, rid)
    h.bridge.consume_response(rid)
    rows = h.bridge.ledger.read_records()
    if damage == 'mutation':
        rows[1]['wall_clock'] = 'corrupt'
        raw = b''.join(json.dumps(row).encode() + b'\n' for row in rows)
    elif damage == 'deletion':
        raw = b''.join(json.dumps(row).encode() + b'\n' for row in (rows[0], rows[2]))
    elif damage.startswith('duplicate'):
        idx = {'duplicate_request': 0, 'duplicate_response': 1, 'duplicate_consumed': 2}[damage]
        rows.insert(idx + 1, dict(rows[idx]))
        raw = rechain(rows)
    elif damage == 'illegal_order':
        raw = rechain([rows[1], rows[0], rows[2]])
    elif damage in ('request_digest', 'response_digest'):
        rows[2][damage.replace('_digest', '_sha256')] = 'a' * 64
        raw = rechain(rows)
    elif damage == 'torn':
        raw = h.bridge.ledger.path.read_bytes()[:-1]
    elif damage == 'invalid_json':
        raw = b'{broken}\n'
    else:
        rows[1]['seq'] = 42
        raw = b''.join(json.dumps(row).encode() + b'\n' for row in rows)
    h.bridge.ledger.path.write_bytes(raw)
    operations = {
        'recovery': lambda: h.bridge.recovery_state(),
        'consume': lambda: h.bridge.consume_response(rid),
        'append': lambda: h.bridge.ledger.append('request_published', request_id='new', request_sha256='b'*64),
        'runner': lambda: h(snapshot()),
        'request_lookup': lambda: h.bridge.request_payload(rid),
        'response_lookup': lambda: h.bridge.responses.published_bytes(rid),
    }
    with pytest.raises(LedgerError):
        operations[operation]()
    assert h.bridge.ledger.path.read_bytes() == raw


def test_c5_valid_chain(package, tmp_path):
    h = handler_at(tmp_path)
    for i in range(2):
        rid = publish(h, snapshot(i))
        publish_response(h.bridge, rid)
        h.bridge.consume_response(rid)
    assert h.bridge.recovery_state()['ledger']['ok']
    assert h.bridge.integrity()['ok']
    assert len(h.bridge.ledger.read_records()) == 6


@pytest.mark.parametrize('event', ['request_published', 'response_published', 'response_consumed'])
def test_c5_duplicate_append_refused(package, tmp_path, event):
    from aios_exchange.ledger import LedgerError
    h = handler_at(tmp_path)
    rid = publish(h, snapshot())
    publish_response(h.bridge, rid)
    h.bridge.consume_response(rid)
    record = h.bridge.ledger.latest_event(rid, event)
    before = h.bridge.ledger.path.read_bytes()
    with pytest.raises(LedgerError):
        h.bridge.ledger.append(event, request_id=rid, request_sha256=record['request_sha256'],
            response_sha256=record['response_sha256'])
    assert h.bridge.ledger.path.read_bytes() == before
