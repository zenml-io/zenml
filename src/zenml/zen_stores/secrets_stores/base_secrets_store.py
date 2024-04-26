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
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.enums import SecretsStoreType
from zenml.logger import get_logger
from zenml.utils import source_utils
from zenml.utils.pydantic_utils import before_validator_handler
from zenml.zen_stores.secrets_stores.secrets_store_interface import (
    SecretsStoreInterface,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.zen_stores.base_zen_store import BaseZenStore

ZENML_SECRET_LABEL = "zenml"
ZENML_SECRET_ID_LABEL = "zenml_secret_id"
ZENML_SECRET_NAME_LABEL = "zenml_secret_name"


class BaseSecretsStore(BaseModel, SecretsStoreInterface, ABC):
    """Base class for accessing and persisting ZenML secret values.

    Attributes:
        config: The configuration of the secret store.
        _zen_store: The ZenML store that owns this secrets store.
    """

    config: SecretsStoreConfiguration
    _zen_store: Optional["BaseZenStore"] = None

    TYPE: ClassVar[SecretsStoreType]
    CONFIG_TYPE: ClassVar[Type[SecretsStoreConfiguration]]

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def convert_config(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Method to infer the correct type of the config and convert.

        Args:
            data: The provided configuration object, can potentially be a
                generic object

        Raises:
            ValueError: If the provided config object's type does not match
                any of the current implementations.

        Returns:
            The converted configuration object.
        """
        if data["config"].type == SecretsStoreType.SQL:
            from zenml.zen_stores.secrets_stores.sql_secrets_store import (
                SqlSecretsStoreConfiguration,
            )

            data["config"] = SqlSecretsStoreConfiguration(
                **data["config"].model_dump()
            )

        elif data["config"].type == SecretsStoreType.GCP:
            from zenml.zen_stores.secrets_stores.gcp_secrets_store import (
                GCPSecretsStoreConfiguration,
            )

            data["config"] = GCPSecretsStoreConfiguration(
                **data["config"].model_dump()
            )

        elif data["config"].type == SecretsStoreType.AWS:
            from zenml.zen_stores.secrets_stores.aws_secrets_store import (
                AWSSecretsStoreConfiguration,
            )

            data["config"] = AWSSecretsStoreConfiguration(
                **data["config"].model_dump()
            )

        elif data["config"].type == SecretsStoreType.AZURE:
            from zenml.zen_stores.secrets_stores.azure_secrets_store import (
                AzureSecretsStoreConfiguration,
            )

            data["config"] = AzureSecretsStoreConfiguration(
                **data["config"].model_dump()
            )

        elif data["config"].type == SecretsStoreType.HASHICORP:
            from zenml.zen_stores.secrets_stores.hashicorp_secrets_store import (
                HashiCorpVaultSecretsStoreConfiguration,
            )

            data["config"] = HashiCorpVaultSecretsStoreConfiguration(
                **data["config"].model_dump()
            )
        elif (
            data["config"].type == SecretsStoreType.CUSTOM
            or data["config"].type == SecretsStoreType.NONE
        ):
            pass
        else:
            raise ValueError(
                f"Unknown type '{data['config'].type}' for the configuration."
            )

        return data

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

    # --------------------------------------------------------
    # Helpers for Secrets Store back-ends that use tags/labels
    # --------------------------------------------------------

    def _get_secret_metadata(
        self,
        secret_id: Optional[UUID] = None,
    ) -> Dict[str, str]:
        """Get a dictionary with metadata that can be used as tags/labels.

        This utility method can be used with Secrets Managers that can
        associate metadata (e.g. tags, labels) with a secret. The metadata can
        be configured alongside each secret.

        NOTE: the ZENML_SECRET_LABEL is always included in the metadata to
        distinguish ZenML secrets from other secrets that might be stored in
        the same backend, as well as to distinguish between different ZenML
        deployments using the same backend. Its value is set to the ZenML
        deployment ID.

        Args:
            secret_id: Optional secret ID to include in the metadata.

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

        # Include the secret ID if provided.
        if secret_id is not None:
            metadata[ZENML_SECRET_ID_LABEL] = str(secret_id)

        return metadata

    def _verify_secret_metadata(
        self,
        secret_id: UUID,
        metadata: Dict[str, str],
    ) -> None:
        """Verify that the given metadata corresponds to a valid ZenML secret.

        Args:
            secret_id: The ID of the secret.
            metadata: ZenML secret metadata collected from the backend secret
                (e.g. from secret tags/labels).

        Raises:
            KeyError: If the secret does not have the required metadata or if it
                is not managed by this ZenML instance.
        """
        # Double-check that the secret is managed by this ZenML instance.
        if metadata.get(ZENML_SECRET_LABEL) != str(
            self.zen_store.get_store_info().id
        ):
            raise KeyError("Secret is not managed by this ZenML instance")

        # Recover the ZenML secret fields from the input secret metadata.
        try:
            stored_secret_id = UUID(metadata[ZENML_SECRET_ID_LABEL])
        except KeyError as e:
            raise KeyError(
                f"Secret could not be retrieved: missing required metadata: {e}"
            )

        if secret_id != stored_secret_id:
            raise KeyError(
                f"Secret could not be retrieved: secret ID mismatch: "
                f"expected {secret_id}, got {stored_secret_id}"
            )

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
    )
