"""Private cryptographic authority for the synthetic provider.

ISOLATION BOUNDARY:
-------------------
This module contains private RSA signing key material (_RSA_D) and the signing
closure for the C15 synthetic provider.

Under the AIOS trust model:
1. Only the provider-side process/harness may import this module.
2. OperatorSession, RelayJournal, RunBackend, and all recovery callers MUST NOT
   import or reference this module.
3. Operator and recovery processes hold ONLY the public LateReturnVerifier
   material exposed through provider.route_b_verifier().
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from aios_core.runtime import ModelDirective
from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptStore,
    encode_model_directive,
)
from aios_core.runtime.late_return import (
    LateReturnSigningContext,
    LateReturnVerifier,
    late_return_message,
)

PROVIDER_KEY_ID = "c15-synthetic-provider-key"
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


def rsa_sign_message(message: bytes, key_id: str = PROVIDER_KEY_ID) -> str:
    """Sign canonical message bytes with the provider private key using RSA PKCS#1 v1.5 SHA-256."""
    digest_info = _SHA256_DER + hashlib.sha256(message).digest()
    size = (_RSA_N.bit_length() + 7) // 8
    encoded = (
        b"\x00\x01"
        + (b"\xff" * (size - len(digest_info) - 3))
        + b"\x00"
        + digest_info
    )
    signature = pow(int.from_bytes(encoded, "big"), _RSA_D, _RSA_N)
    return f"bglate_rsa_v1:{key_id}:" + signature.to_bytes(size, "big").hex()


class ProviderSigningAuthority:
    """Provider-internal authority for creating genuine cryptographic proofs."""

    def __init__(self, key_id: str = PROVIDER_KEY_ID) -> None:
        self.key_id = key_id
        self.contexts: dict[str, LateReturnSigningContext] = {}

    def accept_return_context(
        self, snapshot: object, context: LateReturnSigningContext
    ) -> None:
        self.contexts[context.attempt_id] = context

    def sign_exact_provider_response(
        self,
        attempt_id: str,
        directive: ModelDirective,
    ) -> dict[str, Any]:
        """Sign ONLY an exact provider-generated response for a registered context."""
        context = self.contexts.get(attempt_id)
        if context is None:
            raise KeyError(f"provider authority has no dispatch context for attempt {attempt_id}")
        payload = encode_model_directive(directive)
        fingerprint = BackgroundModelAttemptStore._response_fingerprint(directive)
        payload_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        fields: dict[str, object] = {
            **context.scope_fields(),
            "provider": directive.provenance.provider,
            "model": directive.provenance.model,
            "provider_request_id": directive.provenance.request_id,
            "response_fingerprint": fingerprint,
            "payload_sha256": payload_sha256,
        }
        msg = late_return_message(**fields)
        proof_str = rsa_sign_message(msg, context.verifier_key_id)
        return {
            "attempt_id": attempt_id,
            "authenticity_proof": proof_str,
            "provider": directive.provenance.provider,
            "model": directive.provenance.model,
            "provider_request_id": directive.provenance.request_id,
            "response_fingerprint": fingerprint,
            "relay_id": context.relay_id,
        }
