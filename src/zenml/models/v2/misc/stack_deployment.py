#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Models related to cloud stack deployments."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from zenml.enums import StackDeploymentProvider
from zenml.models.v2.core.service_connector import ServiceConnectorResponse
from zenml.models.v2.core.stack import StackResponse


class StackDeploymentInfo(BaseModel):
    """Information about a stack deployment."""

    provider: StackDeploymentProvider = Field(
        title="The provider of the stack deployment."
    )
    description: str = Field(
        title="The description of the stack deployment.",
        description="The description of the stack deployment.",
    )
    instructions: str = Field(
        title="The instructions for deploying the stack.",
        description="The instructions for deploying the stack.",
    )
    post_deploy_instructions: str = Field(
        title="The instructions for post-deployment.",
        description="The instructions for post-deployment.",
    )
    permissions: Dict[str, List[str]] = Field(
        title="The permissions granted to ZenML to access the cloud resources.",
        description="The permissions granted to ZenML to access the cloud "
        "resources, as a dictionary grouping permissions by resource.",
    )
    locations: Dict[str, str] = Field(
        title="The locations where the stack can be deployed.",
        description="The locations where the stack can be deployed, as a "
        "dictionary mapping location names to descriptions.",
    )


class StackDeploymentConfig(BaseModel):
    """Configuration about a stack deployment."""

    deployment_url: str = Field(
        title="The cloud provider console URL where the stack will be deployed.",
    )
    deployment_url_text: str = Field(
        title="A textual description for the cloud provider console URL.",
    )
    configuration: Optional[str] = Field(
        title="Configuration for the stack deployment that the user must "
        "manually configure into the cloud provider console.",
    )


class DeployedStack(BaseModel):
    """Information about a deployed stack."""

    stack: StackResponse = Field(
        title="The stack that was deployed.",
        description="The stack that was deployed.",
    )
    service_connector: Optional[ServiceConnectorResponse] = Field(
        default=None,
        title="The service connector for the deployed stack.",
        description="The service connector for the deployed stack.",
    )
