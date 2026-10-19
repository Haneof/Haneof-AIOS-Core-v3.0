"""Completion state-machine and fault-window unit tests."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
HARNESS = REPO / 'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness'
sys.path.insert(0, str(HARNESS))

from r005.completion import (CompletionError, candidate_record, finalize_local,
                             operation_id, validate_candidate, validate_completed,
                             write_candidate)
from r005.canonical import canonical_json_bytes


class InjectedCrash(RuntimeError):
    pass


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='r005-completion-')
        self.marker = Path(self.temp.name) / 'operation.json'
        self.spec = {'mode': 'user', 'at': '2026-10-14T12:00:00+00:00', 'cursor': 1,
                     'event_id': 'event-1', 'turn_index': 1, 'user_input': 'hello', 'timeout': 30}
        self.result = {'response': 'cached once', 'world_version': 3}
        self.marker.write_bytes(canonical_json_bytes({
            'state': 'started', 'operation_id': operation_id(self.spec), 'spec': self.spec}))

    def tearDown(self):
        self.temp.cleanup()

    def test_fault_before_local_result_write_leaves_started_state(self):
        def crash(point):
            self.assertEqual(point, 'before_local_result_write')
            raise InjectedCrash(point)
        with self.assertRaises(InjectedCrash):
            write_candidate(self.marker, self.spec, self.result, fault_hook=crash)
        self.assertEqual(json.loads(self.marker.read_bytes())['state'], 'started')

    def test_fault_after_local_result_write_leaves_only_candidate_not_complete(self):
        def crash(point):
            if point == 'after_local_result_write_before_remote_commit':
                raise InjectedCrash(point)
        with self.assertRaises(InjectedCrash):
            write_candidate(self.marker, self.spec, self.result, fault_hook=crash)
        record = json.loads(self.marker.read_bytes())
        self.assertEqual(record['state'], 'remote_committing')
        self.assertEqual(record['result'], self.result)
        self.assertEqual(record['result_sha256'], candidate_record(self.spec, self.result)['result_sha256'])

    def test_write_candidate_requires_exact_started_operation_marker(self):
        self.marker.write_bytes(canonical_json_bytes({
            'state': 'started', 'operation_id': '0' * 64, 'spec': self.spec}))
        with self.assertRaisesRegex(CompletionError, 'exact started operation'):
            write_candidate(self.marker, self.spec, self.result)
        self.assertEqual(json.loads(self.marker.read_bytes())['state'], 'started')

    def test_finalize_rechecks_current_disk_candidate_before_local_confirmation(self):
        candidate = write_candidate(self.marker, self.spec, self.result)
        altered = {**candidate, 'result': {'response': 'substituted'}}
        self.marker.write_bytes(canonical_json_bytes(altered))
        with self.assertRaisesRegex(CompletionError, 'changed before confirmation'):
            finalize_local(self.marker, candidate,
                remote_ref='refs/heads/persistence/run-1', remote_commit='c' * 40,
                remote_candidate_bytes=canonical_json_bytes(candidate))
        self.assertEqual(json.loads(self.marker.read_bytes())['state'], 'remote_committing')

    def test_remote_bytes_must_match_before_local_completion(self):
        candidate = write_candidate(self.marker, self.spec, self.result)
        with self.assertRaisesRegex(CompletionError, 'do not match'):
            finalize_local(self.marker, candidate, remote_ref='refs/heads/persistence/run-1',
                           remote_commit='a' * 40, remote_candidate_bytes=b'{}')
        self.assertEqual(json.loads(self.marker.read_bytes())['state'], 'remote_committing')

    def test_fault_after_remote_commit_preconfirmation_is_recoverable_candidate(self):
        candidate = write_candidate(self.marker, self.spec, self.result)
        committed = canonical_json_bytes(candidate)
        def crash(point):
            self.assertEqual(point, 'after_remote_commit_before_local_confirmation')
            raise InjectedCrash(point)
        with self.assertRaises(InjectedCrash):
            finalize_local(self.marker, candidate, remote_ref='refs/heads/persistence/run-1',
                           remote_commit='b' * 40, remote_candidate_bytes=committed,
                           fault_hook=crash)
        self.assertEqual(json.loads(self.marker.read_bytes())['state'], 'remote_committing')
        completed = finalize_local(self.marker, candidate,
            remote_ref='refs/heads/persistence/run-1', remote_commit='b' * 40,
            remote_candidate_bytes=committed)
        self.assertEqual(completed['state'], 'completed')
        self.assertEqual(completed['remote_commit'], 'b' * 40)
        replay = validate_completed(completed, self.spec,
            remote_candidate_bytes=committed, remote_commit='b' * 40)
        self.assertEqual(replay['result'], self.result)

    def test_operation_and_result_tampering_or_replay_mismatch_fails(self):
        candidate = candidate_record(self.spec, self.result)
        with self.assertRaisesRegex(CompletionError, 'replay binding'):
            validate_candidate(candidate, {**self.spec, 'user_input': 'different'})
        tampered = {**candidate, 'result': {'response': 'changed'}}
        with self.assertRaisesRegex(CompletionError, 'digest mismatch'):
            validate_candidate(tampered, self.spec)


if __name__ == '__main__':
    unittest.main()
