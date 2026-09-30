# Reproduction guide — Window 10 independent acceptance probes

All commands are read-only with respect to PR #302 and the authoritative persistence ref. Git fetches write only local review refs. The two SQLite databases used by probes are opened URI `mode=ro`; corruption detection flips a byte only in a temporary copy.

## 1. Fresh exact refs

```bash
git fetch --all --prune
git fetch origin refs/pull/302/head:refs/review/pr-302
git fetch origin refs/pull/296/head:refs/review/pr-296
git fetch origin refs/pull/303/head:refs/review/pr-303
git fetch origin refs/heads/persistence/c15-rcc-res-b-rerun-003-60997e04:refs/review/persistence-c15-rcc-res-b-rerun-003

gh pr view 302 --json number,state,isDraft,headRefName,headRefOid,baseRefName,mergedAt,url
gh pr view 296 --json number,state,headRefName,headRefOid,baseRefName,mergedAt,url
gh pr view 303 --json number,state,headRefName,headRefOid,baseRefName,mergedAt,url
git ls-remote origin refs/heads/main refs/heads/persistence/c15-rcc-res-b-rerun-003-60997e04
```

Expected exact PR #302 SHA/tree/parent/base and persistence identities are recorded in `IA_REPORT.md`. Do not substitute a new candidate head.

## 2. Read-only materialization

```bash
mkdir -p /tmp/ia-run /tmp/ia-a
git archive refs/review/persistence-c15-rcc-res-b-rerun-003 | tar -x -C /tmp/ia-run
git archive refs/review/pr-296 | tar -x -C /tmp/ia-a
```

Fresh A run root:

```text
/tmp/ia-a/reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003/run
```

Create the exact W08 operator-evidence input from the pinned PR head if needed:

```bash
git show refs/review/pr-302:evidence/w08/OPERATOR_LOG.md > /tmp/W08_OPERATOR_LOG.md
git show refs/review/pr-302:evidence/w08/evidence-incident-reconciliation.md > /tmp/W08_incident_reconciliation.md
cat /tmp/W08_OPERATOR_LOG.md /tmp/W08_incident_reconciliation.md > /tmp/ia-operator-evidence.txt
```

## 3. Frozen adversarial probe sources

Verify the source hashes before execution:

```bash
sha256sum -c reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/probe-source-final.sha256
sha256sum -c reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/probes/lineage_recovery_world_probe.final.sha256
sha256sum -c reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/probes/exchange_semantics_probe.sha256
sha256sum -c reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/probes/identity_scan_probe.sha256
```

Run the generation/artifact/ledger/terminal/future-cue/authorship scan:

```bash
python3 reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/probes/audit_probe.py \
  --run-root /tmp/ia-run \
  --output reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/raw/audit_probe_output.json
```

Run Fresh A→B lineage, SQLite logical-row comparison, exact fingerprint-based request↔attempt↔meter mapping, synthetic corruption detection, generation-34 reconciliation and World duplicate/wake checks:

```bash
python3 reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/probes/lineage_recovery_world_probe.py \
  --run-root /tmp/ia-run \
  --fresh-a-root /tmp/ia-a/reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003/run \
  --operator-evidence /tmp/ia-operator-evidence.txt \
  --output reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/raw/lineage_recovery_world_probe_output.json
```

Run the persistence run/session identity scan (only the exact RERUN-003 identity pair should be present; RERUN-002 must be absent):

```bash
python3 reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/probes/identity_scan_probe.py \
  --run-root /tmp/ia-run \
  --output reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/raw/identity_scan_probe_output.json
```

Frozen identity probe SHA: `c5f3cbeacc858f453d93d9d0bf0fffa957e46b69813bd3c05eb581a246686a37`.

Run exact A-response byte comparison, B response uniqueness/replay scan, provenance summary, and per-round capability-result adaptation review:

```bash
python3 reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/probes/exchange_semantics_probe.py \
  --run-root /tmp/ia-run \
  --fresh-a-root /tmp/ia-a/reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003/run \
  --output reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/raw/exchange_semantics_probe_output.json
```

The current frozen outputs are preserved in `raw/`. Earlier pre-fix outputs and old probe source snapshots remain for transparency; final findings use the corrected, re-frozen probe hashes listed above and in `probe-source-change-log.txt` / `probes/lineage-probe-change-log.txt`.

## 4. Additional direct checks

```bash
# Verify the ten sealed freeze files from their pinned digest list.
(cd /tmp/ia-run/evidence/freeze && sha256sum -c digests.sha256)

# Inspect the exact req-0039 ledger triplet and bytes without mutation.
grep 'req-0039-model_directive-ed097a32' /tmp/ia-run/exchange/ledger.jsonl
sha256sum /tmp/ia-run/exchange/requests/req-0039-model_directive-ed097a32.json \
          /tmp/ia-run/exchange/responses/req-0039-model_directive-ed097a32.json

# Recheck the c19 recovery parent/history on the read-only fetched ref.
git show -s --format='%H %P %s' 4f12ee0edaceef637dd879d829763133fc4087a2
git rev-list --count refs/review/persistence-c15-rcc-res-b-rerun-003
```

## 5. Runtime disclosure

The probes use only the Python standard library on the reviewer sandbox (CPython 3.11.2, SQLite 3.40.1, OpenSSL 3.0.20; no installed Pydantic/pytest). The formal run runtime remains the frozen CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1 / OpenSSL 3.0.13. No runtime tests were represented as having run in the formal environment.
