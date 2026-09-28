# BLOCKED DRAFT — C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE

Status: `DRAFT / NOT READY / DO NOT EXECUTE`

Activation:
- Corrective-003 has been formally re-released after accepted RC-003 + A-004 lineage;
- a new scope-correct candidate exists;
- candidate contains no unauthorized `src/aios_core/**` change;
- task board releases this IA.

Role:
Independent Persistence Corrective Reviewer.

Frozen binding scope:
1. C002-001 — authoritative remote checkpoint failure hard-stops the normal operator path and cannot be swallowed by structured capability-error wrapping.
2. C002-002 — later-round K3/K5 remote-only crash recovery converges exactly once without redispatch, duplicate semantic work/output/metering/ACK.
3. C002-004 — remote-authoritative binding loss/corruption cannot silently downgrade to local-only.

Preserve ordinary generation-corruption checks.

Do not promote the historical non-blocking hardening findings 003/005/006 into release blockers unless fresh governance explicitly changes scope.

Required fresh probes:
- kill/restart at reveal;
- ingest;
- provider staged;
- trusted reply/application boundary;
- capability/model-before-ACK;
- push-success/local-cache-loss;
- remote metadata missing/corrupt/unavailable;
- authoritative checkpoint failure through a real registered capability path;
- later-round multi-step model/capability recovery;
- no duplicate reveal/ingest/semantic application/output/meter/ACK;
- projection/binding/mailbox/failure evidence survival.

Candidate must remain a C15 operator/release persistence harness, not a new product truth store.

Verdict:
`ACCEPTANCE_PASS / blocker=0` or `ACCEPTANCE_FAIL / blocker=N`.

Do not release B.
