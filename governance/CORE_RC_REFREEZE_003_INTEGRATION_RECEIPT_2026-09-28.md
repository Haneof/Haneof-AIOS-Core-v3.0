# CORE-RC-REFREEZE-003 Integration Receipt — 2026-09-28

Status: **DONE / ACCEPTED / INTEGRATED**

Task:
`CORE-RC-REFREEZE-003`

Candidate PR:
#269

PM verdict:
`PM_ACCEPTED / INTEGRATED`

## 1. Exact identities

| Identity | Value |
|---|---|
| Frozen software | `f20f2edfa7af00d0286493fd15196ca9503bc315` |
| Frozen repository tree | `1ac3a675b884167d3a29aa432e7ef3eaff94d404` |
| Frozen Core tree (`src/aios_core`) | `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623` |
| Frozen tests tree | `7e33b5ef8432370234965d3ccd61248c703c4019` |
| Frozen workflows tree | `fb168f8540070ff7b0c521e5990b03c7f3c56bf4` |
| `pyproject.toml` blob | `b38833c7537fa60d5c2f02ed4bb19158d8995a11` |
| `pyproject.toml` SHA-256 | `993a6e9dd821d8d5885f4cc1f2da0aa34d40284618097a1de507e885f2eaab30` |
| Source manifest SHA-256 | `837bba36ef5ff84640e66a662a213f3c4f763f2412b94495e8c9bec35c3ddf84` |
| Accepted RC candidate | `6f95431036dd0304947d67ec4a8de7229d1d3ba9` |
| Candidate first parent | `f2ef4886cbd7253543e82debbaa14ea387417f03` |
| Candidate tree | `a43a761ac3570dfc4aab296818310068f877e881` |
| Candidate exact-head gate | run `36437699641` — SUCCESS |
| Independent review PR | #271 — review-only / draft / do not merge |
| Independent review exact | `6eaf91822c39398c610a80c6985d28b4cab48eed` |
| Independent verdict | `ACCEPTANCE_PASS / blocker=0` |
| RC candidate merge | `79ee5161491fb6a9215700f6391281083661b8ca` |

The software frozen by this RC is `f20f2edf...`.
The PR #269 candidate and its merge commit are evidence/release-packet integration identities, not a replacement software baseline.

## 2. Independent Acceptance

Fresh Independent Acceptance was executed by a separate reviewer and durably published in PR #271.

Verified independently:

- exact candidate head remained `6f954310...`;
- zero Core/test/package implementation drift;
- merge-ref equivalence proven;
- RC checksums 23/23 independently recomputed and matched;
- full repository regression: 919 passed / 0 failed;
- trusted-return/recovery focused suite: 248 passed / 0 failed;
- Core systems focused suite: 356 passed / 0 failed;
- runtime registry: 43 total / 22 side-effecting;
- all 22 side-effecting replay scenarios converged exactly once;
- 21-mutation authenticity tamper matrix failed closed;
- real POSIX SIGKILL recovery probe passed without duplicate provider dispatch, meter, operation or semantic effect;
- clean wheel/non-editable install and headless lifecycle passed;
- backup/restore/index rebuild and writer/restart probes passed;
- open-PR contamination review found no imported competing implementation.

Reviewer disposition:

`READY_FOR_PM_INTEGRATION`

PR #271 remains review-only / unmerged.

## 3. Post-merge equivalence

PM merged only exact candidate:

`6f95431036dd0304947d67ec4a8de7229d1d3ba9`

as:

`79ee5161491fb6a9215700f6391281083661b8ca`

PM then compared accepted candidate to post-merge main.

Observed differences are only the already-integrated PM governance/IA dispatch files:

- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `governance/CORE_RC_REFREEZE_003_PM_REVIEW_READY_2026-09-28.md`
- `governance/prompts/CORE_RC_REFREEZE_003_INDEPENDENT_ACCEPTANCE_2026-09-28.md`

Therefore:

- `src/**` post-acceptance drift = ZERO;
- `tests/**` post-acceptance drift = ZERO;
- package implementation drift = ZERO.

The accepted RC evidence packet is integrated without altering the frozen software semantics.

## 4. Formal environment

Formal RC gate:

- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2
- SQLite 3.45.1
- Ubuntu 24.04.5 LTS
- x86_64

The review sandbox itself used CPython 3.11.2 for its local independent reruns, while the exact candidate's hosted formal gate `36437699641` supplied the required CPython 3.12.14 environment evidence. The independent reviewer explicitly adjudicated that split as non-blocking.

## 5. RC impact

Binding disposition:

`FRESH_A_REQUIRED`

Therefore:

- prior `C15-RCC-RES-A-RERUN-003` remains immutable historical evidence;
- A-003 = `HISTORICAL_FOR_PRIOR_RC_ONLY`;
- A-003 must not be hash-swapped or semantically reused as evidence for RC-003;
- the next Resident lineage must start from a fresh private World/index/release-state/session/process on frozen software `f20f2edf...`;
- the next task is `C15-RCC-RES-A-RERUN-004`.

## 6. Known limitations preserved

This integration does not upgrade any unproven claim.

Still preserved:

- in-process trusted code with direct trusted store/runtime access remains inside the HMAC trust root;
- no distributed multi-host HA claim;
- no public UI/hardware performance claim;
- SCALE evidence does not imply hardware/wearable performance;
- provider/token cost remains UNKNOWN where not measured;
- C15 is not complete;
- persona/identity continuity governance #263 remains a separate unmerged draft until independently accepted.

## 7. Downstream control state

After this integration receipt is merged:

- `CORE-RC-REFREEZE-003 = DONE / ACCEPTED / INTEGRATED`
- `C15-RCC-RES-A-RERUN-004 = READY`
- `C15-RCC-RES-A-RERUN-004-INDEPENDENT-ACCEPTANCE = BLOCKED`
- persistence Corrective-003 resume = BLOCKED
- Resident B = BLOCKED
- Resident C = BLOCKED
- final C15 evaluator/close = BLOCKED

No Resident is executed in this PM integration window.
