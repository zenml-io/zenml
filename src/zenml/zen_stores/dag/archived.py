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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Recorded execution graphs built entirely from retained SQL relationships."""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from sqlmodel import Session, col, select

from zenml.config.source import Source
from zenml.enums import (
    ArtifactSaveType,
    ExecutionStatus,
    StepRunInputArtifactType,
)
from zenml.models import PipelineRunDAG
from zenml.zen_stores.dag.dag_generator import DAGGeneratorHelper
from zenml.zen_stores.dag.utils import (
    load_input_artifact_rows,
    load_output_artifact_rows,
    load_step_run_metadata,
)
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    StepRunParentsSchema,
    StepRunSchema,
)


def generate_archived_dag(
    session: Session,
    run: PipelineRunSchema,
    helper: DAGGeneratorHelper,
    include_step_metadata: Optional[List[str]],
) -> PipelineRunDAG:
    """Build the recorded graph without interpreting archived configuration.

    Configuration-only nodes, groups and unrealized outputs are unavailable.
    Parent rows and artifact links describe what actually ran, including
    cached outputs, without inventing missing configuration.

    Args:
        session: The SQL session.
        run: The archived run with step identities loaded.
        helper: Graph builder containing retained run context.
        include_step_metadata: Retained metadata keys to add to step nodes.

    Returns:
        The graph of recorded steps and their retained relationships.
    """
    steps = {
        step.id: step
        for step in run.step_runs
        if step.status != ExecutionStatus.RETRIED.value
    }
    parents: Dict[UUID, Set[UUID]] = defaultdict(set)
    query = (
        select(StepRunParentsSchema)
        .join(
            StepRunSchema,
            col(StepRunSchema.id) == StepRunParentsSchema.child_id,
        )
        .where(col(StepRunSchema.pipeline_run_id) == run.id)
    )
    for link in session.exec(query):
        if link.parent_id in steps and link.child_id in steps:
            parents[link.child_id].add(link.parent_id)

    metadata = (
        load_step_run_metadata(session, run.id, include_step_metadata)
        if include_step_metadata
        else {}
    )
    outputs = load_output_artifact_rows(session, run.id)
    inputs = load_input_artifact_rows(session, run.id)
    producers: Dict[UUID, List[Tuple[UUID, str]]] = defaultdict(list)
    for step in steps.values():
        details: Dict[str, Any] = {"status": step.status}
        if step.step_type is not None:
            details["type"] = step.step_type
        if step.start_time:
            details["start_time"] = step.start_time.isoformat()
            if step.end_time:
                details["duration"] = (
                    step.end_time - step.start_time
                ).total_seconds()
        if step_metadata := metadata.get(step.id):
            details["run_metadata"] = step_metadata
        node = helper.add_step_node(
            node_id=helper.get_step_node_id(step.name),
            name=step.name,
            id=step.id,
            **details,
        )
        for output in outputs.get(step.id, []):
            artifact = helper.add_artifact_node(
                node_id=helper.get_artifact_node_id(
                    name=str(output.artifact_id)
                    if output.artifact_save_type == ArtifactSaveType.MANUAL
                    else output.name,
                    step_name=step.name,
                    io_type=output.artifact_save_type,
                    is_input=False,
                ),
                id=output.artifact_id,
                name=output.name,
                type=output.artifact_type,
                data_type=Source.model_validate_json(
                    output.artifact_data_type
                ).import_path,
                save_type=output.artifact_save_type,
            )
            helper.add_edge(
                source=node.node_id,
                target=artifact.node_id,
                output_name=output.name,
                type=output.artifact_save_type,
            )
            if output.artifact_save_type == ArtifactSaveType.STEP_OUTPUT:
                producers[output.artifact_id].append(
                    (step.id, artifact.node_id)
                )

        for triggered in step.triggered_runs:
            details = {"status": triggered.status, "index": triggered.index}
            if triggered.start_time:
                details["start_time"] = triggered.start_time.isoformat()
                if triggered.end_time:
                    details["duration"] = (
                        triggered.end_time - triggered.start_time
                    ).total_seconds()
            triggered_node = helper.add_triggered_run_node(
                node_id=helper.get_triggered_run_node_id(triggered.name),
                name=triggered.name,
                id=triggered.id,
                **details,
            )
            helper.add_edge(source=node.node_id, target=triggered_node.node_id)

    for step in steps.values():
        node_id = helper.get_step_node_id(step.name)
        for input in inputs.get(step.id, []):
            candidates = (
                [
                    output_node
                    for parent_id, output_node in producers[input.artifact_id]
                    if parent_id in parents[step.id]
                ]
                if input.type == StepRunInputArtifactType.STEP_OUTPUT
                else []
            )
            if len(candidates) == 1:
                input_node_id = candidates[0]
            else:
                # SQL links cannot disambiguate two parents or output aliases
                # publishing the same artifact. Keep that input separate rather
                # than claiming an unrecorded producer/output association.
                artifact = helper.add_artifact_node(
                    node_id=helper.get_artifact_node_id(
                        name=f"{input.name}/{input.artifact_id}",
                        step_name=step.name,
                        io_type=input.type,
                        is_input=True,
                    ),
                    id=input.artifact_id,
                    name=input.name,
                    type=input.artifact_type,
                    data_type=Source.model_validate_json(
                        input.artifact_data_type
                    ).import_path,
                    save_type=input.artifact_save_type,
                )
                input_node_id = artifact.node_id
            helper.add_edge(
                source=input_node_id,
                target=node_id,
                input_name=input.name,
                type=input.type,
                index=input.input_index,
                chunk_index=input.chunk_index,
                chunk_size=input.chunk_size,
            )
        for parent_id in parents[step.id]:
            helper.add_edge(
                source=helper.get_step_node_id(steps[parent_id].name),
                target=node_id,
            )

    return helper.finalize_dag(
        pipeline_run_id=run.id, status=ExecutionStatus(run.status)
    )
