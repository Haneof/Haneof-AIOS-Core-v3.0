"""Approved bootstrap behavioral attacks, with real qualified interpreter.
Runtime value/import fault injection is via test-only sitecustomize, not candidate edits.
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import pytest

FROZEN = 'f20f2edfa7af00d0286493fd15196ca9503bc315'

@pytest.fixture
def repo_copy(package, tmp_path):
    source = pathlib.Path(os.environ['C002_REPO'])
    target = tmp_path / 'repo'
    target.mkdir()
    shutil.copytree(source / '.git', target / '.git')
    for name in ('src', 'tests'):
        shutil.copytree(source / name, target / name, ignore=shutil.ignore_patterns('__pycache__'))
    return target


def verify(package, repo, tmp_path, *, injection='', extra_env=None):
    env = dict(os.environ, AIOS_REPO_ROOT=str(repo), AIOS_RUNTIME_ROOT=os.environ['C002_RUNTIME'],
        PYTHONDONTWRITEBYTECODE='1')
    hook = tmp_path / 'hook'
    hook.mkdir(exist_ok=True)
    (hook / 'sitecustomize.py').write_text(injection)
    env['PYTHONPATH'] = str(hook)
    if extra_env:
        env.update(extra_env)
    run = subprocess.run(['bash', str(package / 'bootstrap/bootstrap_runtime.sh'), '--verify'],
        env=env, capture_output=True, text=True, timeout=120)
    print(run.stdout, run.stderr)
    return run


@pytest.mark.parametrize('damage', ['none', 'wrong_root', 'missing_git', 'missing_object', 'core_byte', 'tests_byte', 'foreign_import'])
def test_c6_bootstrap_identity(package, repo_copy, tmp_path, damage):
    injection = ''
    extra = {}
    if damage == 'wrong_root':
        repo_copy = tmp_path / 'not_repo'
        repo_copy.mkdir()
    elif damage == 'missing_git':
        shutil.rmtree(repo_copy / '.git')
    elif damage == 'missing_object':
        # Use a valid empty Git database, not a metadata-missing case.
        shutil.rmtree(repo_copy / '.git')
        subprocess.run(['git', 'init', '-q', str(repo_copy)], check=True)
        assert subprocess.run(['git', '-C', str(repo_copy), 'cat-file', '-e', FROZEN],
            capture_output=True).returncode != 0
    elif damage in ('core_byte', 'tests_byte'):
        folder = repo_copy / ('src/aios_core' if damage == 'core_byte' else 'tests')
        path = sorted(folder.rglob('*.py'))[0]
        path.write_bytes(path.read_bytes() + b'\n# synthetic drift\n')
    elif damage == 'foreign_import':
        foreign = tmp_path / 'foreign.py'
        foreign.write_text('# synthetic foreign import\n')
        injection = ('import sys, types\n'
            "m=types.ModuleType('aios_core')\n"
            f'm.__file__={str(foreign)!r}\n'
            "sys.modules['aios_core']=m\n")
    result = verify(package, repo_copy, tmp_path, injection=injection, extra_env=extra)
    if damage == 'none':
        assert result.returncode == 0
    else:
        assert result.returncode != 0, 'unsafe bootstrap returned success'
        assert 'BLOCKED' in result.stderr


def test_c6_shared_canonical_manifest(package, repo_copy):
    from operator_tools import rc_identity
    from aios_exchange.verify import core_content_manifest
    first = core_content_manifest(repo_copy / 'src/aios_core')
    second = core_content_manifest(repo_copy / 'src/aios_core')
    assert first == second
    assert [r['path'] for r in first['files']] == sorted(r['path'] for r in first['files'])
    report = rc_identity.verify(repo_copy)
    assert report['ok']
    packet = json.loads((package / 'RESIDENT_SAFE_LAUNCH_PACKET.json').read_text())
    assert first['manifest_sha256'] == packet['frozen_core_content_manifest_sha256']
    assert report['observed']['core_content_manifest_sha256'] == first['manifest_sha256']


@pytest.mark.parametrize('library,value,accepted', [
    ('sqlite','3.45.1',True), ('sqlite','3.40.1',False),
    ('openssl','OpenSSL 3.0.13 30 Jan 2024',True), ('openssl','OpenSSL 3.0.14 4 Jun 2024',False)])
def test_c7_exact_runtime_pin(package, repo_copy, tmp_path, library, value, accepted):
    injection = (f'import sqlite3\nsqlite3.sqlite_version={value!r}\n' if library == 'sqlite'
        else f'import ssl\nssl.OPENSSL_VERSION={value!r}\n')
    result = verify(package, repo_copy, tmp_path, injection=injection)
    assert (result.returncode == 0) == accepted
    if not accepted:
        assert 'BLOCKED' in result.stderr


def test_c7_real_system_sqlite_fallback(package, repo_copy, tmp_path):
    path = pathlib.Path('/usr/lib/x86_64-linux-gnu/libsqlite3.so.0')
    assert path.is_file(), 'probe requires Debian x86_64 system SQLite'
    env = dict(os.environ, LD_PRELOAD=str(path))
    observed = subprocess.check_output([sys.executable, '-c', 'import sqlite3; print(sqlite3.sqlite_version)'], env=env, text=True).strip()
    assert observed != '3.45.1', 'negative-control system SQLite unexpectedly equals pin'
    result = verify(package, repo_copy, tmp_path, extra_env={'LD_PRELOAD': str(path)})
    assert result.returncode != 0
    assert 'BLOCKED' in result.stderr
