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
"""HashiCorp Vault Secrets Store implementation."""

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
)
from uuid import UUID

import hvac  # type: ignore[import-untyped]
from hvac.exceptions import (  # type: ignore[import-untyped]
    InvalidPath,
    VaultError,
)
from pydantic import SecretStr

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_decorator
from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.enums import (
    SecretsStoreType,
)
from zenml.exceptions import EntityExistsError
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


HVAC_ZENML_SECRET_NAME_PREFIX = "zenml"
ZENML_VAULT_SECRET_VALUES_KEY = "zenml_secret_values"
ZENML_VAULT_SECRET_METADATA_KEY = "zenml_secret_metadata"
ZENML_VAULT_SECRET_CREATED_KEY = "zenml_secret_created"
ZENML_VAULT_SECRET_UPDATED_KEY = "zenml_secret_updated"


class HashiCorpVaultSecretsStoreConfiguration(SecretsStoreConfiguration):
    """HashiCorp Vault secrets store configuration.

    Attributes:
        type: The type of the store.
        vault_addr: The url of the Vault server. If not set, the value will be
            loaded from the VAULT_ADDR environment variable, if configured.
        vault_token: The token used to authenticate with the Vault server. If
            not set, the token will be loaded from the VAULT_TOKEN environment
            variable or from the ~/.vault-token file, if configured.
        vault_namespace: The Vault Enterprise namespace.
        mount_point: The mount point to use for all secrets.
        max_versions: The maximum number of secret versions to keep.
    """

    type: SecretsStoreType = SecretsStoreType.HASHICORP

    vault_addr: str
    vault_token: Optional[SecretStr] = None
    vault_namespace: Optional[str] = None
    mount_point: Optional[str] = None
    max_versions: int = 1

    class Config:
        """Pydantic configuration class."""

        # Forbid extra attributes set in the class.
        extra = "forbid"


class HashiCorpVaultSecretsStore(BaseSecretsStore):
    """Secrets store implementation that uses the HashiCorp Vault API.

    This secrets store implementation uses the HashiCorp Vault API to
    store secrets. It allows a single HashiCorp Vault server to be shared with
    other ZenML deployments as well as other third party users and applications.

    Here are some implementation highlights:

    * the name/ID of an HashiCorp Vault secret is derived from the ZenML secret
    UUID and a `zenml` prefix in the form `zenml/{zenml_secret_uuid}`. This
    clearly identifies a secret as being managed by ZenML in the HashiCorp Vault
    server. This also allows use to reduce the scope of `list_secrets` to cover
    only secrets managed by ZenML by using `zenml/` as the path prefix.

    * given that HashiCorp Vault secrets do not support attaching arbitrary
    metadata in the form of label or tags, we store the entire ZenML secret
    metadata (e.g. name, scope, etc.) alongside the secret values in the
    HashiCorp Vault secret value.

    * when a user or workspace is deleted, the secrets associated with it are
    deleted automatically via registered event handlers.

    Known challenges and limitations:

    * HashiCorp Vault secrets do not support filtering secrets by metadata
    attached to secrets in the form of label or tags. This means that we cannot
    filter secrets server-side based on their metadata (e.g. name, scope, etc.).
    Instead, we have to retrieve all ZenML managed secrets and filter them
    client-side.

    * HashiCorp Vault secrets are versioned. This means that when a secret is
    updated, a new version is created which has its own creation timestamp.
    Furthermore, older secret versions are deleted automatically after a certain
    configurable number of versions is reached. To work around this, we also
    manage `created` and `updated` timestamps here and store them in the secret
    value itself.


    Attributes:
        config: The configuration of the HashiCorp Vault secrets store.
        TYPE: The type of the store.
        CONFIG_TYPE: The type of the store configuration.
    """

    config: HashiCorpVaultSecretsStoreConfiguration
    TYPE: ClassVar[SecretsStoreType] = SecretsStoreType.HASHICORP
    CONFIG_TYPE: ClassVar[
        Type[SecretsStoreConfiguration]
    ] = HashiCorpVaultSecretsStoreConfiguration

    _client: Optional[hvac.Client] = None

    @property
    def client(self) -> hvac.Client:
        """Initialize and return the HashiCorp Vault client.

        Returns:
            The HashiCorp Vault client.
        """
        if self._client is None:
            # Initialize the HashiCorp Vault client with the
            # credentials from the configuration.
            self._client = hvac.Client(
                url=self.config.vault_addr,
                token=self.config.vault_token.get_secret_value()
                if self.config.vault_token
                else None,
                namespace=self.config.vault_namespace,
            )
            self._client.secrets.kv.v2.configure(
                max_versions=self.config.max_versions,
            )
            if self.config.mount_point:
                self._client.secrets.kv.v2.configure(
                    mount_point=self.config.mount_point,
                )
        return self._client

    # ====================================
    # Secrets Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize(self) -> None:
        """Initialize the HashiCorp Vault secrets store."""
        logger.debug("Initializing HashiCorpVaultSecretsStore")

        # Initialize the HashiCorp Vault client early, just to catch any
        # configuration or authentication errors early, before the Secrets
        # Store is used.
        _ = self.client

    # ------
    # Secrets
    # ------

    @staticmethod
    def _validate_vault_secret_name(name: str) -> None:
        """Validate a secret name.

        HashiCorp Vault secret names must contain only alphanumeric characters
        and the characters _+=.@-/.

        Args:
            name: the secret name

        Raises:
            ValueError: if the secret name is invalid
        """
        if not re.fullmatch(r"[a-zA-Z0-9_+=\.@\-/]*", name):
            raise ValueError(
                f"Invalid secret name or namespace '{name}'. Must contain "
                f"only alphanumeric characters and the characters _+=.@-/."
            )

    @staticmethod
    def _get_vault_secret_id(
        secret_id: UUID,
    ) -> str:
        """Get the HashiCorp Vault secret ID corresponding to a ZenML secret ID.

        The convention used for HashiCorp Vault secret names is to use the ZenML
        secret UUID prefixed with `zenml` as the HashiCorp Vault secret name,
        i.e. `zenml/<secret_uuid>`.

        Args:
            secret_id: The ZenML secret ID.

        Returns:
            The HashiCorp Vault secret name.
        """
        return f"{HVAC_ZENML_SECRET_NAME_PREFIX}/{str(secret_id)}"

    def _convert_vault_secret(
        self,
        vault_secret: Dict[str, Any],
    ) -> SecretResponseModel:
        """Create a ZenML secret model from data stored in an HashiCorp Vault secret.

        If the HashiCorp Vault secret cannot be converted, the method acts as if
        the secret does not exist and raises a KeyError.

        Args:
            vault_secret: The HashiCorp Vault secret in JSON form.

        Returns:
            The ZenML secret.

        Raises:
            KeyError: if the HashiCorp Vault secret cannot be converted.
        """
        try:
            metadata = vault_secret[ZENML_VAULT_SECRET_METADATA_KEY]
            values = vault_secret[ZENML_VAULT_SECRET_VALUES_KEY]
            created = datetime.fromisoformat(
                vault_secret[ZENML_VAULT_SECRET_CREATED_KEY],
            )
            updated = datetime.fromisoformat(
                vault_secret[ZENML_VAULT_SECRET_UPDATED_KEY],
            )
        except (KeyError, ValueError) as e:
            raise KeyError(
                f"Secret could not be retrieved: missing required metadata: {e}"
            )

        return self._create_secret_from_metadata(
            metadata=metadata,
            created=created,
            updated=updated,
            values=values,
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
            RuntimeError: If the HashiCorp Vault API returns an unexpected
                error.
        """
        self._validate_vault_secret_name(secret.name)
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
        vault_secret_id = self._get_vault_secret_id(secret_id)

        metadata = self._get_secret_metadata_for_secret(
            secret, secret_id=secret_id
        )

        created = datetime.utcnow()
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=vault_secret_id,
                # Store the ZenML secret metadata alongside the secret values
                secret={
                    ZENML_VAULT_SECRET_VALUES_KEY: secret.secret_values,
                    ZENML_VAULT_SECRET_METADATA_KEY: metadata,
                    ZENML_VAULT_SECRET_CREATED_KEY: created.isoformat(),
                    ZENML_VAULT_SECRET_UPDATED_KEY: created.isoformat(),
                },
                # Do not allow overwriting an existing secret
                cas=0,
            )
        except VaultError as e:
            raise RuntimeError(f"Error creating secret: {e}")

        logger.debug("Created HashiCorp Vault secret: %s", vault_secret_id)

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
            RuntimeError: If the HashiCorp Vault API returns an unexpected
                error.
        """
        vault_secret_id = self._get_vault_secret_id(secret_id)

        try:
            vault_secret = (
                self.client.secrets.kv.v2.read_secret(
                    path=vault_secret_id,
                )
                .get("data", {})
                .get("data", {})
            )
        except InvalidPath:
            raise KeyError(f"Secret with ID {secret_id} not found")
        except VaultError as e:
            raise RuntimeError(
                f"Error fetching secret with ID {secret_id} {e}"
            )

        # The _convert_vault_secret method raises a KeyError if the
        # secret is tied to a workspace or user that no longer exists. Here we
        # simply pass the exception up the stack, as if the secret was not found
        # in the first place, knowing that it will be cascade-deleted soon.
        return self._convert_vault_secret(
            vault_secret,
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
            RuntimeError: If the HashiCorp Vault API returns an unexpected
                error.
        """
        # The HashiCorp Vault API does not natively support any of the
        # filtering, sorting or pagination options that ZenML supports. The
        # implementation of this method therefore has to fetch all secrets from
        # the Key Vault, then apply the filtering, sorting and pagination on
        # the client side.

        results: List[SecretResponseModel] = []

        try:
            # List all ZenML secrets in the Vault
            all_secrets = (
                self.client.secrets.kv.v2.list_secrets(
                    path=HVAC_ZENML_SECRET_NAME_PREFIX
                )
                .get("data", {})
                .get("keys", [])
            )
        except InvalidPath:
            # no secrets created yet
            pass
        except VaultError as e:
            raise RuntimeError(f"Error listing HashiCorp Vault secrets: {e}")
        else:
            # Convert the Vault secrets to ZenML secrets
            for secret_uuid in all_secrets:
                vault_secret_id = (
                    f"{HVAC_ZENML_SECRET_NAME_PREFIX}/{secret_uuid}"
                )
                try:
                    vault_secret = (
                        self.client.secrets.kv.v2.read_secret(
                            path=vault_secret_id
                        )
                        .get("data", {})
                        .get("data", {})
                    )
                except (InvalidPath, VaultError) as e:
                    logging.warning(
                        f"Error fetching secret with ID {vault_secret_id}: {e}",
                    )
                    continue

                try:
                    secret_model = self._convert_vault_secret(
                        vault_secret,
                    )
                except KeyError as e:
                    # The _convert_vault_secret method raises a KeyError
                    # if the secret is tied to a workspace or user that no
                    # longer exists or if it is otherwise not valid. Here we
                    # pretend that the secret does not exist.
                    logging.warning(
                        f"Error fetching secret with ID {vault_secret_id}: {e}",
                    )
                    continue

                # Filter the secret on the client side.
                if not secret_filter_model.secret_matches(secret_model):
                    continue

                # Remove the secret values from the response
                secret_model.values = {}
                results.append(secret_model)

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
            KeyError: If the secret does not exist.
            EntityExistsError: If the update includes a change of name or
                scope and a secret with the same name already exists in the
                same scope.
            RuntimeError: If the HashiCorp Vault API returns an unexpected
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
            self._validate_vault_secret_name(secret_update.name)
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

        vault_secret_id = self._get_vault_secret_id(secret_id)

        # Convert the ZenML secret metadata to HashiCorp Vault tags
        metadata = self._get_secret_metadata_for_secret(secret)

        updated = datetime.utcnow()
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=vault_secret_id,
                # Store the ZenML secret metadata alongside the secret values
                secret={
                    ZENML_VAULT_SECRET_VALUES_KEY: secret.secret_values,
                    ZENML_VAULT_SECRET_METADATA_KEY: metadata,
                    ZENML_VAULT_SECRET_CREATED_KEY: secret.created.isoformat(),
                    ZENML_VAULT_SECRET_UPDATED_KEY: updated.isoformat(),
                },
            )
        except InvalidPath:
            raise KeyError(f"Secret with ID {secret_id} does not exist.")
        except VaultError as e:
            raise RuntimeError(f"Error updating secret {secret_id}: {e}")

        logger.debug("Updated HashiCorp Vault secret: %s", vault_secret_id)

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
            RuntimeError: If the HashiCorp Vault API returns an unexpected
                error.
        """
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=self._get_vault_secret_id(secret_id),
            )
        except InvalidPath:
            raise KeyError(f"Secret with ID {secret_id} does not exist.")
        except VaultError as e:
            raise RuntimeError(
                f"Error deleting secret with ID {secret_id}: {e}"
            )
