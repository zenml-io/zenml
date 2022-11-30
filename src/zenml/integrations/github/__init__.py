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
"""Initialization of the GitHub ZenML integration.

The GitHub integration provides a way to orchestrate pipelines using GitHub 
Actions.
"""
from typing import List, Type

from zenml.enums import StackComponentType
from zenml.integrations.constants import GITHUB
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

GITHUB_SECRET_MANAGER_FLAVOR = "github"
GITHUB_ORCHESTRATOR_FLAVOR = "github"


class GitHubIntegration(Integration):
    """Definition of GitHub integration for ZenML."""

    NAME = GITHUB
    REQUIREMENTS: List[str] = ["PyNaCl~=1.5.0"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the GitHub integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.github.flavors import (
            GitHubActionsOrchestratorFlavor,
            GitHubSecretsManagerFlavor,
        )

        return [GitHubActionsOrchestratorFlavor, GitHubSecretsManagerFlavor]


GitHubIntegration.check_installation()
