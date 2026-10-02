# BASELINE_RED

Formal RED-first run materialized exact failed candidate `5ad0524c425592210ff184e00ad52abb2c14e366` and byte-frozen probes from canonical review `84457badc562416f59fb25ca41103700276e0df2`.

Formal environment:
- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2
- SQLite 3.45.1
- OpenSSL 3.0.13

Fresh reproduced historical product RED:
- IA14-ORACLE-001 — RED
- IA14-NONCE-001 — RED
- IA14-NS-001 — RED
- original S3 / IA14-ROTATE-001 family — RED with `failures=2`

Control probes:
- IA14-ID-001 PASS
- IA14-JSON-001 PASS
- IA14-RACE-001 PASS
- IA14-SIGKILL-001 PASS
- supplementary S1/S2 PASS

The original S3 remains immutable historical RED. Corrective Route B does not rewrite that historical expectation into a green test.
