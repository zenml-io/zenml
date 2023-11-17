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
"""REST Secrets Store implementation."""

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Type,
)
from uuid import UUID

from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.constants import SECRETS
from zenml.enums import (
    SecretsStoreType,
)
from zenml.exceptions import (
    IllegalOperationError,
)
from zenml.logger import get_logger
from zenml.models import (
    Page,
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
)
from zenml.zen_stores.secrets_stores.base_secrets_store import (
    BaseSecretsStore,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.zen_stores.base_zen_store import BaseZenStore
    from zenml.zen_stores.rest_zen_store import RestZenStore


class RestSecretsStoreConfiguration(SecretsStoreConfiguration):
    """REST secrets store configuration.

    Attributes:
        type: The type of the store.
    """

    type: SecretsStoreType = SecretsStoreType.REST

    class Config:
        """Pydantic configuration class."""

        # Don't validate attributes when assigning them. This is necessary
        # because the certificate attributes can be expanded to the contents
        # of the certificate files.
        validate_assignment = False
        # Forbid extra attributes set in the class.
        extra = "forbid"


class RestSecretsStore(BaseSecretsStore):
    """Secrets store implementation that uses the REST ZenML store as a backend.

    This secrets store piggybacks on the REST ZenML store. It uses the same
    REST client configuration as the REST ZenML store.

    Attributes:
        config: The configuration of the REST secrets store.
        TYPE: The type of the store.
        CONFIG_TYPE: The type of the store configuration.
    """

    config: RestSecretsStoreConfiguration
    TYPE: ClassVar[SecretsStoreType] = SecretsStoreType.REST
    CONFIG_TYPE: ClassVar[
        Type[SecretsStoreConfiguration]
    ] = RestSecretsStoreConfiguration

    def __init__(
        self,
        zen_store: "BaseZenStore",
        **kwargs: Any,
    ) -> None:
        """Create and initialize the REST secrets store.

        Args:
            zen_store: The ZenML store that owns this REST secrets store.
            **kwargs: Additional keyword arguments to pass to the Pydantic
                constructor.

        Raises:
            IllegalOperationError: If the ZenML store to which this secrets
                store belongs is not a REST ZenML store.
        """
        from zenml.zen_stores.rest_zen_store import RestZenStore

        if not isinstance(zen_store, RestZenStore):
            raise IllegalOperationError(
                "The REST secrets store can only be used with the REST ZenML "
                "store."
            )
        super().__init__(zen_store, **kwargs)

    @property
    def zen_store(self) -> "RestZenStore":
        """The ZenML store that this REST secrets store is using as a back-end.

        Returns:
            The ZenML store that this REST secrets store is using as a back-end.

        Raises:
            ValueError: If the store is not initialized.
        """
        from zenml.zen_stores.rest_zen_store import RestZenStore

        if not self._zen_store:
            raise ValueError("Store not initialized")
        assert isinstance(self._zen_store, RestZenStore)
        return self._zen_store

    # ====================================
    # Secrets Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize(self) -> None:
        """Initialize the secrets REST store."""
        logger.debug("Initializing RestSecretsStore")

        # Nothing else to do here, the REST ZenML store back-end is already
        # initialized

    # ------
    # Secrets
    # ------

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
        """
        return self.zen_store._create_workspace_scoped_resource(
            resource=secret,
            route=SECRETS,
            response_model=SecretResponseModel,
        )

    def get_secret(self, secret_id: UUID) -> SecretResponseModel:
        """Get a secret by ID.

        Args:
            secret_id: The ID of the secret to fetch.

        Returns:
            The secret.
        """
        return self.zen_store._get_resource(
            resource_id=secret_id,
            route=SECRETS,
            response_model=SecretResponseModel,
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
        """
        return self.zen_store._list_paginated_resources(
            route=SECRETS,
            response_model=SecretResponseModel,
            filter_model=secret_filter_model,
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
        """
        return self.zen_store._update_resource(
            resource_id=secret_id,
            resource_update=secret_update,
            route=SECRETS,
            response_model=SecretResponseModel,
            # The default endpoint behavior is to replace all secret values
            # with the values in the update. We want to merge the values
            # instead.
            params=dict(patch_values=True),
        )

    def delete_secret(self, secret_id: UUID) -> None:
        """Delete a secret.

        Args:
            secret_id: The id of the secret to delete.
        """
        self.zen_store._delete_resource(
            resource_id=secret_id,
            route=SECRETS,
        )
