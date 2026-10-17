"""Unittest runner that emits a JUnit-equivalent development-only report."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import time
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
TESTS = Path(__file__).resolve().parent / 'tests'


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
        self.outcomes.append(self._case(test, 'expected-failure', self._exc_info_to_string(err, test)))

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.outcomes.append(self._case(test, 'unexpected-success'))


def write_junit(path: Path, result: RecordingResult, elapsed: float):
    tests = result.outcomes
    failures = sum(item['status'] in {'failure', 'unexpected-success'} for item in tests)
    errors = sum(item['status'] == 'error' for item in tests)
    skipped = sum(item['status'] in {'skipped', 'expected-failure'} for item in tests)
    suite = ET.Element('testsuite', {
        'name': 'window55.development', 'tests': str(len(tests)),
        'failures': str(failures), 'errors': str(errors), 'skipped': str(skipped),
        'time': f'{elapsed:.6f}',
    })
    for item in tests:
        case = ET.SubElement(suite, 'testcase', {
            'classname': item['classname'], 'name': item['name'], 'time': '0',
        })
        if item['status'] in {'failure', 'unexpected-success'}:
            node = ET.SubElement(case, 'failure', {'message': item['status']})
            node.text = item['detail']
        elif item['status'] == 'error':
            node = ET.SubElement(case, 'error', {'message': 'test error'})
            node.text = item['detail']
        elif item['status'] in {'skipped', 'expected-failure'}:
            node = ET.SubElement(case, 'skipped', {'message': item['status']})
            node.text = item['detail']
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(path, encoding='utf-8', xml_declaration=True)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--junit', type=Path, required=True)
    args = parser.parse_args(argv)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    suite = unittest.defaultTestLoader.discover(str(TESTS), pattern='test_*.py')
    runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=2, resultclass=RecordingResult)
    started = time.monotonic()
    result = runner.run(suite)
    elapsed = time.monotonic() - started
    write_junit(args.junit, result, elapsed)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
