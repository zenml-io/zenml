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

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.github import GITHUB_ORCHESTRATOR_FLAVOR
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor
from zenml.utils import deprecation_utils

if TYPE_CHECKING:
    from zenml.integrations.github.orchestrators import (
        GitHubActionsOrchestrator,
    )


class GitHubActionsOrchestratorConfig(BaseOrchestratorConfig):
    """Configuration for the GitHub Actions orchestrator.

    Attributes:
        custom_docker_base_image_name: Name of a docker image that should be
            used as the base for the image that will be run on GitHub Action
            runners. If no custom image is given, a basic image of the active
            ZenML version will be used. **Note**: This image needs to have
            ZenML installed, otherwise the pipeline execution will fail. For
            that reason, you might want to extend the ZenML docker images
            found here: https://hub.docker.com/r/zenmldocker/zenml/
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

    custom_docker_base_image_name: Optional[str] = None
    skip_dirty_repository_check: bool = False
    skip_github_repository_check: bool = False
    push: bool = False

    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes(
        ("custom_docker_base_image_name", "docker_parent_image")
    )


class GitHubActionsOrchestratorFlavor(BaseOrchestratorFlavor):
    """GitHub Actions orchestrator flavor."""

    @property
    def name(self) -> str:
        return GITHUB_ORCHESTRATOR_FLAVOR

    @property
    def config_class(self) -> Type[GitHubActionsOrchestratorConfig]:
        return GitHubActionsOrchestratorConfig

    @property
    def implementation_class(self) -> Type["GitHubActionsOrchestrator"]:
        from zenml.integrations.github.orchestrators import (
            GitHubActionsOrchestrator,
        )

        return GitHubActionsOrchestrator
