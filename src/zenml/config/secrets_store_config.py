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
"""Functionality to support ZenML secrets store configurations."""


from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, root_validator

from zenml.enums import SecretsStoreType
from zenml.logger import get_logger

logger = get_logger(__name__)


class SecretsStoreConfiguration(BaseModel):
    """Generic secrets store configuration.

    The store configurations of concrete secrets store implementations must
    inherit from this class and validate any extra attributes that are
    configured in addition to those defined in this class.

    Attributes:
        type: The type of store backend.
        class_path: The Python class path of the store backend. Should point to
            a subclass of `BaseSecretsStore`. This is optional and only
            required if the store backend is not one of the built-in
            implementations.
    """

    type: SecretsStoreType
    class_path: Optional[str] = None

    @root_validator
    def validate_custom(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that class_path is set for custom secrets stores.

        Args:
            values: Dict representing user-specified runtime settings.

        Returns:
            Validated settings.

        Raises:
            ValueError: If class_path is not set when using an custom secrets
                store.
        """
        if not values.get("type"):
            return values
        if values["type"] == SecretsStoreType.CUSTOM:
            if values["class_path"] is None:
                raise ValueError(
                    "A class_path must be set when using a custom secrets "
                    "store implementation."
                )
        elif values["class_path"] is not None:
            raise ValueError(
                f"The class_path attribute is not supported for the "
                f"{values['type']} secrets store type."
            )

        return values

    # TODO[pydantic]: The following keys were removed: `underscore_attrs_are_private`.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow",
        underscore_attrs_are_private=True,
    )
