"""Reproduce the unresolved staged-reply/Core-resume boundary, synthetic only.

Exit 2 means the corrective convergence requirement is still BLOCKED, not that
Core regressed. This probe never invokes a provider, capability, or real fixture.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import uuid

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import TurnExecutionInDoubt
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


def turn(session):
    return dict(session_id=session, turn_index=1,
                user_input='SYNTHETIC persistence boundary only',
                occurred_at=datetime(2026, 9, 26, tzinfo=timezone.utc))


def runtime(root, model):
    store = SQLiteWorldStore(root / 'world.sqlite')
    return FusedTurnRuntime(store=store,
        index=WorldSearchIndex(root / 'index.sqlite', store=store), model_handler=model)


def worker(root, session):
    def staged_reply(_):
        # Opaque synthetic transport bytes. This intentionally does not return a
        # ModelDirective: kill after reply staging, before runtime application.
        fd = os.open(root / 'reply.raw', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, b'{ "synthetic_only": true, "reply": "opaque" }\n')
            os.fsync(fd)
        finally:
            os.close(fd)
        fd = os.open(root, os.O_DIRECTORY | os.O_RDONLY)
        os.fsync(fd)
        os.close(fd)
        os.kill(os.getpid(), signal.SIGKILL)
    runtime(root, staged_reply).run_turn(**turn(session))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--worker':
        root = Path(sys.argv[2])
        if not root.is_relative_to('/home/user/c15-persistence-unit-probes'):
            raise RuntimeError('synthetic workspace only')
        if not sys.argv[3].startswith('synthetic-'):
            raise RuntimeError('synthetic identity only')
        worker(root, sys.argv[3])
        raise RuntimeError('kill point was not reached')
    base = Path('/home/user/c15-persistence-unit-probes')
    base.mkdir(exist_ok=True, mode=0o700)
    identity = 'synthetic-core-gap-' + uuid.uuid4().hex
    root = base / identity
    root.mkdir(mode=0o700)
    child = subprocess.run([sys.executable, __file__, '--worker', str(root), identity],
                           capture_output=True, text=True)
    if child.returncode != -signal.SIGKILL:
        print(child.stdout, child.stderr)
        raise RuntimeError(f'kill point not reached: {child.returncode}; state retained at {root}')
    calls = []
    def forbidden(_):
        calls.append('unexpected')
        raise AssertionError('must not redispatch')
    reopened = runtime(root, forbidden)
    status = reopened.inspect_turn_execution(**turn(identity))
    assert status.recovery_disposition == 'in_doubt', status
    ordinary_refused = retry_refused = False
    try:
        reopened.run_turn(**turn(identity))
    except TurnExecutionInDoubt:
        ordinary_refused = True
    try:
        reopened.authorize_turn_retry(**turn(identity),
            evidence='SYNTHETIC exact reply bytes survived; not proof of non-submission')
    except TurnExecutionInDoubt:
        retry_refused = True
    assert ordinary_refused and retry_refused and calls == []
    receipt = dict(status='CORRECTIVE_CONVERGENCE_BLOCKED', synthetic=True,
        root=str(root), killed_returncode=child.returncode,
        disposition=status.recovery_disposition, ordinary_retry_refused=ordinary_refused,
        explicit_retry_refused=retry_refused, redispatches=len(calls),
        reply_sha256=hashlib.sha256((root / 'reply.raw').read_bytes()).hexdigest(),
        note='Expected Core fail-closed behavior; not exactly-once convergence or a Core regression.')
    (root / 'probe-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
    return 2


if __name__ == '__main__':
    sys.exit(main())
