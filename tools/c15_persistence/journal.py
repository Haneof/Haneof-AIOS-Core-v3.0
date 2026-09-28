"""Fail-closed, byte-preserving synthetic relay journal.

This is NOT a production recovery adapter. In particular, recording APPLYING
before returning a reply cannot atomically commit a Core effect. An interrupted
APPLYING row remains IN_DOUBT; callers must not retry it. The synthetic-only gate
is intentional until the frozen runtime integration has a mechanical proof.

All checkpoint artifacts and request/reply bytes live in one SQLite transaction
(domain bytes are opaque). No callbacks, model choices, replay, or fixture reads.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import stat
from typing import Iterator, Mapping

WORKSPACE = Path('/home/user')
EXCLUDED = frozenset({'.arena', '.cache', '.local', '.mypy_cache', '.next',
    '.nox', '.npm', '.nuxt', '.output', '.parcel-cache', '.pytest_cache',
    '.ruff_cache', '.svelte-kit', '.tox', '.turbo', '.venv', '.vite',
    '__pycache__', 'build', 'coverage', 'dist', 'node_modules', 'out', 'target',
    '.git'})
REQUIRED = frozenset({'runtime/world.sqlite', 'runtime/index.sqlite',
    'runtime/release_state.json', 'current-event.json',
    'binding/current-event-binding.json', 'evidence/projection.json',
    'evidence/failures.jsonl', 'mailbox/archive.jsonl'})
META = frozenset({'cursor', 'event_id', 'round', 'request_id', 'nonce',
    'request_digest', 'binding_digest'})


class PersistenceError(RuntimeError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise PersistenceError(reason)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False).encode('utf-8')


def durable_path(root: Path) -> Path:
    """Validate this platform's workspace snapshot path, not just /tmp spelling.

    This checks the declared platform contract; it does NOT prove that a live
    platform snapshot has occurred. Reattachment needs a separate external test.
    """
    root = root.absolute()
    require(root == root.resolve(), 'symlink/non-canonical backend path')
    require(root.is_relative_to(WORKSPACE) and root != WORKSPACE,
            'backend must be a private child of /home/user')
    require(not (set(root.relative_to(WORKSPACE).parts) & EXCLUDED),
            'backend path excluded from platform persistence')
    # Longest matching Linux mount entry; nested tmpfs under /home/user rejected.
    mounts = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        fields = line.split()
        target = Path(fields[4].replace('\\040', ' ').replace('\\134', '\\'))
        if root.is_relative_to(target):
            mounts.append((len(target.parts), fields[fields.index('-') + 1]))
    require(bool(mounts), 'cannot determine backing filesystem')
    require(max(mounts)[1] not in {'tmpfs', 'ramfs'}, 'ephemeral backing filesystem')
    return root


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def synthetic_identity(value: str) -> None:
    require(isinstance(value, str) and value.startswith('synthetic-')
            and len(value) > len('synthetic-'), 'only synthetic identities permitted')


class Journal:
    def __init__(self, root: Path, *, run_id: str, session_id: str,
                 create: bool = False):
        synthetic_identity(run_id)
        synthetic_identity(session_id)
        self.root = durable_path(root)
        self.path = self.root / 'journal.sqlite'
        self.identity = (run_id, session_id)
        if create:
            require(self.root.parent.is_dir(), 'backend parent must already exist')
            self.root.mkdir(mode=0o700)  # exclusive; never silently adopt a run
            fsync_dir(self.root.parent)
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            with self._connect() as db:
                db.executescript('''
                    CREATE TABLE identity(run TEXT NOT NULL, session TEXT NOT NULL);
                    CREATE TABLE checkpoints(
                        id INTEGER PRIMARY KEY, manifest BLOB NOT NULL,
                        digest TEXT NOT NULL);
                    CREATE TABLE artifacts(
                        checkpoint INTEGER NOT NULL REFERENCES checkpoints(id),
                        name TEXT NOT NULL, body BLOB NOT NULL, sha TEXT NOT NULL,
                        PRIMARY KEY(checkpoint,name));
                    CREATE TABLE relay(
                        request_id TEXT PRIMARY KEY, metadata BLOB NOT NULL,
                        checkpoint INTEGER NOT NULL REFERENCES checkpoints(id),
                        request BLOB NOT NULL, request_sha TEXT NOT NULL,
                        state TEXT NOT NULL CHECK(state IN
                          ('staged','exposed','reply-staged','applying','applied')),
                        reply BLOB, reply_sha TEXT, receipt BLOB);
                    CREATE TABLE audit(
                        id INTEGER PRIMARY KEY, request_id TEXT NOT NULL,
                        state TEXT NOT NULL);
                ''')
                db.execute('INSERT INTO identity VALUES (?,?)', self.identity)
            fsync_dir(self.root)
        require(self.path.is_file() and not self.path.is_symlink(), 'journal missing')
        require(stat.S_IMODE(self.root.stat().st_mode) == 0o700,
                'backend directory must be private mode 0700')
        require(stat.S_IMODE(self.path.stat().st_mode) == 0o600,
                'journal must be private mode 0600')
        with self._connect() as db:
            require(db.execute('PRAGMA quick_check').fetchall() == [('ok',)],
                    'journal corruption')
            require(db.execute('SELECT * FROM identity').fetchall() == [self.identity],
                    'wrong run/session identity')

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # mode=rw prevents missing-state reconstruction on restart.
        db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=10)
        try:
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('PRAGMA synchronous=EXTRA')
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def checkpoint(self, artifacts: Mapping[str, bytes]) -> int:
        """Persist a caller-prepared coherent bundle, NOT a live-directory copy.

        World/index must come from a quiesced writer or SQLite backup; this
        prototype does not certify how the caller acquired those bytes.
        """
        require(REQUIRED <= artifacts.keys(), 'missing required evidence')
        for name, body in artifacts.items():
            p = PurePosixPath(name)
            require(not p.is_absolute() and '..' not in p.parts
                    and str(p) == name and name != '.', 'unsafe artifact name')
            require(type(body) is bytes, 'artifact must be exact bytes')
        manifest = canonical({name: digest(body) for name, body in artifacts.items()})
        with self._connect() as db:
            cur = db.execute('INSERT INTO checkpoints(manifest,digest) VALUES (?,?)',
                             (manifest, digest(manifest)))
            cid = cur.lastrowid
            db.executemany('INSERT INTO artifacts VALUES (?,?,?,?)',
                [(cid, name, body, digest(body)) for name, body in artifacts.items()])
        return int(cid)

    @staticmethod
    def _bundle(db: sqlite3.Connection, cid: int) -> dict[str, bytes]:
        row = db.execute('SELECT manifest,digest FROM checkpoints WHERE id=?',
                         (cid,)).fetchone()
        require(row is not None, 'checkpoint missing')
        manifest, sha = row
        require(digest(manifest) == sha, 'checkpoint manifest corruption')
        rows = db.execute('SELECT name,body,sha FROM artifacts WHERE checkpoint=?',
                          (cid,)).fetchall()
        require(all(digest(body) == sha for _, body, sha in rows), 'artifact corruption')
        require(canonical({name: sha for name, _, sha in rows}) == manifest,
                'checkpoint artifact set mismatch')
        require(REQUIRED <= {name for name, _, _ in rows}, 'required evidence missing')
        return {name: body for name, body, _ in rows}

    def recover_checkpoint(self, cid: int) -> dict[str, bytes]:
        with self._connect() as db:
            return self._bundle(db, cid)

    def stage(self, metadata: dict, request: bytes, checkpoint: int) -> None:
        require(set(metadata) == META, 'incomplete/unexpected relay metadata')
        synthetic_identity(metadata['request_id'])
        require(type(metadata['cursor']) is int and metadata['cursor'] > 0,
                'invalid cursor')
        require(type(metadata['round']) is int and metadata['round'] > 0,
                'invalid round')
        for key in META - {'cursor', 'round'}:
            require(isinstance(metadata[key], str) and bool(metadata[key]), 'empty metadata')
        require(type(request) is bytes and bool(request), 'request must be exact bytes')
        with self._connect() as db:
            bundle = self._bundle(db, checkpoint)
            require(metadata['binding_digest'] == digest(bundle['binding/current-event-binding.json']),
                    'binding digest mismatch')
            # request_digest is the protocol envelope digest, not body SHA.
            require(db.execute("SELECT count(*) FROM relay WHERE state != 'applied'").fetchone()[0] == 0,
                    'outstanding request; no restaging or second dispatch')
            db.execute('INSERT INTO relay VALUES (?,?,?,?,?,?,?,?,?)',
                       (metadata['request_id'], canonical(metadata), checkpoint,
                        request, digest(request), 'staged', None, None, None))
            db.execute('INSERT INTO audit(request_id,state) VALUES (?,?)',
                       (metadata['request_id'], 'staged'))

    @staticmethod
    def _row(db: sqlite3.Connection, request_id: str) -> tuple:
        row = db.execute('SELECT metadata,checkpoint,request,request_sha,state,reply,reply_sha,receipt '
                         'FROM relay WHERE request_id=?', (request_id,)).fetchone()
        require(row is not None, 'unknown request')
        require(digest(row[2]) == row[3], 'request corruption')
        require(row[5] is None or digest(row[5]) == row[6], 'reply corruption')
        Journal._bundle(db, row[1])
        return row

    @staticmethod
    def _transition(db: sqlite3.Connection, rid: str, state: str) -> None:
        db.execute('UPDATE relay SET state=? WHERE request_id=?', (state, rid))
        db.execute('INSERT INTO audit(request_id,state) VALUES (?,?)', (rid, state))

    def expose(self, request_id: str) -> bytes:
        # Persist BEFORE bytes can leave. A lost delivery acknowledgement is not
        # permission to expose again; exposed returns WAIT, never a second send.
        with self._connect() as db:
            row = self._row(db, request_id)
            require(row[4] == 'staged', 'already exposed or invalid state; do not resend')
            self._transition(db, request_id, 'exposed')
            raw = row[2]
        return raw

    def stage_reply(self, request_id: str, raw: bytes) -> None:
        require(type(raw) is bytes and bool(raw), 'reply must be exact bytes')
        with self._connect() as db:
            row = self._row(db, request_id)
            if row[5] is not None:
                require(row[5] == raw, 'conflicting reply; preserve original')
                return  # identical transport redelivery; not semantic application
            require(row[4] == 'exposed', 'reply before exposure')
            db.execute('UPDATE relay SET reply=?,reply_sha=? WHERE request_id=?',
                       (raw, digest(raw), request_id))
            self._transition(db, request_id, 'reply-staged')

    def begin_application(self, request_id: str) -> bytes:
        with self._connect() as db:
            row = self._row(db, request_id)
            require(row[4] == 'reply-staged', 'application in doubt or already applied; STOP')
            self._transition(db, request_id, 'applying')
            raw = row[5]
        return raw

    def record_synthetic_application(self, request_id: str, receipt: bytes) -> None:
        """Record externally supplied receipt; NOT proof of a Core transaction."""
        require(type(receipt) is bytes and bool(receipt), 'receipt required')
        with self._connect() as db:
            row = self._row(db, request_id)
            require(row[4] == 'applying', 'application was not started')
            db.execute('UPDATE relay SET receipt=? WHERE request_id=?', (receipt, request_id))
            self._transition(db, request_id, 'applied')

    def recovery(self, request_id: str) -> dict:
        with self._connect() as db:
            row = self._row(db, request_id)
            disposition = {'staged': 'EXPOSURE_PERMITTED', 'exposed': 'WAIT_NO_RESEND',
                'reply-staged': 'REPLY_AVAILABLE_NOT_APPLIED', 'applying': 'IN_DOUBT_STOP',
                'applied': 'RECEIPT_RECORDED_NOT_CORE_VERIFIED'}[row[4]]
            return {'state': row[4], 'disposition': disposition,
                    'metadata': json.loads(row[0]), 'checkpoint': row[1],
                    'request': row[2], 'reply': row[5], 'receipt': row[7]}
