#!/usr/bin/env bash
# =============================================================================
# AIOS C15 Operator-Prep — Resident-Safe Mechanical Runtime Bootstrap
# -----------------------------------------------------------------------------
# Task      : C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP
# Role      : Resident Launch / Test Infrastructure Operator (NOT a Resident)
# Purpose   : Provision a reproducible, pinned, semantic-free runtime:
#               CPython 3.12.14 + Pydantic 2.13.5 + pytest 8.4.2 + SQLite 3.45.1
#
# Contains  : environment provisioning only.
# Contains NO: C15 fixture payload, event, cursor, evaluator expectation,
#              Resident semantic content, decision, reply, claim or summary.
#
# Idempotent and path-deterministic. Every upstream artifact is pinned by
# SHA-256 and verified before use; every stage fails closed.
#
# Produces (defaults; override with AIOS_RUNTIME_ROOT):
#   <root>/src/                          pinned upstream source tarballs
#   <root>/build/                        build trees
#   <root>/runtime/3.12.14/deps/         zlib + sqlite3 + openssl prefix
#   <root>/runtime/3.12.14/python/       CPython install prefix
#   <root>/runtime/3.12.14/venv/         qualified venv (pydantic + pytest)
#   <root>/runtime/3.12.14/wheelhouse/   hash-pinned wheels + SHA256SUMS
#   <root>/evidence/environment_record.json
#
# Modes:
#   --build   (default) provision/repair the runtime, then verify
#   --verify            verify an existing runtime only (no network, no build)
#   --print-paths       print resolved paths as JSON and exit
#
# Exit codes: 0 = qualified, 1 = usage error, 2 = BLOCKED (precondition failed)
# =============================================================================
set -Eeuo pipefail

# ---------------------------------------------------------------------------
# 0. Pins (exact, immutable; changing any of these invalidates the freeze)
# ---------------------------------------------------------------------------
PY_VERSION="3.12.14"
PY_TAG="v3.12.14"
PY_TAG_OBJECT_SHA="4b65faa0b452113bf130086fb1519be6d9cd9b06"
PY_COMMIT_SHA="2abcf904b8dac8c999d2b3aac76681abb333798a"
PY_TARBALL_URL="https://codeload.github.com/python/cpython/tar.gz/refs/tags/v3.12.14"
PY_TARBALL_SHA256="5b8f5847fc28eea401f7415dc367b8365485ee97f068cd1a0cee124a096bb171"

ZLIB_VERSION="1.3.1"
ZLIB_TARBALL_URL="https://codeload.github.com/madler/zlib/tar.gz/refs/tags/v1.3.1"
ZLIB_TARBALL_SHA256="17e88863f3600672ab49182f217281b6fc4d3c762bde361935e436a95214d05c"

OPENSSL_VERSION="3.0.13"
OPENSSL_TAG="openssl-3.0.13"
OPENSSL_COMMIT_SHA="85cf92f55d9e2ac5aacf92bedd33fb890b9f8b4c"
OPENSSL_TARBALL_URL="https://codeload.github.com/openssl/openssl/tar.gz/refs/tags/openssl-3.0.13"
OPENSSL_TARBALL_SHA256="e74504ed7035295ec7062b1da16c15b57ff2a03cd2064a28d8c39458cacc45fc"

# SQLite amalgamation, exactly SQLITE_VERSION 3.45.1 (matches the formal RC gate
# environment record). Vendored in the npm package better-sqlite3@9.4.1; the npm
# registry publishes an SRI sha512 for that tarball, pinned here as well.
SQLITE_VERSION="3.45.1"
SQLITE_NPM_PKG="better-sqlite3"
SQLITE_NPM_VERSION="9.4.1"
SQLITE_TARBALL_URL="https://registry.npmjs.org/better-sqlite3/-/better-sqlite3-9.4.1.tgz"
SQLITE_TARBALL_SHA256="b813ed754ff786d095fc34da8b8c9203f304d36e3f002dd252b126df80a4734c"
SQLITE_TARBALL_SRI_SHA512="sha512-QpqiQeMI4WkE+dQ68zTMX5OzlPGc7lXIDP1iKUt4Omt9PdaVgzKYxHIJRIzt1E+RUBQoFmkip/IbvzyrxehAIg=="
SQLITE_TARBALL_NPM_SHASUM="006bc6a899a69166c5fe89c9cff64509295d12b2"
SQLITE_C_SHA256="a760118a161b77a79dd9acdd16af324ed059e70d1e7571c504966fc2e40712cc"
SQLITE_H_SHA256="41e066ccd4f89e938f136ceb48c996c54dc381b59fe566dea48864c3750b779e"

# SQLite amalgamation compile flags (recorded in the environment record)
SQLITE_CFLAGS="-DSQLITE_THREADSAFE=1 -DSQLITE_ENABLE_COLUMN_METADATA=1 -DSQLITE_ENABLE_FTS3 -DSQLITE_ENABLE_FTS3_PARENTHESIS -DSQLITE_ENABLE_FTS4 -DSQLITE_ENABLE_FTS5 -DSQLITE_ENABLE_RTREE -DSQLITE_ENABLE_DBSTAT_VTAB=1 -DSQLITE_ENABLE_LOAD_EXTENSION=1 -DSQLITE_ENABLE_JSON1=1 -DSQLITE_ENABLE_MATH_FUNCTIONS=1"

# Qualified python packages (exact versions; wheels pinned by hash at fetch time)
PYDANTIC_VERSION="2.13.5"
PYTEST_VERSION="8.4.2"

# Frozen RC pins (software / repository / Core / tests) — CORE-RC-REFREEZE-003
RC_SOFTWARE_COMMIT="f20f2edfa7af00d0286493fd15196ca9503bc315"
RC_REPO_TREE="1ac3a675b884167d3a29aa432e7ef3eaff94d404"
RC_CORE_TREE="9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623"
RC_TESTS_TREE="7e33b5ef8432370234965d3ccd61248c703c4019"

# ---------------------------------------------------------------------------
# 1. Paths / mode
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT_DEFAULT="$(cd -- "$SCRIPT_DIR/../../../../../.." && pwd -P)"

MODE="build"
case "${1:-}" in
  --build|"") MODE="build" ;;
  --verify) MODE="verify" ;;
  --print-paths) MODE="print-paths" ;;
  -h|--help) sed -n '2,30p' "${BASH_SOURCE[0]}"; exit 0 ;;
  *) echo "usage: $0 [--build|--verify|--print-paths]" >&2; exit 1 ;;
esac

AIOS_RUNTIME_ROOT="${AIOS_RUNTIME_ROOT:-/opt/aios}"
AIOS_REPO_ROOT="${AIOS_REPO_ROOT:-$REPO_ROOT_DEFAULT}"

SRC_DIR="$AIOS_RUNTIME_ROOT/src"
BUILD_DIR="$AIOS_RUNTIME_ROOT/build"
RUNTIME_DIR="$AIOS_RUNTIME_ROOT/runtime/$PY_VERSION"
DEPS_DIR="$RUNTIME_DIR/deps"
PY_PREFIX="$RUNTIME_DIR/python"
VENV_DIR="$RUNTIME_DIR/venv"
WHEELHOUSE_DIR="$RUNTIME_DIR/wheelhouse"
EVIDENCE_DIR="$AIOS_RUNTIME_ROOT/evidence"
PY_MINOR="${PY_VERSION%.*}"
PY="$PY_PREFIX/bin/python$PY_MINOR"
VENV_PY="$VENV_DIR/bin/python"
JOBS="${AIOS_BUILD_JOBS:-$( (nproc 2>/dev/null || echo 2) )}"

json_paths() {
  cat <<JSON
{"aios_runtime_root":"$AIOS_RUNTIME_ROOT","aios_repo_root":"$AIOS_REPO_ROOT","runtime_dir":"$RUNTIME_DIR","deps_dir":"$DEPS_DIR","python_prefix":"$PY_PREFIX","python_bin":"$PY","venv_dir":"$VENV_DIR","venv_python":"$VENV_PY","wheelhouse_dir":"$WHEELHOUSE_DIR","evidence_dir":"$EVIDENCE_DIR"}
JSON
}

if [ "$MODE" = "print-paths" ]; then json_paths; exit 0; fi

log() { printf '[bootstrap] %s\n' "$*" >&2; }
blocked() { printf '[bootstrap] BLOCKED: %s\n' "$*" >&2; exit 2; }

mkdir -p "$SRC_DIR" "$BUILD_DIR" "$RUNTIME_DIR" "$DEPS_DIR" "$EVIDENCE_DIR"

# ---------------------------------------------------------------------------
# 2. Artifact fetch + hash verification (fail closed)
# ---------------------------------------------------------------------------
sha256_of() { sha256sum "$1" | awk '{print $1}'; }

fetch_verified() { # url dest sha256
  local url="$1" dest="$2" want="$3" got
  if [ -f "$dest" ]; then
    got="$(sha256_of "$dest")"
    if [ "$got" = "$want" ]; then log "cached OK $(basename "$dest")"; return 0; fi
    log "cached artifact hash mismatch, refetching: $(basename "$dest")"
    rm -f "$dest"
  fi
  log "fetch $url"
  curl -fsSL --retry 3 --retry-delay 2 -o "$dest.part" "$url" || blocked "cannot fetch $url"
  got="$(sha256_of "$dest.part")"
  if [ "$got" != "$want" ]; then
    rm -f "$dest.part"
    blocked "sha256 mismatch for $url (want $want got $got)"
  fi
  mv -f "$dest.part" "$dest"
}

verify_sri_sha512() { # file expected_sri
  python3 - "$1" "$2" <<'PY'
import base64, hashlib, sys
path, want = sys.argv[1], sys.argv[2]
alg, _, b64 = want.partition("-")
digest = hashlib.new(alg, open(path, "rb").read()).digest()
sys.exit(0 if (alg + "-" + base64.b64encode(digest).decode()) == want else 1)
PY
}

ensure_sources() {
  fetch_verified "$PY_TARBALL_URL" "$SRC_DIR/cpython-$PY_VERSION.tar.gz" "$PY_TARBALL_SHA256"
  fetch_verified "$ZLIB_TARBALL_URL" "$SRC_DIR/zlib-$ZLIB_VERSION.tar.gz" "$ZLIB_TARBALL_SHA256"
  fetch_verified "$OPENSSL_TARBALL_URL" "$SRC_DIR/openssl-$OPENSSL_VERSION.tar.gz" "$OPENSSL_TARBALL_SHA256"
  fetch_verified "$SQLITE_TARBALL_URL" "$SRC_DIR/better-sqlite3-$SQLITE_NPM_VERSION.tgz" "$SQLITE_TARBALL_SHA256"
  verify_sri_sha512 "$SRC_DIR/better-sqlite3-$SQLITE_NPM_VERSION.tgz" "$SQLITE_TARBALL_SRI_SHA512" \
    || blocked "npm SRI sha512 mismatch for better-sqlite3 tarball"
  log "npm SRI sha512 verified for $SQLITE_NPM_PKG@$SQLITE_NPM_VERSION"

  local sq="$BUILD_DIR/sqlite-$SQLITE_VERSION"
  if [ ! -f "$sq/sqlite3.c" ]; then
    mkdir -p "$sq"
    tar xzf "$SRC_DIR/better-sqlite3-$SQLITE_NPM_VERSION.tgz" -C "$sq" \
      --strip-components=3 --wildcards 'package/deps/sqlite3/sqlite3.c' 'package/deps/sqlite3/sqlite3.h'
  fi
  local csha hsha
  csha="$(sha256_of "$sq/sqlite3.c")"
  hsha="$(sha256_of "$sq/sqlite3.h")"
  [ "$csha" = "$SQLITE_C_SHA256" ] || blocked "sqlite3.c sha256 mismatch (want $SQLITE_C_SHA256 got $csha)"
  [ "$hsha" = "$SQLITE_H_SHA256" ] || blocked "sqlite3.h sha256 mismatch (want $SQLITE_H_SHA256 got $hsha)"
  grep -q "#define SQLITE_VERSION        \"$SQLITE_VERSION\"" "$sq/sqlite3.c" \
    || blocked "vendored amalgamation is not SQLITE_VERSION $SQLITE_VERSION"
  log "sqlite amalgamation verified: $SQLITE_VERSION c=$csha"
}

# ---------------------------------------------------------------------------
# 3. Dependency prefix (zlib + sqlite3 + openssl)
# ---------------------------------------------------------------------------
deps_fingerprint() {
  printf '%s|%s|%s|%s|%s|%s\n' \
    "$ZLIB_VERSION" "$ZLIB_TARBALL_SHA256" "$SQLITE_VERSION" "$SQLITE_C_SHA256" \
    "$OPENSSL_VERSION" "$OPENSSL_TARBALL_SHA256" | sha256sum | awk '{print substr($1,1,16)}'
}

build_deps() {
  if [ ! -f "$DEPS_DIR/.stamp-zlib-$ZLIB_VERSION" ]; then
    [ -d "$BUILD_DIR/zlib-$ZLIB_VERSION" ] || tar xzf "$SRC_DIR/zlib-$ZLIB_VERSION.tar.gz" -C "$BUILD_DIR"
    log "build zlib $ZLIB_VERSION"
    ( cd "$BUILD_DIR/zlib-$ZLIB_VERSION" && ./configure --prefix="$DEPS_DIR" >/dev/null \
      && make -j"$JOBS" >/dev/null && make install >/dev/null )
    touch "$DEPS_DIR/.stamp-zlib-$ZLIB_VERSION"
  fi

  if [ ! -f "$DEPS_DIR/.stamp-sqlite-$SQLITE_VERSION" ]; then
    local sq="$BUILD_DIR/sqlite-$SQLITE_VERSION"
    log "build sqlite $SQLITE_VERSION"
    # shellcheck disable=SC2086
    gcc -O2 -fPIC -shared $SQLITE_CFLAGS -Wl,-soname,libsqlite3.so.0 \
      -o "$DEPS_DIR/lib/libsqlite3.so.$SQLITE_VERSION" "$sq/sqlite3.c" -lpthread -ldl -lm
    ln -sf "libsqlite3.so.$SQLITE_VERSION" "$DEPS_DIR/lib/libsqlite3.so.0"
    ln -sf "libsqlite3.so.$SQLITE_VERSION" "$DEPS_DIR/lib/libsqlite3.so"
    # shellcheck disable=SC2086
    gcc -O2 -fPIC -c $SQLITE_CFLAGS -o "$sq/sqlite3.o" "$sq/sqlite3.c"
    ar rcs "$DEPS_DIR/lib/libsqlite3.a" "$sq/sqlite3.o"
    cp "$sq/sqlite3.h" "$DEPS_DIR/include/sqlite3.h"
    touch "$DEPS_DIR/.stamp-sqlite-$SQLITE_VERSION"
  fi

  if [ ! -f "$DEPS_DIR/.stamp-openssl-$OPENSSL_VERSION" ]; then
    if [ ! -f "$BUILD_DIR/openssl-$OPENSSL_VERSION/Configure" ]; then
      rm -rf "$BUILD_DIR/openssl-$OPENSSL_VERSION"
      mkdir -p "$BUILD_DIR/openssl-$OPENSSL_VERSION"
      tar xzf "$SRC_DIR/openssl-$OPENSSL_VERSION.tar.gz" \
        -C "$BUILD_DIR/openssl-$OPENSSL_VERSION" --strip-components=1
    fi
    log "build openssl $OPENSSL_VERSION (several minutes)"
    ( cd "$BUILD_DIR/openssl-$OPENSSL_VERSION" \
      && ./Configure --prefix="$DEPS_DIR" --openssldir="$DEPS_DIR/ssl" --libdir=lib shared no-tests \
           >configure.log 2>&1 || { tail -30 configure.log >&2; blocked "openssl configure failed"; } )
    ( cd "$BUILD_DIR/openssl-$OPENSSL_VERSION" \
      && make -j"$JOBS" >make.log 2>&1 || { tail -40 make.log >&2; blocked "openssl make failed"; } \
      && make install_sw >install.log 2>&1 || { tail -40 install.log >&2; blocked "openssl install failed"; } )
    touch "$DEPS_DIR/.stamp-openssl-$OPENSSL_VERSION"
  fi
  log "deps prefix ready: $DEPS_DIR (fingerprint $(deps_fingerprint))"
}

# ---------------------------------------------------------------------------
# 4. CPython build
# ---------------------------------------------------------------------------
build_cpython() {
  local fingerprint stamp
  fingerprint="$(deps_fingerprint)"
  stamp="$RUNTIME_DIR/.stamp-cpython-$PY_VERSION-$fingerprint"
  if [ -f "$stamp" ] && [ -x "$PY" ]; then
    log "cpython already built (stamp $fingerprint)"
    return 0
  fi
  log "building cpython $PY_VERSION against deps fingerprint $fingerprint"
  rm -rf "$BUILD_DIR/cpython-$PY_VERSION" "$PY_PREFIX"
  mkdir -p "$PY_PREFIX"
  tar xzf "$SRC_DIR/cpython-$PY_VERSION.tar.gz" -C "$BUILD_DIR"
  (
    cd "$BUILD_DIR/cpython-$PY_VERSION"
    CPPFLAGS="-I$DEPS_DIR/include" \
    LDFLAGS="-L$DEPS_DIR/lib -Wl,-rpath,$DEPS_DIR/lib -Wl,-rpath-link,$DEPS_DIR/lib" \
    LD_LIBRARY_PATH="$DEPS_DIR/lib" \
      ./configure --prefix="$PY_PREFIX" \
        --with-openssl="$DEPS_DIR" \
        --with-ensurepip=install \
        --enable-loadable-sqlite-extensions \
        >> configure.log 2>&1 || { tail -30 configure.log >&2; blocked "cpython configure failed"; }
  )
  log "make -j$JOBS (several minutes)"
  ( cd "$BUILD_DIR/cpython-$PY_VERSION" && make -j"$JOBS" >> make.log 2>&1 ) \
    || { tail -40 "$BUILD_DIR/cpython-$PY_VERSION/make.log" >&2; blocked "cpython make failed"; }
  ( cd "$BUILD_DIR/cpython-$PY_VERSION" && make install >> install.log 2>&1 ) \
    || { tail -40 "$BUILD_DIR/cpython-$PY_VERSION/install.log" >&2; blocked "cpython install failed"; }
  rm -f "$RUNTIME_DIR"/.stamp-cpython-*
  touch "$stamp"
  rm -rf "$VENV_DIR"
  log "cpython installed at $PY_PREFIX"
}

# ---------------------------------------------------------------------------
# 5. Qualified venv + hash-pinned wheels
# ---------------------------------------------------------------------------
ensure_wheelhouse() {
  mkdir -p "$WHEELHOUSE_DIR"
  local lock_file="$SCRIPT_DIR/PYTHON_WHEEL_LOCK.json"
  local verifier="$SCRIPT_DIR/wheel_lock.py"
  [ -f "$lock_file" ] || blocked "pre-frozen Python wheel lock is missing: $lock_file"
  [ -f "$verifier" ] || blocked "wheel-lock verifier is missing: $verifier"

  # acquire verifies every downloaded byte against the source-controlled lock
  # before a .whl is accepted. It rejects missing/extra artifacts as a closed set.
  python3 "$verifier" acquire --lock "$lock_file" --wheelhouse "$WHEELHOUSE_DIR" \
    || blocked "pre-frozen wheel-lock acquisition/verification failed"
  ( cd "$WHEELHOUSE_DIR" && sha256sum ./*.whl > SHA256SUMS ) \
    || blocked "cannot write post-download wheel evidence"
  python3 "$verifier" verify --lock "$lock_file" --wheelhouse "$WHEELHOUSE_DIR" \
    > "$EVIDENCE_DIR/wheel_lock_verification.json" \
    || blocked "wheelhouse failed final closed-set verification"
  log "pre-frozen wheel lock verified: $(wc -l < "$WHEELHOUSE_DIR/SHA256SUMS") exact wheels"
}

build_venv() {
  if [ ! -x "$VENV_PY" ]; then
    log "create venv at $VENV_DIR"
    "$PY" -m venv "$VENV_DIR" || blocked "venv creation failed"
  fi
  ensure_wheelhouse
  if [ ! -f "$VENV_DIR/.stamp-deps-$PYDANTIC_VERSION-$PYTEST_VERSION" ]; then
    local lock_file="$SCRIPT_DIR/PYTHON_WHEEL_LOCK.json"
    local verifier="$SCRIPT_DIR/wheel_lock.py"
    mapfile -t LOCKED_WHEELS < <(python3 "$verifier" list --lock "$lock_file" --wheelhouse "$WHEELHOUSE_DIR")
    [ "${#LOCKED_WHEELS[@]}" -eq 11 ] || blocked "locked wheel list is not the exact 11-artifact dependency/bootstrap closure"
    "$VENV_PY" -m pip install --quiet --disable-pip-version-check --no-index --no-deps \
      "${LOCKED_WHEELS[@]}" || blocked "offline no-dependency-resolution wheel installation failed"
    touch "$VENV_DIR/.stamp-deps-$PYDANTIC_VERSION-$PYTEST_VERSION"
  fi
  "$VENV_PY" -m pip freeze --all > "$RUNTIME_DIR/requirements.lock.txt"
  log "venv ready from prelocked local wheel files only: $VENV_DIR"
}

# ---------------------------------------------------------------------------
# 6. Verification (version triple, stdlib modules, frozen RC identity)
# ---------------------------------------------------------------------------
probe_json() {
  AIOS_REPO_ROOT="$AIOS_REPO_ROOT" "$VENV_PY" - <<'PY'
import importlib.metadata, json, os, platform, sqlite3, sys, sysconfig
sys.path.insert(0, os.path.join(os.environ["AIOS_REPO_ROOT"], "src"))
import aios_core
out = {
    "python_version": platform.python_version(),
    "python_version_info": list(sys.version_info[:3]),
    "python_full_version": sys.version.split()[0],
    "implementation": platform.python_implementation(),
    "config_args": sysconfig.get_config_var("CONFIG_ARGS"),
    "prefix": sys.prefix,
    "base_prefix": sys.base_prefix,
    "executable": sys.executable,
    "sqlite_version": sqlite3.sqlite_version,
    "sqlite_module_version": getattr(sqlite3, "version", None),
    "aios_core_file": aios_core.__file__,
    "installed_distributions": sorted(
        {f"{distribution.metadata['Name']}=={distribution.version}" for distribution in importlib.metadata.distributions()},
        key=str.lower,
    ),
}
for name, module in (("pydantic", "pydantic"), ("pytest", "pytest"), ("open_ssl", "ssl")):
    try:
        imported = __import__(module)
        out[name + "_version"] = getattr(imported, "VERSION", None) or getattr(imported, "__version__", None) or getattr(imported, "OPENSSL_VERSION", None)
    except Exception as exc:
        out[name + "_version"] = "MISSING:%s" % type(exc).__name__
modules = {}
for name in ("sqlite3", "hashlib", "zlib", "ssl", "uuid", "zoneinfo", "unicodedata",
             "socket", "fcntl", "secrets", "ctypes", "readline", "bz2", "lzma", "decimal"):
    try:
        __import__(name)
        modules[name] = "ok"
    except Exception as exc:
        modules[name] = "unavailable:%s" % type(exc).__name__
out["stdlib_modules"] = modules
try:
    out["openssl_runtime_version"] = __import__("ssl").OPENSSL_VERSION
except Exception:
    out["openssl_runtime_version"] = None
print(json.dumps(out, indent=2))
PY
}

verify_runtime() {
  [ -x "$VENV_PY" ] || blocked "venv python missing ($VENV_PY)"
  python3 "$SCRIPT_DIR/wheel_lock.py" verify \
    --lock "$SCRIPT_DIR/PYTHON_WHEEL_LOCK.json" --wheelhouse "$WHEELHOUSE_DIR" \
    > "$EVIDENCE_DIR/wheel_lock_verification.json" \
    || blocked "pre-frozen wheel trust root verification failed"
  local out pyv pyd yt sq
  out="$(probe_json)" || blocked "python self-check failed"
  printf '%s\n' "$out" > "$EVIDENCE_DIR/environment_probe.json"
  pyv="$(printf '%s' "$out" | python3 -c 'import json,sys;print(json.load(sys.stdin)["python_version"])')"
  pyd="$(printf '%s' "$out" | python3 -c 'import json,sys;print(json.load(sys.stdin)["pydantic_version"])')"
  yt="$(printf '%s' "$out" | python3 -c 'import json,sys;print(json.load(sys.stdin)["pytest_version"])')"
  sq="$(printf '%s' "$out" | python3 -c 'import json,sys;print(json.load(sys.stdin)["sqlite_version"])')"
  [ "$pyv" = "$PY_VERSION" ] || blocked "python version mismatch: want $PY_VERSION got $pyv"
  [ "$pyd" = "$PYDANTIC_VERSION" ] || blocked "pydantic version mismatch: want $PYDANTIC_VERSION got $pyd"
  [ "$yt" = "$PYTEST_VERSION" ] || blocked "pytest version mismatch: want $PYTEST_VERSION got $yt"
  "$VENV_PY" -c 'import sqlite3, hashlib, ssl; sqlite3.connect(":memory:").execute("select 1"); hashlib.sha256(b"x").hexdigest(); assert ssl.OPENSSL_VERSION' \
    || blocked "sqlite3/hashlib/ssl functional check failed"
  log "version triple OK: python=$pyv pydantic=$pyd pytest=$yt sqlite=$sq"

  if [ -d "$AIOS_REPO_ROOT/.git" ] && command -v git >/dev/null 2>&1; then
    local core_tree tests_tree sw_tree
    core_tree="$(git -C "$AIOS_REPO_ROOT" rev-parse "$RC_SOFTWARE_COMMIT:src/aios_core" 2>/dev/null || echo MISSING)"
    tests_tree="$(git -C "$AIOS_REPO_ROOT" rev-parse "$RC_SOFTWARE_COMMIT:tests" 2>/dev/null || echo MISSING)"
    sw_tree="$(git -C "$AIOS_REPO_ROOT" rev-parse "$RC_SOFTWARE_COMMIT^{tree}" 2>/dev/null || echo MISSING)"
    [ "$core_tree" = "$RC_CORE_TREE" ] || blocked "frozen Core tree mismatch ($core_tree)"
    [ "$tests_tree" = "$RC_TESTS_TREE" ] || blocked "frozen tests tree mismatch ($tests_tree)"
    [ "$sw_tree" = "$RC_REPO_TREE" ] || blocked "frozen repository tree mismatch ($sw_tree)"
    log "frozen RC identity OK: software=$RC_SOFTWARE_COMMIT core=$core_tree tests=$tests_tree"
  else
    log "WARNING: repo git metadata unavailable; frozen RC identity not machine-verified here"
  fi
}

# ---------------------------------------------------------------------------
# 7. Environment record
# ---------------------------------------------------------------------------
emit_environment_record() {
  local record="$EVIDENCE_DIR/environment_record.json"
  PY_VERSION="$PY_VERSION" PYDANTIC_VERSION="$PYDANTIC_VERSION" PYTEST_VERSION="$PYTEST_VERSION" \
  SQLITE_VERSION="$SQLITE_VERSION" OPENSSL_VERSION="$OPENSSL_VERSION" \
  PY_TARBALL_URL="$PY_TARBALL_URL" PY_TARBALL_SHA256="$PY_TARBALL_SHA256" \
  PY_TAG="$PY_TAG" PY_TAG_OBJECT_SHA="$PY_TAG_OBJECT_SHA" PY_COMMIT_SHA="$PY_COMMIT_SHA" \
  ZLIB_VERSION="$ZLIB_VERSION" ZLIB_TARBALL_URL="$ZLIB_TARBALL_URL" ZLIB_TARBALL_SHA256="$ZLIB_TARBALL_SHA256" \
  OPENSSL_TAG="$OPENSSL_TAG" OPENSSL_COMMIT_SHA="$OPENSSL_COMMIT_SHA" \
  OPENSSL_TARBALL_URL="$OPENSSL_TARBALL_URL" OPENSSL_TARBALL_SHA256="$OPENSSL_TARBALL_SHA256" \
  SQLITE_TARBALL_URL="$SQLITE_TARBALL_URL" SQLITE_TARBALL_SHA256="$SQLITE_TARBALL_SHA256" \
  SQLITE_TARBALL_SRI_SHA512="$SQLITE_TARBALL_SRI_SHA512" SQLITE_TARBALL_NPM_SHASUM="$SQLITE_TARBALL_NPM_SHASUM" \
  SQLITE_NPM_PKG="$SQLITE_NPM_PKG" SQLITE_NPM_VERSION="$SQLITE_NPM_VERSION" SQLITE_CFLAGS="$SQLITE_CFLAGS" \
  SQLITE_C_SHA256="$SQLITE_C_SHA256" SQLITE_H_SHA256="$SQLITE_H_SHA256" \
  RC_SOFTWARE_COMMIT="$RC_SOFTWARE_COMMIT" RC_REPO_TREE="$RC_REPO_TREE" RC_CORE_TREE="$RC_CORE_TREE" RC_TESTS_TREE="$RC_TESTS_TREE" \
  AIOS_RUNTIME_ROOT="$AIOS_RUNTIME_ROOT" AIOS_REPO_ROOT="$AIOS_REPO_ROOT" \
  RUNTIME_DIR="$RUNTIME_DIR" DEPS_DIR="$DEPS_DIR" PY_PREFIX="$PY_PREFIX" VENV_DIR="$VENV_DIR" \
  WHEELHOUSE_DIR="$WHEELHOUSE_DIR" VENV_PY="$VENV_PY" DEPS_FINGERPRINT="$(deps_fingerprint)" \
  python3 - "$record" <<'PY'
import datetime, hashlib, json, os, platform, subprocess, sys

def sha256_file(path):
    try:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except Exception:
        return None

def identity(path):
    return {"path": path, "sha256": sha256_file(path), "size": os.path.getsize(path) if os.path.isfile(path) else None}

def cmd(*args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception:
        return None

e = os.environ
evidence_dir = os.path.dirname(os.path.abspath(sys.argv[1]))
probe = {}
probe_path = os.path.join(evidence_dir, "environment_probe.json")
if os.path.isfile(probe_path):
    try:
        probe = json.load(open(probe_path))
    except Exception:
        probe = {}

wheelhouse = e["WHEELHOUSE_DIR"]
wheels = []
if os.path.isdir(wheelhouse):
    for name in sorted(os.listdir(wheelhouse)):
        if name.endswith(".whl"):
            path = os.path.join(wheelhouse, name)
            wheels.append({"wheel": name, "sha256": sha256_file(path), "size": os.path.getsize(path)})

core_root = os.path.join(e["AIOS_REPO_ROOT"], "src", "aios_core")
core_files = []
if os.path.isdir(core_root):
    for root, dirs, files in os.walk(core_root):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in sorted(files):
            path = os.path.join(root, name)
            core_files.append({"path": os.path.relpath(path, core_root).replace(os.sep, "/"),
                               "sha256": sha256_file(path)})
core_manifest_sha256 = hashlib.sha256(json.dumps(core_files, sort_keys=True, separators=(",", ":")).encode()).hexdigest() if core_files else None

record = {
    "record_version": 1,
    "task_id": "C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP",
    "role": "Resident Launch / Test Infrastructure Operator (non-Resident)",
    "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "runtime_root": e["AIOS_RUNTIME_ROOT"],
    "repo_root": e["AIOS_REPO_ROOT"],
    "paths": {"deps": e["DEPS_DIR"], "python_prefix": e["PY_PREFIX"], "venv": e["VENV_DIR"],
              "wheelhouse": wheelhouse, "venv_python": e["VENV_PY"]},
    "deps_fingerprint": e["DEPS_FINGERPRINT"],
    "pins": {
        "cpython": {"version": e["PY_VERSION"], "tag": e["PY_TAG"], "tag_object_sha": e["PY_TAG_OBJECT_SHA"],
                    "commit_sha": e["PY_COMMIT_SHA"], "source_url": e["PY_TARBALL_URL"],
                    "source_sha256": e["PY_TARBALL_SHA256"]},
        "zlib": {"version": e["ZLIB_VERSION"], "source_url": e["ZLIB_TARBALL_URL"], "source_sha256": e["ZLIB_TARBALL_SHA256"]},
        "openssl": {"version": e["OPENSSL_VERSION"], "tag": e["OPENSSL_TAG"], "commit_sha": e["OPENSSL_COMMIT_SHA"],
                    "source_url": e["OPENSSL_TARBALL_URL"], "source_sha256": e["OPENSSL_TARBALL_SHA256"]},
        "sqlite": {"version": e["SQLITE_VERSION"], "npm_package": e["SQLITE_NPM_PKG"], "npm_version": e["SQLITE_NPM_VERSION"],
                   "source_url": e["SQLITE_TARBALL_URL"], "source_sha256": e["SQLITE_TARBALL_SHA256"],
                   "npm_sri_sha512": e["SQLITE_TARBALL_SRI_SHA512"], "npm_shasum": e["SQLITE_TARBALL_NPM_SHASUM"],
                   "amalgamation_c_sha256": e["SQLITE_C_SHA256"], "amalgamation_h_sha256": e["SQLITE_H_SHA256"],
                   "compile_flags": e["SQLITE_CFLAGS"].split()},
        "pydantic": {"version": e["PYDANTIC_VERSION"]},
        "pytest": {"version": e["PYTEST_VERSION"]},
        "frozen_rc": {"software": e["RC_SOFTWARE_COMMIT"], "repository_tree": e["RC_REPO_TREE"],
                      "core_tree": e["RC_CORE_TREE"], "tests_tree": e["RC_TESTS_TREE"]},
    },
    "observed": {
        "python_version": probe.get("python_version"),
        "python_full_version": probe.get("python_full_version"),
        "implementation": probe.get("implementation"),
        "config_args": probe.get("config_args"),
        "pydantic_version": probe.get("pydantic_version"),
        "pytest_version": probe.get("pytest_version"),
        "sqlite_version": probe.get("sqlite_version"),
        "sqlite_module_version": probe.get("sqlite_module_version"),
        "openssl_version": probe.get("open_ssl_version"),
        "openssl_runtime_version": probe.get("openssl_runtime_version"),
        "stdlib_modules": probe.get("stdlib_modules"),
        "venv_prefix": probe.get("prefix"),
        "venv_base_prefix": probe.get("base_prefix"),
        "executable": probe.get("executable"),
        "aios_core_file": probe.get("aios_core_file"),
        "installed_distributions": probe.get("installed_distributions", []),
    },
    "system": {
        "os": platform.platform(),
        "os_release": dict(line.split("=", 1) for line in open("/etc/os-release").read().splitlines() if "=" in line) if os.path.isfile("/etc/os-release") else {},
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "libc": " ".join(platform.libc_ver()),
        "glibc_version": cmd("getconf", "GNU_LIBC_VERSION"),
        "cpu_count": os.cpu_count(),
        "tzdata_dir_present": os.path.isdir("/usr/share/zoneinfo"),
    },
    "artifacts": {
        "venv_python": identity(e["VENV_PY"]),
        "sqlite_shared_lib": identity(os.path.join(e["DEPS_DIR"], "lib", "libsqlite3.so." + e["SQLITE_VERSION"])),
        "openssl_libssl": identity(os.path.join(e["DEPS_DIR"], "lib", "libssl.so.3")),
        "requirements_lock": identity(os.path.join(e["RUNTIME_DIR"], "requirements.lock.txt")),
    },
    "wheels": wheels,
    "frozen_core_content_manifest_sha256": core_manifest_sha256,
    "frozen_core_file_count": len(core_files),
    "bootstrap": {"script": "bootstrap_runtime.sh", "deterministic": True, "resident_safe": True,
                  "contains_c15_semantics": False,
                  "repairable": "rerun this script with --build; pass --verify for offline verification only"},
}
with open(sys.argv[1], "w") as handle:
    json.dump(record, handle, indent=2)
    handle.write("\n")
print(json.dumps({"environment_record": sys.argv[1], "python": record["observed"]["python_version"],
                  "pydantic": record["observed"]["pydantic_version"], "pytest": record["observed"]["pytest_version"],
                  "sqlite": record["observed"]["sqlite_version"],
                  "core_content_manifest_sha256": core_manifest_sha256}, indent=2))
PY
}

# ---------------------------------------------------------------------------
# 8. Main
# ---------------------------------------------------------------------------
case "$MODE" in
  verify)
    verify_runtime
    emit_environment_record
    log "VERIFY OK"
    ;;
  build)
    ensure_sources
    build_deps
    build_cpython
    build_venv
    verify_runtime
    emit_environment_record
    log "BUILD OK — qualified runtime at $RUNTIME_DIR"
    json_paths
    ;;
esac
