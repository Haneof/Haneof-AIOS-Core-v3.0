"""The enrollment gate must validate the run/session scope it is relied on for.

DEVELOPMENT_ONLY / FORMAL_VALIDATION_NOT_PERFORMED / DO_NOT_MERGE

FINDING (Arena C15-ENG-001)
---------------------------
``load_grant`` is the single "this TEST_ONLY enrollment is approved" gate. It
meticulously validates the domain, version, purpose, ``test_only`` flag, issuer
identity, Resident identity/UID/key, the embedded public key against the pinned
trust copy, the whole time window, the enrollment-id shape, the instance-id
shape, the bounded exact ``operation_ids`` scope, the bounded ``request_kinds``
scope and the revocation record.

It does **not** validate ``run_id`` or ``session_id`` at all -- yet two separate
production call sites treat them as authoritative scope bindings:

* ``SignedResponseAuthority.register``:
  ``require(identity['run_id'] == grant['run_id'] and
            identity['session_id'] == grant['session_id'] ...)``
* ``safe_runner`` pre-launch:
  ``require(grant['run_id'] == run_id and grant['session_id'] == session_id
            and opid in grant['operation_ids'], ...)``

Consequence, reproduced by ``test_unscoped_grant_can_never_authorize_a_response``
below: an enrollment that omits those fields passes the approval gate and is
only stopped later by a bare ``KeyError`` raised deep inside the Publisher
dispatch loop -- after the Runner's durable request registration has already
succeeded. The request then can never be answered in signed mode, and the
failure surfaces as ``KeyError: 'run_id'`` rather than as an enrollment
rejection.

SEVERITY: fail-closed hardening, **not** an authorization bypass. No test in
this suite demonstrates a response being published that should have been
refused; the security property holds both before and after the patch. What the
patch changes is *where* the refusal happens: at the enrollment gate, with the
same clean ``ValueError`` vocabulary every other scope check in ``load_grant``
uses, instead of an uncontrolled ``KeyError`` two layers deeper.

The real Operator-issued grants recorded in
``reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66/reproduction/issue-finalcandidate.py``
always carry non-blank string ``run_id`` and ``session_id``, so the added
requirement cannot reject any enrollment that could ever have worked.
"""
from __future__ import annotations

import os
from pathlib import Path
import time
import unittest
from unittest import mock

from synthetic_fixtures import (ExchangeBridge, RunnerRegistrationAuthority,
                                SyntheticTrustRoot, canonical_json_bytes,
                                make_workdir, process_start_time,
                                response_authorization as ra)

ENROLLMENT_ENV = 'AIOS66_TEST_ENROLLMENT'
EXPECTED_REASON = 'enrollment run/session scope required'


class EnrollmentScopeGateTests(unittest.TestCase):
    """RED-first tests for the missing run/session scope validation."""

    OPERATION_ID = 'b' * 64
    INSTANCE_ID = 'a' * 64

    def setUp(self):
        self._temp = make_workdir('arena-eng-scope-')
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.trust = SyntheticTrustRoot(self.root).install()
        self.addCleanup(self.trust.restore)
        self.now = int(time.time())
        saved = os.environ.get(ENROLLMENT_ENV)
        os.environ[ENROLLMENT_ENV] = SyntheticTrustRoot.GRANT_PATH
        self.addCleanup(self._restore_env, saved)

        # A real durable exchange and a real Runner registration, used by the
        # invariant test to prove no response can ever be authorized.
        self.bridge = ExchangeBridge(self.root / 'exchange')
        record = self.bridge.publish_request(
            kind='round_summary',
            body={'identity': {'run_id': 'arena-synthetic-run',
                               'session_id': 'arena-synthetic-session',
                               'subject_id': 'arena-synthetic-subject'},
                  'prompt': 'arena synthetic'})
        self.rid = record['request_id']
        runner_pid = os.getpid()
        authority = RunnerRegistrationAuthority(
            runner_pid=runner_pid, runner_uid=os.getuid(), runner_gid=os.getgid(),
            runner_start_time=process_start_time(runner_pid),
            runner_instance_id=self.INSTANCE_ID, operation_id=self.OPERATION_ID,
            key_id='arena-synthetic-key', runner_alive=lambda: True)
        _rid, self.registration = authority.register(
            (runner_pid, os.getuid(), os.getgid()),
            {'command': 'register', 'request_id': self.rid,
             'request_sha256': record['request_sha256'], 'context': None,
             'core_attempt_id': None, 'runner_instance_id': self.INSTANCE_ID,
             'operation_id': self.OPERATION_ID}, self.bridge)
        self.registration_authority = authority

    @staticmethod
    def _restore_env(saved):
        if saved is None:
            os.environ.pop(ENROLLMENT_ENV, None)
        else:
            os.environ[ENROLLMENT_ENV] = saved

    # -- grant builders ---------------------------------------------------
    def publish_grant(self, **overrides) -> dict:
        grant = self.trust.grant(now=self.now, operation_ids=[self.OPERATION_ID],
                                 instance_id=self.INSTANCE_ID, **overrides)
        self.trust.publish(grant)
        return grant

    def publish_grant_without_scope(self, *, blank=False):
        """A grant that is otherwise perfect but has no usable run/session scope."""
        grant = self.trust.grant(now=self.now, operation_ids=[self.OPERATION_ID],
                                 instance_id=self.INSTANCE_ID)
        if blank:
            grant['run_id'] = ''
            grant['session_id'] = ''
        else:
            grant.pop('run_id')
            grant.pop('session_id')
        self.trust.publish(grant)
        return grant

    # -- positive control -------------------------------------------------
    def test_positive_control_a_fully_scoped_grant_is_accepted(self):
        """Without this, the refusals below could pass vacuously."""
        self.publish_grant()
        grant = self.trust.load()
        self.assertEqual(grant['run_id'], 'arena-synthetic-run')
        self.assertEqual(grant['session_id'], 'arena-synthetic-session')

    # -- RED-first gate assertions ----------------------------------------
    def test_gate_rejects_a_grant_that_omits_the_run_and_session_scope(self):
        """The approval gate must refuse what its callers treat as mandatory."""
        self.publish_grant_without_scope()
        with self.assertRaises(ValueError) as caught:
            self.trust.load()
        self.assertIn(EXPECTED_REASON, str(caught.exception))

    def test_gate_rejects_a_blank_run_or_session_scope(self):
        for field in ('run_id', 'session_id'):
            with self.subTest(field=field):
                self.publish_grant(**{field: ''})
                with self.assertRaises(ValueError) as caught:
                    self.trust.load()
                self.assertIn(EXPECTED_REASON, str(caught.exception))

    def test_gate_rejects_a_non_string_run_or_session_scope(self):
        for field, value in (('run_id', 12345), ('session_id', None),
                             ('run_id', ['arena-run']), ('session_id', {'id': 'x'})):
            with self.subTest(field=field, value=type(value).__name__):
                self.publish_grant(**{field: value})
                with self.assertRaises(ValueError) as caught:
                    self.trust.load()
                self.assertIn(EXPECTED_REASON, str(caught.exception))

    def test_refusal_is_a_clean_gate_error_not_a_late_key_error(self):
        """The refusal must arrive at the enrollment gate as a ValueError."""
        self.publish_grant_without_scope()
        try:
            self.trust.load()
        except KeyError as exc:  # pragma: no cover - the pre-patch symptom
            self.fail(f'the enrollment gate leaked a bare KeyError({exc}) instead of '
                      f'refusing the grant with {EXPECTED_REASON!r}')
        except ValueError as exc:
            self.assertIn(EXPECTED_REASON, str(exc))
        else:  # pragma: no cover - the pre-patch symptom
            self.fail('an enrollment without run/session scope was approved by the gate')

    # -- invariant: true before AND after the patch ------------------------
    def test_unscoped_grant_can_never_authorize_a_response(self):
        """Holds pre- and post-patch: no publication, no proof, no marker."""
        for label, blank in (('omitted', False), ('blank', True)):
            with self.subTest(scope=label):
                self.publish_grant_without_scope(blank=blank)
                with self.assertRaises((ValueError, KeyError)) as caught:
                    with mock.patch('os.getuid', return_value=999):
                        authority = ra.SignedResponseAuthority(self.OPERATION_ID,
                                                               self.INSTANCE_ID)
                    # Only reached when the gate approved the grant (pre-patch).
                    authority.register(self.rid, self.registration, self.bridge)
                self.assertIsInstance(caught.exception, (ValueError, KeyError))
                self.assertFalse(self.bridge.responses.path_for(self.rid).exists(),
                                 'no response artifact may ever be produced')
                self.assertIsNone(self.bridge.published_response_record(self.rid),
                                  'no response_published ledger record may ever exist')
                self.assertEqual(list((self.root / 'exchange' / 'proofs').glob('*'))
                                 if (self.root / 'exchange' / 'proofs').exists() else [],
                                 [], 'no Publisher proof may ever be written')

    def test_safe_runner_scope_check_also_depends_on_these_fields(self):
        """Documents the second production consumer of the unvalidated fields."""
        source = (Path(ra.__file__).parent / 'safe_runner.py').read_text(encoding='utf-8')
        compact = ''.join(source.split())
        self.assertIn("grant['run_id']==run_id", compact)
        self.assertIn("grant['session_id']==session_id", compact)
        self.assertIn('configured_grant()', source)
        self.publish_grant_without_scope()
        # Pre-patch this raises KeyError on the subscript; post-patch the gate
        # refuses the enrollment outright. Either way it can never succeed.
        with self.assertRaises((ValueError, KeyError)):
            _ = ra.configured_grant()['run_id']


if __name__ == '__main__':
    unittest.main(verbosity=2)
