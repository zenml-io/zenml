#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

"""Utility functions and classes to run ZenML steps."""

from typing import Any, Dict, Tuple

import pydantic.typing as pydantic_typing

from zenml.logger import get_logger
from zenml.steps.step_output import Output

logger = get_logger(__name__)

SINGLE_RETURN_OUT_NAME = "output"


def resolve_type_annotation(obj: Any) -> Any:
    """Returns the non-generic class for generic aliases of the typing module.

    If the input is no generic typing alias, the input itself is returned.

    Example: if the input object is `typing.Dict`, this method will return the
    concrete class `dict`.

    Args:
        obj: The object to resolve.

    Returns:
        The non-generic class for generic aliases of the typing module.
    """
    origin = pydantic_typing.get_origin(obj) or obj

    if pydantic_typing.is_union(origin):
        return obj

    return origin


def get_args(obj: Any) -> Tuple[Any, ...]:
    """Get arguments of a Union type annotation.

    Example:
        `get_args(Union[int, str]) == (int, str)`

    Args:
        obj: The annotation.

    Returns:
        The args of the Union annotation.
    """
    return tuple(
        pydantic_typing.get_origin(v) or v
        for v in pydantic_typing.get_args(obj)
    )


def parse_return_type_annotations(return_annotation: Any) -> Dict[str, Any]:
    """Parse the returns of a step function into a dict of resolved types.

    Called within `BaseStepMeta.__new__()` to define `cls.OUTPUT_SIGNATURE`.

    Args:
        return_annotation: Return annotation of the step function.

    Returns:
        Output signature of the new step class.
    """
    if return_annotation is None:
        return {}

    # Cast simple output types to `Output`.
    if not isinstance(return_annotation, Output):
        return_annotation = Output(
            **{SINGLE_RETURN_OUT_NAME: return_annotation}
        )

    # Resolve type annotations of all outputs and save in new dict.
    output_signature = {
        output_name: resolve_type_annotation(output_type)
        for output_name, output_type in return_annotation.items()
    }
    return output_signature
