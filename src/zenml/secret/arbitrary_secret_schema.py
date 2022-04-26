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
from typing import Any, ClassVar, Dict

from pydantic import root_validator

from zenml.secret.base_secret import BaseSecretSchema

ARBITRARY_SECRET_SCHEMA_TYPE = "arbitrary"


class ArbitrarySecretSchema(BaseSecretSchema):
    """Schema for arbitrary collections of key value pairs with no
    predefined schema."""

    TYPE: ClassVar[str] = ARBITRARY_SECRET_SCHEMA_TYPE

    arbitrary_kv_pairs: Dict[str, Any]

    @root_validator(pre=True)
    def build_arbitrary_kv_pairs(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Pydantic root_validator that takes all unused passed kwargs
        and passes them into the arbitrary_kv_pairs attribute.

        Args:
            values: Values passed to the object constructor

        Returns:
            Values passed to the object constructor
        """
        all_required_field_names = {
            field.alias
            for field in cls.__fields__.values()
            if field.alias != "arbitrary_kv_pairs"
        }

        arbitrary_kv_pairs: Dict[str, Any] = {
            field_name: values.pop(field_name)
            for field_name in list(values)
            if field_name not in all_required_field_names
        }

        values["arbitrary_kv_pairs"] = arbitrary_kv_pairs
        return values
