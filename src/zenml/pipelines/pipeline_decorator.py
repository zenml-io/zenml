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
"""Legacy ZenML pipeline decorator definition."""

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)

from zenml.logger import get_logger
from zenml.model.model import Model
from zenml.pipelines.base_pipeline import (
    CLASS_CONFIGURATION,
    PARAM_ENABLE_ARTIFACT_METADATA,
    PARAM_ENABLE_ARTIFACT_VISUALIZATION,
    PARAM_ENABLE_CACHE,
    PARAM_ENABLE_STEP_LOGS,
    PARAM_EXTRA_OPTIONS,
    PARAM_MODEL,
    PARAM_ON_FAILURE,
    PARAM_ON_SUCCESS,
    PARAM_PIPELINE_NAME,
    PARAM_SETTINGS,
    PIPELINE_INNER_FUNC_NAME,
    BasePipeline,
)

if TYPE_CHECKING:
    from zenml.config.base_settings import SettingsOrDict
    from zenml.types import HookSpecification


logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., None])


@overload
def pipeline(_func: F) -> Type[BasePipeline]: ...


@overload
def pipeline(
    *,
    name: Optional[str] = None,
    enable_cache: Optional[bool] = None,
    enable_artifact_metadata: Optional[bool] = None,
    enable_artifact_visualization: Optional[bool] = None,
    enable_step_logs: Optional[bool] = None,
    settings: Optional[Dict[str, "SettingsOrDict"]] = None,
    extra: Optional[Dict[str, Any]] = None,
    model: Optional["Model"] = None,
) -> Callable[[F], Type[BasePipeline]]: ...


def pipeline(
    _func: Optional[F] = None,
    *,
    name: Optional[str] = None,
    enable_cache: Optional[bool] = None,
    enable_artifact_metadata: Optional[bool] = None,
    enable_artifact_visualization: Optional[bool] = None,
    enable_step_logs: Optional[bool] = None,
    settings: Optional[Dict[str, "SettingsOrDict"]] = None,
    extra: Optional[Dict[str, Any]] = None,
    on_failure: Optional["HookSpecification"] = None,
    on_success: Optional["HookSpecification"] = None,
    model: Optional["Model"] = None,
) -> Union[Type[BasePipeline], Callable[[F], Type[BasePipeline]]]:
    """Outer decorator function for the creation of a ZenML pipeline.

    Args:
        _func: The decorated function.
        name: The name of the pipeline. If left empty, the name of the
            decorated function will be used as a fallback.
        enable_cache: Whether to use caching or not.
        enable_artifact_metadata: Whether to enable artifact metadata or not.
        enable_artifact_visualization: Whether to enable artifact visualization.
        enable_step_logs: Whether to enable step logs.
        settings: Settings for this pipeline.
        extra: Extra configurations for this pipeline.
        on_failure: Callback function in event of failure of the step. Can be a
            function with a single argument of type `BaseException`, or a source
            path to such a function (e.g. `module.my_function`).
        on_success: Callback function in event of success of the step. Can be a
            function with no arguments, or a source path to such a function
            (e.g. `module.my_function`).
        model: configuration of the model in the Model Control Plane.

    Returns:
        the inner decorator which creates the pipeline class based on the
        ZenML BasePipeline
    """

    def inner_decorator(func: F) -> Type[BasePipeline]:
        pipeline_name = name or func.__name__
        logger.warning(
            "The `@pipeline` decorator that you used to define your "
            f"{pipeline_name} pipeline is deprecated. Check out the 0.40.0 "
            "migration guide for more information on how to migrate your "
            "pipelines to the new syntax: "
            "https://docs.zenml.io/reference/migration-guide/migration-zero-forty.html"
        )

        return type(
            name or func.__name__,
            (BasePipeline,),
            {
                PIPELINE_INNER_FUNC_NAME: staticmethod(func),
                CLASS_CONFIGURATION: {
                    PARAM_PIPELINE_NAME: name,
                    PARAM_ENABLE_CACHE: enable_cache,
                    PARAM_ENABLE_ARTIFACT_METADATA: enable_artifact_metadata,
                    PARAM_ENABLE_ARTIFACT_VISUALIZATION: enable_artifact_visualization,
                    PARAM_ENABLE_STEP_LOGS: enable_step_logs,
                    PARAM_SETTINGS: settings,
                    PARAM_EXTRA_OPTIONS: extra,
                    PARAM_ON_FAILURE: on_failure,
                    PARAM_ON_SUCCESS: on_success,
                    PARAM_MODEL: model,
                },
                "__module__": func.__module__,
                "__doc__": func.__doc__,
            },
        )

    return inner_decorator if _func is None else inner_decorator(_func)
