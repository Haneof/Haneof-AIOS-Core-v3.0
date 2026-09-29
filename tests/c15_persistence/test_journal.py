"""Synthetic-only storage tests. NOT a Core exactly-once acceptance suite."""
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid

from tools.c15_persistence.journal import Journal, PersistenceError, REQUIRED, digest, durable_path


class JournalTests(unittest.TestCase):
    def setUp(self):
        base = Path('/home/user/c15-persistence-unit-probes')
        base.mkdir(exist_ok=True, mode=0o700)
        self.parent = Path(tempfile.mkdtemp(prefix='synthetic-unit-', dir=base))
        self.root = self.parent / 'backend'
        self.run = 'synthetic-run-' + uuid.uuid4().hex
        self.session = 'synthetic-session-' + uuid.uuid4().hex
        self.rid = 'synthetic-request-' + uuid.uuid4().hex
        self.j = Journal(self.root, run_id=self.run, session_id=self.session, create=True)
        self.bundle = {name: ('synthetic:' + name).encode() for name in REQUIRED}
        # Exercise actual SQLite bytes including a committed WAL tail. SQLite's
        # backup API makes each opaque DB snapshot coherent; no Core is invoked.
        live = self.parent / 'synthetic-live.sqlite'
        with sqlite3.connect(live) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE synthetic_effects(id INTEGER PRIMARY KEY, body BLOB)')
            db.execute('INSERT INTO synthetic_effects VALUES (1, ?)', (b'exact\x00world',))
            db.commit()
            with sqlite3.connect(self.parent / 'snapshot.sqlite') as target:
                db.backup(target)
        self.bundle['runtime/world.sqlite'] = (self.parent / 'snapshot.sqlite').read_bytes()
        self.bundle['runtime/index.sqlite'] = self.bundle['runtime/world.sqlite']
        self.bundle['evidence/failures.jsonl'] = b'{"synthetic_failure":true}\n'
        self.cid = self.j.checkpoint(self.bundle)
        self.meta = dict(cursor=101, event_id='synthetic-event-101', round=1,
            request_id=self.rid, nonce='synthetic-nonce', request_digest=digest(b'envelope'),
            binding_digest=digest(self.bundle['binding/current-event-binding.json']))
        self.request = b'{ "synthetic_request": "\\u4f60", "n": 1 }\n'
        self.reply = b' {"synthetic_reply": true, "opaque": "\\u0041"}\r\n'

    def tearDown(self):
        # Disposable state only. Frozen E2E roots and evidence logs are retained.
        result = self._outcome.result
        failed = any(test is self for test, _ in result.errors + result.failures)
        if failed:
            print('RED_STATE_RETAINED=' + str(self.parent), flush=True)
        else:
            shutil.rmtree(self.parent)

    def reopen(self):
        return Journal(self.root, run_id=self.run, session_id=self.session)

    def stage(self):
        self.j.stage(self.meta, self.request, self.cid)

    def kill_after(self, operation):
        script = '''
import os, signal, sys
from pathlib import Path
from tools.c15_persistence.journal import Journal
j = Journal(Path(sys.argv[1]), run_id=sys.argv[2], session_id=sys.argv[3])
rid = sys.argv[4]
operation = sys.argv[5]
if operation == 'expose': j.expose(rid)
if operation == 'reply': j.stage_reply(rid, bytes.fromhex(sys.argv[6]))
if operation == 'apply': j.begin_application(rid)
os.kill(os.getpid(), signal.SIGKILL)
'''
        completed = subprocess.run([sys.executable, '-c', script, str(self.root),
            self.run, self.session, self.rid, operation, self.reply.hex()],
            capture_output=True, text=True)
        self.assertEqual(completed.returncode, -signal.SIGKILL, completed.stderr)

    def test_exact_checkpoint_and_required_evidence_survive_reopen(self):
        self.assertEqual(self.reopen().recover_checkpoint(self.cid), self.bundle)
        for name in REQUIRED:
            changed = dict(self.bundle)
            changed.pop(name)
            with self.assertRaises(PersistenceError):
                self.j.checkpoint(changed)
        self.assertEqual(self.j.recover_checkpoint(self.cid), self.bundle)

    def test_request_staged_kill_reopen_exact_bytes(self):
        self.stage()
        self.kill_after('none')
        recovered = self.reopen()
        self.assertEqual(recovered.recovery(self.rid)['state'], 'staged')
        self.assertEqual(recovered.expose(self.rid), self.request)
        with self.assertRaises(PersistenceError):
            recovered.expose(self.rid)

    def test_exposed_kill_reopen_wait_no_resend(self):
        self.stage()
        self.kill_after('expose')
        recovered = self.reopen()
        self.assertEqual(recovered.recovery(self.rid)['disposition'], 'WAIT_NO_RESEND')
        with self.assertRaises(PersistenceError):
            recovered.expose(self.rid)

    def test_reply_staged_kill_reopen_no_byte_rewriting(self):
        self.stage()
        self.j.expose(self.rid)
        self.kill_after('reply')
        recovered = self.reopen()
        self.assertEqual(recovered.recovery(self.rid)['reply'], self.reply)
        recovered.stage_reply(self.rid, self.reply)
        with self.assertRaises(PersistenceError):
            recovered.stage_reply(self.rid, self.reply.strip())
        self.assertEqual(recovered.begin_application(self.rid), self.reply)

    def test_application_gap_is_in_doubt_not_exactly_once_claim(self):
        self.stage()
        self.j.expose(self.rid)
        self.j.stage_reply(self.rid, self.reply)
        self.kill_after('apply')
        recovered = self.reopen()
        self.assertEqual(recovered.recovery(self.rid)['disposition'], 'IN_DOUBT_STOP')
        with self.assertRaises(PersistenceError):
            recovered.begin_application(self.rid)
        self.assertIsNone(recovered.recovery(self.rid)['receipt'])

    def test_receipt_recording_does_not_claim_core_verification(self):
        self.stage()
        self.j.expose(self.rid)
        self.j.stage_reply(self.rid, self.reply)
        self.j.begin_application(self.rid)
        self.j.record_synthetic_application(self.rid, b'synthetic-receipt')
        recovered = self.reopen().recovery(self.rid)
        self.assertEqual(recovered['disposition'], 'RECEIPT_RECORDED_NOT_CORE_VERIFIED')
        with self.assertRaises(PersistenceError):
            self.j.begin_application(self.rid)

    def test_no_production_or_retired_identity_entrypoint(self):
        with self.assertRaises(PersistenceError):
            Journal(self.parent / 'denied', run_id='not-synthetic', session_id=self.session, create=True)
        meta = dict(self.meta, request_id='not-synthetic')
        with self.assertRaises(PersistenceError):
            self.j.stage(meta, self.request, self.cid)
        self.assertFalse((self.parent / 'denied').exists())

    def test_wrong_identity_missing_backend_no_recreation(self):
        with self.assertRaises(PersistenceError):
            Journal(self.root, run_id=self.run, session_id='synthetic-other')
        with self.assertRaises(PersistenceError):
            Journal(self.parent / 'missing', run_id=self.run, session_id=self.session)
        self.assertFalse((self.parent / 'missing').exists())
        with self.assertRaises(FileExistsError):
            Journal(self.root, run_id=self.run, session_id=self.session, create=True)

    def test_bad_paths(self):
        for p in ('/tmp/synthetic', '/var/tmp/synthetic', '/dev/shm/synthetic',
                  '/home/user/.cache/synthetic', '/home/user/dist/synthetic',
                  '/home/user/.git/synthetic'):
            with self.subTest(path=p), self.assertRaises(PersistenceError):
                durable_path(Path(p))
        link = self.parent / 'link'
        link.symlink_to('/tmp', target_is_directory=True)
        with self.assertRaises(PersistenceError):
            durable_path(link / 'synthetic')

    def test_corrupt_artifact_blocks_exposure(self):
        self.stage()
        with sqlite3.connect(self.j.path) as db:
            db.execute('UPDATE artifacts SET body=? WHERE name=?',
                       (b'tampered', 'runtime/world.sqlite'))
        with self.assertRaises(PersistenceError):
            self.j.expose(self.rid)

    def test_missing_barrier_wrong_binding_and_outstanding(self):
        with self.assertRaises(PersistenceError):
            self.j.stage(self.meta, self.request, 999)
        with self.assertRaises(PersistenceError):
            self.j.stage(dict(self.meta, binding_digest='wrong'), self.request, self.cid)
        self.stage()
        with self.assertRaises(PersistenceError):
            self.j.stage(dict(self.meta, request_id='synthetic-other'), self.request, self.cid)
        with self.assertRaises(PersistenceError):
            self.j.stage_reply(self.rid, self.reply)

    def test_concurrent_exposure_one_winner(self):
        self.stage()
        script = '''
import sys
from pathlib import Path
from tools.c15_persistence.journal import Journal, PersistenceError
j = Journal(Path(sys.argv[1]), run_id=sys.argv[2], session_id=sys.argv[3])
try: j.expose(sys.argv[4])
except PersistenceError: sys.exit(3)
'''
        cmd = [sys.executable, '-c', script, str(self.root), self.run, self.session, self.rid]
        children = [subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        results = []
        for p in children:
            _, err = p.communicate(timeout=20)
            self.assertIn(p.returncode, (0, 3), err)
            results.append(p.returncode)
        self.assertEqual(sorted(results), [0, 3])

    def test_uncommitted_transaction_kill_preserves_old_checkpoint(self):
        code = '''
import os, signal, sqlite3, sys
c = sqlite3.connect(sys.argv[1])
c.execute('BEGIN IMMEDIATE')
c.execute('DELETE FROM artifacts')
os.kill(os.getpid(), signal.SIGKILL)
'''
        p = subprocess.run([sys.executable, '-c', code, str(self.j.path)])
        self.assertEqual(p.returncode, -signal.SIGKILL)
        self.assertEqual(self.reopen().recover_checkpoint(self.cid), self.bundle)


if __name__ == '__main__':
    unittest.main(verbosity=2)
