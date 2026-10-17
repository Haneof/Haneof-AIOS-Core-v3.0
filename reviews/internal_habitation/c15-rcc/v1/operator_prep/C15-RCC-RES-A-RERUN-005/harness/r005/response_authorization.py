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
