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
import botocore

from zenml.exceptions import SecretExistsError
from zenml.integrations.aws import AWS_SECRET_MANAGER_FLAVOR
from zenml.logger import get_logger
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secrets_managers.base_secrets_manager import (
    BaseSecretsManager,
    SecretsManagerScope,
)
from zenml.secrets_managers.utils import secret_from_dict, secret_to_dict

logger = get_logger(__name__)


class AWSSecretsManager(BaseSecretsManager):
    """Class to interact with the AWS secrets manager."""

    region_name: str

    # Class configuration
    FLAVOR: ClassVar[str] = AWS_SECRET_MANAGER_FLAVOR
    SUPPORTS_SCOPING: ClassVar[bool] = True
    CLIENT: ClassVar[Any] = None

    @classmethod
    def _validate_scope(
        cls,
        scope: SecretsManagerScope,
        namespace: Optional[str],
    ) -> None:
        """Validate the scope and namespace value.

        Args:
            scope: Scope value.
            namespace: Optional namespace value.
        """
        if namespace:
            cls.validate_secret_name_or_namespace(namespace)

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
    def validate_secret_name_or_namespace(cls, name: str) -> None:
        """Validate a secret name or namespace.

        AWS secret names must contain only alphanumeric characters and the
        characters /_+=.@-. The `/` character is only used internally to delimit
        scopes.

        Args:
            name: the secret name or namespace

        Raises:
            ValueError: if the secret name or namespace is invalid
        """
        if not re.fullmatch(r"[a-zA-Z0-9_+=\.@\-]*", name):
            raise ValueError(
                f"Invalid secret name or namespace '{name}'. Must contain "
                f"only alphanumeric characters and the characters _+=.@-."
            )

    def _get_scoped_secret_name(self, name: str) -> str:
        """Convert a ZenML secret name into an AWS scoped secret name.

        Args:
            name: the name of the secret

        Returns:
            The AWS scoped secret name
        """
        return "/".join(self._get_scoped_secret_path(name))

    def _get_unscoped_secret_name(self, name: str) -> Optional[str]:
        """Extract the name of a ZenML secret from an AWS scoped secret name.

        Args:
            name: the name of the AWS scoped secret

        Returns:
            The ZenML secret name or None, if the input secret name does not
            belong to the current scope.
        """
        return self._get_secret_name_from_path(name.split("/"))

    def _get_secret_tags(
        self, secret: BaseSecretSchema
    ) -> List[Dict[str, str]]:
        """Return a list of AWS secret tag values for a given secret.

        Args:
            secret: the secret object

        Returns:
            A list of AWS secret tag values
        """
        metadata = self._get_secret_metadata(secret)
        return [{"Key": k, "Value": v} for k, v in metadata.items()]

    def _get_secret_scope_filters(
        self,
        secret_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return a list of AWS filters for the entire scope or just a scoped secret.

        These filters can be used when querying the AWS Secrets Manager
        for all secrets or for a single secret available in the configured
        scope.

        Args:
            secret_name: Optional secret name to filter for.

        Returns:
            A list of AWS filters uniquely identifying all secrets
            or a named secret within the configured scope.
        """
        metadata = self._get_secret_scope_metadata(secret_name)
        filters: List[Dict[str, Any]] = []
        for k, v in metadata.items():
            filters.append(
                {
                    "Key": "tag-key",
                    "Values": [
                        k,
                    ],
                }
            )
            filters.append(
                {
                    "Key": "tag-value",
                    "Values": [
                        str(v),
                    ],
                }
            )

        return filters

    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        Args:
            secret: the secret to register

        Raises:
            SecretExistsError: if the secret already exists
        """
        self.validate_secret_name_or_namespace(secret.name)
        self._ensure_client_connected(self.region_name)
        secret_value = json.dumps(secret_to_dict(secret, encode=False))

        try:
            self.get_secret(secret.name)
            raise SecretExistsError(
                f"A Secret with the name {secret.name} already exists"
            )
        except KeyError:
            pass

        kwargs: Dict[str, Any] = {
            "Name": self._get_scoped_secret_name(secret.name),
            "SecretString": secret_value,
            "Tags": self._get_secret_tags(secret),
        }

        self.CLIENT.create_secret(**kwargs)

        logger.debug("Created AWS secret: %s", kwargs["Name"])

    def get_secret(self, secret_name: str) -> BaseSecretSchema:
        """Gets a secret.

        Args:
            secret_name: the name of the secret to get

        Returns:
            The secret.

        Raises:
            KeyError: if the secret does not exist
            RuntimeError: if an unexpected AWS client error occurs
        """
        self.validate_secret_name_or_namespace(secret_name)
        self._ensure_client_connected(self.region_name)

        try:
            get_secret_value_response = self.CLIENT.get_secret_value(
                SecretId=self._get_scoped_secret_name(secret_name)
            )
            if "SecretString" not in get_secret_value_response:
                get_secret_value_response = None
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] == "ResourceNotFoundException":
                get_secret_value_response = None
            else:
                raise RuntimeError(
                    f"An unexpected failure occurred while reading secret "
                    f"'{secret_name}'"
                ) from error

        if get_secret_value_response is None:
            raise KeyError(f"Can't find the specified secret '{secret_name}'")

        return secret_from_dict(
            json.loads(get_secret_value_response["SecretString"]),
            secret_name=secret_name,
            decode=False,
        )

    def get_all_secret_keys(self) -> List[str]:
        """Get all secret keys.

        Returns:
            A list of all secret keys
        """
        self._ensure_client_connected(self.region_name)

        filters: List[Dict[str, Any]] = []
        if self.scope == SecretsManagerScope.NONE:
            # unscoped (legacy) secrets don't have tags. We want to filter out
            # non-legacy secrets
            filters = [
                {
                    "Key": "tag-key",
                    "Values": [
                        "!zenml_scope",
                    ],
                },
            ]
        else:
            filters = self._get_secret_scope_filters()
            # add the name prefix to the filters to account for the fact that
            # AWS does not do exact matching but prefix-matching on the filters
            prefix = "/".join(self._get_scope_path())
            filters.append(
                {
                    "Key": "name",
                    "Values": [
                        f"{prefix}/",
                    ],
                }
            )

        # TODO [ENG-720]: Deal with pagination in the aws secret manager when
        #  listing all secrets
        # TODO [ENG-721]: take out this magic maxresults number
        response = self.CLIENT.list_secrets(MaxResults=100, Filters=filters)
        # print(response)
        results = [
            self._get_unscoped_secret_name(secret["Name"])
            for secret in response["SecretList"]
        ]

        # remove out-of-scope secrets that may have slipped through (i.e.
        # for which `_get_unscoped_secret_name` returned None) because AWS does
        # not use exact matching with the filters, but prefix matching instead
        return list(filter(None, results))

    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret.

        Args:
            secret: the secret to update

        Raises:
            KeyError: if the secret does not exist
            RuntimeError: if an unexpected AWS client error occurs
        """
        self.validate_secret_name_or_namespace(secret.name)
        self._ensure_client_connected(self.region_name)

        secret_value = json.dumps(secret_to_dict(secret))

        kwargs = {
            "SecretId": self._get_scoped_secret_name(secret.name),
            "SecretString": secret_value,
            "Tags": self._get_secret_tags(secret),
        }

        try:
            self.CLIENT.put_secret_value(**kwargs)
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] == "ResourceNotFoundException":
                raise KeyError(
                    f"Can't find the specified secret '{secret.name}'"
                )
            else:
                raise RuntimeError(
                    f"An unexpected failure occurred while updating secret "
                    f"'{secret.name}'"
                ) from error

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret.

        Args:
            secret_name: the name of the secret to delete

        Raises:
            KeyError: if the secret does not exist
            RuntimeError: if an unexpected AWS client error occurs
        """
        self._ensure_client_connected(self.region_name)
        try:
            self.CLIENT.delete_secret(
                SecretId=self._get_scoped_secret_name(secret_name),
                ForceDeleteWithoutRecovery=True,
            )
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] == "ResourceNotFoundException":
                raise KeyError(
                    f"Can't find the specified secret '{secret_name}'"
                )
            else:
                raise RuntimeError(
                    f"An unexpected failure occurred while deleting secret "
                    f"'{secret_name}'"
                ) from error

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
