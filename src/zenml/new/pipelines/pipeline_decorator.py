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
"""ZenML pipeline decorator definition."""

from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Optional,
    TypeVar,
    Union,
    overload,
)

from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.base_settings import SettingsOrDict
    from zenml.model.model import Model
    from zenml.new.pipelines.pipeline import Pipeline

    HookSpecification = Union[str, FunctionType]
    F = TypeVar("F", bound=Callable[..., None])

logger = get_logger(__name__)


@overload
def pipeline(_func: "F") -> "Pipeline": ...


@overload
def pipeline(
    *,
    name: Optional[str] = None,
    enable_cache: Optional[bool] = None,
    enable_artifact_metadata: Optional[bool] = None,
    enable_step_logs: Optional[bool] = None,
    settings: Optional[Dict[str, "SettingsOrDict"]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Callable[["F"], "Pipeline"]: ...


def pipeline(
    _func: Optional["F"] = None,
    *,
    name: Optional[str] = None,
    enable_cache: Optional[bool] = None,
    enable_artifact_metadata: Optional[bool] = None,
    enable_step_logs: Optional[bool] = None,
    settings: Optional[Dict[str, "SettingsOrDict"]] = None,
    extra: Optional[Dict[str, Any]] = None,
    on_failure: Optional["HookSpecification"] = None,
    on_success: Optional["HookSpecification"] = None,
    model: Optional["Model"] = None,
    model_version: Optional["Model"] = None,  # TODO: deprecate me
) -> Union["Pipeline", Callable[["F"], "Pipeline"]]:
    """Decorator to create a pipeline.

    Args:
        _func: The decorated function.
        name: The name of the pipeline. If left empty, the name of the
            decorated function will be used as a fallback.
        enable_cache: Whether to use caching or not.
        enable_artifact_metadata: Whether to enable artifact metadata or not.
        enable_step_logs: If step logs should be enabled for this pipeline.
        settings: Settings for this pipeline.
        extra: Extra configurations for this pipeline.
        on_failure: Callback function in event of failure of the step. Can be a
            function with a single argument of type `BaseException`, or a source
            path to such a function (e.g. `module.my_function`).
        on_success: Callback function in event of success of the step. Can be a
            function with no arguments, or a source path to such a function
            (e.g. `module.my_function`).
        model: configuration of the model in the Model Control Plane.
        model_version: DEPRECATED, please use `model` instead.

    Returns:
        A pipeline instance.
    """

    def inner_decorator(func: "F") -> "Pipeline":
        from zenml.new.pipelines.pipeline import Pipeline

        if model_version:
            logger.warning(
                "Pipeline decorator argument `model_version` is deprecated. Please use `model` instead."
            )

        p = Pipeline(
            name=name or func.__name__,
            enable_cache=enable_cache,
            enable_artifact_metadata=enable_artifact_metadata,
            enable_step_logs=enable_step_logs,
            settings=settings,
            extra=extra,
            on_failure=on_failure,
            on_success=on_success,
            model=model or model_version,
            entrypoint=func,
        )

        p.__doc__ = func.__doc__
        return p

    return inner_decorator if _func is None else inner_decorator(_func)
