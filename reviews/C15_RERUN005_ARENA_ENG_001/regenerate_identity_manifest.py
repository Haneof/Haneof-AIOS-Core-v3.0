#!/usr/bin/env python3
"""Recompute ONLY the allowlisted file-digest entries of harness/IDENTITY.json.

DEVELOPMENT_ONLY / FORMAL_VALIDATION_NOT_PERFORMED / DO_NOT_MERGE

WHY THIS SCRIPT EXISTS
----------------------
Issue #388 and the Option-B PM authorization require the new candidate's derived
identity pins to be updated "through the established reproducible build process",
which is ``reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66/build_delivery.py``.

That builder **verifies** the harness tree against the existing manifest and then
packs it; it does **not** produce the manifest. Run against a modified harness
file it fails closed with:

    IdentityBlocked: BLOCKED / PROTECTED_BYTE_IDENTITY_DRIFT:
                     harness/r005/response_authorization.py

No committed tool in this repository generates ``IDENTITY.json``, so exactly one
step precedes the builder: refreshing the manifest's per-file digests. This script
performs that step in the narrowest auditable way and is committed as evidence of
HOW the new pins were derived, so anyone can recompute the same values.

FAIL-CLOSED CONTRACT (hardened per PM review 2026-10-17T12:19:01Z)
------------------------------------------------------------------
``--write`` is refused unless an explicit allowlist of entries permitted to change
is supplied via ``--expect-changed``, and the set of digests that actually differ
must be **exactly equal** to that allowlist -- not merely a subset of it. Every
rejection path returns non-zero **before** any byte is written; the manifest is
written only as the final action of a fully successful run.

It refuses, without writing, when any of the following holds:

1. ``--write`` is given with no ``--expect-changed`` allowlist.
2. An allowlist entry is malformed, names a scope other than ``harness_files``,
   is not a canonical relative ``.py`` path, or is not a listed manifest entry.
3. The set of changed digests differs from the allowlist in **either** direction:
   an unauthorized extra digest changed, or an allowlisted digest did not change.
4. Harness tree membership changed in either direction (the manifest is a closed
   set), or any ``__pycache__``/``*.pyc`` bytecode pollution is present.
5. Any ``src/aios_core/**`` or ``tools/c15_persistence/**`` digest drifted, or any
   listed file is missing from disk.
6. Any protected provenance/runtime/structure field would change.
7. Reserialization is not line-faithful (same line count, differing lines exactly
   the changed digest lines), so the diff could not be reviewed as minimal.

WHAT IT NEVER INVENTS
---------------------
Digests are pure ``sha256`` of the bytes on disk. These eleven fields are never
added, removed or edited, and are asserted byte-identical after reserialization:

``accepted_baseline``, ``harness_baseline_commit``, ``source_commit``,
``python_sha256``, ``python_version``, ``schema``, ``identity_mode``,
``core_tree``, ``c15_tree``, ``file_modes``, ``directory_modes``.

Serialization is reproduced exactly (``indent=2``, ``sort_keys=True``, trailing
newline), so a successful run yields one changed line per allowlisted digest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

REPO = Path(__file__).resolve().parents[2]
BASE = (REPO / 'reviews/internal_habitation/c15-rcc/v1/operator_prep'
             / 'C15-RCC-RES-A-RERUN-005')
HARNESS = BASE / 'harness'

#: Result codes. Anything non-zero means "refused; nothing was written".
OK = 0
NO_CHANGE = 0
BLOCKED = 2

#: Fields this script must never modify. Preserved unchanged on the new candidate:
#: all three provenance commits resolve from the GitHub Git Commit API (see the
#: engineering report's provenance section) and describe inherited lineage that a
#: two-line ``load_grant`` guard does not alter.
UNTOUCHABLE = ('accepted_baseline', 'harness_baseline_commit', 'source_commit',
               'python_sha256', 'python_version', 'schema', 'identity_mode',
               'core_tree', 'c15_tree', 'file_modes', 'directory_modes')

#: The only manifest scope whose digests may ever be refreshed by this tool.
MUTABLE_SCOPE = 'harness_files'

#: Scopes that must never drift and must never be allowlisted.
PROTECTED_SCOPES = ('source_files',)


class Layout:
    """Where the manifest and the trees it pins live.

    Parameterized so the fail-closed behaviour can be exercised against throwaway
    synthetic directories instead of the real frozen artifacts. Deliberately a
    plain class rather than a ``dataclass``: this module is loaded through
    ``importlib`` by the tests, and ``dataclasses`` needs the module registered in
    ``sys.modules`` to resolve annotations.
    """

    __slots__ = ('repo', 'harness')

    def __init__(self, repo: Path, harness: Path) -> None:
        self.repo = Path(repo)
        self.harness = Path(harness)

    @property
    def manifest(self) -> Path:
        return self.harness / 'IDENTITY.json'

    def __eq__(self, other) -> bool:
        return (isinstance(other, Layout) and self.repo == other.repo
                and self.harness == other.harness)

    def __hash__(self) -> int:
        return hash((self.repo, self.harness))

    def __repr__(self) -> str:
        return f'Layout(repo={self.repo!r}, harness={self.harness!r})'


DEFAULT_LAYOUT = Layout(repo=REPO, harness=HARNESS)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def serialize(manifest: dict) -> bytes:
    """Reproduce the established manifest serialization byte-for-byte."""
    return (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()


def is_canonical_relative_py(rel: str) -> bool:
    """A plain relative POSIX .py path with no traversal or drive/absolute form."""
    if not isinstance(rel, str) or not rel or not rel.endswith('.py'):
        return False
    if rel.startswith('/') or '\\' in rel or '\x00' in rel:
        return False
    parts = rel.split('/')
    return all(p and p not in ('.', '..') for p in parts)


def actual_python_files(root: Path) -> set[Path]:
    """Every real .py under root, ignoring bytecode directories."""
    return {p for p in root.rglob('*.py')
            if p.is_file() and '__pycache__' not in p.parts}


def bytecode_pollution(root: Path) -> list[str]:
    """Bytecode artifacts inside the identity-pinned tree (a known identity trap)."""
    found = []
    for p in root.rglob('__pycache__'):
        found.append(str(p.relative_to(root)))
    for p in root.rglob('*.pyc'):
        if '__pycache__' not in p.parts:
            found.append(str(p.relative_to(root)))
    return sorted(found)


def parse_allowlist(entries: list[str] | None) -> tuple[list[tuple[str, str]] | None, str | None]:
    """Validate --expect-changed entries. Returns (parsed, error)."""
    if entries is None:
        return None, None
    parsed: list[tuple[str, str]] = []
    for raw in entries:
        scope, sep, rel = raw.partition(':')
        if not sep:
            return None, (f'allowlist entry {raw!r} is malformed; expected SCOPE:REL '
                          f'where SCOPE is {MUTABLE_SCOPE!r}')
        if scope != MUTABLE_SCOPE:
            return None, (f'allowlist entry {raw!r} names scope {scope!r}; only '
                          f'{MUTABLE_SCOPE!r} may ever be refreshed. '
                          f'{"/".join(PROTECTED_SCOPES)} digests are protected and must '
                          f'never change in this corrective.')
        if not is_canonical_relative_py(rel):
            return None, f'allowlist entry {raw!r} is not a canonical relative .py path'
        if (scope, rel) in parsed:
            return None, f'allowlist entry {raw!r} is duplicated'
        parsed.append((scope, rel))
    if not parsed:
        return None, 'allowlist is empty'
    return parsed, None


def recompute(layout: Layout = DEFAULT_LAYOUT, *,
              expect_changed: list[str] | None = None,
              write: bool = False,
              emit=print) -> int:
    """Recompute allowlisted manifest digests. Returns a process exit code.

    Every rejection path returns before any write; ``write`` only takes effect on
    a fully successful run.
    """
    allowlist, error = parse_allowlist(expect_changed)
    if error is not None:
        emit(f'BLOCKED: {error}')
        return BLOCKED

    # -- guard 1: --write is meaningless and dangerous without an allowlist
    if write and allowlist is None:
        emit('BLOCKED: --write requires an explicit --expect-changed allowlist.')
        emit('  Refusing to rewrite an identity manifest without naming, in advance, '
             'exactly which digest entries are authorized to change. The changed set '
             'must then equal that allowlist exactly.')
        emit(f'  For this corrective the only authorized entry is: '
             f'{MUTABLE_SCOPE}:r005/response_authorization.py')
        return BLOCKED

    manifest_path = layout.manifest
    if not manifest_path.is_file():
        emit(f'BLOCKED: manifest not found: {manifest_path}')
        return BLOCKED

    original_bytes = manifest_path.read_bytes()
    try:
        manifest = json.loads(original_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        emit(f'BLOCKED: manifest is not valid JSON: {exc}')
        return BLOCKED
    if not isinstance(manifest, dict):
        emit('BLOCKED: manifest root is not a JSON object')
        return BLOCKED
    original = json.loads(original_bytes)

    # -- guard: required structure present before anything is trusted
    for field in UNTOUCHABLE:
        if field not in manifest:
            emit(f'BLOCKED: manifest is missing protected field {field!r}')
            return BLOCKED
    for field in (MUTABLE_SCOPE, *PROTECTED_SCOPES):
        if not isinstance(manifest.get(field), dict) or not manifest[field]:
            emit(f'BLOCKED: manifest field {field!r} must be a non-empty object')
            return BLOCKED

    # -- guard: allowlist must name entries the manifest actually lists
    if allowlist is not None:
        for scope, rel in allowlist:
            if rel not in manifest[scope]:
                emit(f'BLOCKED: allowlist entry {scope}:{rel} is not listed in the '
                     f'manifest; the manifest is a closed set and this tool never '
                     f'adds or removes entries')
                return BLOCKED

    # -- guard 4: bytecode pollution inside the identity-pinned tree
    pollution = bytecode_pollution(layout.harness)
    if pollution:
        emit('BLOCKED: bytecode pollution inside the identity-pinned harness tree: '
             f'{pollution}')
        emit('  Remove __pycache__/*.pyc and re-run; launch.py rejects these as '
             'UNAPPROVED_OR_REPLACED_DIRECTORY.')
        return BLOCKED

    # -- guard 4: harness membership is a closed set, both directions
    listed = {layout.harness / rel for rel in manifest[MUTABLE_SCOPE]}
    present = actual_python_files(layout.harness)
    if listed != present:
        emit('BLOCKED: harness tree membership changed; the manifest is a closed set')
        emit('  listed-but-absent   : '
             f'{sorted(str(p.relative_to(layout.harness)) for p in listed - present)}')
        emit('  present-but-unlisted: '
             f'{sorted(str(p.relative_to(layout.harness)) for p in present - listed)}')
        return BLOCKED

    # -- guard 5: protected source trees must not have drifted
    missing: list[str] = []
    for rel, pinned in sorted(manifest['source_files'].items()):
        path = layout.repo / rel
        if not path.is_file():
            missing.append(f'source_files:{rel}')
            continue
        actual = sha256_bytes(path.read_bytes())
        if actual != pinned:
            emit(f'BLOCKED: protected source file drifted: source_files:{rel}')
            emit('  src/aios_core/** and tools/c15_persistence/** must not change in '
                 'this corrective; refuse to absorb the drift into the manifest.')
            return BLOCKED

    # -- compute the harness digests that genuinely differ
    changed: dict[str, tuple[str, str]] = {}
    for rel, pinned in sorted(manifest[MUTABLE_SCOPE].items()):
        path = layout.harness / rel
        if not path.is_file():
            missing.append(f'{MUTABLE_SCOPE}:{rel}')
            continue
        actual = sha256_bytes(path.read_bytes())
        if actual != pinned:
            changed[f'{MUTABLE_SCOPE}:{rel}'] = (pinned, actual)
            manifest[MUTABLE_SCOPE][rel] = actual

    if missing:
        emit(f'BLOCKED: listed files are missing from disk: {sorted(missing)}')
        return BLOCKED

    # -- guard 6: protected fields untouched, proved on values not intent
    for field in UNTOUCHABLE:
        if manifest[field] != original[field]:
            emit(f'BLOCKED: protected field {field!r} would have been modified')
            return BLOCKED

    if not changed:
        emit('NO_CHANGE: every manifest digest already matches the bytes on disk')
        emit(f'  IDENTITY.json sha256 = {sha256_bytes(original_bytes)}')
        if allowlist is not None:
            emit('BLOCKED: the allowlist requires changes that did not occur: '
                 f'{sorted(f"{s}:{r}" for s, r in allowlist)}')
            return BLOCKED
        if write:
            emit('NOTHING_TO_WRITE: no digest differs, so no write is performed')
        return NO_CHANGE

    emit('Digest entries that genuinely changed:')
    for name, (old, new) in sorted(changed.items()):
        emit(f'  {name}\n    old = {old}\n    new = {new}')

    # -- guard 3: changed set must EQUAL the allowlist, in both directions
    if allowlist is not None:
        expected = {f'{scope}:{rel}' for scope, rel in allowlist}
        actual_set = set(changed)
        unauthorized = actual_set - expected
        absent = expected - actual_set
        if unauthorized or absent:
            emit('BLOCKED: changed digest set is not exactly equal to the allowlist')
            if unauthorized:
                emit(f'  unauthorized changes : {sorted(unauthorized)}')
            if absent:
                emit(f'  allowlisted but unchanged: {sorted(absent)}')
            return BLOCKED
        emit(f'ALLOWLIST_MATCH: changed set == allowlist == {sorted(actual_set)}')

    new_bytes = serialize(manifest)

    # -- guard 7: reserialization must be line-faithful
    old_lines = original_bytes.decode().splitlines()
    new_lines = new_bytes.decode().splitlines()
    if len(old_lines) != len(new_lines):
        emit('BLOCKED: reserialization changed the manifest line count '
             f'({len(old_lines)} -> {len(new_lines)}); the on-disk manifest is not in '
             'the expected serialization (indent=2, sort_keys=True, trailing newline) '
             'and rewriting it would produce an unreviewable diff')
        return BLOCKED
    differing = [i for i, (a, b) in enumerate(zip(old_lines, new_lines), 1) if a != b]
    if len(differing) != len(changed):
        emit(f'BLOCKED: {len(differing)} lines differ but only {len(changed)} digests '
             'changed; reserialization is not faithful')
        return BLOCKED

    # Each differing line must be a digest line whose KEY is unchanged and whose
    # old/new values are exactly the 64-hex digests of one allowlisted entry.
    hex64 = set('0123456789abcdef')
    expected_pairs = {(old, new) for old, new in changed.values()}
    seen_pairs: set[tuple[str, str]] = set()
    for i in differing:
        old_line, new_line = old_lines[i - 1], new_lines[i - 1]
        old_key, old_sep, old_val = old_line.partition(':')
        new_key, new_sep, new_val = new_line.partition(':')
        if not old_sep or not new_sep or old_key != new_key:
            emit(f'BLOCKED: differing line {i} changes a key, not a digest value')
            return BLOCKED
        old_digest = old_val.strip().strip('",')
        new_digest = new_val.strip().strip('",')
        for digest in (old_digest, new_digest):
            if len(digest) != 64 or any(c not in hex64 for c in digest):
                emit(f'BLOCKED: differing line {i} does not hold a 64-hex digest')
                return BLOCKED
        if (old_digest, new_digest) not in expected_pairs:
            emit(f'BLOCKED: differing line {i} carries an unexpected digest transition '
                 f'{old_digest[:12]}... -> {new_digest[:12]}...')
            return BLOCKED
        seen_pairs.add((old_digest, new_digest))
    if seen_pairs != expected_pairs:
        emit('BLOCKED: the differing lines do not account for every changed digest')
        return BLOCKED

    # -- guard 6 (second pass): re-read the serialized form and re-assert
    reserialized = json.loads(new_bytes)
    for field in UNTOUCHABLE:
        if reserialized[field] != original[field]:
            emit(f'BLOCKED: protected field {field!r} differs after reserialization')
            return BLOCKED
    if set(reserialized[MUTABLE_SCOPE]) != set(original[MUTABLE_SCOPE]):
        emit('BLOCKED: harness_files membership differs after reserialization')
        return BLOCKED
    if set(reserialized['source_files']) != set(original['source_files']):
        emit('BLOCKED: source_files membership differs after reserialization')
        return BLOCKED

    emit(f'\nline-level diff is exactly {len(differing)} line(s): {differing}')
    emit(f'old IDENTITY.json sha256 = {sha256_bytes(original_bytes)}')
    emit(f'new IDENTITY.json sha256 = {sha256_bytes(new_bytes)}')

    if not write:
        emit('DRY_RUN: nothing written (pass --write with an --expect-changed '
             'allowlist to apply)')
        return OK

    # -- the only write in the program, reached solely after every guard passed
    manifest_path.write_bytes(new_bytes)
    emit(f'WROTE {manifest_path}')
    emit('Next: run the established builder to regenerate the artifact, member '
         'inventory, launch packet and build receipt:')
    emit('  python -B reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66/build_delivery.py')
    return OK


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--write', action='store_true',
                        help='apply the recomputed digests; REQUIRES --expect-changed. '
                             'Default is a dry run that writes nothing.')
    parser.add_argument('--expect-changed', action='append', default=None,
                        metavar='harness_files:REL',
                        help='digest entry authorized to change, e.g. '
                             'harness_files:r005/response_authorization.py. The changed '
                             'set must equal the union of these entries exactly. '
                             'Repeatable. Mandatory with --write.')
    parser.add_argument('--harness', default=None, metavar='DIR',
                        help='override the harness root (used by the fail-closed tests '
                             'to exercise throwaway synthetic directories)')
    parser.add_argument('--repo', default=None, metavar='DIR',
                        help='override the repository root, paired with --harness')
    args = parser.parse_args(argv)

    if (args.harness is None) != (args.repo is None):
        parser.error('--harness and --repo must be given together')
    layout = (Layout(repo=Path(args.repo).resolve(), harness=Path(args.harness).resolve())
              if args.harness else DEFAULT_LAYOUT)

    return recompute(layout, expect_changed=args.expect_changed, write=args.write)


if __name__ == '__main__':
    raise SystemExit(main())
