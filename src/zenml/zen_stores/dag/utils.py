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
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlmodel import Session, col

from zenml.enums import ExecutionStatus, MetadataResourceTypes
from zenml.metadata.metadata_types import MetadataType
from zenml.models import RunMetadataEntry
from zenml.zen_stores.dag.dag_generator import DAGGeneratorHelper
from zenml.zen_stores.dag.models import InputArtifactRow, OutputArtifactRow
from zenml.zen_stores.schemas import (
    ArtifactVersionSchema,
    PipelineRunSchema,
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


def add_run_context(
    helper: DAGGeneratorHelper, run: PipelineRunSchema
) -> None:
    """Add retained wait conditions and child runs to either DAG representation.

    Args:
        helper: The graph being built.
        run: The SQL run with its retained relationships loaded.
    """
    for condition in run.wait_conditions:
        node_metadata: Dict[str, Any] = {
            "status": condition.status,
            "type": condition.type,
            "created_at": condition.created.isoformat(),
        }
        if condition.resolution:
            node_metadata["resolution"] = condition.resolution
        if condition.question and not run.is_archived:
            node_metadata["question"] = condition.question
        if condition.resolved_at:
            node_metadata["resolved_at"] = condition.resolved_at.isoformat()

        helper.add_wait_condition_node(
            node_id=helper.get_wait_condition_node_id(condition.name),
            id=condition.id,
            name=condition.name,
            **node_metadata,
        )

    for child_run in run.child_runs:
        child_run_metadata: Dict[str, Any] = {
            "status": child_run.status,
        }
        if child_run.start_time:
            child_run_metadata["start_time"] = child_run.start_time.isoformat()
            if child_run.end_time:
                child_run_metadata["end_time"] = child_run.end_time.isoformat()
                child_run_metadata["duration"] = (
                    child_run.end_time - child_run.start_time
                ).total_seconds()

        helper.add_child_run_node(
            node_id=helper.get_child_run_node_id(child_run.name),
            id=child_run.id,
            name=child_run.name,
            **child_run_metadata,
        )
        # TODO: maybe include nodes for outputs and connect via edges?
