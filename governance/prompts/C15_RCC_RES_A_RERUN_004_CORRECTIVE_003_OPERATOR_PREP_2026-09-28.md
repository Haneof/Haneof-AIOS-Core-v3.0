# C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Status:

`READY`

Role:

**Resident Launch / Test Infrastructure Operator**

You are not:
- Resident A;
- an evaluator;
- PM;
- Core implementation engineer;
- Resident B/C.

Your task:

> Prepare, test, freeze, and publish a clean-room Resident A launch environment and mechanical harness. Do not run the real C15 Resident and do not reveal any real C15 event.

## 1. Fresh control-plane read

Fresh-fetch live `main`.

Read:
- current task board/checkpoint;
- `governance/C15_RCC_RES_A_RERUN_004_CORRECTIVE_002_PRE_REVEAL_BLOCKED_ADJUDICATION_2026-09-28.md`;
- prior mechanical blocker adjudications as needed;
- frozen Core source/types as needed;
- `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_RUN_CONTRACT.md`;
- `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_CORRECTIVE_003_CLEAN_ROOM_CONTRACT.md`.

You may inspect historical mechanical failure evidence.
Do not open the sealed C15 fixture payload or evaluator expected semantics.

Confirm:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP = READY`

## 2. Frozen RC

Prepare against exact:

- software `f20f2edfa7af00d0286493fd15196ca9503bc315`
- Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`

No Core modifications are allowed.

## 3. Qualified environment

Produce a reproducible environment bootstrap for:

- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2 for prep tests

The bootstrap must be mechanical and Resident-safe.

It must contain no C15 semantics.

Prove it from a clean/synthetic location and record:
- Python;
- Pydantic;
- pytest;
- SQLite;
- OS/kernel/arch;
- `aios_core.__file__`.

If the environment cannot be reproducibly established, return `BLOCKED` and stop.

## 4. Mechanical harness

Build/fix a run-local harness package that contains only:
- request publisher;
- response publisher;
- exchange ledger;
- runner/runtime plumbing;
- verification utilities.

It must contain no semantic Resident callback.

No `resident_agent.py`-style semantic router is allowed.

## 5. Binding gate A — durable exchange

Test:
- request-id roundtrip;
- request/response SHA binding;
- atomic publication;
- fsync ordering;
- no partial consumption;
- monotonic/hash-chained ledger;
- fail-closed torn writes;
- pre/post request-publication dispatch boundary;
- durable recovery after response publication;
- ID/digest mismatch fail-closed.

## 6. Binding gate B — actual frozen Core contracts

Import the actual frozen Core types.

Test runner serialization of real:
- `RuntimeSnapshot`;
- successful `CapabilityResult`;
- failed `CapabilityResult`;
- multiple `CapabilityResult` entries.

Allowed fields are exactly:
- name;
- ok;
- data;
- error_code;
- error_message;
- call_id.

No nonexistent fields may be referenced.

## 7. Binding gate C — integrated two-round frozen runtime

Using a disposable synthetic World and test-only deterministic semantics:

- round 0 request;
- at least one legal synthetic capability call;
- actual frozen Core capability execution;
- round 1 request with non-empty capability history;
- successful publish/serialization;
- terminal response/silence.

No real C15 fixture content.

The deterministic callback used here must live only in test code and must be impossible to enable in real-run mode.

## 8. Binding gate D — no semantic script

Mechanically scan/inspect the real-run package and prove:
- no keyword-to-capability rules;
- no event-ID/cursor semantic rules;
- no prewritten Resident reply;
- no Claim/policy/goal generation logic;
- no real-run semantic callback.

Real-run response mode must be:

`EXTERNAL_CURRENT_RESIDENT_SESSION`

## 9. Freeze

After all gates pass under CPython 3.12.14:

freeze:
- environment bootstrap;
- runner;
- request/response publisher;
- ledger;
- schema;
- tests;
- gate raw outputs;
- environment record;
- SHA256SUMS;
- harness manifest.

Do not run a real Resident.

Do not init the real C15 release-state.

Do not reveal cursor 1.

## 10. Resident-safe launch packet

Generate:

`RESIDENT_SAFE_LAUNCH_PACKET.json`

It must contain only:
- task = `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003`;
- status = `PREP_REVIEW_READY` (not READY_FOR_RESIDENT yet);
- frozen software/Core/tests pins;
- CPython/Pydantic versions;
- bootstrap path/hash;
- harness root/hash manifest;
- gate A/B/C/D PASS evidence hashes;
- clean-room contract path/hash;
- safe Resident A run contract path/hash;
- cursor range 1..13;
- real response mode;
- explicit forbidden control-plane categories.

It must contain no historical Resident semantic content.

## 11. Deliverable

Create a new evidence-only operator-prep PR.

Pin:
- exact head/parent/tree;
- frozen RC;
- bootstrap hashes;
- harness hashes;
- gate evidence;
- launch packet hash.

Disposition:

`OPERATOR_PREP_COMPLETE / REVIEW_READY`

Then:

`READY_FOR_INDEPENDENT_ACCEPTANCE`

Do not self-accept.
Do not run Resident A.
Do not release persistence/B/C/evaluator.
