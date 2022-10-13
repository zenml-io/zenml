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
