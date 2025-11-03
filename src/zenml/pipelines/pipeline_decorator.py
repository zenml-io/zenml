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

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    TypeVar,
    Union,
    overload,
)
from uuid import UUID

from zenml.enums import ExecutionMode
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.config.base_settings import SettingsOrDict
    from zenml.config.cache_policy import CachePolicyOrString
    from zenml.config.retry_config import StepRetryConfig
    from zenml.model.model import Model
    from zenml.pipelines.pipeline_definition import Pipeline
    from zenml.steps.base_step import BaseStep
    from zenml.types import HookSpecification, InitHookSpecification
    from zenml.utils.tag_utils import Tag

    F = TypeVar("F", bound=Callable[..., Any])

logger = get_logger(__name__)


@overload
def pipeline(_func: "F") -> "Pipeline": ...


@overload
def pipeline(
    *,
    name: Optional[str] = None,
    dynamic: Optional[bool] = None,
    depends_on: Optional[List["BaseStep"]] = None,
    enable_cache: Optional[bool] = None,
    enable_artifact_metadata: Optional[bool] = None,
    enable_step_logs: Optional[bool] = None,
    environment: Optional[Dict[str, Any]] = None,
    secrets: Optional[List[Union[UUID, str]]] = None,
    enable_pipeline_logs: Optional[bool] = None,
    settings: Optional[Dict[str, "SettingsOrDict"]] = None,
    tags: Optional[List[Union[str, "Tag"]]] = None,
    extra: Optional[Dict[str, Any]] = None,
    on_failure: Optional["HookSpecification"] = None,
    on_success: Optional["HookSpecification"] = None,
    on_init: Optional["InitHookSpecification"] = None,
    on_init_kwargs: Optional[Dict[str, Any]] = None,
    on_cleanup: Optional["HookSpecification"] = None,
    model: Optional["Model"] = None,
    retry: Optional["StepRetryConfig"] = None,
    substitutions: Optional[Dict[str, str]] = None,
    execution_mode: Optional["ExecutionMode"] = None,
    cache_policy: Optional["CachePolicyOrString"] = None,
) -> Callable[["F"], "Pipeline"]: ...


def pipeline(
    _func: Optional["F"] = None,
    *,
    name: Optional[str] = None,
    dynamic: Optional[bool] = None,
    depends_on: Optional[List["BaseStep"]] = None,
    enable_cache: Optional[bool] = None,
    enable_artifact_metadata: Optional[bool] = None,
    enable_step_logs: Optional[bool] = None,
    environment: Optional[Dict[str, Any]] = None,
    secrets: Optional[List[Union[UUID, str]]] = None,
    enable_pipeline_logs: Optional[bool] = None,
    settings: Optional[Dict[str, "SettingsOrDict"]] = None,
    tags: Optional[List[Union[str, "Tag"]]] = None,
    extra: Optional[Dict[str, Any]] = None,
    on_failure: Optional["HookSpecification"] = None,
    on_success: Optional["HookSpecification"] = None,
    on_init: Optional["InitHookSpecification"] = None,
    on_init_kwargs: Optional[Dict[str, Any]] = None,
    on_cleanup: Optional["HookSpecification"] = None,
    model: Optional["Model"] = None,
    retry: Optional["StepRetryConfig"] = None,
    substitutions: Optional[Dict[str, str]] = None,
    execution_mode: Optional["ExecutionMode"] = None,
    cache_policy: Optional["CachePolicyOrString"] = None,
) -> Union["Pipeline", Callable[["F"], "Pipeline"]]:
    """Decorator to create a pipeline.

    Args:
        _func: The decorated function.
        name: The name of the pipeline. If left empty, the name of the
            decorated function will be used as a fallback.
        dynamic: Whether this is a dynamic pipeline or not.
        depends_on: The steps that this pipeline depends on.
        enable_cache: Whether to use caching or not.
        enable_artifact_metadata: Whether to enable artifact metadata or not.
        enable_step_logs: If step logs should be enabled for this pipeline.
        environment: Environment variables to set when running this pipeline.
        secrets: Secrets to set as environment variables when running this
            pipeline.
        enable_pipeline_logs: If pipeline logs should be enabled for this pipeline.
        settings: Settings for this pipeline.
        tags: Tags to apply to runs of the pipeline.
        extra: Extra configurations for this pipeline.
        on_failure: Callback function in event of failure of the step. Can be a
            function with a single argument of type `BaseException`, or a source
            path to such a function (e.g. `module.my_function`).
        on_success: Callback function in event of success of the step. Can be a
            function with no arguments, or a source path to such a function
            (e.g. `module.my_function`).
        on_init: Callback function to run on initialization of the pipeline. Can
            be a function with no arguments, or a source path to such a function
            (e.g. `module.my_function`) if the function returns a value, it will
            be stored as the pipeline state.
        on_init_kwargs: Arguments for the init hook.
        on_cleanup: Callback function to run on cleanup of the pipeline. Can be a
            function with no arguments, or a source path to such a function
            (e.g. `module.my_function`).
        model: configuration of the model in the Model Control Plane.
        retry: Retry configuration for the pipeline steps.
        substitutions: Extra placeholders to use in the name templates.
        execution_mode: The execution mode to use for the pipeline.
        cache_policy: Cache policy for this pipeline.

    Returns:
        A pipeline instance.
    """

    def inner_decorator(func: "F") -> "Pipeline":
        from zenml.pipelines.pipeline_definition import Pipeline

        PipelineClass = Pipeline
        pipeline_args: Dict[str, Any] = {}

        if dynamic:
            from zenml.pipelines.dynamic.pipeline_definition import (
                DynamicPipeline,
            )

            PipelineClass = DynamicPipeline

            pipeline_args = {
                "depends_on": depends_on,
            }
        elif depends_on:
            logger.warning(
                "The `depends_on` argument is not supported "
                "for static pipelines and will be ignored."
            )

        p = PipelineClass(
            name=name or func.__name__,
            entrypoint=func,
            enable_cache=enable_cache,
            enable_artifact_metadata=enable_artifact_metadata,
            enable_step_logs=enable_step_logs,
            environment=environment,
            secrets=secrets,
            enable_pipeline_logs=enable_pipeline_logs,
            settings=settings,
            tags=tags,
            extra=extra,
            on_failure=on_failure,
            on_success=on_success,
            on_init=on_init,
            on_init_kwargs=on_init_kwargs,
            on_cleanup=on_cleanup,
            model=model,
            retry=retry,
            substitutions=substitutions,
            execution_mode=execution_mode,
            cache_policy=cache_policy,
            **pipeline_args,
        )

        p.__doc__ = func.__doc__
        return p

    return inner_decorator if _func is None else inner_decorator(_func)
