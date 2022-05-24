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

import os
from typing import TYPE_CHECKING, Any, Dict, Optional

import requests
from pydantic import BaseModel, Field, root_validator

from zenml.constants import (
    ENV_ZENML_ACTIVATED_STACK,
    ENV_ZENML_DEFAULT_STORE_TYPE,
)
from zenml.enums import StoreType
from zenml.io import fileio
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.global_config import GlobalConfiguration


logger = get_logger(__name__)


DEFAULT_PROFILE_NAME = "default"


def get_default_store_type() -> StoreType:
    """Return the default store type.

    The default store type can be set via the environment variable
    ZENML_DEFAULT_STORE_TYPE. If this variable is not set, the default
    store type is set to 'LOCAL'.

    NOTE: this is a global function instead of a default
    `ProfileConfiguration.store_type` value because it makes it easier to mock
    in the unit tests.

    Returns:
        The default store type.
    """
    store_type = os.getenv(ENV_ZENML_DEFAULT_STORE_TYPE)
    if store_type and store_type in StoreType.values():
        return StoreType(store_type)
    return StoreType.LOCAL


class ProfileConfiguration(BaseModel):
    """Stores configuration profile options.

    Attributes:
        name: Name of the profile.
        active_user: Name of the active user.
        store_url: URL pointing to the ZenML store backend.
        store_type: Type of the store backend.
        active_stack: Optional name of the active stack.
        _config: global configuration to which this profile belongs.
    """

    name: str
    active_user: str
    store_url: Optional[str]
    store_type: StoreType = Field(default_factory=get_default_store_type)
    active_stack: Optional[str]
    _config: Optional["GlobalConfiguration"]

    def __init__(
        self, config: Optional["GlobalConfiguration"] = None, **kwargs: Any
    ) -> None:
        """Initializes a ProfileConfiguration object.

        Args:
            config: global configuration to which this profile belongs. When not
                specified, the default global configuration path is used.
            **kwargs: additional keyword arguments are passed to the
                BaseModel constructor.
        """
        self._config = config
        super().__init__(**kwargs)

    @property
    def config_directory(self) -> str:
        """Directory where the profile configuration is stored."""
        return os.path.join(
            self.global_config.config_directory, "profiles", self.name
        )

    def initialize(self) -> None:
        """Initialize the profile."""

        # import here to avoid circular dependency
        from zenml.repository import Repository

        logger.info("Initializing profile `%s`...", self.name)

        # Create and initialize the profile using a special repository instance.
        # This also validates and updates the store URL configuration and
        # creates all necessary resources (e.g. paths, initial DB, default
        # stacks).
        repo = Repository(profile=self)

        if not self.active_stack:
            try:
                stacks = repo.stack_configurations
            except requests.exceptions.ConnectionError:
                stacks = None
            if stacks:
                self.active_stack = list(stacks.keys())[0]

    def cleanup(self) -> None:
        """Cleanup the profile directory."""
        if fileio.isdir(self.config_directory):
            fileio.rmtree(self.config_directory)

    @property
    def global_config(self) -> "GlobalConfiguration":
        """Return the global configuration to which this profile belongs."""
        from zenml.config.global_config import GlobalConfiguration

        return self._config or GlobalConfiguration()

    def get_active_stack(self) -> Optional[str]:
        """Get the active stack for the profile.

        Returns:
            The name of the active stack or None if no stack is active.
        """
        return os.getenv(ENV_ZENML_ACTIVATED_STACK, self.active_stack)

    def activate_stack(self, stack_name: str) -> None:
        """Set the active stack for the profile.

        Args:
            stack_name: name of the stack to activate
        """
        self.active_stack = stack_name
        self.global_config._write_config()

    def activate_user(self, user_name: str) -> None:
        """Set the active user for the profile.

        Args:
            user_name: name of the user to activate
        """
        self.active_user = user_name
        self.global_config._write_config()

    @root_validator(pre=True)
    def _ensure_active_user_is_set(
        cls, attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ensures that an active user is set for this profile.

        If the active user is missing and the profile specifies a local store,
        a default user is used as fallback.

        Raises:
            RuntimeError: If the active user is missing for a profile with a
                REST ZenStore.
        """
        store_type = attributes.get("store_type") or get_default_store_type()

        if (
            store_type != StoreType.REST
            and attributes.get("active_user") is None
        ):
            # in case of a local store, fallback to the default user that is
            # created when initializing the store
            from zenml.zen_stores.base_zen_store import DEFAULT_USERNAME

            attributes["active_user"] = DEFAULT_USERNAME

        if not attributes.get("active_user"):
            raise RuntimeError(
                f"Active user missing for profile '{attributes['name']}'."
            )

        if store_type == StoreType.REST and attributes.get("store_url") is None:
            raise RuntimeError(
                f"Store URL missing for profile '{attributes['name']}'."
            )

        return attributes

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
