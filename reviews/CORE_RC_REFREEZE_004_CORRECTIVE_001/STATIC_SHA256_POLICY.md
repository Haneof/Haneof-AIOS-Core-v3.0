# STATIC_SHA256_POLICY

The canonical Window 25 false-green reviewer probe is preserved byte-for-byte from technical review commit `ffa6475fe4dde4b5d06b09a629b059b89f1ff434`.

- repository blob: `c8a9050819440cc10605b08c943d29827f2b76c5`
- SHA-256: `fc7df49fdc80b340d2ddc065ad87c01c81987bef78f13fd6494ab035613796a9`

`SHA256SUMS` intentionally pins only this externally canonical frozen probe. Corrective helper scripts are candidate-owned and are pinned by the final candidate Git tree; runtime formal outputs receive `SHA256SUMS.runtime` inside Job A.

Preliminary head `04c37f7dd8ba6f20e1c67dad43c0f21087f51eeb` was byte-audited before finalization and is NON-FINAL because its copied reviewer probe was not byte-identical. No formal result from that preliminary head is acceptance evidence.
