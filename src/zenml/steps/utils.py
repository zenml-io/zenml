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

import sys
import typing
from typing import Any, Dict

from zenml.logger import get_logger
from zenml.steps.step_output import Output

logger = get_logger(__name__)

STEP_INNER_FUNC_NAME = "entrypoint"
SINGLE_RETURN_OUT_NAME = "output"
PARAM_STEP_NAME = "name"
PARAM_ENABLE_CACHE = "enable_cache"
PARAM_CREATED_BY_FUNCTIONAL_API = "created_by_functional_api"
PARAM_STEP_OPERATOR = "step_operator"
PARAM_EXPERIMENT_TRACKER = "experiment_tracker"
INSTANCE_CONFIGURATION = "INSTANCE_CONFIGURATION"
PARAM_OUTPUT_ARTIFACTS = "output_artifacts"
PARAM_OUTPUT_MATERIALIZERS = "output_materializers"
PARAM_SETTINGS = "settings"
PARAM_EXTRA_OPTIONS = "extra"


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
    from typing import _GenericAlias  # type: ignore[attr-defined]

    if sys.version_info >= (3, 8):
        return typing.get_origin(obj) or obj
    else:
        # python 3.7
        if isinstance(obj, _GenericAlias):
            return obj.__origin__
        else:
            return obj


def parse_return_type_annotations(
    step_annotations: Dict[str, Any]
) -> Dict[str, Any]:
    """Parse the returns of a step function into a dict of resolved types.

    Called within `BaseStepMeta.__new__()` to define `cls.OUTPUT_SIGNATURE`.
    Called within `Do()` to resolve type annotations.

    Args:
        step_annotations: Type annotations of the step function.

    Returns:
        Output signature of the new step class.
    """
    return_type = step_annotations.get("return", None)
    if return_type is None:
        return {}

    # Cast simple output types to `Output`.
    if not isinstance(return_type, Output):
        return_type = Output(**{SINGLE_RETURN_OUT_NAME: return_type})

    # Resolve type annotations of all outputs and save in new dict.
    output_signature = {
        output_name: resolve_type_annotation(output_type)
        for output_name, output_type in return_type.items()
    }
    return output_signature
