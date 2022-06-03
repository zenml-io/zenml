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
from typing import ClassVar, List, Optional

import requests
from requests.auth import HTTPBasicAuth

from zenml.entrypoints.step_entrypoint_configuration import (
    _b64_decode,
    _b64_encode,
)
from zenml.integrations.github import GITHUB_SECRET_MANAGER_FLAVOR
from zenml.logger import get_logger
from zenml.secret import BaseSecretSchema
from zenml.secret.secret_schema_class_registry import SecretSchemaClassRegistry
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager

logger = get_logger(__name__)

from base64 import b64encode


def encrypt(public_key: str, secret_value: str) -> str:
    """Encrypt a Unicode string using the public key."""
    from nacl import encoding, public

    public_key = public.PublicKey(
        public_key.encode("utf-8"), encoding.Base64Encoder()
    )
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")


# Prefix used for ZenML secrets stored as GitHub secrets
GITHUB_SECRET_PREFIX = "__ZENML__"
# Environment variable that is set to `true` if executing in a GitHub Actions
# environment
ENV_IN_GITHUB_ACTIONS = "GITHUB_ACTIONS"


ENV_GITHUB_USERNAME = "GITHUB_USERNAME"
ENV_GITHUB_AUTHENTICATION_TOKEN = "GITHUB_AUTHENTICATION_TOKEN"


def inside_github_action_environment() -> bool:
    """Returns if the current code is executing in a GitHub Actions environment.

    Returns:
        `True` if running in a GitHub Actions environment, `False` otherwise.
    """
    return os.getenv(ENV_IN_GITHUB_ACTIONS) == "true"


class GitHubSecretsManager(BaseSecretsManager):
    """Class to interact with the GitHub secrets manager.

    Attributes:
        owner:
        repository:
    """

    owner: str
    repository: str

    # Class configuration
    FLAVOR: ClassVar[str] = GITHUB_SECRET_MANAGER_FLAVOR

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Gets the value of a secret.

        Args:
            secret_name: The name of the secret to get.

        Raises:
            RuntimeError:
            KeyError:
        """
        if not inside_github_action_environment():
            raise RuntimeError(
                "Getting GitHub secrets is only possible within a GitHub "
                "Actions workflow."
            )

        env_variable = GITHUB_SECRET_PREFIX + secret_name
        value = os.getenv(env_variable)
        if not value:
            raise KeyError(
                f"Unable to find secret '{secret_name}'. Please check the "
                "GitHub UI to see if a **Repository** secret called "
                f"'{GITHUB_SECRET_PREFIX}{secret_name}' exists. (The "
                f"'{GITHUB_SECRET_PREFIX}' to differentiate them from other "
                "GitHub secrets)"
            )

        json_string = _b64_decode(value)
        secret_dict = json.loads(json_string)

        schema_class = SecretSchemaClassRegistry.get_class(
            secret_schema=secret_dict["secret_schema"]
        )

        return schema_class(name=secret_name, **secret_dict["values"])

    def get_all_secret_keys(self, include_prefix: bool = False) -> List[str]:
        """Get all secret keys."""
        if inside_github_action_environment():
            all_keys = list(os.environ)
        else:
            logger.info(
                "Fetching list of secrets for repository %s/%s",
                self.owner,
                self.repository,
            )
            response = requests.get(
                self.secrets_api_url, auth=self._authentication_credentials
            )
            secrets = response.json()["secrets"]
            all_keys = [secret_dict["name"] for secret_dict in secrets]

        keys = [
            key if include_prefix else key[len(GITHUB_SECRET_PREFIX) :]
            for key in all_keys
            if key.startswith(GITHUB_SECRET_PREFIX)
        ]

        return keys

    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        Args:
            secret: The secret to register.
        """
        # TODO: KeyError if exists

        secret_dict = {"secret_schema": secret.TYPE, "values": secret.content}
        json_string = json.dumps(secret_dict)
        secret_value = _b64_encode(json_string)

        public_key_response = requests.get(
            f"{self.secrets_api_url}/public-key",
            auth=self._authentication_credentials,
        ).json()
        print(public_key_response)
        encrypted_secret = encrypt(
            public_key=public_key_response["key"], secret_value=secret_value
        )
        print(encrypted_secret)
        body = {
            "encrypted_value": encrypted_secret,
            "key_id": public_key_response["key_id"],
        }
        url = f"{self.secrets_api_url}/{GITHUB_SECRET_PREFIX}{secret.name}"
        response = requests.put(
            url, json=body, auth=self._authentication_credentials
        )
        print(response.content)

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
        url = f"{self.secrets_api_url}/{GITHUB_SECRET_PREFIX}{secret_name}"
        requests.delete(url)

    def delete_all_secrets(self, force: bool = False) -> None:
        """Delete all existing secrets.

        Args:
            force: Whether to force deletion of secrets.
        """
        for secret_name in self.get_all_secret_keys():
            self.delete_secret(secret_name=secret_name)

    @property
    def secrets_api_url(self) -> str:
        return (
            f"https://api.github.com/repos/{self.owner}/{self.repository}"
            "/actions/secrets"
        )

    @property
    def _authentication_credentials(self) -> HTTPBasicAuth:
        github_username = os.getenv(ENV_GITHUB_USERNAME)
        authentication_token = os.getenv(ENV_GITHUB_AUTHENTICATION_TOKEN)

        if not github_username or not authentication_token:
            raise RuntimeError

        return HTTPBasicAuth(github_username, authentication_token)

    @property
    def post_registration_message(self) -> Optional[str]:
        """Prints information regarding the required environment variables to
        authenticate with the GitHub API."""
        return None
