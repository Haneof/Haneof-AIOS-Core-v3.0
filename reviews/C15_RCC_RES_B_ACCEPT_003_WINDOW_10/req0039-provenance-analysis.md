# req-0039 — Independent provenance and reconciliation analysis

**Run:** `c15-rcc-res-b-rerun-003-60997e04`  
**Cursor / round:** `20 / 0`  
**Request:** `req-0039-model_directive-ed097a32`  
**W09-F2:** `BLOCKER`  
**W09-F3:** `BLOCKER / NON_CANONICAL`

## Exact byte / chronology findings

| Evidence | Value |
|---|---|
| request-published | seq 115, `2026-09-29T20:06:29.156116Z` |
| request SHA-256 | `705f912fe30553a0022f4588262404fc46421557d089b5b813e2207e022518bb` |
| response-published | seq 116, `2026-09-29T20:37:01.219554Z` |
| response SHA-256 | `21a31eb306938b1c777f431cff9183e86c1233298344aebb0dcced3a78dd22c2` |
| response-consumed | seq 117, `2026-09-29T20:45:20.168905Z` |
| provider/model provenance | none; anonymous transport; `provenance=None`; trusted provider identity `UNKNOWN` |
| trusted-response receipts in sealed world | 0 |
| response envelope `authored_by` | `EXTERNAL_CURRENT_RESIDENT_SESSION` (self-asserted field; not process-authenticated) |
| decision | `read_periodic_review_anchors(limit=10)` |

The W08 operator evidence says the first invocation died while waiting for the exact request response; a second invocation failed closed at Core admission as `in_doubt` before the exchange handler could run. The exchange response was published after the first process death. The response bytes later consumed are byte-identical to the seq-116 bytes. No evidence binds those bytes to the assigned resident process/session; the process ID file only names the released resident process and is not a request/response invocation receipt.

The evidence says the operator **published** the response post-mortem. It does not conclusively establish whether the operator manually wrote/pasted the semantic payload or transported bytes genuinely produced by the assigned Resident outside the failed process. That ambiguity is precisely the blocker: the required claim (“the assigned Resident independently generated these exact bytes for this exact request”) is not supported. We do not assert as fact that a human authored it.

## Why later success does not recover authorship

The response is later consumed exactly once; the request/response files match their ledger hashes; the round-0 capability is a read. Those facts establish integrity and consumption, not authorship. The response's envelope `authored_by` field is unauthenticated. No model/provider identity is asserted, which is allowed by Release-003, but there is also no non-forgeable process linkage. The next round shows capability-result adaptation but cannot retroactively identify the producer of round 0.

## Reconciliation contradiction

The exact exchange contract defines `request_published` as semantic dispatch. Therefore at seq 115:

```text
semantic_dispatch_occurred = true
not_submitted_allowed = false
```

Generation 34 durably stores the attempt as `not_submitted`. Its `reconciliation_evidence` says that the request had crossed the exchange-side dispatch boundary and that `not_submitted` was chosen as the only retry-enabling implementation value. Audit record 211 records `in_doubt → not_submitted` under the “continue” directive. This is not merely an incomplete in-memory status: gen34 is sealed and remains part of the authoritative generation chain.

The later successful consumption and final attempt state `metered` are preserved; no redispatch or duplicate meter was found. They do not make the historical gen34 field accurate. The evidence pair makes the contradiction transparent, but transparency is not state truthfulness and does not authorize the contract-disallowed transition.

### Independent three-question ruling

- **IA-Q1:** Yes — false `not_submitted` violates durable historical truthfulness enough to make this run `NON_CANONICAL`.
- **IA-Q2:** No — `not_submitted` plus an evidence field that disproves it is not sufficient for admissible canonical evidence.
- **IA-Q3:** Yes — exactly-once effects cannot waive the independent semantic contract falsification.

“Continue” authorizes operations; it does not change the fact that `request_published` occurred. The PM readiness ruling is not evidence for either authorship or truthful state.

## Reproduction

From repo root after fetching exact PR/ref:

```bash
git fetch origin refs/pull/302/head:refs/review/pr-302
git fetch origin refs/heads/persistence/c15-rcc-res-b-rerun-003-60997e04:refs/review/persistence-c15-rcc-res-b-rerun-003
git archive refs/review/persistence-c15-rcc-res-b-rerun-003 | tar -x -C /tmp/ia-run
python3 reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/probes/lineage_recovery_world_probe.py \
  --run-root /tmp/ia-run \
  --fresh-a-root /tmp/ia-a/reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003/run \
  --operator-evidence /tmp/ia-operator-evidence.txt \
  --output reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/raw/lineage_recovery_world_probe_output.json
```

The source was frozen before the corrected run; SHA history and preserved pre-fix source are in `probes/` and `lineage-probe-change-log.txt`.
