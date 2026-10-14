"""Remote-commit-gated idempotent operation completion records.

A local operation is never marked ``completed`` until a separately durable
remote Git commit is positively identified and its committed candidate bytes
have been verified. The remote candidate is immutable input to restart recovery;
recovery never redispatches a semantic request.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .atomic import atomic_write_bytes
from .canonical import canonical_json_bytes

SCHEMA = 'r005-remote-operation-completion-v1'


class CompletionError(RuntimeError):
    pass


def operation_id(spec: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(spec)).hexdigest()


def result_sha256(result: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(result)).hexdigest()


def candidate_record(spec: Mapping[str, Any], result: Any) -> dict[str, Any]:
    return {
        'schema': SCHEMA,
        'state': 'remote_committing',
        'operation_id': operation_id(spec),
        'spec': dict(spec),
        'result': result,
        'result_sha256': result_sha256(result),
    }


def validate_candidate(record: Any, spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict) or record.get('schema') != SCHEMA:
        raise CompletionError('operation record schema is not an R005 completion record')
    if record.get('state') != 'remote_committing':
        raise CompletionError('operation record is not a remote completion candidate')
    expected_operation = operation_id(spec)
    if record.get('operation_id') != expected_operation or record.get('spec') != dict(spec):
        raise CompletionError('operation replay binding mismatch')
    if record.get('result_sha256') != result_sha256(record.get('result')):
        raise CompletionError('operation result digest mismatch')
    return record


def write_candidate(marker: Path, spec: Mapping[str, Any], result: Any,
                    *, fault_hook: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Durably save the exact result before any remote commit is attempted."""
    try:
        current = json.loads(Path(marker).read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise CompletionError('started operation marker is unreadable') from exc
    if (not isinstance(current, dict) or current.get('state') != 'started'
            or current.get('operation_id') != operation_id(spec)
            or current.get('spec') != dict(spec)):
        raise CompletionError('only the exact started operation may publish a result candidate')
    if fault_hook:
        fault_hook('before_local_result_write')
    candidate = candidate_record(spec, result)
    atomic_write_bytes(marker, canonical_json_bytes(candidate))
    if fault_hook:
        fault_hook('after_local_result_write_before_remote_commit')
    return candidate


def completion_record(candidate: Mapping[str, Any], *, remote_ref: str,
                      remote_commit: str) -> dict[str, Any]:
    spec = candidate.get('spec')
    validated = validate_candidate(dict(candidate), spec)
    if not isinstance(remote_ref, str) or not remote_ref.startswith('refs/heads/persistence/'):
        raise CompletionError('completion remote ref is not a canonical persistence ref')
    if (not isinstance(remote_commit, str) or len(remote_commit) not in (40, 64)
            or any(ch not in '0123456789abcdef' for ch in remote_commit)):
        raise CompletionError('remote commit identity is invalid')
    return {
        'schema': SCHEMA,
        'state': 'completed',
        'operation_id': validated['operation_id'],
        'spec': validated['spec'],
        'result': validated['result'],
        'result_sha256': validated['result_sha256'],
        'remote_ref': remote_ref,
        'remote_commit': remote_commit,
        'remote_candidate_sha256': hashlib.sha256(canonical_json_bytes(validated)).hexdigest(),
    }


def finalize_local(marker: Path, candidate: Mapping[str, Any], *, remote_ref: str,
                   remote_commit: str, remote_candidate_bytes: bytes,
                   fault_hook: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Mark the local record completed only after exact remote bytes are proven."""
    validated = validate_candidate(dict(candidate), candidate.get('spec'))
    try:
        current_bytes = Path(marker).read_bytes()
        current_record = json.loads(current_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise CompletionError('local operation candidate is unreadable') from exc
    if current_record != validated or current_bytes != canonical_json_bytes(validated):
        raise CompletionError('local operation candidate changed before confirmation')
    expected_bytes = canonical_json_bytes(validated)
    if remote_candidate_bytes != expected_bytes:
        raise CompletionError('authoritative remote candidate bytes do not match local operation/result')
    if fault_hook:
        fault_hook('after_remote_commit_before_local_confirmation')
    completed = completion_record(validated, remote_ref=remote_ref, remote_commit=remote_commit)
    atomic_write_bytes(marker, canonical_json_bytes(completed))
    return completed


def validate_completed(record: Any, spec: Mapping[str, Any], *,
                       remote_candidate_bytes: bytes,
                       remote_commit: str | None = None) -> dict[str, Any]:
    if not isinstance(record, dict) or record.get('schema') != SCHEMA or record.get('state') != 'completed':
        raise CompletionError('cached operation has no remote-bound completion receipt')
    expected_op = operation_id(spec)
    if record.get('operation_id') != expected_op or record.get('spec') != dict(spec):
        raise CompletionError('cached operation replay binding mismatch')
    if record.get('result_sha256') != result_sha256(record.get('result')):
        raise CompletionError('cached operation result digest mismatch')
    if remote_commit is not None and record.get('remote_commit') != remote_commit:
        raise CompletionError('cached operation remote commit binding mismatch')
    if hashlib.sha256(remote_candidate_bytes).hexdigest() != record.get('remote_candidate_sha256'):
        raise CompletionError('cached operation remote candidate digest mismatch')
    try:
        candidate = json.loads(remote_candidate_bytes)
    except Exception as exc:
        raise CompletionError('authoritative remote candidate is invalid JSON') from exc
    validate_candidate(candidate, spec)
    if candidate.get('result') != record.get('result'):
        raise CompletionError('cached result differs from authoritative remote candidate')
    return record
