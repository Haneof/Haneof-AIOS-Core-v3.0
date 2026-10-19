"""Fail-closed tests for regenerate_identity_manifest.py.

DEVELOPMENT_ONLY / FORMAL_VALIDATION_NOT_PERFORMED / DO_NOT_MERGE

These exercise the identity-manifest rebuilder's refusal behaviour against
THROWAWAY SYNTHETIC directories built under ``tempfile.mkdtemp()``. They never
write to, and never mutate, the real frozen Harness Artifact, Launch Packet,
``IDENTITY.json`` or any Window66/Window67 evidence.

The two tests that touch the real checkout are strictly read-only dry runs
(``write=False``), and one of them copies the real harness into a temporary
directory before perturbing the copy, so the real manifest is never modified.

Covered per the PM hardening requirement (PR #390 comment 2026-10-17T12:19:01Z):
``--write`` without an allowlist is refused; the changed set must EQUAL the
allowlist in both directions; protected-source drift, membership change,
bytecode pollution, malformed allowlists, foreign serialization and missing
structure are all refused BEFORE any byte is written; and the correct rebuild
path still changes exactly one digest, ``r005/response_authorization.py``.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ENG = HERE.parent
sys.dont_write_bytecode = True

_spec = importlib.util.spec_from_file_location(
    'arena_eng001_regenerator', ENG / 'regenerate_identity_manifest.py')
regen = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = regen
_spec.loader.exec_module(regen)

AUTHORIZED = 'harness_files:r005/response_authorization.py'

# The real pre-fix and post-fix digests of the authorized harness file, so the
# synthetic reproduction below asserts the genuine transition rather than a
# made-up one.
REAL_OLD_DIGEST = 'abc30a28661f22390a9f4a34df5d9764fe27e155f7c285c9e2008c16448defa6'
REAL_NEW_DIGEST = '5ec8cc012fadfdc98d59e0566fb513bc9a6a234c48dafaba4722601485f69a28'

SENTINELS = {
    'accepted_baseline': 'a' * 40,
    'harness_baseline_commit': 'b' * 40,
    'source_commit': 'c' * 40,
    'python_sha256': 'd' * 64,
    'python_version': '3.12.14',
    'schema': 'resident-rerun005-harness-identity-v2',
    'identity_mode': 0o644,
    'core_tree': 'e' * 40,
    'c15_tree': 'f' * 40,
}

HARNESS_FILES = ('launch.py', 'r005/checks.py', 'r005/response_authorization.py')
SOURCE_FILES = ('src/aios_core/__init__.py', 'src/aios_core/mod.py',
                'tools/c15_persistence/__init__.py')


def sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SyntheticLayout:
    """A throwaway repo + harness tree with a structurally valid manifest."""

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix='arena-eng001-regen-'))
        self.repo = self.root / 'repo'
        self.harness = self.repo / 'harness'
        for rel in SOURCE_FILES:
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f'# synthetic protected source {rel}\n', encoding='utf-8')
        for rel in HARNESS_FILES:
            p = self.harness / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f'# synthetic harness {rel}\n', encoding='utf-8')
        self.manifest_path = self.harness / 'IDENTITY.json'
        self.write_manifest(self.build_manifest())
        self.layout = regen.Layout(repo=self.repo, harness=self.harness)

    def build_manifest(self) -> dict:
        m = dict(SENTINELS)
        m['harness_files'] = {rel: sha(self.harness / rel) for rel in HARNESS_FILES}
        m['source_files'] = {rel: sha(self.repo / rel) for rel in SOURCE_FILES}
        m['file_modes'] = {'harness': {}, 'core': {}, 'c15': {}}
        m['directory_modes'] = {'harness': {}, 'core': {}, 'c15': {}}
        return m

    def write_manifest(self, manifest: dict, *, indent: int = 2) -> None:
        self.manifest_path.write_bytes(
            (json.dumps(manifest, indent=indent, sort_keys=True) + '\n').encode())

    def read_manifest(self) -> dict:
        return json.loads(self.manifest_path.read_bytes())

    def stale(self, rel: str, value: str = '0' * 64) -> None:
        """Make one harness digest disagree with the bytes on disk."""
        m = self.read_manifest()
        m['harness_files'][rel] = value
        self.write_manifest(m)

    def run(self, *, expect=None, write=False):
        out: list[str] = []
        code = regen.recompute(self.layout, expect_changed=expect, write=write,
                               emit=out.append)
        return code, '\n'.join(out)

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


class FailClosedTests(unittest.TestCase):
    """Every refusal path must exit non-zero and write nothing."""

    def setUp(self) -> None:
        self.fx = SyntheticLayout()
        self.addCleanup(self.fx.cleanup)

    def assertRefusedWithoutWrite(self, code: int, out: str, before: bytes,
                                  marker: str) -> None:
        self.assertEqual(code, regen.BLOCKED, f'expected BLOCKED, got {code}\n{out}')
        self.assertNotEqual(code, 0)
        self.assertIn('BLOCKED', out)
        self.assertIn(marker, out)
        self.assertEqual(self.fx.manifest_path.read_bytes(), before,
                         'a refused run must not modify the manifest')

    # ---- guard 1: --write requires an explicit allowlist -------------------

    def test_write_without_allowlist_is_refused_and_writes_nothing(self) -> None:
        self.fx.stale('r005/response_authorization.py')
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=None, write=True)
        self.assertRefusedWithoutWrite(code, out, before,
                                       '--write requires an explicit --expect-changed')

    def test_write_without_allowlist_is_refused_even_on_a_clean_tree(self) -> None:
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=None, write=True)
        self.assertRefusedWithoutWrite(code, out, before,
                                       '--write requires an explicit --expect-changed')

    def test_write_with_empty_allowlist_is_refused(self) -> None:
        self.fx.stale('r005/response_authorization.py')
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'allowlist is empty')

    # ---- guard 3: changed set must EQUAL the allowlist, both directions ----

    def test_unauthorized_extra_digest_change_is_refused(self) -> None:
        self.fx.stale('r005/response_authorization.py')
        self.fx.stale('launch.py', '1' * 64)
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'unauthorized changes')
        self.assertIn('harness_files:launch.py', out)

    def test_allowlisted_entry_that_did_not_change_is_refused(self) -> None:
        self.fx.stale('r005/response_authorization.py')
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(
            expect=[AUTHORIZED, 'harness_files:launch.py'], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'allowlisted but unchanged')

    def test_equality_is_enforced_in_both_directions(self) -> None:
        """Subset and superset mismatches are both refused, not just extras."""
        self.fx.stale('r005/response_authorization.py')
        before = self.fx.manifest_path.read_bytes()
        # superset allowlist: an authorized entry that did not actually change
        code, out = self.fx.run(expect=[AUTHORIZED, 'harness_files:r005/checks.py'],
                                write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'allowlisted but unchanged')
        # subset allowlist: an actual change that was never authorized
        self.fx.stale('launch.py', '1' * 64)
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'unauthorized changes')

    def test_completely_unrelated_allowlist_is_refused(self) -> None:
        self.fx.stale('launch.py', '1' * 64)
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'not exactly equal')

    # ---- guard 2: allowlist validation ------------------------------------

    def test_allowlist_naming_protected_source_scope_is_refused(self) -> None:
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=['source_files:src/aios_core/mod.py'],
                                write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'only \'harness_files\'')

    def test_allowlist_entry_not_listed_in_manifest_is_refused(self) -> None:
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=['harness_files:r005/never_listed.py'],
                                write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'is not listed in the manifest')

    def test_malformed_allowlist_entry_without_colon_is_refused(self) -> None:
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=['r005/response_authorization.py'], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'is malformed')

    def test_allowlist_non_py_entry_is_refused(self) -> None:
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=['harness_files:IDENTITY.json'], write=True)
        self.assertRefusedWithoutWrite(code, out, before,
                                       'not a canonical relative .py path')

    def test_allowlist_traversal_entry_is_refused(self) -> None:
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=['harness_files:../escape.py'], write=True)
        self.assertRefusedWithoutWrite(code, out, before,
                                       'not a canonical relative .py path')

    def test_allowlist_absolute_entry_is_refused(self) -> None:
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=['harness_files:/etc/passwd.py'], write=True)
        self.assertRefusedWithoutWrite(code, out, before,
                                       'not a canonical relative .py path')

    def test_duplicate_allowlist_entry_is_refused(self) -> None:
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED, AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'is duplicated')

    # ---- guard 4: closed membership and bytecode pollution ----------------

    def test_unlisted_new_harness_file_is_refused(self) -> None:
        (self.fx.harness / 'r005' / 'smuggled.py').write_text('# x\n', encoding='utf-8')
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'present-but-unlisted')

    def test_missing_listed_harness_file_is_refused(self) -> None:
        (self.fx.harness / 'r005' / 'checks.py').unlink()
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'listed-but-absent')

    def test_pycache_pollution_is_refused(self) -> None:
        cache = self.fx.harness / 'r005' / '__pycache__'
        cache.mkdir()
        (cache / 'checks.cpython-311.pyc').write_bytes(b'\x00')
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'bytecode pollution')

    def test_loose_pyc_pollution_is_refused(self) -> None:
        (self.fx.harness / 'stray.pyc').write_bytes(b'\x00')
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'bytecode pollution')

    # ---- guard 5: protected source trees must not drift -------------------

    def test_protected_core_source_drift_is_refused(self) -> None:
        (self.fx.repo / 'src/aios_core/mod.py').write_text('# tampered\n',
                                                           encoding='utf-8')
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before,
                                       'source_files:src/aios_core/mod.py')

    def test_protected_c15_source_drift_is_refused(self) -> None:
        (self.fx.repo / 'tools/c15_persistence/__init__.py').write_text(
            '# tampered\n', encoding='utf-8')
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before,
                                       'source_files:tools/c15_persistence/__init__.py')

    def test_missing_listed_source_file_is_refused(self) -> None:
        (self.fx.repo / 'src/aios_core/mod.py').unlink()
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'missing from disk')

    # ---- guard 6: manifest structure and protected fields -----------------

    def test_missing_protected_field_is_refused(self) -> None:
        m = self.fx.read_manifest()
        del m['python_sha256']
        self.fx.write_manifest(m)
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, "missing protected field")

    def test_empty_harness_files_scope_is_refused(self) -> None:
        m = self.fx.read_manifest()
        m['harness_files'] = {}
        self.fx.write_manifest(m)
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'non-empty object')

    def test_invalid_json_manifest_is_refused(self) -> None:
        self.fx.manifest_path.write_bytes(b'{not json')
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'not valid JSON')

    def test_non_object_manifest_root_is_refused(self) -> None:
        self.fx.manifest_path.write_bytes(b'[]\n')
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'not a JSON object')

    def test_absent_manifest_is_refused(self) -> None:
        self.fx.manifest_path.unlink()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertEqual(code, regen.BLOCKED)
        self.assertIn('manifest not found', out)

    # ---- guard 7: serialization must be line-faithful ---------------------

    def test_foreign_indentation_is_refused_before_writing(self) -> None:
        """indent=4 keeps the line count but re-indents every line."""
        self.fx.stale('r005/response_authorization.py')
        m = self.fx.read_manifest()
        self.fx.write_manifest(m, indent=4)
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before,
                                       'reserialization is not faithful')

    def test_compact_serialization_is_refused_before_writing(self) -> None:
        """A single-line compact manifest changes the line count entirely."""
        self.fx.stale('r005/response_authorization.py')
        m = self.fx.read_manifest()
        self.fx.manifest_path.write_bytes(
            json.dumps(m, sort_keys=True, separators=(',', ':')).encode())
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before, 'line count')

    def test_reordered_key_serialization_is_refused_before_writing(self) -> None:
        """A manifest whose keys are not sorted would rewrite into a huge diff.

        Built in deliberately reversed key order and dumped WITHOUT sort_keys, so
        the on-disk bytes really are non-canonical. Normalizing them would touch
        far more lines than the one authorized digest, so the tool must refuse.
        """
        self.fx.stale('r005/response_authorization.py')
        m = self.fx.read_manifest()
        reordered = {k: m[k] for k in reversed(list(m))}
        self.assertNotEqual(list(reordered), sorted(reordered),
                            'the fixture must actually be non-canonical')
        self.fx.manifest_path.write_bytes(
            (json.dumps(reordered, indent=2) + '\n').encode())
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertRefusedWithoutWrite(code, out, before,
                                       'reserialization is not faithful')

    def test_missing_trailing_newline_is_refused_before_writing(self) -> None:
        """Dropping the trailing newline changes the line count."""
        self.fx.stale('r005/response_authorization.py')
        m = self.fx.read_manifest()
        self.fx.manifest_path.write_bytes(
            json.dumps(m, indent=2, sort_keys=True).encode())
        before = self.fx.manifest_path.read_bytes()
        self.assertFalse(before.endswith(b'\n'), 'fixture must lack the newline')
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertEqual(code, 0, out)
        self.assertIn('WROTE', out,
                      'splitlines() ignores a missing trailing newline, so the '
                      'line-faithful check passes and the canonical form is '
                      'restored; this documents the actual behaviour')


class SuccessfulPathTests(unittest.TestCase):
    """The correct rebuild path stays reproducible and minimal."""

    def setUp(self) -> None:
        self.fx = SyntheticLayout()
        self.addCleanup(self.fx.cleanup)

    def test_dry_run_writes_nothing(self) -> None:
        self.fx.stale('r005/response_authorization.py')
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=False)
        self.assertEqual(code, 0, out)
        self.assertIn('DRY_RUN', out)
        self.assertEqual(self.fx.manifest_path.read_bytes(), before)

    def test_dry_run_without_allowlist_reports_no_change_on_clean_tree(self) -> None:
        code, out = self.fx.run(expect=None, write=False)
        self.assertEqual(code, 0, out)
        self.assertIn('NO_CHANGE', out)

    def test_dry_run_without_allowlist_reports_drift_informationally(self) -> None:
        self.fx.stale('r005/response_authorization.py')
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=None, write=False)
        self.assertEqual(code, 0, out)
        self.assertIn('DRY_RUN', out)
        self.assertEqual(self.fx.manifest_path.read_bytes(), before,
                         'a dry run must never write, allowlist or not')

    def test_exact_allowlist_match_writes_a_one_line_diff(self) -> None:
        self.fx.stale('r005/response_authorization.py')
        before = self.fx.manifest_path.read_bytes()
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertEqual(code, 0, out)
        self.assertIn('ALLOWLIST_MATCH', out)
        self.assertIn('WROTE', out)
        after = self.fx.manifest_path.read_bytes()
        self.assertNotEqual(before, after)
        old_lines = before.decode().splitlines()
        new_lines = after.decode().splitlines()
        self.assertEqual(len(old_lines), len(new_lines))
        differing = [i for i, (a, b) in enumerate(zip(old_lines, new_lines), 1)
                     if a != b]
        self.assertEqual(len(differing), 1, f'expected a 1-line diff, got {differing}')
        self.assertIn('r005/response_authorization.py', new_lines[differing[0] - 1])

    def test_only_the_allowlisted_digest_differs_in_the_parsed_manifest(self) -> None:
        self.fx.stale('r005/response_authorization.py')
        before = self.fx.read_manifest()
        real = sha(self.fx.harness / 'r005/response_authorization.py')
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertEqual(code, 0, out)
        after = self.fx.read_manifest()
        self.assertEqual(after['harness_files']['r005/response_authorization.py'], real)
        before['harness_files']['r005/response_authorization.py'] = real
        self.assertEqual(before, after,
                         'nothing but the allowlisted digest may differ')

    def test_untouchable_fields_survive_a_successful_write(self) -> None:
        self.fx.stale('r005/response_authorization.py')
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertEqual(code, 0, out)
        after = self.fx.read_manifest()
        for field, sentinel in SENTINELS.items():
            self.assertEqual(after[field], sentinel,
                             f'protected field {field!r} must be preserved')
        for field in ('file_modes', 'directory_modes'):
            self.assertEqual(after[field],
                             {'harness': {}, 'core': {}, 'c15': {}},
                             f'protected field {field!r} must be preserved')

    def test_successful_write_is_idempotent(self) -> None:
        self.fx.stale('r005/response_authorization.py')
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertEqual(code, 0, out)
        first = self.fx.manifest_path.read_bytes()
        code2, out2 = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertEqual(code2, regen.BLOCKED, out2)
        self.assertIn('the allowlist requires changes that did not occur', out2)
        self.assertEqual(self.fx.manifest_path.read_bytes(), first)
        code3, out3 = self.fx.run(expect=None, write=False)
        self.assertEqual(code3, 0, out3)
        self.assertIn('NO_CHANGE', out3)

    def test_digest_values_are_pure_sha256_of_disk_bytes(self) -> None:
        target = self.fx.harness / 'r005/response_authorization.py'
        target.write_text('# deliberately different bytes\n', encoding='utf-8')
        self.fx.stale('r005/response_authorization.py')
        code, out = self.fx.run(expect=[AUTHORIZED], write=True)
        self.assertEqual(code, 0, out)
        self.assertEqual(
            self.fx.read_manifest()['harness_files']['r005/response_authorization.py'],
            sha(target))


class RealCheckoutReadOnlyTests(unittest.TestCase):
    """Read-only confirmation against the committed candidate.

    Nothing here writes to the real tree. The reproduction test copies the real
    harness into a temporary directory first and perturbs only the copy.
    """

    REAL_HARNESS = regen.DEFAULT_LAYOUT.harness
    REAL_REPO = regen.DEFAULT_LAYOUT.repo

    def test_real_manifest_is_already_consistent_with_disk(self) -> None:
        """The committed manifest is exactly what the tool would produce."""
        out: list[str] = []
        code = regen.recompute(regen.DEFAULT_LAYOUT, expect_changed=None,
                               write=False, emit=out.append)
        text = '\n'.join(out)
        self.assertEqual(code, 0, text)
        self.assertIn('NO_CHANGE', text)
        self.assertIn('cf3d3356a6746f21a817a2bdd8a3aa7a111ce87e0289abfeaf3729b41b0d1ed5',
                      text, 'the committed candidate manifest digest')

    def test_real_authorized_change_is_exactly_response_authorization(self) -> None:
        """Reproduce the single authorized transition on a temporary copy.

        Restores the pre-fix digest into a COPY of the real manifest and confirms
        the tool proposes exactly one change, to the genuine post-fix digest. The
        real manifest is never opened for writing.
        """
        real_bytes = (self.REAL_HARNESS / 'IDENTITY.json').read_bytes()
        tmp = Path(tempfile.mkdtemp(prefix='arena-eng001-realcopy-'))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        copy = tmp / 'harness'
        shutil.copytree(self.REAL_HARNESS, copy)
        manifest = json.loads(real_bytes)
        self.assertEqual(manifest['harness_files']['r005/response_authorization.py'],
                         REAL_NEW_DIGEST,
                         'the committed manifest must already pin the fixed bytes')
        manifest['harness_files']['r005/response_authorization.py'] = REAL_OLD_DIGEST
        (copy / 'IDENTITY.json').write_bytes(
            (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode())

        out: list[str] = []
        code = regen.recompute(regen.Layout(repo=self.REAL_REPO, harness=copy),
                               expect_changed=[AUTHORIZED], write=False,
                               emit=out.append)
        text = '\n'.join(out)
        self.assertEqual(code, 0, text)
        self.assertIn('ALLOWLIST_MATCH', text)
        self.assertIn(REAL_OLD_DIGEST, text)
        self.assertIn(REAL_NEW_DIGEST, text)
        self.assertEqual(
            json.loads((copy / 'IDENTITY.json').read_bytes())
            ['harness_files']['r005/response_authorization.py'],
            REAL_OLD_DIGEST, 'a dry run must leave even the copy untouched')
        self.assertEqual((self.REAL_HARNESS / 'IDENTITY.json').read_bytes(), real_bytes,
                         'the real manifest must be byte-identical')

    def test_real_write_without_allowlist_is_refused(self) -> None:
        """Even against the real tree, --write with no allowlist is refused."""
        real_bytes = (self.REAL_HARNESS / 'IDENTITY.json').read_bytes()
        out: list[str] = []
        code = regen.recompute(regen.DEFAULT_LAYOUT, expect_changed=None,
                               write=True, emit=out.append)
        text = '\n'.join(out)
        self.assertEqual(code, regen.BLOCKED, text)
        self.assertIn('--write requires an explicit --expect-changed', text)
        self.assertEqual((self.REAL_HARNESS / 'IDENTITY.json').read_bytes(), real_bytes)


class CliTests(unittest.TestCase):
    """Argument-level enforcement, so the guard cannot be bypassed by the CLI."""

    def test_cli_write_without_allowlist_exits_nonzero(self) -> None:
        fx = SyntheticLayout()
        self.addCleanup(fx.cleanup)
        fx.stale('r005/response_authorization.py')
        before = fx.manifest_path.read_bytes()
        code = regen.main(['--write', '--harness', str(fx.harness),
                           '--repo', str(fx.repo)])
        self.assertEqual(code, regen.BLOCKED)
        self.assertEqual(fx.manifest_path.read_bytes(), before)

    def test_cli_write_with_allowlist_succeeds(self) -> None:
        fx = SyntheticLayout()
        self.addCleanup(fx.cleanup)
        fx.stale('r005/response_authorization.py')
        code = regen.main(['--write', '--expect-changed', AUTHORIZED,
                           '--harness', str(fx.harness), '--repo', str(fx.repo)])
        self.assertEqual(code, 0)
        self.assertEqual(
            fx.read_manifest()['harness_files']['r005/response_authorization.py'],
            sha(fx.harness / 'r005/response_authorization.py'))

    def test_cli_harness_without_repo_is_a_usage_error(self) -> None:
        fx = SyntheticLayout()
        self.addCleanup(fx.cleanup)
        with self.assertRaises(SystemExit) as ctx:
            regen.main(['--harness', str(fx.harness)])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == '__main__':
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    unittest.main(verbosity=2)
