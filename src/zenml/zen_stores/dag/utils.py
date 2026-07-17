#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""DAG generation utilities."""

import json
from collections import defaultdict
from typing import Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlmodel import Session, col

from zenml.enums import ExecutionStatus, MetadataResourceTypes
from zenml.metadata.metadata_types import MetadataType
from zenml.models import RunMetadataEntry
from zenml.zen_stores.dag.models import InputArtifactRow, OutputArtifactRow
from zenml.zen_stores.schemas import (
    ArtifactVersionSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
    StepRunInputArtifactSchema,
    StepRunOutputArtifactSchema,
    StepRunSchema,
)
from zenml.zen_stores.schemas.utils import resolve_metadata_collection


def load_input_artifact_rows(
    session: Session, pipeline_run_id: UUID
) -> Dict[UUID, List[InputArtifactRow]]:
    """Load the input artifact rows for a pipeline run.

    Args:
        session: The database session.
        pipeline_run_id: The ID of the pipeline run.

    Returns:
        The input artifact rows, grouped by step run ID.
    """
    query = (
        select(
            col(StepRunInputArtifactSchema.step_id),
            col(StepRunInputArtifactSchema.name),
            col(StepRunInputArtifactSchema.artifact_id),
            col(StepRunInputArtifactSchema.type),
            col(StepRunInputArtifactSchema.input_index),
            col(StepRunInputArtifactSchema.chunk_index),
            col(StepRunInputArtifactSchema.chunk_size),
            col(ArtifactVersionSchema.type),
            col(ArtifactVersionSchema.data_type),
            col(ArtifactVersionSchema.save_type),
        )
        .join(
            StepRunSchema,
            col(StepRunSchema.id) == StepRunInputArtifactSchema.step_id,
        )
        .join(
            ArtifactVersionSchema,
            col(ArtifactVersionSchema.id)
            == StepRunInputArtifactSchema.artifact_id,
        )
        .where(col(StepRunSchema.pipeline_run_id) == pipeline_run_id)
        .where(col(StepRunSchema.status) != ExecutionStatus.RETRIED.value)
    )
    rows: Dict[UUID, List[InputArtifactRow]] = defaultdict(list)
    for db_row in session.execute(query):
        row = InputArtifactRow(*db_row)
        rows[row.step_id].append(row)

    return rows


def load_output_artifact_rows(
    session: Session, pipeline_run_id: UUID
) -> Dict[UUID, List[OutputArtifactRow]]:
    """Load the output artifact rows for a pipeline run.

    Args:
        session: The database session.
        pipeline_run_id: The ID of the pipeline run.

    Returns:
        The output artifact rows, grouped by step run ID.
    """
    query = (
        select(
            col(StepRunOutputArtifactSchema.step_id),
            col(StepRunOutputArtifactSchema.name),
            col(StepRunOutputArtifactSchema.artifact_id),
            col(ArtifactVersionSchema.type),
            col(ArtifactVersionSchema.data_type),
            col(ArtifactVersionSchema.save_type),
        )
        .join(
            StepRunSchema,
            col(StepRunSchema.id) == StepRunOutputArtifactSchema.step_id,
        )
        .join(
            ArtifactVersionSchema,
            col(ArtifactVersionSchema.id)
            == StepRunOutputArtifactSchema.artifact_id,
        )
        .where(col(StepRunSchema.pipeline_run_id) == pipeline_run_id)
        .where(col(StepRunSchema.status) != ExecutionStatus.RETRIED.value)
    )
    rows: Dict[UUID, List[OutputArtifactRow]] = defaultdict(list)
    for db_row in session.execute(query):
        row = OutputArtifactRow(*db_row)
        rows[row.step_id].append(row)

    return rows


def load_step_run_metadata(
    session: Session,
    pipeline_run_id: UUID,
    metadata_keys: List[str],
) -> Dict[UUID, Dict[str, MetadataType]]:
    """Load run metadata values for the step runs of a pipeline run.

    Args:
        session: The database session.
        pipeline_run_id: The ID of the pipeline run.
        metadata_keys: The run metadata keys to load.

    Returns:
        The resolved metadata values, grouped by step run ID.
    """
    query = (
        select(
            col(RunMetadataResourceSchema.resource_id),
            col(RunMetadataSchema.key),
            col(RunMetadataSchema.value),
            col(RunMetadataSchema.created),
        )
        .join(
            RunMetadataSchema,
            col(RunMetadataSchema.id)
            == RunMetadataResourceSchema.run_metadata_id,
        )
        .join(
            StepRunSchema,
            col(StepRunSchema.id) == RunMetadataResourceSchema.resource_id,
        )
        .where(
            col(RunMetadataResourceSchema.resource_type)
            == MetadataResourceTypes.STEP_RUN
        )
        .where(col(StepRunSchema.pipeline_run_id) == pipeline_run_id)
        .where(col(StepRunSchema.status) != ExecutionStatus.RETRIED.value)
        .where(col(RunMetadataSchema.key).in_(metadata_keys))
    )
    metadata_collections: Dict[UUID, Dict[str, List[RunMetadataEntry]]] = (
        defaultdict(dict)
    )
    for step_id, key, value, created in session.execute(query):
        metadata_collections[step_id].setdefault(key, []).append(
            RunMetadataEntry(value=json.loads(value), created=created)
        )

    return {
        step_id: resolve_metadata_collection(collection)
        for step_id, collection in metadata_collections.items()
    }
