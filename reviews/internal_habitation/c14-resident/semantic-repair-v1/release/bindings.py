#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

RELEASE_DIR = Path(__file__).resolve().parent
REPAIR_ROOT = RELEASE_DIR.parent
FIXTURE_VERSION = "c14-semantic-repair-fixture-v1"
FIXTURE_SHA256 = "sha256:1095d5aef52061753db7d9dab558af1361b92976f2ded0e6956d70afe3e6527f"
SCHEMA_VERSION = "c14-semantic-repair-event-v1"
CONTRACT_VERSION = "c14-semantic-repair-sequential-release-v1"
OPERATOR_VERSION = "c14-sem-repair-blind-release-operator-v1"
STATE_VERSION = "c14-sem-repair-release-state-v1"
INGEST_ADAPTER_VERSION = "c14-sem-repair-mechanical-ingest-adapter-v1"
BINDING_VERSION = "c14-sem-repair-fixture-event-binding-v1"
CANONICAL_ADAPTER_VERSION = "c14-sem-repair-canonical-conversation-adapter-v1"
CANONICAL_BINDING_VERSION = "c14-sem-repair-canonical-conversation-binding-v1"
SUBJECT_ID = "user_1"
PHASE_A_MAX = 6
PHASE_B_START = 7


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (
            (parent / "src" / "aios_core").is_dir()
            and (parent / "reviews" / "internal_habitation" / "c14-resident" / "v2" / "release").is_dir()
        ):
            return parent
    raise RuntimeError("repository root not found")


REPO_ROOT = _repo_root()
V2_RELEASE = REPO_ROOT / "reviews" / "internal_habitation" / "c14-resident" / "v2" / "release"


def _load_module(name: str, filename: str) -> ModuleType:
    path = V2_RELEASE / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen v2 release module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_release_operator() -> ModuleType:
    module = _load_module("_c14_semrepair_v2_release_operator", "release_operator.py")
    module.OPERATOR_VERSION = OPERATOR_VERSION
    module.LEGACY_HANDOFF_OPERATOR_VERSION = "__semantic_repair_no_legacy_handoff__"
    module.STATE_VERSION = STATE_VERSION
    module.FIXTURE_VERSION = FIXTURE_VERSION
    module.FIXTURE_SHA256 = FIXTURE_SHA256
    module.SCHEMA_VERSION = SCHEMA_VERSION
    module.CONTRACT_VERSION = CONTRACT_VERSION
    module.INGEST_ADAPTER_VERSION = INGEST_ADAPTER_VERSION
    module.BINDING_VERSION = BINDING_VERSION
    module.CANONICAL_CONVERSATION_ADAPTER_VERSION = CANONICAL_ADAPTER_VERSION
    module.CANONICAL_CONVERSATION_BINDING_VERSION = CANONICAL_BINDING_VERSION
    module.PHASE_A_MAX = PHASE_A_MAX
    module.PHASE_B_START = PHASE_B_START
    module.ROOT = REPAIR_ROOT
    module.FIXTURE_PATH = REPAIR_ROOT / "fixture" / "sealed_fixture.json"
    module.MANIFEST_PATH = REPAIR_ROOT / "fixture" / "fixture_manifest.json"
    return module


def load_mechanical_adapter() -> ModuleType:
    module = _load_module("_c14_semrepair_v2_mechanical_adapter", "mechanical_ingest_adapter.py")
    module.FIXTURE_VERSION = FIXTURE_VERSION
    module.FIXTURE_SHA256 = FIXTURE_SHA256
    module.INGEST_ADAPTER_VERSION = INGEST_ADAPTER_VERSION
    module.BINDING_VERSION = BINDING_VERSION
    module.SUBJECT_ID = SUBJECT_ID
    module.V2_ROOT = REPAIR_ROOT
    module.MANIFEST_PATH = REPAIR_ROOT / "fixture" / "fixture_manifest.json"

    original_validate = module._validate_projection

    def validate_repair_projection(raw):
        event = original_validate(raw)
        if (
            event.get("dimension") == "dim:conversation"
            and event.get("source_kind") == "conversation"
            and event.get("source_class") == "USER"
            and event.get("modality") == "text"
        ):
            raise module.IngestAdapterError(
                "repair USER conversation must use canonical_conversation_ingest.py"
            )
        return event

    module._validate_projection = validate_repair_projection
    return module


def load_canonical_adapter() -> ModuleType:
    module = _load_module("_c14_semrepair_v2_canonical_adapter", "canonical_conversation_ingest.py")
    module.FIXTURE_VERSION = FIXTURE_VERSION
    module.FIXTURE_SHA256 = FIXTURE_SHA256
    module.ADAPTER_VERSION = CANONICAL_ADAPTER_VERSION
    module.BINDING_VERSION = CANONICAL_BINDING_VERSION
    module.V2_ROOT = REPAIR_ROOT
    module.MANIFEST_PATH = REPAIR_ROOT / "fixture" / "fixture_manifest.json"
    return module
