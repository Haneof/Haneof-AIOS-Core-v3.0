# Evidence identity and finalization method

1. Initial carry + v1 freeze: 4b7afc6f5bff1deb7407eb2f1470a3b68c0aa79a,
   sole parent task-start live main b7c9e85014806637f7a01c8fd6695bc9f57672ba.
2. Preserve v1 RED and freeze v2: 95d9da9d6d75b7f563afe42d88a14b07e86911c1.
   Only scanner core_source argument corrected; no expectation changes.
3. Genuine v2 H2 RED committed: 8e34fba00edf4fdb5b80f04d7a648f6b5bb8c40e.
   137 carried hashes rechecked before any implementation repair.
4. Corrected candidate H1 freezes the code and provisional mechanical packet.
   Final candidate-tier tests identify H1 + its tree + the unchanged code manifest.
5. Final packet pins candidate-tier evidence. A separate final-audit tier reruns
   unchanged frozen probes against the final packet and verifies its exact SHA.
   That audit is outside the packet's pin graph to avoid a self-hash cycle.
6. Final freeze H2 is evidence/packet-only and has sole parent H1. Its SHA/tree
   are reported in the PR, not recursively embedded inside their own content.

Do not claim tests executed on final commit H2 before that commit existed. All
covered source files must be unchanged before/after both evidence tiers. Checksums
cover final audit/packet/freeze evidence but exclude themselves.

Whole-record ledger tail deletion remains indistinguishable from a valid prefix
without an external head anchor; no new anchor is added and no stronger detection
claim is made. Operational validation does reject interior damage/duplicate events.

Historical bootstrap's source tree is an H2 archive with copied Git metadata (HEAD
is not H2). Source identity is independently verified against exact Git blobs and
CARRY_FORWARD_IDENTITY.json, not inferred from that scratch metadata HEAD.
