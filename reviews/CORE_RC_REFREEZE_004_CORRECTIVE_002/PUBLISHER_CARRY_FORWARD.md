# Publisher carry-forward

IA25-BLK-003 remains CLOSED.

Production semantics:
- formal gate must succeed
- fresh canonical equality before publication
- HTTP 201 only
- transport failure fatal
- every non-201 fatal
- fresh canonical equality after publication
- no diagnostic status laundering
- no checkout or candidate executable under write token

Pre-final formal run 37268221493:
- workflow security static probe PASS
- live publication HTTP 201

Fresh disposable hosted run 37291221473 on CPython 3.12.14 / pytest 8.4.2:
- 200,202,204,301,302,307,400,401,403,404,409,422,429,500,502,503 -> nonzero
- 201 -> zero
- transport failure -> curl rc 7
- PUBLISHER_FULL_FAULT_MATRIX=PASS
