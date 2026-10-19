"""Canonical content identity, shared by bootstrap/operator tools/packet.

Algorithm v1: regular files sorted by POSIX relative path; exclude only
__pycache__ directories. Reject symlinks. JSON list of path/sha256/size,
sorted keys, compact separators, UTF-8, no newline; SHA256 of those bytes.
No import of Core is needed to verify its bytes.
"""
import hashlib
import json
import pathlib

ALGORITHM = 'sorted-path-sha256-size-json-v1'
FROZEN_CORE_MANIFEST = '220718d6b5a2650b5e4263bbe8b7e661444cb33b486a7ecd7b5ad3d7d3399caa'


def core_content_manifest(core_root):
    root = pathlib.Path(core_root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError('content root must be a real directory')
    files = []
    for path in sorted(root.rglob('*')):
        if '__pycache__' in path.relative_to(root).parts:
            continue
        if path.is_symlink():
            raise ValueError(f'symlink in verified tree: {path}')
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f'nonregular file in verified tree: {path}')
        data = path.read_bytes()
        files.append({'path': path.relative_to(root).as_posix(),
            'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)})
    raw = json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return {'core_root': str(root), 'file_count': len(files), 'files': files,
        'manifest_sha256': hashlib.sha256(raw).hexdigest()}
