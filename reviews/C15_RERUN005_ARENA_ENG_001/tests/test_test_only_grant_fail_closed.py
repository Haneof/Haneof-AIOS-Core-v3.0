"""TEST_ONLY enrollment gate: fail-closed BEFORE any response publication.

DEVELOPMENT_ONLY / FORMAL_VALIDATION_NOT_PERFORMED / DO_NOT_MERGE

PM priority case: "Missing/wrong-purpose/expired TEST_ONLY grant fails closed
*before* any response publication; never use actual Window68 grants for these
synthetic developer tests."

Every enrollment here is a synthetic disposable grant signed by a throwaway
Ed25519 issuer key created inside a temporary directory. The real pinned
Operator issuer key, the real Resident private key, the real
``/var/lib/aios-window65/trust`` root and any real Window68 grant are never
read, written, exported or substituted. Three tests explicitly assert that the
real trust anchors are ABSENT from this sandbox, which is the property that
makes those substitutions impossible rather than merely unused.

The real production code under test is ``load_grant``, ``configured_grant``,
``SignedResponseAuthority.__init__``, ``trusted_bytes``, ``key_fingerprint``
and ``verify_signature`` -- all unmodified.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
import unittest
from unittest import mock

from synthetic_fixtures import (SyntheticTrustRoot, canonical_json_bytes,
                                ed25519_sign, generate_ed25519_keypair,
                                make_workdir, response_authorization as ra)

REAL_TRUST_ROOT = Path('/var/lib/aios-window65/trust')
REAL_RESPONSE_ROOT = Path('/run/aios-w66-responses')
ENROLLMENT_ENV = 'AIOS66_TEST_ENROLLMENT'


class RealTrustAnchorsAbsentTests(unittest.TestCase):
    """Prove the pinned Operator facilities do not exist in this sandbox.

    This is the honest basis for every synthetic substitution below: no test in
    this suite can read or reuse a real key, because there is none present.
    """

    def test_pinned_operator_trust_root_is_absent(self):
        self.assertFalse(REAL_TRUST_ROOT.exists(),
                         'the real Window65 Operator trust root must not exist in an '
                         'unprivileged Arena sandbox; if it does, these synthetic '
                         'substitutions are no longer necessary and this suite must be '
                         're-reviewed')
        self.assertEqual(ra.TRUST, REAL_TRUST_ROOT,
                         'the module must still pin the real Operator trust path')

    def test_operator_response_socket_root_is_absent(self):
        self.assertFalse(REAL_RESPONSE_ROOT.exists())

    def test_pinned_constants_are_unchanged_by_this_suite(self):
        self.assertEqual(ra.ISSUER_SHA256,
                         '1124f54a497c9dfa5fcc6e16fb9fc570816fadba6f32016a8b53d5f0243090dd')
        self.assertEqual(ra.RESIDENT_SHA256,
                         '838a1a7d168ac6dd8441c0c8a2deab439a7b775d6583c40618a51f627e6e3b7f')
        self.assertEqual(ra.PURPOSE, 'aios.r005.test.response.sign.v1')
        self.assertEqual(ra.DOMAIN, 'aios.r005.test.response.v1')


class SyntheticGrantGateTests(unittest.TestCase):
    """The full ``load_grant`` predicate chain against a synthetic trust root."""

    def setUp(self):
        self._temp = make_workdir('arena-eng-grant-')
        self.addCleanup(self._temp.cleanup)
        self.trust = SyntheticTrustRoot(self._temp.name).install()
        self.addCleanup(self.trust.restore)
        self.now = int(time.time())

    def accept(self, **overrides) -> dict:
        grant = self.trust.grant(now=self.now, **overrides)
        raw = self.trust.publish(grant)
        loaded = self.trust.load()
        self.assertEqual(loaded['_sha256'], hashlib.sha256(raw).hexdigest())
        return loaded

    def reject(self, expected_reason, *, raw=None, signature=None, revocation=None,
               **overrides):
        grant = self.trust.grant(now=self.now, **overrides)
        self.trust.publish(grant, raw=raw, signature=signature, revocation=revocation)
        with self.assertRaises(Exception) as caught:
            self.trust.load()
        self.assertIn(expected_reason, str(caught.exception),
                      f'unexpected refusal reason: {caught.exception}')
        return caught.exception

    # -- positive control -------------------------------------------------
    def test_valid_synthetic_response_grant_is_accepted(self):
        """Positive control: the rejection matrix below is not vacuously passing."""
        grant = self.accept()
        self.assertEqual(grant['purpose'], ra.PURPOSE)
        self.assertIs(grant['test_only'], True)
        self.assertEqual(grant['resident_uid'], 996)
        self.assertEqual(grant['resident_id'], 'AIOS_RESIDENT_TEST')
        self.assertEqual(grant['resident_key_id'], self.trust.resident_fingerprint)

    # -- MISSING grant ----------------------------------------------------
    def test_missing_grant_file_fails_closed(self):
        with self.assertRaises(FileNotFoundError):
            ra.load_grant('/synthetic-arena/does-not-exist.json')

    def test_configured_grant_is_none_when_the_environment_is_unset(self):
        """No enrollment configured means no signed authority is engaged at all."""
        saved = os.environ.pop(ENROLLMENT_ENV, None)
        if saved is not None:
            self.addCleanup(os.environ.__setitem__, ENROLLMENT_ENV, saved)
        self.assertIsNone(ra.configured_grant())

    def test_real_pinned_trust_root_is_demanded_without_the_synthetic_redirect(self):
        """Removing the redirect makes the real (absent) Operator root mandatory."""
        grant = self.trust.grant(now=self.now)
        self.trust.publish(grant)
        self.trust.restore()          # real trusted_bytes / TRUST / fingerprints
        self.assertFalse(REAL_TRUST_ROOT.exists())
        with self.assertRaises(Exception) as caught:
            ra.load_grant(SyntheticTrustRoot.GRANT_PATH)
        self.assertIsInstance(caught.exception, (FileNotFoundError, OSError, ValueError))

    # -- WRONG PURPOSE / wrong enrollment shape ---------------------------
    def test_wrong_purpose_grant_fails_closed(self):
        """The mechanical.ping purpose can never authorize semantic responses."""
        self.reject('response-purpose TEST_ONLY enrollment required',
                    purpose='aios.r005.test.mechanical.ping.v1')

    def test_non_test_only_grant_fails_closed(self):
        self.reject('response-purpose TEST_ONLY enrollment required', test_only=False)

    def test_wrong_domain_or_version_fails_closed(self):
        self.reject('response-purpose TEST_ONLY enrollment required',
                    domain='aios.r005.other.v1')
        self.reject('response-purpose TEST_ONLY enrollment required', version=2)

    # -- EXPIRED / invalid time window ------------------------------------
    def test_expired_grant_fails_closed(self):
        self.reject('expired or invalid enrollment',
                    issued_at=self.now - 7200, not_before=self.now - 7200,
                    expires_at=self.now - 3600)

    def test_not_yet_valid_grant_fails_closed(self):
        self.reject('expired or invalid enrollment', not_before=self.now + 3600)

    def test_overlong_grant_lifetime_fails_closed(self):
        """TEST_ONLY response grants are bounded to one hour."""
        self.reject('expired or invalid enrollment', expires_at=self.now + 7200)

    def test_non_integer_grant_time_fails_closed(self):
        self.reject('invalid grant time', issued_at=str(self.now))

    # -- identity / key pinning -------------------------------------------
    def test_wrong_resident_identity_fails_closed(self):
        self.reject('unapproved Resident identity', resident_id='AIOS_RESIDENT_PROD')
        self.reject('unapproved Resident identity', resident_uid=1001)
        self.reject('unapproved Resident identity', resident_key_id='c' * 64)

    def test_wrong_issuer_identity_fails_closed(self):
        self.reject('wrong issuer identity', issuer_key_id='d' * 64)

    def test_unpinned_issuing_root_fails_closed(self):
        """A grant verified against a different pinned root is refused."""
        self.trust.publish(self.trust.grant(now=self.now))
        ra.ISSUER_SHA256 = 'f' * 64
        with self.assertRaises(ValueError) as caught:
            self.trust.load()
        self.assertIn('issuing root is not pinned', str(caught.exception))

    def test_resident_public_key_must_equal_the_pinned_trust_copy(self):
        """The grant's embedded key must byte-match the Operator trust copy."""
        grant = self.trust.grant(now=self.now)
        grant['resident_public_key_pem'] = self.trust.rogue_public.decode('ascii')
        self.trust.publish(grant)
        with self.assertRaises(ValueError) as caught:
            self.trust.load()
        self.assertIn('unapproved Resident', str(caught.exception))

    # -- scope bounds ------------------------------------------------------
    def test_invalid_enrollment_or_instance_identity_fails_closed(self):
        self.reject('invalid enrollment identity', enrollment_id='W99-' + '0' * 36)
        self.reject('invalid enrollment identity', enrollment_id='not-an-enrollment')
        self.reject('invalid Resident instance', instance_id='not-hex')

    def test_operation_scope_is_bounded_and_exact(self):
        self.reject('bounded exact operation scope required', operation_ids=[])
        self.reject('bounded exact operation scope required',
                    operation_ids=['b' * 64] * 17)
        self.reject('bounded exact operation scope required',
                    operation_ids=['not-hex'])

    def test_request_kind_scope_is_bounded(self):
        self.reject('invalid request-kind scope', request_kinds=[])
        self.reject('invalid request-kind scope', request_kinds=['mechanical_ping'])

    # -- revocation --------------------------------------------------------
    def test_revoked_enrollment_fails_closed(self):
        grant = self.trust.grant(now=self.now)
        self.reject('revoked enrollment',
                    revocation={'epoch': 7,
                                'revoked_enrollment_ids': [grant['enrollment_id']]})

    def test_revocation_epoch_mismatch_fails_closed(self):
        self.reject('revoked enrollment',
                    revocation={'epoch': 8, 'revoked_enrollment_ids': []})

    # -- canonical form / signature ---------------------------------------
    def test_noncanonical_enrollment_bytes_fail_closed(self):
        grant = self.trust.grant(now=self.now)
        self.reject('noncanonical enrollment', raw=json.dumps(grant, indent=2).encode())

    def test_grant_signed_by_a_non_issuer_key_fails_closed(self):
        grant = self.trust.grant(now=self.now)
        raw = canonical_json_bytes(grant)
        forged = ed25519_sign(self.trust.resident_private, raw,
                              Path(self._temp.name) / 'sign')
        self.reject('signature verification failed', raw=raw, signature=forged)

    def test_signature_over_different_bytes_fails_closed(self):
        """Tampering with the grant after issuance breaks the issuer signature."""
        self.trust.publish(self.trust.grant(now=self.now))
        other = self.trust.grant(now=self.now, expires_at=self.now + 99999)
        detached = ed25519_sign(self.trust.issuer_private, canonical_json_bytes(other),
                                Path(self._temp.name) / 'sign')
        self.reject('signature verification failed', signature=detached)

    def test_reloaded_grant_digest_is_stable(self):
        self.assertEqual(self.accept()['_sha256'], self.accept()['_sha256'])


class ConstructorGateTests(unittest.TestCase):
    """``SignedResponseAuthority.__init__`` is the gate before any publication.

    The real constructor hard-requires ``os.getuid() == 999``. UID999 is
    simulated with a mocked ``os.getuid`` so the real constructor logic can be
    exercised; this is NOT a claim that a real UID999 Runner was started.
    """

    def setUp(self):
        self._temp = make_workdir('arena-eng-ctor-')
        self.addCleanup(self._temp.cleanup)
        self.trust = SyntheticTrustRoot(self._temp.name).install()
        self.addCleanup(self.trust.restore)
        self.now = int(time.time())
        self.operation_id = 'b' * 64
        self.instance_id = 'a' * 64
        saved = os.environ.get(ENROLLMENT_ENV)
        os.environ[ENROLLMENT_ENV] = SyntheticTrustRoot.GRANT_PATH
        self.addCleanup(self._restore_env, saved)

    @staticmethod
    def _restore_env(saved):
        if saved is None:
            os.environ.pop(ENROLLMENT_ENV, None)
        else:
            os.environ[ENROLLMENT_ENV] = saved

    def arm_grant(self, **overrides):
        grant = self.trust.grant(now=self.now, operation_ids=[self.operation_id],
                                 instance_id=self.instance_id, **overrides)
        self.trust.publish(grant)
        return grant

    def test_valid_grant_constructs_an_authority_that_has_authorized_nothing(self):
        self.arm_grant()
        with mock.patch('os.getuid', return_value=999):
            authority = ra.SignedResponseAuthority(self.operation_id, self.instance_id)
        self.addCleanup(authority.close)
        self.assertEqual(authority.pending, {}, 'construction must pre-authorize no request')
        self.assertEqual(authority.used, set())
        self.assertEqual(authority.verified_digests, {})
        self.assertIsNone(authority.server, 'construction must open no endpoint')
        self.assertEqual(len(authority.epoch), 32, 'a fresh Publisher epoch must be generated')

    def test_wrong_operation_scope_is_refused_at_construction(self):
        self.arm_grant()
        with mock.patch('os.getuid', return_value=999):
            with self.assertRaises(ValueError) as caught:
                ra.SignedResponseAuthority('c' * 64, self.instance_id)
        self.assertIn('test Runner operation/instance scope mismatch', str(caught.exception))

    def test_wrong_instance_scope_is_refused_at_construction(self):
        self.arm_grant()
        with mock.patch('os.getuid', return_value=999):
            with self.assertRaises(ValueError) as caught:
                ra.SignedResponseAuthority(self.operation_id, 'd' * 64)
        self.assertIn('test Runner operation/instance scope mismatch', str(caught.exception))

    def test_non_runner_uid_is_refused_at_construction(self):
        """The signed authority is Runner-side; the Resident cannot construct it."""
        self.arm_grant()
        with mock.patch('os.getuid', return_value=996):
            with self.assertRaises(ValueError) as caught:
                ra.SignedResponseAuthority(self.operation_id, self.instance_id)
        self.assertIn('test Runner operation/instance scope mismatch', str(caught.exception))

    def test_rejected_grant_never_reaches_construction(self):
        """A wrong-purpose grant fails closed before any authority exists."""
        self.arm_grant(purpose='aios.r005.test.mechanical.ping.v1')
        with mock.patch('os.getuid', return_value=999):
            with self.assertRaises(ValueError) as caught:
                ra.SignedResponseAuthority(self.operation_id, self.instance_id)
        self.assertIn('response-purpose TEST_ONLY enrollment required', str(caught.exception))

    def test_expired_grant_never_reaches_construction(self):
        self.arm_grant(issued_at=self.now - 7200, not_before=self.now - 7200,
                       expires_at=self.now - 3600)
        with mock.patch('os.getuid', return_value=999):
            with self.assertRaises(ValueError) as caught:
                ra.SignedResponseAuthority(self.operation_id, self.instance_id)
        self.assertIn('expired or invalid enrollment', str(caught.exception))

    def test_missing_enrollment_environment_refuses_construction(self):
        os.environ.pop(ENROLLMENT_ENV, None)
        with mock.patch('os.getuid', return_value=999):
            with self.assertRaises(KeyError):
                ra.SignedResponseAuthority(self.operation_id, self.instance_id)

    def test_endpoint_cannot_be_opened_without_the_operator_response_root(self):
        """Fail closed: no Operator root here means no response endpoint at all."""
        self.arm_grant()
        with mock.patch('os.getuid', return_value=999):
            authority = ra.SignedResponseAuthority(self.operation_id, self.instance_id)
        self.addCleanup(authority.close)
        self.assertFalse(REAL_RESPONSE_ROOT.exists())
        with self.assertRaises((FileNotFoundError, OSError, ValueError)):
            authority.open_endpoint()
        self.assertIsNone(authority.server,
                          'a failed endpoint open must not leave a live listening socket')


class TrustedBytesFailClosedTests(unittest.TestCase):
    """``trusted_bytes`` cannot be satisfied by an unprivileged caller."""

    def setUp(self):
        self._temp = make_workdir('arena-eng-trusted-')
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)

    def test_relative_path_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            ra.trusted_bytes('relative/grant.json')
        self.assertIn('absolute Operator path required', str(caught.exception))

    def test_unprivileged_ancestor_is_refused(self):
        """A world-writable ancestor (any /tmp path here) can never be trusted."""
        target = self.root / 'grant.json'
        target.write_bytes(b'{}')
        self.assertTrue(os.lstat('/tmp').st_mode & 0o022,
                        'this assertion depends on /tmp being world-writable')
        with self.assertRaises(ValueError) as caught:
            ra.trusted_bytes(target)
        self.assertIn('Operator trust ancestor is mutable or not a directory',
                      str(caught.exception))

    def test_ancestor_gate_precedes_file_access_so_there_is_no_existence_oracle(self):
        """An untrusted ancestor is refused before the target is ever opened.

        Consequence: ``trusted_bytes`` cannot be used by an unprivileged caller
        as a file-existence oracle for Operator-owned paths. A missing file and
        a present file under the same untrusted ancestor are indistinguishable.
        """
        absent = self.root / 'absent.json'
        present = self.root / 'present.json'
        present.write_bytes(b'{}')
        self.assertFalse(absent.exists())
        outcomes = {}
        for label, target in (('absent', absent), ('present', present)):
            with self.assertRaises(ValueError) as caught:
                ra.trusted_bytes(target)
            outcomes[label] = str(caught.exception)
        self.assertEqual(outcomes['absent'], outcomes['present'],
                         'refusal must not depend on whether the target exists')
        self.assertIn('Operator trust ancestor is mutable or not a directory',
                      outcomes['absent'])




class CryptoPrimitiveTests(unittest.TestCase):
    """``key_fingerprint`` / ``verify_signature`` with synthetic keys only."""

    def setUp(self):
        self._temp = make_workdir('arena-eng-crypto-')
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.private, self.public = generate_ed25519_keypair(self.root, 'synthetic')
        self.message = canonical_json_bytes({'arena': 'synthetic message'})
        self.signature = ed25519_sign(self.private, self.message, self.root)

    def test_fingerprint_is_a_stable_sha256_hex_digest(self):
        fingerprint = ra.key_fingerprint(self.public)
        self.assertRegex(fingerprint, r'^[0-9a-f]{64}$')
        self.assertEqual(fingerprint, ra.key_fingerprint(self.public),
                         'fingerprinting must be deterministic')

    def test_invalid_public_key_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            ra.key_fingerprint(b'not a pem public key')
        self.assertIn('invalid public key', str(caught.exception))

    def test_valid_signature_verifies(self):
        self.assertEqual(len(self.signature), 64)
        ra.verify_signature(self.public, self.message, self.signature)

    def test_flipped_signature_bit_is_refused(self):
        flipped = bytearray(self.signature)
        flipped[0] ^= 0x01
        with self.assertRaises(ValueError) as caught:
            ra.verify_signature(self.public, self.message, bytes(flipped))
        self.assertIn('signature verification failed', str(caught.exception))

    def test_flipped_message_bit_is_refused(self):
        tampered = self.message.replace(b'synthetic', b'SYNTHETIC')
        self.assertNotEqual(tampered, self.message)
        with self.assertRaises(ValueError) as caught:
            ra.verify_signature(self.public, tampered, self.signature)
        self.assertIn('signature verification failed', str(caught.exception))

    def test_wrong_key_is_refused(self):
        _other_private, other_public = generate_ed25519_keypair(self.root, 'other')
        with self.assertRaises(ValueError) as caught:
            ra.verify_signature(other_public, self.message, self.signature)
        self.assertIn('signature verification failed', str(caught.exception))

    def test_wrong_signature_length_is_refused_before_any_subprocess(self):
        for bad in (b'', b'\x00' * 63, b'\x00' * 65):
            with self.subTest(length=len(bad)):
                with self.assertRaises(ValueError) as caught:
                    ra.verify_signature(self.public, self.message, bad)
                self.assertIn('Ed25519 signature size', str(caught.exception))


if __name__ == '__main__':
    unittest.main(verbosity=2)
