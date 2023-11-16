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
"""Base Secrets Store implementation."""
from abc import ABC
from datetime import datetime
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Optional,
    Tuple,
    Type,
    Union,
)
from uuid import UUID

from pydantic import BaseModel

from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.enums import SecretScope, SecretsStoreType
from zenml.exceptions import IllegalOperationError
from zenml.logger import get_logger
from zenml.models import (
    SecretFilterModel,
    SecretRequestModel,
    SecretResponseModel,
    SecretUpdateModel,
    UserResponse,
    WorkspaceResponse,
)
from zenml.utils import source_utils
from zenml.utils.pagination_utils import depaginate
from zenml.zen_stores.enums import StoreEvent
from zenml.zen_stores.secrets_stores.secrets_store_interface import (
    SecretsStoreInterface,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.zen_stores.base_zen_store import BaseZenStore

ZENML_SECRET_LABEL = "zenml"
ZENML_SECRET_ID_LABEL = "zenml_secret_id"
ZENML_SECRET_NAME_LABEL = "zenml_secret_name"
ZENML_SECRET_SCOPE_LABEL = "zenml_secret_scope"
ZENML_SECRET_USER_LABEL = "zenml_secret_user"
ZENML_SECRET_WORKSPACE_LABEL = "zenml_secret_workspace"


class BaseSecretsStore(BaseModel, SecretsStoreInterface, ABC):
    """Base class for accessing and persisting ZenML secret objects.

    Attributes:
        config: The configuration of the secret store.
        _zen_store: The ZenML store that owns this secrets store.
    """

    config: SecretsStoreConfiguration
    _zen_store: Optional["BaseZenStore"] = None

    TYPE: ClassVar[SecretsStoreType]
    CONFIG_TYPE: ClassVar[Type[SecretsStoreConfiguration]]

    # ---------------------------------
    # Initialization and configuration
    # ---------------------------------

    def __init__(
        self,
        zen_store: "BaseZenStore",
        **kwargs: Any,
    ) -> None:
        """Create and initialize a secrets store.

        Args:
            zen_store: The ZenML store that owns this secrets store.
            **kwargs: Additional keyword arguments to pass to the Pydantic
                constructor.

        Raises:
            RuntimeError: If the store cannot be initialized.
        """
        super().__init__(**kwargs)
        self._zen_store = zen_store

        self.zen_store.register_event_handler(
            StoreEvent.WORKSPACE_DELETED, self._on_workspace_deleted
        )

        self.zen_store.register_event_handler(
            StoreEvent.USER_DELETED, self._on_user_deleted
        )

        try:
            self._initialize()
        except Exception as e:
            raise RuntimeError(
                f"Error initializing {self.type.value} secrets store: {str(e)}"
            ) from e

    @staticmethod
    def _load_custom_store_class(
        store_config: SecretsStoreConfiguration,
    ) -> Type["BaseSecretsStore"]:
        """Loads the custom secrets store class from the given config.

        Args:
            store_config: The configuration of the secrets store.

        Returns:
            The secrets store class corresponding to the configured custom
            secrets store.

        Raises:
            ValueError: If the configured class path cannot be imported or is
                not a subclass of `BaseSecretsStore`.
        """
        # Ensured through Pydantic root validation
        assert store_config.class_path is not None

        # Import the class dynamically
        try:
            store_class = source_utils.load_and_validate_class(
                store_config.class_path, expected_class=BaseSecretsStore
            )
        except (ImportError, AttributeError) as e:
            raise ValueError(
                f"Could not import class `{store_config.class_path}`: {str(e)}"
            ) from e

        return store_class

    @staticmethod
    def get_store_class(
        store_config: SecretsStoreConfiguration,
    ) -> Type["BaseSecretsStore"]:
        """Returns the class of the given secrets store type.

        Args:
            store_config: The configuration of the secrets store.

        Returns:
            The class corresponding to the configured secrets store or None if
            the type is unknown.

        Raises:
            TypeError: If the secrets store type is unsupported.
        """
        if store_config.type == SecretsStoreType.SQL:
            from zenml.zen_stores.secrets_stores.sql_secrets_store import (
                SqlSecretsStore,
            )

            return SqlSecretsStore

        if store_config.type == SecretsStoreType.REST:
            from zenml.zen_stores.secrets_stores.rest_secrets_store import (
                RestSecretsStore,
            )

            return RestSecretsStore

        if store_config.type == SecretsStoreType.AWS:
            from zenml.zen_stores.secrets_stores.aws_secrets_store import (
                AWSSecretsStore,
            )

            return AWSSecretsStore
        elif store_config.type == SecretsStoreType.GCP:
            from zenml.zen_stores.secrets_stores.gcp_secrets_store import (
                GCPSecretsStore,
            )

            return GCPSecretsStore
        elif store_config.type == SecretsStoreType.AZURE:
            from zenml.zen_stores.secrets_stores.azure_secrets_store import (
                AzureSecretsStore,
            )

            return AzureSecretsStore
        elif store_config.type == SecretsStoreType.HASHICORP:
            from zenml.zen_stores.secrets_stores.hashicorp_secrets_store import (
                HashiCorpVaultSecretsStore,
            )

            return HashiCorpVaultSecretsStore
        elif store_config.type != SecretsStoreType.CUSTOM:
            raise TypeError(
                f"No store implementation found for secrets store type "
                f"`{store_config.type.value}`."
            )

        return BaseSecretsStore._load_custom_store_class(store_config)

    @staticmethod
    def create_store(
        config: SecretsStoreConfiguration,
        **kwargs: Any,
    ) -> "BaseSecretsStore":
        """Create and initialize a secrets store from a secrets store configuration.

        Args:
            config: The secrets store configuration to use.
            **kwargs: Additional keyword arguments to pass to the store class

        Returns:
            The initialized secrets store.
        """
        logger.debug(
            f"Creating secrets store with type '{config.type.value}'..."
        )
        store_class = BaseSecretsStore.get_store_class(config)
        store = store_class(
            config=config,
            **kwargs,
        )
        return store

    @property
    def type(self) -> SecretsStoreType:
        """The type of the secrets store.

        Returns:
            The type of the secrets store.
        """
        return self.TYPE

    @property
    def zen_store(self) -> "BaseZenStore":
        """The ZenML store that owns this secrets store.

        Returns:
            The ZenML store that owns this secrets store.

        Raises:
            ValueError: If the store is not initialized.
        """
        if not self._zen_store:
            raise ValueError("Store not initialized")
        return self._zen_store

    # --------------------
    # Store Event Handlers
    # --------------------

    def _on_workspace_deleted(
        self, event: StoreEvent, workspace_id: UUID
    ) -> None:
        """Handle the deletion of a workspace.

        This method deletes all secrets associated with the given workspace.

        Args:
            event: The store event.
            workspace_id: The ID of the workspace that was deleted.
        """
        logger.debug(
            "Handling workspace deletion event for workspace %s", workspace_id
        )

        # Delete all secrets associated with the workspace.
        secrets = depaginate(
            partial(
                self.list_secrets,
                secret_filter_model=SecretFilterModel(
                    workspace_id=workspace_id
                ),
            )
        )
        for secret in secrets:
            try:
                self.delete_secret(secret.id)
            except KeyError:
                pass
            except Exception as e:
                logger.warning("Failed to delete secret %s: %s", secret.id, e)

    def _on_user_deleted(self, event: StoreEvent, user_id: UUID) -> None:
        """Handle the deletion of a user.

        This method deletes all secrets associated with the given user.

        Args:
            event: The store event.
            user_id: The ID of the user that was deleted.
        """
        logger.debug("Handling user deletion event for user %s", user_id)

        # Delete all secrets associated with the user.
        secrets = depaginate(
            partial(
                self.list_secrets,
                secret_filter_model=SecretFilterModel(user_id=user_id),
            )
        )
        for secret in secrets:
            try:
                self.delete_secret(secret.id)
            except KeyError:
                pass
            except Exception as e:
                logger.warning("Failed to delete secret %s: %s", secret.id, e)

    # ------------------------------------------
    # Common helpers for Secrets Store back-ends
    # ------------------------------------------

    def _validate_user_and_workspace(
        self, user_id: UUID, workspace_id: UUID
    ) -> Tuple[UserResponse, WorkspaceResponse]:
        """Validates that the given user and workspace IDs are valid.

        This method calls the ZenML store to validate the user and workspace
        IDs. It raises a KeyError exception if either the user or workspace
        does not exist.

        Args:
            user_id: The ID of the user to validate.
            workspace_id: The ID of the workspace to validate.

        Returns:
            The user and workspace.
        """
        user = self.zen_store.get_user(user_id)
        workspace = self.zen_store.get_workspace(workspace_id)

        return user, workspace

    def _validate_user_and_workspace_update(
        self,
        secret_update: SecretUpdateModel,
        current_user: UUID,
        current_workspace: UUID,
    ) -> None:
        """Validates that a secret update does not change the user or workspace.

        Args:
            secret_update: Secret update.
            current_user: The current user ID.
            current_workspace: The current workspace ID.

        Raises:
            IllegalOperationError: If the user or workspace is changed.
        """
        if secret_update.user and current_user != secret_update.user:
            raise IllegalOperationError("Cannot change the user of a secret.")
        if (
            secret_update.workspace
            and current_workspace != secret_update.workspace
        ):
            raise IllegalOperationError(
                "Cannot change the workspace of a secret."
            )

    def _check_secret_scope(
        self,
        secret_name: str,
        scope: SecretScope,
        workspace: UUID,
        user: UUID,
        exclude_secret_id: Optional[UUID] = None,
    ) -> Tuple[bool, str]:
        """Checks if a secret with the given name already exists in the given scope.

        This method enforces the following scope rules:

          - only one workspace-scoped secret with the given name can exist
            in the target workspace.
          - only one user-scoped secret with the given name can exist in the
            target workspace for the target user.

        Args:
            secret_name: The name of the secret.
            scope: The scope of the secret.
            workspace: The ID of the workspace to which the secret belongs.
            user: The ID of the user to which the secret belongs.
            exclude_secret_id: The ID of a secret to exclude from the check
                (used e.g. during an update to exclude the existing secret).

        Returns:
            True if a secret with the given name already exists in the given
            scope, False otherwise, and an error message.
        """
        filter = SecretFilterModel(
            name=secret_name,
            scope=scope,
            page=1,
            size=2,  # We only need to know if there is more than one secret
        )

        if scope in [SecretScope.WORKSPACE, SecretScope.USER]:
            filter.workspace_id = workspace
        if scope == SecretScope.USER:
            filter.user_id = user

        existing_secrets = self.list_secrets(secret_filter_model=filter).items
        if exclude_secret_id is not None:
            existing_secrets = [
                s for s in existing_secrets if s.id != exclude_secret_id
            ]

        if existing_secrets:
            existing_secret_model = existing_secrets[0]

            msg = (
                f"Found an existing {scope.value} scoped secret with the "
                f"same '{secret_name}' name"
            )
            if scope in [SecretScope.WORKSPACE, SecretScope.USER]:
                msg += (
                    f" in the same '{existing_secret_model.workspace.name}' "
                    f"workspace"
                )
            if scope == SecretScope.USER:
                assert existing_secret_model.user
                msg += (
                    f" for the same '{existing_secret_model.user.name}' user"
                )

            return True, msg

        return False, ""

    # --------------------------------------------------------
    # Helpers for Secrets Store back-ends that use tags/labels
    # --------------------------------------------------------

    def _get_secret_metadata(
        self,
        secret_id: Optional[UUID] = None,
        secret_name: Optional[str] = None,
        scope: Optional[SecretScope] = None,
        workspace: Optional[UUID] = None,
        user: Optional[UUID] = None,
    ) -> Dict[str, str]:
        """Get a dictionary with metadata that can be used as tags/labels.

        This utility method can be used with Secrets Managers that can
        associate metadata (e.g. tags, labels) with a secret. The metadata can
        be configured alongside each secret and then used as a filter criteria
        when running queries against the backend e.g. to retrieve all the
        secrets within a given scope or to retrieve all secrets with a given
        name within a given scope.

        NOTE: the ZENML_SECRET_LABEL is always included in the metadata to
        distinguish ZenML secrets from other secrets that might be stored in
        the same backend, as well as to distinguish between different ZenML
        deployments using the same backend. Its value is set to the ZenML
        deployment ID and it should be included in all queries to the backend.

        Args:
            secret_id: Optional secret ID to include in the metadata.
            secret_name: Optional secret name to include in the metadata.
            scope: Optional scope to include in the metadata.
            workspace: Optional workspace ID to include in the metadata.
            user: Optional user ID to include in the scope metadata.

        Returns:
            Dictionary with secret metadata information.
        """
        # Always include the main ZenML label to distinguish ZenML secrets
        # from other secrets that might be stored in the same backend and
        # to distinguish between different ZenML deployments using the same
        # backend.
        metadata: Dict[str, str] = {
            ZENML_SECRET_LABEL: str(self.zen_store.get_store_info().id)
        }

        if secret_id:
            metadata[ZENML_SECRET_ID_LABEL] = str(secret_id)
        if secret_name:
            metadata[ZENML_SECRET_NAME_LABEL] = secret_name
        if scope:
            metadata[ZENML_SECRET_SCOPE_LABEL] = scope.value
        if workspace:
            metadata[ZENML_SECRET_WORKSPACE_LABEL] = str(workspace)
        if user:
            metadata[ZENML_SECRET_USER_LABEL] = str(user)

        return metadata

    def _get_secret_metadata_for_secret(
        self,
        secret: Union[SecretRequestModel, SecretResponseModel],
        secret_id: Optional[UUID] = None,
    ) -> Dict[str, str]:
        """Get a dictionary with the secrets metadata describing a secret.

        This utility method can be used with Secrets Managers that can
        associate metadata (e.g. tags, labels) with a secret. The metadata can
        be configured alongside each secret and then used as a filter criteria
        when running queries against the backend.

        Args:
            secret: The secret to get the metadata for.
            secret_id: Optional secret ID to include in the metadata (if not
                already included in the secret).

        Returns:
            Dictionary with secret metadata information.
        """
        if isinstance(secret, SecretRequestModel):
            return self._get_secret_metadata(
                secret_id=secret_id,
                secret_name=secret.name,
                scope=secret.scope,
                workspace=secret.workspace,
                user=secret.user,
            )

        return self._get_secret_metadata(
            secret_id=secret.id,
            secret_name=secret.name,
            scope=secret.scope,
            workspace=secret.workspace.id,
            user=secret.user.id if secret.user else None,
        )

    def _create_secret_from_metadata(
        self,
        metadata: Dict[str, str],
        created: datetime,
        updated: datetime,
        values: Optional[Dict[str, str]] = None,
    ) -> SecretResponseModel:
        """Create a ZenML secret model from metadata stored in the secrets store backend.

        Args:
            metadata: ZenML secret metadata collected from the backend secret
                (e.g. from secret tags/labels).
            created: The secret creation time.
            updated: The secret last updated time.
            values: The secret values (optional).

        Returns:
            The ZenML secret.

        Raises:
            KeyError: If the secret does not have the required metadata, if it
                is not managed by this ZenML instance or if it is linked to a
                user or workspace that no longer exists.
        """
        # Double-check that the secret is managed by this ZenML instance.
        if metadata.get(ZENML_SECRET_LABEL) != str(
            self.zen_store.get_store_info().id
        ):
            raise KeyError("Secret is not managed by this ZenML instance")

        # Recover the ZenML secret fields from the input secret metadata.
        try:
            secret_id = UUID(metadata[ZENML_SECRET_ID_LABEL])
            name = metadata[ZENML_SECRET_NAME_LABEL]
            scope = SecretScope(metadata[ZENML_SECRET_SCOPE_LABEL])
            workspace_id = UUID(metadata[ZENML_SECRET_WORKSPACE_LABEL])
            user_id = UUID(metadata[ZENML_SECRET_USER_LABEL])
        except KeyError as e:
            raise KeyError(
                f"Secret could not be retrieved: missing required metadata: {e}"
            )

        try:
            user, workspace = self._validate_user_and_workspace(
                user_id, workspace_id
            )
        except KeyError as e:
            # The user or workspace associated with the secret no longer
            # exists. This can happen if the user or workspace is being
            # deleted nearly at the same time as this call. In this case, we
            # raise a KeyError exception. The caller should handle this
            # exception by assuming that the secret no longer exists.
            logger.warning(
                f"Secret with ID {secret_id} is associated with a "
                f"non-existent user or workspace. Silently ignoring the "
                f"secret: {e}"
            )
            raise KeyError(
                f"Secret with ID {secret_id} could not be retrieved: "
                f"the secret is associated with a non-existent user or "
                f"workspace: {e}"
            )

        secret_model = SecretResponseModel(
            id=secret_id,
            name=name,
            scope=scope,
            workspace=workspace,
            user=user,
            values=values if values else {},
            created=created,
            updated=updated,
        )

        return secret_model

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment = True
        # Ignore extra attributes from configs of previous ZenML versions
        extra = "ignore"
        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True
