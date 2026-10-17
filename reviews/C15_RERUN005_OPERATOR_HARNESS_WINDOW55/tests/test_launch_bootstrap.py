"""Synthetic verification of the child launcher's pre-exec byte check."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
SAFE_RUNNER = REPO / 'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness/r005/safe_runner.py'


def _bootstrap_code():
    tree = ast.parse(SAFE_RUNNER.read_bytes(), filename=str(SAFE_RUNNER))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == '_VERIFIED_LAUNCH_BOOTSTRAP'
                for target in node.targets):
            value = ast.literal_eval(node.value)
            if not isinstance(value, str):
                raise AssertionError('verified launch bootstrap is not a string')
            return value
    raise AssertionError('verified launch bootstrap constant is missing')


class LaunchBootstrapTests(unittest.TestCase):
    def test_exact_bootstrap_bytes_execute_in_real_main_namespace(self):
        code = _bootstrap_code()
        with tempfile.TemporaryDirectory(prefix='r005-bootstrap-') as temp:
            launch = Path(temp) / 'probe_launch.py'
            launch.write_text(
                "import pathlib,sys\n"
                "assert __name__ == '__main__'\n"
                "assert pathlib.Path(__file__).resolve() == pathlib.Path(sys.argv[0]).resolve()\n"
                "print('BOOTSTRAP_EXECUTED_PINNED_BYTES')\n",
                encoding='utf-8')
            expected = hashlib.sha256(launch.read_bytes()).hexdigest()
            completed = subprocess.run([sys.executable, '-I', '-c', code,
                                        str(launch), expected], capture_output=True,
                                       text=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout.strip(), 'BOOTSTRAP_EXECUTED_PINNED_BYTES')

    def test_tampered_bootstrap_bytes_are_never_executed(self):
        code = _bootstrap_code()
        with tempfile.TemporaryDirectory(prefix='r005-bootstrap-tamper-') as temp:
            launch = Path(temp) / 'probe_launch.py'
            launch.write_text("print('SHOULD_NOT_RUN')\n", encoding='utf-8')
            completed = subprocess.run([sys.executable, '-I', '-c', code,
                                        str(launch), '0' * 64], capture_output=True,
                                       text=True, timeout=10)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn('LAUNCH_BYTES_CHANGED', completed.stderr)
            self.assertNotIn('SHOULD_NOT_RUN', completed.stdout)


if __name__ == '__main__':
    unittest.main()
