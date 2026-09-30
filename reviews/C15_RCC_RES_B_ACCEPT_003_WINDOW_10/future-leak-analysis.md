# Cursor 14–22 future/fixture leakage scan

## Method

Used the exact remote-authoritative run archive at generation 48. For each cursor 14–22, the probe maps `request_published` ledger timestamps to the interval after that cursor's unique `cursor_revealed` audit event and before the next cursor reveal. It then scans all matched request and response bytes, including serialized cockpit/RuntimeSnapshot/capability catalog/history, for the unrevealed events' exact:

- event IDs;
- `occurred_at` values;
- `resident_visible_payload` strings.

A separate weak-cue pass records generic `source_kind`, `source_class`, `dimension`, and `modality` matches for manual classification. It does not silently discard them or equate a common catalog vocabulary item with future event content.

## Request groups and event-specific result

| Revealed cursor | Requests in that exposure interval | Exact future ID/time/payload hits |
|---:|---|---:|
| 14 | req-0022..req-0026 | 0 |
| 15 | req-0027..req-0031 | 0 |
| 16 | none | 0 |
| 17 | req-0032..req-0036 | 0 |
| 18 | none | 0 |
| 19 | req-0037..req-0038 | 0 |
| 20 | req-0039..req-0042 | 0 |
| 21 | none | 0 |
| 22 | req-0043 | 0 |

This includes the key boundaries cursor 14 against 15–22, cursor 15 against 16–22, and cursor 20 against 21–22. No exact later payload, event identifier, or event timestamp was found in any scanned request or response before reveal.

Weak matches include generic terms such as `conversation`, `text`, and dimension names from the standing capability catalog. They are present as schema/tool vocabulary and not as the future event's unique content. The preserved JSON output records those matches with the explicit label `schema-or-source-cue; manual review`; no weak cue is promoted to a semantic leak finding.

## Limits / packet note

The W08 operator log records a resident-safe startup packet hash but the full packet bytes are not included in PR #302 or the authoritative generation tree. Therefore this independent scan establishes the contents of the exact captured exchange request/response/runtime snapshots and revealed-event evidence; it cannot independently re-hash/scan every out-of-band startup-packet byte. No specific packet leakage was observed, but a complete packet-content negative cannot be certified from this evidence set.

This limitation does not change the two blockers in `IA_REPORT.md`. In particular, absence of event-specific future cues does not prove who produced `req-0039`.

## Reproduction

```bash
python3 reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/probes/audit_probe.py \
  --run-root /tmp/ia-run \
  --output reviews/C15_RCC_RES_B_ACCEPT_003_WINDOW_10/raw/audit_probe_output.json
```

Frozen source SHA: `436dec9468e4a4120803d215c67d2bfc29a87ca789258c230a33176fc4ba0904`.
