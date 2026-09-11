# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Map immutable archive record models to their live SQL schemas."""

from typing import Dict, Type

from zenml.zen_stores.retention.manifest import (
    ConfigurationRecord,
    Record,
    RunRecord,
    SnapshotRecord,
    StepRecord,
)
from zenml.zen_stores.schemas import (
    BaseSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.schemas.archivable_schemas import ArchivableSchema

RECORD_SCHEMAS: Dict[Type[Record], Type[BaseSchema]] = {
    RunRecord: PipelineRunSchema,
    StepRecord: StepRunSchema,
    SnapshotRecord: PipelineSnapshotSchema,
    ConfigurationRecord: StepConfigurationSchema,
}

ARCHIVABLE_RECORD_SCHEMAS: Dict[Type[Record], Type[ArchivableSchema]] = {
    RunRecord: PipelineRunSchema,
    StepRecord: StepRunSchema,
    SnapshotRecord: PipelineSnapshotSchema,
}


def schema_for_record(record: Record) -> Type[BaseSchema]:
    """Return the SQL schema paired with an immutable record model.

    Args:
        record: Verified record from the frozen archive format.

    Returns:
        Live SQL schema that owns the record identity.
    """
    return RECORD_SCHEMAS[type(record)]
