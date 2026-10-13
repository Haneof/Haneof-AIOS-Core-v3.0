"""Synthetic-only responders; never importable from the real run package."""
import dataclasses


def snapshot(round_index=0):
    from aios_core.runtime.cognitive_runtime import RuntimeSnapshot
    return RuntimeSnapshot(user_input='SYNTHETIC C002 probe', wake_reason='synthetic',
        cockpit={'synthetic': True}, capability_catalog=(), capability_history=(),
        round_index=round_index, remaining_tool_rounds=1)


def publish_response(bridge, request_id):
    from aios_exchange.canonical import canonical_json_bytes
    envelope = {'response_version': 1, 'request_id': request_id,
        'request_sha256': bridge.request_sha256(request_id),
        'authored_by': 'EXTERNAL_CURRENT_RESIDENT_SESSION',
        'directive': {'capability_calls': [], 'response': 'SYNTHETIC C002 TERMINAL', 'silence': False}}
    return bridge.responses.publish_bytes(request_id=request_id,
        response_bytes=canonical_json_bytes(envelope) + b'\n')


def forbidden_model_call(_snapshot):
    raise AssertionError('setup must not invoke a model')


class BackgroundResponder:
    def __init__(self, root):
        import threading
        self.root = root
        self.errors = []
        self.event = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True)
    def start(self):
        self.thread.start()
        return self
    def stop(self):
        self.event.set()
        self.thread.join(timeout=15)
        assert not self.thread.is_alive()
    def loop(self):
        from aios_exchange.bridge import ExchangeBridge
        while not self.event.is_set():
            try:
                bridge = ExchangeBridge(self.root)
                for rid in bridge.recovery_state()['open_dispatched']:
                    publish_response(bridge, rid)
            except Exception as exc:
                self.errors.append(repr(exc))
            self.event.wait(.005)
