#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       https://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Functionality to deploy a ZenML stack to a cloud provider."""

from typing import Type

from zenml.enums import StackDeploymentProvider
from zenml.stack_deployments.aws_stack_deployment import (
    AWSZenMLCloudStackDeployment,
)
from zenml.stack_deployments.azure_stack_deployment import (
    AZUREZenMLCloudStackDeployment,
)
from zenml.stack_deployments.gcp_stack_deployment import (
    GCPZenMLCloudStackDeployment,
)
from zenml.stack_deployments.stack_deployment import ZenMLCloudStackDeployment

STACK_DEPLOYMENT_PROVIDERS = {
    StackDeploymentProvider.AWS: AWSZenMLCloudStackDeployment,
    StackDeploymentProvider.GCP: GCPZenMLCloudStackDeployment,
    StackDeploymentProvider.AZURE: AZUREZenMLCloudStackDeployment,
}


def get_stack_deployment_class(
    provider: StackDeploymentProvider,
) -> Type[ZenMLCloudStackDeployment]:
    """Get the ZenML Cloud Stack Deployment class for the specified provider.

    Args:
        provider: The stack deployment provider.

    Returns:
        The ZenML Cloud Stack Deployment class for the specified provider.
    """
    return STACK_DEPLOYMENT_PROVIDERS[provider]
