#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""DAG generator helper."""

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from zenml.enums import ExecutionStatus
from zenml.models import PipelineRunDAG


class DAGGeneratorHelper:
    """Helper class for generating pipeline run DAGs."""

    def __init__(self) -> None:
        """Initialize the DAG generator helper."""
        self.step_nodes: Dict[UUID, PipelineRunDAG.Node] = {}
        self.artifact_nodes: Dict[UUID, PipelineRunDAG.Node] = {}
        self.edges: List[PipelineRunDAG.Edge] = []

    def add_step_node(
        self,
        name: str,
        id: Optional[UUID] = None,
        node_id: Optional[UUID] = None,
        **metadata: Any,
    ) -> PipelineRunDAG.Node:
        """Add a step node to the DAG.

        Args:
            name: The name of the step.
            id: The ID of the step.
            node_id: The ID of the node.
            **metadata: Additional node metadata.

        Returns:
            The added step node.
        """
        step_node = PipelineRunDAG.Node(
            type="step",
            node_id=node_id or uuid4(),
            id=id,
            name=name,
            metadata=metadata,
        )
        self.step_nodes[step_node.node_id] = step_node
        return step_node

    def add_artifact_node(
        self,
        name: str,
        id: Optional[UUID] = None,
        node_id: Optional[UUID] = None,
        **metadata: Any,
    ) -> PipelineRunDAG.Node:
        """Add an artifact node to the DAG.

        Args:
            name: The name of the artifact.
            id: The ID of the artifact.
            node_id: The ID of the node.
            **metadata: Additional node metadata.

        Returns:
            The added artifact node.
        """
        artifact_node = PipelineRunDAG.Node(
            type="artifact",
            node_id=node_id or uuid4(),
            id=id,
            name=name,
            metadata=metadata,
        )
        self.artifact_nodes[artifact_node.node_id] = artifact_node
        return artifact_node

    def add_edge(self, source: UUID, target: UUID, **metadata: Any) -> None:
        """Add an edge to the DAG.

        Args:
            source: The source node ID.
            target: The target node ID.
            metadata: Additional edge metadata.
        """
        self.edges.append(
            PipelineRunDAG.Edge(
                source=source, target=target, metadata=metadata
            )
        )

    def get_step_node_by_name(self, name: str) -> PipelineRunDAG.Node:
        """Get a step node by name.

        Args:
            name: The name of the step.

        Raises:
            KeyError: If the step node with the given name is not found.

        Returns:
            The step node.
        """
        for node in self.step_nodes.values():
            if node.name == name:
                return node
        raise KeyError(f"Step node with name {name} not found")

    def finalize_dag(
        self, pipeline_run_id: UUID, status: ExecutionStatus
    ) -> PipelineRunDAG:
        """Finalize the DAG.

        Args:
            pipeline_run_id: The ID of the pipeline run.
            status: The status of the pipeline run.

        Returns:
            The finalized DAG.
        """
        return PipelineRunDAG(
            id=pipeline_run_id,
            status=status,
            nodes=list(self.step_nodes.values())
            + list(self.artifact_nodes.values()),
            edges=self.edges,
        )
