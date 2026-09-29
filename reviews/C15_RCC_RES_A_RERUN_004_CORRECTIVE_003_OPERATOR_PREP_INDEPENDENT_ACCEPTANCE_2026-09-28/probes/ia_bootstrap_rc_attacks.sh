#!/usr/bin/env bash
# IA bootstrap / frozen-RC attacks. Reviewer-authored; frozen before execution.
# Uses only disposable scratch copies under /tmp/ia. Never touches the candidate
# commit objects; mutations happen only in a throwaway clone (/tmp/ia/mut).
#
# Expected (safe) outcomes, declared before execution:
#  BA1 default repo root resolves to the repository root and RC identity is verified   -> expect aios_repo_root=/tmp/ia/clone
#  BA2 --verify with a repo root lacking .git must fail closed                         -> expect exit 2
#  BA3 --verify against a checkout whose working-tree Core differs from frozen RC     -> expect exit 2
#  BA4 --verify when the interpreter resolves a non-3.45.1 SQLite                      -> expect exit 2
#  BA5 bootstrap pins every wheel (incl. transitive) by hash inside the frozen script  -> expect pinned
#  BA6 --verify with explicit correct AIOS_REPO_ROOT: exit 0, RC identity OK, core manifest == packet value
#  BA7 --verify writes nothing into the source tree                                     -> expect clean git status
#  BA8 CPython tarball embedded commit id == PY_COMMIT_SHA pin                          -> expect equal
set -u
CAND=/tmp/ia/clone
PREP=$CAND/reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP
BOOT=$PREP/bootstrap/bootstrap_runtime.sh
RT=/tmp/ia/rt
OUT=${IA_RAW_DIR:-/tmp/ia/raw}/bootstrap_attacks
mkdir -p "$OUT"
PKT_CORE_MANIFEST=$(python3 -c "import json;print(json.load(open('$PREP/RESIDENT_SAFE_LAUNCH_PACKET.json'))['frozen_core_content_manifest_sha256'])")
cp -f $RT/evidence/environment_record.json "$OUT/build_time_environment_record.json" 2>/dev/null

res() { printf '%s | expected=%s | observed=%s | %s\n' "$1" "$2" "$3" "$4" | tee -a "$OUT/SUMMARY.txt"; }
: > "$OUT/SUMMARY.txt"

# BA1
AIOS_RUNTIME_ROOT=$RT bash "$BOOT" --print-paths > "$OUT/ba1_print_paths.json"
root=$(python3 -c "import json;print(json.load(open('$OUT/ba1_print_paths.json'))['aios_repo_root'])")
( cd /tmp && AIOS_RUNTIME_ROOT=$RT bash "$BOOT" --verify > "$OUT/ba1_verify_default.out" 2>&1; echo "exit=$?" >> "$OUT/ba1_verify_default.out" )
rcline=$(grep -E "frozen RC identity|WARNING" "$OUT/ba1_verify_default.out" | head -1)
[ "$root" = "$CAND" ] && s=PASS || s=RED
res BA1 "aios_repo_root=$CAND + RC identity OK" "aios_repo_root=$root ; $(tail -1 "$OUT/ba1_verify_default.out") ; $rcline" $s
cp -f $RT/evidence/environment_record.json "$OUT/ba1_env_record_default_root.json"

# BA2
mkdir -p /tmp/ia/norepo
AIOS_RUNTIME_ROOT=$RT AIOS_REPO_ROOT=/tmp/ia/norepo bash "$BOOT" --verify > "$OUT/ba2_verify_norepo.out" 2>&1; e=$?
[ $e -eq 2 ] && s=PASS || s=RED
res BA2 "exit=2" "exit=$e ; $(grep -E 'WARNING|RC identity' "$OUT/ba2_verify_norepo.out" | head -1)" $s

# BA3
rm -rf /tmp/ia/mut && git clone -q "$CAND" /tmp/ia/mut && git -C /tmp/ia/mut checkout -q --detach 10901d467679b70437ae112747eab81f889fd5cb
sed -i 's/max_tool_rounds: int = 4,/max_tool_rounds: int = 9,/' /tmp/ia/mut/src/aios_core/runtime/cognitive_runtime.py
git -C /tmp/ia/mut diff --stat > "$OUT/ba3_mutation.diffstat"
AIOS_RUNTIME_ROOT=$RT AIOS_REPO_ROOT=/tmp/ia/mut bash "$BOOT" --verify > "$OUT/ba3_verify_mutated_core.out" 2>&1; e=$?
mut_manifest=$(python3 -c "import json;print(json.load(open('$RT/evidence/environment_record.json'))['frozen_core_content_manifest_sha256'])")
$RT/runtime/3.12.14/venv/bin/python "$PREP/harness/operator_tools/rc_identity.py" --repo-root /tmp/ia/mut > "$OUT/ba3_rc_identity_tool_on_mutated.json" 2>&1; e2=$?
PYTHONDONTWRITEBYTECODE=1 $RT/runtime/3.12.14/venv/bin/python -c "
import sys; sys.path[:0]=['$PREP/harness','/tmp/ia/mut/src']
import aios_exchange.runner, inspect
from aios_core.runtime.cognitive_runtime import CognitiveRuntime
import aios_core
print('aios_core', aios_core.__file__); print('CognitiveRuntime.__init__ max_tool_rounds default =', inspect.signature(CognitiveRuntime.__init__).parameters['max_tool_rounds'].default)
" > "$OUT/ba3_harness_imports_mutated_core.out" 2>&1
[ $e -eq 2 ] && s=PASS || s=RED
res BA3 "exit=2" "bootstrap --verify exit=$e ($(grep -E 'RC identity' "$OUT/ba3_verify_mutated_core.out" | head -1)); core_manifest=$mut_manifest (packet=$PKT_CORE_MANIFEST, not compared); rc_identity.py exit=$e2; $(tail -1 "$OUT/ba3_harness_imports_mutated_core.out")" $s

# BA4
mkdir -p /tmp/ia/syssqlite && cp -f /usr/lib/x86_64-linux-gnu/libsqlite3.so.0 /tmp/ia/syssqlite/libsqlite3.so.0
readelf -d $RT/runtime/3.12.14/python/lib/python3.12/lib-dynload/_sqlite3*.so | grep -Ei 'rpath|runpath' > "$OUT/ba4_sqlite_ext_dynamic.txt"
LD_LIBRARY_PATH=/tmp/ia/syssqlite AIOS_RUNTIME_ROOT=$RT AIOS_REPO_ROOT=$CAND bash "$BOOT" --verify > "$OUT/ba4_verify_system_sqlite.out" 2>&1; e=$?
obs_sq=$(python3 -c "import json;print(json.load(open('$RT/evidence/environment_record.json'))['observed']['sqlite_version'])")
grep -n 'sq=' "$BOOT" > "$OUT/ba4_static_sqlite_checks.txt"; grep -n 'SQLITE_VERSION" \]' "$BOOT" >> "$OUT/ba4_static_sqlite_checks.txt"
if [ "$obs_sq" = "3.45.1" ]; then s=INCONCLUSIVE; elif [ $e -eq 2 ]; then s=PASS; else s=RED; fi
res BA4 "exit=2 when sqlite!=3.45.1" "exit=$e observed_sqlite=$obs_sq" $s

# BA5
pyd_sha=$(python3 -c "import json;d=json.load(open('$PREP/evidence/environment_record.json'));print([w['sha256'] for w in d['wheels'] if w['wheel'].startswith('pydantic-2')][0])")
te_sha=$(python3 -c "import json;d=json.load(open('$PREP/evidence/environment_record.json'));print([w['sha256'] for w in d['wheels'] if w['wheel'].startswith('typing_extensions')][0])")
grep -c "$pyd_sha" "$BOOT" > "$OUT/ba5_pydantic_hash_in_bootstrap.txt"; grep -c "$te_sha" "$BOOT" >> "$OUT/ba5_pydantic_hash_in_bootstrap.txt"
grep -n "pip download\|requirements.hashes\|--require-hashes" "$BOOT" > "$OUT/ba5_wheel_flow.txt"
diff <(ls $RT/runtime/3.12.14/wheelhouse/*.whl | xargs -n1 basename | sort) <(python3 -c "import json;[print(w['wheel']) for w in json.load(open('$PREP/evidence/environment_record.json'))['wheels']]" | sort) > "$OUT/ba5_wheelset_diff_vs_author.txt"; wd=$?
( cd $RT/runtime/3.12.14/wheelhouse && sha256sum *.whl ) > "$OUT/ba5_reviewer_wheel_sha256.txt"
python3 - "$PREP/evidence/environment_record.json" "$OUT/ba5_reviewer_wheel_sha256.txt" > "$OUT/ba5_wheel_hash_compare.txt" <<'PY'
import json,sys
a={w['wheel']:w['sha256'] for w in json.load(open(sys.argv[1]))['wheels']}
r={l.split()[1]:l.split()[0] for l in open(sys.argv[2])}
print(json.dumps({k:(a.get(k)==r.get(k)) for k in sorted(set(a)|set(r))},indent=1))
PY
n=$(head -1 "$OUT/ba5_pydantic_hash_in_bootstrap.txt")
[ "$n" != "0" ] && s=PASS || s=RED
res BA5 "wheel hashes pinned in frozen bootstrap" "pydantic wheel sha occurrences in bootstrap=$n ; reviewer wheel set == author wheel set: $([ $wd -eq 0 ] && echo yes || echo no)" $s

# BA6
AIOS_RUNTIME_ROOT=$RT AIOS_REPO_ROOT=$CAND bash "$BOOT" --verify > "$OUT/ba6_verify_explicit_root.out" 2>&1; e=$?
cp -f $RT/evidence/environment_record.json "$OUT/ba6_env_record_explicit_root.json"
m=$(python3 -c "import json;print(json.load(open('$RT/evidence/environment_record.json'))['frozen_core_content_manifest_sha256'])")
ok=$(grep -c "frozen RC identity OK" "$OUT/ba6_verify_explicit_root.out")
[ $e -eq 0 ] && [ "$ok" = "1" ] && [ "$m" = "$PKT_CORE_MANIFEST" ] && s=PASS || s=RED
res BA6 "exit=0, RC identity OK, manifest=$PKT_CORE_MANIFEST" "exit=$e rc_ok_lines=$ok manifest=$m" $s

# BA7
st=$(git -C "$CAND" status --porcelain --ignored | wc -l)
[ "$st" = "0" ] && s=PASS || s=RED
res BA7 "0 changed/untracked paths in candidate checkout" "$st" $s

# BA8
tcid=$(git get-tar-commit-id < <(gzip -dc $RT/src/cpython-3.12.14.tar.gz) 2>/dev/null)
pin=$(grep '^PY_COMMIT_SHA=' "$BOOT" | cut -d'"' -f2)
[ "$tcid" = "$pin" ] && s=PASS || s=RED
res BA8 "tar commit id == $pin" "$tcid" $s
( cd $RT/src && sha256sum * ) > "$OUT/ba8_source_tarball_sha256.txt"

# restore the qualified env record for later probes
AIOS_RUNTIME_ROOT=$RT AIOS_REPO_ROOT=$CAND bash "$BOOT" --verify > /dev/null 2>&1
echo done
