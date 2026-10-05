#!/usr/bin/env python3
"""Corrective-002 publisher/seal identity fault matrix.

This executes the *exact bytes* of the two write-capable job scripts extracted
from `.github/workflows/core-rc-refreeze-004-formal-gate.yml` against a
fault-injecting `curl` shim. It is not a re-implementation of the logic: the
extracted scripts are the same text the hosted runner executes, so every case
below is a mechanical statement about the shipped publication logic.

Covered:
  * fresh canonical-ref equality pre-publish, post-publish, pre-hold,
    post-hold and post-seal;
  * canonical-ref query transport failure, HTTP failure and malformed payload;
  * the full HTTP response matrix for commit-comment creation (201 only);
  * commit-comment PATCH matrix for the identity seal (200 only);
  * post-publish drift -> published provisional pin invalidated, job fails;
  * post-seal drift -> sealed pin invalidated, job fails;
  * publisher-result validation in the seal job (sha / run / provisional);
  * the happy path leaving a pin in IDENTITY_SEALED with all five identity
    phases recorded.

Nothing here is write-capable: the shim never talks to GitHub.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

BEGIN = "# >>> RC004_WHOLE_RUN_IDENTITY_CORE_BEGIN"
END = "# <<< RC004_WHOLE_RUN_IDENTITY_CORE_END"
JOB_PUBLISHER = "  rc004-mandatory-pin-publisher:"
JOB_SEAL = "  rc004-whole-run-identity-seal:"

SHA_A = "2380121639865b1bd29176cf944f5a20afe4112d"
SHA_B = "e4fd46c04c8ad982fa1fa274546dbf0d099343c5"

CURL_SHIM = r"""#!/usr/bin/env bash
# fault-injecting curl shim used only by the local fault matrix
out=""; url=""; method="GET"; has_w=0; data=""
args=("$@"); i=0
while [ "$i" -lt "${#args[@]}" ]; do
  a="${args[$i]}"
  case "$a" in
    -o|-X|-w|--data|-H|--max-time) i=$((i+1))
      case "$a" in
        -o) out="${args[$i]}";;
        -X) method="${args[$i]}";;
        -w) has_w=1;;
        --data) data="${args[$i]}";;
      esac
      ;;
    http*) url="$a";;
    *) ;;
  esac
  i=$((i+1))
done
if [ -n "${FAKE_CALL_LOG:-}" ]; then
  n=$(wc -l < "$FAKE_CALL_LOG" 2>/dev/null || echo 0)
  printf 'call=%s method=%s url=%s data=%s out=%s\n' "$n" "$method" "$url" "$data" "$out" >> "$FAKE_CALL_LOG"
  if [ -n "$data" ] && [ -f "$data" ]; then cp "$data" "$FAKE_CALL_LOG.data.$n"; fi
fi
if [ "$has_w" = "1" ]; then
  if [ "${FAKE_CODE_TRANSPORT_FAIL:-0}" = "1" ]; then
    echo "curl: (7) Failed to connect to api.github.com port 443: Connection refused" >&2
    exit 7
  fi
  printf '%s' "${FAKE_RESPONSE_BODY:-}" > "$out"
  printf '%s' "${FAKE_CODE:-000}"
  exit 0
fi
if [ "${FAKE_GET_TRANSPORT_FAIL:-0}" = "1" ]; then
  echo "curl: (7) Failed to connect to api.github.com port 443: Connection refused" >&2
  exit 7
fi
if [ "${FAKE_GET_HTTP_FAIL:-0}" = "1" ]; then
  echo "curl: (22) The requested URL returned error: 404" >&2
  exit 22
fi
case "$url" in
  */git/ref/*)
    sha="${FAKE_REF_SHA:-}"
    if [ -n "${FAKE_GET_QUEUE:-}" ] && [ -s "${FAKE_GET_QUEUE:-/dev/null}" ]; then
      sha="$(head -1 "$FAKE_GET_QUEUE")"
      tail -n +2 "$FAKE_GET_QUEUE" > "$FAKE_GET_QUEUE.tmp" && mv "$FAKE_GET_QUEUE.tmp" "$FAKE_GET_QUEUE"
    fi
    if [ "$sha" = "MISSING_FIELD" ]; then printf '{"object":{}}'; exit 0; fi
    printf '{"object":{"sha":"%s"}}' "$sha"
    exit 0
    ;;
  */comments/*)
    if [ -n "${FAKE_PIN_BODY_FILE:-}" ] && [ -f "$FAKE_PIN_BODY_FILE" ]; then
      jq -Rs '{body:.}' < "$FAKE_PIN_BODY_FILE"
    else
      printf '{"body":""}'
    fi
    exit 0
    ;;
esac
printf '{}'
exit 0
"""


SLEEP_SHIM = r"""#!/usr/bin/env bash
# instrumented no-op replacement for the bounded settle hold
if [ -n "${FAKE_CALL_LOG:-}" ]; then echo "sleep_args=$*" >> "$FAKE_CALL_LOG.hold"; fi
exit 0
"""


def extract_script(workflow: str, start: str, stop: str | None) -> str:
    lines = workflow.splitlines()
    begin = next(i for i, line in enumerate(lines) if line.startswith(start))
    run_at = next(
        i
        for i in range(begin, len(lines))
        if lines[i].strip() == "run: |" and lines[i].startswith("        run: |")
    )
    body: list[str] = []
    for line in lines[run_at + 1 :]:
        if line.strip() and not line.startswith("          "):
            break
        body.append(line[10:] if line.startswith("          ") else "")
    return "\n".join(body) + "\n"


def run_script(
    script_path: Path,
    tmp: Path,
    env_over: dict[str, str],
    pin_body: str | None = None,
) -> subprocess.CompletedProcess[str]:
    runner_temp = tmp / "runner-temp"
    runner_temp.mkdir(parents=True, exist_ok=True)
    queue = tmp / "get-queue"
    if "FAKE_GET_QUEUE" in env_over:
        queue.write_text("\n".join(env_over.pop("FAKE_GET_QUEUE").split(",")) + "\n", encoding="utf-8")
        env_over["FAKE_GET_QUEUE"] = str(queue)
    pin_file = tmp / "pin-body.md"
    if pin_body is not None:
        pin_file.write_text(pin_body, encoding="utf-8")
        env_over["FAKE_PIN_BODY_FILE"] = str(pin_file)
    env = {
        "PATH": f"{tmp / 'bin'}:{os.environ['PATH']}",
        "HOME": str(tmp),
        "GITHUB_REPOSITORY": "Haneof/Haneof-AIOS-Core-v3.0",
        "GITHUB_SHA": SHA_A,
        "GITHUB_RUN_ID": "99999999999",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKFLOW": "core-rc-refreeze-004-formal-gate",
        "CANONICAL_CORRECTIVE_BRANCH": "release/core-rc-refreeze-004-corrective-002-window28",
        "FROZEN_SHA": "1cee3c5ad12f4b9098232bae11b51df786c5eb2f",
        "RC004_TASK_NAME": "CORE-RC-REFREEZE-004-CORRECTIVE-002",
        "GATE_RESULT": "success",
        "GH_TOKEN": "fault-matrix-token",
        "RUNNER_TEMP": str(runner_temp),
        "GITHUB_OUTPUT": str(tmp / "github-output.txt"),
        "GITHUB_STEP_SUMMARY": str(tmp / "step-summary.md"),
        "FAKE_CALL_LOG": str(tmp / "calls.log"),
        "FAKE_REF_SHA": SHA_A,
        "FAKE_CODE": "201",
        "FAKE_RESPONSE_BODY": '{"id":424242,"body":"published"}',
    }
    env.update(env_over)
    proc = subprocess.run(
        ["bash", str(script_path)],
        capture_output=True,
        text=True,
        env=env,
    )
    proc.env_used = env  # type: ignore[attr-defined]
    return proc


def main() -> int:
    workflow = Path(sys.argv[1]).read_text(encoding="utf-8")
    publisher_script = extract_script(workflow, JOB_PUBLISHER, JOB_SEAL)
    seal_script = extract_script(workflow, JOB_SEAL, None)
    cores = []
    for part in workflow.split(BEGIN)[1:]:
        cores.append(part[: part.index(END)].strip())

    failures: list[str] = []
    cases = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal cases
        cases += 1
        status = "PASS" if ok else "FAIL"
        print(f"case={name} {status}{(' ' + detail) if detail else ''}")
        if not ok:
            failures.append(name)

    check("identity_core_extracted_twice_identical", len(cores) == 2 and cores[0] == cores[1])
    check("publisher_script_extracted", "commit_comment_http_code" in publisher_script)
    check("seal_script_extracted", "IDENTITY_SEALED" in seal_script)
    if failures:
        print("PUBLISHER_IDENTITY_FAULT_MATRIX=FAIL")
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="rc004-fault-matrix-"))
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "curl"
    shim.write_text(CURL_SHIM, encoding="utf-8")
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
    sleep_shim = bin_dir / "sleep"
    sleep_shim.write_text(SLEEP_SHIM, encoding="utf-8")
    sleep_shim.chmod(sleep_shim.stat().st_mode | stat.S_IEXEC)
    pub = tmp / "publisher.sh"
    pub.write_text(publisher_script, encoding="utf-8")
    seal = tmp / "seal.sh"
    seal.write_text(seal_script, encoding="utf-8")
    if shutil.which("jq") is None:
        print("JQ_UNAVAILABLE")
        return 1

    def fresh() -> Path:
        d = Path(tempfile.mkdtemp(prefix="run-", dir=tmp))
        (d / "bin").symlink_to(bin_dir, target_is_directory=True)
        return d

    def log_lines(d: Path) -> list[str]:
        f = d / "calls.log"
        return f.read_text(encoding="utf-8").splitlines() if f.exists() else []

    def mutating_calls(d: Path) -> list[str]:
        return [line for line in log_lines(d) if "method=POST" in line or "method=PATCH" in line]

    def hold_lines(d: Path) -> list[str]:
        f = d / "calls.log.hold"
        return f.read_text(encoding="utf-8").splitlines() if f.exists() else []

    # ---- publisher: happy path -------------------------------------------------
    d = fresh()
    p = run_script(pub, d, {"FAKE_GET_QUEUE": f"{SHA_A},{SHA_A}"})
    check(
        "publisher_happy_path_provisional",
        p.returncode == 0
        and "WHOLE_RUN_IDENTITY_MATCH phase=pre_publish" in p.stdout
        and "WHOLE_RUN_IDENTITY_MATCH phase=post_publish" in p.stdout
        and "commit_comment_http_code=201" in p.stdout,
        f"rc={p.returncode}",
    )
    calls = mutating_calls(d)
    check(
        "publisher_happy_path_single_post_no_patch",
        len(calls) == 1 and "method=POST" in calls[0] and "/commits/" in calls[0],
        f"muations={len(calls)}",
    )
    body = (d / "github-output.txt").read_text(encoding="utf-8")
    check("publisher_happy_path_records_pin_id", "pin_comment_id=424242" in body)

    # ---- publisher: pre-publish drift -----------------------------------------
    d = fresh()
    p = run_script(pub, d, {"FAKE_GET_QUEUE": SHA_B})
    check(
        "publisher_pre_publish_branch_drift",
        p.returncode != 0
        and "WHOLE_RUN_IDENTITY_MISMATCH phase=pre_publish" in p.stdout
        and "commit_comment_http_code" not in p.stdout,
        f"rc={p.returncode}",
    )
    check("publisher_pre_publish_drift_publishes_nothing", mutating_calls(d) == [])

    # ---- publisher: unverifiable identity --------------------------------------
    for name, over in (
        ("publisher_ref_query_transport_failure", {"FAKE_GET_TRANSPORT_FAIL": "1"}),
        ("publisher_ref_query_http_failure", {"FAKE_GET_HTTP_FAIL": "1"}),
        ("publisher_ref_missing_sha_field", {"FAKE_REF_SHA": "MISSING_FIELD"}),
    ):
        d = fresh()
        p = run_script(pub, d, dict(over))
        check(
            name,
            p.returncode != 0
            and "WHOLE_RUN_IDENTITY_UNVERIFIABLE phase=pre_publish" in p.stdout
            and mutating_calls(d) == [],
            f"rc={p.returncode}",
        )

    # ---- publisher: creation HTTP matrix ---------------------------------------
    for code in ("200", "202", "204", "301", "302", "400", "401", "403", "404", "409", "422", "429", "500"):
        d = fresh()
        p = run_script(pub, d, {"FAKE_GET_QUEUE": f"{SHA_A},{SHA_A}", "FAKE_CODE": code})
        check(
            f"publisher_create_http_{code}_fails",
            p.returncode != 0 and f"commit_comment_http_code={code}" in p.stdout,
            f"rc={p.returncode}",
        )
    d = fresh()
    p = run_script(
        pub,
        d,
        {"FAKE_GET_QUEUE": f"{SHA_A},{SHA_A}", "FAKE_CODE_TRANSPORT_FAIL": "1"},
    )
    check(
        "publisher_create_transport_failure_fails",
        p.returncode != 0,
        f"rc={p.returncode}",
    )
    d = fresh()
    p = run_script(pub, d, {"FAKE_GET_QUEUE": f"{SHA_A},{SHA_A}", "FAKE_CODE": "201", "FAKE_RESPONSE_BODY": "{}"})
    check(
        "publisher_unreadable_pin_id_fails",
        p.returncode != 0 and "PUBLISHED_PIN_ID_UNREADABLE" in p.stdout,
        f"rc={p.returncode}",
    )

    # ---- publisher: post-publish drift must invalidate --------------------------
    d = fresh()
    p = run_script(pub, d, {"FAKE_GET_QUEUE": f"{SHA_A},{SHA_B}"})
    invalidated = (d / "runner-temp/rc004-mandatory-pin-patch.json").read_text(encoding="utf-8") if (
        d / "runner-temp/rc004-mandatory-pin-patch.json"
    ).exists() else ""
    check(
        "publisher_post_publish_drift_fails_and_invalidates",
        p.returncode != 0
        and "WHOLE_RUN_IDENTITY_MISMATCH phase=post_publish" in p.stdout
        and "PUBLISHED_PIN_INVALIDATED_AFTER_BRANCH_DRIFT" in p.stdout
        and "pin_status: INVALIDATED" in invalidated
        and any("method=PATCH" in line for line in mutating_calls(d)),
        f"rc={p.returncode}",
    )
    check(
        "publisher_post_publish_drift_records_observed_head",
        SHA_B in invalidated,
        "",
    )

    # ---- seal: publisher-result validation --------------------------------------
    good_pin = "\n".join(
        [
            "## CORE-RC-REFREEZE-004-CORRECTIVE-002 mandatory exact pin",
            "",
            "- pin_status: PROVISIONAL_PENDING_IDENTITY_SEAL",
            "- run_id: 99999999999",
            f"- exact_candidate_sha: {SHA_A}",
        ]
    ) + "\n"
    bad_pins = {
        "seal_rejects_publisher_pin_sha_mismatch": good_pin.replace(SHA_A, SHA_B),
        "seal_rejects_publisher_pin_run_mismatch": good_pin.replace("99999999999", "1234"),
        "seal_rejects_publisher_pin_not_provisional": good_pin.replace(
            "PROVISIONAL_PENDING_IDENTITY_SEAL", "IDENTITY_SEALED"
        ),
    }
    for name, body in bad_pins.items():
        d = fresh()
        p = run_script(seal, d, {"PIN_COMMENT_ID": "424242"}, pin_body=body)
        check(name, p.returncode != 0, f"rc={p.returncode}")
    d = fresh()
    p = run_script(seal, d, {"PIN_COMMENT_ID": ""}, pin_body=good_pin)
    check(
        "seal_rejects_missing_pin_id",
        p.returncode != 0 and "SEAL_MISSING_PUBLISHER_PIN_ID" in p.stdout,
        f"rc={p.returncode}",
    )
    d = fresh()
    p = run_script(seal, d, {"PIN_COMMENT_ID": "424242", "FAKE_GET_HTTP_FAIL": "1"}, pin_body=good_pin)
    check("seal_rejects_unreadable_publisher_pin", p.returncode != 0, f"rc={p.returncode}")

    # ---- seal: identity window --------------------------------------------------
    d = fresh()
    p = run_script(seal, d, {"PIN_COMMENT_ID": "424242", "FAKE_GET_QUEUE": SHA_B}, pin_body=good_pin)
    check(
        "seal_pre_hold_drift_fails_without_seal",
        p.returncode != 0
        and "WHOLE_RUN_IDENTITY_MISMATCH phase=seal_pre_hold" in p.stdout
        and not (d / "runner-temp/rc004-mandatory-pin-patch.json").exists(),
        f"rc={p.returncode}",
    )
    d = fresh()
    p = run_script(seal, d, {"PIN_COMMENT_ID": "424242", "FAKE_GET_QUEUE": f"{SHA_A},{SHA_B}"}, pin_body=good_pin)
    check(
        "seal_post_hold_drift_fails_without_seal",
        p.returncode != 0
        and "WHOLE_RUN_IDENTITY_MISMATCH phase=seal_post_hold" in p.stdout
        and not (d / "runner-temp/rc004-mandatory-pin-patch.json").exists(),
        f"rc={p.returncode}",
    )
    d = fresh()
    p = run_script(
        seal,
        d,
        {"PIN_COMMENT_ID": "424242", "FAKE_GET_QUEUE": f"{SHA_A},{SHA_A}", "FAKE_CODE": "401"},
        pin_body=good_pin,
    )
    check(
        "seal_patch_http_401_fails",
        p.returncode != 0 and "commit_comment_patch_http_code=401" in p.stdout,
        f"rc={p.returncode}",
    )
    d = fresh()
    p = run_script(
        seal,
        d,
        {"PIN_COMMENT_ID": "424242", "FAKE_GET_QUEUE": f"{SHA_A},{SHA_A},{SHA_B}", "FAKE_CODE": "200"},
        pin_body=good_pin,
    )
    check(
        "seal_post_write_drift_invalidates_sealed_pin",
        p.returncode != 0
        and "WHOLE_RUN_IDENTITY_MISMATCH phase=seal_post_write" in p.stdout
        and "SEALED_PIN_INVALIDATED_AFTER_BRANCH_DRIFT" in p.stdout
        and "pin_status: INVALIDATED" in (d / "runner-temp/rc004-mandatory-pin-patch.json").read_text(encoding="utf-8"),
        f"rc={p.returncode}",
    )

    # ---- seal: happy path -------------------------------------------------------
    d = fresh()
    p = run_script(
        seal,
        d,
        {"PIN_COMMENT_ID": "424242", "FAKE_GET_QUEUE": f"{SHA_A},{SHA_A},{SHA_A}", "FAKE_CODE": "200"},
        pin_body=good_pin,
    )
    sealed = (d / "runner-temp/rc004-mandatory-pin-patch.json").read_text(encoding="utf-8")
    check(
        "seal_happy_path_seals_pin",
        p.returncode == 0
        and "commit_comment_patch_http_code=200" in p.stdout
        and "pin_status: IDENTITY_SEALED" in sealed
        and "pre_publish,post_publish,seal_pre_hold,seal_post_hold,seal_post_write" in sealed
        and "NON_AUTHORITATIVE_UNTIL_IDENTITY_SEALED_AND_OVERALL_RUN_SUCCESS" in sealed,
        f"rc={p.returncode}",
    )
    check(
        "seal_happy_path_single_patch",
        len([line for line in mutating_calls(d) if "method=PATCH" in line]) == 1,
        f"patch_calls={len([line for line in mutating_calls(d) if 'method=PATCH' in line])}",
    )
    check(
        "seal_happy_path_bounded_hold_invoked",
        hold_lines(d) == ["sleep_args=30"],
        f"hold={hold_lines(d)}",
    )

    print(f"fault_matrix_cases={cases}")
    if failures:
        print(f"fault_matrix_failures={len(failures)}")
        for name in failures:
            print(f"failing_case={name}")
        print("PUBLISHER_IDENTITY_FAULT_MATRIX=FAIL")
        return 1
    print("PUBLISHER_IDENTITY_FAULT_MATRIX=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
