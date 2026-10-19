"""Pinned bootstrap for the RERUN-005 operator harness.

The launcher performs a closed, no-follow inventory before importing any
Harness, Core, or C15 module. Protected Python modules are then executed from
immutable, hash-checked byte snapshots by a private importer; PathFinder never
gets a chance to resolve a protected name to a .so/.pyc or an ambient package.
The packet-pinned external invocation must authenticate this bootstrap file
before executing it (see the Window 55 bootstrap command draft).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.abc
import importlib.machinery
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
import types

IDENTITY_SCHEMA = "resident-rerun005-harness-identity-v2"
MAX_PROTECTED_FILE_BYTES = 16 * 1024 * 1024
ACTIVE_IDENTITY = None


class IdentityBlocked(RuntimeError):
    """A protected path, byte, inode, module, or loader is not authorized."""


def _fail(code, detail=""):
    suffix = f": {detail}" if detail else ""
    raise IdentityBlocked(f"BLOCKED / {code}{suffix}")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _canonical_relative(value):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    return (not path.is_absolute() and ".." not in path.parts and "." not in path.parts
            and "" not in path.parts and path.as_posix() == value)


def _reject_mounted_overlays(root):
    """Reject mountpoints at/below a protected tree, including same-device binds."""
    try:
        lines = Path('/proc/self/mountinfo').read_text(encoding='utf-8').splitlines()
    except OSError as exc:
        _fail('MOUNT_IDENTITY_UNAVAILABLE', str(exc))
    root = Path(os.path.abspath(os.fspath(root)))
    for line in lines:
        fields = line.split()
        if len(fields) < 5:
            _fail('MOUNT_IDENTITY_MALFORMED')
        name = fields[4].replace('\\040', ' ').replace('\\011', '\t')
        name = name.replace('\\012', '\n').replace('\\134', '\\')
        point = Path(name)
        if not point.is_absolute():
            _fail('MOUNT_IDENTITY_MALFORMED', name)
        if point == root or root in point.parents:
            _fail('PROTECTED_MOUNT_OVERLAY', str(point))


def _open_directory_no_symlinks(path):
    """Open an absolute directory by walking every component with O_NOFOLLOW."""
    if not hasattr(os, 'O_NOFOLLOW') or not hasattr(os, 'O_DIRECTORY'):
        _fail('NOFOLLOW_DIRECTORY_OPEN_UNAVAILABLE')
    absolute = Path(os.path.abspath(os.fspath(path)))
    if not absolute.is_absolute():
        _fail("PROTECTED_ROOT_NOT_ABSOLUTE", str(path))
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(os.sep, flags)
    try:
        for component in absolute.parts[1:]:
            if component in ("", ".", ".."):
                _fail("NONCANONICAL_PROTECTED_PATH", str(absolute))
            next_fd = os.open(component, flags | nofollow, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        st = os.fstat(fd)
        if not stat.S_ISDIR(st.st_mode):
            _fail("PROTECTED_ROOT_NOT_DIRECTORY", str(absolute))
        return fd, absolute, st
    except BaseException:
        os.close(fd)
        raise


def _read_regular_at(dir_fd, name, *, expected_sha, expected_mode, seen_inodes, scope):
    flags = (os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
             | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        fd = os.open(name, flags, dir_fd=dir_fd)
    except OSError as exc:
        _fail("PROTECTED_FILE_OPEN_FAILED", f"{scope}/{name}: {exc}")
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            _fail("PROTECTED_NONREGULAR_FILE", f"{scope}/{name}")
        if before.st_size < 0 or before.st_size > MAX_PROTECTED_FILE_BYTES:
            _fail("PROTECTED_FILE_SIZE_LIMIT", f"{scope}/{name}: {before.st_size}")
        if before.st_nlink != 1:
            _fail("PROTECTED_HARDLINK", f"{scope}/{name}, nlink={before.st_nlink}")
        if before.st_mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX):
            _fail("PROTECTED_SPECIAL_MODE", f"{scope}/{name}")
        mode = stat.S_IMODE(before.st_mode)
        if expected_mode is None or mode != expected_mode:
            _fail("PROTECTED_MODE_DRIFT", f"{scope}/{name}: {mode:o}")
        inode = (before.st_dev, before.st_ino)
        if inode in seen_inodes:
            _fail("PROTECTED_DUPLICATE_INODE", f"{scope}/{name}")
        seen_inodes.add(inode)
        chunks = []
        total = 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_PROTECTED_FILE_BYTES:
                _fail("PROTECTED_FILE_SIZE_LIMIT", f"{scope}/{name}")
            chunks.append(chunk)
        data = b"".join(chunks)
        after = os.fstat(fd)
        stable = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                  before.st_ctime_ns, before.st_nlink, before.st_mode) == (
                  after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                  after.st_ctime_ns, after.st_nlink, after.st_mode)
        if not stable or len(data) != before.st_size:
            _fail("PROTECTED_FILE_CHANGED_DURING_READ", f"{scope}/{name}")
        if _sha(data) != expected_sha:
            _fail("PROTECTED_BYTE_IDENTITY_DRIFT", f"{scope}/{name}")
        return data, {"dev": before.st_dev, "ino": before.st_ino,
                      "size": before.st_size, "mode": mode}
    finally:
        os.close(fd)


def _scan_tree(root, *, scope, expected_hashes, expected_file_modes,
               expected_directory_modes, seen_inodes):
    """Inventory one closed tree without following links or importing files."""
    _reject_mounted_overlays(root)
    root_fd, absolute, root_stat = _open_directory_no_symlinks(root)
    snapshots = {}
    directory_identities = {"": {"dev": root_stat.st_dev, "ino": root_stat.st_ino,
                                    "mode": stat.S_IMODE(root_stat.st_mode)}}
    actual_files = set()
    actual_directories = {""}
    try:
        if root_stat.st_mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX):
            _fail("PROTECTED_SPECIAL_DIRECTORY_MODE", scope)
        if stat.S_IMODE(root_stat.st_mode) != expected_directory_modes.get(""):
            _fail("PROTECTED_DIRECTORY_MODE_DRIFT", f"{scope}/")
        root_device = root_stat.st_dev

        def visit(directory_fd, relative_directory):
            try:
                entries = sorted(os.scandir(directory_fd), key=lambda item: item.name)
            except OSError as exc:
                _fail("PROTECTED_TREE_READ_FAILED", f"{scope}/{relative_directory}: {exc}")
            for entry in entries:
                name = entry.name
                if name in ("", ".", "..") or "/" in name or "\\" in name or "\x00" in name:
                    _fail("NONCANONICAL_PROTECTED_NAME", f"{scope}/{name!r}")
                rel = f"{relative_directory}/{name}" if relative_directory else name
                try:
                    st = entry.stat(follow_symlinks=False)
                except OSError as exc:
                    _fail("PROTECTED_NODE_STAT_FAILED", f"{scope}/{rel}: {exc}")
                if st.st_dev != root_device:
                    _fail("PROTECTED_MOUNT_BOUNDARY", f"{scope}/{rel}")
                if stat.S_ISLNK(st.st_mode):
                    _fail("PROTECTED_SYMLINK", f"{scope}/{rel}")
                if stat.S_ISDIR(st.st_mode):
                    mode = stat.S_IMODE(st.st_mode)
                    if st.st_mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX):
                        _fail("PROTECTED_SPECIAL_DIRECTORY_MODE", f"{scope}/{rel}")
                    if expected_directory_modes.get(rel) != mode:
                        _fail("UNAPPROVED_OR_REPLACED_DIRECTORY", f"{scope}/{rel}")
                    try:
                        child_fd = os.open(name, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                                           | getattr(os, "O_CLOEXEC", 0)
                                           | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd)
                    except OSError as exc:
                        _fail("PROTECTED_DIRECTORY_REPLACED", f"{scope}/{rel}: {exc}")
                    try:
                        opened = os.fstat(child_fd)
                        if (opened.st_dev, opened.st_ino) != (st.st_dev, st.st_ino):
                            _fail("PROTECTED_DIRECTORY_REPLACED", f"{scope}/{rel}")
                        actual_directories.add(rel)
                        directory_identities[rel] = {"dev": opened.st_dev, "ino": opened.st_ino,
                                                     "mode": stat.S_IMODE(opened.st_mode)}
                        visit(child_fd, rel)
                    finally:
                        os.close(child_fd)
                    continue
                if not stat.S_ISREG(st.st_mode):
                    _fail("PROTECTED_UNSAFE_NODE", f"{scope}/{rel}")
                if rel not in expected_hashes:
                    _fail("CLOSED_EXECUTABLE_SET_DRIFT", f"{scope}/{rel}")
                actual_files.add(rel)
                data, identity = _read_regular_at(
                    directory_fd, name, expected_sha=expected_hashes[rel],
                    expected_mode=expected_file_modes.get(rel),
                    seen_inodes=seen_inodes, scope=scope)
                try:
                    after_path = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                except OSError as exc:
                    _fail("PROTECTED_PATH_REPLACED_AFTER_READ", f"{scope}/{rel}: {exc}")
                if (after_path.st_dev, after_path.st_ino) != (identity["dev"], identity["ino"]):
                    _fail("PROTECTED_PATH_REPLACED_AFTER_READ", f"{scope}/{rel}")
                snapshots[rel] = {"bytes": data, "sha256": expected_hashes[rel], **identity}
        visit(root_fd, "")
    finally:
        os.close(root_fd)

    if actual_files != set(expected_hashes):
        missing = sorted(set(expected_hashes) - actual_files)
        extra = sorted(actual_files - set(expected_hashes))
        _fail("CLOSED_FILE_SET_MISMATCH", f"{scope}: missing={missing} extra={extra}")
    if actual_directories != set(expected_directory_modes):
        missing = sorted(set(expected_directory_modes) - actual_directories)
        extra = sorted(actual_directories - set(expected_directory_modes))
        _fail("CLOSED_DIRECTORY_SET_MISMATCH", f"{scope}: missing={missing} extra={extra}")
    if actual_files != set(expected_file_modes):
        _fail("FILE_MODE_MANIFEST_MISMATCH", scope)
    return snapshots, directory_identities


def _expected_directories(files):
    result = {""}
    for name in files:
        parent = PurePosixPath(name).parent
        while str(parent) not in ("", "."):
            result.add(parent.as_posix())
            parent = parent.parent
    return result


def _validate_manifest(manifest):
    if not isinstance(manifest, dict) or manifest.get("schema") != IDENTITY_SCHEMA:
        _fail("IDENTITY_SCHEMA_UNSUPPORTED")
    for key in ("harness_files", "source_files", "file_modes", "directory_modes"):
        if not isinstance(manifest.get(key), dict):
            _fail("IDENTITY_MANIFEST_FIELD_INVALID", key)
    hfiles, sfiles = manifest["harness_files"], manifest["source_files"]
    if not hfiles or not sfiles:
        _fail("IDENTITY_MANIFEST_EMPTY")
    for rel, digest in list(hfiles.items()) + list(sfiles.items()):
        if not _canonical_relative(rel) or not rel.endswith(".py"):
            _fail("IDENTITY_MANIFEST_PATH_INVALID", str(rel))
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            _fail("IDENTITY_MANIFEST_DIGEST_INVALID", str(rel))
    if any(not p.startswith("src/aios_core/") for p in sfiles if p.startswith("src/")):
        _fail("IDENTITY_SOURCE_PATH_OUTSIDE_CORE", "src")
    if any(not (p.startswith("tools/c15_persistence/") or p == "tools/c15_persistence/__init__.py")
           for p in sfiles if p.startswith("tools/")):
        _fail("IDENTITY_SOURCE_PATH_OUTSIDE_C15", "tools")
    prefixes = {"src/", "tools/"}
    if any(not p.startswith(tuple(prefixes)) for p in sfiles):
        _fail("IDENTITY_SOURCE_PATH_INVALID")
    for name in ("harness", "core", "c15"):
        if not isinstance(manifest["file_modes"].get(name), dict):
            _fail("IDENTITY_MODE_MANIFEST_INVALID", f"file_modes.{name}")
        if not isinstance(manifest["directory_modes"].get(name), dict):
            _fail("IDENTITY_MODE_MANIFEST_INVALID", f"directory_modes.{name}")
    if "IDENTITY.json" in hfiles:
        _fail("IDENTITY_MANIFEST_SELF_REFERENCE")
    if "launch.py" not in hfiles or "r005/checks.py" not in hfiles:
        _fail("IDENTITY_BOOTSTRAP_ENTRIES_MISSING")


def scan_identity(root, repo, expected_manifest_sha):
    """Read and validate the complete Harness/Core/C15 executable trees."""
    root = Path(os.path.abspath(os.fspath(root)))
    repo = Path(os.path.abspath(os.fspath(repo)))
    protected_roots = (repo / "src/aios_core", repo / "tools/c15_persistence")
    if root == repo or any(root == protected or root in protected.parents or protected in root.parents
                           for protected in protected_roots):
        _fail("PROTECTED_ROOT_OVERLAP")
    manifest_dir_fd, _, _ = _open_directory_no_symlinks(root)
    try:
        manifest_bytes, manifest_file_identity = _read_regular_at(
            manifest_dir_fd, "IDENTITY.json", expected_sha=expected_manifest_sha,
            expected_mode=0o644, seen_inodes=set(), scope="harness")
    finally:
        os.close(manifest_dir_fd)
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail("IDENTITY_MANIFEST_INVALID_JSON", str(exc))
    _validate_manifest(manifest)

    harness_hashes = {"IDENTITY.json": expected_manifest_sha, **manifest["harness_files"]}
    harness_modes = {"IDENTITY.json": manifest.get("identity_mode", 0o644),
                     **manifest["file_modes"]["harness"]}
    core_hashes = {p.removeprefix("src/aios_core/"): h
                   for p, h in manifest["source_files"].items() if p.startswith("src/aios_core/")}
    c15_hashes = {p.removeprefix("tools/c15_persistence/"): h
                  for p, h in manifest["source_files"].items() if p.startswith("tools/c15_persistence/")}
    core_modes = manifest["file_modes"]["core"]
    c15_modes = manifest["file_modes"]["c15"]
    for label, files, modes, dirs in (
        ("harness", harness_hashes, harness_modes, manifest["directory_modes"]["harness"]),
        ("core", core_hashes, core_modes, manifest["directory_modes"]["core"]),
        ("c15", c15_hashes, c15_modes, manifest["directory_modes"]["c15"]),
    ):
        if set(dirs) != _expected_directories(files):
            _fail("DIRECTORY_MODE_MANIFEST_MISMATCH", label)
        if set(modes) != set(files):
            _fail("FILE_MODE_MANIFEST_MISMATCH", label)

    seen_inodes = set()
    all_snapshots = {}
    all_directory_identities = {}
    roots = (
        (root, "harness", harness_hashes, harness_modes, manifest["directory_modes"]["harness"]),
        (repo / "src/aios_core", "core", core_hashes, core_modes, manifest["directory_modes"]["core"]),
        (repo / "tools/c15_persistence", "c15", c15_hashes, c15_modes, manifest["directory_modes"]["c15"]),
    )
    for tree_root, scope, hashes, modes, dirs in roots:
        scanned, directory_identities = _scan_tree(
            tree_root, scope=scope, expected_hashes=hashes,
            expected_file_modes=modes, expected_directory_modes=dirs,
            seen_inodes=seen_inodes)
        all_directory_identities[scope] = directory_identities
        for rel, entry in scanned.items():
            full = rel if scope == "harness" else (
                f"src/aios_core/{rel}" if scope == "core" else f"tools/c15_persistence/{rel}")
            all_snapshots[full] = entry
    observed_identity = all_snapshots["IDENTITY.json"]
    if (observed_identity["dev"], observed_identity["ino"]) != (
            manifest_file_identity["dev"], manifest_file_identity["ino"]):
        _fail("IDENTITY_MANIFEST_PATH_REPLACED")
    return {
        "root": root,
        "repo": repo,
        "manifest": manifest,
        "manifest_sha256": expected_manifest_sha,
        "snapshots": all_snapshots,
        "directory_identities": all_directory_identities,
        "harness_manifest_identity": manifest_file_identity,
    }


def _module_map(state):
    mapping = {}
    for rel in state["manifest"]["harness_files"]:
        if not rel.startswith("r005/"):
            continue
        prefix = ""
        source = rel
        package = False
        if source.endswith("/__init__.py"):
            dotted = source[:-len("/__init__.py")].replace("/", ".")
            package = True
        elif source == "r005/__init__.py":
            dotted, package = "r005", True
        else:
            dotted = source[:-3].replace("/", ".")
        mapping[dotted] = (rel, package)
    for rel in state["manifest"]["source_files"]:
        if rel.startswith("src/aios_core/"):
            source = rel[len("src/"):]
            if source.endswith("/__init__.py"):
                dotted = source[:-len("/__init__.py")].replace("/", ".")
                package = True
            elif source == "aios_core/__init__.py":
                dotted, package = "aios_core", True
            else:
                dotted, package = source[:-3].replace("/", "."), False
            mapping[dotted] = (rel, package)
        elif rel.startswith("tools/c15_persistence/"):
            source = rel[len("tools/"):]
            if source.endswith("/__init__.py"):
                dotted = "tools." + source[:-len("/__init__.py")].replace("/", ".")
                package = True
            else:
                dotted = "tools." + source[:-3].replace("/", ".")
                package = False
            mapping[dotted] = (rel, package)
    return mapping


class _VerifiedSourceLoader(importlib.abc.Loader):
    def __init__(self, state, fullname, relative, is_package):
        self.state = state
        self.fullname = fullname
        self.relative = relative
        self.is_package = is_package
        self.entry = state["snapshots"][relative]
        self.filename = str((state["root"] / relative) if relative.startswith("r005/") or relative == "launch.py"
                            else (state["repo"] / relative))

    def create_module(self, spec):
        return None

    def get_filename(self, fullname):
        if fullname != self.fullname:
            _fail("LOADER_MODULE_NAME_MISMATCH", fullname)
        return self.filename

    def get_code(self, fullname):
        if fullname != self.fullname:
            _fail("LOADER_MODULE_NAME_MISMATCH", fullname)
        source = self.entry["bytes"]
        if _sha(source) != self.entry["sha256"]:
            _fail("LOADER_SNAPSHOT_IDENTITY_DRIFT", self.relative)
        return compile(source, self.filename, "exec", dont_inherit=True)

    def exec_module(self, module):
        source = self.entry["bytes"]
        code = self.get_code(self.fullname)
        module.__file__ = self.filename
        module.__cached__ = None
        module.__loader__ = self
        if self.is_package:
            module.__path__ = [str(Path(self.filename).parent)]
        exec(code, module.__dict__)
        self.state["loaded"][self.fullname] = {
            "module": module,
            "loader": self,
            "relative": self.relative,
            "sha256": _sha(source),
            "dev": self.entry["dev"],
            "ino": self.entry["ino"],
        }


class _VerifiedTreeFinder(importlib.abc.MetaPathFinder):
    def __init__(self, state):
        self.state = state
        self.modules = _module_map(state)
        state["loaded"] = {}

    def find_spec(self, fullname, path=None, target=None):
        is_protected = (fullname == "r005" or fullname.startswith("r005.")
                        or fullname == "aios_core" or fullname.startswith("aios_core.")
                        or fullname == "tools" or fullname.startswith("tools."))
        if not is_protected:
            return None
        item = self.modules.get(fullname)
        if item is None:
            _fail("UNAPPROVED_PROTECTED_MODULE", fullname)
        relative, is_package = item
        loader = _VerifiedSourceLoader(self.state, fullname, relative, is_package)
        spec = importlib.machinery.ModuleSpec(fullname, loader, origin=loader.filename,
                                              is_package=is_package)
        spec.has_location = True
        if is_package:
            spec.submodule_search_locations = [str(Path(loader.filename).parent)]
        return spec


def activate_verified_importer(state):
    """Install the closed source-only importer after a complete successful scan."""
    global ACTIVE_IDENTITY
    for name in tuple(sys.modules):
        if (name == "r005" or name.startswith("r005.") or name == "aios_core"
                or name.startswith("aios_core.") or name == "tools"
                or name.startswith("tools.")):
            _fail("PROTECTED_MODULE_PRELOADED_BEFORE_VERIFICATION", name)
    finder = _VerifiedTreeFinder(state)
    state["finder"] = finder
    sys.meta_path.insert(0, finder)
    namespace = types.ModuleType("tools")
    namespace.__path__ = []
    namespace.__package__ = "tools"
    namespace.__spec__ = importlib.machinery.ModuleSpec("tools", loader=None, is_package=True)
    namespace.__spec__.submodule_search_locations = []
    state["tools_namespace"] = namespace
    sys.modules["tools"] = namespace
    protected = (str(state["root"]), str(state["repo"]),
                 str(state["repo"] / "src"), str(state["repo"] / "tools"))
    sys.path[:] = [entry for entry in sys.path if os.path.abspath(entry or os.curdir) not in protected]
    ACTIVE_IDENTITY = state
    return state


def verify_current_identity(root, repo, manifest_sha):
    """Re-audit disk and the immutable importer state; fail closed on any drift."""
    state = ACTIVE_IDENTITY
    if state is None:
        _fail("VERIFIED_IMPORTER_NOT_ACTIVE")
    if Path(os.path.abspath(os.fspath(root))) != state["root"]:
        _fail("HARNESS_ROOT_CHANGED")
    if Path(os.path.abspath(os.fspath(repo))) != state["repo"]:
        _fail("SOURCE_ROOT_CHANGED")
    if manifest_sha != state["manifest_sha256"]:
        _fail("IDENTITY_DIGEST_CHANGED")
    fresh = scan_identity(root, repo, manifest_sha)
    old_identity = {k: (_sha(v["bytes"]), v["dev"], v["ino"], v["mode"])
                    for k, v in state["snapshots"].items()}
    fresh_identity = {k: (_sha(v["bytes"]), v["dev"], v["ino"], v["mode"])
                      for k, v in fresh["snapshots"].items()}
    if old_identity != fresh_identity:
        _fail("EXECUTED_SNAPSHOT_DIFFERS_FROM_DISK")
    if state["directory_identities"] != fresh["directory_identities"]:
        _fail("PROTECTED_DIRECTORY_IDENTITY_CHANGED")
    if state["manifest"].get("python_sha256") != fresh["manifest"].get("python_sha256"):
        _fail("RUNTIME_IDENTITY_MANIFEST_DRIFT")
    return state["manifest"]


def verify_loaded_modules(repo=None, root=None):
    """Prove module objects are exactly those executed from pinned byte snapshots."""
    state = ACTIVE_IDENTITY
    if state is None:
        _fail("VERIFIED_IMPORTER_NOT_ACTIVE")
    if repo is not None and Path(os.path.abspath(os.fspath(repo))) != state["repo"]:
        _fail("SOURCE_ROOT_CHANGED")
    if root is not None and Path(os.path.abspath(os.fspath(root))) != state["root"]:
        _fail("HARNESS_ROOT_CHANGED")
    verify_current_identity(state["root"], state["repo"], state["manifest_sha256"])
    loaded_names = []
    for name, module in tuple(sys.modules.items()):
        protected = (name == "r005" or name.startswith("r005.") or name == "aios_core"
                     or name.startswith("aios_core.") or name == "tools.c15_persistence"
                     or name.startswith("tools.c15_persistence."))
        if not protected:
            continue
        identity = state["loaded"].get(name)
        if identity is None or identity["module"] is not module:
            _fail("UNVERIFIED_LOADED_MODULE", name)
        expected_path = str((state["root"] / identity["relative"])
                            if identity["relative"].startswith("r005/")
                            else (state["repo"] / identity["relative"]))
        if (getattr(module, "__file__", None) != expected_path
                or getattr(module, "__loader__", None) is not identity["loader"]
                or getattr(getattr(module, "__spec__", None), "origin", None) != expected_path):
            _fail("LOADED_MODULE_PATH_OR_LOADER_IDENTITY", name)
        entry = state["snapshots"].get(identity["relative"])
        if entry is None or _sha(entry["bytes"]) != identity["sha256"]:
            _fail("LOADED_MODULE_CONTENT_IDENTITY", name)
        loaded_names.append(name)
    if sys.modules.get("tools") is not state["tools_namespace"]:
        _fail("TOOLS_NAMESPACE_SUBSTITUTION")
    for name in sys.modules:
        if name.startswith("tools.") and not (
                name == "tools.c15_persistence" or name.startswith("tools.c15_persistence.")):
            _fail("UNAPPROVED_TOOLS_PACKAGE_MODULE", name)
    if list(state["tools_namespace"].__path__) != []:
        _fail("TOOLS_NAMESPACE_PATH_DRIFT")
    return {
        "module_import_identity": "PASS",
        "loaded_modules": sorted(loaded_names),
        "loaded_source_sha256": {name: state["loaded"][name]["sha256"] for name in sorted(loaded_names)},
        "loader": "closed-in-memory-pinned-source-only",
    }


def _main(argv=None):
    global ACTIVE_IDENTITY
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--identity-sha256", required=True)
    args, remaining = parser.parse_known_args(argv)
    if not remaining:
        _fail("COMMAND_REQUIRED")
    if len(args.identity_sha256) != 64 or any(c not in "0123456789abcdef" for c in args.identity_sha256):
        _fail("IDENTITY_DIGEST_INVALID")

    root = Path(os.path.abspath(__file__)).parent
    repo = Path(os.path.abspath(os.fspath(args.source_repo)))
    sys.pycache_prefix = tempfile.mkdtemp(prefix="r005-verified-import-")
    sys.dont_write_bytecode = True
    try:
        state = scan_identity(root, repo, args.identity_sha256)
        activate_verified_importer(state)
    except Exception as exc:
        raise SystemExit(str(exc)) from exc

    try:
        from r005.checks import verify
        verify(root, repo, args.identity_sha256)
    except Exception as exc:
        raise SystemExit("BLOCKED / STARTUP_VERIFICATION_FAILED: " + str(exc)) from exc

    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["AIOS53_LAUNCH"] = str(root / "launch.py")
    os.environ["AIOS53_SOURCE_REPO"] = str(repo)
    os.environ["AIOS53_IDENTITY_SHA"] = args.identity_sha256
    if remaining[0] == "service":
        service_parser = argparse.ArgumentParser()
        service_parser.add_argument("--exchange", required=True)
        service_parser.add_argument("--socket", required=True)
        service_parser.add_argument("--runner-pid", required=True)
        service_parser.add_argument("--runner-start-time", required=True)
        service_parser.add_argument("--runner-instance-id", required=True)
        service_parser.add_argument("--operation-id", required=True)
        service_parser.add_argument("--parent-fd", required=True)
        service = service_parser.parse_args(remaining[1:])
        sys.argv = ["publisher_service", service.exchange, service.socket,
                    service.runner_pid, service.runner_start_time,
                    service.runner_instance_id, service.operation_id, service.parent_fd]
        from r005.publisher_service import main as publisher_main
        publisher_main()
    else:
        from r005.cli import main
        sys.argv = [str(root / "launch.py"), *remaining]
        main()


if __name__ == "__main__":
    _main()
