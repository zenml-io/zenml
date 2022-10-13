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
"""GitHub Actions orchestrator flavor."""

from typing import TYPE_CHECKING, Type

from zenml.integrations.github import GITHUB_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor

if TYPE_CHECKING:
    from zenml.integrations.github.orchestrators import (
        GitHubActionsOrchestrator,
    )


class GitHubActionsOrchestratorConfig(BaseOrchestratorConfig):
    """Configuration for the GitHub Actions orchestrator.

    Attributes:
        skip_dirty_repository_check: If `True`, this orchestrator will not
            raise an exception when trying to run a pipeline while there are
            still untracked/uncommitted files in the git repository.
        skip_github_repository_check: If `True`, the orchestrator will not check
            if your git repository is pointing to a GitHub remote.
        push: If `True`, this orchestrator will automatically commit and push
            the GitHub workflow file when running a pipeline. If `False`, the
            workflow file will be written to the correct location but needs to
            be committed and pushed manually.
    """

    skip_dirty_repository_check: bool = False
    skip_github_repository_check: bool = False
    push: bool = False

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        This designation is used to determine if the stack component can be
        used with a local ZenML database or if it requires a remote ZenML
        server.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return True


class GitHubActionsOrchestratorFlavor(BaseOrchestratorFlavor):
    """GitHub Actions orchestrator flavor."""

    @property
    def name(self) -> str:
        """Name of the orchestrator flavor.

        Returns:
            Name of the orchestrator flavor.
        """
        return GITHUB_ORCHESTRATOR_FLAVOR

    @property
    def config_class(self) -> Type[GitHubActionsOrchestratorConfig]:
        """Returns `GitHubActionsOrchestratorConfig` config class.

        Returns:
                The config class.
        """
        return GitHubActionsOrchestratorConfig

    @property
    def implementation_class(self) -> Type["GitHubActionsOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.github.orchestrators import (
            GitHubActionsOrchestrator,
        )

        return GitHubActionsOrchestrator
