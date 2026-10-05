#!/usr/bin/env bash
set -euo pipefail
code="$1"
response="$(mktemp)"
printf '%s\n' '{"message":"simulated response"}' > "$response"
echo "commit_comment_http_code=$code"
if [ "$code" != "201" ]; then
  cat "$response"
  rm -f "$response"
  exit 1
fi
rm -f "$response"
exit 0
