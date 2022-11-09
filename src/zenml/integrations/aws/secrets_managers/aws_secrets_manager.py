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
from typing import Any, ClassVar, Dict, List, Optional, cast

import boto3

from zenml.exceptions import SecretExistsError
from zenml.integrations.aws.flavors.aws_secrets_manager_flavor import (
    AWSSecretsManagerConfig,
    validate_aws_secret_name_or_namespace,
)
from zenml.logger import get_logger
from zenml.secret.base_secret import BaseSecretSchema
from zenml.secrets_managers.base_secrets_manager import (
    BaseSecretsManager,
    SecretsManagerScope,
)
from zenml.secrets_managers.utils import secret_from_dict, secret_to_dict

logger = get_logger(__name__)

_BOTO_CLIENT_LIST_SECRETS = "list_secrets"
_PAGINATOR_RESPONSE_SECRETS_LIST_KEY = "SecretList"


class AWSSecretsManager(BaseSecretsManager):
    """Class to interact with the AWS secrets manager."""

    CLIENT: ClassVar[Any] = None

    @property
    def config(self) -> AWSSecretsManagerConfig:
        """Returns the `AWSSecretsManagerConfig` config.

        Returns:
            The configuration.
        """
        return cast(AWSSecretsManagerConfig, self._config)

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
        scope. For more information see: https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_search-secret.html

        Example AWS filters for all secrets in the current (namespace) scope:

        ```python
        [
            {
                "Key: "tag-key",
                "Values": ["zenml_scope"],
            },
            {
                "Key: "tag-value",
                "Values": ["namespace"],
            },
            {
                "Key: "tag-key",
                "Values": ["zenml_namespace"],
            },
            {
                "Key: "tag-value",
                "Values": ["my_namespace"],
            },
        ]
        ```

        Example AWS filters for a particular secret in the current (namespace)
        scope:

        ```python
        [
            {
                "Key: "tag-key",
                "Values": ["zenml_secret_name"],
            },
            {
                "Key: "tag-value",
                "Values": ["my_secret"],
            },
            {
                "Key: "tag-key",
                "Values": ["zenml_scope"],
            },
            {
                "Key: "tag-value",
                "Values": ["namespace"],
            },
            {
                "Key: "tag-key",
                "Values": ["zenml_namespace"],
            },
            {
                "Key: "tag-value",
                "Values": ["my_namespace"],
            },
        ]
        ```

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

    def _list_secrets(self, secret_name: Optional[str] = None) -> List[str]:
        """List all secrets matching a name.

        This method lists all the secrets in the current scope without loading
        their contents. An optional secret name can be supplied to filter out
        all but a single secret identified by name.

        Args:
            secret_name: Optional secret name to filter for.

        Returns:
            A list of secret names in the current scope and the optional
            secret name.
        """
        self._ensure_client_connected(self.config.region_name)

        filters: List[Dict[str, Any]] = []
        prefix: Optional[str] = None
        if self.config.scope == SecretsManagerScope.NONE:
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
            if secret_name:
                prefix = secret_name
        else:
            filters = self._get_secret_scope_filters()
            if secret_name:
                prefix = self._get_scoped_secret_name(secret_name)
            else:
                # add the name prefix to the filters to account for the fact
                # that AWS does not do exact matching but prefix-matching on the
                # filters
                prefix = self._get_scoped_secret_name_prefix()

        if prefix:
            filters.append(
                {
                    "Key": "name",
                    "Values": [
                        f"{prefix}",
                    ],
                }
            )

        paginator = self.CLIENT.get_paginator(_BOTO_CLIENT_LIST_SECRETS)
        pages = paginator.paginate(
            Filters=filters,
            PaginationConfig={
                "PageSize": 100,
            },
        )
        results = []
        for page in pages:
            for secret in page[_PAGINATOR_RESPONSE_SECRETS_LIST_KEY]:
                name = self._get_unscoped_secret_name(secret["Name"])
                # keep only the names that are in scope and filter by secret name,
                # if one was given
                if name and (not secret_name or secret_name == name):
                    results.append(name)

        return results

    def register_secret(self, secret: BaseSecretSchema) -> None:
        """Registers a new secret.

        Args:
            secret: the secret to register

        Raises:
            SecretExistsError: if the secret already exists
        """
        validate_aws_secret_name_or_namespace(secret.name)
        self._ensure_client_connected(self.config.region_name)

        if self._list_secrets(secret.name):
            raise SecretExistsError(
                f"A Secret with the name {secret.name} already exists"
            )

        secret_value = json.dumps(secret_to_dict(secret, encode=False))
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
        """
        validate_aws_secret_name_or_namespace(secret_name)
        self._ensure_client_connected(self.config.region_name)

        if not self._list_secrets(secret_name):
            raise KeyError(f"Can't find the specified secret '{secret_name}'")

        get_secret_value_response = self.CLIENT.get_secret_value(
            SecretId=self._get_scoped_secret_name(secret_name)
        )
        if "SecretString" not in get_secret_value_response:
            get_secret_value_response = None

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
        return self._list_secrets()

    def update_secret(self, secret: BaseSecretSchema) -> None:
        """Update an existing secret.

        Args:
            secret: the secret to update

        Raises:
            KeyError: if the secret does not exist
        """
        validate_aws_secret_name_or_namespace(secret.name)
        self._ensure_client_connected(self.config.region_name)

        if not self._list_secrets(secret.name):
            raise KeyError(f"Can't find the specified secret '{secret.name}'")

        secret_value = json.dumps(secret_to_dict(secret))

        kwargs = {
            "SecretId": self._get_scoped_secret_name(secret.name),
            "SecretString": secret_value,
        }

        self.CLIENT.put_secret_value(**kwargs)

    def delete_secret(self, secret_name: str) -> None:
        """Delete an existing secret.

        Args:
            secret_name: the name of the secret to delete

        Raises:
            KeyError: if the secret does not exist
        """
        self._ensure_client_connected(self.config.region_name)

        if not self._list_secrets(secret_name):
            raise KeyError(f"Can't find the specified secret '{secret_name}'")

        self.CLIENT.delete_secret(
            SecretId=self._get_scoped_secret_name(secret_name),
            ForceDeleteWithoutRecovery=True,
        )

    def delete_all_secrets(self) -> None:
        """Delete all existing secrets.

        This method will force delete all your secrets. You will not be able to
        recover them once this method is called.
        """
        self._ensure_client_connected(self.config.region_name)
        for secret_name in self._list_secrets():
            self.CLIENT.delete_secret(
                SecretId=self._get_scoped_secret_name(secret_name),
                ForceDeleteWithoutRecovery=True,
            )
