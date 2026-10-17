"""A rejected remote authority must never produce a local completion marker.

DEVELOPMENT_ONLY / FORMAL_VALIDATION_NOT_PERFORMED / DO_NOT_MERGE

PM priority case: "A rejected remote authority cannot produce a local
completed/ACK marker; inspect existing logic or use portable synthetic
fixtures. Do not claim full remote CAS if a genuine on-host test cannot run."

These tests use a REAL disposable local bare Git repository as the
authoritative remote -- the same portable technique Window66 itself recorded
("disposable local bare Git authorities"). That is an unprivileged, mechanical
local Git authority only. It is **not** evidence of production remote
durability, of a hosted platform, or of the real C15 remote CAS under the
Operator host's UID isolation. Where the real host facility is required the
test says so explicitly.

Real production code under test, unmodified:
``r005.completion`` (``write_candidate``, ``finalize_local``,
``completion_record``, ``validate_candidate``, ``validate_completed``),
``r005.remote_completion`` (``recover_remote_candidate``,
``verify_completed_remote_record``) and ``tools.c15_persistence.remote_backend``.

Scope note: Window55's ``test_remote_completion.py`` already covers a CAS race
during ``git push`` and a successful crash-before-confirmation recovery. This
module deliberately covers the complementary cases: an authority that is
REJECTED, and the proof that rejection can never be credited locally.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from synthetic_fixtures import canonical_json_bytes, make_workdir

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.c15_persistence import remote_backend                     # noqa: E402
from tools.c15_persistence.backend import GenerationStore            # noqa: E402
from r005.completion import (CompletionError, completion_record,      # noqa: E402
                             finalize_local, validate_completed,
                             write_candidate)
from r005 import remote_completion as remote_completion_module        # noqa: E402
from r005.remote_completion import (RemoteCompletionError,            # noqa: E402
                                    recover_remote_candidate,
                                    verify_completed_remote_record)


class SyntheticRunBackend:
    """Minimal remote-authoritative backend over a disposable directory."""

    def __init__(self, root, *, run_id, session_id, remote_ref):
        self.root = Path(root)
        self.generations_dir = self.root / 'generations'
        self.mailbox_dir = self.root / 'mailbox'
        self.owner = {
            'run_id': run_id,
            'session_id': session_id,
            'subject_id': 'arena-synthetic-subject',
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


def git(repo, *args):
    completed = subprocess.run(['git', *map(str, args)], cwd=str(repo),
                               capture_output=True, text=True)
    if completed.returncode:
        raise AssertionError(f'git {args} failed: {completed.stderr}')
    return completed.stdout.strip()


class RejectedRemoteAuthorityTests(unittest.TestCase):
    """No rejection path may write ``state == 'completed'`` or an ACK marker."""

    REMOTE_KIND = 'local bare git repository (disposable, unprivileged)'

    def setUp(self):
        self._temp = make_workdir('arena-eng-remote-')
        self.addCleanup(self._temp.cleanup)
        base = Path(self._temp.name)

        self.repo = base / 'repo'
        self.bare = base / 'remote.git'
        self.repo.mkdir()
        self.bare.mkdir()
        git(self.repo, 'init', '-q')
        git(self.repo, 'config', 'user.name', 'Arena C15 ENG 001 synthetic')
        git(self.repo, 'config', 'user.email', 'arena-synthetic@example.invalid')
        git(self.repo, 'config', 'commit.gpgsign', 'false')
        git(self.bare, 'init', '--bare', '-q')
        git(self.repo, 'remote', 'add', 'origin', self.bare)

        self.run_id = 'arena-synthetic-run'
        self.session_id = 'arena-synthetic-session'
        self.remote_ref = f'refs/heads/persistence/{self.run_id}'

        self.root = base / 'backend'
        self.root.mkdir(mode=0o700)
        (self.root / 'generations').mkdir(mode=0o700)
        (self.root / 'mailbox').mkdir(mode=0o700)
        (self.root / 'owner.json').write_bytes(canonical_json_bytes({
            'run_id': self.run_id, 'session_id': self.session_id,
            'remote_authoritative': True,
            'remote_authority': {'run_id': self.run_id, 'session_id': self.session_id,
                                 'remote': 'origin', 'remote_ref': self.remote_ref,
                                 'schema': 'c15-remote-authority-v1'}}))
        self.backend = SyntheticRunBackend(self.root, run_id=self.run_id,
                                           session_id=self.session_id,
                                           remote_ref=self.remote_ref)
        GenerationStore(self.backend).seal({'state/initial.bin': b'arena-initial'},
                                           label='initial')
        self.initial_ref, self.initial_commit = remote_backend.push_run_state(
            self.backend, remote_ref=self.remote_ref, repo_dir=self.repo,
            message='arena synthetic initial state')

        self.spec = {'mode': 'user', 'at': '2026-10-17T00:00:00+00:00', 'cursor': 1,
                     'event_id': 'arena-synthetic-event', 'turn_index': 1,
                     'user_input': 'arena synthetic', 'timeout': 1}
        self.opid = hashlib.sha256(canonical_json_bytes(self.spec)).hexdigest()
        self.exchange = self.root / 'mailbox' / 'operations' / self.opid
        self.exchange.mkdir(parents=True)
        self.marker = self.exchange / 'operation.json'
        self.marker.write_bytes(canonical_json_bytes(
            {'state': 'started', 'operation_id': self.opid, 'spec': self.spec}))
        self.result = {'response': 'arena synthetic cached result', 'world_version': 2}
        self.candidate = write_candidate(self.marker, self.spec, self.result)
        self.ack_dir = self.exchange / 'acks'

    # -- helpers ----------------------------------------------------------
    def marker_state(self) -> str:
        return json.loads(self.marker.read_bytes())['state']

    def assert_no_completion_credit(self):
        """Nothing that would mean the operation was locally credited."""
        record = json.loads(self.marker.read_bytes())
        self.assertNotEqual(record.get('state'), 'completed',
                            'a rejected remote authority must never mark the operation completed')
        self.assertNotIn('remote_commit', record,
                         'a rejected remote authority must never record a remote commit binding')
        self.assertFalse(self.ack_dir.exists() and any(self.ack_dir.iterdir()),
                         'a rejected remote authority must never produce an ACK marker')
        self.assertEqual(sorted(p.name for p in self.exchange.glob('*.ack.json')), [])

    def commit_candidate_to_remote(self, *, message='arena synthetic candidate'):
        """Push the pending candidate so recovery has a genuine remote commit."""
        _ref, commit = remote_backend.push_run_state(
            self.backend, remote_ref=self.remote_ref, repo_dir=self.repo, message=message)
        return commit

    # -- positive control -------------------------------------------------
    def test_positive_control_a_verified_remote_authority_does_complete_locally(self):
        """Without this, the rejection tests below could pass vacuously."""
        commit = self.commit_candidate_to_remote()
        recovered = recover_remote_candidate(
            backend=self.backend, marker=self.marker, spec=self.spec,
            remote_ref=self.remote_ref, repo=self.repo, remote_backend=remote_backend,
            verify_local_remote_authority=remote_backend.verify_local_remote_authority)
        self.assertEqual(recovered['remote_commit'], commit)
        self.assertTrue(recovered['recovered_without_redispatch'])
        self.assertEqual(self.marker_state(), 'completed',
                         'the harness CAN complete locally, so a refusal below is meaningful')

    # -- PM priority case: rejected authority, no marker -------------------
    def test_rejected_remote_authority_produces_no_completed_marker(self):
        """The injected seam is the production dependency-injection point."""
        self.commit_candidate_to_remote()
        calls = []

        def rejecting_authority(*args, **kwargs):
            calls.append((args, kwargs))
            raise RuntimeError('arena synthetic remote authority rejection')

        with self.assertRaises(RemoteCompletionError) as caught:
            recover_remote_candidate(
                backend=self.backend, marker=self.marker, spec=self.spec,
                remote_ref=self.remote_ref, repo=self.repo,
                remote_backend=remote_backend,
                verify_local_remote_authority=rejecting_authority)
        self.assertIn('remote authority could not be verified', str(caught.exception))
        self.assertEqual(len(calls), 1, 'the authority must actually have been consulted')
        self.assertEqual(self.marker_state(), 'remote_committing',
                         'the marker must stay a candidate, never a completion')
        self.assert_no_completion_credit()

    def test_rejected_authority_is_consulted_before_any_local_confirmation(self):
        """``finalize_local`` -- the only completion writer -- is never reached."""
        self.commit_candidate_to_remote()
        finalize_calls = []
        original_finalize = remote_completion_module.finalize_local

        def spying_finalize(*args, **kwargs):
            finalize_calls.append((args, kwargs))
            return original_finalize(*args, **kwargs)

        remote_completion_module.finalize_local = spying_finalize
        self.addCleanup(setattr, remote_completion_module, 'finalize_local',
                        original_finalize)

        def rejecting_authority(*_args, **_kwargs):
            raise RuntimeError('arena synthetic rejection before confirmation')

        with self.assertRaises(RemoteCompletionError):
            recover_remote_candidate(
                backend=self.backend, marker=self.marker, spec=self.spec,
                remote_ref=self.remote_ref, repo=self.repo,
                remote_backend=remote_backend,
                verify_local_remote_authority=rejecting_authority)
        self.assertEqual(finalize_calls, [],
                         'finalize_local must never run after the authority rejects')
        self.assertEqual(self.marker_state(), 'remote_committing')
        self.assert_no_completion_credit()

    def test_genuine_remote_head_divergence_is_refused_by_the_real_authority(self):
        """A real competing writer advancing the ref makes the REAL check fail.

        This uses the unmodified ``remote_backend.verify_local_remote_authority``
        against a real bare Git remote -- no stub and no injection.
        """
        self.commit_candidate_to_remote()
        # The cache is now anchored to a known remote head.
        anchored = (self.root / remote_backend.LOCAL_EXPECTED_HEAD).read_text().strip()
        verified = remote_backend.verify_local_remote_authority(
            self.backend, remote_ref=self.remote_ref, repo_dir=self.repo)
        self.assertEqual(verified, anchored)

        # A competing writer advances the same ref behind this cache's back.
        tree = git(self.repo, 'rev-parse', f'{anchored}^{{tree}}')
        competing = git(self.repo, 'commit-tree', tree, '-p', anchored,
                        '-m', 'arena synthetic competing writer')
        git(self.repo, 'push', '-q', 'origin', f'{competing}:{self.remote_ref}')
        self.assertEqual(remote_backend._remote_head(self.repo, 'origin', self.remote_ref),
                         competing)

        with self.assertRaises(Exception) as caught:
            remote_backend.verify_local_remote_authority(
                self.backend, remote_ref=self.remote_ref, repo_dir=self.repo)
        self.assertIn('remote authority head mismatch', str(caught.exception))
        # The local cache must not have been silently re-anchored by the refusal.
        self.assertEqual((self.root / remote_backend.LOCAL_EXPECTED_HEAD).read_text().strip(),
                         anchored)
        self.assertEqual(self.marker_state(), 'remote_committing')
        self.assert_no_completion_credit()

    def test_cached_completion_replay_is_refused_when_the_authority_now_rejects(self):
        """A previously completed record cannot be re-served on a broken anchor."""
        self.commit_candidate_to_remote()
        recovered = recover_remote_candidate(
            backend=self.backend, marker=self.marker, spec=self.spec,
            remote_ref=self.remote_ref, repo=self.repo, remote_backend=remote_backend,
            verify_local_remote_authority=remote_backend.verify_local_remote_authority)
        self.assertEqual(self.marker_state(), 'completed')
        completed_bytes = self.marker.read_bytes()

        def rejecting_authority(*_args, **_kwargs):
            raise RuntimeError('arena synthetic authority rejection on replay')

        with self.assertRaises(RemoteCompletionError) as caught:
            verify_completed_remote_record(
                backend=self.backend, marker=self.marker,
                record=json.loads(completed_bytes), spec=self.spec,
                remote_ref=self.remote_ref, repo=self.repo,
                remote_backend=remote_backend,
                verify_local_remote_authority=rejecting_authority)
        self.assertIn('current remote authority cannot be verified', str(caught.exception))
        self.assertEqual(self.marker.read_bytes(), completed_bytes,
                         'a refused replay must not rewrite the completion record')
        self.assertEqual(json.loads(completed_bytes)['remote_commit'],
                         recovered['remote_commit'])

    def test_absent_remote_ref_is_refused_without_completion(self):
        """No authoritative remote ref at all means no local completion."""
        orphan_ref = 'refs/heads/persistence/arena-synthetic-orphan'
        with self.assertRaises(RemoteCompletionError) as caught:
            recover_remote_candidate(
                backend=self.backend, marker=self.marker, spec=self.spec,
                remote_ref=orphan_ref, repo=self.repo, remote_backend=remote_backend,
                verify_local_remote_authority=remote_backend.verify_local_remote_authority)
        self.assertIn('no authoritative remote ref', str(caught.exception))
        self.assertEqual(self.marker_state(), 'remote_committing')
        self.assert_no_completion_credit()

    def test_locally_diverged_candidate_is_refused_by_the_tree_comparison(self):
        """A locally rewritten candidate is caught before any recovery is attempted.

        Observed behaviour, pinned deliberately: ``_compare_local_tree_to_remote_candidate``
        is a STRICTER and EARLIER gate than the per-candidate byte comparison.
        Because the operation marker lives inside the compared persistence tree,
        any local divergence is refused as a tree mismatch, so the later
        ``remote head does not contain the exact pending operation candidate``
        check is not the gate that fires here.
        """
        self.commit_candidate_to_remote()
        diverged = dict(self.candidate)
        diverged['result'] = {'response': 'arena rewritten result', 'world_version': 3}
        diverged['result_sha256'] = hashlib.sha256(
            canonical_json_bytes(diverged['result'])).hexdigest()
        self.marker.write_bytes(canonical_json_bytes(diverged))
        with self.assertRaises(RemoteCompletionError) as caught:
            recover_remote_candidate(
                backend=self.backend, marker=self.marker, spec=diverged['spec'],
                remote_ref=self.remote_ref, repo=self.repo,
                remote_backend=remote_backend,
                verify_local_remote_authority=remote_backend.verify_local_remote_authority)
        self.assertIn('local persistence bytes differ from remote commit',
                      str(caught.exception))
        self.assertIn(self.marker.relative_to(self.root).as_posix(), str(caught.exception))
        self.assertEqual(json.loads(self.marker.read_bytes())['state'], 'remote_committing')
        self.assert_no_completion_credit()

    def test_remote_tree_containing_an_unexpected_file_refuses_recovery(self):
        """An extra local file also breaks the exact tree correspondence."""
        self.commit_candidate_to_remote()
        (self.root / 'arena-unexpected.bin').write_bytes(b'arena')
        with self.assertRaises(RemoteCompletionError) as caught:
            recover_remote_candidate(
                backend=self.backend, marker=self.marker, spec=self.spec,
                remote_ref=self.remote_ref, repo=self.repo,
                remote_backend=remote_backend,
                verify_local_remote_authority=remote_backend.verify_local_remote_authority)
        self.assertIn('local cache file set differs from the candidate remote commit',
                      str(caught.exception))
        self.assertEqual(self.marker_state(), 'remote_committing')
        self.assert_no_completion_credit()

    def test_wrong_remote_ref_binding_is_refused(self):
        """A cached completion bound to another ref cannot be replayed."""
        self.commit_candidate_to_remote()
        recover_remote_candidate(
            backend=self.backend, marker=self.marker, spec=self.spec,
            remote_ref=self.remote_ref, repo=self.repo, remote_backend=remote_backend,
            verify_local_remote_authority=remote_backend.verify_local_remote_authority)
        record = json.loads(self.marker.read_bytes())
        self.assertEqual(record['state'], 'completed')
        with self.assertRaises(RemoteCompletionError) as caught:
            verify_completed_remote_record(
                backend=self.backend, marker=self.marker, record=record, spec=self.spec,
                remote_ref='refs/heads/persistence/arena-other-run', repo=self.repo,
                remote_backend=remote_backend,
                verify_local_remote_authority=remote_backend.verify_local_remote_authority)
        self.assertIn('cached completion remote ref mismatch', str(caught.exception))


class FinalizeLocalGateTests(unittest.TestCase):
    """``finalize_local`` is the only writer of ``state == 'completed'``."""

    def setUp(self):
        self._temp = make_workdir('arena-eng-finalize-')
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.spec = {'mode': 'user', 'cursor': 1, 'event_id': 'arena-finalize'}
        self.result = {'response': 'arena synthetic result'}
        self.marker = self.root / 'operation.json'
        self.marker.write_bytes(canonical_json_bytes(
            {'state': 'started',
             'operation_id': hashlib.sha256(canonical_json_bytes(self.spec)).hexdigest(),
             'spec': self.spec}))
        self.candidate = write_candidate(self.marker, self.spec, self.result)
        self.candidate_bytes = canonical_json_bytes(self.candidate)

    def test_mismatched_remote_candidate_bytes_never_complete_the_operation(self):
        with self.assertRaises(CompletionError) as caught:
            finalize_local(self.marker, self.candidate,
                           remote_ref='refs/heads/persistence/arena-run',
                           remote_commit='a' * 40,
                           remote_candidate_bytes=canonical_json_bytes(
                               {**self.candidate, 'result': {'response': 'rewritten'}}))
        self.assertIn('authoritative remote candidate bytes do not match', str(caught.exception))
        self.assertEqual(json.loads(self.marker.read_bytes())['state'], 'remote_committing')
        self.assertNotIn('remote_commit', json.loads(self.marker.read_bytes()))

    def test_matching_remote_candidate_bytes_do_complete_the_operation(self):
        """Positive control for the refusal above."""
        completed = finalize_local(self.marker, self.candidate,
                                   remote_ref='refs/heads/persistence/arena-run',
                                   remote_commit='a' * 40,
                                   remote_candidate_bytes=self.candidate_bytes)
        self.assertEqual(completed['state'], 'completed')
        self.assertEqual(json.loads(self.marker.read_bytes())['state'], 'completed')

    def test_locally_modified_candidate_is_refused(self):
        self.marker.write_bytes(canonical_json_bytes({**self.candidate, 'state': 'tampered'}))
        with self.assertRaises(CompletionError) as caught:
            finalize_local(self.marker, self.candidate,
                           remote_ref='refs/heads/persistence/arena-run',
                           remote_commit='a' * 40,
                           remote_candidate_bytes=self.candidate_bytes)
        self.assertIn('local operation candidate changed before confirmation',
                      str(caught.exception))

    def test_completion_record_requires_a_canonical_persistence_ref(self):
        for bad_ref in ('main', 'refs/heads/main', 'persistence/arena-run', '', None):
            with self.subTest(remote_ref=bad_ref):
                with self.assertRaises(CompletionError) as caught:
                    completion_record(self.candidate, remote_ref=bad_ref,
                                      remote_commit='a' * 40)
                self.assertIn('canonical persistence ref', str(caught.exception))

    def test_completion_record_requires_a_valid_commit_identity(self):
        for bad_commit in ('abc', 'z' * 40, 'A' * 40, '', None, 'a' * 39):
            with self.subTest(remote_commit=bad_commit):
                with self.assertRaises(CompletionError) as caught:
                    completion_record(self.candidate,
                                      remote_ref='refs/heads/persistence/arena-run',
                                      remote_commit=bad_commit)
                self.assertIn('remote commit identity is invalid', str(caught.exception))

    def test_completed_record_is_bound_to_its_exact_remote_candidate(self):
        completed = completion_record(self.candidate,
                                      remote_ref='refs/heads/persistence/arena-run',
                                      remote_commit='b' * 40)
        validate_completed(completed, self.spec,
                           remote_candidate_bytes=self.candidate_bytes,
                           remote_commit='b' * 40)
        with self.assertRaises(CompletionError) as caught:
            validate_completed(completed, self.spec,
                               remote_candidate_bytes=canonical_json_bytes({'other': 1}),
                               remote_commit='b' * 40)
        self.assertIn('remote candidate digest mismatch', str(caught.exception))
        with self.assertRaises(CompletionError) as caught:
            validate_completed(completed, self.spec,
                               remote_candidate_bytes=self.candidate_bytes,
                               remote_commit='c' * 40)
        self.assertIn('remote commit binding mismatch', str(caught.exception))


if __name__ == '__main__':
    unittest.main(verbosity=2)
