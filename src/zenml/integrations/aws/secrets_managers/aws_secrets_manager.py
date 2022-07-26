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
"""Implementation of the AWS Secrets Manager integration."""

import json
import re
from typing import Any, ClassVar, Dict, List, Optional

import boto3
from pydantic import validator

from zenml.exceptions import SecretExistsError
from zenml.integrations.aws import AWS_SECRET_MANAGER_FLAVOR
from zenml.logger import get_logger
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secret.secret_schema_class_registry import SecretSchemaClassRegistry
from zenml.secrets_managers.base_secrets_manager import (
    BaseSecretsManager,
    SecretsManagerScope,
)

logger = get_logger(__name__)

ZENML_SCHEMA_NAME = "zenml_schema_name"


def jsonify_secret_contents(secret: BaseSecretSchema) -> str:
    """Adds the secret type to the secret contents.

    This persists the schema type in the secrets backend, so that the correct
    SecretSchema can be retrieved when the secret is queried from the backend.

    Args:
        secret: should be a subclass of the BaseSecretSchema class

    Returns:
        jsonified dictionary containing all key-value pairs and the ZenML schema
        type
    """
    secret_contents = secret.content
    secret_contents[ZENML_SCHEMA_NAME] = secret.TYPE
    return json.dumps(secret_contents)


class AWSSecretsManager(BaseSecretsManager):
    """Class to interact with the AWS secrets manager."""

    region_name: str

    # Class configuration
    FLAVOR: ClassVar[str] = AWS_SECRET_MANAGER_FLAVOR
    CLIENT: ClassVar[Any] = None

    @validator("namespace")
    def validate_namespace(cls, namespace: Optional[str]) -> Optional[str]:
        """Pydantic validator for the namespace value.

        Args:
            namespace: The namespace value to validate.

        Returns:
            The validated namespace value.
        """
        if namespace:
            cls.validate_secret_name(namespace)
        return namespace

    @classmethod
    def _ensure_client_connected(cls, region_name: str) -> None:
        """Ensure that the client is connected to the AWS secrets manager.

        Args:
            region_name: the AWS region name
        """
        if cls.CLIENT is None:
            # Create a Secrets Manager client
            session = boto3.session.Session()
            cls.CLIENT = session.client(
                service_name="secretsmanager", region_name=region_name
            )

    @classmethod
    def validate_secret_name(cls, name: str) -> None:
        """Validate a secret name.

        AWS secret names must contain only alphanumeric characters and the
        characters /_+=.@-. The `/` character is only used internally to delimit
        scopes.

        Args:
            name: the secret name

        Raises:
            ValueError: if the secret name is invalid
        """
        if not re.fullmatch(r"[a-zA-Z0-9_+=\.@\-]+", name):
            raise ValueError(
                f"Invalid secret name or namespace '{name}'. Must contain "
                f"only alphanumeric characters and the characters _+=.@-."
            )

    def _get_scope_prefix(self) -> str:
        """Get the secret name prefix for the current scope.

        Returns:
            the secret name scope prefix
        """
        prefix = ""
        if self.scope == SecretsManagerScope.COMPONENT:
            prefix = f"zenml/{str(self.uuid)}/"
        elif self.scope == SecretsManagerScope.GLOBAL:
            prefix = "zenml/"
        elif self.scope == SecretsManagerScope.NAMESPACE:
            prefix = f"zenml/{self.namespace}/"

        return prefix

    def _get_scoped_secret_name(self, name: str) -> str:
        """Convert a ZenML secret name into an AWS scoped secret name.

        Args:
            name: the name of the secret

        Returns:
            The AWS scoped secret name
        """
        prefix = self._get_scope_prefix()
        return f"{prefix}{name}"

    def _get_unscoped_secret_name(self, name: str) -> Optional[str]:
        """Extract the name of a ZenML secret from an AWS scoped secret name.

        Args:
            name: the name of the AWS scoped secret

        Returns:
            The ZenML secret name or None, if the input secret name does not
            belong to the current scope.
        """
        name_tokens = name.split("/")
        secret_name = name_tokens[-1]
        name_tokens[-1]
        prefix = "/".join(name_tokens)

        if not secret_name or prefix != self._get_scope_prefix():
            # secret name is not in the current scope
            return None

        return secret_name

    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        Args:
            secret: the secret to register

        Raises:
            SecretExistsError: if the secret already exists
        """
        self.validate_secret_name(secret.name)
        self._ensure_client_connected(self.region_name)
        secret_value = jsonify_secret_contents(secret)

        if secret.name in self.get_all_secret_keys():
            raise SecretExistsError(
                f"A Secret with the name {secret.name} already exists"
            )

        kwargs: Dict[str, Any] = {
            "Name": self._get_scoped_secret_name(secret.name),
            "SecretString": secret_value,
        }
        if self.scope != SecretsManagerScope.UNSCOPED:
            # unscoped secrets do not have tags, for backwards compatibility
            # purposes
            kwargs["Tags"] = (
                [
                    {
                        "zenml_component_name": self.name,
                        "zenml_component_uuid": str(self.uuid),
                        "zenml_scope": self.scope.value,
                        "zenml_namespace": self.namespace,
                    },
                ],
            )

        self.CLIENT.create_secret(**kwargs)

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Gets a secret.

        Args:
            secret_name: the name of the secret to get

        Returns:
            The secret.

        Raises:
            RuntimeError: if the secret does not exist
        """
        self.validate_secret_name(secret_name)
        self._ensure_client_connected(self.region_name)
        get_secret_value_response = self.CLIENT.get_secret_value(
            SecretId=self._get_scoped_secret_name(secret_name)
        )
        if "SecretString" not in get_secret_value_response:
            raise RuntimeError(f"No secrets found within the {secret_name}")
        secret_contents: Dict[str, str] = json.loads(
            get_secret_value_response["SecretString"]
        )

        zenml_schema_name = secret_contents.pop(ZENML_SCHEMA_NAME)
        secret_contents["name"] = secret_name

        secret_schema = SecretSchemaClassRegistry.get_class(
            secret_schema=zenml_schema_name
        )
        return secret_schema(**secret_contents)

    def get_all_secret_keys(self) -> List[str]:
        """Get all secret keys.

        Returns:
            A list of all secret keys
        """
        self._ensure_client_connected(self.region_name)

        filters: List[Any]
        prefix = self._get_scope_prefix()
        if prefix:
            filters = [
                {
                    "Key": "name",
                    "Values": [
                        prefix,
                    ],
                },
                {
                    "Key": "tag-key",
                    "Values": [
                        "zenml_scope",
                    ],
                },
                {
                    "Key": "tag-value",
                    "Values": [
                        self.scope,
                    ],
                },
            ]
        else:
            # unscoped (legacy) secrets don't have tags
            filters = [
                {
                    "Key": "tag-key",
                    "Values": [
                        "!zenml_scope",
                    ],
                },
            ]

        # TODO [ENG-720]: Deal with pagination in the aws secret manager when
        #  listing all secrets
        # TODO [ENG-721]: take out this magic maxresults number
        response = self.CLIENT.list_secrets(MaxResults=100, Filters=filters)
        results = [
            self._get_unscoped_secret_name(secret["Name"])
            for secret in response["SecretList"]
        ]

        # filter out out of scope secrets that may have slipped through (i.e.
        # for which `_get_unscoped_secret_name` returned None)
        return list(filter(None, results))

    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret.

        Args:
            secret: the secret to update
        """
        self._ensure_client_connected(self.region_name)

        secret_value = jsonify_secret_contents(secret)

        kwargs = {
            "SecretId": self._get_scoped_secret_name(secret.name),
            "SecretString": secret_value,
        }

        self.CLIENT.put_secret_value(**kwargs)

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret.

        Args:
            secret_name: the name of the secret to delete
        """
        self._ensure_client_connected(self.region_name)
        self.CLIENT.delete_secret(
            SecretId=self._get_scoped_secret_name(secret_name),
            ForceDeleteWithoutRecovery=False,
        )

    def delete_all_secrets(self) -> None:
        """Delete all existing secrets.

        This method will force delete all your secrets. You will not be able to
        recover them once this method is called.
        """
        self._ensure_client_connected(self.region_name)
        for secret_name in self.get_all_secret_keys():
            self.CLIENT.delete_secret(
                SecretId=self._get_scoped_secret_name(secret_name),
                ForceDeleteWithoutRecovery=True,
            )
