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
"""Class for all lineage artifact nodes."""


from typing import Optional

from zenml.post_execution.lineage.node.base_node import (
    BaseNode,
    BaseNodeDetails,
)


class ArtifactNodeDetails(BaseNodeDetails):
    """Captures all artifact details for the node."""

    is_cached: bool
    artifact_type: str
    artifact_data_type: str
    parent_step_id: str
    producer_step_id: Optional[str]
    uri: str


class ArtifactNode(BaseNode):
    """A class that represents an artifact node in a lineage graph."""

    type: str = "artifact"
    data: ArtifactNodeDetails
