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
from abc import ABC
from typing import Any, ClassVar, Dict, List

from pydantic import BaseModel


class BaseSecretSchema(BaseModel, ABC):
    name: str
    TYPE: ClassVar[str]

    @property
    def content(self) -> Dict[str, Any]:
        """The concept of SecretSchemas supports strongly typed
        secret schemas as well as arbitrary collections of key-value pairs.
        This property unifies all attributes into a content dictionary.

        Returns:
            A dictionary containing the content of the SecretSchema.
        """
        fields_dict = self.dict(exclude_none=True)
        fields_dict.pop("name")
        if "arbitrary_kv_pairs" in fields_dict:
            arbitrary_kv_pairs = fields_dict.pop("arbitrary_kv_pairs")
            fields_dict.update(arbitrary_kv_pairs)
        return fields_dict

    @classmethod
    def get_schema_keys(cls) -> List[str]:
        """Get all attribute keys that are not part of the ignored set.
        These schema keys can be used to define all
        required key-value pairs of a secret schema

        Returns:
            A list of all attribute keys that are not part of the ignored set.
        """

        ignored_keys = ["name", "arbitrary_kv_pairs"]
        return [
            schema_key
            for schema_key in cls.__fields__.keys()
            if schema_key not in ignored_keys
        ]

    class Config:
        """Pydantic configuration class."""

        # validate attribute assignments
        validate_assignment = True
        # report extra attributes as validation failures
        extra = "forbid"
