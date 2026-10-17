#!/usr/bin/env python3
"""Recompute ONLY the derivable file-digest entries of harness/IDENTITY.json.

DEVELOPMENT_ONLY / FORMAL_VALIDATION_NOT_PERFORMED / DO_NOT_MERGE

WHY THIS SCRIPT EXISTS
----------------------
Issue #388 / the Option-B PM authorization require the new candidate's derived
identity pins to be updated "through the established reproducible build process".
That process is ``reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66/build_delivery.py``.

Empirically, ``build_delivery.py`` **verifies** the harness tree against the
existing manifest and then packs it; it does **not** produce the manifest. Run
against a modified harness file it fails closed with:

    IdentityBlocked: BLOCKED / PROTECTED_BYTE_IDENTITY_DRIFT:
                     harness/r005/response_authorization.py

So exactly one step precedes it: refreshing the manifest's per-file digests.
No committed tool in this repository does that, so this script performs it in
the narrowest possible auditable way and is committed as evidence of HOW the
new pins were derived. Anyone can re-run it and recompute the same values.

WHAT IT WILL AND WILL NOT DO
----------------------------
It recomputes ``sha256`` for the entries already listed in ``harness_files`` and
``source_files`` from the bytes on disk, and rewrites **only** those digest
strings whose file actually changed.

It never invents, adds, removes or edits anything else. In particular these
provenance/runtime fields are left byte-identical, because they are NOT derivable
in an unprivileged sandbox and preserving them is what the PM authorization
instructed:

* ``python_version`` / ``python_sha256`` - the approved Python 3.12.14 binary is
  absent here, so the pin cannot be re-verified locally. Preserved per
  authorization; MUST be re-confirmed on the approved-runtime host.
* ``accepted_baseline``, ``harness_baseline_commit``, ``source_commit`` - these
  name git objects that exist only in the Operator Codespace's local repository
  and were never pushed to GitHub, so no new value could be computed here
  without inventing one. Preserved, consistent with the recorded Window57
  precedent that "the manifest/source_commit provenance remains unchanged; it
  describes the inherited source lineage, not the final evidence-commit SHA".
* ``schema``, ``identity_mode``, ``core_tree``, ``c15_tree``, ``file_modes``,
  ``directory_modes`` - unchanged inputs; verified, not rewritten.

It FAILS CLOSED (non-zero exit, no write) if:
* a listed file is missing, or an unlisted ``.py`` file appears in the tree;
* any digest that would change belongs to a file outside the authorized change;
* the reserialized manifest would differ in anything but the changed digests.

Serialization is reproduced exactly (``indent=2``, ``sort_keys=True``, trailing
newline), so the diff is one line per genuinely changed file.
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
MANIFEST = HARNESS / 'IDENTITY.json'

#: Fields this script must never modify.
UNTOUCHABLE = ('accepted_baseline', 'harness_baseline_commit', 'source_commit',
               'python_sha256', 'python_version', 'schema', 'identity_mode',
               'core_tree', 'c15_tree', 'file_modes', 'directory_modes')


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def serialize(manifest: dict) -> bytes:
    return (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()


def expected_paths(scope: str, entries: dict) -> set[Path]:
    """The on-disk paths a manifest scope is supposed to cover exactly."""
    if scope == 'harness':
        return {HARNESS / rel for rel in entries}
    return {REPO / rel for rel in entries}


def actual_python_files(root: Path) -> set[Path]:
    return {p for p in root.rglob('*.py') if p.is_file() and '__pycache__' not in p.parts}


def recompute(*, expect_changed: set[str] | None = None, write: bool = False) -> int:
    original_bytes = MANIFEST.read_bytes()
    manifest = json.loads(original_bytes)
    original = json.loads(original_bytes)

    for field in UNTOUCHABLE:
        if field not in manifest:
            print(f'BLOCKED: manifest is missing required field {field!r}')
            return 2

    # -- closed-set check: the manifest must still describe exactly these trees
    harness_listed = expected_paths('harness', manifest['harness_files'])
    harness_actual = actual_python_files(HARNESS)
    if harness_listed != harness_actual:
        print('BLOCKED: harness tree membership changed; the manifest is a closed set')
        print(f'  listed-but-absent : {sorted(str(p) for p in harness_listed - harness_actual)}')
        print(f'  present-but-unlisted: {sorted(str(p) for p in harness_actual - harness_listed)}')
        return 2

    changed: dict[str, tuple[str, str]] = {}
    missing: list[str] = []
    for scope, key, root in (('harness', 'harness_files', HARNESS),):
        for rel, pinned in sorted(manifest[key].items()):
            path = root / rel
            if not path.is_file():
                missing.append(f'{key}:{rel}')
                continue
            actual = sha256_bytes(path.read_bytes())
            if actual != pinned:
                changed[f'{key}:{rel}'] = (pinned, actual)
                manifest[key][rel] = actual

    # source_files covers src/aios_core and tools/c15_persistence, which this
    # corrective does not touch. Verify them; refuse if any differ.
    for rel, pinned in sorted(manifest['source_files'].items()):
        path = REPO / rel
        if not path.is_file():
            missing.append(f'source_files:{rel}')
            continue
        actual = sha256_bytes(path.read_bytes())
        if actual != pinned:
            print(f'BLOCKED: protected source file drifted: source_files:{rel}')
            print('  src/aios_core/** and tools/c15_persistence/** must not change '
                  'in this corrective; refuse to absorb the drift into the manifest.')
            return 2

    if missing:
        print(f'BLOCKED: listed files are missing: {missing}')
        return 2

    # -- untouched-field guard, proved on the serialized bytes, not on intent
    for field in UNTOUCHABLE:
        if manifest[field] != original[field]:
            print(f'BLOCKED: {field} would have been modified')
            return 2

    if not changed:
        print('NO_CHANGE: every manifest digest already matches the bytes on disk')
        print(f'  IDENTITY.json sha256 = {sha256_bytes(original_bytes)}')
        return 0

    print('Digest entries that genuinely changed:')
    for name, (old, new) in sorted(changed.items()):
        print(f'  {name}\n    old = {old}\n    new = {new}')

    if expect_changed is not None:
        unexpected = set(changed) - expect_changed
        if unexpected:
            print(f'BLOCKED: unexpected digest changes outside the authorized scope: '
                  f'{sorted(unexpected)}')
            return 2

    new_bytes = serialize(manifest)
    # Prove the reserialization touched nothing but the changed digest lines.
    old_lines = original_bytes.decode().splitlines()
    new_lines = new_bytes.decode().splitlines()
    if len(old_lines) != len(new_lines):
        print('BLOCKED: reserialization changed the manifest line count')
        return 2
    differing = [i for i, (a, b) in enumerate(zip(old_lines, new_lines), 1) if a != b]
    if len(differing) != len(changed):
        print(f'BLOCKED: {len(differing)} lines differ but only {len(changed)} digests '
              f'changed; reserialization is not faithful')
        return 2

    print(f'\nline-level diff is exactly {len(differing)} line(s): {differing}')
    print(f'old IDENTITY.json sha256 = {sha256_bytes(original_bytes)}')
    print(f'new IDENTITY.json sha256 = {sha256_bytes(new_bytes)}')

    if write:
        MANIFEST.write_bytes(new_bytes)
        print('WROTE harness/IDENTITY.json')
        print('Next: run the established builder to regenerate the artifact, '
              'member inventory, launch packet and build receipt:')
        print('  python -B reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66/build_delivery.py')
    else:
        print('DRY_RUN: nothing written (pass --write to apply)')
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--write', action='store_true',
                        help='apply the recomputed digests (default is a dry run)')
    parser.add_argument('--expect-changed', action='append', default=None,
                        metavar='SCOPE:REL',
                        help='digest entry that is authorized to change, e.g. '
                             'harness_files:r005/response_authorization.py; '
                             'any other change fails closed. Repeatable.')
    args = parser.parse_args(argv)
    expected = set(args.expect_changed) if args.expect_changed else None
    return recompute(expect_changed=expected, write=args.write)


if __name__ == '__main__':
    raise SystemExit(main())
