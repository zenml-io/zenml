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
"""Step decorator function."""

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Mapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    overload,
)

from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.base_settings import SettingsOrDict
    from zenml.config.retry_config import StepRetryConfig
    from zenml.config.source import Source
    from zenml.materializers.base_materializer import BaseMaterializer
    from zenml.model.model import Model
    from zenml.steps import BaseStep
    from zenml.types import HookSpecification

    MaterializerClassOrSource = Union[str, Source, Type[BaseMaterializer]]

    OutputMaterializersSpecification = Union[
        MaterializerClassOrSource,
        Sequence[MaterializerClassOrSource],
        Mapping[str, MaterializerClassOrSource],
        Mapping[str, Sequence[MaterializerClassOrSource]],
    ]
    F = TypeVar("F", bound=Callable[..., Any])


logger = get_logger(__name__)


@overload
def step(_func: "F") -> "BaseStep": ...


@overload
def step(
    *,
    name: Optional[str] = None,
    enable_cache: Optional[bool] = None,
    enable_artifact_metadata: Optional[bool] = None,
    enable_artifact_visualization: Optional[bool] = None,
    enable_step_logs: Optional[bool] = None,
    experiment_tracker: Optional[str] = None,
    step_operator: Optional[str] = None,
    output_materializers: Optional["OutputMaterializersSpecification"] = None,
    settings: Optional[Dict[str, "SettingsOrDict"]] = None,
    extra: Optional[Dict[str, Any]] = None,
    on_failure: Optional["HookSpecification"] = None,
    on_success: Optional["HookSpecification"] = None,
    model: Optional["Model"] = None,
    retry: Optional["StepRetryConfig"] = None,
    name_subs: Optional[Dict[str, str]] = None,
) -> Callable[["F"], "BaseStep"]: ...


def step(
    _func: Optional["F"] = None,
    *,
    name: Optional[str] = None,
    enable_cache: Optional[bool] = None,
    enable_artifact_metadata: Optional[bool] = None,
    enable_artifact_visualization: Optional[bool] = None,
    enable_step_logs: Optional[bool] = None,
    experiment_tracker: Optional[str] = None,
    step_operator: Optional[str] = None,
    output_materializers: Optional["OutputMaterializersSpecification"] = None,
    settings: Optional[Dict[str, "SettingsOrDict"]] = None,
    extra: Optional[Dict[str, Any]] = None,
    on_failure: Optional["HookSpecification"] = None,
    on_success: Optional["HookSpecification"] = None,
    model: Optional["Model"] = None,
    retry: Optional["StepRetryConfig"] = None,
    name_subs: Optional[Dict[str, str]] = None,
) -> Union["BaseStep", Callable[["F"], "BaseStep"]]:
    """Decorator to create a ZenML step.

    Args:
        _func: The decorated function.
        name: The name of the step. If left empty, the name of the decorated
            function will be used as a fallback.
        enable_cache: Specify whether caching is enabled for this step. If no
            value is passed, caching is enabled by default.
        enable_artifact_metadata: Specify whether metadata is enabled for this
            step. If no value is passed, metadata is enabled by default.
        enable_artifact_visualization: Specify whether visualization is enabled
            for this step. If no value is passed, visualization is enabled by
            default.
        enable_step_logs: Specify whether step logs are enabled for this step.
        experiment_tracker: The experiment tracker to use for this step.
        step_operator: The step operator to use for this step.
        output_materializers: Output materializers for this step. If
            given as a dict, the keys must be a subset of the output names
            of this step. If a single value (type or string) is given, the
            materializer will be used for all outputs.
        settings: Settings for this step.
        extra: Extra configurations for this step.
        on_failure: Callback function in event of failure of the step. Can be a
            function with a single argument of type `BaseException`, or a source
            path to such a function (e.g. `module.my_function`).
        on_success: Callback function in event of success of the step. Can be a
            function with no arguments, or a source path to such a function
            (e.g. `module.my_function`).
        model: configuration of the model in the Model Control Plane.
        retry: configuration of step retry in case of step failure.
        name_subs: Extra placeholders for the step name.

    Returns:
        The step instance.
    """

    def inner_decorator(func: "F") -> "BaseStep":
        from zenml.steps.decorated_step import _DecoratedStep

        class_: Type["BaseStep"] = type(
            func.__name__,
            (_DecoratedStep,),
            {
                "entrypoint": staticmethod(func),
                "__module__": func.__module__,
                "__doc__": func.__doc__,
            },
        )

        step_instance = class_(
            name=name or func.__name__,
            enable_cache=enable_cache,
            enable_artifact_metadata=enable_artifact_metadata,
            enable_artifact_visualization=enable_artifact_visualization,
            enable_step_logs=enable_step_logs,
            experiment_tracker=experiment_tracker,
            step_operator=step_operator,
            output_materializers=output_materializers,
            settings=settings,
            extra=extra,
            on_failure=on_failure,
            on_success=on_success,
            model=model,
            retry=retry,
            name_subs=name_subs,
        )

        return step_instance

    if _func is None:
        return inner_decorator
    else:
        return inner_decorator(_func)
