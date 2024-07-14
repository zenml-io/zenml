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
"""Utility classes for adding type information to Pydantic models."""

import json
from typing import Any, Dict, Tuple, Type, cast

from pydantic import BaseModel, Field

# TODO: Investigate if we can solve this import a different way.
from pydantic._internal._model_construction import ModelMetaclass
from typing_extensions import Literal

from zenml.utils import source_utils


class BaseTypedModelMeta(ModelMetaclass):
    """Metaclass responsible for adding type information to Pydantic models."""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "BaseTypedModelMeta":
        """Creates a Pydantic BaseModel class.

        This includes a hidden attribute that reflects the full class
        identifier.

        Args:
            name: The name of the class.
            bases: The base classes of the class.
            dct: The class dictionary.

        Returns:
            A Pydantic BaseModel class that includes a hidden attribute that
            reflects the full class identifier.

        Raises:
            TypeError: If the class is not a Pydantic BaseModel class.
        """
        if "type" in dct:
            raise TypeError(
                "`type` is a reserved attribute name for BaseTypedModel "
                "subclasses"
            )
        type_name = f"{dct['__module__']}.{dct['__qualname__']}"
        type_ann = Literal[type_name]  # type: ignore[valid-type]
        type = Field(type_name)
        dct.setdefault("__annotations__", dict())["type"] = type_ann
        dct["type"] = type
        cls = cast(
            Type["BaseTypedModel"], super().__new__(mcs, name, bases, dct)
        )
        return cls


class BaseTypedModel(BaseModel, metaclass=BaseTypedModelMeta):
    """Typed Pydantic model base class.

    Use this class as a base class instead of BaseModel to automatically
    add a `type` literal attribute to the model that stores the name of the
    class.

    This can be useful when serializing models to JSON and then de-serializing
    them as part of a submodel union field, e.g.:

    ```python

    class BluePill(BaseTypedModel):
        ...

    class RedPill(BaseTypedModel):
        ...

    class TheMatrix(BaseTypedModel):
        choice: Union[BluePill, RedPill] = Field(..., discriminator='type')

    matrix = TheMatrix(choice=RedPill())
    d = matrix.dict()
    new_matrix = TheMatrix.model_validate(d)
    assert isinstance(new_matrix.choice, RedPill)
    ```

    It can also facilitate de-serializing objects when their type isn't known:

    ```python
    matrix = TheMatrix(choice=RedPill())
    d = matrix.dict()
    new_matrix = BaseTypedModel.from_dict(d)
    assert isinstance(new_matrix.choice, RedPill)
    ```
    """

    @classmethod
    def from_dict(
        cls,
        model_dict: Dict[str, Any],
    ) -> "BaseTypedModel":
        """Instantiate a Pydantic model from a serialized JSON-able dict representation.

        Args:
            model_dict: the model attributes serialized as JSON-able dict.

        Returns:
            A BaseTypedModel created from the serialized representation.

        Raises:
            RuntimeError: if the model_dict contains an invalid type.
        """
        model_type = model_dict.get("type")
        if not model_type:
            raise RuntimeError(
                "`type` information is missing from the serialized model dict."
            )
        cls = source_utils.load(model_type)
        if not issubclass(cls, BaseTypedModel):
            raise RuntimeError(
                f"Class `{cls}` is not a ZenML BaseTypedModel subclass."
            )

        return cls.model_validate(model_dict)

    @classmethod
    def from_json(
        cls,
        json_str: str,
    ) -> "BaseTypedModel":
        """Instantiate a Pydantic model from a serialized JSON representation.

        Args:
            json_str: the model attributes serialized as JSON.

        Returns:
            A BaseTypedModel created from the serialized representation.
        """
        model_dict = json.loads(json_str)
        return cls.from_dict(model_dict)
