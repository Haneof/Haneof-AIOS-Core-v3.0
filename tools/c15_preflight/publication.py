"""Fail-closed live publication confirmation, outside the package filesystem.

A package cannot confirm itself. The controller issues an identity capability
ONLY after every publication/source checkpoint I/O has returned successfully.
No capability is issued on exception. It cannot be reconstructed from a READY
file, a manifest digest, JSON or a pickle. After controller death, ordinary
restore is BLOCKED pending a separately authorized independent recovery audit.

This is not a durable distributed commit service, hostile-Python isolation, or
proof that a filesystem/hardware device honored fsync. Those are explicit limits.
"""
from __future__ import annotations

from dataclasses import dataclass
from weakref import WeakKeyDictionary

from .audit import require


class PublicationConfirmation:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise TypeError("publication confirmation is issued only by successful freeze")

    def __reduce__(self):
        raise TypeError("live publication confirmation cannot be persisted or replayed")


_confirmed: WeakKeyDictionary = WeakKeyDictionary()


def _confirm(manifest_sha256: str, publication_id: str) -> PublicationConfirmation:
    confirmation = object.__new__(PublicationConfirmation)
    _confirmed[confirmation] = (manifest_sha256, publication_id)
    return confirmation


def require_confirmation(confirmation, *, manifest_sha256: str, publication_id: str):
    require(isinstance(confirmation, PublicationConfirmation),
            "publication unconfirmed: ordinary restore is blocked")
    require(_confirmed.get(confirmation) == (manifest_sha256, publication_id),
            "publication confirmation absent/foreign; independent recovery audit required")


@dataclass(frozen=True)
class FrozenPackage:
    manifest: dict
    confirmation: PublicationConfirmation
