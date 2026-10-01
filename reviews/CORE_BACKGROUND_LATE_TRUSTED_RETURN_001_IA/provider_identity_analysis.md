# Provider-identity ambiguity analysis (§15) — WINDOW 14

Candidate `5ad0524c425592210ff184e00ad52abb2c14e366`.

## Helper under test

`provider_identity(directive)` (`src/aios_core/runtime/background_attempt.py:398-419`)
starts from `directive.provenance` and lets any **non-null** `directive.usage` field
override. Naively this looks like a two-source canonicalization with silent override —
the exact ambiguity class §15 targets.

## Why it is mechanically closed

`ModelDirective.__post_init__` (`src/aios_core/runtime/cognitive_runtime.py:94-104`)
rejects construction whenever usage and provenance both carry a field and disagree:

```python
if usage_value is not None and usage_value != provenance_value:
    raise ValueError(f"usage {field_name} conflicts with model-call provenance")
```

So "override" can only ever *fill* a missing side, never *replace* a conflicting one.
The same rule is enforced on the decode path (`decode_model_directive`,
`background_attempt.py:125-224`: exact field sets, non-blank identity strings,
duplicate-key rejection) before any `ModelDirective` is built.

## Matrix ID-A … ID-E (frozen `IA14-ID-001` + construction probes)

| ID | construction | result | verdict |
|---|---|---|---|
| ID-A `provenance.provider != usage.provider` | refused at `ModelDirective()` | `ValueError: usage provider conflicts with model-call provenance` | fail closed ✓ |
| ID-B `provenance.model != usage.model` | refused at construction (same rule) | ValueError | fail closed ✓ |
| ID-C `provenance.request_id != usage.request_id` | refused at construction (same rule) | ValueError | fail closed ✓ |
| ID-D partial provenance + partial usage | allowed only when non-null sides agree; null side fills | single unambiguous canonical triple | deterministic ✓ |
| ID-E one field anonymous, other source fills | usage field None → provenance value used; all-null side → identity `None` | late attach **requires** all three (`attach_late_trusted_return`, `:1806-1813`) and refuses anonymous returns (`ValueError: … full provider/model/request_id identity`) | fail closed ✓ |

Blank/empty identities are rejected (`ModelCallProvenance.__post_init__` non-blank;
`ModelUsage` "provider must be non-blank when provided"; decoder rejects blank).
Bool-as-int in identity fields cannot occur (identity fields are strings).

## Binding of identity to the proof

The MAC message (`late_return_message`, `late_return.py:96-128`) includes
`provider`, `model`, `provider_request_id` alongside `response_fingerprint` and
`payload_sha256`; `stage_exact_response` additionally requires the caller-supplied
identity to equal the directive's own identity (`:2270-2285`) and the receipt to
bind the same identity (`_verify_response_authenticity`, `:2404-2470`). Any identity
change after proof minting invalidates the proof.

## Verdict

No exploitable provider-identity ambiguity; no silent canonicalization of conflicting
sources. The dual-source rule is mechanical, uniform across encode/decode/prove/attach,
and conflicts fail at construction. **PASS** (ID-A…ID-E).
