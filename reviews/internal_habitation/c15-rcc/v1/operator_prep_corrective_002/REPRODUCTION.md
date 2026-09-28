# Mechanical reproduction (non-Resident only)

Use a new empty AIOS_RUNTIME_ROOT and AIOS_REPO_ROOT pointing to the exact candidate.
Build with `bash <P>/bootstrap/bootstrap_runtime.sh --build`; use its qualified
runtime/3.12.14/venv/bin/python for every binding test. Verify with --verify both
with explicit AIOS_REPO_ROOT and with that variable unset from outside the checkout.

Set PYTHONDONTWRITEBYTECODE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1,
PYTHONPATH=<P>/harness:<repo>/src, C002_REPO=<repo>, C002_PACKAGE=<P>,
C002_RUNTIME=<new-runtime>, C002_RAW=<new-output-directory>.

1. In Q/probes_v2: `sha256sum -c PROBE_SHA256SUMS.v2`.
2. Qualified Python `-m pytest --collect-only -q -p no:cacheprovider -o addopts=
   --rootdir=<Q>/probes_v2 <Q>/probes_v2/tests`.
3. Qualified Python `-m pytest -vv -p no:cacheprovider -o addopts=
   --rootdir=<Q>/probes_v2 --junitxml=<output>/results.xml <Q>/probes_v2/tests`.
4. Qualified Python `<Corrective-001>/probes/corrective_probes_v6.py
   --candidate-root <P> --core-source <repo>/src/aios_core/runtime/turn_runtime.py
   --output <output>/c1_c3.json`.
5. Qualified Python `<P>/harness/operator_tools/gate_runner.py --repo-root <repo>
   --harness-root <P>/harness --evidence-dir <output>`.
6. Qualified Python `<P>/harness/operator_tools/packet_audit.py
   --operator-prep-root <P> --repo-root <repo>
   --packet <P>/RESIDENT_SAFE_LAUNCH_PACKET.json`.

P = reviews/internal_habitation/c15-rcc/v1/operator_prep/
C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP
Q = reviews/internal_habitation/c15-rcc/v1/operator_prep_corrective_002
Corrective-001 = reviews/internal_habitation/c15-rcc/v1/operator_prep_corrective_001

Do not write over frozen evidence during reproduction; use a disposable checkout
and new output paths. All Worlds/responders in these tests are synthetic. These
commands do not authorize real Resident execution.
