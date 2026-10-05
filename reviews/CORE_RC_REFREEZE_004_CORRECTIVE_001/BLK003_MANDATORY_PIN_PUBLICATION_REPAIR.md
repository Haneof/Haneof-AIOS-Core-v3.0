# BLK003_MANDATORY_PIN_PUBLICATION_REPAIR

Job B is separate, needs Job A, and has only contents:write. It has no checkout and executes no candidate script/helper. The fixed comment body uses GitHub context plus workflow literals and binds task, run id/attempt, exact candidate SHA, frozen software SHA, formal gate identity/result and canonical branch.

HTTP 201 is mandatory. Any other status prints the response and exits 1. Pre-run fault injection proves 201 -> 0 and 401/403/500 -> non-zero.
