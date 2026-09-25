#!/bin/sh
set -e
echo "=== sealed-path leak probe (categories from release_contract §2 / preflight §6) ==="
leak=0
for p in \
    /repo/reviews/internal_habitation/c15-rcc/v1/fixture \
    /repo/reviews/internal_habitation/c15-rcc/v1/evaluator \
    /repo/reviews/internal_habitation/c15-rcc/v1/release \
    /repo/reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002 \
    /repo/reviews/internal_habitation/c14-resident \
    /repo/governance \
    /repo/prompts \
    /repo/.git \
    /repo/AIOS_SINGLE_WINDOW_TASK_BOARD.md \
    /repo/AIOS_v3.0_CURRENT_CHECKPOINT.md \
    /repo/PROJECT_MASTER_MAP.md \
    ; do
    if [ -e "$p" ]; then
        echo "LEAK:$p"
        leak=1
    else
        echo "sealed:$p absent"
    fi
done
# Note: /repo/src and /repo/reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md
# are EXPECTED to be visible (frozen Core code + the Resident-safe run contract).
echo
echo "=== Expected-visible check ==="
for p in /repo/src /repo/src/aios_core /repo/reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md; do
    if [ -e "$p" ]; then
        echo "visible:$p present (expected)"
    else
        echo "MISSING:$p (UNEXPECTED)"
        leak=1
    fi
done
echo
echo "=== privilege audit ==="
id
echo
echo "=== /proc/1/root readable? ==="
if /bin/ls -la /proc/1/root >/dev/null 2>&1; then
    echo "LEAK: can read host /proc/1/root"
    leak=1
else
    echo "blocked: cannot read host /proc/1/root (expected)"
fi
echo
echo "=== mount() syscall as unprivileged user ==="
/usr/bin/python3 -c "
import ctypes, ctypes.util, os
libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
try:
    os.mkdir('/tmp/mnt_test')
except FileExistsError:
    pass
ret = libc.mount(b'tmpfs', b'/tmp/mnt_test', b'tmpfs', 0, b'size=1m')
err = ctypes.get_errno()
print(f'mount() returned {ret}, errno={err} (EPERM=1)')
if err == 1:
    print('blocked: mount denied (expected)')
else:
    print('WARNING: mount unexpectedly permitted')
"
echo
if [ "$leak" -eq 0 ]; then
    echo "ISOLATION_PASS"
else
    echo "ISOLATION_FAIL"
    exit 1
fi
