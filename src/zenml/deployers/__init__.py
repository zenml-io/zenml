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
"""Deployers are stack components responsible for deploying pipelines as HTTP services.

Deploying pipelines is the process of hosting and running machine-learning
pipelines as part of a managed web service and providing access to pipeline
execution through an API endpoint like HTTP or GRPC. Once deployed, you can send
execution requests to the pipeline through the web service's API and receive
responses containing the pipeline results or execution status.

Add a deployer to your ZenML stack to be able to provision pipelines deployments
that transform your ML pipelines into long-running HTTP services
for real-time, on-demand execution instead of traditional batch processing.

When present in a stack, the deployer also acts as a registry for pipeline
endpoints that are deployed with ZenML. You can use the deployer to list all
deployments that are currently provisioned for online execution or filtered
according to a particular snapshot or configuration, or to delete an external
deployment managed through ZenML.
"""

from zenml.deployers.base_deployer import (
    BaseDeployer,
    BaseDeployerFlavor,
    BaseDeployerConfig,
)
from zenml.deployers.containerized_deployer import (
    ContainerizedDeployer,
)
from zenml.deployers.docker.docker_deployer import (
    DockerDeployer,
    DockerDeployerConfig,
    DockerDeployerFlavor,
    DockerDeployerSettings,
)
from zenml.deployers.local.local_deployer import (
    LocalDeployer,
    LocalDeployerConfig,
    LocalDeployerFlavor,
    LocalDeployerSettings,
)

__all__ = [
    "BaseDeployer",
    "BaseDeployerFlavor",
    "BaseDeployerConfig",
    "ContainerizedDeployer",
    "DockerDeployer",
    "DockerDeployerConfig",
    "DockerDeployerFlavor",
    "DockerDeployerSettings",
    "LocalDeployer",
    "LocalDeployerConfig",
    "LocalDeployerFlavor",
    "LocalDeployerSettings",
]
