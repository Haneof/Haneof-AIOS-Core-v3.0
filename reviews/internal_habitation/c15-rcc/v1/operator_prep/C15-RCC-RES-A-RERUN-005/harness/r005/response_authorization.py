"""Ephemeral, request-scoped Resident response authorization capabilities."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import os
import stat
from typing import Any, MutableMapping

from .canonical import canonical_json_bytes


def open_resident_terminal() -> int:
    """Require a real controlling TTY for disclosure of Resident capabilities."""
    if not hasattr(os, 'O_NOFOLLOW'):
        raise RuntimeError('Resident authorization requires O_NOFOLLOW terminal open')
    fd = os.open('/dev/tty', os.O_WRONLY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISCHR(info.st_mode) or not os.isatty(fd):
            raise RuntimeError('Resident authorization output is not a controlling terminal')
        return fd
    except BaseException:
        os.close(fd)
        raise


def write_resident_capability(fd: int, token: str, request_id: str, operation_id: str) -> None:
    """Write the one-request token only to the pre-opened controlling TTY."""
    message = (f'\nRESIDENT_PUBLISH_AUTHORIZATION={token}'
               f' REQUEST_ID={request_id} OPERATION_ID={operation_id}\n').encode('ascii')
    offset = 0
    while offset < len(message):
        offset += os.write(fd, message[offset:])


def issue_response_authorization(registry: MutableMapping[str, dict[str, str]], request_id: str,
                                 *, runner_instance_id: str, operation_id: str) -> str:
    """Issue a single-request, single-operation capability in process memory."""
    if request_id in registry:
        raise ValueError('response authorization already issued for this request')
    token = secrets.token_urlsafe(48)
    registry[request_id] = {
        'token': token,
        'runner_instance_id': runner_instance_id,
        'operation_id': operation_id,
    }
    return token


def response_authorization_valid(registry: MutableMapping[str, dict[str, str]],
                                 request_id: str, content: Any, proof: Any, *,
                                 runner_instance_id: str, operation_id: str) -> bool:
    """Check capability scope and proof without consuming the token on failure."""
    capability = registry.get(request_id)
    if (not isinstance(capability, dict)
            or capability.get('runner_instance_id') != runner_instance_id
            or capability.get('operation_id') != operation_id
            or not isinstance(content, dict)
            or content.get('request_id') != request_id):
        return False
    expected = hmac.new(capability['token'].encode(),
                        canonical_json_bytes(content), hashlib.sha256).hexdigest()
    return secrets.compare_digest(str(proof), expected)


def retire_response_authorization(registry: MutableMapping[str, dict[str, str]], request_id: str,
                                  *, runner_instance_id: str, operation_id: str) -> None:
    """Consume only a matching request capability after durable proof publication."""
    capability = registry.get(request_id)
    if (not isinstance(capability, dict)
            or capability.get('runner_instance_id') != runner_instance_id
            or capability.get('operation_id') != operation_id):
        raise ValueError('response authorization binding changed before retirement')
    del registry[request_id]


"""TEST_ONLY Operator-enrolled Ed25519 response authorization.

The host Operator is trusted. No private signing key is loaded here. The
separate response endpoint never accepts Runner registrations.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import subprocess
import tempfile
import time

from .canonical import canonical_json_bytes
from .registration_ipc import peer_credentials, receive_message, send_message

ISSUER_SHA256 = '1124f54a497c9dfa5fcc6e16fb9fc570816fadba6f32016a8b53d5f0243090dd'
RESIDENT_SHA256 = '838a1a7d168ac6dd8441c0c8a2deab439a7b775d6583c40618a51f627e6e3b7f'
TRUST = Path('/var/lib/aios-window65/trust')
PURPOSE = 'aios.r005.test.response.sign.v1'
DOMAIN = 'aios.r005.test.response.v1'

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def trusted_bytes(path):
    path = Path(path)
    require(path.is_absolute(), 'absolute Operator path required')
    for parent in reversed(path.parents):
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
                'Operator trust ancestor is mutable or not a directory')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022
                and info.st_size <= 65536, 'Operator record is not protected')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            return stream.read(65537)
    finally:
        os.close(fd)

def key_fingerprint(pem):
    result = subprocess.run(['/usr/bin/openssl', 'pkey', '-pubin', '-outform', 'DER'],
        input=pem, capture_output=True, timeout=5, close_fds=True)
    require(result.returncode == 0, 'invalid public key')
    return hashlib.sha256(result.stdout).hexdigest()

def verify_signature(pem, message, signature):
    require(len(signature) == 64, 'Ed25519 signature size')
    with tempfile.TemporaryDirectory(prefix='aios66-verify-') as directory:
        root = Path(directory)
        for name, data in [('key.pem', pem), ('message', message), ('signature', signature)]:
            file = root / name
            with file.open('xb') as stream:
                stream.write(data)
            file.chmod(0o600)
        result = subprocess.run(['/usr/bin/openssl', 'pkeyutl', '-verify', '-rawin',
            '-pubin', '-inkey', str(root/'key.pem'), '-in', str(root/'message'),
            '-sigfile', str(root/'signature')], capture_output=True, timeout=5, close_fds=True)
    require(result.returncode == 0, 'signature verification failed')

def load_grant(path):
    raw = trusted_bytes(path)
    grant = json.loads(raw)
    require(canonical_json_bytes(grant) == raw, 'noncanonical enrollment')
    issuer = trusted_bytes(TRUST/'issuer.pub')
    require(key_fingerprint(issuer) == ISSUER_SHA256, 'issuing root is not pinned')
    verify_signature(issuer, raw, trusted_bytes(Path(path).with_suffix('.sig')))
    require(grant.get('domain') == 'aios.r005.test.enrollment.v1' and
            type(grant.get('version')) is int and grant['version'] == 1 and
            grant.get('purpose') == PURPOSE and grant.get('test_only') is True,
            'response-purpose TEST_ONLY enrollment required')
    require(grant.get('issuer_key_id') == ISSUER_SHA256, 'wrong issuer identity')
    require(grant.get('resident_id') == 'AIOS_RESIDENT_TEST' and
            grant.get('resident_uid') == 996 and grant.get('resident_key_id') == RESIDENT_SHA256,
            'unapproved Resident identity')
    public = grant['resident_public_key_pem'].encode('ascii')
    require(key_fingerprint(public) == RESIDENT_SHA256 and
            public == trusted_bytes(TRUST/'resident.pub'), 'unapproved Resident public key')
    now = time.time()
    require(all(type(grant.get(k)) is int for k in ('issued_at','not_before','expires_at')),
            'invalid grant time')
    require(grant['issued_at'] <= grant['not_before'] <= now < grant['expires_at'] and
            0 < grant['expires_at'] - grant['issued_at'] <= 3600, 'expired or invalid enrollment')
    require(re.fullmatch(r'W66-[0-9a-f-]{36}', grant['enrollment_id']) is not None,
            'invalid enrollment identity')
    require(re.fullmatch(r'[0-9a-f]{64}', grant['instance_id']) is not None,
            'invalid Resident instance')
    require(isinstance(grant['operation_ids'], list) and 0 < len(grant['operation_ids']) <= 16 and
            all(re.fullmatch(r'[0-9a-f]{64}', value) for value in grant['operation_ids']),
            'bounded exact operation scope required')
    require(isinstance(grant['request_kinds'], list) and bool(grant['request_kinds']) and
            set(grant['request_kinds']) <= {'model_directive','round_summary','dimension_summary'},
            'invalid request-kind scope')
    require(all(type(grant.get(k)) is str and grant[k] for k in ('run_id','session_id')),
            'enrollment run/session scope required')
    revocation = json.loads(trusted_bytes(grant['revocation']['file']))
    require(revocation['epoch'] == grant['revocation']['epoch'] and
            grant['enrollment_id'] not in revocation['revoked_enrollment_ids'], 'revoked enrollment')
    grant['_sha256'] = hashlib.sha256(raw).hexdigest()
    return grant

def configured_grant():
    path = os.environ.get('AIOS66_TEST_ENROLLMENT')
    return load_grant(path) if path else None

class SignedResponseAuthority:
    def __init__(self, operation_id, instance_id):
        self.path = os.environ['AIOS66_TEST_ENROLLMENT']
        self.grant = load_grant(self.path)
        require(os.getuid() == 999 and operation_id in self.grant['operation_ids'] and
                instance_id == self.grant['instance_id'], 'test Runner operation/instance scope mismatch')
        self.operation_id = operation_id
        self.instance_id = instance_id
        self.epoch = secrets.token_hex(16)
        self.pending = {}
        self.used = set()
        self.verified_digests = {}
        self.server = None

    def current(self):
        grant = load_grant(self.path)
        require(grant['_sha256'] == self.grant['_sha256'], 'enrollment changed during operation')
        return grant

    def open_endpoint(self):
        parent = Path('/run/aios-w66-responses')
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and
                stat.S_IMODE(info.st_mode) == 0o755, 'Operator response root required')
        directory = parent / self.grant['enrollment_id']
        info = directory.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 999 and info.st_gid == 985 and
                stat.S_IMODE(info.st_mode) == 0o2750, 'restricted response directory required')
        self.socket_path = directory / (self.epoch + '.sock')
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(self.socket_path))
        os.chmod(self.socket_path, 0o660)
        self.server.listen(8)
        self.bound = self.socket_path.lstat()
        require(self.bound.st_uid == 999 and self.bound.st_gid == 985, 'response socket ownership')
        return str(self.socket_path)

    def register(self, rid, registration, bridge):
        grant = self.current()
        request = bridge.requests.payload(rid)
        identity = request['body']['identity']
        require(identity['run_id'] == grant['run_id'] and identity['session_id'] == grant['session_id']
                and request['kind'] in grant['request_kinds'], 'request outside signed enrollment scope')
        require(rid not in self.pending and rid not in self.used, 'request already authorized')
        self.pending[rid] = {'request': request, 'envelope': {
            'domain': DOMAIN, 'version': 1, 'purpose': PURPOSE,
            'enrollment_id': grant['enrollment_id'], 'enrollment_sha256': grant['_sha256'],
            'resident_id': grant['resident_id'], 'resident_key_id': grant['resident_key_id'],
            'run_id': grant['run_id'], 'session_id': grant['session_id'],
            'instance_id': self.instance_id, 'operation_id': self.operation_id,
            'request_id': rid, 'request_sha256': registration['sha256'],
            'request_kind': request['kind'], 'core_attempt_id': registration['core_attempt_id'],
            'context': registration['context'],
            'provenance': request['body'].get('provenance_binding'),
            'publisher_epoch': self.epoch, 'publisher_challenge': secrets.token_hex(32),
            'issued_at': int(time.time()), 'expires_at': min(int(time.time()) + 120, grant['expires_at'])}}

    def dispatch(self, connection, peer, bridge, registration_authority, runner_live, publish):
        require(peer[1:] == (996, 983), 'response endpoint requires the enrolled Resident OS principal')
        require(runner_live(), 'Runner is no longer live')
        grant = self.current()
        command = receive_message(connection)
        if command == {'command': 'pending'}:
            return {'publisher_epoch': self.epoch, 'pending': [v for k,v in self.pending.items() if k not in self.used]}
        require(set(command) == {'command','envelope','signature','raw'} and
                command['command'] == 'publish-signed', 'response-only command schema')
        envelope = command['envelope']
        rid = envelope['request_id']
        require(rid in self.pending and rid not in self.used, 'stale or consumed request challenge')
        expected = self.pending[rid]['envelope']
        raw = base64.b64decode(command['raw'], validate=True)
        require(len(raw) <= 1048576, 'response too large')
        require(envelope == {**expected, 'response_sha256': hashlib.sha256(raw).hexdigest()},
                'signed envelope/request/operation/context/bytes mismatch')
        require(time.time() < envelope['expires_at'], 'response challenge expired')
        registration = registration_authority.get(rid)
        require(bridge.request_sha256(rid) == expected['request_sha256'] == registration['sha256'] and
                registration['core_attempt_id'] == expected['core_attempt_id'] and
                registration['context'] == expected['context'], 'durable request registration changed')
        verify_signature(grant['resident_public_key_pem'].encode('ascii'),
            canonical_json_bytes(envelope), bytes.fromhex(command['signature']))
        # Reserve before any durable side effect. Uncertainty never restores authority.
        self.used.add(rid)
        self.verified_digests[rid] = hashlib.sha256(canonical_json_bytes(envelope)).hexdigest()
        result = publish({'command':'publish','request_id':rid,
            'request_sha256':expected['request_sha256'],'raw':command['raw'],'authorization_proof':''}, peer)
        return {**result, 'resident_authorization_sha256': hashlib.sha256(canonical_json_bytes(envelope)).hexdigest()}

    def close(self):
        if self.server is not None:
            self.server.close()
            try:
                current = self.socket_path.lstat()
                if (current.st_dev,current.st_ino) == (self.bound.st_dev,self.bound.st_ino):
                    self.socket_path.unlink()
            except FileNotFoundError:
                pass
