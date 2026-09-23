# Key Sources for 2528c22 - Evidence Delivery B

## Included Files

- freeze.py - freeze publish/exception protocol
- publication.py - receipt validation + confirm_uncertain_package
- resident_broker.py - isolation classification, broker boundary
- driver.py - checkpoint validation, accepted_a_dir import guard
- restart.py - formal A import + Driver checkpoint validation
- audit.py - HASHES/A_SHA/CORE_SHA/FIXTURE_HASH pins
- real-a-import-312.yml - CI gate
- isolation_probe.py - actual namespace probe
- SHA256SUMS - file hashes
- diff_2528c22_vs_def9174.patch - diff from previous exact-head

## Freeze Publish/Exception - Key Logic (after fix)

```python
# create_receipt - commit point
receipt_path = destination / RECEIPT_NAME
if receipt_path.exists():
    # Prevent marking CONFIRMED only by exists()
    try:
        existing_data = json.loads(receipt_path.read_text())
    except Exception:
        pass
atomic_json(receipt_path, receipt)  # fsync file + dest dir
try:
    fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
    os.fsync(fd)  # parent fsync for durability
except BaseException:
    # Persistence uncertain, cannot ordinary auto pass
    raise
# Verify complete, valid, matching
load_and_verify_receipt(destination, expected_manifest_sha256=manifest_sha256, expected_publication_id=publication_id)
```

```python
# freeze exception - distinguish 3 states via load_and_verify_receipt, not exists()
actual_receipt_exists = receipt_path.is_file() and not receipt_path.is_symlink()
receipt_valid = False
if actual_receipt_exists:
    try:
        manifest_sha = digest(manifest_path)
        pub_id_in_manifest = manifest_data.get("publication", {}).get("id")
        if pub_id_in_manifest == publication_id:
            load_and_verify_receipt(destination, expected_manifest_sha256=manifest_sha, expected_publication_id=publication_id)
            receipt_valid = True
    except Exception:
        receipt_valid = False

if receipt_created and receipt_valid:
    pub_status = "CONFIRMED_BUT_SOURCE_FAILED"
elif actual_receipt_exists and receipt_valid:
    # Parent fsync after receipt failed -> UNCERTAIN, require explicit re-confirmation
    pub_status = "UNCERTAIN"
    is_confirmed = False
else:
    pub_status = "UNCERTAIN"
```

## Publication Receipt Validation + confirm_uncertain_package

```python
def _verify_sqlite_integrity(source):
    # MUST NOT modify source, no deletion
    for db_name in ("private_world.sqlite", "world_index.sqlite"):
        for suffix in ("-wal", "-shm", "-journal"):
            require(not Path(str(db_path) + suffix).exists(), f"unfrozen sidecar present")
    for db_name in ...:
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
        except Exception as exc:
            raise ValueError(f"sqlite immutable open failed, stop: {exc}")
        # quick_check
        # MUST NOT delete sidecars, verify none created
```

```python
def load_and_verify_receipt(source, expected_manifest_sha256, expected_publication_id):
    require(not receipt_path.is_symlink(), "receipt is symlink")
    require(receipt_path.is_file(), "publication unconfirmed: receipt missing, ordinary restore is blocked")
    data = json.loads(...)
    require(data["format"] == RECEIPT_FORMAT)
    require(data["manifest_sha256"] == expected_manifest_sha256)
    # Also verify actual manifest file hash
    actual_manifest_hash = digest(source / "manifest.json")
    require(actual_manifest_hash == expected_manifest_sha256)
```

```python
def confirm_uncertain_package(source, expected_manifest_sha256, operator_attestation_path):
    require(attestation file exists, not symlink)
    require(operator, reason, verified_checks list)
    required_checks = {"manifest_hash", "file_digests", "sqlite_integrity", "watermark_match"}
    require(required_checks.issubset(provided))
    # Perform actual mechanical checks
    if "file_digests" in provided:
        _verify_manifest_files(source, manifest)
    if "sqlite_integrity" in provided:
        _verify_sqlite_integrity(source)
    # Do not overwrite existing valid receipt
    require(not receipt_path.exists(), "receipt already exists; ordinary restore should be used")
    atomic_json(receipt_path, receipt)
    # Verify after creation
    load_and_verify_receipt(source, expected_manifest_sha256=actual_hash, expected_publication_id=pub_id)
```

## Formal A Import + Driver Checkpoint Validation

```python
def import_accepted_a_to_driver_run(staging, driver_run_dir, repo, synthetic=False):
    # Verify fixed hash A structure
    # stage_accepted_a verifies HASHES, A_SHA, CORE_SHA
    # import copies world/index/release/restart/mechanical_restart
    # No manual driver_state.json, no skipping hash/Core checks
    # synthetic=False required for formal, synthetic=True has explicit identifier SYNTHETIC:
    # Forbidden model adapter: Driver with model that immediate error if called
```

Driver checkpoint loss guard (from test_round5):
- Existing progress -> checkpoint loss/damage (delete driver_state.json or corrupt) -> try accepted_a_dir import -> rejected with DriverBlocked "checkpoint loss|existing world files|missing checkpoint"
- No overwrite of existing world files, no deleting WAL/SHM/journal
- Preserves legal budget/defer, don't force-drain

## Isolation Classification

- Decision logic PASS != probe executed PASS != Resident PASS
- synthetic_mechanics: PASS (131 tests)
- actual_namespace_probe: INCONCLUSIVE (unshare permission not permitted in GitHub runner, expected - not FAIL)
- actual_Resident_isolation: BLOCKED (real Resident not launchable without formal approval)
- launchable: false

Exception classification:
- Namespace permission insufficient -> NOT_TESTED/INCONCLUSIVE, not FAIL
- Unexpected program RuntimeError -> explicitly fail, not NOT_TESTED
- Non-permission I/O fault -> explicitly fail
- Illegal probe output -> explicitly fail

## Broker Boundary (after fix)

```python
def _check_packet_boundary(packet, snapshot):
    require(set(packet.keys()) == {"protocol", "request_id", "kind", "input_sha256", "input"})
    require(protocol == "c15-resident-broker-v1")
    approved_snapshot_keys = {"user_input", "wake_reason", "cockpit", "capability_catalog", "capability_history", "round_index", "remaining_tool_rounds"}
    forbidden_keys = {"world_revision", "index_watermark", "release_sha256", "driver_state", "session", "clock", "private_world", "world_index", "release_state", "operator", "git_metadata", "private_a"}
    for fk in forbidden_keys:
        require(fk not in input_data, f"operator private material must not enter")
    require("governance" not in json.dumps(input_data).lower())
    for k in input_data.keys():
        require(k in approved_snapshot_keys, f"unapproved snapshot field")
```

- Credentials in HTTP auth layer: `Authorization: Bearer <token>`, not in model message or ordinary log
- Synthetic endpoint is transport test double, no claim "no filesystem" unless OS permission verified
- No sensitive info sent and process has no read permission separately accounted
- Core legal AIOS capability calls retained via Runtime execution
- Request/reply binding validation: response must have same request_id, kind, input_sha256, otherwise BrokerError
- Error propagation: directive validation failure -> BrokerError with propagation

## CI Gate Diff

See diff_2528c22_vs_def9174.patch - 575 lines, includes:
- publication.py: sidecar non-deletion, immutable-only, receipt verification
- freeze.py: exception handling via load_and_verify_receipt
- resident_broker.py: structure boundary, auth header, binding validation
- test_round5_fixes.py: updated fault window parent fsync expectation to UNCERTAIN per new protocol

Previous head def9174 already had real-a-import-312 workflow with exact-head evidence, PYTHONDONTWRITEBYTECODE, clean pycache.

New head 2528c22 adds the three PM-required fixes and keeps all CI green.

## Exact-Head Evidence

- c15: 35924990848 - 131 preflight, 146 regression, Python 3.12.14, exact-head 2528c22, 0 failures, 0 skipped
- p16: 35924990895 - SUCCESS
- real-a-312: 35924990859 - SUCCESS with JSON receipt (see main report)

No zero-skipped as ready proof - all counts explicit.
