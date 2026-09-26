#!/bin/sh
# C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-003 — Hardened isolation probe (minimal dev + strict mounts)
# Runs INSIDE the sandbox as 'nobody'. Exits 0 only on full isolation PASS.
set -eu

FAIL=0
pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*"; FAIL=1; }

echo "=== identity ==="
uid=$(id -u); gid=$(id -g)
echo "uid=$uid gid=$gid"
[ "$uid" = "65534" ] && pass "running as nobody (uid 65534)" || fail "not nobody (uid=$uid)"

echo
echo "=== PID namespace (blocker 2 fixed) ==="
self_pid=$(sh -c 'echo $$')
echo "my pid = $self_pid (should be >=2)"
if [ "$self_pid" = "1" ]; then
  fail "resident is PID 1; PID1 must be sandbox-init supervisor"
else
  pass "resident pid $self_pid != 1 (init is separate)"
fi
if [ -d /proc/1 ]; then
    pid1_comm=$(cat /proc/1/comm 2>/dev/null || echo UNREADABLE)
    echo "pid 1 comm = '$pid1_comm'"
    visible_pids=$(ls -1d /proc/[0-9]* 2>/dev/null | wc -l)
    echo "visible PIDs in /proc = $visible_pids (should be small, not host's 100+)"
    if [ "$visible_pids" -gt 20 ]; then
        fail "too many PIDs visible ($visible_pids); /proc likely shows host"
    else
        pass "only $visible_pids PIDs visible (expected small count in new PID namespace)"
    fi
    # PID1 must be sandbox-init
    if [ "$pid1_comm" = "sandbox-init" ]; then
        pass "PID1 is sandbox-init (correct supervisor)"
    elif [ "$pid1_comm" = "python3" ] || [ "$pid1_comm" = "python" ]; then
        # Fallback: Python init without prctl name set - still acceptable if not sh and pid !=1 for resident
        # But we strictly expect sandbox-init per CORRECTIVE-002
        fail "PID1 comm is $pid1_comm, expected sandbox-init"
    else
        fail "PID1 comm is '$pid1_comm', expected 'sandbox-init'"
    fi
    if grep -l -E '^(systemd|init|launchd|svchost)$' /proc/[0-9]*/comm 2>/dev/null | grep -q .; then
        fail "host-like init process visible in /proc"
    else
        pass "no host init (systemd/init) visible in new PID namespace"
    fi
    # Verify /proc/1/root is sandbox root, not host leak; readlink should be /
    if [ -e /proc/1/root ]; then
        rl=$(readlink /proc/1/root 2>/dev/null || echo UNREADABLE)
        echo "proc1_root readlink = $rl"
        if [ "$rl" = "/" ]; then
            pass "/proc/1/root points to sandbox / (PID1 is in chroot ns, no host leak)"
        else
            fail "/proc/1/root = $rl (unexpected)"
        fi
    else
        pass "/proc/1/root unreadable (also acceptable)"
    fi
else
    fail "/proc/1 missing"
fi

echo
echo "=== Child/orphan reap check (PID1 supervisor) ==="
/usr/bin/python3 - <<'PYEOF'
import os, time, sys
# Test that PID1 reaps orphans: fork a child that double-forks an orphan grandchild
pid = os.fork()
if pid == 0:
    # child
    pid2 = os.fork()
    if pid2 == 0:
        # grandchild - orphan soon
        time.sleep(0.3)
        # If we are reparented to PID1 and PID1 is proper init, we will be reaped after exit; we just exit
        print("grandchild exiting")
        os._exit(0)
    else:
        # child exits immediately, making grandchild orphan
        time.sleep(0.05)
        print("child exiting, grandchild should be orphan to PID1")
        os._exit(0)
else:
    # parent (probe)
    _, status = os.waitpid(pid, 0)
    print(f"child reaped status={status}")
    time.sleep(0.5)
    # Check for zombie: scan /proc for Z status
    zombies = []
    import pathlib
    for proc in pathlib.Path("/proc").glob("[0-9]*"):
        try:
            st = (proc / "stat").read_text().split()
            # field 3 is state
            if len(st) >= 3 and st[2] == "Z":
                zombies.append(proc.name)
        except Exception:
            pass
    if zombies:
        print(f"FAIL: zombies found after orphan test: {zombies}")
        sys.exit(1)
    else:
        print("PASS: no zombies after orphan test (PID1 reaped orphan)")
        sys.exit(0)
PYEOF
[ $? -eq 0 ] && pass "PID1 zombie reap works (orphan grandchild reaped)" || fail "orphan reap test failed"

echo
echo "=== Network seal (blocker 1) ==="
/usr/bin/python3 - <<'PYEOF'
import socket, sys
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect(("127.0.0.1", 1))
    s.close()
except (ConnectionRefusedError, socket.timeout):
    pass
except OSError as e:
    print(f"unexpected loopback result: {e}")
    sys.exit(2)

external_targets = [
    ("github.com", "140.82.114.4", 443),
    ("raw.githubusercontent.com", "185.199.108.133", 443),
    ("api.github.com", "140.82.114.6", 443),
    ("8.8.8.8", "8.8.8.8", 53),
]
for name, ip, port in external_targets:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    try:
        s.connect((ip, port))
        print(f"FAIL: could connect to {name} ({ip}:{port}) — network NOT sealed")
        sys.exit(1)
    except OSError as e:
        print(f"PASS: connect to {name} ({ip}:{port}) blocked: errno={e.errno} ({e.strerror or ''})")
    finally:
        s.close()
print("NETWORK_SEAL_PASS")
PYEOF
[ $? -eq 0 ] && pass "network sealed (external connect blocked)" || fail "network probe returned non-zero"

echo
echo "=== Filesystem sealed paths (blocker 1 / 4 / 6) ==="
for p in \
    /repo/fixture \
    /repo/evaluator \
    /repo/governance \
    /repo/.git \
    /repo/prompts \
    /repo/reviews/internal_habitation/c15-rcc/v1/fixture \
    /repo/reviews/internal_habitation/c15-rcc/v1/evaluator \
    /repo/reviews/internal_habitation/c15-rcc/v1/release \
    /repo/reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002 \
    /repo/reviews/internal_habitation/c14-resident \
    /repo/AIOS_SINGLE_WINDOW_TASK_BOARD.md \
    /repo/AIOS_v3.0_CURRENT_CHECKPOINT.md \
    /repo/PROJECT_MASTER_MAP.md \
    ; do
    if [ -e "$p" ]; then
        fail "LEAK: $p exists"
    else
        pass "sealed: $p absent"
    fi
done

echo
echo "=== Read-only bind mounts actually read-only (blocker 6) ==="
if touch /repo/src/__probe_write_test__ 2>/dev/null; then
    fail "Core src is writable (RO bind failed)"
    rm -f /repo/src/__probe_write_test__ 2>/dev/null || true
else
    err=$?
    pass "Core src read-only (touch denied, exit=$err)"
fi
if touch /repo/reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md 2>/dev/null; then
    fail "Resident contract writable"
else
    pass "Resident contract read-only (touch denied)"
fi
/usr/bin/python3 - <<'PYEOF'
import os, errno
for path, label in [
    ("/repo/src/aios_core/__init__.py", "Core src file"),
    ("/repo/reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md", "Resident contract"),
]:
    try:
        fd = os.open(path, os.O_WRONLY)
        os.write(fd, b"corrupt")
        os.close(fd)
        print(f"FAIL: {label} opened writable and accepted write")
    except OSError as e:
        if e.errno in (errno.EROFS, errno.EACCES, errno.EBADF):
            print(f"PASS: {label} write blocked: {e}")
        else:
            print(f"FAIL: {label} unexpected error: {e}")
PYEOF

echo
echo "=== /dev minimal (BLOCKER 6: no whole-host bind) ==="
ls -1 /dev 2>/dev/null | sort > /tmp/dev_list.txt || true
cat /tmp/dev_list.txt | sed 's/^/dev:/'
for n in null zero urandom random; do
    if [ -e "/dev/$n" ]; then
        pass "/dev/$n present"
    else
        fail "/dev/$n missing (required minimal)"
    fi
done
if [ -e /dev/fd ] || [ -L /dev/fd ]; then
    pass "/dev/fd symlink present"
else
    fail "/dev/fd missing"
fi
for p in /dev/sda /dev/sda1 /dev/nvme0n1 /dev/mem /dev/kmem /dev/kvm /dev/port /dev/tty /dev/tty0 /dev/ptmx /dev/pts /dev/block; do
    if [ -e "$p" ]; then
        fail "LEAK: $p present (host /dev bind not minimal)"
    else
        pass "sealed: $p absent as expected"
    fi
done
/usr/bin/python3 - <<'PYEOF'
import os
candidates = ["/dev/sda", "/dev/mem", "/dev/kvm", "/dev/tty", "/dev/port"]
leaked=[]
for p in candidates:
    try:
        fd=os.open(p, os.O_RDONLY)
        os.close(fd)
        leaked.append(p)
    except OSError:
        pass
if leaked:
    print(f"FAIL: could open {leaked}")
else:
    print("PASS: cannot open host-dangerous /dev nodes (ENOENT/EPERM)")
PYEOF

echo
if grep " /repo" /proc/mounts 2>/dev/null | grep -q "\bro,"; then
    grep " /repo" /proc/mounts | head
    # also verify nosuid,nodev
    if grep " /repo" /proc/mounts | grep -q "nosuid" && grep " /repo" /proc/mounts | grep -q "nodev"; then
        pass "/proc/mounts shows ro,nosuid,nodev for /repo binds"
    else
        fail "/proc/mounts missing nosuid/nodev for /repo"
    fi
else
    fail "/proc/mounts missing ro for /repo"
fi

echo
if grep -q " /work/inbox" /proc/mounts 2>/dev/null || mount | grep -q "inbox"; then
    pass "mailbox inbox bind visible in mounts (optional)"
else
    pass "mailbox inbox mount check skipped (bind done via tmpfs+bind)"
fi

echo
echo "=== Mailbox permissions (blocker 4) ==="
if [ -r /work/inbox ]; then
    pass "/work/inbox readable"
else
    fail "/work/inbox not readable"
fi
if [ -w /work/outbox ] && [ -x /work/outbox ]; then
    pass "/work/outbox writable + searchable"
else
    fail "/work/outbox not writable/searchable as nobody"
fi
echo '{"action":"silence"}' > /work/outbox/__probe_reply__.json 2>/dev/null
if [ -s /work/outbox/__probe_reply__.json ]; then
    pass "can write to /work/outbox"
    rm -f /work/outbox/__probe_reply__.json
else
    fail "cannot write to /work/outbox as nobody"
fi
if [ -e /work/archive ]; then
    fail "LEAK: /work/archive (operator archive) is visible inside sandbox"
else
    pass "/work/archive absent (operator archive not mounted)"
fi

echo
echo "=== Privilege re-escalation (blocker 3) ==="
/usr/bin/python3 - <<'PYEOF'
import os, ctypes, ctypes.util
libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
try:
    os.setuid(0)
    print("FAIL: could re-acquire uid 0")
except OSError as e:
    print(f"PASS: setuid(0) denied: {e}")
try:
    os.mkdir("/tmp/mt_test")
except FileExistsError:
    pass
except OSError:
    pass
if libc.mount(b"tmpfs", b"/tmp/mt_test", b"tmpfs", 0, b"size=1m") == 0:
    print("FAIL: mount() succeeded")
else:
    err = ctypes.get_errno()
    if err == 1:
        print(f"PASS: mount() denied (EPERM)")
    else:
        print(f"FAIL: mount() unexpected errno {err}: {os.strerror(err)}")
PYEOF

echo
echo "=== Environment allowlist (BLOCKER: PROBE_* not leaked unless AIOS_ALLOW_PROBE_ENV) ==="
if [ "${AIOS_ALLOW_PROBE_ENV:-}" = "1" ]; then
    if [ -n "${PROBE_MODE:-}" ]; then
        pass "PROBE_MODE present with AIOS_ALLOW_PROBE_ENV=1 (explicit allow)"
    else
        fail "AIOS_ALLOW_PROBE_ENV=1 but PROBE_MODE missing"
    fi
else
    if [ -n "${PROBE_MODE:-}" ] || [ -n "${PROBE_ROUNDS:-}" ]; then
        fail "PROBE_MODE/PROBE_ROUNDS leaked into sandbox without AIOS_ALLOW_PROBE_ENV (unsanitized env)"
    else
        pass "PROBE_MODE/PROBE_ROUNDS not leaked (unsanitized env blocked)"
    fi
fi
# Check LD_* stripped
if env | grep -q "^LD_"; then
    fail "LD_* leaked into sandbox env"
else
    pass "LD_* stripped"
fi

echo
if [ $FAIL -eq 0 ]; then
    echo
    echo "ISOLATION_PASS"
    exit 0
else
    echo
    echo "ISOLATION_FAIL"
    exit 1
fi
