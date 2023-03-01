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
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional, Type, Union

from pydantic import BaseModel

from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.enums import SecretsStoreType
from zenml.logger import get_logger
from zenml.utils.analytics_utils import (
    AnalyticsEvent,
    AnalyticsTrackerMixin,
    track_event,
)
from zenml.zen_stores.secrets_stores.secrets_store_interface import (
    SecretsStoreInterface,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.zen_stores.base_zen_store import BaseZenStore


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
    def get_store_class(
        store_type: SecretsStoreType,
    ) -> Type["BaseSecretsStore"]:
        """Returns the class of the given secrets store type.

        Args:
            store_type: The type of the secrets store to get the class for.

        Returns:
            The class of the given store type or None if the type is unknown.

        Raises:
            TypeError: If the secrets store type is unsupported.
        """
        if store_type == SecretsStoreType.SQL:
            from zenml.zen_stores.secrets_stores.sql_secrets_store import (
                SqlSecretsStore,
            )

            return SqlSecretsStore
        elif store_type == SecretsStoreType.REST:
            from zenml.zen_stores.secrets_stores.rest_secrets_store import (
                RestSecretsStore,
            )

            return RestSecretsStore
        else:
            raise TypeError(
                f"No store implementation found for secrets store type "
                f"`{store_type.value}`."
            )

    @staticmethod
    def get_store_config_class(
        store_type: SecretsStoreType,
    ) -> Type["SecretsStoreConfiguration"]:
        """Returns the secrets store config class of the given secrets store type.

        Args:
            store_type: The type of the secrets store to get the class for.

        Returns:
            The config class of the given secrets store type.
        """
        store_class = BaseSecretsStore.get_store_class(store_type)
        return store_class.CONFIG_TYPE

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
        store_class = BaseSecretsStore.get_store_class(config.type)
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
