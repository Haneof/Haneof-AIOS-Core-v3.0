"""CA2-010 .. CA2-014: canonical late-return encoding and RSA parameter contract.

Corrective-002 (`BLK-W17-003`, `C2-5` / `C2-6`) frozen expectations:

* the proof encoding ``bglate_rsa_v1:<key_id>:<signature>`` is unambiguous, so
  ``encode -> decode -> identical key_id`` holds for every allowed identifier;
* every identifier that cannot round-trip (in particular any ``":"`` or other
  non-canonical form) is refused at construction instead of being durably bound
  and then being permanently unverifiable;
* only a positive odd modulus of at least 2048 bits and a positive odd exponent
  ``3 <= e < n`` may be durably bound;
* a genuine external signature still verifies for every accepted verifier.
"""

from __future__ import annotations

import hashlib

import pytest

from aios_core.runtime.late_return import (
    LATE_RETURN_PROOF_PREFIX,
    LateReturnEncodingError,
    LateReturnVerifier,
    canonical_key_id,
    canonical_late_return_proof,
    canonical_modulus_hex,
    canonical_public_exponent,
    decode_late_return_proof,
    late_return_message,
    verify_late_return_proof,
)

_RSA_E = 65537
# Independent Corrective-002 engineering test keypair (distinct from any
# reviewer-owned Window 17 material).
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
_RSA_D = int(
    "4f65a141974da6459bdddb2171607e5f04a2e14a8acea7a7c5ed49e893bc4d78"
    "fa83a9f7c1685a49743d31acacef27b6359b7ca41dd94074ac25583a0b703849"
    "437bb65c031bcf7bbe4e1079e7a812780bcfadb849c179aed8cc99e07e51fda2"
    "344eeab86c13f8625a479d2ef2ecb1076c3db401d2f7da5664ff99ad1c492fd5"
    "de8b9b604849dc3e3eeaf84939f171cc95c73a7ecf05479c722f1037ee1e029e"
    "f2bffec168a14e2e3b344c3cb0d0f210c2619eb39fc4a43c2b10046b1b59f5dc"
    "4eff617acc02628c7a1433d2e37486a6d8a51a21d8713da54a866c57fb2320d4"
    "1b7e3e5347f3cb83e6df0514314dc9adc34ba4618fd67db8e717f061016ec651",
    16,
)
_SHA256_DER = bytes.fromhex("3031300d060960864801650304020105000420")

_ALLOWED_KEY_IDS = (
    "k",
    "provider-key-2026-v1",
    "provider.key_2026.v1",
    "A1",
    "0",
    "0x-prefixed",
    "x" * 128,
)
_REJECTED_KEY_IDS = (
    "provider:key-2026-v1",
    ":leading",
    "trailing:",
    "",
    " has-space",
    "has space",
    "has\ttab",
    "has\nnewline",
    "unicode-ключ",
    "x" * 129,
    "-leading-dash",
    "_leading-underscore",
    ".",
)


def make_verifier(key_id: str = "corrective-002-ext-key") -> LateReturnVerifier:
    return LateReturnVerifier(
        key_id=key_id,
        algorithm="rsa-pkcs1v15-sha256",
        modulus_hex=f"{_RSA_N:x}",
        public_exponent=_RSA_E,
    )


def rsa_sign(message: bytes, key_id: str) -> str:
    digest_info = _SHA256_DER + hashlib.sha256(message).digest()
    size = (_RSA_N.bit_length() + 7) // 8
    encoded = (
        b"\x00\x01"
        + (b"\xff" * (size - len(digest_info) - 3))
        + b"\x00"
        + digest_info
    )
    signature = pow(int.from_bytes(encoded, "big"), _RSA_D, _RSA_N)
    return canonical_late_return_proof(
        key_id=key_id, signature_hex=signature.to_bytes(size, "big").hex()
    )


def sample_message() -> bytes:
    return late_return_message(
        attempt_id="bgattempt_ca2",
        subject_id="subject",
        work_kind="user_turn",
        work_id="work",
        model_round_index=0,
        outbound_request_fingerprint="a" * 64,
        relay_id="relay_ca2",
        provider="provider-ca2",
        model="model-ca2",
        provider_request_id="request-ca2",
        response_fingerprint="b" * 64,
        payload_sha256="c" * 64,
    )


# --------------------------------------------------------------------- CA2-010
@pytest.mark.parametrize("key_id", _ALLOWED_KEY_IDS)
def test_ca2_010_allowed_key_id_round_trips_exactly(key_id: str) -> None:
    verifier = make_verifier(key_id)
    message = sample_message()
    proof = rsa_sign(message, key_id)

    decoded_key_id, decoded_signature = decode_late_return_proof(proof)
    assert decoded_key_id == key_id
    assert proof.startswith(f"{LATE_RETURN_PROOF_PREFIX}{key_id}:")
    assert verify_late_return_proof(verifier, message=message, proof=proof) is True
    assert (
        canonical_late_return_proof(
            key_id=key_id, signature_hex=decoded_signature
        )
        == proof
    )


@pytest.mark.parametrize("key_id", _REJECTED_KEY_IDS)
def test_ca2_010_ambiguous_or_non_canonical_key_id_refused_at_construction(
    key_id: str,
) -> None:
    with pytest.raises(ValueError):
        make_verifier(key_id)
    with pytest.raises(LateReturnEncodingError):
        canonical_key_id(key_id)


def test_ca2_010_colon_key_id_can_never_be_durably_bound() -> None:
    """The historical defect: accepted at binding time, unverifiable afterwards."""

    with pytest.raises(ValueError):
        LateReturnVerifier(
            key_id="provider:key-2026-v1",
            algorithm="rsa-pkcs1v15-sha256",
            modulus_hex=f"{_RSA_N:x}",
            public_exponent=_RSA_E,
        )


def test_ca2_010_proof_parser_refuses_extra_delimiters_and_malformed_hex() -> None:
    message = sample_message()
    verifier = make_verifier()
    good = rsa_sign(message, verifier.key_id)
    signature_hex = good.rsplit(":", 1)[1]

    for malformed in (
        f"{LATE_RETURN_PROOF_PREFIX}{verifier.key_id}:{signature_hex}:extra",
        f"{LATE_RETURN_PROOF_PREFIX}{verifier.key_id}:{signature_hex.upper()}",
        f"{LATE_RETURN_PROOF_PREFIX}{verifier.key_id}:",
        f"{LATE_RETURN_PROOF_PREFIX}{verifier.key_id}",
        f"{LATE_RETURN_PROOF_PREFIX}other-key:{signature_hex}",
        f"bglate_other_v1:{verifier.key_id}:{signature_hex}",
    ):
        assert verify_late_return_proof(
            verifier, message=message, proof=malformed
        ) is False


# --------------------------------------------------------------------- CA2-011
@pytest.mark.parametrize(
    "modulus_hex,label",
    (
        (f"-{_RSA_N:x}", "negative"),
        ("0", "zero"),
        ("1", "one"),
        (f"{_RSA_N + 1:x}", "even"),
        (f"{(1 << 1024) + 1:x}", "undersized-1025-bit"),
        (f"{1 << 2047:x}", "even-2048-bit"),
        (f"0{_RSA_N:x}", "leading-zero"),
        (f"{_RSA_N:x}".upper(), "uppercase"),
        (f"0x{_RSA_N:x}", "0x-prefix"),
        (f"+{_RSA_N:x}", "plus-sign"),
        (f"{_RSA_N:x}_", "trailing-underscore"),
        (f" {_RSA_N:x}", "leading-space"),
        ("", "empty"),
        ("not-hex", "non-hexadecimal"),
    ),
)
def test_ca2_011_invalid_modulus_refused_before_durable_binding(
    modulus_hex: str, label: str
) -> None:
    del label
    with pytest.raises(ValueError):
        LateReturnVerifier(
            key_id="ca2-key",
            algorithm="rsa-pkcs1v15-sha256",
            modulus_hex=modulus_hex,
            public_exponent=_RSA_E,
        )


def test_ca2_011_negative_modulus_is_not_silently_usable() -> None:
    """The historical defect: ``bit_length`` alone accepted ``-<modulus>``."""

    with pytest.raises(ValueError):
        LateReturnVerifier(
            key_id="neg-mod-key",
            algorithm="rsa-pkcs1v15-sha256",
            modulus_hex=f"-{_RSA_N:x}",
            public_exponent=_RSA_E,
        )


def test_ca2_011_canonical_modulus_helper_contract() -> None:
    canonical, value = canonical_modulus_hex(f"{_RSA_N:x}")
    assert canonical == f"{_RSA_N:x}"
    assert value == _RSA_N
    assert canonical == f"{value:x}"


# --------------------------------------------------------------------- CA2-012
@pytest.mark.parametrize(
    "exponent",
    (-65537, -1, 0, 1, 2, 3 - 3, 4, 6, 65536, _RSA_N, _RSA_N + 2),
)
def test_ca2_012_invalid_public_exponent_refused(exponent: int) -> None:
    with pytest.raises(ValueError):
        LateReturnVerifier(
            key_id="ca2-key",
            algorithm="rsa-pkcs1v15-sha256",
            modulus_hex=f"{_RSA_N:x}",
            public_exponent=exponent,
        )


def test_ca2_012_exponent_helper_rejects_non_integers_and_booleans() -> None:
    for bad in (True, False, "65537", 3.0, None):
        with pytest.raises((LateReturnEncodingError, TypeError)):
            canonical_public_exponent(bad, modulus=_RSA_N)  # type: ignore[arg-type]


def test_ca2_012_algorithm_must_be_the_frozen_one() -> None:
    with pytest.raises(ValueError):
        LateReturnVerifier(
            key_id="ca2-key",
            algorithm="rsa-pkcs1v15-md5",
            modulus_hex=f"{_RSA_N:x}",
            public_exponent=_RSA_E,
        )


# --------------------------------------------------------------------- CA2-013
def test_ca2_013_valid_boundary_verifier_verifies_a_genuine_signature() -> None:
    verifier = make_verifier("boundary.key-2026_v1")
    message = sample_message()
    proof = rsa_sign(message, verifier.key_id)

    assert verifier.modulus_int == _RSA_N
    assert verifier.modulus_hex == f"{_RSA_N:x}"
    assert verify_late_return_proof(verifier, message=message, proof=proof) is True
    # Maximum allowed key id length is still exact, not truncated.
    longest = make_verifier("y" * 128)
    longest_proof = rsa_sign(message, longest.key_id)
    assert verify_late_return_proof(
        longest, message=message, proof=longest_proof
    ) is True


# --------------------------------------------------------------------- CA2-014
@pytest.mark.parametrize(
    "field_name",
    (
        "attempt_id",
        "subject_id",
        "work_kind",
        "work_id",
        "model_round_index",
        "outbound_request_fingerprint",
        "relay_id",
        "provider",
        "model",
        "provider_request_id",
        "response_fingerprint",
        "payload_sha256",
    ),
)
def test_ca2_014_every_bound_field_transplant_fails_closed(field_name: str) -> None:
    verifier = make_verifier()
    fields: dict[str, object] = {
        "attempt_id": "bgattempt_ca2",
        "subject_id": "subject",
        "work_kind": "user_turn",
        "work_id": "work",
        "model_round_index": 0,
        "outbound_request_fingerprint": "a" * 64,
        "relay_id": "relay_ca2",
        "provider": "provider-ca2",
        "model": "model-ca2",
        "provider_request_id": "request-ca2",
        "response_fingerprint": "b" * 64,
        "payload_sha256": "c" * 64,
    }
    proof = rsa_sign(late_return_message(**fields), verifier.key_id)

    mutated = dict(fields)
    mutated[field_name] = (
        1 if field_name == "model_round_index" else "transplanted-" + field_name
    )
    assert (
        verify_late_return_proof(
            verifier, message=late_return_message(**mutated), proof=proof
        )
        is False
    )
