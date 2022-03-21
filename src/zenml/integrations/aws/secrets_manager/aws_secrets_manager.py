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

    def register_secret_set(
        self, secret_set_name: str, secret_set: BaseSecretSet
    ) -> None:
        """
        Creates a new secret. The secret value can be a string or bytes.
        """
        self._ensure_client_connected(self.region_name)
        secret_value = json.dumps(secret_set.dict())
        kwargs = {"Name": secret_set_name, "SecretString": secret_value}
        self.CLIENT.create_secret(**kwargs)

    def get_all_secret_sets_keys(self) -> List[Optional[str]]:
        """Get all secret keys."""
        self._ensure_client_connected(self.region_name)

        response = self.CLIENT.list_secrets()

        secrets = []
        for secret in response["SecretList"]:
            secrets.append(secret["Name"])
        return secrets

    def get_secret_set_by_key(
        self, secret_set_name: str
    ) -> Optional[Dict[str, str]]:
        """Gets the value of a secret."""
        self._ensure_client_connected(self.region_name)
        try:
            get_secret_value_response = self.CLIENT.get_secret_value(
                SecretId=secret_set_name
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
                secret_dict = json.loads(
                    get_secret_value_response["SecretString"]
                )
                return secret_dict
        return

    def update_secret_set_by_key(
        self, secret_set_name: str, secret_set: Dict[str, str]
    ) -> None:
        """Update existing secret."""
        self._ensure_client_connected(self.region_name)

        kwargs = {
            "SecretId": secret_set_name,
            "SecretString": json.dumps(secret_set),
        }
        self.CLIENT.put_secret_value(**kwargs)

    def delete_secret_set_by_key(self, secret_set_name: str) -> None:
        """Delete existing secret."""
        self._ensure_client_connected(self.region_name)
        self.CLIENT.delete_secret(
            SecretId=secret_set_name, ForceDeleteWithoutRecovery=False
        )

    def register_secret(
        self, name: str, secret_value: str, secret_set_name: str
    ) -> None:
        """Register secret within a secret set."""
        secret_set_contents = self.get_secret_set_by_key(secret_set_name)

        if name not in secret_set_contents:
            secret_set_contents[name] = secret_value
            self.update_secret_set_by_key(
                secret_set_name=secret_set_name, secret_set=secret_set_contents
            )
        else:
            raise KeyError(
                f"Secret `{name}` already exists in secret-set "
                f"'{secret_set_name}'."
            )

    def get_secret_by_key(
        self, name: str, secret_set_name: str
    ) -> Optional[str]:
        """Get secret within secret set by key."""
        secret_set_contents = self.get_secret_set_by_key(secret_set_name)

        if name in secret_set_contents:
            secret_value = secret_set_contents[name]
            return secret_value
        else:
            raise KeyError(
                f"Secret `{name}` does not exist in secret-set "
                f"'{secret_set_name}'."
            )

    def get_all_secret_keys(self, secret_set_name: str) -> List[Optional[str]]:
        """Get secret within secret set by key."""
        secret_set_contents = self.get_secret_set_by_key(secret_set_name)
        return list(secret_set_contents.keys())

    def update_secret_by_key(
        self, name: str, secret_value: str, secret_set_name: str
    ) -> None:
        """Register secret within a secret set."""
        secret_set_contents = self.get_secret_set_by_key(secret_set_name)

        if name in secret_set_contents:
            secret_set_contents[name] = secret_value
            self.update_secret_set_by_key(
                secret_set_name=secret_set_name, secret_set=secret_set_contents
            )
        else:
            raise KeyError(
                f"Secret `{name}` does not exist in secret-set "
                f"'{secret_set_name}'."
            )

    def delete_secret_by_key(self, name: str, secret_set_name) -> None:
        secret_set_contents = self.get_secret_set_by_key(secret_set_name)

        if name in secret_set_contents:
            secret_set_contents.pop(name)
            self.update_secret_set_by_key(
                secret_set_name=secret_set_name, secret_set=secret_set_contents
            )
        else:
            raise KeyError(
                f"Secret `{name}` did not exist in secret-set "
                f"'{secret_set_name}'."
            )
