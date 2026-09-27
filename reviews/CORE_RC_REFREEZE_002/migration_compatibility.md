# Migration / existing store compatibility

Covered by recovery + authenticity tests (GREEN):

- fresh store: authority created deterministically (`INSERT OR IGNORE` authority_id `trusted-return-v1`)
- missing authenticity authority: fail closed
- malformed authority: fail closed
- old staged rows without proof: remain unauthenticated / fail closed (comment in source: historical staged rows have no authenticity authority)
- migration does not fabricate authenticity for historical unauthenticated responses

No data-destruction path observed in freeze gates.
