#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""
A container registry is a store for (Docker) containers. A ZenML workflow
involving a container registry would automatically containerize your code to
be transported across stacks running remotely. As part of the deployment to
the cluster, the ZenML base image would be downloaded (from a cloud container
registry) and used as the basis for the deployed 'run'.

For instance, when you are running a local container-based stack, you would
therefore have a local container registry which stores the container images
you create that bundle up your pipeline code. You could also use a remote
container registry like the Elastic Container Registry at AWS in a more
production setting.
"""
from zenml.container_registries.azure_container_registry import (
    AzureContainerRegistry,
)
from zenml.container_registries.base_container_registry import (
    BaseContainerRegistry,
)
from zenml.container_registries.default_container_registry import (
    DefaultContainerRegistry,
)
from zenml.container_registries.dockerhub_container_registry import (
    DockerHubContainerRegistry,
)
from zenml.container_registries.gcp_container_registry import (
    GCPContainerRegistry,
)
from zenml.container_registries.github_container_registry import (
    GitHubContainerRegistry,
)
from zenml.container_registries.gitlab_container_registry import (
    GitLabContainerRegistry,
)

__all__ = [
    "BaseContainerRegistry",
    "DefaultContainerRegistry",
    "AzureContainerRegistry",
    "DockerHubContainerRegistry",
    "GCPContainerRegistry",
    "GitLabContainerRegistry",
    "GitHubContainerRegistry",
]
