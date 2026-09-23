# Structured transport protocol v1

A request contains `protocol`, `request_id`, `kind`, and `input`.
The authorized interface supplies the current request. Echo its exact
`request_id` in one newline-terminated JSON response with an `output` field.

For `kind: runtime`, output is exactly one of:

- `{"response": "<your visible response>"}`
- `{"silence": true}`
- `{"capability_calls": [{"name": "<catalog name>", "arguments": {}, "call_id": "<optional id>"}]}`

For `kind: round_summary` or `kind: dimension_summary`, output is
`{"text": "<your summary>"}`. The request supplies the current typed input.

Only observable structured outputs are requested; do not submit hidden reasoning.
No filesystem path, shell command, provider credential or model identity field is
part of this protocol. Capabilities and their arguments come from the current
Runtime catalog, not from this document. Missing or malformed responses stop the
transport; they do not mean silence. A response must belong to the current request.
