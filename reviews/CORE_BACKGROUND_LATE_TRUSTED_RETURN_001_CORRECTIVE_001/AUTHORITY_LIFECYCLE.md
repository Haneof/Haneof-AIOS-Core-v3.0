# AUTHORITY_LIFECYCLE — Phase D consumption freeze

This probe was added before the Phase D production change that introduces verifier
consumption state.

Binding requirements:

- External trusted side owns the private RSA signing key.
- Core stores only the public verifier + exact first-dispatch scope.
- First valid late-return proof atomically marks the verifier consumed together with
  the durable receipt/handoff authority.
- Exact identical attach remains idempotent.
- A second, genuinely valid signature under the same external key for different
  response bytes is rejected and cannot create a second receipt, handoff, staged
  response, meter, semantic effect, output, completion or ACK.
- Recovery never resets or rotates the verifier.
