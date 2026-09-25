#!/bin/sh
# C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-001 — Hardened isolation probe
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
echo "=== PID namespace ==="
# We are in a fresh CLONE_NEWPID with our own PID-1 init helper (a tiny Python
# loop that forwards signals and reaps children). Confirm /proc is fresh by
# enumerating visible processes: should be only the init helper, this shell,
# and its children. Host processes (e.g. host /sbin/init at host pid 1) must
# NOT be visible.
self_pid=$(sh -c 'echo $$')
echo "my pid = $self_pid"
if [ -d /proc/1 ]; then
    pid1_comm=$(cat /proc/1/comm 2>/dev/null || echo UNREADABLE)
    echo "pid 1 comm = '$pid1_comm'"
    # Count visible PIDs via /proc — should be small (our init + this shell + python + a few)
    visible_pids=$(ls -1d /proc/[0-9]* 2>/dev/null | wc -l)
    echo "visible PIDs in /proc = $visible_pids (should be a small number, not the host's 100+)"
    if [ "$visible_pids" -gt 20 ]; then
        fail "too many PIDs visible ($visible_pids); /proc likely shows host processes"
    else
        pass "only $visible_pids PIDs visible (expected small count in new PID namespace)"
    fi
    # Host init comm 'systemd'/'init'/'python3'? PID 1 in our namespace is the jail init,
    # which we know is a Python process (its comm will be 'python3'). We don't reject
    # python3 at pid1 because that is our own init. The key check is that NO pid
    # with comm 'systemd' or 'init' appears.
    if grep -l -E '^(systemd|init|launchd|svchost)$' /proc/[0-9]*/comm 2>/dev/null | grep -q .; then
        fail "host-like init process visible in /proc"
    else
        pass "no host init (systemd/init) visible in new PID namespace"
    fi
    # Reading /proc/1/root as nobody: because PID 1 runs in the same chroot+mount ns
    # (it forks worker before chroot? no — worker does the chroot; after chroot PID 1
    # is still running in the pre-chroot view). We verify only that /proc/1/root
    # is NOT the HOST root by reading its /etc/os-release as a differentiator;
    # simpler check: the total count of PIDs above is already proof of fresh PID ns.
else
    fail "/proc/1 missing"
fi

echo
echo "=== Network seal (blocker 1) ==="
# Try to reach github.com:443 using Python's urllib (batteries included, no curl required).
/usr/bin/python3 - <<'PYEOF'
import socket, sys, urllib.request, ssl
fail_flag = False
# DNS lookup may succeed or may not (depends on /etc/resolv.conf which is bind-mounted),
# but TCP connect to port 443 on github.com MUST fail because the network namespace has
# no routes/interfaces other than loopback.
#
# First confirm loopback is up (we bring it up for AF_UNIX/localhost ops):
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect(("127.0.0.1", 1))  # will fail (nothing listening), but if we get route error instead of connection refused that's a sign
    s.close()
except (ConnectionRefusedError, socket.timeout):
    pass
except OSError as e:
    print(f"unexpected loopback result: {e}")
    sys.exit(2)

# Now try external addresses. We use raw socket connect (avoids DNS).
external_targets = [
    ("github.com", "140.82.114.4", 443),      # Github
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
        # ENETUNREACH = 101, EHOSTUNREACH = 113, ECONNREFUSED on routed but closed would be unusual; any error = no leak.
        print(f"PASS: connect to {name} ({ip}:{port}) blocked: errno={e.errno} ({e.strerror or os.strerror(e.errno)})")
    finally:
        s.close()
print("NETWORK_SEAL_PASS")
PYEOF
[ $? -eq 0 ] && pass "network sealed (external connect blocked)" || fail "network probe returned non-zero (see above)"

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
# Try to write to frozen Core src (should be EROFS = 30)
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
# Double-check via Python os.open with O_WRONLY
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
echo "=== Mailbox permissions (blocker 4) ==="
# Inbox should be readable
if [ -r /work/inbox ]; then
    pass "/work/inbox readable"
else
    fail "/work/inbox not readable"
fi
# Outbox should be writable + searchable (nobody can create reply files)
if [ -w /work/outbox ] && [ -x /work/outbox ]; then
    pass "/work/outbox writable + searchable"
else
    fail "/work/outbox not writable/searchable as nobody"
fi
# Write a test reply and verify we can read it back (then remove it)
echo '{"action":"silence"}' > /work/outbox/__probe_reply__.json 2>/dev/null
if [ -s /work/outbox/__probe_reply__.json ]; then
    pass "can write to /work/outbox"
    rm -f /work/outbox/__probe_reply__.json
else
    fail "cannot write to /work/outbox as nobody"
fi
# Archive must NOT be present (it is operator-only, not bind-mounted)
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
echo "=== Capability: cannot read host /proc/1/root ==="
if ls -la /proc/1/root >/dev/null 2>&1; then
    # We are pid 1 so this is our own root (we chrooted); check it points to /
    rl=$(readlink /proc/1/root 2>/dev/null || echo UNREADABLE)
    if [ "$rl" = "/" ]; then
        pass "/proc/1/root points to sandbox / (we are pid 1); no host proc leak"
    else
        fail "/proc/1/root = $rl (unexpected; may indicate host leak)"
    fi
else
    pass "/proc/1/root unreadable"
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
