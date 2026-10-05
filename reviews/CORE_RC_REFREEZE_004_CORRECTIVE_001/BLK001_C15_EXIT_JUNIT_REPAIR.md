# BLK001_C15_EXIT_JUNIT_REPAIR

The authoritative classifier is pytest exit semantics plus JUnit XML.
- only rc 0/1 admitted;
- rc 2/3/4/5/unknown fail;
- JUnit must exist, be non-empty and parse;
- rc 0 requires no structured failure/error;
- rc 1 requires at least one structured failed/error testcase;
- every rc 1 failed/error testcase must map to tests/c15_persistence/**;
- any non-downstream structured failure is ACCEPTED_CORE_REGRESSION_EXPOSED_BY_C15 and fails;
- console FAILED parsing is not authoritative.

Ten regression cases are frozen in probes/c15_junit_classifier.py. No C15 implementation was changed.
