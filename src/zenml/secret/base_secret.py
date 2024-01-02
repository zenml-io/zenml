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
"""Implementation of the Base SecretSchema class."""

from typing import Any, Dict, List

from pydantic import BaseModel


class BaseSecretSchema(BaseModel):
    """Base class for all Secret Schemas."""

    @classmethod
    def get_schema_keys(cls) -> List[str]:
        """Get all attributes that are part of the schema.

        These schema keys can be used to define all required key-value pairs of
        a secret schema.

        Returns:
            A list of all attribute names that are part of the schema.
        """
        return list(cls.__fields__.keys())

    def get_values(self) -> Dict[str, Any]:
        """Get all values of the secret schema.

        Returns:
            A dictionary of all attribute names and their corresponding values.
        """
        return self.dict(exclude_none=True)

    class Config:
        """Pydantic configuration class."""

        # validate attribute assignments
        validate_assignment = True
        # report extra attributes as validation failures
        extra = "forbid"
