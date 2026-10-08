"""Deterministic, cross-process synthetic provider for the kill/restart probes.

Why a separate process
----------------------
The probes need a *provider boundary* whose dispatch count is observable and
durable, and which survives the death of the operator process. Writing the
request to a durable outbox and having a **separate process** answer it gives an
exact, countable dispatch event that is independent of the operator's memory.

The provider is deliberately dumb and deterministic:

* the reply is a pure function of the exact request bytes, so re-presenting the
  same request after a restart yields byte-identical reply bytes;
* a request identity is dispatched **once** - the dispatch ledger is append-only
  and keyed by request id, so re-presenting an outstanding request never creates
  a second dispatch;
* it never inspects Core, never touches World, and never decides anything: it
  only turns request bytes into reply bytes;
* provider-side signing authority lives exclusively within the provider boundary
  and is NEVER exposed to operator or recovery callers.

This stands in for the Resident-facing relay. It is synthetic: no real Resident
is contacted and no real model provider is called.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

CAPABILITY_NAME = "c15_probe_capability"
PROVIDER_NAME = "c15-synthetic-relay"
MODEL_NAME = "c15-synthetic-model"
PROVIDER_KEY_ID = "c15-synthetic-provider-key"


def _bootstrap() -> None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "src" / "aios_core").is_dir():
            sys.path.insert(0, str(parent / "src"))
            return


_bootstrap()

from aios_core.runtime import CapabilityCall, ModelCallProvenance, ModelDirective, ModelUsage  # noqa: E402
from aios_core.runtime.background_attempt import decode_model_directive, encode_model_directive  # noqa: E402
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


# Internal provider-side authority instance (lazily initialized within provider boundary).
_provider_authority_instance = None


def _get_provider_authority():
    global _provider_authority_instance
    if _provider_authority_instance is None:
        from ._provider_authority import ProviderSigningAuthority
        _provider_authority_instance = ProviderSigningAuthority(key_id=PROVIDER_KEY_ID)
    return _provider_authority_instance


class ProviderReturnObserver(ExternalReturnObserver):
    """Provider boundary observer capturing dispatch context outside operator control."""

    def accept_return_context(
        self, snapshot: object, context: LateReturnSigningContext
    ) -> None:
        authority = _get_provider_authority()
        authority.accept_return_context(snapshot, context)


_observer_instance = ProviderReturnObserver()


def get_provider_observer() -> ExternalReturnObserver:
    """Return the provider-side dispatch context observer."""
    return _observer_instance


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


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build_directive(request: bytes) -> ModelDirective:
    """Deterministic ModelDirective for exact request bytes."""
    envelope = json.loads(request.decode("utf-8"))
    request_id = str(envelope["model_request_id"])
    attempt_id = str(envelope["attempt_id"])
    round_index = int(envelope["round"])
    provider = str(envelope["provider"])
    model = str(envelope["model"])
    turn_text = str(envelope["resident_visible_payload"])

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


def build_reply(request: bytes) -> bytes:
    """Deterministic reply bytes for exact request bytes."""
    directive = build_directive(request)
    return encode_model_directive(directive).encode("utf-8")


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    dir_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _mirror(mailbox: Path, source: Path, target: Path) -> None:
    """Keep a stable ``current.*`` slot so re-attach manifests stay meaningful."""
    if source.is_file():
        _atomic_write(target, source.read_bytes())


def dispatch(mailbox: Path, request_id: str) -> dict[str, object]:
    """Cross the provider submission boundary exactly once, without returning a reply."""
    mailbox = Path(mailbox)
    request_file = outbox_path(mailbox, request_id)
    if not request_file.is_file():
        raise SystemExit(f"provider: no durable request for {request_id}")
    request = request_file.read_bytes()
    request_sha = digest(request)
    previous = [row for row in read_ledger(mailbox) if row.get("request_id") == request_id]
    if previous:
        return {
            "request_id": request_id,
            "request_sha256": request_sha,
            "dispatch": "reattached",
            "dispatch_count": len(previous),
        }
    append_ledger(
        mailbox,
        {
            "request_id": request_id,
            "request_sha256": request_sha,
            "dispatched_at_epoch": time.time(),
            "provider_pid": os.getpid(),
        },
    )
    return {
        "request_id": request_id,
        "request_sha256": request_sha,
        "dispatch": "dispatched",
        "dispatch_count": 1,
    }


def read_proof(mailbox: Path, request_id: str) -> dict[str, Any] | None:
    """Read provider-produced proof from inbox if available."""
    p_file = proof_path(Path(mailbox), request_id)
    if not p_file.is_file():
        return None
    try:
        return json.loads(p_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def collect(mailbox: Path, request_id: str) -> dict[str, object]:
    """Collect the exact reply for an already-dispatched request without redispatch."""
    mailbox = Path(mailbox)
    request_file = outbox_path(mailbox, request_id)
    if not request_file.is_file():
        raise SystemExit(f"provider: no durable request for {request_id}")
    request = request_file.read_bytes()
    request_sha = digest(request)
    previous = [row for row in read_ledger(mailbox) if row.get("request_id") == request_id]
    if not previous:
        raise SystemExit(f"provider: request {request_id} was never dispatched")
    reply_file = inbox_path(mailbox, request_id)
    proof_file = proof_path(mailbox, request_id)
    if not reply_file.is_file():
        directive = build_directive(request)
        reply = encode_model_directive(directive).encode("utf-8")
        _atomic_write(reply_file, reply)
        _mirror(mailbox, reply_file, current_reply_path(mailbox))

    if not proof_file.is_file():
        envelope = json.loads(request.decode("utf-8"))
        attempt_id = str(envelope["attempt_id"])
        authority = _get_provider_authority()
        if attempt_id in authority.contexts:
            directive = build_directive(request)
            proof_dict = authority.sign_exact_provider_response(attempt_id, directive)
            _atomic_write(proof_file, json.dumps(proof_dict, sort_keys=True).encode("utf-8"))
    return {
        "request_id": request_id,
        "request_sha256": request_sha,
        "dispatch": "reattached",
        "dispatch_count": len(previous),
        "reply_sha256": digest(reply_file.read_bytes()),
    }


def serve(mailbox: Path, request_id: str) -> dict[str, object]:
    """Compatibility helper: dispatch once, then collect the exact reply."""
    dispatch_report = dispatch(mailbox, request_id)
    reply_report = collect(mailbox, request_id)
    return {
        **reply_report,
        "dispatch": dispatch_report["dispatch"],
        "dispatch_count": dispatch_report["dispatch_count"],
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: provider.py <mailbox_dir> <request_id>", file=sys.stderr)
        return 2
    report = serve(Path(argv[1]), argv[2])
    print(json.dumps(report, sort_keys=True))
    return 0
