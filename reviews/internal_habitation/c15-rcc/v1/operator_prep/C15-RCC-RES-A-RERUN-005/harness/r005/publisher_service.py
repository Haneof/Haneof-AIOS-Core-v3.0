"""Byte-only external publisher with Runner-authenticated registration.

This authority is subprocess-only. Registration is accepted only from the
actual live parent Runner identified by Linux SO_PEERCRED and a pidfd/lifetime
binding. External response publication remains a separate, Resident-authorized
HMAC operation; it cannot register requests or choose Core signing context.
Importing this module defines helpers only; signing authority exists only when
``main`` runs in its separately launched process.
"""
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import select
import socket
import stat
import sys
import time

from r005.atomic import atomic_write_bytes
from r005.canonical import canonical_json_bytes
from r005.bridge import ExchangeBridge
from r005.schema import parse_model_directive
from r005.payload import parse
from r005.registration_ipc import peer_credentials, receive_message, send_message
from r005.registration import (RegistrationError, RunnerRegistrationAuthority,
    process_start_time)
from r005.response_authorization import (issue_response_authorization,
    open_resident_terminal, response_authorization_valid,
    retire_response_authorization, write_resident_capability)
from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.late_return import late_return_message


def prime(bits):
    while True:
        n = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if any(n % p == 0 for p in (3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41)):
            continue
        d = n - 1
        s = 0
        while d % 2 == 0:
            d //= 2
            s += 1
        valid = True
        for _ in range(32):
            a = secrets.randbelow(n - 3) + 2
            x = pow(a, d, n)
            if x in (1, n - 1):
                continue
            for _ in range(s - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                valid = False
                break
        if valid:
            return n


def main():
    if len(sys.argv) != 8:
        raise SystemExit('publisher_service requires exchange, socket, Runner identity, instance, operation, parent fd')
    root = Path(sys.argv[1])
    socket_path = Path(sys.argv[2])
    runner_pid = int(sys.argv[3])
    runner_start_time = sys.argv[4]
    runner_instance_id = sys.argv[5]
    operation_id = sys.argv[6]
    parent_fd = int(sys.argv[7])
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError('exchange root must be a real directory')
    from r005.checks import loaded_modules
    source_repo = Path(os.environ['AIOS53_SOURCE_REPO'])
    harness_root = Path(os.environ['AIOS53_LAUNCH']).parent
    module_identity = loaded_modules(source_repo, harness_root)
    atomic_write_bytes(root / 'publisher-module-identity.json',
                       canonical_json_bytes(module_identity))
    if os.getppid() != runner_pid:
        raise RuntimeError('Publisher must be a direct child of the Runner')
    if process_start_time(runner_pid) != runner_start_time:
        raise RuntimeError('Runner process-start identity mismatch')
    if not hasattr(os, 'pidfd_open'):
        raise RuntimeError('Linux pidfd support is required; no PID-only fallback is permitted')
    runner_pidfd = os.pidfd_open(runner_pid, 0)
    runner_stat = os.stat(f'/proc/{runner_pid}')
    runner_uid = runner_stat.st_uid
    runner_gid = runner_stat.st_gid
    if runner_uid != os.getuid() or runner_gid != os.getgid():
        os.close(runner_pidfd)
        raise RuntimeError('Publisher and Runner credentials differ')

    parent_lifetime = select.poll()
    parent_lifetime.register(parent_fd, select.POLLHUP | select.POLLERR)
    runner_lifetime = select.poll()
    runner_lifetime.register(runner_pidfd, select.POLLIN | select.POLLHUP | select.POLLERR)

    signed = None
    if os.environ.get('AIOS66_TEST_ENROLLMENT'):
        from r005.response_authorization import SignedResponseAuthority
        signed = SignedResponseAuthority(operation_id, runner_instance_id)
    resident_tty_fd = None if signed is not None else open_resident_terminal()
    p = q = 0
    n = 0
    e = 65537
    while n.bit_length() != 2048 or p == q or math.gcd(e, (p - 1) * (q - 1)) != 1:
        p = prime(1024)
        q = prime(1024)
        n = p * q
    d = pow(e, -1, (p - 1) * (q - 1))
    del p, q
    key_id = 'resident-publisher-' + secrets.token_hex(12)
    public = {'key_id': key_id, 'algorithm': 'rsa-pkcs1v15-sha256',
              'modulus_hex': format(n, 'x'), 'public_exponent': e}
    atomic_write_bytes(root / 'publisher-public.json', canonical_json_bytes(public))

    socket_dir = socket_path.parent
    directory_stat = os.lstat(socket_dir)
    if not stat.S_ISDIR(directory_stat.st_mode) or stat.S_ISLNK(directory_stat.st_mode):
        raise RuntimeError('private Publisher socket directory is not a real directory')
    if stat.S_IMODE(directory_stat.st_mode) != 0o700:
        raise RuntimeError('private Publisher socket directory mode must be 0700')
    if os.path.lexists(socket_path):
        raise RuntimeError('Publisher socket path already exists')
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.settimeout(0.2)
    server.bind(str(socket_path))
    os.chmod(socket_path, 0o600)
    server.listen(32)
    bound = os.lstat(socket_path)
    if not stat.S_ISSOCK(bound.st_mode) or stat.S_ISLNK(bound.st_mode):
        server.close()
        raise RuntimeError('bound Publisher endpoint is not a Unix socket')

    bridge = ExchangeBridge(root)

    def runner_is_live():
        if parent_lifetime.poll(0) or runner_lifetime.poll(0):
            return False
        if os.getppid() != runner_pid:
            return False
        try:
            return process_start_time(runner_pid) == runner_start_time
        except (OSError, RuntimeError):
            return False

    registration_authority = RunnerRegistrationAuthority(
        runner_pid=runner_pid, runner_uid=runner_uid, runner_gid=runner_gid,
        runner_start_time=runner_start_time, runner_instance_id=runner_instance_id,
        operation_id=operation_id, key_id=key_id, runner_alive=runner_is_live)
    # One ephemeral response capability per kernel-authenticated registration.
    # It is intentionally never returned over the Runner registration RPC or
    # written to the exchange tree, and it dies with this one-operation process.
    authorization_by_request = {}
    signed_server = None
    if signed is not None:
        endpoint = signed.open_endpoint()
        signed_server = signed.server
        atomic_write_bytes(root / 'signed-endpoint.json', canonical_json_bytes({
            'socket': endpoint, 'publisher_pid': os.getpid(),
            'publisher_start_time': process_start_time(os.getpid()),
            'publisher_epoch': signed.epoch}))

    def dispatch(connection, peer, *, resident_verified=False, signed_command=None):
        peer_pid, peer_uid, peer_gid = peer
        if not resident_verified and (peer_uid != runner_uid or peer_gid != runner_gid):
            raise ValueError('IPC peer credentials do not match the local session')
        command = signed_command if resident_verified else receive_message(connection)
        kind = command.get('command')
        if kind == 'register':
            if resident_verified:
                raise ValueError('response endpoint cannot register Runner requests')
            rid, _registration = registration_authority.register(peer, command, bridge)
            if signed is not None:
                signed.register(rid, _registration, bridge)
            else:
                token = issue_response_authorization(
                    authorization_by_request, rid,
                    runner_instance_id=runner_instance_id, operation_id=operation_id)
                write_resident_capability(resident_tty_fd, token, rid, operation_id)
            return {'registered': rid, 'publisher_pid': os.getpid(),
                    'runner_instance_id': runner_instance_id,
                    'operation_id': operation_id}
        if kind == 'publish':
            if signed is not None and not resident_verified:
                raise ValueError('signed mode requires response-only Resident endpoint')
            if peer_pid == runner_pid:
                raise ValueError('Runner registration authority cannot publish Resident responses')
            required = {'command', 'request_id', 'request_sha256', 'raw', 'authorization_proof'}
            if set(command) != required:
                raise ValueError('publish command schema mismatch')
            if not runner_is_live():
                raise ValueError('Runner process lifetime ended')
            content = {key: command[key] for key in ('request_id', 'request_sha256', 'raw')}
            rid = command['request_id']
            if not resident_verified and not response_authorization_valid(
                    authorization_by_request, rid, content, command.get('authorization_proof', ''),
                    runner_instance_id=runner_instance_id, operation_id=operation_id):
                raise ValueError('external Resident authorization required for this request/operation')
            registration = registration_authority.get(rid)
            if command['request_sha256'] != registration['sha256']:
                raise ValueError('request digest mismatch')
            raw = base64.b64decode(command['raw'], validate=True)
            request = bridge.requests.payload(rid)
            if bridge.request_sha256(rid) != registration['sha256']:
                raise ValueError('durable request identity changed after registration')
            directive = parse(request['kind'], raw)
            if request['kind'] == 'model_directive':
                binding = request['body']['provenance_binding']
                if directive.provenance is None or {
                    key: getattr(directive.provenance, key) for key in binding
                } != binding:
                    raise ValueError('external response provenance mismatch')
            result = bridge.responses.publish_bytes(request_id=rid, response_bytes=raw)
            proof_path = root / 'proofs' / f'{rid}.json'
            if proof_path.exists():
                proof = json.loads(proof_path.read_bytes())
                if proof['response_sha256'] != hashlib.sha256(raw).hexdigest():
                    raise ValueError('conflicting proof replay')
            else:
                proof = {
                    'request_id': rid,
                    'request_sha256': registration['sha256'],
                    'response_sha256': hashlib.sha256(raw).hexdigest(),
                    'publisher_pid': os.getpid(),
                    'runner_pid': runner_pid,
                    'runner_instance_id': runner_instance_id,
                    'operation_id': operation_id,
                    'core_attempt_id': registration['core_attempt_id'],
                    'core_proof': None,
                    **({'resident_authorization_sha256': signed.verified_digests[rid]}
                       if signed is not None else {}),
                }
                scope = registration['context']
                if scope is not None:
                    if directive.provenance is None:
                        raise ValueError('background return requires external provenance')
                    payload = encode_model_directive(directive)
                    fingerprint = hashlib.sha256(payload.encode()).hexdigest()
                    fields = {**scope,
                        'provider': directive.provenance.provider,
                        'model': directive.provenance.model,
                        'provider_request_id': directive.provenance.request_id,
                        'response_fingerprint': fingerprint,
                        'payload_sha256': fingerprint}
                    proof['core_proof'] = sign(late_return_message(**fields))
                message = canonical_json_bytes({key: proof[key] for key in (
                    'request_id', 'request_sha256', 'response_sha256')})
                proof['exchange_proof'] = sign(message)
                atomic_write_bytes(proof_path, canonical_json_bytes(proof))
            result.update({'proof': str(proof_path), 'publisher_pid': os.getpid(),
                           'operation_id': operation_id,
                           'runner_instance_id': runner_instance_id})
            if signed is None:
                retire_response_authorization(
                    authorization_by_request, rid,
                    runner_instance_id=runner_instance_id, operation_id=operation_id)
            return result
        raise ValueError('unsupported publisher command')

    def sign(message):
        info = bytes.fromhex('3031300d060960864801650304020105000420') + hashlib.sha256(message).digest()
        encoded = b'\x00\x01' + b'\xff' * (256 - len(info) - 3) + b'\x00' + info
        signature = pow(int.from_bytes(encoded, 'big'), d, n).to_bytes(256, 'big').hex()
        return 'bglate_rsa_v1:' + key_id + ':' + signature

    try:
        while runner_is_live():
            try:
                listeners = [server] + ([signed_server] if signed_server is not None else [])
                readable, _, _ = select.select(listeners, [], [], 0.2)
                if not readable:
                    continue
                listener = readable[0]
                connection, _ = listener.accept()
            except TimeoutError:
                continue
            with connection:
                connection.settimeout(5.0)
                try:
                    peer = peer_credentials(connection)
                    if listener is signed_server:
                        result = signed.dispatch(connection, peer, bridge, registration_authority,
                            runner_is_live, lambda command, peer: dispatch(connection, peer,
                                resident_verified=True, signed_command=command))
                    else:
                        result = dispatch(connection, peer)
                    send_message(connection, {'ok': True, 'result': result})
                except Exception as exc:
                    try:
                        send_message(connection, {'ok': False, 'error': str(exc)})
                    except Exception:
                        pass
    finally:
        server.close()
        try:
            current = os.lstat(socket_path)
            if (stat.S_ISSOCK(current.st_mode)
                    and (current.st_dev, current.st_ino) == (bound.st_dev, bound.st_ino)):
                socket_path.unlink(missing_ok=True)
        except FileNotFoundError:
            pass
        os.close(parent_fd)
        os.close(runner_pidfd)
        if resident_tty_fd is not None:
            os.close(resident_tty_fd)
        if signed is not None:
            signed.close()


if __name__ == '__main__':
    main()
