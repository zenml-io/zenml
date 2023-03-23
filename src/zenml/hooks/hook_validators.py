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
"""Validation functions for hooks."""

import inspect
from types import FunctionType
from typing import TYPE_CHECKING, Union

from zenml.utils import source_utils

if TYPE_CHECKING:
    HookSpecification = Union[str, FunctionType]


def resolve_and_validate_hook(hook_func: "HookSpecification") -> str:
    """Resolves and validates a hook callback.

    Args:
        hook_func: Callable hook function.

    Returns:
        str: Resolved source path of `hook_func`.

    Raises:
        ValueError: If `hook_func` is not a valid callable.
    """
    if type(hook_func) is str:
        func = source_utils.load_source_path(hook_func)
    else:
        func = hook_func

    if not callable(func):
        raise ValueError(f"{func} is not a valid function.")

    from zenml.steps.base_parameters import BaseParameters
    from zenml.steps.step_context import StepContext

    sig = inspect.getfullargspec(inspect.unwrap(func))
    sig_annotations = sig.annotations
    if "return" in sig_annotations:
        sig_annotations.pop("return")

    if sig.args and len(sig.args) != len(sig_annotations):
        raise ValueError(
            "If you pass args to a hook, you must annotate them with one "
            "of the following types: `BaseException`, `BaseParameters`, "
            "and/or `StepContext`."
        )

    if sig_annotations:
        annotations = sig_annotations.values()
        seen_annotations = set()
        for annotation in annotations:
            if annotation:
                if annotation not in (
                    BaseException,
                    BaseParameters,
                    StepContext,
                ):
                    raise ValueError(
                        "Hook parameters must be of type `BaseException`, `BaseParameters`, "
                        f"and/or `StepContext`, not {annotation}"
                    )

                if annotation in seen_annotations:
                    raise ValueError(
                        "It looks like your hook function accepts more than of the "
                        "same argument annotation type. Please ensure you pass exactly "
                        "one of the following: `BaseException`, `BaseParameters`, "
                        "and/or `StepContext`. Currently your function has "
                        f"the following annotations: {sig_annotations}"
                    )
                seen_annotations.add(annotation)

    return source_utils.resolve_class(func)
