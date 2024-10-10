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
"""Class for all lineage step nodes."""

from typing import Any, Dict, List, Tuple

from zenml.enums import ExecutionStatus
from zenml.lineage_graph.node.base_node import (
    BaseNode,
    BaseNodeDetails,
)


class StepNodeDetails(BaseNodeDetails):
    """Captures all artifact details for the node."""

    status: ExecutionStatus
    entrypoint_name: str
    parameters: Dict[str, Any]
    configuration: Dict[str, Any]
    inputs: Dict[str, str]  # (key, uri)
    outputs: Dict[str, List[str]]  # (key, [uris,...])
    metadata: List[Tuple[str, str, str]]  # (key, value, type)


class StepNode(BaseNode):
    """A class that represents a step node in a lineage graph."""

    type: str = "step"
    data: StepNodeDetails
