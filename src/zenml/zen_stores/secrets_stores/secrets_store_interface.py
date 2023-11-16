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
"""ZenML secrets store interface."""
from abc import ABC, abstractmethod
from uuid import UUID

from zenml.models import (
    Page,
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
)


class SecretsStoreInterface(ABC):
    """ZenML secrets store interface.

    All ZenML secrets stores must implement the methods in this interface.
    """

    # ---------------------------------
    # Initialization and configuration
    # ---------------------------------

    @abstractmethod
    def _initialize(self) -> None:
        """Initialize the secrets store.

        This method is called immediately after the secrets store is created.
        It should be used to set up the backend (database, connection etc.).
        """

    # ---------
    # Secrets
    # ---------

    @abstractmethod
    def create_secret(
        self,
        secret: SecretRequestModel,
    ) -> SecretResponseModel:
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
            KeyError: if the user or workspace does not exist.
            EntityExistsError: If a secret with the same name already exists in
                the same scope.
            ValueError: if the secret is invalid.
        """

    @abstractmethod
    def get_secret(self, secret_id: UUID) -> SecretResponseModel:
        """Get a secret with a given name.

        Args:
            secret_id: ID of the secret.

        Returns:
            The secret.

        Raises:
            KeyError: if the secret does not exist.
        """

    @abstractmethod
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

    @abstractmethod
    def update_secret(
        self,
        secret_id: UUID,
        secret_update: SecretUpdateModel,
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
            KeyError: if the secret doesn't exist.
            EntityExistsError: If a secret with the same name already exists in
                the same scope.
            ValueError: if the secret is invalid.
        """

    @abstractmethod
    def delete_secret(self, secret_id: UUID) -> None:
        """Deletes a secret.

        Args:
            secret_id: The ID of the secret to delete.

        Raises:
            KeyError: if the secret doesn't exist.
        """
