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
"""Pipeline run DAG models."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from zenml.enums import ExecutionStatus


class PipelineRunDAG(BaseModel):
    """Pipeline run DAG."""

    id: UUID
    status: ExecutionStatus
    nodes: List["Node"]
    edges: List["Edge"]

    class Node(BaseModel):
        """Node in the pipeline run DAG."""

        node_id: str
        type: str
        id: Optional[UUID] = None
        name: str
        metadata: Dict[str, Any] = {}

    class Edge(BaseModel):
        """Edge in the pipeline run DAG."""

        source: str
        target: str
        metadata: Dict[str, Any] = {}
