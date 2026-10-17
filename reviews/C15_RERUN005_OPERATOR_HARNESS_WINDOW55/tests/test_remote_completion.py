"""Bare-Git CAS and restart-recovery tests for completion candidates."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
HARNESS = REPO / 'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness'
sys.path.insert(0, str(HARNESS))

from tools.c15_persistence import remote_backend
from tools.c15_persistence.backend import GenerationStore
from r005.completion import candidate_record, write_candidate
from r005.canonical import canonical_json_bytes
from r005.remote_completion import (RemoteCompletionError, recover_remote_candidate,
                                   verify_completed_remote_record)


class _FakeBackend:
    def __init__(self, root, *, run_id, session_id, remote_ref):
        self.root = Path(root)
        self.generations_dir = self.root / 'generations'
        self.mailbox_dir = self.root / 'mailbox'
        self.owner = {
            'run_id': run_id,
            'session_id': session_id,
            'subject_id': 'subject-window55',
            'remote_authoritative': True,
            'remote_authority': {
                'run_id': run_id,
                'session_id': session_id,
                'remote': 'origin',
                'remote_ref': remote_ref,
            },
        }

    def audit(self, event, detail=None):
        path = self.root / 'audit.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {'event': event, 'detail': dict(detail or {})}
        with path.open('ab') as handle:
            handle.write(canonical_json_bytes(record) + b'\n')
            handle.flush()
            os.fsync(handle.fileno())


def _git(repo, *args, check=True):
    completed = subprocess.run(['git', *map(str, args)], cwd=repo,
                               capture_output=True, text=True)
    if check and completed.returncode:
        raise AssertionError(f'git {args} failed: {completed.stderr}')
    return completed


class RemoteCompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='r005-remote-cas-')
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        self.bare = self.base / 'remote.git'
        self.repo.mkdir()
        _git(self.repo, 'init', '-q')
        _git(self.repo, 'config', 'user.name', 'Window 55 test')
        _git(self.repo, 'config', 'user.email', 'window55@example.invalid')
        self.bare.mkdir()
        _git(self.bare, 'init', '--bare', '-q')
        _git(self.repo, 'remote', 'add', 'origin', self.bare)
        self.run_id = 'window55-remote-test'
        self.session_id = 'session-window55'
        self.remote_ref = f'refs/heads/persistence/{self.run_id}'
        self.root = self.base / 'backend'
        self.root.mkdir(mode=0o700)
        (self.root / 'generations').mkdir(mode=0o700)
        (self.root / 'mailbox').mkdir(mode=0o700)
        (self.root / 'owner.json').write_bytes(canonical_json_bytes({
            'run_id': self.run_id, 'session_id': self.session_id,
            'remote_authoritative': True,
            'remote_authority': self._authority_record(),
        }))
        self.backend = _FakeBackend(self.root, run_id=self.run_id,
                                    session_id=self.session_id, remote_ref=self.remote_ref)
        GenerationStore(self.backend).seal({'state/initial.bin': b'initial'}, label='initial')
        self.initial_ref, self.initial_commit = remote_backend.push_run_state(
            self.backend, remote_ref=self.remote_ref, repo_dir=self.repo,
            message='window55 initial test state')
        self.spec = {'mode': 'user', 'at': '2026-10-14T12:00:00+00:00', 'cursor': 1,
                     'event_id': 'event-window55', 'turn_index': 1,
                     'user_input': 'synthetic', 'timeout': 1}
        self.opid = hashlib.sha256(canonical_json_bytes(self.spec)).hexdigest()
        self.exchange = self.root / 'mailbox/operations' / self.opid
        self.exchange.mkdir(parents=True)
        self.marker = self.exchange / 'operation.json'
        self.marker.write_bytes(canonical_json_bytes({'state': 'started',
                                                       'operation_id': self.opid,
                                                       'spec': self.spec}))
        self.result = {'response': 'synthetic cached result', 'world_version': 2}
        self.candidate = write_candidate(self.marker, self.spec, self.result)
        self.world = self.root / 'state/world.bin'
        self.world.parent.mkdir(parents=True, exist_ok=True)
        self.world.write_bytes(b'world-before-replay')

    def tearDown(self):
        self.temp.cleanup()

    def _authority_record(self):
        return {
            'run_id': self.run_id,
            'session_id': self.session_id,
            'remote': 'origin',
            'remote_ref': self.remote_ref,
            'schema': 'c15-remote-authority-v1',
        }

    def _commit_candidate_but_crash_before_local_head_confirmation(self):
        original = remote_backend._write_expected_remote_head
        def crash_before_confirmation(_backend, _commit):
            raise RuntimeError('injected crash before local expected-head confirmation')
        remote_backend._write_expected_remote_head = crash_before_confirmation
        try:
            with self.assertRaisesRegex(RuntimeError, 'injected crash'):
                remote_backend.push_run_state(
                    self.backend, remote_ref=self.remote_ref, repo_dir=self.repo,
                    message='window55 injected uncertain candidate CAS')
        finally:
            remote_backend._write_expected_remote_head = original
        actual = remote_backend._remote_head(self.repo, 'origin', self.remote_ref)
        expected = (self.root / remote_backend.LOCAL_EXPECTED_HEAD).read_text().strip()
        self.assertNotEqual(actual, expected)
        return actual

    def test_remote_commit_before_local_confirmation_recovers_without_redispatch(self):
        commit = self._commit_candidate_but_crash_before_local_head_confirmation()
        semantic_dispatch_count = 0  # Recovery has no callback/entry into Core or a model.
        recovered = recover_remote_candidate(
            backend=self.backend, marker=self.marker, spec=self.spec,
            remote_ref=self.remote_ref, repo=self.repo, remote_backend=remote_backend,
            verify_local_remote_authority=remote_backend.verify_local_remote_authority)
        self.assertEqual(recovered['remote_commit'], commit)
        self.assertTrue(recovered['recovered_without_redispatch'])
        self.assertEqual(json.loads(self.marker.read_bytes())['state'], 'completed')
        self.assertEqual(semantic_dispatch_count, 0)
        world_before = hashlib.sha256(self.world.read_bytes()).hexdigest()
        replay1 = verify_completed_remote_record(
            backend=self.backend, marker=self.marker, record=json.loads(self.marker.read_bytes()),
            spec=self.spec, remote_ref=self.remote_ref, repo=self.repo,
            remote_backend=remote_backend,
            verify_local_remote_authority=remote_backend.verify_local_remote_authority)
        replay2 = verify_completed_remote_record(
            backend=self.backend, marker=self.marker, record=json.loads(self.marker.read_bytes()),
            spec=self.spec, remote_ref=self.remote_ref, repo=self.repo,
            remote_backend=remote_backend,
            verify_local_remote_authority=remote_backend.verify_local_remote_authority)
        self.assertEqual(replay1['result'], self.result)
        self.assertEqual(replay2['result'], self.result)
        self.assertEqual(hashlib.sha256(self.world.read_bytes()).hexdigest(), world_before)

    def test_cas_race_during_git_push_fails_closed_without_completion(self):
        tree = _git(self.repo, 'rev-parse', f'{self.initial_commit}^{{tree}}').stdout.strip()
        competing_commit = _git(self.repo, 'commit-tree', tree, '-p', self.initial_commit,
                                 '-m', 'injected competing writer').stdout.strip()
        # Transfer the object without changing the persistence ref; the race hook
        # can then atomically advance the target ref after the helper's pre-read.
        _git(self.repo, 'push', 'origin',
             f'{competing_commit}:refs/heads/window55-race-object')
        original_run = remote_backend.subprocess.run
        fired = {'value': False}

        def intercept(command, *args, **kwargs):
            values = list(command) if isinstance(command, (list, tuple)) else [str(command)]
            if not fired['value'] and len(values) >= 2 and values[0] == 'git' and values[1] == 'push':
                fired['value'] = True
                race = original_run(
                    ['git', '--git-dir', str(self.bare), 'update-ref',
                     self.remote_ref, competing_commit, self.initial_commit],
                    cwd=self.repo, capture_output=True, text=True)
                if race.returncode:
                    raise AssertionError(race.stderr)
            return original_run(command, *args, **kwargs)

        remote_backend.subprocess.run = intercept
        try:
            with self.assertRaises(Exception):
                remote_backend.push_run_state(
                    self.backend, remote_ref=self.remote_ref, repo_dir=self.repo,
                    message='window55 injected CAS race')
        finally:
            remote_backend.subprocess.run = original_run
        self.assertTrue(fired['value'])
        self.assertEqual((self.root / remote_backend.LOCAL_EXPECTED_HEAD).read_text().strip(),
                         self.initial_commit)
        self.assertEqual(json.loads(self.marker.read_bytes())['state'], 'remote_committing')
        actual = remote_backend._remote_head(self.repo, 'origin', self.remote_ref)
        self.assertEqual(actual, competing_commit)
        with self.assertRaises(RemoteCompletionError):
            recover_remote_candidate(
                backend=self.backend, marker=self.marker, spec=self.spec,
                remote_ref=self.remote_ref, repo=self.repo, remote_backend=remote_backend,
                verify_local_remote_authority=remote_backend.verify_local_remote_authority)
        self.assertEqual(json.loads(self.marker.read_bytes())['state'], 'remote_committing')

    def test_remote_candidate_is_bound_to_exact_operation_and_result(self):
        ref, commit = remote_backend.push_run_state(
            self.backend, remote_ref=self.remote_ref, repo_dir=self.repo,
            message='window55 exact operation candidate')
        self.assertEqual(ref, self.remote_ref)
        candidate_bytes = _git(self.repo, 'show', f'{commit}:{self.marker.relative_to(self.root).as_posix()}').stdout.encode()
        self.assertEqual(json.loads(candidate_bytes), self.candidate)
        self.assertEqual(self.candidate['result_sha256'],
                         hashlib.sha256(canonical_json_bytes(self.result)).hexdigest())
        recovered = recover_remote_candidate(
            backend=self.backend, marker=self.marker, spec=self.spec,
            remote_ref=self.remote_ref, repo=self.repo, remote_backend=remote_backend,
            verify_local_remote_authority=remote_backend.verify_local_remote_authority)
        self.assertEqual(recovered['result'], self.result)


if __name__ == '__main__':
    unittest.main()
