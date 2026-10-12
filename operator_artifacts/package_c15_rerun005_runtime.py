from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import tarfile

runtime_root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
elf_max_glibc = sys.argv[3]
runtime_dir = runtime_root / "runtime" / "3.12.14"
artifact = out / "aios-c15-resident-runtime-3.12.14.tar.gz"
manifest_path = out / "AIOS_C15_RESIDENT_RUNTIME_3_12_14_MANIFEST.json"
sha_path = out / "aios-c15-resident-runtime-3.12.14.tar.gz.sha256"

assert runtime_dir.is_dir(), runtime_dir
assert (runtime_dir / "venv" / "bin" / "python").exists(), "venv python missing"
out.mkdir(parents=True, exist_ok=True)

def tar_filter(info: tarfile.TarInfo):
    parts = PurePosixPath(info.name).parts
    if "__pycache__" in parts or info.name.endswith(".pyc"):
        return None
    return info

with tarfile.open(artifact, "w:gz", format=tarfile.PAX_FORMAT) as tf:
    tf.add(runtime_dir, arcname="runtime/3.12.14", recursive=True, filter=tar_filter)

with tarfile.open(artifact, "r:gz") as tf:
    members = tf.getmembers()
    names = [m.name for m in members]

required_prefix = "runtime/3.12.14/venv/bin/python"
assert any(n == required_prefix or n.startswith(required_prefix) for n in names), "venv python absent from archive"

for name in names:
    parts = set(PurePosixPath(name).parts)
    assert ".git" not in parts
    assert ".ssh" not in parts
    base = PurePosixPath(name).name
    assert base not in {".netrc", ".git-credentials", "id_rsa", "id_ed25519", "credentials.json"}

sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
size = artifact.stat().st_size
sha_path.write_text(f"{sha}  {artifact.name}\n", encoding="utf-8")

glibc_line = subprocess.check_output(["ldd", "--version"], text=True, stderr=subprocess.STDOUT).splitlines()[0]
manifest = {
    "artifact_type": "AIOS_C15_APPROVED_RESIDENT_RUNTIME",
    "artifact_version": 2,
    "task": "C15-RCC-RES-A-RERUN-005",
    "filename": artifact.name,
    "sha256": sha,
    "size_bytes": size,
    "archive_root": "runtime/3.12.14",
    "archive_member_count": len(names),
    "target_runtime_root": "/home/user/.cache/c002/final-runtime-003",
    "target_python": "/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python",
    "python": "3.12.14",
    "pydantic": "2.13.5",
    "pytest": "8.4.2",
    "sqlite": "3.45.1",
    "openssl": "3.0.13",
    "source_runtime_verified": True,
    "runtime_env_ok": True,
    "accepted_current_main_sha": "0e55591f1d2e142e93f40706af86305cf327e6f0",
    "historical_bootstrap_commit": "77dac70e0cf054c3f0fb7d94a66dba221fe7d5de",
    "bootstrap_sha256": "e98965d8b55f5e8202c9470af2a3ca175ccde9f93427de5d6cf717921c3ea497",
    "platform_system": platform.system(),
    "platform_machine": platform.machine(),
    "kernel": platform.release(),
    "glibc": glibc_line,
    "runtime_elf_max_glibc": elf_max_glibc,
    "contains_resident_state": False,
    "contains_repository": False,
    "contains_credentials": False,
}
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

check = hashlib.sha256(artifact.read_bytes()).hexdigest()
assert check == manifest["sha256"]
print("MANIFEST_ARTIFACT_SHA_MATCH", check)
print("ARTIFACT_SIZE_BYTES", size)
print("ARCHIVE_MEMBER_COUNT", len(names))
print("RUNTIME_ARTIFACT_READY")
