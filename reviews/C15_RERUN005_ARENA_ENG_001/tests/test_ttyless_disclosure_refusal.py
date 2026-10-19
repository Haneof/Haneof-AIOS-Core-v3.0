"""Signed mode exists because this environment has no controlling TTY.

DEVELOPMENT_ONLY / FORMAL_VALIDATION_NOT_PERFORMED / DO_NOT_MERGE

These tests use the Arena sandbox's genuine absence of a controlling terminal.
That is a real, reproducible property of this environment, not a simulation:
``os.isatty`` is false on all three standard descriptors and ``os.open`` on
``/dev/tty`` fails with ``ENXIO`` because no controlling terminal is attached
to this process.

They establish:
* the legacy per-request TTY disclosure path is genuinely unavailable here, so
  the Window66 signed path is the only possible authorization channel;
* ``open_resident_terminal`` fails closed and leaks no descriptor when the
  opened object is not a real controlling terminal;
* signed mode does not open a Resident TTY at all;
* there is no stdout/stderr token fallback anywhere in the harness (the PM
  authorization forbids one, so its absence is pinned as a regression).

``os`` is substituted for the module under test through a delegating proxy
rather than by mutating the global ``os`` module, so no other code in the
interpreter observes the override.
"""
from __future__ import annotations

import ast
import errno
import os
from pathlib import Path
import stat as stat_module
import unittest

from synthetic_fixtures import HARNESS, make_workdir, response_authorization as ra

PUBLISHER_SERVICE = HARNESS / 'r005' / 'publisher_service.py'
RESPONSE_AUTHORIZATION = HARNESS / 'r005' / 'response_authorization.py'
SAFE_RUNNER = HARNESS / 'r005' / 'safe_runner.py'
TOKEN_NAME = 'RESIDENT_PUBLISH_AUTHORIZATION'


class OsProxy:
    """Delegating stand-in for ``os`` that overrides only named attributes."""

    def __init__(self, real, **overrides):
        self._real = real
        self._overrides = overrides

    def __getattr__(self, name):
        if name in ('_real', '_overrides'):
            return object.__getattribute__(self, name)
        overrides = object.__getattribute__(self, '_overrides')
        if name in overrides:
            return overrides[name]
        return getattr(object.__getattribute__(self, '_real'), name)


class TtylessEnvironmentTests(unittest.TestCase):
    """Record the actual environment facts these tests depend on."""

    def test_this_process_has_no_controlling_terminal(self):
        for descriptor, label in ((0, 'stdin'), (1, 'stdout'), (2, 'stderr')):
            with self.subTest(descriptor=label):
                try:
                    is_tty = os.isatty(descriptor)
                except OSError:
                    is_tty = False
                self.assertFalse(is_tty, f'{label} must not be a TTY in this sandbox')

    def test_dev_tty_cannot_be_opened_without_a_controlling_terminal(self):
        with self.assertRaises(OSError) as caught:
            os.open('/dev/tty', os.O_WRONLY | os.O_NOFOLLOW)
        self.assertEqual(caught.exception.errno, errno.ENXIO,
                         'ENXIO is the kernel answer when no controlling terminal exists')

    def test_legacy_resident_terminal_disclosure_is_refused_here(self):
        """The pre-Window66 authorization channel is genuinely unavailable."""
        with self.assertRaises(OSError) as caught:
            ra.open_resident_terminal()
        self.assertEqual(caught.exception.errno, errno.ENXIO)
        self.assertIn('/dev/tty', str(caught.exception))

    def test_kernel_facilities_the_signed_path_does_need_are_present(self):
        """AF_UNIX, SO_PEERCRED and pidfd exist here; only UID isolation does not."""
        import socket
        self.assertTrue(hasattr(socket, 'AF_UNIX'))
        self.assertTrue(hasattr(socket, 'SO_PEERCRED'))
        self.assertTrue(hasattr(os, 'pidfd_open'))
        self.assertTrue(hasattr(os, 'O_NOFOLLOW'))
        self.assertNotEqual(os.getuid(), 999, 'no real UID999 Runner identity here')
        self.assertNotEqual(os.getuid(), 996, 'no real UID996 Resident identity here')


class TerminalDescriptorFailClosedTests(unittest.TestCase):
    """``open_resident_terminal`` must accept only a real controlling terminal."""

    def setUp(self):
        self._temp = make_workdir('arena-eng-tty-')
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.regular = self.root / 'not-a-terminal'
        self.regular.write_bytes(b'')

    def use_os(self, **overrides):
        proxy = OsProxy(os, **overrides)
        ra.os = proxy
        self.addCleanup(setattr, ra, 'os', os)
        return proxy

    def test_a_regular_file_is_refused_and_the_descriptor_is_not_leaked(self):
        opened = []
        real_open = os.open

        def redirected_open(path, flags, *args, **kwargs):
            if path == '/dev/tty':
                descriptor = real_open(str(self.regular), os.O_WRONLY)
                opened.append(descriptor)
                return descriptor
            return real_open(path, flags, *args, **kwargs)

        self.use_os(open=redirected_open)
        with self.assertRaises(RuntimeError) as caught:
            ra.open_resident_terminal()
        self.assertIn('not a controlling terminal', str(caught.exception))
        self.assertEqual(len(opened), 1, 'exactly one descriptor was opened')
        with self.assertRaises(OSError) as leaked:
            os.fstat(opened[0])
        self.assertEqual(leaked.exception.errno, errno.EBADF,
                         'the failed descriptor must be closed, never leaked')

    def test_a_character_device_that_is_not_a_tty_is_also_refused(self):
        """``os.isatty`` is enforced in addition to the character-device test."""
        real_open = os.open

        class CharacterDeviceStat:
            st_mode = stat_module.S_IFCHR | 0o600

        self.assertTrue(stat_module.S_ISCHR(CharacterDeviceStat.st_mode))
        self.use_os(open=lambda path, flags, *a, **k: (
                        real_open(str(self.regular), os.O_WRONLY)
                        if path == '/dev/tty'
                        else real_open(path, flags, *a, **k)),
                    fstat=lambda _fd: CharacterDeviceStat(),
                    isatty=lambda _fd: False)
        with self.assertRaises(RuntimeError) as caught:
            ra.open_resident_terminal()
        self.assertIn('not a controlling terminal', str(caught.exception))

    def test_missing_o_nofollow_support_is_refused_outright(self):
        """No fallback exists when the platform cannot open without following."""

        class OsWithoutNofollow:
            """Delegates to the real ``os`` but reports ``O_NOFOLLOW`` absent.

            ``hasattr`` resolves ``__getattr__`` on the TYPE, so this must be a
            class-level definition rather than an instance attribute.
            """

            def __getattr__(self, name):
                if name == 'O_NOFOLLOW':
                    raise AttributeError(name)
                return getattr(os, name)

        self.assertTrue(hasattr(os, 'O_NOFOLLOW'),
                        'this host does support O_NOFOLLOW; the test exercises the '
                        'module guard for platforms that do not')
        ra.os = OsWithoutNofollow()
        self.addCleanup(setattr, ra, 'os', os)
        self.assertFalse(hasattr(ra.os, 'O_NOFOLLOW'))
        with self.assertRaises(RuntimeError) as caught:
            ra.open_resident_terminal()
        self.assertIn('O_NOFOLLOW', str(caught.exception))


class SignedModeNeedsNoTerminalTests(unittest.TestCase):
    """Source-level contract: signed mode never opens a Resident TTY."""

    def setUp(self):
        self.source = PUBLISHER_SERVICE.read_text(encoding='utf-8')
        self.tree = ast.parse(PUBLISHER_SERVICE.read_bytes())
        self.main = next(node for node in self.tree.body
                         if isinstance(node, ast.FunctionDef) and node.name == 'main')

    def test_tty_open_is_conditional_on_signed_mode_being_absent(self):
        """``resident_tty_fd = None if signed is not None else open_resident_terminal()``."""
        assignments = [node for node in ast.walk(self.main)
                       if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name)
                               and target.id == 'resident_tty_fd' for target in node.targets)]
        self.assertEqual(len(assignments), 1, 'exactly one resident_tty_fd binding')
        value = assignments[0].value
        self.assertIsInstance(value, ast.IfExp,
                              'TTY disclosure must be conditional, never unconditional')
        self.assertIsInstance(value.body, ast.Constant)
        self.assertIsNone(value.body.value, 'signed mode must set the TTY fd to None')
        self.assertIsInstance(value.test, ast.Compare)
        self.assertIn('signed', ast.unparse(value.test))
        self.assertIn('open_resident_terminal', ast.unparse(value.orelse))

    def test_terminal_descriptor_is_closed_on_shutdown(self):
        self.assertIn('resident_tty_fd is not None', self.source)
        self.assertIn('os.close(resident_tty_fd)', self.source)

    def test_signed_endpoint_is_closed_on_shutdown(self):
        self.assertIn('signed.close()', self.source)

    def test_signed_authority_is_imported_only_inside_main(self):
        """Importing the module must not create signing authority."""
        for node in self.tree.body:
            if isinstance(node, ast.ImportFrom):
                names = {alias.name for alias in node.names}
                self.assertNotIn('SignedResponseAuthority', names,
                                 'the signed authority must be imported lazily inside main()')

    def test_runner_engages_signed_mode_only_from_the_configured_enrollment(self):
        runner_source = SAFE_RUNNER.read_text(encoding='utf-8')
        self.assertIn("os.environ.get('AIOS66_TEST_ENROLLMENT')", runner_source)
        self.assertIn('configured_grant()', runner_source)


class NoStdoutTokenFallbackTests(unittest.TestCase):
    """The PM authorization forbids a stdout token fallback; pin its absence."""

    def test_no_harness_module_echoes_the_capability_token_to_stdout_or_stderr(self):
        offenders = []
        for path in sorted(HARNESS.rglob('*.py')):
            text = path.read_text(encoding='utf-8', errors='replace')
            if TOKEN_NAME not in text:
                continue
            for node in ast.walk(ast.parse(text)):
                if not isinstance(node, ast.Call):
                    continue
                if ast.unparse(node.func) in ('print', 'sys.stdout.write',
                                              'sys.stderr.write', 'stdout.write',
                                              'stderr.write'):
                    offenders.append(f'{path.relative_to(HARNESS)}:{node.lineno}')
        self.assertEqual(offenders, [],
                         'the one-request capability must never be echoed to stdout/stderr')

    def test_the_token_is_written_only_through_the_pre_opened_descriptor(self):
        tree = ast.parse(RESPONSE_AUTHORIZATION.read_bytes())
        writer = next(node for node in ast.walk(tree)
                      if isinstance(node, ast.FunctionDef)
                      and node.name == 'write_resident_capability')
        calls = {ast.unparse(node.func) for node in ast.walk(writer)
                 if isinstance(node, ast.Call)}
        self.assertIn('os.write', calls)
        for forbidden in ('print', 'sys.stdout.write', 'sys.stderr.write'):
            self.assertNotIn(forbidden, calls)
        rendered = ast.unparse(writer)
        self.assertIn('fd', rendered)
        self.assertIn(TOKEN_NAME, rendered)

    def test_open_resident_terminal_requires_o_nofollow_and_a_real_tty(self):
        tree = ast.parse(RESPONSE_AUTHORIZATION.read_bytes())
        opener = next(node for node in ast.walk(tree)
                      if isinstance(node, ast.FunctionDef)
                      and node.name == 'open_resident_terminal')
        rendered = ast.unparse(opener)
        for required in ('O_NOFOLLOW', 'S_ISCHR', 'isatty', "'/dev/tty'", 'os.close'):
            self.assertIn(required, rendered)


if __name__ == '__main__':
    unittest.main(verbosity=2)
