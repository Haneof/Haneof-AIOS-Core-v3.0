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

sudo mkdir -p "$RUNTIME_ROOT"
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

ELF_MAX_GLIBC="$(readelf --version-info "$RUNTIME_ROOT/runtime/3.12.14/python/bin/python3.12" | grep -o 'GLIBC_[0-9][0-9.]*' | sort -V | uniq | tail -n 1)"
echo "RUNTIME_ELF_MAX_GLIBC $ELF_MAX_GLIBC"
MAX_ALLOWED_GLIBC="GLIBC_2.35"
if [ "$(printf '%s\n%s\n' "$ELF_MAX_GLIBC" "$MAX_ALLOWED_GLIBC" | sort -V | tail -n 1)" != "$MAX_ALLOWED_GLIBC" ]; then
  echo "runtime requires newer glibc than allowed: $ELF_MAX_GLIBC > $MAX_ALLOWED_GLIBC" >&2
  exit 1
fi
export ARTIFACT_ELF_MAX_GLIBC="$ELF_MAX_GLIBC"

mkdir -p "$OUT"
ARTIFACT="$OUT/aios-c15-resident-runtime-3.12.14.tar.gz"
cd "$RUNTIME_ROOT"
tar --exclude='*/__pycache__/*' --exclude='*.pyc' -czf "$ARTIFACT" runtime/3.12.14
gzip -t "$ARTIFACT"
ARCHIVE_LIST="$OUT/aios-c15-resident-runtime-3.12.14.contents.txt"
tar -tzf "$ARTIFACT" > "$ARCHIVE_LIST"
grep -q '^runtime/3.12.14/venv/bin/python' "$ARCHIVE_LIST"

if grep -E '(^|/)(\.git|\.ssh)(/|$)|(^|/)(\.netrc|\.git-credentials|id_rsa|id_ed25519|credentials\.json)

export ARTIFACT_PLATFORM_SYSTEM="$(uname -s)"
export ARTIFACT_PLATFORM_MACHINE="$(uname -m)"
export ARTIFACT_KERNEL="$(uname -r)"
export ARTIFACT_GLIBC="$(ldd --version | head -n 1 || true)"

cd "$GITHUB_WORKSPACE"
python3 operator_artifacts/write_c15_rerun005_runtime_manifest.py "$OUT"

test -s "$OUT/AIOS_C15_RESIDENT_RUNTIME_3_12_14_MANIFEST.json"
test -s "$OUT/aios-c15-resident-runtime-3.12.14.tar.gz.sha256"
echo "RUNTIME_ARTIFACT_READY"
 "$ARCHIVE_LIST"; then
  echo "forbidden credential path detected in runtime archive" >&2
  exit 1
fi

export ARTIFACT_PLATFORM_SYSTEM="$(uname -s)"
export ARTIFACT_PLATFORM_MACHINE="$(uname -m)"
export ARTIFACT_KERNEL="$(uname -r)"
export ARTIFACT_GLIBC="$(ldd --version | head -n 1 || true)"

cd "$GITHUB_WORKSPACE"
python3 operator_artifacts/write_c15_rerun005_runtime_manifest.py "$OUT"

test -s "$OUT/AIOS_C15_RESIDENT_RUNTIME_3_12_14_MANIFEST.json"
test -s "$OUT/aios-c15-resident-runtime-3.12.14.tar.gz.sha256"
echo "RUNTIME_ARTIFACT_READY"
