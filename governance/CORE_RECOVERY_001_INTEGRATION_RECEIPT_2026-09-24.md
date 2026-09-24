# CORE-RECOVERY-001 Integration Receipt — 2026-09-24

Status: DONE
Task: CORE-RECOVERY-001

## Pins

- Construction main: `06b3a98fd3c098f861f49ab936500f81de030991`
- Tested implementation exact head: `58b6b5e2e653e258e778a0f2dd3d77978cd585ff`
- Evidence-only handoff: `f90b93608a13f9e04ff9b7997f2b4f92b5331f88`
- Engineering PR: #191
- Independent acceptance PR: #195
- Independent acceptance report: `reviews/CORE_RECOVERY_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
- Fresh probe PR: #194 — CLOSED / UNMERGED
- Probe head: `6e0dd3a0fbe4ca4842ad1723794b91f352c7afb3`
- Probe run: `36000803577`

## Accepted recovery surface

Independent acceptance returned `ACCEPTANCE_PASS / blocker=0`.

R1-R10 all PASS, including:
- real process SQLite/WAL crash boundaries;
- durable user-turn and background recovery;
- FIX-001 historical read cut under restart;
- index missing/stale/corrupt/interrupted rebuild from World;
- coherent SQLite online backup;
- separate-path restore preserving World/execution/attempt/metering state;
- future-schema pre-write fail-closed;
- interrupted migration marker safety;
- canonical writer-lease enforcement for recovery operations;
- truthful IN_DOUBT/reconciliation operational classification.

Fresh adversarial acceptance probes independently covered:
1. future-schema non-destructive refusal;
2. live-WAL backup/restore ledger equivalence;
3. interrupted index publication/rebuild;
4. recovery operation vs live canonical writer lease;
5. interrupted v0->v1 version publication;
6. fresh process-level WAL crash boundary.

No second World, recovery truth store, provider-attempt ledger, or blind provider retry path was introduced.

## Exact-head evidence

At exact implementation head `58b6b5e2...`:

- core-recovery run `35998900821` — SUCCESS
  - fault injection job `107630398418`: 12/12 PASS
  - installed clean restart job `107630398731`: SUCCESS
  - retained recovery regressions job `107630398704`: 193 pass markers
- full P16 run `35998900838`, job `107630397697` — SUCCESS
  - direct `pytest -q`
  - Python 3.12.14
  - pytest 8.4.2
  - pydantic 2.13.5
  - 687 pass markers / 0 failure-error markers / 100%
- core-headless `35998900833` — SUCCESS
- world-kernel `35998900847` — SUCCESS
- world-index `35998900841` — SUCCESS
- constitutional-cognition-closure `35998900832` — SUCCESS
- C14 scheduler/runtime `35998900826` — SUCCESS

Historical red run `35997231887` remains preserved and was independently reviewed; final acceptance did not rewrite it as green history.

## Integration

PM merged independent acceptance evidence first:
- PR #195 merge: `23b215c7735f099ee3c772f3322faf765c8f2eaa`.

Before candidate integration:
- PR #191 head remained exactly `f90b93608a13f9e04ff9b7997f2b4f92b5331f88`;
- implementation-to-handoff delta remained exactly one completion-evidence file;
- review-time main drift was governance/review only;
- after GitHub recomputation, PR #191 was `mergeable=true / mergeable_state=clean / rebaseable=true`.

PM merged PR #191 with expected-head pin:
- merge: `17e3807024359e990890ff4c249e55da93886475`.

## Honest post-merge note

At integration writeback time GitHub returned no automatic workflow runs for merge commit
`17e3807024359e990890ff4c249e55da93886475`.

No post-merge green run is claimed.
Authoritative evidence is the accepted exact-head recovery/compatibility/P16 gates, independent acceptance #195, and fresh probe #194.

## Release effect

`CORE-RECOVERY-001 = DONE`.

The next S2 task is:
`CORE-SCALE-001`.

RC-FREEZE remains blocked until SCALE is independently accepted and integrated.
Fresh Resident execution remains blocked until RC-FREEZE.
