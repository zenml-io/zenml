#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Util functions for materializers."""

from typing import TYPE_CHECKING, Any, Optional, Sequence, Type

if TYPE_CHECKING:
    from zenml.materializers.base_materializer import BaseMaterializer


def select_materializer(
    data_type: Type[Any],
    materializer_classes: Sequence[Type["BaseMaterializer"]],
) -> Type["BaseMaterializer"]:
    """Select a materializer for a given data type.

    Args:
        data_type: The data type for which to select the materializer.
        materializer_classes: Available materializer classes.

    Raises:
        RuntimeError: If no materializer can handle the given data type.

    Returns:
        The first materializer that can handle the given data type.
    """
    fallback: Optional[Type["BaseMaterializer"]] = None

    for class_ in data_type.__mro__:
        for materializer_class in materializer_classes:
            if class_ in materializer_class.ASSOCIATED_TYPES:
                return materializer_class
            elif not fallback and materializer_class.can_handle_type(class_):
                fallback = materializer_class

    if fallback:
        return fallback

    raise RuntimeError(f"No materializer found for type {data_type}.")
