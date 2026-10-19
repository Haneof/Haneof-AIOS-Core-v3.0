#!/usr/bin/env python3
"""Arena C15-ENG-001 development test runner.

DEVELOPMENT_ONLY / FORMAL_VALIDATION_NOT_PERFORMED / DO_NOT_MERGE

Runs the new ``reviews/C15_RERUN005_ARENA_ENG_001/tests`` suite with the stdlib
``unittest`` runner (the project's existing convention) and records real exit
codes, real runtime and real environment facts under this directory only.

Two deliberate differences from the Window55 runner:

1. Bytecode suppression uses ``sys.dont_write_bytecode`` in addition to
   ``PYTHONDONTWRITEBYTECODE``. Setting only the environment variable from
   inside an already-started interpreter has no effect, and ``__pycache__``
   written into the identity-pinned harness tree makes
   ``launch.scan_identity`` fail with ``UNAPPROVED_OR_REPLACED_DIRECTORY``.
   Verified during this task: running the Window55 runner directly with
   ``python3`` instead of the blessed ``run_development_tests.sh`` (which uses
   ``python3 -B``) reproduced exactly that blockage.
2. Evidence is written ONLY under ``reviews/C15_RERUN005_ARENA_ENG_001/``.
   Archived Window55/Window57/Window66 evidence is never modified.

This runner never touches ``src/aios_core/**``, ``tools/c15_persistence/**``,
the original regression assertions, or any official evidence directory.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

# Must happen before any test module is imported.
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
TESTS = HERE / 'tests'
RUNS = HERE / 'development-test-runs'

# Makes ``import synthetic_fixtures`` and explicit ``--tests`` module names work
# the same way unittest discovery would.
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = []

    @staticmethod
    def _case(test, status, detail=''):
        test_id = test.id()
        module, _, qualname = test_id.rpartition('.')
        classname, _, method = qualname.rpartition('.')
        return {'classname': '.'.join(x for x in (module, classname) if x),
                'name': method or qualname or test_id,
                'status': status, 'detail': detail}

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes.append(self._case(test, 'passed'))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes.append(self._case(test, 'failure', self._exc_info_to_string(err, test)))

    def addError(self, test, err):
        super().addError(test, err)
        self.outcomes.append(self._case(test, 'error', self._exc_info_to_string(err, test)))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes.append(self._case(test, 'skipped', str(reason)))

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.outcomes.append(self._case(test, 'expected-failure',
                                        self._exc_info_to_string(err, test)))

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.outcomes.append(self._case(test, 'unexpected-success'))

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            status = 'failure' if issubclass(err[0], test.failureException) else 'error'
            label = str(subtest) if subtest else test.id()
            self.outcomes.append({'classname': test.__class__.__module__ + '.'
                                             + test.__class__.__qualname__,
                                  'name': label, 'status': status,
                                  'detail': self._exc_info_to_string(err, test)})


def write_junit(path: Path, result: RecordingResult, elapsed: float, suite_name: str):
    outcomes = result.outcomes
    failures = sum(item['status'] in {'failure', 'unexpected-success'} for item in outcomes)
    errors = sum(item['status'] == 'error' for item in outcomes)
    skipped = sum(item['status'] in {'skipped', 'expected-failure'} for item in outcomes)
    suite = ET.Element('testsuite', {
        'name': suite_name, 'tests': str(len(outcomes)), 'failures': str(failures),
        'errors': str(errors), 'skipped': str(skipped), 'time': f'{elapsed:.6f}',
    })
    for item in outcomes:
        case = ET.SubElement(suite, 'testcase',
                             {'classname': item['classname'], 'name': item['name'], 'time': '0'})
        if item['status'] in {'failure', 'unexpected-success'}:
            ET.SubElement(case, 'failure', {'message': item['status']}).text = item['detail']
        elif item['status'] == 'error':
            ET.SubElement(case, 'error', {'message': 'test error'}).text = item['detail']
        elif item['status'] in {'skipped', 'expected-failure'}:
            ET.SubElement(case, 'skipped', {'message': item['status']}).text = item['detail']
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(path, encoding='utf-8', xml_declaration=True)
    return {'tests': len(outcomes), 'failures': failures, 'errors': errors, 'skipped': skipped}


def environment_facts() -> dict:
    return {
        'python_implementation': platform.python_implementation(),
        'python_version': platform.python_version(),
        'approved_python_3_12_14_used': False,
        'approved_python_note': ('Arena sandbox provides CPython '
                                 + platform.python_version()
                                 + '; the project-approved 3.12.14 runtime is NOT present '
                                   'and was NOT exercised'),
        'platform': platform.platform(),
        'system': platform.system(),
        'release': platform.release(),
        'uid': os.getuid(),
        'gid': os.getgid(),
        'runner_uid_is_999': os.getuid() == 999,
        'resident_uid_is_996': os.getuid() == 996,
        'stdin_isatty': os.isatty(0),
        'stdout_isatty': os.isatty(1),
        'controlling_tty_available': _controlling_tty_available(),
        'openssl_path': '/usr/bin/openssl',
        'openssl_version': _openssl_version(),
        'argv0': sys.argv[0],
        'executable': sys.executable,
        'dont_write_bytecode': bool(sys.dont_write_bytecode),
    }


def _controlling_tty_available() -> bool:
    try:
        fd = os.open('/dev/tty', os.O_WRONLY | os.O_NOFOLLOW)
    except OSError as exc:
        return f'unavailable: {exc}'
    os.close(fd)
    return True


def _openssl_version() -> str:
    import subprocess
    try:
        out = subprocess.run(['/usr/bin/openssl', 'version'], capture_output=True, timeout=10)
        return out.stdout.decode('utf-8', 'replace').strip()
    except Exception as exc:  # pragma: no cover - diagnostic only
        return f'unavailable: {exc}'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', action='store_true',
                        help='write a timestamped run record under development-test-runs/')
    parser.add_argument('--junit', type=Path, default=None,
                        help='explicit JUnit XML destination')
    parser.add_argument('--suite-name', default='arena.c15.eng.001.development')
    parser.add_argument('tests', nargs='*', default=None,
                        help='optional explicit test module names (default: discover all)')
    args = parser.parse_args(argv)

    loader = unittest.TestLoader()
    if args.tests:
        suite = unittest.TestSuite()
        for name in args.tests:
            suite.addTests(loader.loadTestsFromName(name))
    else:
        suite = loader.discover(str(TESTS), pattern='test_*.py', top_level_dir=str(TESTS))

    runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=2,
                                     resultclass=RecordingResult)
    started_wall = dt.datetime.now(dt.timezone.utc)
    started = time.monotonic()
    result = runner.run(suite)
    elapsed = time.monotonic() - started
    exit_code = 0 if result.wasSuccessful() else 1

    junit_path = args.junit
    run_dir = None
    if args.record:
        run_id = started_wall.strftime('%Y%m%dT%H%M%SZ') + f'-{os.getpid()}'
        run_dir = RUNS / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        junit_path = junit_path or (run_dir / 'test-results.xml')
    if junit_path is None:
        # Never leave a stray artifact inside the repository when the caller did
        # not ask for a recorded run.
        junit_path = Path(tempfile.mkdtemp(prefix='arena-c15-eng-junit-')) / 'test-results.xml'
    counts = write_junit(junit_path, result, elapsed, args.suite_name)

    record = {
        'task': 'C15-ARENA-ENG-001-SIGNED-TTYLESS-REGRESSION-CORRECTIVE-PILOT',
        'classification': ['DEVELOPMENT_ONLY', 'FORMAL_VALIDATION_NOT_PERFORMED',
                           'DO_NOT_MERGE'],
        'suite_name': args.suite_name,
        'started_utc': started_wall.isoformat(timespec='seconds'),
        'elapsed_seconds': round(elapsed, 6),
        'exit_code': exit_code,
        'was_successful': bool(result.wasSuccessful()),
        'counts': counts,
        'testsRun': result.testsRun,
        'junit': str(junit_path),
        'environment': environment_facts(),
        'outcomes': [{'classname': item['classname'], 'name': item['name'],
                      'status': item['status']} for item in result.outcomes],
    }
    if run_dir is not None:
        (run_dir / 'test-record.json').write_text(json.dumps(record, indent=2) + '\n',
                                                  encoding='utf-8')
    print(json.dumps({k: record[k] for k in ('suite_name', 'elapsed_seconds', 'exit_code',
                                             'was_successful', 'counts', 'testsRun', 'junit')},
                     indent=2))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
