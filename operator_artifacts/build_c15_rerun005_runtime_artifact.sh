#!/usr/bin/env bash
set -euo pipefail

HISTORICAL_BOOTSTRAP_COMMIT="77dac70e0cf054c3f0fb7d94a66dba221fe7d5de"
CURRENT_MAIN_SHA="0e55591f1d2e142e93f40706af86305cf327e6f0"
RUNTIME_ROOT="/home/user/.cache/c002/final-runtime-003"
BOOTSTRAP_REL="reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/bootstrap/bootstrap_runtime.sh"
EXPECTED_BOOTSTRAP_SHA256="e98965d8b55f5e8202c9470af2a3ca175ccde9f93427de5d6cf717921c3ea497"
HIST="/tmp/aios-c15-rerun005-bootstrap-operator"
CUR="/tmp/aios-c15-rerun005-current-main"
OUT="$GITHUB_WORKSPACE/out"

sudo mkdir -p /home/user/.cache/c002/final-runtime-003
sudo chown -R "$(id -u):$(id -g)" /home/user

git cat-file -e "$HISTORICAL_BOOTSTRAP_COMMIT^{commit}"
rm -rf "$HIST" "$CUR"
git worktree add --detach "$HIST" "$HISTORICAL_BOOTSTRAP_COMMIT"
BOOTSTRAP="$HIST/$BOOTSTRAP_REL"
test -f "$BOOTSTRAP"
printf '%s  %s\n' "$EXPECTED_BOOTSTRAP_SHA256" "$BOOTSTRAP" | sha256sum -c -

AIOS_REPO_ROOT="$HIST" AIOS_RUNTIME_ROOT="$RUNTIME_ROOT" bash "$BOOTSTRAP" --build
AIOS_REPO_ROOT="$HIST" AIOS_RUNTIME_ROOT="$RUNTIME_ROOT" bash "$BOOTSTRAP" --verify

git worktree add --detach "$CUR" "$CURRENT_MAIN_SHA"
cd "$CUR"
PYTHONPATH=src:. "$RUNTIME_ROOT/runtime/3.12.14/venv/bin/python" -c 'import pathlib,platform,sqlite3,ssl,pydantic,pytest,aios_core; r=pathlib.Path.cwd().resolve(); a=pathlib.Path(aios_core.__file__).resolve(); assert platform.python_version()=="3.12.14"; assert pydantic.__version__=="2.13.5"; assert pytest.__version__=="8.4.2"; assert sqlite3.sqlite_version=="3.45.1"; assert ssl.OPENSSL_VERSION.split()[1]=="3.0.13"; assert r in a.parents; print("RUNTIME_ENV_OK", platform.python_version(), pydantic.__version__, pytest.__version__, sqlite3.sqlite_version, ssl.OPENSSL_VERSION, a)'

mkdir -p "$OUT"
ARTIFACT="$OUT/aios-c15-resident-runtime-3.12.14.tar.gz"
cd "$RUNTIME_ROOT"
tar --exclude='*/__pycache__/*' --exclude='*.pyc' -czf "$ARTIFACT" runtime/3.12.14
gzip -t "$ARTIFACT"
tar -tzf "$ARTIFACT" | grep -q '^runtime/3.12.14/venv/bin/python'
if tar -tzf "$ARTIFACT" | grep -E '(^|/)(\.git|\.ssh)(/|$)|(^|/)(\.netrc|\.git-credentials|id_rsa|id_ed25519|credentials\.json)
sha256sum "$ARTIFACT" | tee "$OUT/aios-c15-resident-runtime-3.12.14.tar.gz.sha256"

SHA="$(sha256sum "$ARTIFACT" | awk '{print $1}')"
SIZE="$(stat -c '%s' "$ARTIFACT")"
SYS="$(uname -s)"
MACH="$(uname -m)"
KERNEL="$(uname -r)"
GLIBC="$(ldd --version | head -n 1 || true)"

python3 - "$OUT/AIOS_C15_RESIDENT_RUNTIME_3_12_14_MANIFEST.json" "$SHA" "$SIZE" "$SYS" "$MACH" "$KERNEL" "$GLIBC" <<'PY'
import json, sys
path, sha, size, system, machine, kernel, glibc = sys.argv[1:]
manifest = {
  "artifact_type": "AIOS_C15_APPROVED_RESIDENT_RUNTIME",
  "artifact_version": 1,
  "task": "C15-RCC-RES-A-RERUN-005",
  "filename": "aios-c15-resident-runtime-3.12.14.tar.gz",
  "sha256": sha,
  "size_bytes": int(size),
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
  "platform_system": system,
  "platform_machine": machine,
  "kernel": kernel,
  "glibc": glibc,
  "contains_resident_state": False,
  "contains_repository": False,
  "contains_credentials": False
}
with open(path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
    f.write("\n")
PY

python3 - "$OUT" <<'PY'
import hashlib, json, pathlib, sys
out = pathlib.Path(sys.argv[1])
m = json.loads((out/"AIOS_C15_RESIDENT_RUNTIME_3_12_14_MANIFEST.json").read_text())
h = hashlib.sha256((out/m["filename"]).read_bytes()).hexdigest()
assert h == m["sha256"], (h, m["sha256"])
print("MANIFEST_ARTIFACT_SHA_MATCH", h)
PY

echo "RUNTIME_ARTIFACT_READY"
; then
  echo "forbidden credential path detected in runtime archive" >&2
  exit 1
fi
sha256sum "$ARTIFACT" | tee "$OUT/aios-c15-resident-runtime-3.12.14.tar.gz.sha256"

SHA="$(sha256sum "$ARTIFACT" | awk '{print $1}')"
SIZE="$(stat -c '%s' "$ARTIFACT")"
SYS="$(uname -s)"
MACH="$(uname -m)"
KERNEL="$(uname -r)"
GLIBC="$(ldd --version | head -n 1 || true)"

python3 - "$OUT/AIOS_C15_RESIDENT_RUNTIME_3_12_14_MANIFEST.json" "$SHA" "$SIZE" "$SYS" "$MACH" "$KERNEL" "$GLIBC" <<'PY'
import json, sys
path, sha, size, system, machine, kernel, glibc = sys.argv[1:]
manifest = {
  "artifact_type": "AIOS_C15_APPROVED_RESIDENT_RUNTIME",
  "artifact_version": 1,
  "task": "C15-RCC-RES-A-RERUN-005",
  "filename": "aios-c15-resident-runtime-3.12.14.tar.gz",
  "sha256": sha,
  "size_bytes": int(size),
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
  "platform_system": system,
  "platform_machine": machine,
  "kernel": kernel,
  "glibc": glibc,
  "contains_resident_state": False,
  "contains_repository": False,
  "contains_credentials": False
}
with open(path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
    f.write("\n")
PY

python3 - "$OUT" <<'PY'
import hashlib, json, pathlib, sys
out = pathlib.Path(sys.argv[1])
m = json.loads((out/"AIOS_C15_RESIDENT_RUNTIME_3_12_14_MANIFEST.json").read_text())
h = hashlib.sha256((out/m["filename"]).read_bytes()).hexdigest()
assert h == m["sha256"], (h, m["sha256"])
print("MANIFEST_ARTIFACT_SHA_MATCH", h)
PY

echo "RUNTIME_ARTIFACT_READY"
