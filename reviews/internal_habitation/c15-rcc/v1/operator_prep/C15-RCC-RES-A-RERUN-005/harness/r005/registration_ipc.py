"""Length-bounded AF_UNIX IPC with kernel peer-credential checks.

The socket is transport only. Registration authorization is the Publisher's
SO_PEERCRED + pidfd/lifetime decision; JSON identity fields are never trusted.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import struct

MAX_MESSAGE_BYTES = 1024 * 1024


class RegistrationIPCError(RuntimeError):
    pass


def peer_credentials(connection):
    if not hasattr(socket, 'SO_PEERCRED'):
        raise RegistrationIPCError('kernel SO_PEERCRED is required')
    raw = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
    if len(raw) != struct.calcsize('3i'):
        raise RegistrationIPCError('kernel peer credentials are truncated')
    pid, uid, gid = struct.unpack('3i', raw)
    if pid <= 0 or uid < 0 or gid < 0:
        raise RegistrationIPCError('kernel peer credentials are invalid')
    return pid, uid, gid


def require_runner_peer(peer, *, pid, uid, gid):
    if not isinstance(peer, tuple) or len(peer) != 3:
        raise RegistrationIPCError('kernel peer credential tuple is invalid')
    if peer != (int(pid), int(uid), int(gid)):
        raise RegistrationIPCError('only the exact live Runner kernel identity may register')


def receive_message(connection):
    chunks = []
    size = 0
    while True:
        chunk = connection.recv(min(65536, MAX_MESSAGE_BYTES + 1 - size))
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_MESSAGE_BYTES:
            raise RegistrationIPCError('IPC message exceeds size limit')
        chunks.append(chunk)
        if b'\n' in chunk:
            break
    raw = b''.join(chunks)
    if not raw.endswith(b'\n') or raw.count(b'\n') != 1:
        raise RegistrationIPCError('IPC requires exactly one newline-terminated JSON object')
    try:
        value = json.loads(raw[:-1])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistrationIPCError('IPC message is not valid JSON') from exc
    if not isinstance(value, dict):
        raise RegistrationIPCError('IPC message must be a JSON object')
    return value


def send_message(connection, value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8') + b'\n'
    if len(raw) > MAX_MESSAGE_BYTES:
        raise RegistrationIPCError('IPC response exceeds size limit')
    connection.sendall(raw)


def _proc_start_time(pid):
    raw = Path(f'/proc/{int(pid)}/stat').read_text(encoding='ascii')
    end = raw.rfind(')')
    if end < 0:
        raise RegistrationIPCError('cannot read Publisher process identity')
    fields = raw[end + 1:].split()
    if len(fields) <= 19:
        raise RegistrationIPCError('Publisher process identity is truncated')
    return fields[19]


def rpc(socket_path, command, *, expected_server_pid=None,
        expected_server_start_time=None, timeout=30.0):
    if expected_server_pid is None or expected_server_start_time is None:
        raise RegistrationIPCError('Publisher PID and process-start identity are both required')
    if not isinstance(command, dict) or 'caller_pid' in command:
        raise RegistrationIPCError('self-declared caller identity is forbidden')
    payload = json.dumps(command, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8') + b'\n'
    if len(payload) > MAX_MESSAGE_BYTES:
        raise RegistrationIPCError('IPC command exceeds size limit')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        connection.connect(str(socket_path))
        server_pid, server_uid, _ = peer_credentials(connection)
        if server_pid != int(expected_server_pid):
            raise RegistrationIPCError(
                f'publisher socket identity mismatch: expected pid {expected_server_pid}, observed {server_pid}'
            )
        if _proc_start_time(server_pid) != str(expected_server_start_time):
            raise RegistrationIPCError('publisher socket PID was reused or process identity changed')
        if server_uid != os.getuid():
            raise RegistrationIPCError('publisher socket UID mismatch')
        connection.sendall(payload)
        connection.shutdown(socket.SHUT_WR)
        result = receive_message(connection)
    if result.get('ok') is not True:
        raise RegistrationIPCError(str(result.get('error', 'publisher IPC rejected request')))
    if not isinstance(result.get('result'), dict):
        raise RegistrationIPCError('publisher returned an invalid result envelope')
    return result['result']
