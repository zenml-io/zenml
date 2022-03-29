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
from typing import Any, ClassVar, Dict, List

import boto3 as boto3  # type: ignore

from zenml.enums import SecretsManagerFlavor, StackComponentType
from zenml.logger import get_logger
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secret.secret_schema_class_registry import SecretSchemaClassRegistry
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)

logger = get_logger(__name__)

DEFAULT_AWS_REGION = "us-east-1"
ZENML_SCHEMA_NAME = "zenml_schema_name"


def jsonify_secret_contents(secret: BaseSecretSchema) -> str:
    """Adds the secret type to the secret contents to persist the schema
    type in the secrets backend, so that the correct SecretSchema can be
    retrieved when the secret is queried from the backend.

    Args:
        secret: should be a subclass of the BaseSecretSchema class

    Returns:
        jsonified dictionary containing all key-value pairs and the ZenML schema
        type
    """
    secret_contents = secret.content
    secret_contents[ZENML_SCHEMA_NAME] = secret.schema_type
    return json.dumps(secret_contents)


@register_stack_component_class(
    component_type=StackComponentType.SECRETS_MANAGER,
    component_flavor=SecretsManagerFlavor.AWS,
)
class AWSSecretsManager(BaseSecretsManager):
    """Class to interact with the AWS secrets manager."""

    supports_local_execution: bool = True
    supports_remote_execution: bool = True
    region_name: str = DEFAULT_AWS_REGION

    CLIENT: ClassVar[Any] = None

    @classmethod
    def _ensure_client_connected(cls, region_name: str) -> None:
        if cls.CLIENT is None:
            # Create a Secrets Manager client
            session = boto3.session.Session()
            cls.CLIENT = session.client(
                service_name="secretsmanager", region_name=region_name
            )

    @property
    def flavor(self) -> SecretsManagerFlavor:
        """The secrets manager flavor.

        Returns:
            The secrets manager flavor."""
        return SecretsManagerFlavor.AWS

    @property
    def type(self) -> StackComponentType:
        """The secrets manager type.

        Returns:
            The secrets manager type."""
        return StackComponentType.SECRETS_MANAGER

    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        Args:
            secret: the secret to register"""
        self._ensure_client_connected(self.region_name)
        secret_value = jsonify_secret_contents(secret)

        kwargs = {"Name": secret.name, "SecretString": secret_value}
        self.CLIENT.create_secret(**kwargs)

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Gets a secret.

        Args:
            secret_name: the name of the secret to get

        Returns:
            The secret.

        Raises:
            RuntimeError: if the secret does not exist"""
        self._ensure_client_connected(self.region_name)
        get_secret_value_response = self.CLIENT.get_secret_value(
            SecretId=secret_name
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
            A list of all secret keys."""
        self._ensure_client_connected(self.region_name)

        # TODO [ENG-720]: Deal with pagination in the aws secret manager when
        #  listing all secrets
        # TODO [ENG-721]: take out this magic maxresults number
        response = self.CLIENT.list_secrets(MaxResults=100)
        return [secret["Name"] for secret in response["SecretList"]]

    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret.

        Args:
            secret: the secret to update"""
        self._ensure_client_connected(self.region_name)

        secret_value = jsonify_secret_contents(secret)

        kwargs = {"SecretId": secret.name, "SecretString": secret_value}

        self.CLIENT.put_secret_value(**kwargs)

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret.

        Args:
            secret_name: the name of the secret to delete"""
        self._ensure_client_connected(self.region_name)
        self.CLIENT.delete_secret(
            SecretId=secret_name, ForceDeleteWithoutRecovery=False
        )

    def delete_all_secrets(self, force: bool = False) -> None:
        """Delete all existing secrets.

        Args:
            force: whether to force delete all secrets"""
        self._ensure_client_connected(self.region_name)
        for secret_name in self.get_all_secret_keys():
            self.CLIENT.delete_secret(
                SecretId=secret_name, ForceDeleteWithoutRecovery=force
            )
