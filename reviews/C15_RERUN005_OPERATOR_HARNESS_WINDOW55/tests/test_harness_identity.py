"""Closed protected-tree inventory and pinned in-memory importer tests."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
HARNESS_SOURCE = REPO / 'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness'
LAUNCH_SOURCE = HARNESS_SOURCE / 'launch.py'


def _load_launcher():
    spec = importlib.util.spec_from_file_location('_r005_window55_launch_tests', LAUNCH_SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _copy_python_tree(source: Path, target: Path, *, include_identity=False):
    source = Path(source)
    target.mkdir(parents=True, exist_ok=False)
    for directory, child_dirs, filenames in os.walk(source, topdown=True, followlinks=False):
        child_dirs[:] = sorted(name for name in child_dirs if name != '__pycache__')
        src_dir = Path(directory)
        dst_dir = target / src_dir.relative_to(source)
        if not dst_dir.exists():
            dst_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(dst_dir, os.stat(src_dir, follow_symlinks=False).st_mode & 0o777)
        for name in sorted(filenames):
            src = src_dir / name
            if src.suffix != '.py' and not (include_identity and name == 'IDENTITY.json'):
                continue
            if src.is_symlink():
                raise AssertionError(f'fixture source unexpectedly contains symlink: {src}')
            dst = dst_dir / name
            shutil.copy2(src, dst, follow_symlinks=False)
    for directory, child_dirs, _ in os.walk(target, topdown=False, followlinks=False):
        src_dir = source / Path(directory).relative_to(target)
        os.chmod(directory, os.stat(src_dir, follow_symlinks=False).st_mode & 0o777)


class HarnessIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.launcher = _load_launcher()
        raw = (HARNESS_SOURCE / 'IDENTITY.json').read_bytes()
        cls.identity_sha = hashlib.sha256(raw).hexdigest()
        cls._identity_bytes = raw

    def fixture(self):
        temp = tempfile.TemporaryDirectory(prefix='r005-identity-')
        base = Path(temp.name)
        harness = base / 'harness'
        source_repo = base / 'source'
        _copy_python_tree(HARNESS_SOURCE, harness, include_identity=True)
        source_repo.mkdir(mode=0o755)
        (source_repo / 'src').mkdir()
        (source_repo / 'tools').mkdir()
        _copy_python_tree(REPO / 'src/aios_core', source_repo / 'src/aios_core')
        _copy_python_tree(REPO / 'tools/c15_persistence', source_repo / 'tools/c15_persistence')
        return temp, harness, source_repo

    def scan(self, harness, source_repo):
        return self.launcher.scan_identity(harness, source_repo, self.identity_sha)

    def test_actual_repository_protected_trees_match_pinned_identity(self):
        state = self.launcher.scan_identity(HARNESS_SOURCE, REPO, self.identity_sha)
        self.assertEqual(state['manifest']['schema'], 'resident-rerun005-harness-identity-v2')
        self.assertIn('r005/checks.py', state['snapshots'])
        self.assertIn('src/aios_core/headless/core.py', state['snapshots'])
        self.assertIn('tools/c15_persistence/backend.py', state['snapshots'])

    def test_full_harness_core_and_c15_trees_scan_as_closed_identity(self):
        temp, harness, source_repo = self.fixture()
        with temp:
            state = self.scan(harness, source_repo)
        self.assertIn('r005/checks.py', state['snapshots'])
        self.assertIn('src/aios_core/headless/core.py', state['snapshots'])
        self.assertIn('tools/c15_persistence/backend.py', state['snapshots'])
        mapping = self.launcher._module_map(state)
        self.assertEqual(mapping['r005.checks'][0], 'r005/checks.py')
        self.assertEqual(mapping['aios_core.headless.core'][0], 'src/aios_core/headless/core.py')
        self.assertEqual(mapping['tools.c15_persistence.backend'][0],
                         'tools/c15_persistence/backend.py')
        self.assertEqual(mapping['r005.publisher_service'][0], 'r005/publisher_service.py')
        self.assertEqual(mapping['r005.response_authorization'][0],
                         'r005/response_authorization.py')

    def test_rejects_same_device_mount_overlay_inside_protected_root(self):
        with tempfile.TemporaryDirectory(prefix='r005-mount-info-') as temp:
            root = Path(temp) / 'harness'
            root.mkdir()
            mountpoint = root / 'r005'
            line = f'41 25 0:42 / {mountpoint} rw - bind /dev/loop0 rw\n'
            original = Path.read_text

            def mountinfo(path, *args, **kwargs):
                if os.fspath(path) == '/proc/self/mountinfo':
                    return line
                return original(path, *args, **kwargs)

            with mock.patch.object(Path, 'read_text', mountinfo):
                with self.assertRaisesRegex(self.launcher.IdentityBlocked,
                                            'PROTECTED_MOUNT_OVERLAY'):
                    self.launcher._reject_mounted_overlays(root)

    def test_rejects_unapproved_pyc_so_python_and_package_overlay(self):
        for filename in ('r005/checks.pyc', 'r005/checks.so',
                         'r005/injected.pyc', 'r005/injected.so',
                         'r005/unlisted.py',
                         'src/aios_core/headless/core.pyc',
                         'src/aios_core/headless/core.so',
                         'r005/checks/__init__.py',
                         'src/aios_core/headless/core/__init__.py'):
            with self.subTest(filename=filename):
                temp, harness, source_repo = self.fixture()
                with temp:
                    path = (harness / filename if filename.startswith('r005/')
                            else source_repo / filename)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b'not authorized')
                    with self.assertRaisesRegex(self.launcher.IdentityBlocked,
                                                'CLOSED_EXECUTABLE_SET_DRIFT|CLOSED_FILE_SET_MISMATCH|UNAPPROVED_OR_REPLACED_DIRECTORY'):
                        self.scan(harness, source_repo)

    def test_rejects_symlink_and_hardlink_aliases(self):
        temp, harness, source_repo = self.fixture()
        with temp:
            original = harness / 'r005/checks.py'
            saved = Path(temp.name) / 'checks.saved'
            shutil.copy2(original, saved)
            original.unlink()
            original.symlink_to(saved)
            with self.assertRaisesRegex(self.launcher.IdentityBlocked, 'PROTECTED_SYMLINK'):
                self.scan(harness, source_repo)

        temp, harness, source_repo = self.fixture()
        with temp:
            source = harness / 'r005/checks.py'
            alias = harness / 'r005/overlay.py'
            os.link(source, alias)
            with self.assertRaisesRegex(self.launcher.IdentityBlocked, 'PROTECTED_HARDLINK'):
                self.scan(harness, source_repo)

    def test_rejects_directory_mode_drift(self):
        temp, harness, source_repo = self.fixture()
        with temp:
            os.chmod(harness / 'r005', 0o700)
            with self.assertRaisesRegex(self.launcher.IdentityBlocked,
                                        'PROTECTED_DIRECTORY_MODE_DRIFT|UNAPPROVED_OR_REPLACED_DIRECTORY'):
                self.scan(harness, source_repo)

    def test_rechecks_inode_and_rejects_path_replacement_after_verified_read(self):
        temp, harness, source_repo = self.fixture()
        with temp:
            original_read = self.launcher._read_regular_at
            swapped = {'done': False}

            def race(directory_fd, name, **kwargs):
                result = original_read(directory_fd, name, **kwargs)
                if kwargs.get('scope') == 'harness' and name == 'checks.py' and not swapped['done']:
                    path = harness / 'r005/checks.py'
                    replacement = path.with_suffix('.replacement')
                    replacement.write_bytes(result[0])
                    os.chmod(replacement, 0o644)
                    os.replace(replacement, path)
                    swapped['done'] = True
                return result

            self.launcher._read_regular_at = race
            try:
                with self.assertRaisesRegex(self.launcher.IdentityBlocked,
                                            'PROTECTED_PATH_REPLACED_AFTER_READ'):
                    self.scan(harness, source_repo)
            finally:
                self.launcher._read_regular_at = original_read

    def test_detects_same_bytes_inode_replacement_after_initial_snapshot(self):
        temp, harness, source_repo = self.fixture()
        with temp:
            state = self.scan(harness, source_repo)
            self.launcher.ACTIVE_IDENTITY = state
            target = harness / 'r005/checks.py'
            replacement = target.with_suffix('.replacement')
            replacement.write_bytes(target.read_bytes())
            os.chmod(replacement, 0o644)
            os.replace(replacement, target)
            with self.assertRaisesRegex(self.launcher.IdentityBlocked,
                                        'EXECUTED_SNAPSHOT_DIFFERS_FROM_DISK'):
                self.launcher.verify_current_identity(harness, source_repo, self.identity_sha)
            self.launcher.ACTIVE_IDENTITY = None

    def test_private_finder_imports_from_snapshots_and_rejects_module_substitution(self):
        temp, harness, source_repo = self.fixture()
        with temp:
            probe = r"""
import importlib, importlib.util, pathlib, sys, types
launch_path = pathlib.Path(sys.argv[1])
harness = pathlib.Path(sys.argv[2])
source = pathlib.Path(sys.argv[3])
identity_sha = sys.argv[4]
spec = importlib.util.spec_from_file_location('_verified_launch_probe', launch_path)
launch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = launch
spec.loader.exec_module(launch)
state = launch.scan_identity(harness, source, identity_sha)
launch.activate_verified_importer(state)
import r005.checks
import r005.response_authorization
import aios_core
import tools.c15_persistence
status = launch.verify_loaded_modules(source, harness)
assert status['module_import_identity'] == 'PASS'
assert 'r005.checks' in status['loaded_modules']
assert 'r005.response_authorization' in status['loaded_modules']
assert 'aios_core' in status['loaded_modules']
assert 'tools.c15_persistence' in status['loaded_modules']
try:
    import tools.unapproved_helper
except launch.IdentityBlocked as exc:
    assert 'UNAPPROVED_PROTECTED_MODULE' in str(exc)
else:
    raise AssertionError('unapproved tools helper path was exposed')
core_loader = launch._VerifiedSourceLoader(
    state, 'aios_core.headless.core', 'src/aios_core/headless/core.py', False)
core_code = core_loader.get_code('aios_core.headless.core')
assert core_code.co_filename.endswith('/src/aios_core/headless/core.py')
assert launch._sha(state['snapshots']['src/aios_core/headless/core.py']['bytes']) == \
       state['snapshots']['src/aios_core/headless/core.py']['sha256']
for protected_name in ('r005.checks', 'aios_core.headless.core'):
    sys.modules[protected_name] = types.ModuleType(protected_name)
    try:
        launch.verify_loaded_modules(source, harness)
    except launch.IdentityBlocked as exc:
        assert 'UNVERIFIED_LOADED_MODULE' in str(exc)
    else:
        raise AssertionError('preloaded protected override was trusted: ' + protected_name)
"""
            completed = subprocess.run(
                [sys.executable, '-I', '-B', '-c', probe, str(HARNESS_SOURCE / 'launch.py'),
                 str(harness), str(source_repo), self.identity_sha],
                capture_output=True, text=True, timeout=30,
                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
            self.assertEqual(completed.returncode, 0,
                             f'stdout={completed.stdout}\nstderr={completed.stderr}')


if __name__ == '__main__':
    unittest.main()
