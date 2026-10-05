# RED_FIRST

Before workflow repair, all three blockers were freshly reproduced against 70134269ddfc7c80c4a703a933253bd099746504.

BLK-001: canonical reviewer probe SHA-256 matched fc7df49fdc80b340d2ddc065ad87c01c81987bef78f13fd6494ab035613796a9. Pytest exit 4 with no FAILED line was laundered to the two downstream-debt acceptance markers and process exit 0.

BLK-002: old workflow had contents:write, default checkout credential persistence, candidate-controlled execution in the same write-capable job, only one pre-test remote-head check, and no terminal remote/frozen/tracked-mutation check. This proves an admitted false-green authority path, not that a historical malicious push occurred.

BLK-003: exact old set -uo pipefail plus test "$code" = "201" || cat response returned exit 0 for simulated 401/403/500.

See raw/ and probes/.
