"""Verifier-only authenticity for provider returns that arrive after Core death.

The trusted external/provider side owns the signing key.  Core persists only the
public verifier and the exact request scope.  This module intentionally contains no
signing helper, private key, nonce, proof preimage, or capability object.

Corrective-002 (`BLK-W17-003`) freezes one canonical proof encoding and one
canonical verifier-parameter contract:

``proof``
    ``bglate_rsa_v1:<key_id>:<signature_hex>``.  The encoding is unambiguous only
    because :data:`LATE_RETURN_KEY_ID_PATTERN` forbids ``":"`` inside ``key_id``,
    so ``encoded.split(":", 1)`` always recovers the exact identifier that was
    accepted at construction.  :func:`canonical_late_return_proof` mechanically
    enforces ``encode -> decode -> identical key_id`` for every allowed id.

``key_id``
    Canonical grammar only: 1..128 characters, first character alphanumeric,
    remaining characters ``[A-Za-z0-9._-]``.  Delimiter-bearing, empty, padded or
    otherwise non-canonical identifiers are rejected at construction rather than
    accepted and then made permanently unverifiable.

``modulus_hex``
    Canonical, normalized, unsigned lowercase hexadecimal produced by ``"%x"`` of
    the exact integer value (no sign, no ``0x`` prefix, no ``+``, no underscores,
    no whitespace, no uppercase, no leading zero).  Parsing rejects signed,
    malformed or non-normalized representations instead of silently coercing them.

``public_exponent`` / ``modulus``
    A verifier is only constructible with a positive **odd** modulus of at least
    2048 bits and a positive odd public exponent with ``3 <= e < n``.  A verifier
    that could be durably bound but could never verify a genuine signature (for
    example a negative modulus, or a key id that cannot round-trip) is refused
    before durable binding, per `C2-5` / `C2-6`.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.storage.idempotency import canonical_json_dumps

if False:  # pragma: no cover - typing without a runtime import cycle
    from .cognitive_runtime import RuntimeSnapshot


LATE_RETURN_PROOF_PREFIX = "bglate_rsa_v1:"
LATE_RETURN_SCHEMA = "aios.background-model-late-return.rsa.v1"
LATE_RETURN_ALGORITHM = "rsa-pkcs1v15-sha256"
# Minimum RSA modulus strength accepted for a durable late-return verifier.
LATE_RETURN_MINIMUM_MODULUS_BITS = 2048
# Canonical key-id grammar.  Deliberately excludes ":" so the proof encoding is
# unambiguous, and excludes whitespace/control/unicode so a durable row always
# re-serializes to the same bytes.
LATE_RETURN_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
# Canonical normalized lowercase hexadecimal, no leading zero.
LATE_RETURN_MODULUS_HEX_PATTERN = re.compile(r"^(0|[1-9a-f][0-9a-f]*)$")

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


class LateReturnVerifierError(RuntimeError):
    """Durable verifier material is unusable; every dependent path fails closed."""


class LateReturnEncodingError(ValueError):
    """A proof or key id does not satisfy the frozen canonical encoding."""


def canonical_key_id(key_id: object) -> str:
    """Return ``key_id`` if it satisfies the frozen canonical grammar."""

    if not isinstance(key_id, str):
        raise LateReturnEncodingError("late return key_id must be a string")
    if not LATE_RETURN_KEY_ID_PATTERN.match(key_id):
        raise LateReturnEncodingError(
            "late return key_id must match "
            f"{LATE_RETURN_KEY_ID_PATTERN.pattern!r} (delimiter, whitespace, "
            "unicode and non-canonical identifiers are refused)"
        )
    return key_id


def canonical_modulus_hex(modulus_hex: object) -> tuple[str, int]:
    """Return ``(canonical_hex, value)`` for a canonical positive odd RSA modulus."""

    if not isinstance(modulus_hex, str):
        raise LateReturnEncodingError("late return modulus_hex must be a string")
    if not LATE_RETURN_MODULUS_HEX_PATTERN.match(modulus_hex):
        raise LateReturnEncodingError(
            "late return modulus_hex must be canonical unsigned lowercase "
            "hexadecimal without sign, prefix, whitespace, underscores, "
            "uppercase characters or leading zeros"
        )
    modulus = int(modulus_hex, 16)
    if modulus <= 0:
        raise LateReturnEncodingError(
            "late return verifier RSA modulus must be positive"
        )
    if modulus % 2 == 0:
        raise LateReturnEncodingError(
            "late return verifier RSA modulus must be odd"
        )
    if modulus.bit_length() < LATE_RETURN_MINIMUM_MODULUS_BITS:
        raise LateReturnEncodingError(
            "late return verifier RSA modulus must be at least "
            f"{LATE_RETURN_MINIMUM_MODULUS_BITS} bits"
        )
    if f"{modulus:x}" != modulus_hex:
        # Defensive: the pattern above already forbids every non-normalized form.
        raise LateReturnEncodingError(
            "late return modulus_hex is not the canonical normalization of its value"
        )
    return modulus_hex, modulus


def canonical_public_exponent(public_exponent: object, *, modulus: int) -> int:
    """Return a valid RSA public exponent or raise."""

    if isinstance(public_exponent, bool) or not isinstance(public_exponent, int):
        raise LateReturnEncodingError(
            "late return public_exponent must be an integer"
        )
    if public_exponent <= 1:
        raise LateReturnEncodingError(
            "late return public exponent must be greater than 1"
        )
    if public_exponent % 2 == 0:
        raise LateReturnEncodingError(
            "late return public exponent must be odd"
        )
    if public_exponent >= modulus:
        raise LateReturnEncodingError(
            "late return public exponent must be smaller than the modulus"
        )
    return public_exponent


def canonical_late_return_proof(*, key_id: str, signature_hex: str) -> str:
    """Encode a proof and mechanically prove ``encode -> decode -> same key_id``."""

    canonical = canonical_key_id(key_id)
    if not isinstance(signature_hex, str) or not signature_hex:
        raise LateReturnEncodingError(
            "late return proof signature must be non-empty lowercase hexadecimal"
        )
    if not re.match(r"^[0-9a-f]+$", signature_hex):
        raise LateReturnEncodingError(
            "late return proof signature must be lowercase hexadecimal"
        )
    encoded = f"{LATE_RETURN_PROOF_PREFIX}{canonical}:{signature_hex}"
    decoded_key_id, decoded_signature = decode_late_return_proof(encoded)
    if decoded_key_id != canonical or decoded_signature != signature_hex:
        raise LateReturnEncodingError(
            "late return proof encoding does not round-trip its key id"
        )
    return encoded


def decode_late_return_proof(proof: str) -> tuple[str, str]:
    """Split a proof into ``(key_id, signature_hex)`` under the frozen encoding."""

    if not isinstance(proof, str) or not proof.startswith(LATE_RETURN_PROOF_PREFIX):
        raise LateReturnEncodingError(
            f"late return proof must start with {LATE_RETURN_PROOF_PREFIX!r}"
        )
    encoded = proof[len(LATE_RETURN_PROOF_PREFIX) :]
    key_id, separator, signature_hex = encoded.partition(":")
    if not separator:
        raise LateReturnEncodingError(
            "late return proof must contain a key id and a signature"
        )
    # A colon can never occur inside a canonical key id, so any extra colon here
    # means the caller supplied a malformed or ambiguous encoding.
    if ":" in signature_hex:
        raise LateReturnEncodingError(
            "late return proof signature contains a reserved delimiter"
        )
    canonical_key_id(key_id)
    if not signature_hex or not re.match(r"^[0-9a-f]+$", signature_hex):
        raise LateReturnEncodingError(
            "late return proof signature must be non-empty lowercase hexadecimal"
        )
    return key_id, signature_hex


class LateReturnVerifier(BaseModel):
    """Public verifier material durably scoped to one provider trust domain."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key_id: str = Field(min_length=1)
    algorithm: str = Field(pattern=r"^rsa-pkcs1v15-sha256$")
    modulus_hex: str = Field(min_length=1)
    public_exponent: int

    @model_validator(mode="after")
    def _validate_canonical_parameters(self) -> "LateReturnVerifier":
        # Order matters for error clarity: encoding/key id first, then RSA numbers.
        canonical_key_id(self.key_id)
        _, modulus = canonical_modulus_hex(self.modulus_hex)
        canonical_public_exponent(self.public_exponent, modulus=modulus)
        return self

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
    try:
        key_id, signature_hex = decode_late_return_proof(proof)
    except LateReturnEncodingError:
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
    "LATE_RETURN_ALGORITHM",
    "LATE_RETURN_KEY_ID_PATTERN",
    "LATE_RETURN_MINIMUM_MODULUS_BITS",
    "LATE_RETURN_MODULUS_HEX_PATTERN",
    "LATE_RETURN_PROOF_PREFIX",
    "LateReturnEncodingError",
    "LateReturnSigningContext",
    "LateReturnVerifier",
    "LateReturnVerifierError",
    "canonical_key_id",
    "canonical_late_return_proof",
    "canonical_modulus_hex",
    "canonical_public_exponent",
    "decode_late_return_proof",
    "late_return_message",
    "verify_late_return_proof",
]
