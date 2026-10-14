"""Exact byte/import/executable checks before any runtime or provider startup."""
import ast
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import ssl
import subprocess
import sys

APPROVED_PYTHON=Path('/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python')
FORBIDDEN_MODULES=('tools.c15_preflight','aios_core.headless.testing',
    'tools.c15_persistence.provider','tools.c15_persistence.provider_process',
    'tools.c15_persistence.synthetic_release','tools.c15_persistence.operator_session')
ENTRY_FILES=('launch.py','r005/cli.py','r005/safe_runner.py','r005/publisher_service.py','r005/payload.py')


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def static_scan(root):
    for relative in ENTRY_FILES:
        tree=ast.parse((root/relative).read_bytes(),filename=relative)
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names=[n.name for n in node.names] if isinstance(node,ast.Import) else [node.module or '']
                if any(n.startswith(FORBIDDEN_MODULES) for n in names):raise ValueError('forbidden semantic adapter import')
            if isinstance(node,ast.Call):
                name=node.func.id if isinstance(node.func,ast.Name) else getattr(node.func,'attr','')
                if name=='ModelDirective':raise ValueError('entry must parse external directive, never construct one')
            if isinstance(node,ast.Compare):
                # Entry code may validate schemas/identities, never route on semantic text.
                if any(isinstance(n,ast.Attribute) and n.attr=='user_input' for n in ast.walk(node)):
                    raise ValueError('scripted semantic user_input router')
                if any(isinstance(n,ast.Subscript) and isinstance(n.slice,ast.Constant)
                    and n.slice.value=='user_input' for n in ast.walk(node)):
                    raise ValueError('scripted semantic user_input router')


def verify(root,repo,manifest_sha):
    root=Path(root).resolve();repo=Path(repo).resolve();p=root/'IDENTITY.json'
    if sha(p)!=manifest_sha:raise ValueError('manifest substitution')
    manifest=json.loads(p.read_bytes())
    actual={str(p.relative_to(root)) for p in root.rglob('*.py')}
    if actual!=set(manifest['harness_files']):raise ValueError('harness file set substitution')
    for rel,digest in manifest['harness_files'].items():
        p=root/rel
        if p.is_symlink() or sha(p)!=digest:raise ValueError('harness byte substitution: '+rel)
    for rel,digest in manifest['source_files'].items():
        p=repo/rel
        if p.is_symlink() or sha(p)!=digest:raise ValueError('current Core/C15 byte substitution: '+rel)
    for directory in ('src/aios_core','tools/c15_persistence'):
        actual={str(p.relative_to(repo)) for p in (repo/directory).rglob('*.py')}
        expected={p for p in manifest['source_files'] if p.startswith(directory+'/')}
        if actual!=expected:raise ValueError('Core/C15 file set drift')
    if Path(sys.executable).resolve()!=APPROVED_PYTHON.resolve():raise ValueError('executable path substitution')
    if sha(APPROVED_PYTHON.resolve())!=manifest['python_sha256']:raise ValueError('executable byte substitution')
    if (platform.python_version(),sqlite3.sqlite_version,ssl.OPENSSL_VERSION.split()[1])!=('3.12.14','3.45.1','3.0.13'):
        raise ValueError('runtime version substitution')
    import pydantic,pytest
    if (pydantic.__version__,pytest.__version__)!=('2.13.5','8.4.2'):raise ValueError('dependency substitution')
    static_scan(root)
    return manifest


def loaded_modules(repo,root):
    for name in sys.modules:
        if name.startswith(FORBIDDEN_MODULES):raise ValueError('forbidden linked semantic adapter: '+name)
    for name,module in list(sys.modules.items()):
        filename=getattr(module,'__file__',None)
        if not filename:continue
        path=Path(filename).resolve()
        if name=='aios_core' or name.startswith('aios_core.'):
            if not path.is_relative_to(Path(repo).resolve()/'src/aios_core'):raise ValueError('Core import substitution')
        if name=='r005' or name.startswith('r005.'):
            if not path.is_relative_to(Path(root).resolve()/'r005'):raise ValueError('Harness import substitution')
        if name=='tools.c15_persistence' or name.startswith('tools.c15_persistence.'):
            if not path.is_relative_to(Path(repo).resolve()/'tools/c15_persistence'):raise ValueError('C15 import substitution')
    return {'semantic_callback_router_disabled':'PASS','module_import_identity':'PASS',
        'loaded_modules':sorted(n for n in sys.modules if n.startswith(('aios_core','r005','tools.c15_persistence')))}
