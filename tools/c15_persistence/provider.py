"""Deterministic, cross-process synthetic provider client for the kill/restart probes.

Why a separate process
----------------------
The probes need a *provider boundary* whose dispatch count is observable and
durable, and which survives the death of the operator process. Writing the
request to a durable outbox and having a **separate process** answer it gives an
exact, countable dispatch event that is independent of the operator's memory.

Under the AIOS trust model:
* Provider-side signing authority lives exclusively within the isolated
  `provider_process` subprocess boundary (OPERATOR_PID != PROVIDER_PID).
* Private RSA key material is generated via CSPRNG purely in the memory heap of
  the provider process.
* Zero private keys or static secrets exist in the repository or on disk.
* This client module contains ONLY public verifier configuration and data-only
  mailbox IPC dispatch/collection triggers.
* Operator and recovery callers hold only the public `LateReturnVerifier` and
  rely exclusively on provider-produced proofs across the mailbox boundary.
"""

from __future__ import annotations

try:
    import fcntl
except ImportError:
    fcntl = None

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

CAPABILITY_NAME = "c15_probe_capability"
PROVIDER_NAME = "c15-synthetic-relay"
MODEL_NAME = "c15-synthetic-model"
PROVIDER_KEY_ID = "c15-synthetic-provider-key"

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from aios_core.runtime.late_return import (  # noqa: E402
    ExternalReturnObserver,
    LateReturnSigningContext,
    LateReturnVerifier,
)


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o777)
    except Exception:
        pass
    temp = path.with_name(f"{path.name}.{uuid.uuid4()}.tmp")
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.chmod(temp, 0o666)
    except Exception:
        pass
    os.replace(temp, path)
    try:
        os.chmod(path, 0o666)
    except Exception:
        pass


RUNTIME_BASE_DIR = Path(tempfile.gettempdir()) / ".aios_provider_runtime"


def is_instance_alive(instance_id: str | None) -> bool:
    if not instance_id:
        return False
    runtime_dir = RUNTIME_BASE_DIR / str(instance_id)
    lock_file = runtime_dir / "provider.lock"
    pid_file = runtime_dir / "provider.pid"
    if not lock_file.is_file() or not pid_file.is_file():
        return False
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        if not _is_pid_alive(pid):
            return False
    except Exception:
        return False
    if fcntl is None:
        return True
    try:
        fd = os.open(lock_file, os.O_RDWR, 0o666)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Acquired lock -> provider is NOT holding it!
            fcntl.flock(fd, fcntl.LOCK_UN)
            return False
        except (BlockingIOError, OSError):
            return True
        finally:
            os.close(fd)
    except Exception:
        return False


def is_provider_locked(mailbox: Path) -> bool:
    mailbox = Path(mailbox)
    # Check mailbox-level lock first
    if fcntl is not None:
        lock_file = mailbox / "provider.lock"
        if lock_file.is_file():
            try:
                fd = os.open(lock_file, os.O_RDWR, 0o666)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except (BlockingIOError, OSError):
                    return True
                finally:
                    os.close(fd)
            except Exception:
                pass
    # Check if instance is bound and alive in runtime
    for fname in ("provider-binding.json", "provider-public.json"):
        fpath = mailbox / fname
        if fpath.is_file():
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                inst = data.get("provider_instance_id")
                if inst and is_instance_alive(inst):
                    return True
            except Exception:
                pass
    return False


def ensure_provider_service(mailbox: Path | str, instance_id: str | None = None, timeout: float = 15.0) -> int:
    """Ensure the long-lived provider service is running for the given mailbox."""
    mailbox = Path(mailbox)
    mailbox.mkdir(parents=True, exist_ok=True)
    pid_file = mailbox / "provider.pid"
    pub_file = mailbox / "provider-public.json"
    binding_file = mailbox / "provider-binding.json"

    target_instance = instance_id
    if not target_instance:
        if binding_file.is_file():
            try:
                target_instance = json.loads(binding_file.read_text(encoding="utf-8")).get("provider_instance_id")
            except Exception:
                pass
        elif pub_file.is_file():
            try:
                target_instance = json.loads(pub_file.read_text(encoding="utf-8")).get("provider_instance_id")
            except Exception:
                pass

    # If target instance is specified and alive in runtime dir, reuse it directly!
    if target_instance and is_instance_alive(target_instance):
        inst_runtime_dir = RUNTIME_BASE_DIR / str(target_instance)
        inst_pub = inst_runtime_dir / "provider-public.json"
        inst_pid = inst_runtime_dir / "provider.pid"
        if inst_pub.is_file() and inst_pid.is_file():
            try:
                pub_data = inst_pub.read_text(encoding="utf-8")
                _atomic_write(pub_file, pub_data.encode("utf-8"))
                _atomic_write(binding_file, pub_data.encode("utf-8"))
                pid_val = inst_pid.read_text(encoding="utf-8").strip()
                _atomic_write(pid_file, f"{pid_val}\n".encode("utf-8"))
                return int(pid_val)
            except Exception:
                pass

    # If provider is already running for this exact mailbox
    if pub_file.is_file() and (is_provider_locked(mailbox) or pid_file.is_file()):
        try:
            res = _send_provider_command(mailbox, {"cmd": "status"}, timeout=3.0, auto_ensure=False)
            if res.get("status") == "running":
                provider_pid = int(res.get("provider_pid", 0))
                if provider_pid > 0 and provider_pid != os.getpid():
                    return provider_pid
        except Exception:
            if is_provider_locked(mailbox):
                try:
                    return int(pid_file.read_text(encoding="utf-8").strip())
                except Exception:
                    return 1

    # Clean up stale files only if lock is NOT held
    if not is_provider_locked(mailbox):
        pid_file.unlink(missing_ok=True)
        pub_file.unlink(missing_ok=True)
        binding_file.unlink(missing_ok=True)

    # Spawn fresh provider service subprocess
    env = dict(os.environ)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "tools.c15_persistence.provider_process",
            "service",
            str(mailbox),
        ],
        cwd=str(_REPO_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    start = time.time()
    while time.time() - start < timeout:
        if pub_file.is_file():
            try:
                res = _send_provider_command(mailbox, {"cmd": "status"}, timeout=1.0, auto_ensure=False)
                if res.get("status") == "running":
                    return int(res.get("provider_pid", 0))
            except Exception:
                pass
        if proc.poll() is not None:
            if proc.returncode == 0 and pub_file.is_file():
                try:
                    res = _send_provider_command(mailbox, {"cmd": "status"}, timeout=2.0, auto_ensure=False)
                    if res.get("status") == "running":
                        return int(res.get("provider_pid", 0))
                except Exception:
                    pass
            raise RuntimeError(f"Provider service exited prematurely with code {proc.returncode}")
        time.sleep(0.01)

    raise TimeoutError(f"Timed out waiting for provider service to start in {mailbox}")


def stop_provider_service(mailbox: Path | str) -> None:
    """Stop the provider service running for the given mailbox."""
    mailbox = Path(mailbox)
    pid_file = mailbox / "provider.pid"
    binding_file = mailbox / "provider-binding.json"
    pub_file = mailbox / "provider-public.json"
    inst_id = None
    for f in (binding_file, pub_file):
        if f.is_file():
            try:
                inst_id = json.loads(f.read_text(encoding="utf-8")).get("provider_instance_id")
                if inst_id:
                    break
            except Exception:
                pass

    pid = None
    if pid_file.is_file():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
        except Exception:
            pass

    if inst_id and is_instance_alive(inst_id):
        try:
            runtime_pid_file = RUNTIME_BASE_DIR / str(inst_id) / "provider.pid"
            if runtime_pid_file.is_file():
                pid = int(runtime_pid_file.read_text(encoding="utf-8").strip())
        except Exception:
            pass

    if pid and _is_pid_alive(pid) and pid != os.getpid():
        try:
            _send_provider_command(mailbox, {"cmd": "stop"}, timeout=1.0, auto_ensure=False)
        except Exception:
            try:
                os.kill(pid, 15)
            except Exception:
                pass
        start = time.time()
        while time.time() - start < 2.0 and _is_pid_alive(pid):
            time.sleep(0.01)
        if _is_pid_alive(pid):
            try:
                os.kill(pid, 9)
            except Exception:
                pass
    pid_file.unlink(missing_ok=True)


RECOVERY_PROVIDER_COMMAND_COUNT: int = 0
RECOVERY_INTERCEPTOR_ACTIVE: bool = False
_RECOVERY_MODE: bool = False


class RecoveryProviderContactForbidden(RuntimeError):
    """Raised when an attempt is made to contact the provider service during recovery."""


def reset_recovery_command_counter() -> None:
    global RECOVERY_PROVIDER_COMMAND_COUNT
    RECOVERY_PROVIDER_COMMAND_COUNT = 0


def get_recovery_command_count() -> int:
    return RECOVERY_PROVIDER_COMMAND_COUNT


def set_recovery_interceptor(active: bool) -> None:
    global RECOVERY_INTERCEPTOR_ACTIVE
    RECOVERY_INTERCEPTOR_ACTIVE = bool(active)


def set_recovery_mode(active: bool) -> None:
    global _RECOVERY_MODE
    _RECOVERY_MODE = bool(active)


def read_public_descriptor(mailbox: Path | str, auto_ensure: bool = True) -> dict[str, Any]:
    """Read the public key descriptor written by the provider service."""
    mailbox = Path(mailbox)
    if auto_ensure:
        ensure_provider_service(mailbox)
    pub_file = mailbox / "provider-public.json"
    if not pub_file.is_file():
        raise FileNotFoundError(f"Provider public descriptor missing at {pub_file}")
    data = json.loads(pub_file.read_text(encoding="utf-8"))

    # Assert local binding consistency if binding file exists
    binding_file = mailbox / "provider-binding.json"
    if binding_file.is_file():
        binding = json.loads(binding_file.read_text(encoding="utf-8"))
        if (
            str(data.get("public_key_fingerprint")) != str(binding.get("public_key_fingerprint"))
            or str(data.get("provider_instance_id")) != str(binding.get("provider_instance_id"))
        ):
            from tools.c15_persistence.backend import BackendError

            raise BackendError("Provider fingerprint mismatch: verifier substitution detected")

    return data


def route_b_verifier(
    mailbox: Path | str | None = None,
    key_id: str = PROVIDER_KEY_ID,
    expected_fingerprint: str | None = None,
) -> LateReturnVerifier:
    """Return the public verifier corresponding to the external provider signer."""
    if mailbox is None:
        mailbox = Path(tempfile.gettempdir()) / f"c15-provider-default-{os.getpid()}"
    mailbox = Path(mailbox)
    pub_file = mailbox / "provider-public.json"
    if pub_file.is_file():
        descriptor = read_public_descriptor(mailbox, auto_ensure=False)
    else:
        ensure_provider_service(mailbox)
        descriptor = read_public_descriptor(mailbox, auto_ensure=False)
    if expected_fingerprint is not None:
        if str(descriptor.get("public_key_fingerprint")) != str(expected_fingerprint):
            from tools.c15_persistence.backend import BackendError

            raise BackendError(
                f"Provider fingerprint mismatch: expected={expected_fingerprint}, "
                f"actual={descriptor.get('public_key_fingerprint')}"
            )
    return LateReturnVerifier(
        key_id=key_id,
        algorithm=str(descriptor.get("algorithm", "rsa-pkcs1v15-sha256")),
        modulus_hex=str(descriptor["modulus_hex"]),
        public_exponent=int(descriptor["public_exponent"]),
    )


class ProviderReturnObserver(ExternalReturnObserver):
    """Provider boundary observer capturing public dispatch context (zero private authority)."""

    def __init__(self, mailbox: Path | None = None) -> None:
        self.mailbox = Path(mailbox) if mailbox is not None else None

    def accept_return_context(
        self, snapshot: object, context: LateReturnSigningContext
    ) -> None:
        if self.mailbox is not None:
            context_path = self.mailbox / "contexts" / f"{context.attempt_id}.json"
            context_path.parent.mkdir(parents=True, exist_ok=True)
            context_path.write_text(
                json.dumps(context.scope_fields(), sort_keys=True) + "\n",
                encoding="utf-8",
            )


def get_provider_observer(mailbox: Path | None = None) -> ExternalReturnObserver:
    """Return the provider-side dispatch context observer."""
    return ProviderReturnObserver(mailbox=mailbox)


def outbox_path(mailbox: Path, request_id: str) -> Path:
    return mailbox / "outbox" / f"{request_id}.request"


def inbox_path(mailbox: Path, request_id: str) -> Path:
    return mailbox / "inbox" / f"{request_id}.reply"


def proof_path(mailbox: Path, request_id: str) -> Path:
    return mailbox / "inbox" / f"{request_id}.proof"


def ledger_path(mailbox: Path) -> Path:
    return mailbox / "dispatch-ledger.jsonl"


def current_request_path(mailbox: Path) -> Path:
    return mailbox / "outbox" / "current.request"


def current_reply_path(mailbox: Path) -> Path:
    return mailbox / "inbox" / "current.reply"


def read_ledger(mailbox: Path) -> list[dict[str, object]]:
    path = ledger_path(mailbox)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_proof(mailbox: Path, request_id: str) -> dict[str, Any] | None:
    """Read provider-produced proof from inbox if available."""
    p_file = proof_path(Path(mailbox), request_id)
    if not p_file.is_file():
        return None
    try:
        return json.loads(p_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _mirror(mailbox: Path, source: Path, target: Path) -> None:
    if source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(target.parent, 0o777)
        except Exception:
            pass
        _atomic_write(target, source.read_bytes())


def _send_provider_command(
    mailbox: Path, cmd_payload: dict[str, Any], timeout: float = 10.0, auto_ensure: bool = True
) -> dict[str, object]:
    """Execute provider operation via data-only mailbox command IPC to the isolated provider service."""
    global RECOVERY_PROVIDER_COMMAND_COUNT
    if _RECOVERY_MODE:
        RECOVERY_PROVIDER_COMMAND_COUNT += 1
        if RECOVERY_INTERCEPTOR_ACTIVE:
            raise RecoveryProviderContactForbidden(
                f"SECURITY_TEST_PROVIDER_CONTACTED_DURING_RECOVERY: cmd={cmd_payload.get('cmd')}"
            )
    mailbox = Path(mailbox)
    if auto_ensure:
        ensure_provider_service(mailbox)

    # Determine runtime dir if instance is known
    inst_id = None
    for fname in ("provider-binding.json", "provider-public.json"):
        fpath = mailbox / fname
        if fpath.is_file():
            try:
                inst_id = json.loads(fpath.read_text(encoding="utf-8")).get("provider_instance_id")
                if inst_id:
                    break
            except Exception:
                pass

    cmd_id = f"cmd-{uuid.uuid4()}"
    payload = {**cmd_payload, "operator_pid": os.getpid(), "mailbox": str(mailbox)}

    # Send command to mailbox commands dir AND runtime commands dir (if available)
    cmds_dirs = [mailbox / "commands"]
    if inst_id:
        cmds_dirs.append(RUNTIME_BASE_DIR / str(inst_id) / "commands")

    res_files = []
    cmd_files = []
    for cd in cmds_dirs:
        try:
            cd.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(cd, 0o777)
            except Exception:
                pass
            c_file = cd / f"{cmd_id}.cmd"
            r_file = cd / f"{cmd_id}.result"
            _atomic_write(c_file, json.dumps(payload, sort_keys=True).encode("utf-8"))
            cmd_files.append(c_file)
            res_files.append(r_file)
        except Exception:
            pass

    start = time.time()
    while time.time() - start < timeout:
        for r_file in res_files:
            if r_file.is_file():
                try:
                    raw = r_file.read_text(encoding="utf-8")
                    res = json.loads(raw)
                    for rf in res_files:
                        rf.unlink(missing_ok=True)
                    for cf in cmd_files:
                        cf.unlink(missing_ok=True)
                    if "error" in res:
                        raise RuntimeError(f"provider_process error: {res['error']}")
                    provider_pid = int(res.get("provider_pid", 0))
                    if provider_pid == os.getpid():
                        raise RuntimeError(
                            "Security violation: provider_process ran in the same process as operator!"
                        )
                    return res
                except json.JSONDecodeError:
                    time.sleep(0.005)
                    continue
        time.sleep(0.005)

    for cf in cmd_files:
        cf.unlink(missing_ok=True)
    raise TimeoutError(f"Provider service did not respond within {timeout}s for command {cmd_payload.get('cmd')}")


def dispatch(
    mailbox: Path, request_id: str, reattach: bool = False
) -> dict[str, object]:
    """Cross the provider submission boundary exactly once in a separate process."""
    return _send_provider_command(mailbox, {"cmd": "dispatch", "request_id": request_id, "reattach": reattach})


def collect(mailbox: Path, request_id: str) -> dict[str, object]:
    """Collect the exact reply for an already-dispatched request via provider subprocess."""
    return _send_provider_command(mailbox, {"cmd": "collect", "request_id": request_id})


def serve(
    mailbox: Path, request_id: str, reattach: bool = False
) -> dict[str, object]:
    """Compatibility helper: dispatch once, then collect the exact reply."""
    return _send_provider_command(mailbox, {"cmd": "serve", "request_id": request_id, "reattach": reattach})


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: provider.py <mailbox_dir> <request_id>", file=sys.stderr)
        return 2
    report = serve(Path(argv[1]), argv[2])
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
