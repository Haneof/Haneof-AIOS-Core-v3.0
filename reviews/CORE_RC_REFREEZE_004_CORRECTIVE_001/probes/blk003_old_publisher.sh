#!/usr/bin/env bash
set -uo pipefail
code="$1"
response="$(mktemp)"
printf '%s\n' '{"message":"simulated failure"}' > "$response"
echo "commit_comment_http_code=$code"
test "$code" = "201" || cat "$response"
