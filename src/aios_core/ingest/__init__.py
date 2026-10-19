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
from .multimodal_edge import (
    FEATURE_DIM,
    EdgeMultimodalCleaner,
    ImageSemanticObservation,
    QualityGate,
    RawByteSink,
    VoiceprintLSHIndex,
    VoiceprintLifecycleManager,
    VoiceprintProfile,
    VoiceprintTTLRegistry,
    assess_image_quality,
)

__all__ = [
    "AUDIT_DIMENSION",
    "ConversationCommit",
    "ConversationIngestor",
    "ConversationMessageCommit",
    "EdgeMultimodalCleaner",
    "FEATURE_DIM",
    "ImageSemanticObservation",
    "IngestFailureReceipt",
    "IngestReceipt",
    "MechanicalSeriesPolicy",
    "MechanicalSeriesReceipt",
    "MediaDescriptorRecord",
    "NumericSample",
    "QualityGate",
    "RawByteSink",
    "RealityIngestService",
    "RealityRecord",
    "SourceAdapterSpec",
    "VoiceprintLSHIndex",
    "VoiceprintLifecycleManager",
    "VoiceprintProfile",
    "VoiceprintTTLRegistry",
    "assess_image_quality",
]
