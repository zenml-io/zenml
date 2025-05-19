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
from zenml.models.v2.misc.pipeline_run_dag import Edge, Node, PipelineRunDAG


class DAGGeneratorHelper:
    def __init__(self) -> None:
        self.step_nodes: Dict[UUID, Node] = {}
        self.artifact_nodes: Dict[UUID, Node] = {}
        self.edges: List[Edge] = []

    def add_step_node(
        self,
        name: str,
        id: Optional[UUID] = None,
        node_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Node:
        step_node = Node(
            type="step",
            node_id=node_id or uuid4(),
            id=id,
            name=name,
            metadata=kwargs,
        )
        self.step_nodes[step_node.node_id] = step_node
        return step_node

    def add_artifact_node(
        self,
        name: str,
        id: Optional[UUID] = None,
        node_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Node:
        artifact_node = Node(
            type="artifact",
            node_id=node_id or uuid4(),
            id=id,
            name=name,
            metadata=kwargs,
        )
        self.artifact_nodes[artifact_node.node_id] = artifact_node
        return artifact_node

    def add_edge(
        self, source: UUID, target: UUID, type: Optional[str] = None
    ) -> None:
        self.edges.append(Edge(source=source, target=target, type=type))

    def get_step_node_by_id(self, id: UUID) -> Node:
        for node in self.step_nodes.values():
            if node.id == id:
                return node
        raise KeyError(f"Step node with id {id} not found")

    def get_step_node_by_name(self, name: str) -> Node:
        for node in self.step_nodes.values():
            if node.name == name:
                return node
        raise KeyError(f"Step node with name {name} not found")

    def finalize_dag(
        self, pipeline_run_id: UUID, status: ExecutionStatus
    ) -> PipelineRunDAG:
        return PipelineRunDAG(
            id=pipeline_run_id,
            status=status,
            nodes=list(self.step_nodes.values())
            + list(self.artifact_nodes.values()),
            edges=self.edges,
        )
