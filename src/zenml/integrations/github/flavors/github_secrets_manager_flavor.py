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
"""GitHub secrets manager flavor."""

from typing import TYPE_CHECKING, Type

from zenml.integrations.github import GITHUB_SECRET_MANAGER_FLAVOR
from zenml.secrets_managers import (
    BaseSecretsManagerConfig,
    BaseSecretsManagerFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.github.secrets_managers import GitHubSecretsManager


class GitHubSecretsManagerConfig(BaseSecretsManagerConfig):
    """The configuration for the GitHub Secrets Manager.

    Attributes:
        owner: The owner (either individual or organization) of the repository.
        repository: Name of the GitHub repository.
    """

    owner: str
    repository: str


class GitHubSecretsManagerFlavor(BaseSecretsManagerFlavor):
    """Class for the `GitHubSecretsManagerFlavor`."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return GITHUB_SECRET_MANAGER_FLAVOR

    @property
    def config_class(self) -> Type[GitHubSecretsManagerConfig]:
        """Returns `GitHubSecretsManagerConfig` config class.

        Returns:
                The config class.
        """
        return GitHubSecretsManagerConfig

    @property
    def implementation_class(self) -> Type["GitHubSecretsManager"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.github.secrets_managers import (
            GitHubSecretsManager,
        )

        return GitHubSecretsManager
