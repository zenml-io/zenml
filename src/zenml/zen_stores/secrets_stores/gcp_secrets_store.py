#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Implementation of the GCP Secrets Store."""

import json
import os
from typing import (
    Any,
    ClassVar,
    Dict,
    Optional,
    Type,
    cast,
)
from uuid import UUID

from google.api_core import exceptions as google_exceptions
from google.cloud.secretmanager import SecretManagerServiceClient
from pydantic import root_validator

from zenml.enums import (
    SecretsStoreType,
)
from zenml.integrations.gcp import (
    GCP_CONNECTOR_TYPE,
    GCP_RESOURCE_TYPE,
)
from zenml.integrations.gcp.service_connectors.gcp_service_connector import (
    GCPAuthenticationMethods,
)
from zenml.logger import get_logger
from zenml.zen_stores.secrets_stores.service_connector_secrets_store import (
    ServiceConnectorSecretsStore,
    ServiceConnectorSecretsStoreConfiguration,
)

logger = get_logger(__name__)


GCP_ZENML_SECRET_NAME_PREFIX = "zenml"
ZENML_GROUP_KEY = "zenml-group-key"
ZENML_GCP_SECRET_SCOPE_PATH_SEPARATOR = "-"


class GCPSecretsStoreConfiguration(ServiceConnectorSecretsStoreConfiguration):
    """GCP secrets store configuration.

    Attributes:
        type: The type of the store.
    """

    type: SecretsStoreType = SecretsStoreType.GCP

    @property
    def project_id(self) -> str:
        """Get the GCP project ID.

        Returns:
            The GCP project ID.

        Raises:
            ValueError: If the project ID is not set.
        """
        project_id = self.auth_config.get("project_id")
        if project_id:
            return str(project_id)

        raise ValueError("GCP `project_id` must be specified in auth_config.")

    @root_validator(pre=True)
    def populate_config(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Populate the connector configuration from legacy attributes.

        Args:
            values: Dict representing user-specified runtime settings.

        Returns:
            Validated settings.
        """
        # Search for legacy attributes and populate the connector configuration
        # from them, if they exist.
        if values.get("project_id"):
            if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                logger.warning(
                    "The `project_id` GCP secrets store attribute is "
                    "deprecated and will be removed in a future version of ZenML. "
                    "Please use the `auth_method` and `auth_config` attributes "
                    "instead. Using an implicit GCP authentication to access "
                    "the GCP Secrets Manager API."
                )
                values["auth_method"] = GCPAuthenticationMethods.IMPLICIT
                values["auth_config"] = dict(
                    project_id=values.get("project_id"),
                )
            else:
                logger.warning(
                    "The `project_id` GCP secrets store attribute and the "
                    "`GOOGLE_APPLICATION_CREDENTIALS` environment variable are "
                    "deprecated and will be removed in a future version of ZenML. "
                    "Please use the `auth_method` and `auth_config` attributes "
                    "instead."
                )
                values["auth_method"] = (
                    GCPAuthenticationMethods.SERVICE_ACCOUNT
                )
                values["auth_config"] = dict(
                    project_id=values.get("project_id"),
                )
                # Load the service account credentials from the file
                with open(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]) as f:
                    values["auth_config"]["service_account_json"] = f.read()

        return values

    class Config:
        """Pydantic configuration class."""

        # Forbid extra attributes set in the class.
        extra = "allow"


class GCPSecretsStore(ServiceConnectorSecretsStore):
    """Secrets store implementation that uses the GCP Secrets Manager API."""

    config: GCPSecretsStoreConfiguration
    TYPE: ClassVar[SecretsStoreType] = SecretsStoreType.GCP
    CONFIG_TYPE: ClassVar[Type[ServiceConnectorSecretsStoreConfiguration]] = (
        GCPSecretsStoreConfiguration
    )
    SERVICE_CONNECTOR_TYPE: ClassVar[str] = GCP_CONNECTOR_TYPE
    SERVICE_CONNECTOR_RESOURCE_TYPE: ClassVar[str] = GCP_RESOURCE_TYPE

    _client: Optional[SecretManagerServiceClient] = None

    @property
    def client(self) -> SecretManagerServiceClient:
        """Initialize and return the GCP Secrets Manager client.

        Returns:
            The GCP Secrets Manager client instance.
        """
        return cast(SecretManagerServiceClient, super().client)

    # ====================================
    # Secrets Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize_client_from_connector(self, client: Any) -> Any:
        """Initialize the GCP Secrets Manager client from the service connector client.

        Args:
            client: The authenticated client object returned by the service
                connector.

        Returns:
            The GCP Secrets Manager client.
        """
        return SecretManagerServiceClient(credentials=client)

    # ------
    # Secrets
    # ------

    @property
    def parent_name(self) -> str:
        """Construct the GCP parent path to the secret manager.

        Returns:
            The parent path to the secret manager
        """
        return f"projects/{self.config.project_id}"

    def _get_gcp_secret_name(
        self,
        secret_id: UUID,
    ) -> str:
        """Get the GCP secret name for the given secret.

        The convention used for GCP secret names is to use the ZenML
        secret UUID prefixed with `zenml` as the AWS secret name,
        i.e. `zenml/<secret_uuid>`.

        Args:
            secret_id: The ZenML secret ID.

        Returns:
            The GCP secret name.
        """
        return f"{GCP_ZENML_SECRET_NAME_PREFIX}-{str(secret_id)}"

    def store_secret_values(
        self,
        secret_id: UUID,
        secret_values: Dict[str, str],
    ) -> None:
        """Store secret values for a new secret.

        Args:
            secret_id: ID of the secret.
            secret_values: Values for the secret.

        Raises:
            RuntimeError: if the GCP Secrets Manager API returns an unexpected
                error.
        """
        secret_value = json.dumps(secret_values)

        labels = self._get_secret_metadata(secret_id=secret_id)

        try:
            gcp_secret = self.client.create_secret(
                request={
                    "parent": self.parent_name,
                    "secret_id": self._get_gcp_secret_name(secret_id),
                    "secret": {
                        "replication": {"automatic": {}},
                        "labels": labels,
                    },
                }
            )

            logger.debug(f"Created empty GCP parent secret: {gcp_secret.name}")

            self.client.add_secret_version(
                request={
                    "parent": gcp_secret.name,
                    "payload": {"data": secret_value.encode()},
                }
            )

            logger.debug(f"Added value to GCP secret {gcp_secret.name}")
        except Exception as e:
            raise RuntimeError(f"Failed to create secret.: {str(e)}") from e

        logger.debug(f"Created GCP secret {gcp_secret.name}")

    def get_secret_values(self, secret_id: UUID) -> Dict[str, str]:
        """Get the secret values for an existing secret.

        Args:
            secret_id: ID of the secret.

        Returns:
            The secret values.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
            RuntimeError: if the GCP Secrets Manager API returns an unexpected
                error.
        """
        gcp_secret_name = self.client.secret_path(
            self.config.project_id,
            self._get_gcp_secret_name(secret_id=secret_id),
        )

        try:
            secret = self.client.get_secret(name=gcp_secret_name)
            secret_version_values = self.client.access_secret_version(
                name=f"{gcp_secret_name}/versions/latest"
            )
        except google_exceptions.NotFound as e:
            raise KeyError(
                f"Can't find the secret values for secret ID '{secret_id}' "
                f"in the secrets store back-end: {str(e)}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Error fetching secret with ID {secret_id} {e}"
            )

        # The GCP secret labels do not really behave like a dictionary: when
        # a key is not found, it does not raise a KeyError, but instead
        # returns an empty string. That's why we make this conversion.
        metadata = dict(secret.labels)

        # The _verify_secret_metadata method raises a KeyError if the
        # secret is not valid or does not belong to this server. Here we
        # simply pass the exception up the stack, as if the secret was not found
        # in the first place.
        self._verify_secret_metadata(
            secret_id=secret_id,
            metadata=metadata,
        )

        secret_values = json.loads(
            secret_version_values.payload.data.decode("UTF-8")
        )

        if not isinstance(secret_values, dict):
            raise RuntimeError(
                f"Google secret values for secret ID {gcp_secret_name} could "
                "not be decoded: expected a dictionary."
            )

        logger.debug(f"Fetched GCP secret: {gcp_secret_name}")

        return secret_values

    def update_secret_values(
        self,
        secret_id: UUID,
        secret_values: Dict[str, str],
    ) -> None:
        """Updates secret values for an existing secret.

        Args:
            secret_id: The ID of the secret to be updated.
            secret_values: The new secret values.

        Raises:
            RuntimeError: if the GCP Secrets Manager API returns an unexpected
                error.
        """
        gcp_secret_name = self.client.secret_path(
            self.config.project_id,
            self._get_gcp_secret_name(secret_id=secret_id),
        )

        # Convert the ZenML secret metadata to GCP labels
        metadata = self._get_secret_metadata(secret_id)

        try:
            # Update the secret metadata
            update_secret = {
                "name": gcp_secret_name,
                "labels": metadata,
            }
            update_mask = {"paths": ["labels"]}
            gcp_updated_secret = self.client.update_secret(
                request={
                    "secret": update_secret,
                    "update_mask": update_mask,
                }
            )
            # Add a new secret version
            secret_value = json.dumps(secret_values)
            self.client.add_secret_version(
                request={
                    "parent": gcp_updated_secret.name,
                    "payload": {"data": secret_value.encode()},
                }
            )
        except Exception as e:
            raise RuntimeError(f"Error updating secret: {e}") from e

        logger.debug(f"Updated GCP secret: {gcp_secret_name}")

    def delete_secret_values(self, secret_id: UUID) -> None:
        """Deletes secret values for an existing secret.

        Args:
            secret_id: The ID of the secret.

        Raises:
            KeyError: if no secret values for the given ID are stored in the
                secrets store.
            RuntimeError: if the GCP Secrets Manager API returns an unexpected
                error.
        """
        gcp_secret_name = self.client.secret_path(
            self.config.project_id,
            self._get_gcp_secret_name(secret_id=secret_id),
        )

        try:
            self.client.delete_secret(request={"name": gcp_secret_name})
        except google_exceptions.NotFound:
            raise KeyError(f"Secret with ID {secret_id} not found")
        except Exception as e:
            raise RuntimeError(f"Failed to delete secret: {str(e)}") from e

        logger.debug(f"Deleted GCP secret: {gcp_secret_name}")
