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
"""Functionality to support ZenML store configurations."""

from pathlib import PurePath
from typing import Optional

from pydantic import BaseModel

from zenml.enums import StoreType
from zenml.logger import get_logger

logger = get_logger(__name__)


class StoreConfiguration(BaseModel):
    """Generic store configuration.

    The store configurations of concrete store implementations must inherit from
    this class and validate any extra attributes that are configured in addition
    to those defined in this class.

    Attributes:
        type: The type of store backend.
        url: The URL of the store backend.
    """

    type: StoreType
    url: str

    @classmethod
    def copy_configuration(
        cls,
        config: "StoreConfiguration",
        config_path: str,
        load_config_path: Optional[PurePath] = None,
    ) -> "StoreConfiguration":
        """Create a copy of the store config using a different configuration path.

        This method is used to create a copy of the store configuration that can
        be loaded using a different configuration path or in the context of a
        new environment, such as a container image.

        The configuration files accompanying the store configuration are also
        copied to the new configuration path (e.g. certificates etc.).

        Args:
            config: The store configuration to copy.
            config_path: new path where the configuration copy will be loaded
                from.
            load_config_path: absolute path that will be used to load the copied
                configuration. This can be set to a value different from
                `config_path` if the configuration copy will be loaded from
                a different environment, e.g. when the configuration is copied
                to a container image and loaded using a different absolute path.
                This will be reflected in the paths and URLs encoded in the
                copied configuration.

        Returns:
            A new store configuration object that reflects the new configuration
            path.
        """
        return config.copy()

    @classmethod
    def supports_url_scheme(cls, url: str) -> bool:
        """Check if a URL scheme is supported by this store.

        Concrete store configuration classes should override this method to
        check if a URL scheme is supported by the store.

        Args:
            url: The URL to check.

        Returns:
            True if the URL scheme is supported, False otherwise.
        """
        return True

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment = True
        # Allow extra attributes to be set in the base class. The concrete
        # classes are responsible for validating the attributes.
        extra = "allow"
        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True
