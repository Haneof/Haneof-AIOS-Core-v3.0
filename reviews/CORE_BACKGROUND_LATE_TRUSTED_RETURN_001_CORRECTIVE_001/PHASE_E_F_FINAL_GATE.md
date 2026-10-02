# PHASE_E_F_FINAL_GATE

Task: `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001`

Final test-only closure adds no production behavior.

## Phase E

A real child process runs the actual `FusedTurnRuntime`, receives only the public
RSA verifier and public dispatch context, then is killed with `SIGKILL` at the
provider boundary. Only after exit code `-SIGKILL` is observed does the surviving
external side sign the exact provider return. A fresh Core process must:

- verify against the verifier pinned before dispatch;
- attach one exact response to the same attempt/round;
- perform zero provider redispatch;
- create one meter, one semantic application/output and one completion;
- persist verifier consumption;
- treat a second turn invocation as terminal/already completed.

## Phase F

The formal workflow runs:

1. all Corrective-001 Route-B / CA1-CA5 / secret-separation / consumption probes;
2. accepted trusted-return R1-R5, adversarial, response-recovery, process-loss,
   FIX-002 and turn-execution regressions;
3. complete Core test domains under CPython 3.12.14:
   `tests/unit`, `tests/integration`, `tests/runtime`, `tests/habitation`.

The C15 persistence and C15 preflight harness directories are not Core product
implementation and are not part of this Core release gate, per
`governance/C15_RCC_RES_B_PERSISTENCE_SCOPE_ADJUDICATION_2026-09-28.md`.
They are not modified by this corrective.
