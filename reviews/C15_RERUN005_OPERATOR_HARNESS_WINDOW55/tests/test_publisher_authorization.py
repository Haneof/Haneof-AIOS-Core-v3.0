"""One-request Resident authorization capability isolation tests."""
from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
import pty
import sys
import unittest

REPO = Path(__file__).resolve().parents[3]
HARNESS = REPO / 'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness'
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HARNESS))

from r005.response_authorization import (issue_response_authorization,
                                         response_authorization_valid,
                                         retire_response_authorization,
                                         write_resident_capability)
from r005.canonical import canonical_json_bytes


class PublisherAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.registry = {}
        self.instance = 'runner-instance-current'
        self.operation = 'operation-current'
        self.request_id = 'request-current'
        self.content = {
            'request_id': self.request_id,
            'request_sha256': 'a' * 64,
            'raw': 'eyJyZXNwb25zZSI6Im9rIn0=',
        }
        self.token = issue_response_authorization(
            self.registry, self.request_id,
            runner_instance_id=self.instance, operation_id=self.operation)
        self.proof = hmac.new(self.token.encode(), canonical_json_bytes(self.content),
                              hashlib.sha256).hexdigest()

    def test_authorization_is_bound_to_request_runner_instance_and_operation(self):
        self.assertTrue(response_authorization_valid(
            self.registry, self.request_id, self.content, self.proof,
            runner_instance_id=self.instance, operation_id=self.operation))
        self.assertFalse(response_authorization_valid(
            self.registry, 'another-request', self.content, self.proof,
            runner_instance_id=self.instance, operation_id=self.operation))
        self.assertFalse(response_authorization_valid(
            self.registry, self.request_id, self.content, self.proof,
            runner_instance_id='restarted-runner', operation_id=self.operation))
        self.assertFalse(response_authorization_valid(
            self.registry, self.request_id, self.content, self.proof,
            runner_instance_id=self.instance, operation_id='another-operation'))
        changed = {**self.content, 'raw': 'different-response'}
        self.assertFalse(response_authorization_valid(
            self.registry, self.request_id, changed, self.proof,
            runner_instance_id=self.instance, operation_id=self.operation))
        self.assertFalse(response_authorization_valid(
            self.registry, self.request_id, self.content, 'copied-invalid-capability',
            runner_instance_id=self.instance, operation_id=self.operation))

    def test_capability_disclosure_writes_to_terminal_descriptor(self):
        master, terminal = pty.openpty()
        try:
            write_resident_capability(terminal, self.token, self.request_id, self.operation)
            visible = os.read(master, 4096).decode('ascii')
        finally:
            os.close(master)
            os.close(terminal)
        self.assertIn('RESIDENT_PUBLISH_AUTHORIZATION=' + self.token, visible)
        self.assertIn('REQUEST_ID=' + self.request_id, visible)
        self.assertIn('OPERATION_ID=' + self.operation, visible)

    def test_capability_is_one_use_and_not_reissued_for_a_registered_request(self):
        with self.assertRaisesRegex(ValueError, 'already issued'):
            issue_response_authorization(
                self.registry, self.request_id,
                runner_instance_id=self.instance, operation_id=self.operation)
        retire_response_authorization(
            self.registry, self.request_id,
            runner_instance_id=self.instance, operation_id=self.operation)
        self.assertNotIn(self.request_id, self.registry)
        self.assertFalse(response_authorization_valid(
            self.registry, self.request_id, self.content, self.proof,
            runner_instance_id=self.instance, operation_id=self.operation))


if __name__ == '__main__':
    unittest.main()
