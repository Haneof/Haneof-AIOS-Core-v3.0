"""Fact-ingestion adapters for AIOS v3.0."""

from .conversation import (
    ConversationCommit,
    ConversationIngestor,
    ConversationMessageCommit,
    INTERACTION_DIMENSION,
)
from .reality import (
    AUDIT_DIMENSION,
    IngestFailureReceipt,
    IngestReceipt,
    MechanicalSeriesPolicy,
    MechanicalSeriesReceipt,
    MediaDescriptorRecord,
    NumericSample,
    RealityIngestService,
    RealityRecord,
    SourceAdapterSpec,
)

__all__ = [
    "AUDIT_DIMENSION",
    "ConversationCommit",
    "ConversationIngestor",
    "ConversationMessageCommit",
    "INTERACTION_DIMENSION",
    "IngestFailureReceipt",
    "IngestReceipt",
    "MechanicalSeriesPolicy",
    "MechanicalSeriesReceipt",
    "MediaDescriptorRecord",
    "NumericSample",
    "RealityIngestService",
    "RealityRecord",
    "SourceAdapterSpec",
]
