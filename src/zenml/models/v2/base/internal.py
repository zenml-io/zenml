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
"""Utility methods for internal models."""

from typing import Type, TypeVar

from zenml.models.v2.base.base import BaseRequest

T = TypeVar("T", bound="BaseRequest")


def server_owned_request_model(_cls: Type[T]) -> Type[T]:
    """Convert a request model to a model which does not require a user ID.

    Args:
        _cls: The class to decorate

    Returns:
        The decorated class.
    """
    if user_field := _cls.__fields__.get("user", None):
        user_field.required = False
        user_field.allow_none = True
        user_field.default = None

    return _cls
