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


def ensure_provider_service(mailbox: Path | str, timeout: float = 15.0) -> int:
    """Ensure the long-lived provider service is running for the given mailbox."""
    mailbox = Path(mailbox)
    mailbox.mkdir(parents=True, exist_ok=True)
    pid_file = mailbox / "provider.pid"
    pub_file = mailbox / "provider-public.json"

    if pid_file.is_file():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            if _is_pid_alive(pid) and pid != os.getpid():
                # Process is alive! Verify if responsive
                try:
                    res = _send_provider_command(mailbox, {"cmd": "status"}, timeout=2.0, auto_ensure=False)
                    if res.get("status") == "running":
                        provider_pid = int(res.get("provider_pid", 0))
                        if provider_pid > 0 and provider_pid != os.getpid():
                            return provider_pid
                except Exception:
                    if pub_file.is_file():
                        return pid
        except Exception:
            pass

    # Clean up stale files
    pid_file.unlink(missing_ok=True)
    pub_file.unlink(missing_ok=True)

    # Spawn provider service subprocess
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
        if pub_file.is_file() and pid_file.is_file():
            try:
                res = _send_provider_command(mailbox, {"cmd": "status"}, timeout=0.5, auto_ensure=False)
                if res.get("status") == "running":
                    return int(res.get("provider_pid", 0))
            except Exception:
                pass
        if proc.poll() is not None:
            raise RuntimeError(f"Provider service exited prematurely with code {proc.returncode}")
        time.sleep(0.01)

    raise TimeoutError(f"Timed out waiting for provider service to start in {mailbox}")


def stop_provider_service(mailbox: Path | str) -> None:
    """Stop the provider service running for the given mailbox."""
    mailbox = Path(mailbox)
    pid_file = mailbox / "provider.pid"
    if not pid_file.is_file():
        return
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        if _is_pid_alive(pid) and pid != os.getpid():
            _send_provider_command(mailbox, {"cmd": "stop"}, timeout=1.0)
    except Exception:
        pass
    finally:
        pid_file.unlink(missing_ok=True)


def read_public_descriptor(mailbox: Path | str) -> dict[str, Any]:
    """Read the public key descriptor written by the provider service."""
    mailbox = Path(mailbox)
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
) -> LateReturnVerifier:
    """Return the public verifier corresponding to the external provider signer."""
    if mailbox is None:
        mailbox = Path(tempfile.gettempdir()) / f"c15-provider-default-{os.getpid()}"
    mailbox = Path(mailbox)
    ensure_provider_service(mailbox)
    descriptor = read_public_descriptor(mailbox)
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
    mailbox = Path(mailbox)
    if auto_ensure:
        ensure_provider_service(mailbox)
    cmds_dir = mailbox / "commands"
    cmds_dir.mkdir(parents=True, exist_ok=True)
    cmd_id = f"cmd-{uuid.uuid4()}"
    cmd_file = cmds_dir / f"{cmd_id}.cmd"
    res_file = cmds_dir / f"{cmd_id}.result"

    payload = {**cmd_payload, "operator_pid": os.getpid()}
    _atomic_write(cmd_file, json.dumps(payload, sort_keys=True).encode("utf-8"))

    start = time.time()
    while time.time() - start < timeout:
        if res_file.is_file():
            try:
                raw = res_file.read_text(encoding="utf-8")
                res = json.loads(raw)
                res_file.unlink(missing_ok=True)
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

    cmd_file.unlink(missing_ok=True)
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
