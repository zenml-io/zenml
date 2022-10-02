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
"""Implementation of the GitHub Secrets Manager."""

import base64
import json
import os
from typing import Any, List, NoReturn, Optional, Tuple, cast

import requests
from requests.auth import HTTPBasicAuth

from zenml.client import Client
from zenml.exceptions import SecretExistsError
from zenml.integrations.github.flavors.github_secrets_manager_flavor import (
    GitHubSecretsManagerConfig,
)
from zenml.logger import get_logger
from zenml.secret import BaseSecretSchema
from zenml.secret.secret_schema_class_registry import SecretSchemaClassRegistry
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager
from zenml.utils import string_utils

logger = get_logger(__name__)


# Prefix used for ZenML secrets stored as GitHub secrets
GITHUB_SECRET_PREFIX = "__ZENML__"
# Environment variable that is set to `true` if executing in a GitHub Actions
# environment
ENV_IN_GITHUB_ACTIONS = "GITHUB_ACTIONS"

# Environment variables used to authenticate with the GitHub API
ENV_GITHUB_USERNAME = "GITHUB_USERNAME"
ENV_GITHUB_AUTHENTICATION_TOKEN = "GITHUB_AUTHENTICATION_TOKEN"

AUTHENTICATION_CREDENTIALS_MESSAGE = (
    "In order to use this secrets manager outside of a GitHub Actions "
    "environment, you need to provide authentication credentials using the "
    f"`{ENV_GITHUB_USERNAME}` and `{ENV_GITHUB_AUTHENTICATION_TOKEN}` "
    "environment variables. Check out https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token "
    "for more information on how to create the authentication token."
)

# Dictionary keys used for serializing a secret schema to a json string
SECRET_SCHEMA_DICT_KEY = "schema"
SECRET_CONTENT_DICT_KEY = "content"


def inside_github_action_environment() -> bool:
    """Returns if the current code is executing in a GitHub Actions environment.

    Returns:
        `True` if running in a GitHub Actions environment, `False` otherwise.
    """
    return os.getenv(ENV_IN_GITHUB_ACTIONS) == "true"


def _convert_secret_name(
    secret_name: str, add_prefix: bool = False, remove_prefix: bool = False
) -> str:
    """Converts a secret name to upper case and adds/removes the ZenML prefix.

    Args:
        secret_name: The secret name to convert.
        add_prefix: If `True`, the ZenML GitHub secret prefix is added to
            the secret name.
        remove_prefix: If `True`, the ZenML GitHub secret prefix is removed
            from the secret name.

    Returns:
        The converted secret name.
    """
    if remove_prefix and secret_name.startswith(GITHUB_SECRET_PREFIX):
        secret_name = secret_name[len(GITHUB_SECRET_PREFIX) :]

    secret_name = secret_name.upper()

    if add_prefix:
        secret_name = GITHUB_SECRET_PREFIX + secret_name

    return secret_name


class GitHubSecretsManager(BaseSecretsManager):
    """Class to interact with the GitHub secrets manager."""

    _session: Optional[requests.Session] = None

    @property
    def config(self) -> GitHubSecretsManagerConfig:
        """Returns the `GitHubSecretsManagerConfig` config.

        Returns:
            The configuration.
        """
        return cast(GitHubSecretsManagerConfig, self._config)

    @property
    def post_registration_message(self) -> Optional[str]:
        """Info message regarding GitHub API authentication env variables.

        Returns:
            The info message.
        """
        return AUTHENTICATION_CREDENTIALS_MESSAGE

    @property
    def session(self) -> requests.Session:
        """Session to send requests to the GitHub API.

        Returns:
            Session to use for GitHub API calls.

        Raises:
            RuntimeError: If authentication credentials for the GitHub API are
                not set.
        """
        if not self._session:
            session = requests.Session()
            github_username = os.getenv(ENV_GITHUB_USERNAME)
            authentication_token = os.getenv(ENV_GITHUB_AUTHENTICATION_TOKEN)

            if not github_username or not authentication_token:
                raise RuntimeError(
                    "Missing authentication credentials for GitHub secrets "
                    "manager. " + AUTHENTICATION_CREDENTIALS_MESSAGE
                )

            session.auth = HTTPBasicAuth(github_username, authentication_token)
            session.headers["Accept"] = "application/vnd.github.v3+json"
            self._session = session

        return self._session

    def _send_request(
        self, method: str, resource: Optional[str] = None, **kwargs: Any
    ) -> requests.Response:
        """Sends an HTTP request to the GitHub API.

        Args:
            method: Method of the HTTP request that should be sent.
            resource: Optional resource to which the request should be sent. If
                none is given, the default GitHub API secrets endpoint will be
                used.
            **kwargs: Will be passed to the `requests` library.

        Returns:
            HTTP response.

        # noqa: DAR402

        Raises:
            HTTPError: If the request failed due to a client or server error.
        """
        url = (
            f"https://api.github.com/repos/{self.config.owner}"
            f"/{self.config.repository}/actions/secrets"
        )
        if resource:
            url += resource

        response = self.session.request(method=method, url=url, **kwargs)
        # Raise an exception in case of a client or server error
        response.raise_for_status()

        return response

    def _encrypt_secret(self, secret_value: str) -> Tuple[str, str]:
        """Encrypts a secret value.

        This method first fetches a public key from the GitHub API and then uses
        this key to encrypt the secret value. This is needed in order to
        register GitHub secrets using the API.

        Args:
            secret_value: Secret value to encrypt.

        Returns:
            The encrypted secret value and the key id of the GitHub public key.
        """
        from nacl.encoding import Base64Encoder
        from nacl.public import PublicKey, SealedBox

        response_json = self._send_request("GET", resource="/public-key").json()
        public_key = PublicKey(
            response_json["key"].encode("utf-8"), Base64Encoder
        )
        sealed_box = SealedBox(public_key)
        encrypted_bytes = sealed_box.encrypt(secret_value.encode("utf-8"))
        encrypted_string = base64.b64encode(encrypted_bytes).decode("utf-8")
        return encrypted_string, cast(str, response_json["key_id"])

    def _has_secret(self, secret_name: str) -> bool:
        """Checks whether a secret exists for the given name.

        Args:
            secret_name: Name of the secret which should be checked.

        Returns:
            `True` if a secret with the given name exists, `False` otherwise.
        """
        secret_name = _convert_secret_name(secret_name, remove_prefix=True)
        return secret_name in self.get_all_secret_keys(include_prefix=False)

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Gets the value of a secret.

        This method only works when called from within a GitHub Actions
        environment.

        Args:
            secret_name: The name of the secret to get.

        Returns:
            The secret.

        Raises:
            KeyError: If a secret with this name doesn't exist.
            RuntimeError: If not inside a GitHub Actions environments.
        """
        full_secret_name = _convert_secret_name(secret_name, add_prefix=True)
        # Raise a KeyError if the secret doesn't exist. We can do that even
        # if we're not inside a GitHub Actions environment
        if not self._has_secret(secret_name):
            raise KeyError(
                f"Unable to find secret '{secret_name}'. Please check the "
                "GitHub UI to see if a **Repository** secret called "
                f"'{full_secret_name}' exists. (ZenML uses the "
                f"'{GITHUB_SECRET_PREFIX}' to differentiate ZenML "
                "secrets from other GitHub secrets)"
            )

        if not inside_github_action_environment():
            stack_name = Client().active_stack_model.name
            commands = [
                f"zenml stack copy {stack_name} <NEW_STACK_NAME>",
                "zenml secrets_manager register <NEW_SECRETS_MANAGER_NAME> "
                "--flavor=local",
                "zenml stack update <NEW_STACK_NAME> "
                "--secrets_manager=<NEW_SECRETS_MANAGER_NAME>",
                "zenml stack set <NEW_STACK_NAME>",
                f"zenml secrets-manager secret register {secret_name} ...",
            ]

            raise RuntimeError(
                "Getting GitHub secrets is only possible within a GitHub "
                "Actions workflow. If you need this secret to access "
                "stack components locally, you need to "
                "register this secret in a different secrets manager. "
                "You can do this by running the following commands: \n\n"
                + "\n".join(commands)
            )

        # If we're running inside an GitHub Actions environment using the a
        # workflow generated by the GitHub Actions orchestrator, all ZenML
        # secrets stored in the GitHub secrets manager will be accessible as
        # environment variables
        secret_value = cast(str, os.getenv(full_secret_name))

        secret_dict = json.loads(string_utils.b64_decode(secret_value))
        schema_class = SecretSchemaClassRegistry.get_class(
            secret_schema=secret_dict[SECRET_SCHEMA_DICT_KEY]
        )
        secret_content = secret_dict[SECRET_CONTENT_DICT_KEY]

        return schema_class(name=secret_name, **secret_content)

    def get_all_secret_keys(self, include_prefix: bool = False) -> List[str]:
        """Get all secret keys.

        If we're running inside a GitHub Actions environment, this will return
        the names of all environment variables starting with a ZenML internal
        prefix. Otherwise, this will return all GitHub **Repository** secrets
        created by ZenML.

        Args:
            include_prefix: Whether or not the internal prefix that is used to
                differentiate ZenML secrets from other GitHub secrets should be
                included in the returned names.

        Returns:
            List of all secret keys.
        """
        if inside_github_action_environment():
            potential_secret_keys = list(os.environ)
        else:
            logger.info(
                "Fetching list of secrets for repository %s/%s",
                self.config.owner,
                self.config.repository,
            )
            response = self._send_request("GET", params={"per_page": 100})
            potential_secret_keys = [
                secret_dict["name"]
                for secret_dict in response.json()["secrets"]
            ]

        keys = [
            _convert_secret_name(key, remove_prefix=not include_prefix)
            for key in potential_secret_keys
            if key.startswith(GITHUB_SECRET_PREFIX)
        ]

        return keys

    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        Args:
            secret: The secret to register.

        Raises:
            SecretExistsError: If a secret with this name already exists.
        """
        if self._has_secret(secret.name):
            raise SecretExistsError(
                f"A secret with name '{secret.name}' already exists for this "
                "GitHub repository. If you want to register a new value for "
                f"this secret, please run `zenml secrets-manager secret delete {secret.name}` "
                f"followed by `zenml secrets-manager secret register {secret.name} ...`."
            )

        secret_dict = {
            SECRET_SCHEMA_DICT_KEY: secret.TYPE,
            SECRET_CONTENT_DICT_KEY: secret.content,
        }
        secret_value = string_utils.b64_encode(json.dumps(secret_dict))
        encrypted_secret, public_key_id = self._encrypt_secret(
            secret_value=secret_value
        )
        body = {
            "encrypted_value": encrypted_secret,
            "key_id": public_key_id,
        }

        full_secret_name = _convert_secret_name(secret.name, add_prefix=True)
        self._send_request("PUT", resource=f"/{full_secret_name}", json=body)

    def update_secret(self, secret: BaseSecretSchema) -> NoReturn:
        """Update an existing secret.

        Args:
            secret: The secret to update.

        Raises:
            NotImplementedError: Always, as this functionality is not possible
                using GitHub secrets which doesn't allow us to retrieve the
                secret values outside of a GitHub Actions environment.
        """
        raise NotImplementedError(
            "Updating secrets is not possible with the GitHub secrets manager "
            "as it is not possible to retrieve GitHub secrets values outside "
            "of a GitHub Actions environment."
        )

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret.

        Args:
            secret_name: The name of the secret to delete.
        """
        full_secret_name = _convert_secret_name(secret_name, add_prefix=True)
        self._send_request("DELETE", resource=f"/{full_secret_name}")

    def delete_all_secrets(self) -> None:
        """Delete all existing secrets."""
        for secret_name in self.get_all_secret_keys(include_prefix=False):
            self.delete_secret(secret_name=secret_name)
