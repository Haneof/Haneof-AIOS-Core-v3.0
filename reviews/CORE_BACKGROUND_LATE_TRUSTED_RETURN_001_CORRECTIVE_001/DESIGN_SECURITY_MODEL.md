# DESIGN_SECURITY_MODEL

## Trust boundary

External trusted/provider side:
- owns the RSA private signing key;
- observes the genuine provider return;
- signs the canonical late-return message.

Core:
- receives only a public RSA verifier plus public request scope;
- durably pins verifier + first request binding before provider dispatch;
- after restart can VERIFY only;
- has no signing helper, private key, nonce, proof preimage, bearer capability, or proof-minting callable.

## Durable state

Core DB stores:
- attempt identity/state;
- first outbound request binding and relay id;
- RSA public verifier (key id, modulus, exponent, algorithm);
- verifier consumed-at marker;
- exact response receipt/handoff/staging after a valid proof.

Core DB does not store:
- private signing key;
- HMAC signing key;
- capability nonce;
- proof preimage.

Historical secret-at-rest tables are securely deleted and WAL-truncated during upgrade. They are not converted into new verifier authority.

## Authentication paths

1. Live in-process trusted return: Core callback directly owns the return event and atomically records exact receipt/handoff bytes. Receipt proof is an integrity fingerprint, not a signing authority.
2. Late post-death return: only an external RSA signature verified against the verifier pinned before dispatch can create the receipt/handoff.

Anonymous/local interrupted dispatch remains in_doubt / fail-closed.
