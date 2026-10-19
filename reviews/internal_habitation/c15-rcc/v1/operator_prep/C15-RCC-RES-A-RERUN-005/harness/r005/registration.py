"""Kernel-peer and attempt-bound Runner registration authority."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from .registration_ipc import RegistrationIPCError, require_runner_peer


class RegistrationError(RuntimeError):
    pass


def process_start_time(pid: int) -> str:
    raw = Path(f'/proc/{int(pid)}/stat').read_text(encoding='ascii')
    end = raw.rfind(')')
    if end < 0:
        raise RegistrationError('cannot authenticate Runner process start time')
    fields = raw[end + 1:].split()
    if len(fields) <= 19:
        raise RegistrationError('Runner process identity is truncated')
    return fields[19]


def validate_registration(command: Mapping[str, Any], bridge, *, runner_pid: int,
                          runner_uid: int, runner_start_time: str,
                          runner_instance_id: str, operation_id: str,
                          key_id: str) -> tuple[str, dict[str, Any]]:
    required = {'command', 'request_id', 'request_sha256', 'context',
                'core_attempt_id', 'runner_instance_id', 'operation_id'}
    if not isinstance(command, dict) or set(command) != required or command.get('command') != 'register':
        raise RegistrationError('registration command schema mismatch')
    if command['runner_instance_id'] != runner_instance_id:
        raise RegistrationError('registration belongs to a stale Runner instance')
    if command['operation_id'] != operation_id:
        raise RegistrationError('registration belongs to a different operation')
    if process_start_time(runner_pid) != runner_start_time:
        raise RegistrationError('Runner PID was reused or its start identity changed')
    rid = command['request_id']
    digest = command['request_sha256']
    if (not isinstance(rid, str) or not rid or not isinstance(digest, str)
            or len(digest) != 64 or any(ch not in '0123456789abcdef' for ch in digest)):
        raise RegistrationError('registration request identity is malformed')
    request = bridge.requests.payload(rid)
    if bridge.request_sha256(rid) != digest:
        raise RegistrationError('request digest mismatch')
    context = command['context']
    attempt_id = command['core_attempt_id']
    if context is None:
        if attempt_id is not None or request.get('kind') not in {
                'round_summary', 'dimension_summary', 'model_directive'}:
            raise RegistrationError('contextless registration is not a foreground/summary request')
        body = request.get('body')
        identity = body.get('identity') if isinstance(body, dict) else None
        if (not isinstance(identity, dict)
                or not all(isinstance(identity.get(field), str) and identity[field]
                           for field in ('run_id', 'session_id', 'subject_id'))):
            raise RegistrationError('contextless request has no complete operation identity')
        if request.get('kind') == 'model_directive':
            binding = body.get('provenance_binding')
            if (not isinstance(binding, dict)
                    or binding.get('provider') != 'external-resident'
                    or binding.get('model') != identity['session_id']
                    or not isinstance(binding.get('request_id'), str)
                    or not binding['request_id']):
                raise RegistrationError('foreground request has no valid external provenance binding')
        safe_context = None
    else:
        expected_context = {
            'attempt_id', 'subject_id', 'work_kind', 'work_id', 'model_round_index',
            'outbound_request_fingerprint', 'relay_id', 'verifier_key_id',
        }
        if not isinstance(context, dict) or set(context) != expected_context:
            raise RegistrationError('Core signing context schema mismatch')
        if (not isinstance(attempt_id, str) or not attempt_id
                or context['attempt_id'] != attempt_id
                or request.get('kind') != 'model_directive'):
            raise RegistrationError('registration is not bound to a genuine Core attempt')
        if context['verifier_key_id'] != key_id:
            raise RegistrationError('Core context is bound to a different publisher key')
        if not isinstance(context['subject_id'], str) or not context['subject_id']:
            raise RegistrationError('Core context subject is invalid')
        if not isinstance(context['work_kind'], str) or not context['work_kind']:
            raise RegistrationError('Core context work kind is invalid')
        if not isinstance(context['work_id'], str) or not context['work_id']:
            raise RegistrationError('Core context work id is invalid')
        round_index = context['model_round_index']
        if isinstance(round_index, bool) or not isinstance(round_index, int) or round_index < 0:
            raise RegistrationError('Core context round index is invalid')
        for field in ('outbound_request_fingerprint', 'relay_id'):
            if not isinstance(context[field], str) or not context[field]:
                raise RegistrationError(f'Core context {field} is invalid')
        body = request.get('body')
        identity = body.get('identity') if isinstance(body, dict) else None
        binding = body.get('provenance_binding') if isinstance(body, dict) else None
        if not isinstance(identity, dict) or not isinstance(binding, dict):
            raise RegistrationError('Core request has no exact identity/provenance binding')
        if identity.get('subject_id') != context['subject_id']:
            raise RegistrationError('Core attempt subject does not match its durable request')
        if (binding.get('provider') != 'external-resident'
                or binding.get('model') != identity.get('session_id')
                or binding.get('request_id') != context['relay_id']):
            raise RegistrationError('Core attempt provenance does not match its durable request')
        safe_context = {field: context[field] for field in (
            'attempt_id', 'subject_id', 'work_kind', 'work_id', 'model_round_index',
            'outbound_request_fingerprint', 'relay_id')}
    registration = {
        'sha256': digest,
        'context': safe_context,
        'operation_id': operation_id,
        'runner_instance_id': runner_instance_id,
        'core_attempt_id': attempt_id,
        'runner_pid': runner_pid,
        'runner_uid': runner_uid,
    }
    return rid, registration


class RunnerRegistrationAuthority:
    """Ephemeral per-Runner registration table; never restored from disk."""

    def __init__(self, *, runner_pid: int, runner_uid: int, runner_gid: int,
                 runner_start_time: str, runner_instance_id: str,
                 operation_id: str, key_id: str,
                 runner_alive: Callable[[], bool]):
        self.runner_pid = int(runner_pid)
        self.runner_uid = int(runner_uid)
        self.runner_gid = int(runner_gid)
        self.runner_start_time = runner_start_time
        self.runner_instance_id = runner_instance_id
        self.operation_id = operation_id
        self.key_id = key_id
        self.runner_alive = runner_alive
        self.registered: dict[str, dict[str, Any]] = {}

    def register(self, peer, command: Mapping[str, Any], bridge) -> tuple[str, dict[str, Any]]:
        try:
            require_runner_peer(peer, pid=self.runner_pid, uid=self.runner_uid, gid=self.runner_gid)
        except RegistrationIPCError as exc:
            raise RegistrationError(str(exc)) from exc
        if not self.runner_alive():
            raise RegistrationError('only the live Runner process may register')
        try:
            rid, entry = validate_registration(
                command, bridge, runner_pid=self.runner_pid, runner_uid=self.runner_uid,
                runner_start_time=self.runner_start_time,
                runner_instance_id=self.runner_instance_id,
                operation_id=self.operation_id, key_id=self.key_id)
        except (RegistrationError, OSError) as exc:
            raise RegistrationError(str(exc)) from exc
        if rid in self.registered:
            raise RegistrationError('request registration replay rejected')
        self.registered[rid] = entry
        return rid, entry

    def get(self, request_id: str) -> dict[str, Any]:
        entry = self.registered.get(request_id)
        if entry is None:
            raise RegistrationError('unregistered/stale request')
        if (entry['operation_id'] != self.operation_id
                or entry['runner_instance_id'] != self.runner_instance_id
                or entry['runner_pid'] != self.runner_pid):
            raise RegistrationError('request registration is bound to another Runner operation')
        return entry
