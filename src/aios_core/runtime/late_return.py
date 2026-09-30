"""One-shot external return capability for a late trusted provider return.

Why this module exists
----------------------
The accepted ``CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001`` covers
a return that *crossed the in-process* model-return boundary and was durably handed
off before the crash. It cannot cover a return that only finishes **after** the Core
process has died: ``admit()`` raises ``BackgroundModelExecutionInDoubt`` before the
model handler runs, so the trusted-return callback is unreachable for that round and
``stage_exact_response`` has no receipt row to verify against.

Closing that gap without creating a signing oracle requires an authenticity
artifact that

* is produced **at** the external return boundary, not reconstructed during
  recovery;
* cannot be minted by an arbitrary recovery caller, and
* is scoped so narrowly that leaking it cannot be turned into a general signer.

This module provides exactly one such artifact: a **pre-issued, single-use,
per-attempt return capability**, handed to an explicitly registered external-return
observer at dispatch time and consumed by Core at most once.

The trust model in one paragraph
-------------------------------
Core mints a random 32-byte nonce *before* the provider handler runs, persists it
next to the durable originating-request binding, and hands the capability to the
registered observer. Only the holder of that capability can produce a late-return
proof, and the proof is an HMAC over the complete binding (attempt, subject, work
kind, work id, round, outbound request fingerprint, relay id) plus the exact
response identity and digests. A recovery caller holds none of that: it has
``attempt_id``, the response bytes, and metadata it can compute itself. Supplying
those three does not produce a proof, so supplying them can never produce a trusted
return. There is deliberately **no** public Core API that turns bytes into a proof.

What this is *not*
------------------
* It is not a signing oracle. The capability cannot speak for any attempt other
  than the exact one it was issued for, and Core consumes it once.
* It does not auto-upgrade anonymous/local model handlers. A capability is issued
  only when the embedder explicitly registers an ``ExternalReturnObserver``; with
  no registration, ``background_model_return_capabilities`` has no row and the
  late-return path is mechanically unavailable (fail closed).
* It is not a second truth store. It holds no response bytes and no semantic
  state; it is a security/recovery record living in the same runtime database.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from aios_core.storage.idempotency import canonical_json_dumps

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .cognitive_runtime import ModelDirective, RuntimeSnapshot

__all__ = [
    "LATE_RETURN_PROOF_PREFIX",
    "BackgroundModelReturnCapability",
    "ExternalReturnObserver",
    "late_return_message",
    "late_return_proof",
]

LATE_RETURN_PROOF_PREFIX = "bglate_v1_"

LATE_RETURN_SCHEMA = "aios.background-model-late-return.v1"

#: The exact fields a late trusted return is bound to. Identity fields that Core
#: already holds durably are never taken from the recovery caller.
LATE_RETURN_SCOPE_FIELDS = (
    "attempt_id",
    "subject_id",
    "work_kind",
    "work_id",
    "model_round_index",
    "outbound_request_fingerprint",
    "relay_id",
)

#: The exact response fields observed at the trusted external return boundary.
LATE_RETURN_RESPONSE_FIELDS = (
    "provider",
    "model",
    "provider_request_id",
    "response_fingerprint",
    "payload_sha256",
)


def late_return_message(**fields: object) -> bytes:
    """Canonical MAC message binding one exact late return to one exact attempt.

    Every key is required. A missing field is a programming error, never a value
    that may be filled with an empty or invented string.
    """

    missing = [
        name
        for name in (*LATE_RETURN_SCOPE_FIELDS, *LATE_RETURN_RESPONSE_FIELDS)
        if name not in fields
    ]
    if missing:
        raise ValueError(
            "late trusted return proof is missing required binding fields: "
            + ", ".join(sorted(missing))
        )
    payload = {
        "attempt_id": fields["attempt_id"],
        "model": fields["model"],
        "model_round_index": int(fields["model_round_index"]),
        "outbound_request_fingerprint": fields["outbound_request_fingerprint"],
        "payload_sha256": fields["payload_sha256"],
        "provider": fields["provider"],
        "provider_request_id": fields["provider_request_id"],
        "relay_id": fields["relay_id"],
        "response_fingerprint": fields["response_fingerprint"],
        "schema": LATE_RETURN_SCHEMA,
        "subject_id": fields["subject_id"],
        "work_id": fields["work_id"],
        "work_kind": fields["work_kind"],
    }
    return canonical_json_dumps(payload).encode("utf-8")


def late_return_proof(capability_nonce: bytes, **fields: object) -> str:
    """Mint or verify one late-return proof under a single-attempt capability."""

    if not isinstance(capability_nonce, (bytes, bytearray)) or len(capability_nonce) != 32:
        raise ValueError("a late trusted return capability requires a 32-byte nonce")
    digest = hmac.new(
        bytes(capability_nonce), late_return_message(**fields), hashlib.sha256
    ).hexdigest()
    return f"{LATE_RETURN_PROOF_PREFIX}{digest}"


class BackgroundModelReturnCapability(BaseModel):
    """One-shot, single-attempt authority to prove one late external return.

    Issued by the private dispatch-time issuer on
    :class:`BackgroundModelAttemptStore`
    at the moment the outbound request is dispatched, and handed only to the
    registered :class:`ExternalReturnObserver`. It is a bearer token for exactly
    one ``(attempt, round, originating request)`` triple.

    Security properties, all mechanically enforced by
    ``BackgroundModelAttemptStore.attach_late_trusted_return``:

    * it cannot mint a proof for a different attempt, round, subject, work item or
      originating request, because every scope field is verified against the durable
      pre-dispatch binding rather than against anything the caller says;
    * it cannot mint a proof for changed response bytes, because the exact response
      fingerprint and payload digest are inside the MAC message;
    * Core consumes it once, so a leaked capability yields at most one attach for
      one attempt and can never become a repeated or general signing oracle;
    * it never carries the store's receipt authenticity authority, which stays
      private and is used only for in-process receipt verification.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    work_kind: str = Field(min_length=1)
    work_id: str = Field(min_length=1)
    model_round_index: int = Field(ge=0)
    outbound_request_fingerprint: str = Field(min_length=1)
    relay_id: str = Field(min_length=1)

    _capability_nonce: bytes = PrivateAttr(default=b"")

    def __init__(
        self,
        *,
        attempt_id: str,
        subject_id: str,
        work_kind: str,
        work_id: str,
        model_round_index: int,
        outbound_request_fingerprint: str,
        relay_id: str,
        capability_nonce: bytes,
    ) -> None:
        super().__init__(
            attempt_id=attempt_id,
            subject_id=subject_id,
            work_kind=work_kind,
            work_id=work_id,
            model_round_index=model_round_index,
            outbound_request_fingerprint=outbound_request_fingerprint,
            relay_id=relay_id,
        )
        if (
            not isinstance(capability_nonce, (bytes, bytearray))
            or len(capability_nonce) != 32
        ):
            raise ValueError("a late trusted return capability requires a 32-byte nonce")
        self._capability_nonce = bytes(capability_nonce)

    def prove_external_return(self, directive: "ModelDirective") -> str:
        """Authenticate one exact external return observed at the return boundary.

        Call this at the moment the authorized observer actually receives the
        external response. The returned proof is contemporaneous with the real
        return and is the only thing Core will accept as authority for a late
        attach. An anonymous return with no provider/model/request identity is
        refused rather than being padded with invented strings.
        """

        from .background_attempt import (
            encode_model_directive,
            provider_identity,
            response_fingerprint,
        )

        provider, model, provider_request_id = provider_identity(directive)
        if provider is None or model is None or provider_request_id is None:
            raise ValueError(
                "a late trusted return must carry full provider/model/request_id "
                "identity; an anonymous external return can never be proven"
            )
        payload = encode_model_directive(directive)
        return late_return_proof(
            self._capability_nonce,
            attempt_id=self.attempt_id,
            subject_id=self.subject_id,
            work_kind=self.work_kind,
            work_id=self.work_id,
            model_round_index=self.model_round_index,
            outbound_request_fingerprint=self.outbound_request_fingerprint,
            relay_id=self.relay_id,
            provider=provider,
            model=model,
            provider_request_id=provider_request_id,
            response_fingerprint=response_fingerprint(directive),
            payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        )

    def scope_fields(self) -> dict[str, object]:
        """The durable binding this capability is scoped to."""

        return {
            "attempt_id": self.attempt_id,
            "subject_id": self.subject_id,
            "work_kind": self.work_kind,
            "work_id": self.work_id,
            "model_round_index": self.model_round_index,
            "outbound_request_fingerprint": self.outbound_request_fingerprint,
            "relay_id": self.relay_id,
        }


@runtime_checkable
class ExternalReturnObserver(Protocol):
    """A dispatch target authorized to observe the real external/provider return.

    Registering an observer is the embedder's explicit trust assertion that the
    configured model handler reaches a genuine external responder. Core issues a
    one-shot return capability to it at dispatch and to nobody else. An observer
    that never actually observes a real return simply never produces a proof, and
    the attempt stays fail-closed in ``in_doubt``.
    """

    def accept_return_capability(
        self, snapshot: "RuntimeSnapshot", capability: BackgroundModelReturnCapability
    ) -> None:  # pragma: no cover - protocol declaration
        ...


def new_capability_nonce() -> bytes:
    """Fresh, unguessable per-attempt capability nonce."""

    return secrets.token_bytes(32)
