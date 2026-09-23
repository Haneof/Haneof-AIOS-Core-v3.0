"""Plan forward-only invalidation; the caller commits it WITH the root change.

This is mechanical dependency maintenance, not replacement cognition. Scope is
supplied by a trusted private-world coordinator, never inferred from all users.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from aios_core.contracts.base import WorldObject
from aios_core.contracts.enums import ObjectType, SummaryStatus
from aios_core.contracts.models import Dependency
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.registry import canonical_model_for_object_type
from aios_core.dependency.graph import collect_impacted_dependents
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore


@dataclass(frozen=True)
class InvalidationPlan:
    objects: tuple[WorldObject, ...]
    stale_refs: tuple[tuple[str, int], ...]
    skipped_refs: tuple[tuple[str, int], ...]


def plan_invalidation(
    store: SQLiteWorldStore, *, changed_ref: ObjectRef,
    changed_at: datetime, reason: str, subject_ids: Sequence[str],
) -> InvalidationPlan:
    allowed = frozenset(subject_ids)
    payloads: dict[tuple[str, int | None], dict] = {}

    def payload(ref: ObjectRef) -> dict:
        key = (ref.object_id, ref.revision)
        if key not in payloads:
            payloads[key] = store.get_payload(ref.object_id, revision=ref.revision)
        return payloads[key]

    if changed_ref.revision is None or payload(changed_ref)["subject_id"] not in allowed:
        raise ValueError("invalidation root must be pinned within the private-world scope")
    dependencies = []
    for raw in store.list_payloads(object_type=ObjectType.DEPENDENCY):
        if raw["subject_id"] not in allowed:
            continue
        edge = Dependency.model_validate(raw)
        # Check endpoints too: the edge's own subject is not an authorization
        # to traverse or revise an unrelated private World's objects.
        if any(payload(ref)["subject_id"] not in allowed for ref in
               (edge.dependent_ref, edge.dependency_ref)):
            continue
        dependencies.append(edge)

    objects: list[WorldObject] = []
    stale, skipped = [], []
    for ref in collect_impacted_dependents(dependencies, changed_ref, transitive=True):
        latest = payload(ObjectRef(object_id=ref.object_id))
        key = (ref.object_id, int(ref.revision))
        if latest["revision"] != ref.revision or latest["subject_id"] not in allowed:
            skipped.append(key)
            continue
        data = dict(latest)
        old_revision = int(data["revision"])
        data.update(revision=old_revision + 1, learned_at=changed_at,
                    recorded_at=changed_at, status="stale_review_required")
        metadata = dict(data.get("metadata") or {})
        markers = list(metadata.get("stale_due_to_refs") or [])
        marker = changed_ref.model_dump(mode="json")
        if marker not in markers:
            markers.append(marker)
        metadata.update(stale_due_to_refs=markers, stale_reason=reason,
                        stale_at=changed_at.isoformat())
        data["metadata"] = metadata
        kind = ObjectType(data["object_type"])
        if kind is ObjectType.EVIDENCE_SET:
            data["stale"] = True
        elif kind is ObjectType.SUMMARY:
            data["summary_status"] = SummaryStatus.STALE.value
        elif kind is ObjectType.COGNITIVE_POLICY:
            # A policy version IS its World revision. An invalidation is an
            # auditable new version, not an automatic new learned policy value.
            data.update(version=old_revision + 1, previous_version=old_revision,
                        rollback_pointer=old_revision, changed_at=changed_at,
                        changed_by="dependency_propagation", reason=reason)
        obj = canonical_model_for_object_type(kind).model_validate(data)
        objects.append(obj)
        stale.append(key)
        identity = [obj.object_id, obj.revision, changed_ref.object_id, changed_ref.revision]
        suffix = hashlib.sha256(canonical_json_dumps(identity).encode()).hexdigest()[:24]
        objects.append(Dependency(
            object_id=f"dep_stale_{suffix}", subject_id=obj.subject_id,
            learned_at=changed_at, recorded_at=changed_at,
            created_by="cognition_revision:propagation",
            dependent_ref=ObjectRef(object_id=obj.object_id, revision=obj.revision),
            dependency_ref=changed_ref,
            dependency_type="stale_due_to_superseded_cognition",
        ))
    return InvalidationPlan(tuple(objects), tuple(stale), tuple(skipped))
