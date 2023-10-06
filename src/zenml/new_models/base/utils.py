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
from typing import TYPE_CHECKING, Type, TypeVar

if TYPE_CHECKING:
    from zenml.new_models.base.base_models import BaseResponseModel

T = TypeVar("T", bound="BaseRequestModel")


def update_model(_cls: Type[T]) -> Type[T]:
    """Base update model.

    This is used as a decorator on top of request models to convert them
    into update models where the fields are optional and can be set to None.

    Args:
        _cls: The class to decorate

    Returns:
        The decorated class.
    """
    for _, value in _cls.__fields__.items():
        value.required = False
        value.allow_none = True

    return _cls


def generate_property(name):
    """Generates a property specifically for response model metadata.

    Args:
        name: the name of the property

    Returns:
        the property that returns the corresponding field in the metadata.
    """

    def wrapper(instance: "BaseResponseModel"):
        """The wrapper function to base the property on.

        It makes sure that the metadata fields of the response model is
        populated and returns the corresponding field.

        Args:
            instance: the instance of the response model.

        Returns:
            the corresponding fields in the metadata of the instance.
        """
        if instance.metadata is None:
            instance.metadata = instance.get_metadata()
        return getattr(instance.metadata, name)

    return property(wrapper)
