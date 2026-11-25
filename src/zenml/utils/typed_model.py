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
from typing import Any, Dict

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from typing_extensions import Literal

from zenml.utils import source_utils


class BaseTypedModel(BaseModel):
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

    type: str = "zenml.utils.typed_model.BaseTypedModel"

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Upgrade `type` to a Literal of the subclass's fully-qualified path.

        Args:
            **kwargs: Extra keyword arguments passed to the class definition.

        Raises:
            TypeError: If the subclass tries to declare `type` itself.
        """
        super().__pydantic_init_subclass__(**kwargs)

        if "type" in cls.__dict__.get("__annotations__", {}):
            raise TypeError(
                "`type` is a reserved attribute name for BaseTypedModel "
                "subclasses"
            )

        type_name = f"{cls.__module__}.{cls.__qualname__}"
        cls.model_fields["type"] = FieldInfo(
            annotation=Literal[type_name],  # type: ignore[arg-type]
            default=type_name,
        )
        cls.model_rebuild(force=True)

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
