# CORE-RC-REFREEZE-002 full regression

Frozen software SHA: `27a21db5b656d441248b9240020910b66a223830`  
Core tree: `a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6`  
Tests tree: `92fcbcc5876833735fb3cb7c73a98c4a8a4a3541`

## Formal CPython 3.12.14 gate

- Workflow: `core-rc-refreeze-002-formal-gate`
- Run: `36314420939` **SUCCESS** (2m55s)
- Job: `108606307712`
- Head at run: `91c93c4` (src/aios_core and tests identical to frozen software)
- Environment notice: `ENV 3.12.14 2.13.5 8.4.2`
- Step "Fresh full pytest -q": **SUCCESS** (exit 0)
- Step "Focused authenticity / recovery / headless / scale / writer": **SUCCESS**
- Durable comment: https://github.com/Haneof/Haneof-AIOS-Core-v3.0/pull/232#issuecomment-5855273999
- pytest progress reached `[100%]` with no failure annotation
- Historical Corrective-002 IA count on the **same Core tree** was `763 passed in 252.50s`. This freeze does **not** reuse that number as a substitute; it records a **fresh** 3.12.14 full-suite SUCCESS. Exact junit tests=/failures=/skipped=/time= is emitted by the freeze-candidate formal-gate (junitxml) on the packet SHA.

## Supporting p16 (setup-python "3.12", not pin 3.12.14)

- Run `36313973884` **SUCCESS** 3m19s
- Job `108605062773`
- Probe head `16bfdda` (comment-only workflow delta; Core/tests/pyproject ZERO DIFF vs frozen software)

## Prior historical count (not this freeze)

Corrective-002 IA `763 passed in 252.50s` is historical acceptance evidence, cited only as Core-tree continuity, not as this freeze's run.

## Local sandbox

CPython 3.11.2 present; **not** used for formal evidence (`requires-python = ">=3.12"`).
