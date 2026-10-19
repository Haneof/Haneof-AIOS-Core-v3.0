"""Create an auditable DEVELOPMENT_TEST_ONLY run record from raw test logs."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
WINDOW = Path(__file__).resolve().parent
HARNESS = ROOT / 'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness'
APPROVED_PYTHON = Path('/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python')


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def source_inventory():
    candidates = []
    candidates.extend(HARNESS.rglob('*.py'))
    candidates.append(HARNESS / 'IDENTITY.json')
    candidates.extend((ROOT / 'src/aios_core').rglob('*.py'))
    candidates.extend((ROOT / 'tools/c15_persistence').rglob('*.py'))
    candidates.extend((WINDOW / 'tests').rglob('*.py'))
    candidates.extend([WINDOW / 'run_development_tests.py',
                       WINDOW / 'record_development_run.py',
                       WINDOW / 'run_development_tests.sh'])
    inventory = {}
    for path in sorted(set(candidates)):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(ROOT).as_posix()
        inventory[relative] = sha_bytes(path.read_bytes())
    return inventory


def git_head():
    completed = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                               capture_output=True, text=True)
    return completed.stdout.strip() if completed.returncode == 0 else None


def main(argv=None):
    if len(sys.argv) != 3:
        raise SystemExit('usage: record_development_run.py EXIT_CODE RESULT_DIRECTORY')
    exit_code = int(sys.argv[1])
    result_dir = Path(sys.argv[2]).resolve()
    output = result_dir / 'stdout.txt'
    error = result_dir / 'stderr.txt'
    junit = result_dir / 'test-results.xml'
    identity_path = HARNESS / 'IDENTITY.json'
    inventory = source_inventory()
    inventory_payload = ''.join(f'{path}\0{digest}\n'
                                for path, digest in sorted(inventory.items())).encode()
    try:
        junit_root = ET.parse(junit).getroot()
        junit_summary = {key: int(junit_root.attrib.get(key, '0'))
                         for key in ('tests', 'failures', 'errors', 'skipped')}
    except (OSError, ET.ParseError):
        junit_summary = None
    record = {
        'schema': 'window55-development-test-record-v1',
        'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
        'classification': 'DEVELOPMENT_TEST_ONLY',
        'test_type': ['unit', 'synthetic', 'static', 'linux-ipc', 'bare-git-cas-fault-injection'],
        'command': 'bash reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW55/run_development_tests.sh',
        'exit_code': exit_code,
        'python_version': platform.python_version(),
        'python_executable': sys.executable,
        'python_executable_realpath': str(Path(sys.executable).resolve()),
        'platform': {'system': platform.system(), 'release': platform.release(),
                     'machine': platform.machine()},
        'source_commit': git_head(),
        'tested_source_sha256': sha_bytes(inventory_payload),
        'tested_source_sha256_algorithm': 'SHA256 of UTF-8 sorted lines: repo-relative-path NUL file-SHA256 LF',
        'tested_source_file_count': len(inventory),
        'tested_source_files': inventory,
        'identity_manifest_sha256': sha_bytes(identity_path.read_bytes()),
        'approved_runtime_used': False,
        'approved_runtime_status': 'AVAILABLE_NOT_USED' if APPROVED_PYTHON.is_file() else 'NOT_PRESENT',
        'formal_runtime_validation': 'PENDING_APPROVED_RUNTIME_AND_PM_AUTHORIZATION',
        'test_summary': junit_summary,
        'artifacts': {
            'stdout': {'path': str(output.relative_to(ROOT)),
                       'sha256': sha_bytes(output.read_bytes()) if output.exists() else None},
            'stderr': {'path': str(error.relative_to(ROOT)),
                       'sha256': sha_bytes(error.read_bytes()) if error.exists() else None},
            'junit': {'path': str(junit.relative_to(ROOT)),
                      'sha256': sha_bytes(junit.read_bytes()) if junit.exists() else None},
        },
    }
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / 'test-record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
