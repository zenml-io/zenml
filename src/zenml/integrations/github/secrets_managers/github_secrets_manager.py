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
import json
import os
import subprocess
from typing import ClassVar, List

from zenml.integrations.github import GITHUB_SECRET_MANAGER_FLAVOR
from zenml.logger import get_logger
from zenml.secret import ArbitrarySecretSchema, BaseSecretSchema
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager

logger = get_logger(__name__)

GITHUB_SECRET_PREFIX = "__ZENML__"
ENV_IN_GITHUB_ACTIONS = "GITHUB_ACTIONS"


def inside_github_action_environment() -> bool:
    """Returns if the current code is executing in a GitHub Actions environment.

    Returns:
        `True` if running in a GitHub Actions environment, `False` otherwise.
    """
    return os.getenv(ENV_IN_GITHUB_ACTIONS) == "true"


class GitHubSecretsManager(BaseSecretsManager):
    """Class to interact with the GitHub secrets manager."""

    # TODO: git_repository: Optional[str] = None

    # Class configuration
    FLAVOR: ClassVar[str] = GITHUB_SECRET_MANAGER_FLAVOR

    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        Args:
            secret: The secret to register.
        """
        raise NotImplementedError()

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Gets the value of a secret.

        Args:
            secret_name: The name of the secret to get.
        """
        if not inside_github_action_environment():
            raise RuntimeError(
                "Getting secrets is only possible within GitHub Actions "
                "environment"
            )

        env_variable = GITHUB_SECRET_PREFIX + secret_name
        value = os.getenv(env_variable)
        if not value:
            raise KeyError()

        return ArbitrarySecretSchema(
            name=secret_name, arbitrary_kv_pairs={"key": value}
        )

    def get_all_secret_keys(self, include_prefix: bool = False) -> List[str]:
        """Get all secret keys."""
        if inside_github_action_environment():
            all_keys = list(os.environ)
        else:
            response = subprocess.check_output(
                ["gh", "api", "/repos/zenml-io/zenml/actions/secrets"]
            )
            gh_secrets = json.loads(response.decode())["secrets"]
            all_keys = [secret_dict["name"] for secret_dict in gh_secrets]

        keys = [
            key if include_prefix else key[len(GITHUB_SECRET_PREFIX) :]
            for key in all_keys
            if key.startswith(GITHUB_SECRET_PREFIX)
        ]

        return keys

    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret.

        Args:
            secret: The secret to update.
        """
        raise NotImplementedError()

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret.

        Args:
            secret_name: The name of the secret to delete.
        """
        raise NotImplementedError()

    def delete_all_secrets(self, force: bool = False) -> None:
        """Delete all existing secrets.

        Args:
            force: Whether to force deletion of secrets.
        """
        raise NotImplementedError()
