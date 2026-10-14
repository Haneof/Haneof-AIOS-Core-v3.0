"""Development-only Linux IPC/registration tests; never starts a Resident."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest

REPO = Path(__file__).resolve().parents[3]
HARNESS = REPO / 'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness'
sys.path.insert(0, str(HARNESS))

from r005.registration import (RegistrationError, RunnerRegistrationAuthority,
                                process_start_time)
from r005.registration_ipc import (RegistrationIPCError, peer_credentials,
                                    receive_message, rpc, send_message)


class _Requests:
    def __init__(self, payload):
        self._payload = payload
        self.reads = 0

    def payload(self, request_id):
        self.reads += 1
        if request_id != 'request-1':
            raise KeyError(request_id)
        return self._payload


class _Bridge:
    def __init__(self, kind='model_directive'):
        identity = {'run_id': 'run-1', 'session_id': 'session-1', 'subject_id': 'subject-1'}
        if kind == 'model_directive':
            body = {
                'identity': identity,
                'snapshot': {'round_index': 0},
                'provenance_binding': {
                    'provider': 'external-resident', 'model': 'session-1', 'request_id': 'relay-1'},
            }
        else:
            body = {'identity': identity, 'summary_input': {'response': 'summary'}}
        self.requests = _Requests({'kind': kind, 'body': body})

    @staticmethod
    def request_sha256(_request_id):
        return 'a' * 64


def _context():
    return {
        'attempt_id': 'attempt-1',
        'subject_id': 'subject-1',
        'work_kind': 'wake',
        'work_id': 'wake-1',
        'model_round_index': 0,
        'outbound_request_fingerprint': 'f' * 64,
        'relay_id': 'relay-1',
        'verifier_key_id': 'publisher-key-1',
    }


def _command(**updates):
    value = {
        'command': 'register', 'request_id': 'request-1', 'request_sha256': 'a' * 64,
        'context': _context(), 'core_attempt_id': 'attempt-1',
        'runner_instance_id': 'instance-1', 'operation_id': 'operation-1',
    }
    value.update(updates)
    return value


def _authority(*, instance='instance-1', operation='operation-1', alive=lambda: True,
               start_time=None):
    return RunnerRegistrationAuthority(
        runner_pid=os.getpid(), runner_uid=os.getuid(), runner_gid=os.getgid(),
        runner_start_time=(start_time if start_time is not None else process_start_time(os.getpid())),
        runner_instance_id=instance, operation_id=operation,
        key_id='publisher-key-1', runner_alive=alive)


class RegistrationTests(unittest.TestCase):
    def test_genuine_runner_registration_is_bound_and_one_shot(self):
        bridge = _Bridge()
        authority = _authority()
        peer = (os.getpid(), os.getuid(), os.getgid())
        request_id, entry = authority.register(peer, _command(), bridge)
        self.assertEqual(request_id, 'request-1')
        self.assertEqual(entry['core_attempt_id'], 'attempt-1')
        self.assertEqual(entry['context']['attempt_id'], 'attempt-1')
        self.assertEqual(entry['operation_id'], 'operation-1')
        self.assertEqual(entry['runner_instance_id'], 'instance-1')
        with self.assertRaisesRegex(RegistrationError, 'replay'):
            authority.register(peer, _command(), bridge)

    def test_contextless_foreground_and_summary_have_narrow_shapes(self):
        peer = (os.getpid(), os.getuid(), os.getgid())
        foreground = _command(context=None, core_attempt_id=None)
        self.assertIsNone(_authority().register(peer, foreground, _Bridge())[1]['context'])
        summary = _command(context=None, core_attempt_id=None)
        self.assertIsNone(_authority().register(peer, summary, _Bridge('round_summary'))[1]['context'])

    def test_wrong_operation_instance_attempt_and_provenance_are_rejected(self):
        peer = (os.getpid(), os.getuid(), os.getgid())
        cases = [
            (_command(operation_id='old-operation'), 'different operation'),
            (_command(runner_instance_id='old-instance'), 'stale Runner instance'),
            (_command(core_attempt_id='other-attempt'), 'genuine Core attempt'),
            (_command(context={**_context(), 'attempt_id': 'other-attempt'}), 'genuine Core attempt'),
            (_command(context={**_context(), 'subject_id': 'other-subject'}), 'subject'),
            (_command(context={**_context(), 'relay_id': 'other-relay'}), 'provenance'),
            (_command(caller_pid=os.getpid()), 'schema'),
        ]
        for command, message in cases:
            with self.subTest(message=message):
                authority = _authority()
                bridge = _Bridge()
                with self.assertRaisesRegex(RegistrationError, message):
                    authority.register(peer, command, bridge)
                self.assertEqual(authority.registered, {})

    def test_dead_or_restarted_runner_cannot_reuse_capability(self):
        peer = (os.getpid(), os.getuid(), os.getgid())
        bridge = _Bridge()
        dead = _authority(alive=lambda: False)
        with self.assertRaisesRegex(RegistrationError, 'live Runner'):
            dead.register(peer, _command(), bridge)
        self.assertEqual(dead.registered, {})
        restarted = _authority(instance='new-instance')
        with self.assertRaisesRegex(RegistrationError, 'stale Runner instance'):
            restarted.register(peer, _command(), bridge)
        self.assertEqual(restarted.registered, {})
        reused_pid = _authority(start_time='0')
        with self.assertRaisesRegex(RegistrationError, 'PID was reused'):
            reused_pid.register(peer, _command(), bridge)
        self.assertEqual(reused_pid.registered, {})

    def test_same_uid_child_knowing_real_pid_cannot_register(self):
        """The command self-claims the true PID; SO_PEERCRED still sees the child."""
        with tempfile.TemporaryDirectory(prefix='r005-registration-') as temp:
            directory = Path(temp)
            os.chmod(directory, 0o700)
            socket_path = directory / 'publisher.sock'
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(str(socket_path))
            os.chmod(socket_path, 0o600)
            listener.listen(1)
            authority = _authority()
            bridge = _Bridge()
            outcome = {}

            def serve_one():
                connection, _ = listener.accept()
                with connection:
                    peer = peer_credentials(connection)
                    command = receive_message(connection)
                    outcome['peer'] = peer
                    try:
                        authority.register(peer, command, bridge)
                        send_message(connection, {'ok': True})
                    except RegistrationError as exc:
                        outcome['error'] = str(exc)
                        send_message(connection, {'ok': False, 'error': str(exc)})

            server = threading.Thread(target=serve_one, daemon=True)
            server.start()
            forged = _command(caller_pid=os.getpid())
            client = r"""
import json, socket, sys
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect(sys.argv[1])
sock.sendall(json.dumps(json.loads(sys.argv[2]), separators=(',', ':')).encode() + b'\n')
sock.shutdown(socket.SHUT_WR)
data = b''
while not data.endswith(b'\n'):
    block = sock.recv(4096)
    if not block: break
    data += block
print(data.decode())
"""
            child = subprocess.run([sys.executable, '-c', client, str(socket_path),
                                    json.dumps(forged)], capture_output=True, text=True, timeout=10)
            server.join(timeout=10)
            listener.close()
            self.assertEqual(child.returncode, 0, child.stderr)
            response = json.loads(child.stdout.strip())
            self.assertFalse(response['ok'])
            self.assertIn('exact live Runner kernel identity', response['error'])
            self.assertNotEqual(outcome['peer'][0], os.getpid())
            self.assertEqual(outcome['peer'][1], os.getuid())
            self.assertEqual(authority.registered, {})
            self.assertEqual(bridge.requests.reads, 0)

    def test_rpc_authenticates_publisher_pid_and_process_start_time(self):
        with tempfile.TemporaryDirectory(prefix='r005-rpc-peer-') as temp:
            directory = Path(temp)
            os.chmod(directory, 0o700)
            socket_path = directory / 'publisher.sock'
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(str(socket_path))
            os.chmod(socket_path, 0o600)
            listener.listen(1)
            outcome = {}

            def serve_one():
                connection, _ = listener.accept()
                with connection:
                    outcome['peer'] = peer_credentials(connection)
                    command = receive_message(connection)
                    send_message(connection, {'ok': True, 'result': {'echo': command['command']}})

            server = threading.Thread(target=serve_one, daemon=True)
            server.start()
            result = rpc(socket_path, {'command': 'identity-probe'},
                         expected_server_pid=os.getpid(),
                         expected_server_start_time=process_start_time(os.getpid()))
            server.join(timeout=10)
            listener.close()
            self.assertEqual(result, {'echo': 'identity-probe'})
            self.assertEqual(outcome['peer'][0], os.getpid())

    def test_client_refuses_pid_only_publisher_identity_fallback(self):
        with self.assertRaisesRegex(RegistrationIPCError, 'both required'):
            rpc('/tmp/not-used.sock', {'command': 'publish'}, expected_server_pid=os.getpid())

    def test_unregistered_request_has_no_registration_capability(self):
        authority = _authority()
        with self.assertRaisesRegex(RegistrationError, 'unregistered/stale'):
            authority.get('request-1')
        self.assertEqual(authority.registered, {})


if __name__ == '__main__':
    unittest.main()
