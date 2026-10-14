"""Current Core mechanical runner. This draft deliberately fails closed on recovery.

No response can acquire Core authenticity from the exchange hash chain.
This is an engineering candidate, not an approved Resident entry.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from aios_core.headless.core import HeadlessConfig, HeadlessCore
from aios_core.runtime.cognitive_runtime import RuntimeSnapshot
from r005.bridge import ExchangeBridge, ExchangeContractError
from r005.schema import serialize_runtime_snapshot, parse_model_directive
from r005.canonical import canonical_json_bytes
from r005.atomic import atomic_write_bytes


class ResidentHandler:
    def __init__(self, exchange: Path, identity: dict, timeout: float):
        self.bridge = ExchangeBridge(exchange)
        self.identity = identity
        self.timeout = timeout
        self.request_ids = []

    def __call__(self, snapshot: RuntimeSnapshot):
        if not isinstance(snapshot, RuntimeSnapshot):
            raise TypeError('actual RuntimeSnapshot required')
        if self.bridge.recovery_state()['open_dispatched'] or self.bridge.recovery_state()['durable_unconsumed']:
            raise ExchangeContractError('existing dispatched exchange: no new semantic request permitted')
        body = {'identity': self.identity, 'snapshot': serialize_runtime_snapshot(snapshot)}
        request = self.bridge.publish_request(kind='model_directive', body=body)
        rid = request['request_id']
        self.request_ids.append(rid)
        raw = self.bridge.await_response_bytes(rid, timeout_s=self.timeout)
        directive = parse_model_directive(json.loads(raw))
        self.bridge.consume_response(rid)
        # Route B: ordinary live ModelDirective return confers ZERO durable trust.
        # No attach_late_trusted_return call exists in this draft.
        return directive


def run(spec: dict):
    required = {'world','index','exchange','run_id','session_id','subject_id','mode','at','timeout'}
    if not required <= set(spec):
        raise ValueError('missing runner binding fields')
    moment = dt.datetime.fromisoformat(spec['at'])
    if moment.tzinfo is None:
        raise ValueError('timezone-aware time required')
    root = Path(spec['exchange']).resolve()
    marker = root / 'operation.json'
    identity = {k: spec[k] for k in ('run_id','session_id','subject_id','mode','at')}
    identity['world'] = str(Path(spec['world']).resolve())
    identity['index'] = str(Path(spec['index']).resolve())
    if marker.exists():
        raise ExchangeContractError('existing operation: draft has no approved recovery adapter')
    root.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(marker, canonical_json_bytes({'state':'started','spec':spec}))
    handler = ResidentHandler(root, identity, float(spec['timeout']))
    # Explicit summary handlers fail closed instead of generating a fallback.
    def summary_unavailable(_request):
        raise ExchangeContractError('external summary transport not implemented')
    core = HeadlessCore(config=HeadlessConfig(world_path=Path(spec['world']),
        index_path=Path(spec['index']),subject_id=spec['subject_id']),
        model_handler=handler, round_summary_handler=summary_unavailable,
        dimension_summary_handler=summary_unavailable).start()
    try:
        if spec['mode'] == 'user':
            result = core.submit_user_turn(session_id=spec['session_id'],
                turn_index=spec['turn_index'],user_input=spec['user_input'],occurred_at=moment)
        elif spec['mode'] == 'due':
            result = core.process_due_work(now=moment)
        else:
            raise ValueError('mode must be user or due')
        atomic_write_bytes(marker,canonical_json_bytes({'state':'completed','spec':spec,
            'result':result,'requests':handler.request_ids}))
        return result
    finally:
        core.stop()


def publish(exchange: Path, request_id: str, raw: bytes):
    # Historical publisher only checked the envelope; validate the directive first.
    parse_model_directive(json.loads(raw))
    bridge = ExchangeBridge(exchange)
    bridge.requests.payload(request_id)
    if bridge.ledger.latest_event(request_id,'response_consumed') is not None:
        raise ExchangeContractError('stale/consumed response cannot be published')
    return bridge.responses.publish_bytes(request_id=request_id,response_bytes=raw)
