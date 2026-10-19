"""Git-remote verification and restart recovery for operation candidates."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Mapping

from .completion import (CompletionError, finalize_local, validate_candidate,
                         validate_completed)
from .canonical import canonical_json_bytes


class RemoteCompletionError(RuntimeError):
    pass


def _git_bytes(repo: Path, *args: str) -> bytes:
    result = subprocess.run(['git', *args], cwd=str(repo), capture_output=True)
    if result.returncode != 0:
        raise RemoteCompletionError(
            'Git remote completion verification failed: '
            + result.stderr.decode('utf-8', errors='replace')
        )
    return result.stdout


def _show(repo: Path, commit: str, relative: str) -> bytes:
    return _git_bytes(repo, 'show', f'{commit}:{relative}')


def _excluded_from_remote(relative: str) -> bool:
    path = PurePosixPath(relative)
    name = path.name
    return (
        relative in {'.owner.lock', '.remote-head', 'mailbox/provider.pid'}
        or relative == 'mailbox/commands'
        or relative.startswith('mailbox/commands/')
        or name.endswith(('.tmp', '.snapshot', '-shm', '-wal'))
    )


def _local_remote_files(root: Path) -> set[str]:
    result = set()
    for path in root.rglob('*'):
        relative = path.relative_to(root).as_posix()
        if _excluded_from_remote(relative):
            continue
        if path.is_symlink():
            raise RemoteCompletionError(f'local persistence tree contains symlink: {relative}')
        if path.is_file():
            result.add(relative)
    return result


def _compare_local_tree_to_remote_candidate(root: Path, repo: Path, commit: str) -> None:
    """Allow only post-commit audit appends; all operation/state bytes must match."""
    try:
        raw_names = _git_bytes(repo, 'ls-tree', '-r', '-z', '--name-only', commit)
        remote_files = {item.decode('utf-8') for item in raw_names.split(b'\0') if item}
    except UnicodeDecodeError as exc:
        raise RemoteCompletionError('remote persistence tree has a non-UTF-8 path') from exc
    local_files = _local_remote_files(root)
    remote_files = {name for name in remote_files if not _excluded_from_remote(name)}
    if local_files != remote_files:
        raise RemoteCompletionError(
            'local cache file set differs from the candidate remote commit; refusing to re-anchor'
        )
    for relative in sorted(remote_files):
        try:
            remote_bytes = _show(repo, commit, relative)
            local_bytes = (root / relative).read_bytes()
        except OSError as exc:
            raise RemoteCompletionError(f'cannot verify persistence path {relative}: {exc}') from exc
        if relative == 'audit.jsonl':
            if not remote_bytes.endswith(b'\n') or not local_bytes.startswith(remote_bytes):
                raise RemoteCompletionError('local audit is not an append-only extension of remote audit')
        elif local_bytes != remote_bytes:
            raise RemoteCompletionError(f'local persistence bytes differ from remote commit: {relative}')


def _candidate_relative(marker: Path, backend_root: Path) -> str:
    try:
        return marker.relative_to(backend_root).as_posix()
    except ValueError as exc:
        raise RemoteCompletionError('operation marker is outside its persistence backend') from exc


def recover_remote_candidate(*, backend, marker: Path, spec: Mapping[str, Any],
                             remote_ref: str, repo: Path, remote_backend,
                             verify_local_remote_authority,
                             fault_hook=None) -> dict[str, Any]:
    """Finalize a committed candidate locally without re-entering Core/Resident."""
    try:
        record = json.loads(marker.read_bytes())
        candidate = validate_candidate(record, spec)
    except (OSError, json.JSONDecodeError, CompletionError) as exc:
        raise RemoteCompletionError(f'pending operation candidate is invalid: {exc}') from exc
    relative = _candidate_relative(marker, backend.root)
    expected_path = backend.root / remote_backend.LOCAL_EXPECTED_HEAD
    expected = expected_path.read_text(encoding='utf-8').strip() if expected_path.is_file() else None
    actual = remote_backend._remote_head(repo, 'origin', remote_ref)
    if actual is None:
        raise RemoteCompletionError('remote operation candidate has no authoritative remote ref')
    _compare_local_tree_to_remote_candidate(backend.root, repo, actual)
    remote_candidate = _show(repo, actual, relative)
    if remote_candidate != canonical_json_bytes(candidate):
        raise RemoteCompletionError('remote head does not contain the exact pending operation candidate')
    if actual != expected:
        remote_backend._write_expected_remote_head(backend, actual)
    try:
        verified_head = verify_local_remote_authority(
            backend, remote_ref=remote_ref, repo_dir=repo)
    except Exception as exc:
        raise RemoteCompletionError(f'remote authority could not be verified: {exc}') from exc
    remote_candidate = _show(repo, verified_head, relative)
    try:
        completed = finalize_local(
            marker, candidate, remote_ref=remote_ref, remote_commit=verified_head,
            remote_candidate_bytes=remote_candidate, fault_hook=fault_hook)
    except CompletionError as exc:
        raise RemoteCompletionError(str(exc)) from exc
    return {'result': completed['result'], 'remote_commit': verified_head,
            'remote_ref': remote_ref, 'recovered_without_redispatch': True}


def verify_completed_remote_record(*, backend, marker: Path, record: Mapping[str, Any],
                                   spec: Mapping[str, Any], remote_ref: str, repo: Path,
                                   remote_backend, verify_local_remote_authority) -> dict[str, Any]:
    """Validate an idempotent cached result against its exact authoritative commit."""
    recorded_ref = record.get('remote_ref')
    commit = record.get('remote_commit')
    if recorded_ref != remote_ref:
        raise RemoteCompletionError('cached completion remote ref mismatch')
    try:
        current_head = verify_local_remote_authority(
            backend, remote_ref=remote_ref, repo_dir=repo)
    except Exception as exc:
        raise RemoteCompletionError(f'current remote authority cannot be verified: {exc}') from exc
    ancestry = subprocess.run(
        ['git', 'merge-base', '--is-ancestor', str(commit), current_head],
        cwd=str(repo), capture_output=True)
    if ancestry.returncode != 0:
        raise RemoteCompletionError('completion commit is not an ancestor of the current authoritative ref')
    relative = _candidate_relative(marker, backend.root)
    try:
        remote_candidate = _show(repo, str(commit), relative)
        validated = validate_completed(record, spec,
            remote_candidate_bytes=remote_candidate, remote_commit=str(commit))
    except (CompletionError, RemoteCompletionError) as exc:
        raise RemoteCompletionError(f'cached completion is not bound to its exact remote candidate: {exc}') from exc
    return {'result': validated['result'], 'remote_commit': commit,
            'remote_ref': remote_ref, 'idempotent_replay': True}
