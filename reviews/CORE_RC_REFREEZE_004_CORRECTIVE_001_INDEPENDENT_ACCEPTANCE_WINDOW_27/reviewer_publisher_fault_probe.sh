#!/usr/bin/env bash
set -euo pipefail
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cat > "$work/curl" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
: "${MOCK_RC:=0}"
if [ -z "${MOCK_CODE+x}" ]; then MOCK_CODE=201; fi
out=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-o" ]; then out="$2"; shift 2; continue; fi
  shift
done
if [ -n "$out" ]; then printf '%s\n' '{"message":"mock"}' > "$out"; fi
if [ "$MOCK_RC" -eq 0 ]; then printf '%s' "$MOCK_CODE"; fi
exit "$MOCK_RC"
MOCK
chmod +x "$work/curl"
run_case(){
  local label="$1" code="$2" crc="$3" expect="$4"
  set +e
  PATH="$work:$PATH" MOCK_CODE="$code" MOCK_RC="$crc" bash -c '
    set -euo pipefail
    body="$(mktemp)"; printf "%s\n" x > "$body"
    code="$(curl -sS -o "${body}.response" -w "%{http_code}" -X POST https://example.invalid --data @"$body")"
    echo "commit_comment_http_code=$code"
    if [ "$code" != "201" ]; then cat "${body}.response"; exit 1; fi
  ' >"$work/$label.out" 2>&1
  rc=$?
  set -e
  printf 'case=%s http=%s curl_rc=%s shell_rc=%s expected_rc_class=%s\n' "$label" "$code" "$crc" "$rc" "$expect"
  if [ "$expect" = success ]; then test "$rc" -eq 0; else test "$rc" -ne 0; fi
}
for c in 200 201 202 204 301 302 400 401 403 404 409 422 429 500; do
  if [ "$c" = 201 ]; then e=success; else e=failure; fi
  run_case http_$c "$c" 0 "$e"
done
run_case curl_transport_failure 000 6 failure
run_case empty_response '' 0 failure
run_case invalid_response abc 0 failure
echo 'PUBLISHER_FAULT_PROBE=PASS'
