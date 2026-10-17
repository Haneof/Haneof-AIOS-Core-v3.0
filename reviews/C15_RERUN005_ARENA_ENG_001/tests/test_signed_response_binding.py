"""Window66 signed no-controlling-TTY response authorization binding tests.

DEVELOPMENT_ONLY / FORMAL_VALIDATION_NOT_PERFORMED / DO_NOT_MERGE

Covers the PM-prioritized contract cases against the REAL production code in
``harness/r005/response_authorization.py``:

* a wrong request / operation / instance / context / run / session / kind /
  enrollment / epoch / challenge, or a changed raw-response hash, can NEVER
  satisfy a matching signed-response request, and no Publisher publication,
  ledger record, Core-proof input or completion/ACK marker may be credited;
* a replayed / double-consumed challenge does not authorize a second semantic
  response;
* a stale Publisher epoch (a restarted Publisher) cannot honor an envelope
  issued by a previous epoch.

All keys are synthetic and disposable; all peer credentials are literal
fixtures. No real pinned Operator issuer key, Resident private key, Window68
grant, UID999/UID996 identity or approved Python runtime is used or claimed.

Rejected dispatches are proven to leave no state behind, so a single armed
fixture serves the whole negative matrix. Tests that deliberately corrupt
shared state allocate their own fixture via ``new_fixture``.
"""
from __future__ import annotations

import base64
import hashlib
import time
import unittest

from synthetic_fixtures import (SYNTHETIC_RESIDENT_PEER, SYNTHETIC_UNAPPROVED_PEER,
                                FakeConnection, FrozenClock, SignedExchangeFixture,
                                canonical_json_bytes, make_workdir,
                                response_authorization)


class SignedResponseBindingTests(unittest.TestCase):
    """Envelope-binding matrix for the signed response endpoint."""

    def setUp(self):
        self._root = make_workdir('arena-eng-binding-')
        self.addCleanup(self._root.cleanup)
        self._serial = 0
        self.fixture = self.new_fixture('primary')
        self.rid, self.record = self.fixture.arm()

    def new_fixture(self, label: str, **kwargs) -> SignedExchangeFixture:
        """Allocate an isolated fixture in its own subdirectory of the root."""
        self._serial += 1
        fixture = SignedExchangeFixture(f'{self._root.name}/{label}-{self._serial}', **kwargs)
        self.addCleanup(fixture.restore)
        return fixture

    # -- helpers ----------------------------------------------------------
    def assert_rejected_without_credit(self, fixture, rid, *, command=None, raw=None,
                                       peer=SYNTHETIC_RESIDENT_PEER, runner_live=True,
                                       expected_reason=None):
        """Assert the dispatch fails closed and credits absolutely nothing."""
        before = fixture.credited_anything(rid)
        self.assertEqual(before['publish_calls'], 0, 'fixture must start uncredited')
        with self.assertRaises(Exception) as caught:
            if raw is not None:
                fixture.dispatch_raw(raw, peer=peer, runner_live=runner_live)
            else:
                fixture.dispatch(command, peer=peer, runner_live=runner_live)
        if expected_reason is not None:
            self.assertIn(expected_reason, str(caught.exception),
                          f'unexpected refusal reason: {caught.exception}')
        after = fixture.credited_anything(rid)
        self.assertEqual(after['publish_calls'], 0,
                         'a rejected authority must never reach the Publisher publish path')
        self.assertFalse(after['response_artifact'],
                         'a rejected authority must never create a durable response artifact')
        self.assertFalse(after['response_ledger_record'],
                         'a rejected authority must never append a response_published record')
        self.assertEqual(after['ack_markers'], [],
                         'a rejected authority must never create a completion/ACK marker')
        self.assertNotIn(rid, fixture.authority.verified_digests,
                         'a rejected authority must never record a resident authorization digest')
        return caught.exception

    def reject(self, command=None, *, raw=None, expected_reason=None, **kwargs):
        """Shorthand against the primary armed fixture."""
        return self.assert_rejected_without_credit(
            self.fixture, self.rid, command=command, raw=raw,
            expected_reason=expected_reason, **kwargs)

    # -- positive control -------------------------------------------------
    def test_valid_signed_response_is_published_once_and_credit_is_recorded(self):
        """Positive control: the negative matrix below is not vacuously passing."""
        command = self.fixture.signed_command(self.rid, self.record)
        result = self.fixture.dispatch(command)
        credit = self.fixture.credited_anything(self.rid)
        self.assertEqual(credit['publish_calls'], 1)
        self.assertTrue(credit['response_artifact'])
        self.assertTrue(credit['response_ledger_record'])
        self.assertEqual(len(credit['ack_markers']), 1)
        self.assertTrue(credit['challenge_consumed'])
        self.assertIn('resident_authorization_sha256', result)
        expected_digest = hashlib.sha256(canonical_json_bytes(command['envelope'])).hexdigest()
        self.assertEqual(result['resident_authorization_sha256'], expected_digest)
        self.assertEqual(self.fixture.authority.verified_digests[self.rid], expected_digest)

    # -- changed raw-response hash / bytes --------------------------------
    def test_raw_bytes_that_disagree_with_the_signed_response_hash_are_rejected(self):
        """The signature binds the hash of the bytes that are actually published."""
        honest = self.fixture.signed_command(self.rid, self.record)
        smuggled = base64.b64encode(
            self.fixture.response_bytes(self.rid, self.record['request_sha256'],
                                        text='different bytes than were signed')).decode('ascii')
        self.reject({**honest, 'raw': smuggled},
                    expected_reason='signed envelope/request/operation/context/bytes mismatch')

    def test_response_hash_claimed_without_a_matching_signature_is_rejected(self):
        """Recomputing the hash for new bytes invalidates the original signature."""
        raw = self.fixture.response_bytes(self.rid, self.record['request_sha256'],
                                          text='rewritten after signing')
        self.reject(self.fixture.signed_command(self.rid, self.record, raw=raw,
                                                response_sha256='0' * 64),
                    expected_reason='signed envelope/request/operation/context/bytes mismatch')

    # -- envelope binding matrix -----------------------------------------
    def test_every_issued_envelope_binding_is_individually_enforced(self):
        """Mutating any single issued binding fails closed, even when re-signed.

        ``request_id`` is special: ``dispatch`` reads it out of the SUBMITTED
        envelope and looks it up in the live challenge table first, so a forged
        request id is refused as an unknown/consumed challenge before the exact
        envelope comparison runs. Every other binding is refused by the exact
        envelope equality check.
        """
        envelope_mismatch = 'signed envelope/request/operation/context/bytes mismatch'
        unknown_challenge = 'stale or consumed request challenge'
        cases = {
            'request_id': ('req-9999-round_summary-deadbeef', unknown_challenge),
            'request_sha256': ('f' * 64, envelope_mismatch),
            'request_kind': ('model_directive', envelope_mismatch),
            'operation_id': ('arena-operation-OTHER', envelope_mismatch),
            'instance_id': ('arena-instance-OTHER', envelope_mismatch),
            'context': ({'attempt_id': 'arena-injected-context'}, envelope_mismatch),
            'core_attempt_id': ('arena-injected-attempt', envelope_mismatch),
            'provenance': ({'provider': 'external-resident'}, envelope_mismatch),
            'run_id': ('arena-run-OTHER', envelope_mismatch),
            'session_id': ('arena-session-OTHER', envelope_mismatch),
            'publisher_epoch': ('arena-epoch-STALE', envelope_mismatch),
            'publisher_challenge': ('00' * 32, envelope_mismatch),
            'enrollment_id': ('W66-' + '1' * 36, envelope_mismatch),
            'enrollment_sha256': ('e' * 64, envelope_mismatch),
            'resident_id': ('AIOS_RESIDENT_PROD', envelope_mismatch),
            'resident_key_id': ('c' * 64, envelope_mismatch),
            'domain': ('aios.r005.other.v1', envelope_mismatch),
            'purpose': ('aios.r005.test.mechanical.ping.v1', envelope_mismatch),
            'version': (2, envelope_mismatch),
            'issued_at': (0, envelope_mismatch),
            'expires_at': (int(time.time()) + 999999, envelope_mismatch),
            'response_sha256': ('d' * 64, envelope_mismatch),
        }
        for field, (value, reason) in cases.items():
            with self.subTest(envelope_field=field):
                command = self.fixture.signed_command(
                    self.rid, self.record, mutate=lambda env: env.update({field: value}))
                self.reject(command, expected_reason=reason)

    def test_extra_or_removed_envelope_keys_are_rejected(self):
        """The comparison is exact-key equality, not a subset test."""
        self.reject(self.fixture.signed_command(self.rid, self.record,
                                                mutate=lambda env: env.update(arena_extra='x')),
                    expected_reason='signed envelope/request/operation/context/bytes mismatch')
        self.reject(self.fixture.signed_command(self.rid, self.record,
                                                mutate=lambda env: env.pop('run_id')),
                    expected_reason='signed envelope/request/operation/context/bytes mismatch')

    # -- replay / double consumption -------------------------------------
    def test_replay_of_an_identical_signed_response_authorizes_nothing_second(self):
        fixture = self.new_fixture('replay')
        rid, record = fixture.arm()
        command = fixture.signed_command(rid, record)
        fixture.dispatch(command)
        self.assertEqual(fixture.credited_anything(rid)['publish_calls'], 1)
        with self.assertRaises(ValueError) as caught:
            fixture.dispatch(command)
        self.assertIn('stale or consumed request challenge', str(caught.exception))
        credit = fixture.credited_anything(rid)
        self.assertEqual(credit['publish_calls'], 1,
                         'a consumed challenge must never authorize a second semantic response')
        self.assertEqual(len(credit['ack_markers']), 1,
                         'a consumed challenge must never create a second ACK marker')

    def test_replay_with_different_bytes_is_also_refused_after_consumption(self):
        """Retirement is permanent: consumed authority cannot authorize new bytes."""
        fixture = self.new_fixture('replay-bytes')
        rid, record = fixture.arm()
        fixture.dispatch(fixture.signed_command(rid, record))
        replay = fixture.signed_command(
            rid, record,
            raw=fixture.response_bytes(rid, record['request_sha256'],
                                       text='second, different semantic response'))
        with self.assertRaises(ValueError) as caught:
            fixture.dispatch(replay)
        self.assertIn('stale or consumed request challenge', str(caught.exception))
        credit = fixture.credited_anything(rid)
        self.assertEqual(credit['publish_calls'], 1)
        self.assertEqual(len(credit['ack_markers']), 1)

    def test_unknown_request_id_is_refused_before_any_envelope_evaluation(self):
        self.reject(self.fixture.signed_command(self.rid, self.record,
                                                mutate=lambda env: env.update(
                                                    request_id='req-0000-unknown-00000000')),
                    expected_reason='stale or consumed request challenge')

    # -- stale Publisher epoch -------------------------------------------
    def test_a_restarted_publisher_epoch_cannot_honor_a_previous_round(self):
        """Envelopes are bound to the epoch of the process that issued them."""
        stale_command = self.fixture.signed_command(self.rid, self.record)
        restarted = self.new_fixture('restarted',
                                     operation_id=self.fixture.operation_id,
                                     instance_id=self.fixture.instance_id,
                                     epoch='arena-epoch-2')
        self.assertNotEqual(restarted.epoch, self.fixture.authority.epoch)
        self.assertEqual(restarted.authority.pending, {},
                         'a restarted Publisher must begin with no inherited challenges')
        with self.assertRaises(Exception) as caught:
            restarted.dispatch(stale_command)
        self.assertIn('stale or consumed request challenge', str(caught.exception))
        self.assertEqual(restarted.published_commands, [])

    # -- expiry ------------------------------------------------------------
    def test_expired_challenge_is_refused_and_ttl_is_bounded(self):
        clock = FrozenClock(1_800_000_000.0)
        fixture = self.new_fixture('expiry', clock=clock)
        rid, record = fixture.arm()
        envelope = fixture.authority.pending[rid]['envelope']
        self.assertLessEqual(envelope['expires_at'] - envelope['issued_at'], 120,
                             'challenge TTL must never exceed 120 seconds')
        self.assertLessEqual(envelope['expires_at'], fixture.grant['expires_at'],
                             'challenge TTL must never outlive the enrollment')
        command = fixture.signed_command(rid, record)
        clock.advance(121)
        with self.assertRaises(ValueError) as caught:
            fixture.dispatch(command)
        self.assertIn('response challenge expired', str(caught.exception))
        credit = fixture.credited_anything(rid)
        self.assertEqual(credit['publish_calls'], 0)
        self.assertFalse(credit['response_artifact'])
        self.assertEqual(credit['ack_markers'], [])

    def test_challenge_expiry_is_capped_by_a_sooner_enrollment_expiry(self):
        clock = FrozenClock(1_800_000_000.0)
        fixture = self.new_fixture('shortgrant', clock=clock, grant_expires_in=30)
        rid, _record = fixture.arm()
        envelope = fixture.authority.pending[rid]['envelope']
        self.assertEqual(envelope['expires_at'], fixture.grant['expires_at'])
        self.assertLess(envelope['expires_at'] - envelope['issued_at'], 120)

    # -- transport / principal / liveness --------------------------------
    def test_non_enrolled_kernel_peer_is_refused_before_the_command_is_read(self):
        self.reject(self.fixture.signed_command(self.rid, self.record),
                    peer=SYNTHETIC_UNAPPROVED_PEER,
                    expected_reason='response endpoint requires the enrolled Resident OS principal')

    def test_dead_runner_refuses_an_otherwise_valid_signed_response(self):
        self.reject(self.fixture.signed_command(self.rid, self.record), runner_live=False,
                    expected_reason='Runner is no longer live')

    def test_command_schema_is_exactly_the_response_only_schema(self):
        for bad in ({'command': 'publish-signed'},
                    {'command': 'register'},
                    {'command': 'publish'},
                    {'command': 'publish-signed', 'envelope': {}, 'signature': '00',
                     'raw': '', 'extra': 1}):
            with self.subTest(command_keys=sorted(bad)):
                self.reject(bad, expected_reason='response-only command schema')

    def test_response_endpoint_cannot_register_runner_requests(self):
        """The separate response endpoint never accepts Runner registrations."""
        self.reject({'command': 'register', 'request_id': self.rid,
                     'request_sha256': self.record['request_sha256'], 'context': None,
                     'core_attempt_id': None,
                     'runner_instance_id': self.fixture.instance_id,
                     'operation_id': self.fixture.operation_id},
                    expected_reason='response-only command schema')

    def test_ipc_framing_violations_fail_closed(self):
        """The real bounded, single-newline JSON framer is exercised unchanged."""
        framed = canonical_json_bytes(self.fixture.signed_command(self.rid, self.record)) + b'\n'
        for label, raw in (('no trailing newline', framed[:-1]),
                           ('two newline records', framed + framed),
                           ('embedded newline', framed[:-1].replace(b'"raw"', b'"raw"\n') + b'\n'),
                           ('not json', b'not-json-at-all\n'),
                           ('json array', b'[1,2,3]\n'),
                           ('empty payload', b'')):
            with self.subTest(framing=label):
                self.reject(raw=raw)

    def test_malformed_signature_encodings_fail_closed(self):
        honest = self.fixture.signed_command(self.rid, self.record)
        for label, signature in (('non hex', 'not-hex-at-all'),
                                 ('empty', ''),
                                 ('short', '00' * 63),
                                 ('long', '00' * 65)):
            with self.subTest(signature_encoding=label):
                self.reject({**honest, 'signature': signature})

    def test_signature_from_an_unapproved_key_is_refused(self):
        """A syntactically perfect envelope signed by a rogue key fails closed."""
        self.reject(self.fixture.signed_command(self.rid, self.record,
                                                private_key=self.fixture.trust.rogue_private),
                    expected_reason='signature verification failed')

    # -- durable registration / enrollment consistency --------------------
    def test_changed_durable_registration_is_refused(self):
        """The challenge is bound to the durable registration captured at issue."""
        fixture = self.new_fixture('registration-drift')
        rid, record = fixture.arm()
        command = fixture.signed_command(rid, record)
        fixture.registration_authority.registered[rid]['context'] = {
            'attempt_id': 'arena-injected-late-context'}
        self.assert_rejected_without_credit(fixture, rid, command=command,
                                            expected_reason='durable request registration changed')

    def test_changed_enrollment_during_an_operation_is_refused(self):
        """``current()`` re-loads the enrollment and refuses a changed grant."""
        fixture = self.new_fixture('enrollment-drift')
        rid, record = fixture.arm()
        command = fixture.signed_command(rid, record)
        drifted = dict(fixture.grant)
        drifted['_sha256'] = 'arena-mutated-enrollment-digest'
        response_authorization.load_grant = lambda _path: dict(drifted)
        self.assert_rejected_without_credit(fixture, rid, command=command,
                                            expected_reason='enrollment changed during operation')

    def test_request_outside_the_enrollment_scope_cannot_be_armed(self):
        """``register`` refuses a durable request outside run/session/kind scope."""
        record = self.fixture.publish_request(run_id='arena-run-OUT-OF-SCOPE')
        _rid, registration = self.fixture.register_with_runner(record)
        with self.assertRaises(ValueError) as caught:
            self.fixture.authority.register(record['request_id'], registration,
                                            self.fixture.bridge)
        self.assertIn('request outside signed enrollment scope', str(caught.exception))
        self.assertNotIn(record['request_id'], self.fixture.authority.pending)
        self.assertEqual(self.fixture.published_commands, [])

    def test_a_request_cannot_be_armed_twice(self):
        registration = self.fixture.registration_authority.get(self.rid)
        with self.assertRaises(ValueError) as caught:
            self.fixture.authority.register(self.rid, registration, self.fixture.bridge)
        self.assertIn('request already authorized', str(caught.exception))

    # -- pending disclosure ------------------------------------------------
    def test_pending_lists_only_unconsumed_challenges_with_the_live_epoch(self):
        fixture = self.new_fixture('pending')
        rid, record = fixture.arm()
        first = fixture.signed_command(rid, record)
        listing = fixture.dispatch_raw(canonical_json_bytes({'command': 'pending'}) + b'\n')
        self.assertEqual(listing['publisher_epoch'], fixture.authority.epoch)
        self.assertEqual(len(listing['pending']), 1)
        self.assertEqual(listing['pending'][0]['envelope'],
                         fixture.authority.pending[rid]['envelope'])
        fixture.dispatch(first)
        after = fixture.dispatch_raw(canonical_json_bytes({'command': 'pending'}) + b'\n')
        self.assertEqual(after['pending'], [],
                         'a consumed challenge must no longer be offered for authorization')
        self.assertEqual(fixture.credited_anything(rid)['publish_calls'], 1)

    def test_pending_disclosure_is_refused_to_an_unapproved_peer(self):
        with self.assertRaises(ValueError) as caught:
            self.fixture.dispatch_raw(canonical_json_bytes({'command': 'pending'}) + b'\n',
                                      peer=SYNTHETIC_UNAPPROVED_PEER)
        self.assertIn('enrolled Resident OS principal', str(caught.exception))
        self.assertEqual(self.fixture.published_commands, [])

    # -- fail-closed must not become permanent self-denial -----------------
    def test_a_definite_negative_does_not_permanently_consume_the_challenge(self):
        """A bad signature leaves the challenge usable by a correct attempt.

        This pins the deliberate asymmetry in ``dispatch``: the challenge is
        reserved only AFTER signature verification succeeds, so a definitively
        invalid attempt cannot exhaust a legitimate one, while any attempt that
        reaches the durable publish path stays reserved permanently.
        """
        fixture = self.new_fixture('negative-then-positive')
        rid, record = fixture.arm()
        self.assert_rejected_without_credit(
            fixture, rid,
            command=fixture.signed_command(rid, record,
                                           private_key=fixture.trust.rogue_private),
            expected_reason='signature verification failed')
        self.assertNotIn(rid, fixture.authority.used)
        result = fixture.dispatch(fixture.signed_command(rid, record))
        self.assertIn('resident_authorization_sha256', result)
        self.assertEqual(fixture.credited_anything(rid)['publish_calls'], 1)

    def test_publish_failure_after_verification_never_restores_authority(self):
        """Uncertainty after reservation is permanent: no second attempt."""
        fixture = self.new_fixture('uncertain-publish')
        rid, record = fixture.arm()
        command = fixture.signed_command(rid, record)

        def failing_publish(_command, _peer):
            raise RuntimeError('injected uncertain failure during durable publication')

        with self.assertRaises(RuntimeError):
            fixture.authority.dispatch(FakeConnection(payload=command),
                                       SYNTHETIC_RESIDENT_PEER, fixture.bridge,
                                       fixture.registration_authority,
                                       lambda: True, failing_publish)
        self.assertIn(rid, fixture.authority.used,
                      'reservation must survive an uncertain publish outcome')
        with self.assertRaises(ValueError) as retry:
            fixture.dispatch(command)
        self.assertIn('stale or consumed request challenge', str(retry.exception))
        self.assertFalse(fixture.bridge.responses.path_for(rid).exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
