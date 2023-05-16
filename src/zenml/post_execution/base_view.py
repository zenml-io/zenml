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
"""Base classes for post-execution views."""

from abc import ABC, abstractmethod
from typing import Any, List

from zenml.models.base_models import BaseResponseModel


class BaseView(ABC):
    """Base class for post-execution views.

    Subclasses should override the following attributes/methods:
    - `MODEL_CLASS` should be set to the model class the subclass is wrapping.
    - The `model` property should return `self._model` cast to the correct type.
    - (Optionally) `REPR_KEYS` can be set to include a list of custom attributes
        in the `__repr__` method.
    """

    MODEL_CLASS = BaseResponseModel  # The model class to wrap.
    REPR_KEYS = ["id"]  # Keys to include in the `__repr__` method.

    def __init__(self, model: BaseResponseModel):
        """Initializes a view for the given model.

        Args:
            model: The model to create a view for.

        Raises:
            TypeError: If the model is not of the correct type.
            ValueError: If any of the `REPR_KEYS` are not valid.
        """
        # Check that the model is of the correct type.
        if not isinstance(model, self.MODEL_CLASS):
            raise TypeError(
                f"Model of {self.__class__.__name__} must be of type "
                f"{self.MODEL_CLASS.__name__} but is {type(model).__name__}."
            )

        # Validate that all `REPR_KEYS` are valid.
        for key in self.REPR_KEYS:
            if (
                key not in model.__fields__
                and key not in self._custom_view_properties
            ):
                raise ValueError(
                    f"Key {key} in {self.__class__.__name__}.REPR_KEYS is "
                    f"neither a field of {self.MODEL_CLASS.__name__} nor a "
                    f"custom property of {self.__class__.__name__}."
                )

        self._model = model

    @property
    def _custom_view_properties(self) -> List[str]:
        """Returns a list of custom view properties.

        Returns:
            A list of custom view properties.
        """
        return [attr for attr in dir(self) if not attr.startswith("__")]

    @property
    @abstractmethod
    def model(self) -> BaseResponseModel:
        """Returns the underlying model.

        Subclasses should override this property to return `self._model` with
        the correct model type.

        E.g. `return cast(ArtifactResponseModel, self._model)`

        Returns:
            The underlying model.
        """

    def __getattribute__(self, __name: str) -> Any:
        """Returns the attribute with the given name.

        This method is overridden so we can access the model fields as if they
        were attributes of this class.

        Args:
            __name: The name of the attribute to return.

        Returns:
            The attribute with the given name.
        """
        # Handle special cases that are required by the `dir` call below
        if __name in {"__dict__", "__class__"}:
            return super().__getattribute__(__name)

        # Check the custom view properties first in case of overwrites
        if __name in {attr for attr in dir(self) if not attr.startswith("__")}:
            return super().__getattribute__(__name)

        # Then check if the attribute is a field in the model
        if __name in self._model.__fields__:
            return getattr(self._model, __name)

        # Otherwise, fall back to the default behavior
        return super().__getattribute__(__name)

    def __repr__(self) -> str:
        """Returns a string representation of this artifact.

        The string representation is of the form
        `__qualname__(<key1>=<value1>, <key2>=<value2>, ...)` where the keys
        are the ones specified in `REPR_KEYS`.

        Returns:
            A string representation of this artifact.
        """
        repr = self.__class__.__qualname__
        repr_key_strs = [
            f"{key}={getattr(self, key)}" for key in self.REPR_KEYS
        ]
        details = ", ".join(repr_key_strs)
        if details:
            repr += f"({details})"
        return repr

    def __eq__(self, other: Any) -> bool:
        """Returns whether the other object is referring to the same model.

        Args:
            other: The other object to compare to.

        Returns:
            True if the other object is referring to the same model, else False.
        """
        if not isinstance(other, self.__class__):
            return False
        return self._model == other._model  # Use the model's `__eq__` method.
