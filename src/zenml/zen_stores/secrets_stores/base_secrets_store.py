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
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Optional,
    Type,
    Union,
)
from uuid import UUID

from pydantic import BaseModel

from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.enums import SecretScope, SecretsStoreType
from zenml.logger import get_logger
from zenml.models.secret_models import SecretRequestModel, SecretResponseModel
from zenml.utils.analytics_utils import (
    AnalyticsEvent,
    AnalyticsTrackerMixin,
    track_event,
)
from zenml.utils.source_utils import import_class_by_path
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


class BaseSecretsStore(
    BaseModel, SecretsStoreInterface, AnalyticsTrackerMixin, ABC
):
    """Base class for accessing and persisting ZenML secret objects.

    Attributes:
        config: The configuration of the secret store.
        track_analytics: Only send analytics if set to `True`.
        _zen_store: The ZenML store that owns this secrets store.
    """

    config: SecretsStoreConfiguration
    track_analytics: bool = True
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

        try:
            self._initialize()
        except Exception as e:
            raise RuntimeError(
                f"Error initializing {self.type.value} secrets store: {str(e)}"
            ) from e

    @staticmethod
    def _load_external_store_class(
        store_config: SecretsStoreConfiguration,
    ) -> Type["BaseSecretsStore"]:
        """Loads the external secrets store class from the given config.

        Args:
            store_config: The configuration of the secrets store.

        Returns:
            The secrets store class corresponding to the configured external
            secrets store.

        Raises:
            ValueError: If the secrets store integration is not found, if
                the integration is not installed, or if the configured class
                path cannot be imported or is not a subclass of
                `BaseSecretsStore`.
        """
        if store_config.integration:
            from zenml.integrations.registry import integration_registry

            integration = integration_registry.integrations.get(
                store_config.integration
            )

            if not integration:
                raise ValueError(
                    f"Integration {store_config.integration} was not found "
                    f"in registry."
                )

            if not integration.check_installation():
                raise ValueError(
                    f"Integration {store_config.integration} is not "
                    f"installed. Check that all the requirements are "
                    f"present in your environment."
                )

            integration.activate()

        # Ensured through Pydantic root validation
        assert store_config.class_path is not None

        # Import the class dynamically
        try:
            store_class = import_class_by_path(store_config.class_path)
        except (ImportError, AttributeError) as e:
            raise ValueError(
                f"Could not import class `{store_config.class_path}`: {str(e)}"
            ) from e

        if not issubclass(store_class, BaseSecretsStore):
            raise ValueError(
                f"Class `{store_config.class_path}` is not a subclass of "
                f"`BaseSecretsStore`."
            )

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
            ValueError: If the secrets store integration is not found.
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
            store_config.integration = "aws"
            store_config.class_path = (
                "zenml.integrations.aws.secrets_stores.AWSSecretsStore"
            )
        elif store_config.type == SecretsStoreType.GCP:
            store_config.integration = "gcp"
            store_config.class_path = (
                "zenml.integrations.gcp.secrets_stores.GCPSecretsStore"
            )
        elif store_config.type != SecretsStoreType.CUSTOM:
            raise TypeError(
                f"No store implementation found for secrets store type "
                f"`{store_config.type.value}`."
            )

        return BaseSecretsStore._load_external_store_class(store_config)

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

    # ---------
    # Analytics
    # ---------

    def track_event(
        self,
        event: Union[str, AnalyticsEvent],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track an analytics event.

        Args:
            event: The event to track.
            metadata: Additional metadata to track with the event.
        """
        if self.track_analytics:
            # Server information is always tracked, if available.
            track_event(event, metadata)

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
