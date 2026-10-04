# CORE-RC-REFREEZE-004 — RC impact adjudication

## Verdicts

`FRESH_A_REQUIRED`

`FRESH_OPERATOR_PREP_REQUIRED`

Historical Resident A evidence, including A-003, A-004, and every earlier A, is **HISTORICAL_FOR_PRIOR_RC_ONLY**. It must not be hash-swapped onto RC-REFREEZE-004.

Corrective-003 materially changed Resident-visible trusted-return/recovery semantics by removing local caller-manufacturable live-return trust and retaining external-verifier-plus-genuine-proof as the trust root. The current C15 operator/persistence line was built around the old local-trust behavior and therefore requires dedicated compatibility work against the frozen RC.

## Required downstream order

1. CORE-RC-REFREEZE-004
2. Fresh Independent Acceptance of the exact RC candidate
3. PM Integration of accepted freeze
4. Dedicated C15 operator/persistence compatibility corrective against the frozen RC
5. Fresh Independent Acceptance of that operator corrective
6. Fresh Resident A only after explicit PM release

Window 24 executes none of steps 2–6.

No Resident A/B/C, evaluator, public release/tag, or C15 repair is authorized here.
