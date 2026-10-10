"""Isolated synthetic provider process boundary.

PROCESS & TRUST BOUNDARY:
-------------------------
This module runs exclusively as an independent operating system subprocess
(PROVIDER_PID != OPERATOR_PID) and holds the ephemeral RSA private signing
authority in its own memory heap.

Under the AIOS trust model:
1. This module MUST NOT be imported by operator, recovery, or runner processes.
   Any import attempt immediately raises an ImportError.
2. Operator processes communicate with this boundary exclusively via durable
   mailbox IPC (commands in commands/, files in outbox/ and inbox/).
3. The RSA private key is generated dynamically in memory via CSPRNG on startup.
   Zero static private keys exist in the repository or on disk.
4. Dispatch and collection events record provider PID, operator PID, provider
   instance UUID, and public key fingerprint in the mailbox dispatch ledger.
"""

from __future__ import annotations

import sys

# Hard import isolation: operator / recovery processes cannot import this module
if __name__ != "__main__":
    raise ImportError(
        "provider_process is an isolated process boundary and cannot be imported into operator process"
    )

try:
    import fcntl
except ImportError:
    fcntl = None

import hashlib
import json
import math
import os
import secrets
import signal
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Bootstrap src path for aios_core types
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from aios_core.runtime import (  # noqa: E402
    CapabilityCall,
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
)
from aios_core.runtime.background_attempt import (  # noqa: E402
    BackgroundModelAttemptStore,
    decode_model_directive,
    encode_model_directive,
)
from aios_core.runtime.late_return import (  # noqa: E402
    LateReturnVerifier,
    late_return_message,
)

CAPABILITY_NAME = "c15_probe_capability"
PROVIDER_NAME = "c15-synthetic-relay"
MODEL_NAME = "c15-synthetic-model"
PROVIDER_KEY_ID = "c15-synthetic-provider-key"

_SHA256_DER = bytes.fromhex("3031300d060960864801650304020105000420")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


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


def append_ledger(mailbox: Path, record: dict[str, object]) -> None:
    path = ledger_path(mailbox)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


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


def _mirror(mailbox: Path, source: Path, target: Path) -> None:
    if source.is_file():
        _atomic_write(target, source.read_bytes())


def build_directive(request: bytes) -> ModelDirective:
    """Deterministic ModelDirective for exact request bytes."""
    envelope = json.loads(request.decode("utf-8"))
    request_id = str(envelope["model_request_id"])
    attempt_id = str(envelope["attempt_id"])
    round_index = int(envelope["round"])
    provider = str(envelope["provider"])
    model = str(envelope["model"])
    turn_text = str(envelope.get("resident_visible_payload", ""))

    if round_index == 0:
        return ModelDirective(
            capability_calls=(
                CapabilityCall(
                    name=CAPABILITY_NAME,
                    arguments={"attempt_id": attempt_id, "round": round_index},
                    call_id=f"{request_id}:c0",
                ),
            ),
            usage=ModelUsage(
                input_tokens=11,
                output_tokens=5,
                total_tokens=16,
                provider=provider,
                model=model,
                request_id=request_id,
            ),
            provenance=ModelCallProvenance(
                provider=provider, model=model, request_id=request_id
            ),
        )
    return ModelDirective(
        response=f"[synthetic provider] round {round_index} answer for {turn_text[:24]}",
        usage=ModelUsage(
            input_tokens=13,
            output_tokens=7,
            total_tokens=20,
            provider=provider,
            model=model,
            request_id=request_id,
        ),
        provenance=ModelCallProvenance(
            provider=provider, model=model, request_id=request_id
        ),
    )


_SMALL_PRIMES = (
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
    73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151,
    157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233,
    239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317,
    331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419,
    421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503,
    509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599, 601, 607,
)


def _is_probable_prime(n: int, k: int = 15) -> bool:
    if n < 2:
        return False
    for p in _SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    for _ in range(k):
        a = secrets.randbelow(n - 4) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _generate_prime(bits: int) -> int:
    while True:
        p = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if _is_probable_prime(p):
            return p


def generate_rsa_keypair(key_size: int = 2048, e: int = 65537) -> tuple[int, int, int]:
    """Generate ephemeral (n, e, d) RSA keypair in memory using OS CSPRNG (zero dependencies)."""
    prime_bits = key_size // 2
    while True:
        p = _generate_prime(prime_bits)
        q = _generate_prime(prime_bits)
        if p == q:
            continue
        n = p * q
        if n.bit_length() != key_size:
            continue
        phi = (p - 1) * (q - 1)
        if math.gcd(e, phi) == 1:
            d = pow(e, -1, phi)
            return n, e, d


RUNTIME_BASE_DIR = Path(tempfile.gettempdir()) / ".aios_provider_runtime"


class ProviderService:
    """Isolated, long-lived provider service maintaining private key in memory heap only."""

    def __init__(self, mailbox: Path, key_id: str = PROVIDER_KEY_ID) -> None:
        self.mailbox = Path(mailbox)
        self.key_id = key_id
        self.pid = os.getpid()

        # Ephemeral in-memory RSA keypair (Model A: strictly memory-only, never persisted to disk/vault/temp)
        self.instance_id = str(uuid.uuid4())
        self._n, self._e, self._d = generate_rsa_keypair(key_size=2048, e=65537)
        self.modulus_hex = f"{self._n:x}"
        self.public_key_fingerprint = hashlib.sha256(
            f"{self.modulus_hex}:{self._e}".encode("utf-8")
        ).hexdigest()

        self.runtime_dir = RUNTIME_BASE_DIR / self.instance_id
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(RUNTIME_BASE_DIR, 0o777)
            os.chmod(self.runtime_dir, 0o777)
        except Exception:
            pass

        self.lock_fd: int | None = None
        if fcntl is not None:
            self.lock_file = self.runtime_dir / "provider.lock"
            self.lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_RDWR, 0o666)
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (BlockingIOError, OSError):
                # Another provider service is already running and holding the lock
                sys.exit(0)
            try:
                self.mailbox.mkdir(parents=True, exist_ok=True)
                mb_lock = self.mailbox / "provider.lock"
                self.mb_lock_fd = os.open(mb_lock, os.O_CREAT | os.O_RDWR, 0o666)
                fcntl.flock(self.mb_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except Exception:
                self.mb_lock_fd = None

    def write_public_descriptor(self, target_mailbox: Path | None = None) -> None:
        """Write public key descriptor and PID file (zero private material)."""
        descriptor = {
            "provider_instance_id": self.instance_id,
            "key_id": self.key_id,
            "algorithm": "rsa-pkcs1v15-sha256",
            "modulus_hex": self.modulus_hex,
            "public_exponent": self._e,
            "public_key_fingerprint": self.public_key_fingerprint,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        # Always write to isolated runtime directory
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        pub_runtime = self.runtime_dir / "provider-public.json"
        _atomic_write(pub_runtime, json.dumps(descriptor, indent=2, sort_keys=True).encode("utf-8"))
        pid_runtime = self.runtime_dir / "provider.pid"
        _atomic_write(pid_runtime, f"{self.pid}\n".encode("utf-8"))

        mailboxes_to_write = []
        if self.mailbox is not None:
            mailboxes_to_write.append(self.mailbox)
        if target_mailbox is not None and target_mailbox != self.mailbox:
            mailboxes_to_write.append(target_mailbox)

        for mb in mailboxes_to_write:
            try:
                mb.mkdir(parents=True, exist_ok=True)
                pub_file = mb / "provider-public.json"
                _atomic_write(pub_file, json.dumps(descriptor, indent=2, sort_keys=True).encode("utf-8"))
                binding_file = mb / "provider-binding.json"
                _atomic_write(binding_file, json.dumps(descriptor, indent=2, sort_keys=True).encode("utf-8"))
                pid_file = mb / "provider.pid"
                _atomic_write(pid_file, f"{self.pid}\n".encode("utf-8"))
            except Exception:
                pass

    def sign_message(self, message: bytes) -> str:
        """Sign canonical message bytes with in-memory private key using RSA PKCS#1 v1.5 SHA-256."""
        digest_info = _SHA256_DER + hashlib.sha256(message).digest()
        size = (self._n.bit_length() + 7) // 8
        encoded = (
            b"\x00\x01"
            + (b"\xff" * (size - len(digest_info) - 3))
            + b"\x00"
            + digest_info
        )
        signature = pow(int.from_bytes(encoded, "big"), self._d, self._n)
        return f"bglate_rsa_v1:{self.key_id}:" + signature.to_bytes(size, "big").hex()

    def sign_exact_response(
        self, request: bytes, directive: ModelDirective, target_mailbox: Path | None = None
    ) -> dict[str, Any]:
        mb = target_mailbox or self.mailbox
        envelope = json.loads(request.decode("utf-8"))
        attempt_id = str(envelope["attempt_id"])
        provider = str(envelope["provider"])
        model = str(envelope["model"])
        request_id = str(envelope["model_request_id"])

        payload = encode_model_directive(directive)
        fingerprint = BackgroundModelAttemptStore._response_fingerprint(directive)
        payload_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        context_file = mb / "contexts" / f"{attempt_id}.json"
        if not context_file.is_file() and mb != self.mailbox:
            context_file = self.mailbox / "contexts" / f"{attempt_id}.json"
        if not context_file.is_file():
            raise KeyError(f"provider has no registered dispatch context for attempt {attempt_id}")

        scope = json.loads(context_file.read_text(encoding="utf-8"))
        fields: dict[str, object] = {
            **scope,
            "provider": provider,
            "model": model,
            "provider_request_id": request_id,
            "response_fingerprint": fingerprint,
            "payload_sha256": payload_sha256,
        }
        msg = late_return_message(**fields)
        proof_str = self.sign_message(msg)
        return {
            "attempt_id": attempt_id,
            "authenticity_proof": proof_str,
            "provider": provider,
            "model": model,
            "provider_request_id": request_id,
            "response_fingerprint": fingerprint,
            "relay_id": fields["relay_id"],
        }

    def dispatch(
        self, request_id: str, operator_pid: int = 0, reattach: bool = False, target_mailbox: Path | None = None
    ) -> dict[str, object]:
        """Cross the provider submission boundary exactly once."""
        mb = target_mailbox or self.mailbox
        request_file = outbox_path(mb, request_id)
        if not request_file.is_file() and mb != self.mailbox:
            request_file = outbox_path(self.mailbox, request_id)
        if not request_file.is_file():
            raise FileNotFoundError(f"provider: no durable request for {request_id}")
        request = request_file.read_bytes()
        request_sha = digest(request)
        previous = [row for row in read_ledger(mb) if row.get("request_id") == request_id]
        if not previous and mb != self.mailbox:
            previous = [row for row in read_ledger(self.mailbox) if row.get("request_id") == request_id]
        if previous or reattach:
            return {
                "request_id": request_id,
                "request_sha256": request_sha,
                "dispatch": "reattached",
                "dispatch_count": max(1, len(previous)),
                "provider_pid": self.pid,
                "operator_pid": operator_pid,
                "provider_instance_id": self.instance_id,
                "public_key_fingerprint": self.public_key_fingerprint,
            }
        append_ledger(
            mb,
            {
                "request_id": request_id,
                "request_sha256": request_sha,
                "dispatched_at_epoch": time.time(),
                "provider_pid": self.pid,
                "operator_pid": operator_pid,
                "provider_instance_id": self.instance_id,
                "public_key_fingerprint": self.public_key_fingerprint,
            },
        )
        if mb != self.mailbox:
            try:
                append_ledger(
                    self.mailbox,
                    {
                        "request_id": request_id,
                        "request_sha256": request_sha,
                        "dispatched_at_epoch": time.time(),
                        "provider_pid": self.pid,
                        "operator_pid": operator_pid,
                        "provider_instance_id": self.instance_id,
                        "public_key_fingerprint": self.public_key_fingerprint,
                    },
                )
            except Exception:
                pass
        return {
            "request_id": request_id,
            "request_sha256": request_sha,
            "dispatch": "dispatched",
            "dispatch_count": 1,
            "provider_pid": self.pid,
            "operator_pid": operator_pid,
            "provider_instance_id": self.instance_id,
            "public_key_fingerprint": self.public_key_fingerprint,
        }

    def collect(self, request_id: str, operator_pid: int = 0, target_mailbox: Path | None = None) -> dict[str, object]:
        """Collect the exact reply and proof for an already-dispatched request."""
        mb = target_mailbox or self.mailbox
        request_file = outbox_path(mb, request_id)
        if not request_file.is_file() and mb != self.mailbox:
            request_file = outbox_path(self.mailbox, request_id)
        if not request_file.is_file():
            raise FileNotFoundError(f"provider: no durable request for {request_id}")
        request = request_file.read_bytes()
        request_sha = digest(request)
        previous = [row for row in read_ledger(mb) if row.get("request_id") == request_id]
        if not previous and mb != self.mailbox:
            previous = [row for row in read_ledger(self.mailbox) if row.get("request_id") == request_id]
        reply_file = inbox_path(mb, request_id)
        proof_file = proof_path(mb, request_id)
        directive = build_directive(request)
        if not reply_file.is_file():
            reply = encode_model_directive(directive).encode("utf-8")
            _atomic_write(reply_file, reply)
            _mirror(mb, reply_file, current_reply_path(mb))
            if mb != self.mailbox:
                try:
                    _atomic_write(inbox_path(self.mailbox, request_id), reply)
                    _mirror(self.mailbox, inbox_path(self.mailbox, request_id), current_reply_path(self.mailbox))
                except Exception:
                    pass

        if not proof_file.is_file():
            envelope = json.loads(request.decode("utf-8"))
            attempt_id = str(envelope["attempt_id"])
            context_file = mb / "contexts" / f"{attempt_id}.json"
            if not context_file.is_file() and mb != self.mailbox:
                context_file = self.mailbox / "contexts" / f"{attempt_id}.json"
            if context_file.is_file():
                proof_dict = self.sign_exact_response(request, directive, target_mailbox=mb)
                _atomic_write(proof_file, json.dumps(proof_dict, sort_keys=True).encode("utf-8"))
                if mb != self.mailbox:
                    try:
                        _atomic_write(proof_path(self.mailbox, request_id), json.dumps(proof_dict, sort_keys=True).encode("utf-8"))
                    except Exception:
                        pass

        return {
            "request_id": request_id,
            "request_sha256": request_sha,
            "dispatch": "reattached",
            "dispatch_count": max(1, len(previous)),
            "reply_sha256": digest(reply_file.read_bytes()),
            "provider_pid": self.pid,
            "operator_pid": operator_pid,
            "provider_instance_id": self.instance_id,
            "public_key_fingerprint": self.public_key_fingerprint,
        }

    def serve(
        self, request_id: str, operator_pid: int = 0, reattach: bool = False, target_mailbox: Path | None = None
    ) -> dict[str, object]:
        dispatch_report = self.dispatch(request_id, operator_pid=operator_pid, reattach=reattach, target_mailbox=target_mailbox)
        reply_report = self.collect(request_id, operator_pid=operator_pid, target_mailbox=target_mailbox)
        return {
            **reply_report,
            "dispatch": dispatch_report["dispatch"],
            "dispatch_count": dispatch_report["dispatch_count"],
        }

    def run_service(self) -> int:
        """Run service event loop watching for command files in runtime_dir and mailbox."""
        self.write_public_descriptor()
        runtime_cmds_dir = self.runtime_dir / "commands"
        runtime_cmds_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(runtime_cmds_dir, 0o777)
        except Exception:
            pass

        cmds_dir = self.mailbox / "commands"
        cmds_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(cmds_dir, 0o777)
        except Exception:
            pass

        running = True
        while running:
            try:
                # Poll both runtime commands dir and initial mailbox commands dir
                cmd_files = sorted(runtime_cmds_dir.glob("*.cmd"))
                if cmds_dir.is_dir():
                    cmd_files.extend(sorted(cmds_dir.glob("*.cmd")))
                for cmd_path in cmd_files:
                    try:
                        raw = cmd_path.read_text(encoding="utf-8")
                        cmd_data = json.loads(raw)
                        cmd = cmd_data.get("cmd")
                        req_id = cmd_data.get("request_id", "")
                        op_pid = int(cmd_data.get("operator_pid", 0))
                        reattach = bool(cmd_data.get("reattach", False))
                        target_mb_str = cmd_data.get("mailbox")
                        target_mb = Path(target_mb_str) if target_mb_str else self.mailbox

                        if target_mb is not None:
                            self.write_public_descriptor(target_mailbox=target_mb)

                        if cmd == "dispatch":
                            res = self.dispatch(req_id, operator_pid=op_pid, reattach=reattach, target_mailbox=target_mb)
                        elif cmd == "collect":
                            res = self.collect(req_id, operator_pid=op_pid, target_mailbox=target_mb)
                        elif cmd == "serve":
                            res = self.serve(req_id, operator_pid=op_pid, reattach=reattach, target_mailbox=target_mb)
                        elif cmd == "stop":
                            res = {"status": "stopping", "provider_pid": self.pid}
                            running = False
                        elif cmd == "status":
                            res = {
                                "status": "running",
                                "provider_pid": self.pid,
                                "provider_instance_id": self.instance_id,
                                "public_key_fingerprint": self.public_key_fingerprint,
                            }
                        else:
                            res = {"error": f"unknown cmd {cmd}"}

                        res_path = cmd_path.with_suffix(".result")
                        _atomic_write(res_path, json.dumps(res, sort_keys=True).encode("utf-8"))
                        if target_mb is not None:
                            try:
                                mb_res_path = target_mb / "commands" / res_path.name
                                _atomic_write(mb_res_path, json.dumps(res, sort_keys=True).encode("utf-8"))
                            except Exception:
                                pass
                    except Exception as exc:
                        res_path = cmd_path.with_suffix(".result")
                        _atomic_write(res_path, json.dumps({"error": str(exc)}, sort_keys=True).encode("utf-8"))
                    finally:
                        try:
                            cmd_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                time.sleep(0.005)
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(0.01)

        return 0


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        sys.stderr.write("usage: provider_process.py <service|dispatch|collect|serve> <mailbox_dir> [request_id]\n")
        return 2
    cmd = argv[1]
    mailbox = Path(argv[2])

    if cmd == "service":
        service = ProviderService(mailbox)
        return service.run_service()

    if len(argv) < 4:
        sys.stderr.write(f"usage: provider_process.py {cmd} <mailbox_dir> <request_id>\n")
        return 2
    request_id = argv[3]

    # CLI fallback: send command to running service via mailbox command IPC
    cmds_dir = mailbox / "commands"
    cmds_dir.mkdir(parents=True, exist_ok=True)
    cmd_id = f"cli-{uuid.uuid4()}"
    cmd_file = cmds_dir / f"{cmd_id}.cmd"
    res_file = cmds_dir / f"{cmd_id}.result"

    payload = {"cmd": cmd, "request_id": request_id, "operator_pid": os.getppid()}
    _atomic_write(cmd_file, json.dumps(payload, sort_keys=True).encode("utf-8"))

    start = time.time()
    while time.time() - start < 10.0:
        if res_file.is_file():
            try:
                raw = res_file.read_text(encoding="utf-8")
                res = json.loads(raw)
                res_file.unlink(missing_ok=True)
                if "error" in res:
                    sys.stderr.write(f"provider_process error: {res['error']}\n")
                    return 1
                print(json.dumps(res, sort_keys=True))
                return 0
            except json.JSONDecodeError:
                time.sleep(0.005)
                continue
        time.sleep(0.005)

    cmd_file.unlink(missing_ok=True)
    sys.stderr.write(f"timeout waiting for provider service response for {cmd}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
