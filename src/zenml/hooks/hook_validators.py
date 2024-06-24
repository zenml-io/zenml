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
from typing import TYPE_CHECKING

from zenml.config.source import Source
from zenml.utils import source_utils

if TYPE_CHECKING:
    from zenml.types import HookSpecification


def resolve_and_validate_hook(hook: "HookSpecification") -> Source:
    """Resolves and validates a hook callback.

    Args:
        hook: Hook function or source.

    Returns:
        Hook source.

    Raises:
        ValueError: If `hook_func` is not a valid callable.
    """
    if isinstance(hook, (str, Source)):
        func = source_utils.load(hook)
    else:
        func = hook

    if not callable(func):
        raise ValueError(f"{func} is not a valid function.")

    from zenml.new.steps.step_context import StepContext
    from zenml.steps.base_parameters import BaseParameters

    sig = inspect.getfullargspec(inspect.unwrap(func))
    sig_annotations = sig.annotations
    if "return" in sig_annotations:
        sig_annotations.pop("return")

    if sig.args and len(sig.args) != len(sig_annotations):
        raise ValueError(
            "You can only pass arguments to a hook that are annotated with a "
            "`BaseException` type."
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
                        "Hook arguments must be of type `BaseException`, not "
                        f"`{annotation}`."
                    )

                if annotation in seen_annotations:
                    raise ValueError(
                        "You can only pass one `BaseException` type to a hook."
                        "Currently your function has the following"
                        f"annotations: {sig_annotations}"
                    )
                seen_annotations.add(annotation)

    return source_utils.resolve(func)
