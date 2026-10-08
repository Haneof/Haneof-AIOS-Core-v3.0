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
* This client module contains ONLY public verifier configuration and data-only
  mailbox IPC dispatch/collection triggers.
* No private key material (_RSA_D) or signing closures exist in this module.
* Operator and recovery callers hold only the public `LateReturnVerifier` and
  rely exclusively on provider-produced proofs across the mailbox boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
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

# Public modulus and exponent for the verifier (public cryptographic material only).
_RSA_E = 65537
_RSA_N = int(
    "88e3b1105b0c593e52f0ef365db4d6c0d93f6d53d59b361c0dd3a8539a343734"
    "d3b782c1dff188225d3308fbb514f6790b9175431f18bed22773bb5b0d14a220"
    "c8756976babd2ea0cf6335267151735378d1a6062376a28d1f5a65dcfb16404d"
    "eb9680397abc70c1393456adf8ce0e16fcc661236aee7f9fe0aefc651d60fb11"
    "d787ee0f512b21bc88c1975c9812d0bbb415e2956ed267c961b1bfad451f2378"
    "738c323626e0461a319ca3c0ab8d21cb535905d1eb0a2ba55595974bf1ae96dc"
    "1e0424dca706714c890b27aae6492720d90841e76a2825610bc027f676b73981"
    "8fa5e762fcfba20d1606bd172e8bf4842a6d5007b7d0e0f519cd2366c13153f5",
    16,
)


def route_b_verifier(key_id: str = PROVIDER_KEY_ID) -> LateReturnVerifier:
    """Return the public verifier corresponding to the external provider signer."""
    return LateReturnVerifier(
        key_id=key_id,
        algorithm="rsa-pkcs1v15-sha256",
        modulus_hex=f"{_RSA_N:x}",
        public_exponent=_RSA_E,
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
        target.write_bytes(source.read_bytes())


def _run_provider_subprocess(
    cmd: str, mailbox: Path, request_id: str
) -> dict[str, object]:
    """Execute provider operation in an isolated child subprocess."""
    mailbox = Path(mailbox)
    env = dict(os.environ)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.c15_persistence.provider_process",
            cmd,
            str(mailbox),
            request_id,
        ],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"provider_process {cmd} failed (exit {completed.returncode}):\n"
            f"stdout: {completed.stdout}\nstderr: {completed.stderr}"
        )
    report = json.loads(completed.stdout.strip())
    provider_pid = int(report.get("provider_pid", 0))
    if provider_pid == os.getpid():
        raise RuntimeError(
            "Security violation: provider_process ran in the same process as operator!"
        )
    return report


def dispatch(mailbox: Path, request_id: str) -> dict[str, object]:
    """Cross the provider submission boundary exactly once in a separate process."""
    return _run_provider_subprocess("dispatch", mailbox, request_id)


def collect(mailbox: Path, request_id: str) -> dict[str, object]:
    """Collect the exact reply for an already-dispatched request via provider subprocess."""
    return _run_provider_subprocess("collect", mailbox, request_id)


def serve(mailbox: Path, request_id: str) -> dict[str, object]:
    """Compatibility helper: dispatch once, then collect the exact reply."""
    return _run_provider_subprocess("serve", mailbox, request_id)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: provider.py <mailbox_dir> <request_id>", file=sys.stderr)
        return 2
    report = serve(Path(argv[1]), argv[2])
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
