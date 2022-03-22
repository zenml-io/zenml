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
from typing import Any, ClassVar, Dict, List, Optional

import boto3 as boto3  # type: ignore
from botocore.exceptions import ClientError  # type: ignore

from zenml.enums import SecretsManagerFlavor, StackComponentType
from zenml.logger import get_logger
from zenml.secret.base_secret import Secret
from zenml.secret.secret_schema_class_registry import SecretSchemaClassRegistry
from zenml.secrets_manager.base_secrets_manager import BaseSecretsManager
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)

logger = get_logger(__name__)

DEFAULT_AWS_REGION = "us-east-1"
ZENML_SCHEMA_NAME = "zenml_schema_name"


@register_stack_component_class(
    component_type=StackComponentType.SECRETS_MANAGER,
    component_flavor=SecretsManagerFlavor.AWS,
)
class AWSSecretsManager(BaseSecretsManager):
    """Class to interact with the AWS secret manager."""

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
        """The secrets manager flavor."""
        return SecretsManagerFlavor.AWS

    @property
    def type(self) -> StackComponentType:
        """The secrets manager type."""
        return StackComponentType.SECRETS_MANAGER

    def register_secret(self, secret: Secret) -> None:
        """
        Creates a new secret. The secret value can be a string or bytes.
        """
        self._ensure_client_connected(self.region_name)
        secret_contents = secret.get_contents
        if secret.has_defined_schema:
            secret_contents[ZENML_SCHEMA_NAME] = secret.contents.type
        secret_value = json.dumps(secret_contents)
        kwargs = {"Name": secret.name, "SecretString": secret_value}
        self.CLIENT.create_secret(**kwargs)

    def get_secret(self, secret_name: str) -> Secret:
        """Gets the value of a secret."""
        self._ensure_client_connected(self.region_name)
        get_secret_value_response = self.CLIENT.get_secret_value(
            SecretId=secret_name
        )
        if "SecretString" in get_secret_value_response:
            secret_contents: Dict[str, str] = json.loads(
                get_secret_value_response["SecretString"]
            )

            try:
                zenml_schema_name = secret_contents.pop(ZENML_SCHEMA_NAME)
            except KeyError:
                secret = Secret(
                    name=secret_name,
                    contents=secret_contents,
                )
            else:
                secret_schema = SecretSchemaClassRegistry.get_class(
                    secret_schema=zenml_schema_name
                )
                secret = Secret(
                    name=secret_name,
                    contents=secret_schema(**secret_contents),
                )

            return secret
        else:
            raise RuntimeError(f"No secrets found within the" f" {secret_name}")

    def get_all_secret_keys(self) -> List[str]:
        """Get all secret keys."""
        self._ensure_client_connected(self.region_name)

        # TODO [MEDIUM]: Deal with pagination in the aws secret manager when
        #  listing all secrets
        response = self.CLIENT.list_secrets(MaxResults=100)
        secrets = []
        for secret in response["SecretList"]:
            secrets.append(secret["Name"])
        return secrets

    def update_secret(self, secret: Secret) -> None:
        """Update existing secret."""
        self._ensure_client_connected(self.region_name)

        secret_contents = secret.get_contents
        if secret.has_defined_schema:
            secret_contents[ZENML_SCHEMA_NAME] = secret.contents.type
        secret_value = json.dumps(secret_contents)

        kwargs = {"SecretId": secret.name, "SecretString": secret_value}

        self.CLIENT.put_secret_value(**kwargs)

    def delete_secret(self, secret_name: str) -> None:
        """Delete existing secret."""
        self._ensure_client_connected(self.region_name)
        self.CLIENT.delete_secret(
            SecretId=secret_name, ForceDeleteWithoutRecovery=False
        )

    def delete_all_secrets(self, force: bool = False) -> None:
        """Delete existing secret."""
        self._ensure_client_connected(self.region_name)
        for secret_name in self.get_all_secret_keys():
            self.CLIENT.delete_secret(
                SecretId=secret_name, ForceDeleteWithoutRecovery=force
            )

    def get_value_by_key(self, key: str, secret_name: str) -> Optional[str]:
        """Get value at key within secret"""
        secret = self.get_secret(secret_name)

        secret_contents = secret.get_contents
        if key in secret_contents:
            secret_value = secret_contents[key]
            return secret_value
        else:
            raise KeyError(
                f"Secret `{key}` does not exist in secret-set "
                f"'{secret_name}'."
            )
