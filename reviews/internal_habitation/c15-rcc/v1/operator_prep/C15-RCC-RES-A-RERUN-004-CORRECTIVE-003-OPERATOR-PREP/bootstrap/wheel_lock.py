#!/usr/bin/env python3
"""Pre-download trust-root verification/acquisition for the locked wheelhouse.

Expected SHA-256 values come only from the candidate-controlled lock. This
module never creates or updates expected hashes from acquired wheel bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request
from typing import Any

REQUIRED_PROJECTS = {
    "annotated-types",
    "iniconfig",
    "packaging",
    "pip",
    "pluggy",
    "pydantic",
    "pydantic-core",
    "pygments",
    "pytest",
    "typing-extensions",
    "typing-inspection",
}
LOCK_FIELDS = {
    "project",
    "version",
    "filename",
    "sha256",
    "python_tag",
    "abi_tag",
    "platform_tag",
    "url",
}


class WheelLockError(RuntimeError):
    """The locked artifact closure is absent, malformed, or changed."""


def normalize_project(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_lock(
    lock_path: pathlib.Path,
    *,
    require_qualified_closure: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise WheelLockError(f"cannot read wheel lock: {exc}") from exc
    if lock.get("schema_version") != 1:
        raise WheelLockError("unsupported wheel lock schema_version")
    target = lock.get("target", {})
    if not isinstance(target, dict):
        raise WheelLockError("wheel lock target must be an object")
    if require_qualified_closure and (
        target.get("implementation") != "CPython"
        or target.get("python_version") != "3.12.14"
        or target.get("architecture") != "x86_64"
        or target.get("os") != "linux"
    ):
        raise WheelLockError("wheel lock target is not the qualified CPython 3.12.14 Linux x86_64 environment")
    wheels = lock.get("wheels")
    if not isinstance(wheels, list) or not wheels:
        raise WheelLockError("wheel lock has no non-empty wheels list")

    seen_files: set[str] = set()
    seen_projects: set[str] = set()
    for entry in wheels:
        if not isinstance(entry, dict) or not LOCK_FIELDS <= set(entry):
            raise WheelLockError(f"wheel entry must contain {sorted(LOCK_FIELDS)}")
        project = normalize_project(str(entry["project"]))
        filename = str(entry["filename"])
        version = str(entry["version"])
        digest = str(entry["sha256"])
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise WheelLockError(f"invalid pre-frozen SHA-256 for {filename}")
        if filename in seen_files or project in seen_projects:
            raise WheelLockError(f"duplicate locked artifact or project: {filename}/{project}")
        if not filename.endswith(".whl"):
            raise WheelLockError(f"locked artifact is not a wheel: {filename}")
        parts = filename[:-4].split("-")
        if len(parts) != 5:
            raise WheelLockError(f"unsupported/non-exact wheel filename grammar: {filename}")
        file_project, file_version, python_tag, abi_tag, platform_tag = parts
        if normalize_project(file_project) != project or file_version != version:
            raise WheelLockError(f"filename project/version disagree with lock fields: {filename}")
        if (python_tag, abi_tag, platform_tag) != (
            str(entry["python_tag"]), str(entry["abi_tag"]), str(entry["platform_tag"])
        ):
            raise WheelLockError(f"filename tags disagree with lock fields: {filename}")
        if python_tag not in {"cp312", "py3", "py2.py3"}:
            raise WheelLockError(f"wheel is not compatible with qualified Python 3.12: {filename}")
        if abi_tag not in {"cp312", "none"}:
            raise WheelLockError(f"wheel ABI is not compatible with qualified CPython 3.12: {filename}")
        if platform_tag != "any" and not platform_tag.startswith("manylinux_2_17_x86_64"):
            raise WheelLockError(f"wheel platform is not qualified Linux x86_64: {filename}")
        parsed = urllib.parse.urlparse(str(entry["url"]))
        if parsed.scheme != "https" or parsed.hostname != "files.pythonhosted.org" or pathlib.PurePosixPath(parsed.path).name != filename:
            raise WheelLockError(f"wheel URL is not an exact PyPI-hosted filename: {filename}")
        seen_files.add(filename)
        seen_projects.add(project)

    if require_qualified_closure:
        if seen_projects != REQUIRED_PROJECTS:
            missing = sorted(REQUIRED_PROJECTS - seen_projects)
            unexpected = sorted(seen_projects - REQUIRED_PROJECTS)
            raise WheelLockError(f"dependency closure is not the frozen 10-distribution set; missing={missing} unexpected={unexpected}")
        versions = {normalize_project(str(item["project"])): str(item["version"]) for item in wheels}
        if versions.get("pydantic") != "2.13.5" or versions.get("pytest") != "8.4.2" or versions.get("pip") != "25.0.1":
            raise WheelLockError("required dependency/bootstrap tool versions do not match the qualified runtime")
    return lock, wheels


def _expected_filenames(wheels: list[dict[str, Any]]) -> set[str]:
    return {str(item["filename"]) for item in wheels}


def verify_wheelhouse(lock_path: pathlib.Path | str, wheelhouse: pathlib.Path | str) -> dict[str, Any]:
    """Verify exact closed wheel set and each artifact against pre-existing lock."""
    lock_path = pathlib.Path(lock_path)
    wheelhouse = pathlib.Path(wheelhouse)
    lock, wheels = load_lock(lock_path)
    if not wheelhouse.is_dir():
        raise WheelLockError(f"wheelhouse is missing: {wheelhouse}")

    expected = _expected_filenames(wheels)
    actual_wheels = {path.name for path in wheelhouse.glob("*.whl") if path.is_file()}
    unexpected = actual_wheels - expected
    missing = expected - actual_wheels
    if unexpected:
        raise WheelLockError(f"unexpected wheel(s) in closed wheelhouse: {sorted(unexpected)}")
    if missing:
        raise WheelLockError(f"missing locked wheel(s): {sorted(missing)}")
    extra_files = {
        path.name for path in wheelhouse.iterdir()
        if path.is_file() and path.name not in expected and path.name != "SHA256SUMS"
    }
    if extra_files:
        raise WheelLockError(f"unexpected non-wheel file(s) in wheelhouse: {sorted(extra_files)}")

    verified = []
    for entry in wheels:
        path = wheelhouse / str(entry["filename"])
        observed = sha256_file(path)
        if observed != entry["sha256"]:
            raise WheelLockError(
                f"SHA-256 mismatch for {path.name}: expected {entry['sha256']} observed {observed}"
            )
        verified.append({"project": entry["project"], "version": entry["version"], "filename": path.name, "sha256": observed})
    return {
        "status": "PASS",
        "lock_sha256": sha256_file(lock_path),
        "lock_path": str(lock_path.resolve()),
        "wheelhouse": str(wheelhouse.resolve()),
        "artifact_count": len(verified),
        "artifacts": verified,
    }


def acquire_wheelhouse(lock_path: pathlib.Path | str, wheelhouse: pathlib.Path | str) -> dict[str, Any]:
    """Download only exact lock URLs, verify before accepting, then close the set."""
    lock_path = pathlib.Path(lock_path)
    wheelhouse = pathlib.Path(wheelhouse)
    _lock, wheels = load_lock(lock_path, require_qualified_closure=True)
    wheelhouse.mkdir(parents=True, exist_ok=True)
    expected = _expected_filenames(wheels)

    for path in wheelhouse.iterdir():
        if path.is_file() and path.name.endswith(".whl") and path.name not in expected:
            raise WheelLockError(f"unexpected wheel already present; refusing open wheelhouse: {path.name}")
        if path.is_file() and path.name.endswith(".part"):
            path.unlink()
            raise WheelLockError(f"stale partial wheel removed; refusing build: {path.name}")

    for entry in wheels:
        filename = str(entry["filename"])
        destination = wheelhouse / filename
        if destination.exists():
            observed = sha256_file(destination)
            if observed != entry["sha256"]:
                destination.unlink()
                raise WheelLockError(f"cached wheel hash mismatch; removed and blocked: {filename}")
            continue

        part = wheelhouse / (filename + ".part")
        request = urllib.request.Request(str(entry["url"]), headers={"User-Agent": "AIOS-locked-bootstrap/1"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response, part.open("wb") as output:
                final_host = urllib.parse.urlparse(response.geturl()).hostname
                if final_host != "files.pythonhosted.org":
                    raise WheelLockError(f"wheel download redirected to an unapproved host: {final_host}")
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    output.write(block)
                output.flush()
                os.fsync(output.fileno())
            observed = sha256_file(part)
            if observed != entry["sha256"]:
                part.unlink(missing_ok=True)
                raise WheelLockError(
                    f"downloaded wheel SHA-256 mismatch; rejected and removed: {filename}"
                )
            os.replace(part, destination)
        except Exception:
            part.unlink(missing_ok=True)
            raise

    return verify_wheelhouse(lock_path, wheelhouse)


def list_locked_wheels(lock_path: pathlib.Path | str, wheelhouse: pathlib.Path | str) -> list[str]:
    load_lock(pathlib.Path(lock_path), require_qualified_closure=True)
    verify_wheelhouse(lock_path, wheelhouse)
    _lock, wheels = load_lock(pathlib.Path(lock_path), require_qualified_closure=True)
    return [str((pathlib.Path(wheelhouse) / entry["filename"]).resolve()) for entry in wheels]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("acquire", "verify", "list"))
    parser.add_argument("--lock", required=True, type=pathlib.Path)
    parser.add_argument("--wheelhouse", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "acquire":
            result = acquire_wheelhouse(args.lock, args.wheelhouse)
            print(json.dumps(result, indent=2, sort_keys=True))
        elif args.action == "verify":
            load_lock(args.lock, require_qualified_closure=True)
            print(json.dumps(verify_wheelhouse(args.lock, args.wheelhouse), indent=2, sort_keys=True))
        else:
            print("\n".join(list_locked_wheels(args.lock, args.wheelhouse)))
        return 0
    except Exception as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
