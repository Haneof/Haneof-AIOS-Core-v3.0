# Credential permission audit

Job A: rc004-freeze-gate
- contents: read
- pull-requests: read
- checkout persist-credentials: false
- candidate tests and probes execute only here
- no write token

Job B: rc004-mandatory-pin-publisher
- contents: write only
- no checkout
- no candidate helper, test, sourced repository code, or Python
- fixed inline workflow logic
- write authority limited to exact commit-comment publication

Job C: rc004-whole-run-identity-seal
- contents: read
- actions: read
- no checkout
- no candidate executable
- no write authority

IA25-BLK-002 credential-isolation sub-property remains CLOSED.
