#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Class for lineage graph generation."""

from typing import TYPE_CHECKING, List, Optional, Tuple, Union

from pydantic import BaseModel

from zenml.enums import ExecutionStatus
from zenml.lineage_graph.edge import Edge
from zenml.lineage_graph.node import (
    ArtifactNode,
    ArtifactNodeDetails,
    StepNode,
    StepNodeDetails,
)
from zenml.lineage_graph.node.artifact_node import ArtifactNodeStatus

if TYPE_CHECKING:
    from zenml.models import (
        ArtifactVersionResponse,
        PipelineRunResponse,
        StepRunResponse,
    )


ARTIFACT_PREFIX = "artifact_"
STEP_PREFIX = "step_"


class LineageGraph(BaseModel):
    """A lineage graph representation of a PipelineRunResponseModel."""

    nodes: List[Union[StepNode, ArtifactNode]] = []
    edges: List[Edge] = []
    root_step_id: Optional[str] = None
    run_metadata: List[Tuple[str, str, str]] = []

    def generate_run_nodes_and_edges(self, run: "PipelineRunResponse") -> None:
        """Initializes a lineage graph from a pipeline run.

        Args:
            run: The PipelineRunResponseModel to generate the lineage graph for.
        """
        self.run_metadata = [
            (m.key, str(m.value), str(m.type))
            for m in run.run_metadata.values()
        ]

        for step in run.steps.values():
            self.generate_step_nodes_and_edges(step)

        self.add_external_artifacts(run)
        self.add_direct_edges(run)

    def generate_step_nodes_and_edges(self, step: "StepRunResponse") -> None:
        """Generates the nodes and edges for a step and its artifacts.

        Args:
            step: The step to generate the nodes and edges for.
        """
        step_id = STEP_PREFIX + str(step.id)

        # Set a root step if it doesn't exist yet
        if self.root_step_id is None:
            self.root_step_id = step_id

        # Add the step node
        self.add_step_node(step, step_id)

        # Add nodes and edges for all output artifacts
        for artifact_name, artifact_version in step.outputs.items():
            artifact_version_id = ARTIFACT_PREFIX + str(artifact_version.id)
            if step.status == ExecutionStatus.CACHED:
                artifact_status = ArtifactNodeStatus.CACHED
            elif step.status == ExecutionStatus.COMPLETED:
                artifact_status = ArtifactNodeStatus.CREATED
            else:
                artifact_status = ArtifactNodeStatus.UNKNOWN
            self.add_artifact_node(
                artifact=artifact_version,
                id=artifact_version_id,
                name=artifact_name,
                step_id=str(step_id),
                status=artifact_status,
            )
            self.add_edge(step_id, artifact_version_id)

        # Add nodes and edges for all input artifacts
        for artifact_name, artifact_version in step.inputs.items():
            artifact_version_id = ARTIFACT_PREFIX + str(artifact_version.id)
            self.add_edge(artifact_version_id, step_id)

    def add_external_artifacts(self, run: "PipelineRunResponse") -> None:
        """Adds all external artifacts to the lineage graph.

        Args:
            run: The pipeline run to add external artifacts for.
        """
        nodes_ids = {node.id for node in self.nodes}
        for step in run.steps.values():
            for artifact_name, artifact_version in step.inputs.items():
                artifact_version_id = ARTIFACT_PREFIX + str(
                    artifact_version.id
                )
                if artifact_version_id not in nodes_ids:
                    self.add_artifact_node(
                        artifact=artifact_version,
                        id=artifact_version_id,
                        name=artifact_name,
                        step_id=str(artifact_version.producer_step_run_id),
                        status=ArtifactNodeStatus.EXTERNAL,
                    )

    def add_direct_edges(self, run: "PipelineRunResponse") -> None:
        """Add all direct edges between nodes generated by `after=...`.

        Args:
            run: The pipeline run to add direct edges for.
        """
        for step in run.steps.values():
            step_id = STEP_PREFIX + str(step.id)
            for parent_step_id_uuid in step.parent_step_ids:
                parent_step_id = STEP_PREFIX + str(parent_step_id_uuid)
                if not self.has_artifact_link(step_id, parent_step_id):
                    self.add_edge(parent_step_id, step_id)

    def has_artifact_link(self, step_id: str, parent_step_id: str) -> bool:
        """Checks if a step has an artifact link to a parent step.

        This is the case for all parent steps that were not specified via
        `after=...`.

        Args:
            step_id: The node ID of the step to check.
            parent_step_id: T node ID of the parent step to check.

        Returns:
            True if the steps are linked via an artifact, False otherwise.
        """
        parent_outputs, child_inputs = set(), set()
        for edge in self.edges:
            if edge.source == parent_step_id:
                parent_outputs.add(edge.target)
            if edge.target == step_id:
                child_inputs.add(edge.source)
        return bool(parent_outputs.intersection(child_inputs))

    def add_step_node(
        self,
        step: "StepRunResponse",
        id: str,
    ) -> None:
        """Adds a step node to the lineage graph.

        Args:
            step: The step to add a node for.
            id: The id of the step node.
        """
        step_config = step.config.model_dump()
        if step_config:
            step_config = {
                key: value
                for key, value in step_config.items()
                if key not in ["inputs", "outputs", "parameters"] and value
            }
        self.nodes.append(
            StepNode(
                id=id,
                data=StepNodeDetails(
                    execution_id=str(step.id),
                    name=step.name,  # redundant for consistency
                    status=step.status,
                    entrypoint_name=step.config.name,  # redundant for consistency
                    parameters=step.config.parameters,
                    configuration=step_config,
                    inputs={k: v.uri for k, v in step.inputs.items()},
                    outputs={k: v.uri for k, v in step.outputs.items()},
                    metadata=[
                        (m.key, str(m.value), str(m.type))
                        for m in step.run_metadata.values()
                    ],
                ),
            )
        )

    def add_artifact_node(
        self,
        artifact: "ArtifactVersionResponse",
        id: str,
        name: str,
        step_id: str,
        status: ArtifactNodeStatus,
    ) -> None:
        """Adds an artifact node to the lineage graph.

        Args:
            artifact: The artifact to add a node for.
            id: The id of the artifact node.
            name: The input or output name of the artifact.
            step_id: The id of the step that produced the artifact.
            status: The status of the step that produced the artifact.
        """
        node = ArtifactNode(
            id=id,
            data=ArtifactNodeDetails(
                execution_id=str(artifact.id),
                name=name,
                status=status,
                is_cached=status == ArtifactNodeStatus.CACHED,
                artifact_type=artifact.type,
                artifact_data_type=artifact.data_type.import_path,
                parent_step_id=step_id,
                producer_step_id=str(artifact.producer_step_run_id),
                uri=artifact.uri,
                metadata=[
                    (m.key, str(m.value), str(m.type))
                    for m in artifact.run_metadata.values()
                ],
            ),
        )
        self.nodes.append(node)

    def add_edge(self, source: str, target: str) -> None:
        """Adds an edge to the lineage graph.

        Args:
            source: The source node id.
            target: The target node id.
        """
        self.edges.append(
            Edge(id=source + "_" + target, source=source, target=target)
        )
