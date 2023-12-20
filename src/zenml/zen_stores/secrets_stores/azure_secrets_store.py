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
"""Azure Secrets Store implementation."""

import json
import logging
import math
import re
import uuid
from datetime import datetime
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    cast,
)
from uuid import UUID

from azure.core.credentials import TokenCredential
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.keyvault.secrets import SecretClient
from pydantic import root_validator

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_decorator
from zenml.enums import (
    SecretsStoreType,
)
from zenml.exceptions import EntityExistsError
from zenml.integrations.azure import (
    AZURE_CONNECTOR_TYPE,
    AZURE_RESOURCE_TYPE,
)
from zenml.integrations.azure.service_connectors.azure_service_connector import (
    AzureAuthenticationMethods,
)
from zenml.logger import get_logger
from zenml.models import (
    Page,
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
)
from zenml.zen_stores.secrets_stores.service_connector_secrets_store import (
    ServiceConnectorSecretsStore,
    ServiceConnectorSecretsStoreConfiguration,
)

logger = get_logger(__name__)


AZURE_ZENML_SECRET_NAME_PREFIX = "zenml"
ZENML_AZURE_SECRET_CREATED_KEY = "zenml_secret_created"
ZENML_AZURE_SECRET_UPDATED_KEY = "zenml_secret_updated"


class AzureSecretsStoreConfiguration(
    ServiceConnectorSecretsStoreConfiguration
):
    """Azure secrets store configuration.

    Attributes:
        type: The type of the store.
        key_vault_name: Name of the Azure Key Vault that this secrets store
            will use to store secrets.
    """

    type: SecretsStoreType = SecretsStoreType.AZURE
    key_vault_name: str

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
        if (
            values.get("azure_client_id")
            and values.get("azure_client_secret")
            and values.get("azure_tenant_id")
        ):
            logger.warning(
                "The `azure_client_id`, `azure_client_secret` and "
                "`azure_tenant_id` attributes are deprecated and will be "
                "removed in a future version or ZenML. Please use the "
                "`auth_method` and `auth_config` attributes instead."
            )
            values[
                "auth_method"
            ] = AzureAuthenticationMethods.SERVICE_PRINCIPAL
            values["auth_config"] = dict(
                client_id=values.get("azure_client_id"),
                client_secret=values.get("azure_client_secret"),
                tenant_id=values.get("azure_tenant_id"),
            )

        return values

    class Config:
        """Pydantic configuration class."""

        # Forbid extra attributes set in the class.
        extra = "allow"


class AzureSecretsStore(ServiceConnectorSecretsStore):
    """Secrets store implementation that uses the Azure Key Vault API.

    This secrets store implementation uses the Azure Key Vault API to
    store secrets. It allows a single Azure Key Vault to be shared with other
    ZenML deployments as well as other third party users and applications.

    Here are some implementation highlights:

    * the name/ID of an Azure secret is derived from the ZenML secret UUID and a
    `zenml` prefix in the form `zenml-{zenml_secret_uuid}`. This clearly
    identifies a secret as being managed by ZenML in the Azure console.

    * the Secrets Store also makes heavy use of Azure Key Vault secret tags to
    store all the metadata associated with a ZenML secret (e.g. the secret name,
    scope, user and workspace) and to filter secrets by these metadata. The
    `zenml` tag in particular is used to identify and group all secrets that
    belong to the same ZenML deployment.

    * all secret key-values configured in a ZenML secret are stored as a single
    JSON string value in the Azure Key Vault secret value.

    * when a user or workspace is deleted, the secrets associated with it are
    deleted automatically via registered event handlers.


    Known challenges and limitations:

    * every Azure Key Vault secret has one or more versions. Every update to a
    secret creates a new version. The created_on and updated_on timestamps
    returned by the Secrets Store API are the timestamps of the latest version
    of the secret. This means that we need to fetch the first version of the
    secret to get the created_on timestamp. This is not ideal, as we'd need to
    fetch all versions for every secret to get the created_on timestamp during
    a list operation. So instead we manage the `created` and `updated`
    timestamps ourselves and save them as tags in the Azure Key Vault secret.
    """

    config: AzureSecretsStoreConfiguration
    TYPE: ClassVar[SecretsStoreType] = SecretsStoreType.AZURE
    CONFIG_TYPE: ClassVar[
        Type[ServiceConnectorSecretsStoreConfiguration]
    ] = AzureSecretsStoreConfiguration
    SERVICE_CONNECTOR_TYPE: ClassVar[str] = AZURE_CONNECTOR_TYPE
    SERVICE_CONNECTOR_RESOURCE_TYPE: ClassVar[str] = AZURE_RESOURCE_TYPE

    @property
    def client(self) -> SecretClient:
        """Initialize and return the Azure Key Vault client.

        Returns:
            The Azure Key Vault client.
        """
        return cast(SecretClient, super().client)

    # ====================================
    # Secrets Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize_client_from_connector(self, client: Any) -> Any:
        """Initialize the Azure Key Vault client from the service connector client.

        Args:
            client: The authenticated client object returned by the service
                connector.

        Returns:
            The Azure Key Vault client.
        """
        assert isinstance(client, TokenCredential)
        azure_logger = logging.getLogger("azure")

        # Suppress the INFO logging level of the Azure SDK if the
        # ZenML logging level is WARNING or lower.
        if logger.level <= logging.WARNING:
            azure_logger.setLevel(logging.WARNING)
        else:
            azure_logger.setLevel(logging.INFO)

        vault_url = f"https://{self.config.key_vault_name}.vault.azure.net"
        return SecretClient(vault_url=vault_url, credential=client)

    # ------
    # Secrets
    # ------

    @staticmethod
    def _validate_azure_secret_name(name: str) -> None:
        """Validate a secret name.

        Azure secret names must contain only alphanumeric characters and the
        character `-`.

        Given that the ZenML secret name is stored as an Azure Key Vault secret
        label, we are also limited by the 256 maximum size limitation that Azure
        imposes on label values.

        Args:
            name: the secret name

        Raises:
            ValueError: if the secret name is invalid
        """
        if not re.fullmatch(r"[0-9a-zA-Z-]+", name):
            raise ValueError(
                f"Invalid secret name or namespace '{name}'. Must contain "
                f"only alphanumeric characters and the character -."
            )

        if len(name) > 256:
            raise ValueError(
                f"Invalid secret name or namespace '{name}'. The length is "
                f"limited to maximum 256 characters."
            )

    @staticmethod
    def _get_azure_secret_id(
        secret_id: UUID,
    ) -> str:
        """Get the Azure secret ID corresponding to a ZenML secret ID.

        The convention used for Azure secret names is to use the ZenML
        secret UUID prefixed with `zenml` as the Azure secret name,
        i.e. `zenml-<secret_uuid>`.

        Args:
            secret_id: The ZenML secret ID.

        Returns:
            The Azure secret name.
        """
        return f"{AZURE_ZENML_SECRET_NAME_PREFIX}-{str(secret_id)}"

    def _convert_azure_secret(
        self,
        tags: Dict[str, str],
        values: Optional[str] = None,
    ) -> SecretResponseModel:
        """Create a ZenML secret model from data stored in an Azure secret.

        If the Azure secret cannot be converted, the method acts as if the
        secret does not exist and raises a KeyError.

        Args:
            tags: The Azure secret tags.
            values: The Azure secret values encoded as a JSON string
                (optional).

        Returns:
            The ZenML secret.

        Raises:
            KeyError: if the Azure secret cannot be converted.
        """
        try:
            created = datetime.fromisoformat(
                tags[ZENML_AZURE_SECRET_CREATED_KEY],
            )
            updated = datetime.fromisoformat(
                tags[ZENML_AZURE_SECRET_UPDATED_KEY],
            )
        except KeyError as e:
            raise KeyError(
                f"Secret could not be retrieved: missing required metadata: {e}"
            )

        return self._create_secret_from_metadata(
            metadata=tags,
            created=created,
            updated=updated,
            values=json.loads(values) if values else None,
        )

    @track_decorator(AnalyticsEvent.CREATED_SECRET)
    def create_secret(self, secret: SecretRequestModel) -> SecretResponseModel:
        """Creates a new secret.

        The new secret is also validated against the scoping rules enforced in
        the secrets store:

          - only one workspace-scoped secret with the given name can exist
            in the target workspace.
          - only one user-scoped secret with the given name can exist in the
            target workspace for the target user.

        Args:
            secret: The secret to create.

        Returns:
            The newly created secret.

        Raises:
            EntityExistsError: If a secret with the same name already exists
                in the same scope.
            RuntimeError: If the Azure Key Vault API returns an unexpected
                error.
        """
        self._validate_azure_secret_name(secret.name)
        user, workspace = self._validate_user_and_workspace(
            secret.user, secret.workspace
        )

        # Check if a secret with the same name already exists in the same
        # scope.
        secret_exists, msg = self._check_secret_scope(
            secret_name=secret.name,
            scope=secret.scope,
            workspace=secret.workspace,
            user=secret.user,
        )
        if secret_exists:
            raise EntityExistsError(msg)

        # Generate a new UUID for the secret
        secret_id = uuid.uuid4()
        azure_secret_id = self._get_azure_secret_id(secret_id)
        secret_value = json.dumps(secret.secret_values)

        # Use the ZenML secret metadata as Azure tags
        metadata = self._get_secret_metadata_for_secret(
            secret, secret_id=secret_id
        )

        # We manage the created and updated times ourselves, so we don't need to
        # rely on the Azure Key Vault API to set them.
        created = datetime.utcnow()
        metadata[ZENML_AZURE_SECRET_CREATED_KEY] = created.isoformat()
        metadata[ZENML_AZURE_SECRET_UPDATED_KEY] = created.isoformat()

        try:
            self.client.set_secret(
                azure_secret_id,
                secret_value,
                tags=metadata,
                content_type="application/json",
            )
        except HttpResponseError as e:
            raise RuntimeError(f"Error creating secret: {e}")

        logger.debug("Created Azure secret: %s", azure_secret_id)

        secret_model = SecretResponseModel(
            id=secret_id,
            name=secret.name,
            scope=secret.scope,
            workspace=workspace,
            user=user,
            values=secret.secret_values,
            created=created,
            updated=created,
        )

        return secret_model

    def get_secret(self, secret_id: UUID) -> SecretResponseModel:
        """Get a secret by ID.

        Args:
            secret_id: The ID of the secret to fetch.

        Returns:
            The secret.

        Raises:
            KeyError: If the secret does not exist.
            RuntimeError: If the Azure Key Vault API returns an unexpected
                error.
        """
        azure_secret_id = self._get_azure_secret_id(secret_id)

        try:
            azure_secret = self.client.get_secret(
                azure_secret_id,
            )
        except ResourceNotFoundError:
            raise KeyError(f"Secret with ID {secret_id} not found")
        except HttpResponseError as e:
            raise RuntimeError(
                f"Error fetching secret with ID {secret_id} {e}"
            )

        # The _convert_azure_secret method raises a KeyError if the
        # secret is tied to a workspace or user that no longer exists. Here we
        # simply pass the exception up the stack, as if the secret was not found
        # in the first place, knowing that it will be cascade-deleted soon.
        assert azure_secret.properties.tags is not None
        return self._convert_azure_secret(
            tags=azure_secret.properties.tags,
            values=azure_secret.value,
        )

    def list_secrets(
        self, secret_filter_model: SecretFilterModel
    ) -> Page[SecretResponseModel]:
        """List all secrets matching the given filter criteria.

        Note that returned secrets do not include any secret values. To fetch
        the secret values, use `get_secret`.

        Args:
            secret_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all secrets matching the filter criteria, with pagination
            information and sorted according to the filter criteria. The
            returned secrets do not include any secret values, only metadata. To
            fetch the secret values, use `get_secret` individually with each
            secret.

        Raises:
            ValueError: If the filter contains an out-of-bounds page number.
            RuntimeError: If the Azure Key Vault API returns an unexpected
                error.
        """
        # The Azure Key Vault API does not natively support any of the
        # filtering, sorting or pagination options that ZenML supports. The
        # implementation of this method therefore has to fetch all secrets from
        # the Key Vault, then apply the filtering, sorting and pagination on
        # the client side.

        # The metadata will always contain at least the filter criteria
        # required to exclude everything but Azure secrets that belong to the
        # current ZenML deployment.
        results: List[SecretResponseModel] = []

        try:
            all_secrets = self.client.list_properties_of_secrets()
            for secret_property in all_secrets:
                try:
                    # NOTE: we do not include the secret values in the
                    # response. We would need a separate API call to fetch
                    # them for each secret, which would be very inefficient
                    # anyway.
                    assert secret_property.tags is not None
                    secret_model = self._convert_azure_secret(
                        tags=secret_property.tags,
                    )
                except KeyError:
                    # The _convert_azure_secret method raises a KeyError
                    # if the secret is tied to a workspace or user that no
                    # longer exists or if it is otherwise not valid. Here we
                    # pretend that the secret does not exist.
                    continue

                # Filter the secret on the client side.
                if not secret_filter_model.secret_matches(secret_model):
                    continue
                results.append(secret_model)
        except HttpResponseError as e:
            raise RuntimeError(f"Error listing Azure Key Vault secrets: {e}")

        # Sort the results
        sorted_results = secret_filter_model.sort_secrets(results)

        # Paginate the results
        total = len(sorted_results)
        if total == 0:
            total_pages = 1
        else:
            total_pages = math.ceil(total / secret_filter_model.size)

        if secret_filter_model.page > total_pages:
            raise ValueError(
                f"Invalid page {secret_filter_model.page}. The requested page "
                f"size is {secret_filter_model.size} and there are a total of "
                f"{total} items for this query. The maximum page value "
                f"therefore is {total_pages}."
            )

        return Page[SecretResponseModel](
            total=total,
            total_pages=total_pages,
            items=sorted_results[
                (secret_filter_model.page - 1)
                * secret_filter_model.size : secret_filter_model.page
                * secret_filter_model.size
            ],
            index=secret_filter_model.page,
            max_size=secret_filter_model.size,
        )

    def update_secret(
        self, secret_id: UUID, secret_update: SecretUpdateModel
    ) -> SecretResponseModel:
        """Updates a secret.

        Secret values that are specified as `None` in the update that are
        present in the existing secret are removed from the existing secret.
        Values that are present in both secrets are overwritten. All other
        values in both the existing secret and the update are kept (merged).

        If the update includes a change of name or scope, the scoping rules
        enforced in the secrets store are used to validate the update:

          - only one workspace-scoped secret with the given name can exist
            in the target workspace.
          - only one user-scoped secret with the given name can exist in the
            target workspace for the target user.

        Args:
            secret_id: The ID of the secret to be updated.
            secret_update: The update to be applied.

        Returns:
            The updated secret.

        Raises:
            EntityExistsError: If the update includes a change of name or
                scope and a secret with the same name already exists in the
                same scope.
            RuntimeError: If the Azure Key Vault API returns an unexpected
                error.
        """
        secret = self.get_secret(secret_id)

        # Prevent changes to the secret's user or workspace
        assert secret.user is not None
        self._validate_user_and_workspace_update(
            secret_update=secret_update,
            current_user=secret.user.id,
            current_workspace=secret.workspace.id,
        )

        if secret_update.name is not None:
            self._validate_azure_secret_name(secret_update.name)
            secret.name = secret_update.name
        if secret_update.scope is not None:
            secret.scope = secret_update.scope
        if secret_update.values is not None:
            # Merge the existing values with the update values.
            # The values that are set to `None` in the update are removed from
            # the existing secret when we call `.secret_values` later.
            secret.values.update(secret_update.values)

        if secret_update.name is not None or secret_update.scope is not None:
            # Check if a secret with the same name already exists in the same
            # scope.
            assert secret.user is not None
            secret_exists, msg = self._check_secret_scope(
                secret_name=secret.name,
                scope=secret.scope,
                workspace=secret.workspace.id,
                user=secret.user.id,
                exclude_secret_id=secret.id,
            )
            if secret_exists:
                raise EntityExistsError(msg)

        azure_secret_id = self._get_azure_secret_id(secret_id)
        secret_value = json.dumps(secret.secret_values)

        # Convert the ZenML secret metadata to Azure tags
        metadata = self._get_secret_metadata_for_secret(secret)

        # We manage the created and updated times ourselves, so we don't need to
        # rely on the Azure Key Vault API to set them.
        updated = datetime.utcnow()
        metadata[ZENML_AZURE_SECRET_CREATED_KEY] = secret.created.isoformat()
        metadata[ZENML_AZURE_SECRET_UPDATED_KEY] = updated.isoformat()

        try:
            self.client.set_secret(
                azure_secret_id,
                secret_value,
                tags=metadata,
                content_type="application/json",
            )
        except HttpResponseError as e:
            raise RuntimeError(f"Error updating secret {secret_id}: {e}")

        logger.debug("Updated Azure secret: %s", azure_secret_id)

        secret_model = SecretResponseModel(
            id=secret_id,
            name=secret.name,
            scope=secret.scope,
            workspace=secret.workspace,
            user=secret.user,
            values=secret.secret_values,
            created=secret.created,
            updated=updated,
        )

        return secret_model

    def delete_secret(self, secret_id: UUID) -> None:
        """Delete a secret.

        Args:
            secret_id: The id of the secret to delete.

        Raises:
            KeyError: If the secret does not exist.
            RuntimeError: If the Azure Key Vault API returns an unexpected
                error.
        """
        try:
            self.client.begin_delete_secret(
                self._get_azure_secret_id(secret_id),
            ).wait()
        except ResourceNotFoundError:
            raise KeyError(f"Secret with ID {secret_id} not found")
        except HttpResponseError as e:
            raise RuntimeError(
                f"Error deleting secret with ID {secret_id}: {e}"
            )
