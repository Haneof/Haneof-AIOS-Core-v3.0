"""Verifier-only authenticity for provider returns that arrive after Core death.

The trusted external/provider side owns the signing key.  Core persists only the
public verifier and the exact request scope.  This module intentionally contains no
signing helper, private key, nonce, proof preimage, or capability object.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from aios_core.storage.idempotency import canonical_json_dumps

if False:  # pragma: no cover - typing without a runtime import cycle
    from .cognitive_runtime import RuntimeSnapshot


LATE_RETURN_PROOF_PREFIX = "bglate_rsa_v1:"
LATE_RETURN_SCHEMA = "aios.background-model-late-return.rsa.v1"

_SCOPE_FIELDS = (
    "attempt_id",
    "subject_id",
    "work_kind",
    "work_id",
    "model_round_index",
    "outbound_request_fingerprint",
    "relay_id",
)
_RESPONSE_FIELDS = (
    "provider",
    "model",
    "provider_request_id",
    "response_fingerprint",
    "payload_sha256",
)
_SHA256_DIGEST_INFO_PREFIX = bytes.fromhex(
    "3031300d060960864801650304020105000420"
)


class LateReturnVerifier(BaseModel):
    """Public verifier material durably scoped to one provider trust domain."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key_id: str = Field(min_length=1)
    algorithm: str = Field(pattern=r"^rsa-pkcs1v15-sha256$")
    modulus_hex: str = Field(min_length=1)
    public_exponent: int = Field(ge=3)

    def __init__(self, **data: object) -> None:
        super().__init__(**data)
        try:
            modulus = int(self.modulus_hex, 16)
        except ValueError as exc:
            raise ValueError("late return verifier modulus_hex must be hexadecimal") from exc
        if modulus.bit_length() < 2048:
            raise ValueError("late return verifier RSA modulus must be at least 2048 bits")
        if self.public_exponent % 2 == 0:
            raise ValueError("late return verifier public exponent must be odd")

    @property
    def modulus_int(self) -> int:
        return int(self.modulus_hex, 16)


class LateReturnSigningContext(BaseModel):
    """Public request scope sent to an external signer before provider dispatch.

    Despite the name, this object is not signing authority: it contains only public
    attempt/request identity plus the verifier key id.  The private key remains
    outside Core.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    work_kind: str = Field(min_length=1)
    work_id: str = Field(min_length=1)
    model_round_index: int = Field(ge=0)
    outbound_request_fingerprint: str = Field(min_length=1)
    relay_id: str = Field(min_length=1)
    verifier_key_id: str = Field(min_length=1)

    def scope_fields(self) -> dict[str, object]:
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
    """Receives public signing context; external code retains all private authority."""

    def accept_return_context(
        self,
        snapshot: "RuntimeSnapshot",
        context: LateReturnSigningContext,
    ) -> None:  # pragma: no cover - protocol declaration
        ...


def late_return_message(**fields: object) -> bytes:
    """Canonical message an external trusted side signs and Core verifies."""

    missing = [
        name
        for name in (*_SCOPE_FIELDS, *_RESPONSE_FIELDS)
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


def verify_late_return_proof(
    verifier: LateReturnVerifier,
    *,
    message: bytes,
    proof: str,
) -> bool:
    """Verify RSA PKCS#1 v1.5 SHA-256 using public material only."""

    if not isinstance(verifier, LateReturnVerifier):
        raise TypeError("verifier must be LateReturnVerifier")
    if not isinstance(message, (bytes, bytearray)):
        raise TypeError("message must be bytes")
    if not isinstance(proof, str) or not proof.startswith(LATE_RETURN_PROOF_PREFIX):
        return False
    encoded = proof[len(LATE_RETURN_PROOF_PREFIX) :]
    try:
        key_id, signature_hex = encoded.split(":", 1)
    except ValueError:
        return False
    if key_id != verifier.key_id:
        return False
    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError:
        return False

    modulus = verifier.modulus_int
    width = (modulus.bit_length() + 7) // 8
    if len(signature) != width:
        return False
    signature_int = int.from_bytes(signature, "big")
    if signature_int <= 0 or signature_int >= modulus:
        return False

    decoded = pow(signature_int, verifier.public_exponent, modulus).to_bytes(
        width, "big"
    )
    digest_info = _SHA256_DIGEST_INFO_PREFIX + hashlib.sha256(bytes(message)).digest()
    padding_size = width - len(digest_info) - 3
    if padding_size < 8:
        return False
    expected = b"\x00\x01" + (b"\xff" * padding_size) + b"\x00" + digest_info
    return hmac.compare_digest(decoded, expected)


__all__ = [
    "ExternalReturnObserver",
    "LATE_RETURN_PROOF_PREFIX",
    "LateReturnSigningContext",
    "LateReturnVerifier",
    "late_return_message",
    "verify_late_return_proof",
]
