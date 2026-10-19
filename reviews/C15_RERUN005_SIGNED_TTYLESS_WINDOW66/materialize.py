"""Standalone clean-room materializer; byte pins are supplied by the safe packet.

No extractall, links, overwrite, implicit parent creation, or ambient imports.
All archive members and their bytes are validated before destination creation.
An interrupted extraction leaves a blocked partial target; never retry over it.
"""
import hashlib
import io
import json
import os
from pathlib import PurePosixPath
import stat
import sys
import tarfile

def require(condition, message):
    if not condition:
        raise ValueError(message)

def validate(raw, expected_sha, inventory):
    require(hashlib.sha256(raw).hexdigest() == expected_sha, 'artifact substitution')
    require(len(raw) < 16 * 1024 * 1024, 'artifact too large')
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        require(len(set(names)) == len(names), 'duplicate archive member')
        require(set(names) == set(inventory), 'closed member set mismatch')
        content = {}
        for member in members:
            name = member.name
            path = PurePosixPath(name)
            require(not path.is_absolute() and str(path) == name
                    and all(p not in ('', '.', '..') for p in name.split('/'))
                    and name.startswith('harness/'), 'unsafe member path')
            expected = inventory[name]
            require(member.type == tarfile.REGTYPE and not member.linkname
                    and not member.pax_headers, 'non-regular/link/PAX member')
            require(member.mode == expected['mode'] == 0o644
                    and member.uid == member.gid == member.mtime == 0
                    and member.size == expected['size']
                    and 0 <= member.size <= 8 * 1024 * 1024, 'member metadata mismatch')
            data = archive.extractfile(member).read()
            require(len(data) == member.size
                    and hashlib.sha256(data).hexdigest() == expected['sha256'], 'member hash mismatch')
            content[name] = data
    return content

def open_directory(path):
    require(path.is_absolute() and str(path) == str(PurePosixPath(str(path)))
            and '..' not in path.parts, 'destination must be canonical absolute path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise

def materialize(artifact, target, expected_sha, inventory):
    # Read one immutable snapshot; a path swap after read cannot change extracted bytes.
    fd = os.open(artifact, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size < 16 * 1024 * 1024,
                'artifact must be bounded regular file')
        raw = stream.read(16 * 1024 * 1024)
    content = validate(raw, expected_sha, inventory)
    target = PurePosixPath(target)
    require(target.name not in ('', '.', '..'), 'invalid destination')
    parent = open_directory(target.parent)
    opened = {}
    try:
        # mkdir is exclusive even for dangling symlinks and racing creators.
        os.mkdir(target.name, 0o755, dir_fd=parent)
        root = os.open(target.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        opened[''] = root
        os.fchmod(root, 0o755)
        dirs = {str(PurePosixPath(name).parent) for name in content}
        for directory in sorted(dirs, key=lambda p: (p.count('/'), p)):
            parts = directory.split('/')
            for depth in range(1, len(parts)+1):
                rel = '/'.join(parts[:depth])
                if rel in opened:
                    continue
                pfd = opened['/'.join(parts[:depth-1])]
                os.mkdir(parts[depth-1], 0o755, dir_fd=pfd)
                dfd = os.open(parts[depth-1], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=pfd)
                os.fchmod(dfd, 0o755)
                opened[rel] = dfd
        for name, data in sorted(content.items()):
            path = PurePosixPath(name)
            ffd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                          0o644, dir_fd=opened[str(path.parent)])
            with os.fdopen(ffd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fchmod(stream.fileno(), 0o644)
                os.fsync(stream.fileno())
        for dfd in reversed(list(opened.values())):
            os.fsync(dfd)
        os.fsync(parent)
    finally:
        for dfd in opened.values():
            os.close(dfd)
        os.close(parent)
    print('HARNESS_MATERIALIZATION_PASS')

if __name__ == '__main__':
    materialize(sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4]))
