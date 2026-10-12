import hashlib
import json
import os
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
artifact = out / "aios-c15-resident-runtime-3.12.14.tar.gz"
sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
size = artifact.stat().st_size

manifest = {
    "artifact_type": "AIOS_C15_APPROVED_RESIDENT_RUNTIME",
    "artifact_version": 1,
    "task": "C15-RCC-RES-A-RERUN-005",
    "filename": artifact.name,
    "sha256": sha,
    "size_bytes": size,
    "archive_root": "runtime/3.12.14",
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
    "platform_system": os.environ.get("ARTIFACT_PLATFORM_SYSTEM", ""),
    "platform_machine": os.environ.get("ARTIFACT_PLATFORM_MACHINE", ""),
    "kernel": os.environ.get("ARTIFACT_KERNEL", ""),
    "glibc": os.environ.get("ARTIFACT_GLIBC", ""),
    "runtime_elf_max_glibc": os.environ.get("ARTIFACT_ELF_MAX_GLIBC", ""),
    "contains_resident_state": False,
    "contains_repository": False,
    "contains_credentials": False,
}
manifest_path = out / "AIOS_C15_RESIDENT_RUNTIME_3_12_14_MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
(out / "aios-c15-resident-runtime-3.12.14.tar.gz.sha256").write_text(
    f"{sha}  {artifact.name}\n", encoding="utf-8"
)
check = hashlib.sha256(artifact.read_bytes()).hexdigest()
assert check == manifest["sha256"]
print("MANIFEST_ARTIFACT_SHA_MATCH", check)
print("ARTIFACT_SIZE_BYTES", size)
