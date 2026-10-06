#!/usr/bin/env bash
# Shared fail-closed guard used verbatim by the formal workflow and its controls.
set -euo pipefail
if [ "$#" -ne 3 ]; then
  echo "usage: terminal_protected_drift_guard.sh INITIAL_MAIN TERMINAL_MAIN OUTPUT_FILE" >&2
  exit 64
fi
initial_main="$1"
terminal_main="$2"
output_file="$3"
protected_path_ere='^(src/|tests/|\.github/workflows/|pyproject\.toml$|setup\.py$|setup\.cfg$|setup/|MANIFEST(\.in)?$|requirements([^/]*)(/.*)?$|Pipfile(\.lock)?$|poetry\.lock$|uv\.lock$|tox\.ini$|conda[^/]*\.ya?ml$|environment[^/]*\.ya?ml$)'

git diff --no-renames --name-status "$initial_main" "$terminal_main" | tee "$output_file"
paths="$(git diff --no-renames --name-only "$initial_main" "$terminal_main")"
if printf '%s\n' "$paths" | grep -Eq "$protected_path_ere"; then
  echo "TERMINAL_UNADJUDICATED_PROTECTED_DRIFT=FAIL"
  exit 1
fi
echo "TERMINAL_PROTECTED_DRIFT=PASS"
