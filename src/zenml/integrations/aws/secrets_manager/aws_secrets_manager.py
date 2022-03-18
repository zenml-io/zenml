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
from typing import Any, ClassVar, List, Optional

import boto3 as boto3
from botocore.exceptions import ClientError

from zenml.enums import SecretsManagerFlavor, StackComponentType
from zenml.logger import get_logger
from zenml.secret_sets.base_secret_set import BaseSecretSet
from zenml.secrets_manager.base_secrets_manager import BaseSecretsManager
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)

logger = get_logger(__name__)

DEFAULT_AWS_REGION = "us-east-1"


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
    def _ensure_client_connected(cls, region_name: str):
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

    def register_secret_set(
        self, secret_set_name: str, secret_set: BaseSecretSet
    ) -> None:
        """Register secret."""
        raise NotImplementedError

    def register_secret(self, name: str, secret_value: str) -> None:
        """
        Creates a new secret. The secret value can be a string or bytes.
        """
        self._ensure_client_connected(self.region_name)
        kwargs = {"Name": name, "SecretString": secret_value}
        response = self.CLIENT.create_secret(**kwargs)
        logger.error(response)

    def get_secret_by_key(self, name: str) -> Optional[str]:
        """Gets the value of a secret."""
        self._ensure_client_connected(self.region_name)
        try:
            get_secret_value_response = self.CLIENT.get_secret_value(
                SecretId=name
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "DecryptionFailureException":
                # Secrets Manager can't decrypt the protected secret
                # text using the provided KMS key. Deal with the exception here,
                # and/or rethrow at your discretion.
                raise e
            elif e.response["Error"]["Code"] == "InternalServiceErrorException":
                # An error occurred on the server side.
                # Deal with the exception here, and/or
                # rethrow at your discretion.
                raise e
            elif e.response["Error"]["Code"] == "InvalidParameterException":
                # You provided an invalid value for a parameter.
                # Deal with the exception here, and/or rethrow
                # at your discretion.
                raise e
            elif e.response["Error"]["Code"] == "InvalidRequestException":
                # You provided a parameter value that is not valid for
                # the current state of the resource. Deal with the exception
                # here, and/or rethrow at your discretion.
                raise e
            elif e.response["Error"]["Code"] == "ResourceNotFoundException":
                # We can't find the resource that you asked for.
                # Deal with the exception here, and/or rethrow
                # at your discretion.
                raise e
        else:
            # Decrypts secret using the associated KMS key.
            # Depending on whether the secret is a string or binary,
            # one of these fields will be populated.
            if "SecretString" in get_secret_value_response:
                secret = get_secret_value_response["SecretString"]
                return secret

    def get_all_secret_keys(self) -> List[Optional[str]]:
        """Get all secret keys."""
        self._ensure_client_connected(self.region_name)

        response = self.CLIENT.list_secrets()
        logger.debug(response)

        secrets = []
        for secret in response["SecretList"]:
            secrets.append(secret["Name"])
        return secrets

    def update_secret_by_key(self, name: str, secret_value: str) -> None:
        """Update existing secret."""
        self._ensure_client_connected(self.region_name)

        kwargs = {"SecretId": name, "SecretString": secret_value}
        response = self.CLIENT.put_secret_value(**kwargs)
        logger.debug(response)

    def delete_secret_by_key(self, name: str) -> None:
        """Delete existing secret."""
        self._ensure_client_connected(self.region_name)
        response = self.CLIENT.delete_secret(
            SecretId=name, ForceDeleteWithoutRecovery=False
        )
        logger.debug(response)
