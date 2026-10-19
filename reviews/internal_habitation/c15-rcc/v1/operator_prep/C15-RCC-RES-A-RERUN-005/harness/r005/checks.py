"""Mechanical startup and live-module identity checks for the closed importer."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import platform
import sqlite3
import ssl
import sys

APPROVED_PYTHON = Path('/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python')
FORBIDDEN_MODULES = (
    'tools.c15_preflight', 'aios_core.headless.testing',
    'tools.c15_persistence.provider', 'tools.c15_persistence.provider_process',
    'tools.c15_persistence.synthetic_release', 'tools.c15_persistence.operator_session',
)
ENTRY_FILES = (
    'launch.py', 'r005/cli.py', 'r005/safe_runner.py',
    'r005/publisher_service.py', 'r005/payload.py',
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _launcher():
    launcher = sys.modules.get('__main__')
    if launcher is None or not callable(getattr(launcher, 'verify_current_identity', None)):
        raise ValueError('BLOCKED / VERIFIED_BOOTSTRAP_REQUIRED')
    return launcher


def static_scan(root, *, source_snapshot=None):
    """Reject scripted semantic routing in the immutable entry-source bytes."""
    root = Path(root)
    for relative in ENTRY_FILES:
        if source_snapshot is None:
            data = (root / relative).read_bytes()
        else:
            entry = source_snapshot.get(relative)
            if entry is None:
                raise ValueError(f'BLOCKED / STATIC_SCAN_SOURCE_NOT_PINNED: {relative}')
            data = entry['bytes']
        tree = ast.parse(data, filename=relative)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = ([n.name for n in node.names] if isinstance(node, ast.Import)
                         else [node.module or ''])
                if any(name.startswith(FORBIDDEN_MODULES) for name in names):
                    raise ValueError('forbidden semantic adapter import')
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, 'attr', '')
                if name == 'ModelDirective':
                    raise ValueError('entry must parse external directive, never construct one')
            if isinstance(node, ast.Compare):
                if any(isinstance(n, ast.Attribute) and n.attr == 'user_input' for n in ast.walk(node)):
                    raise ValueError('scripted semantic user_input router')
                if any(isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)
                       and n.slice.value == 'user_input' for n in ast.walk(node)):
                    raise ValueError('scripted semantic user_input router')


def verify(root, repo, manifest_sha):
    """Re-audit full protected trees and verify the actual approved runtime."""
    root = Path(root)
    repo = Path(repo)
    launcher = _launcher()
    manifest = launcher.verify_current_identity(root, repo, manifest_sha)
    state = launcher.ACTIVE_IDENTITY
    source_snapshot = {
        relative: entry for relative, entry in state['snapshots'].items()
        if relative in ENTRY_FILES
    }
    static_scan(root, source_snapshot=source_snapshot)

    if Path(sys.executable).resolve() != APPROVED_PYTHON.resolve():
        raise ValueError('executable path substitution')
    if sha(APPROVED_PYTHON.resolve()) != manifest['python_sha256']:
        raise ValueError('executable byte substitution')
    if (platform.python_version(), sqlite3.sqlite_version, ssl.OPENSSL_VERSION.split()[1]) != (
        '3.12.14', '3.45.1', '3.0.13'
    ):
        raise ValueError('runtime version substitution')
    import pydantic
    import pytest
    if (pydantic.__version__, pytest.__version__) != ('2.13.5', '8.4.2'):
        raise ValueError('dependency substitution')
    launcher.verify_loaded_modules(repo, root)
    return manifest


def bootstrap_sha256():
    """Return the launch.py hash from the verified in-memory identity snapshot."""
    launcher = _launcher()
    state = launcher.ACTIVE_IDENTITY
    if state is None:
        raise ValueError('BLOCKED / VERIFIED_BOOTSTRAP_REQUIRED')
    launcher.verify_current_identity(state['root'], state['repo'], state['manifest_sha256'])
    return state['snapshots']['launch.py']['sha256']


def loaded_modules(repo, root):
    """Report only modules whose live objects came from the pinned byte loader."""
    for name in sys.modules:
        if name.startswith(FORBIDDEN_MODULES):
            raise ValueError('forbidden linked semantic adapter: ' + name)
    launcher = _launcher()
    identity = launcher.verify_loaded_modules(repo, root)
    identity['semantic_callback_router_disabled'] = 'PASS'
    return identity
