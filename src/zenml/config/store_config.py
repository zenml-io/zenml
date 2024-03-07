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

from typing import Any, Dict, Optional

from pydantic import BaseModel, root_validator

from zenml.config.secrets_store_config import SecretsStoreConfiguration
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
        secrets_store: The configuration of the secrets store to use to store
            secrets. If not set, secrets management is disabled.
        backup_secrets_store: The configuration of the secrets store to use to
            store backups of secrets. If not set, backup and restore of secrets
            are disabled.
    """

    type: StoreType
    url: str
    secrets_store: Optional[SecretsStoreConfiguration] = None
    backup_secrets_store: Optional[SecretsStoreConfiguration] = None

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

    @root_validator(pre=True)
    def validate_secrets_store(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the secrets store configuration.

        Args:
            values: The values of the store configuration.

        Returns:
            The values of the store configuration.
        """
        if values.get("secrets_store") is None:
            return values

        # Remove the legacy REST secrets store configuration since it is no
        # longer supported/needed
        secrets_store = values["secrets_store"]
        if isinstance(secrets_store, dict):
            secrets_store_type = secrets_store.get("type")
            if secrets_store_type == "rest":
                del values["secrets_store"]

        return values

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
