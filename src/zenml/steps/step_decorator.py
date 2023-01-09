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
    Type,
    TypeVar,
    Union,
    overload,
)

from zenml.steps import BaseStep
from zenml.steps.utils import (
    INSTANCE_CONFIGURATION,
    PARAM_CREATED_BY_FUNCTIONAL_API,
    PARAM_ENABLE_CACHE,
    PARAM_EXPERIMENT_TRACKER,
    PARAM_EXTRA_OPTIONS,
    PARAM_OUTPUT_ARTIFACTS,
    PARAM_OUTPUT_MATERIALIZERS,
    PARAM_SETTINGS,
    PARAM_STEP_NAME,
    PARAM_STEP_OPERATOR,
    STEP_INNER_FUNC_NAME,
)

if TYPE_CHECKING:
    from zenml.artifacts.base_artifact import BaseArtifact
    from zenml.config.base_settings import SettingsOrDict
    from zenml.materializers.base_materializer import BaseMaterializer

    ArtifactClassOrStr = Union[str, Type["BaseArtifact"]]
    MaterializerClassOrStr = Union[str, Type["BaseMaterializer"]]
    OutputArtifactsSpecification = Union[
        "ArtifactClassOrStr", Mapping[str, "ArtifactClassOrStr"]
    ]
    OutputMaterializersSpecification = Union[
        "MaterializerClassOrStr", Mapping[str, "MaterializerClassOrStr"]
    ]

F = TypeVar("F", bound=Callable[..., Any])


@overload
def step(_func: F) -> Type[BaseStep]:
    ...


@overload
def step(
    *,
    name: Optional[str] = None,
    enable_cache: bool = True,
    experiment_tracker: Optional[str] = None,
    step_operator: Optional[str] = None,
    output_artifacts: Optional["OutputArtifactsSpecification"] = None,
    output_materializers: Optional["OutputMaterializersSpecification"] = None,
    settings: Optional[Dict[str, "SettingsOrDict"]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Callable[[F], Type[BaseStep]]:
    ...


def step(
    _func: Optional[F] = None,
    *,
    name: Optional[str] = None,
    enable_cache: Optional[bool] = None,
    experiment_tracker: Optional[str] = None,
    step_operator: Optional[str] = None,
    output_artifacts: Optional["OutputArtifactsSpecification"] = None,
    output_materializers: Optional["OutputMaterializersSpecification"] = None,
    settings: Optional[Dict[str, "SettingsOrDict"]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Union[Type[BaseStep], Callable[[F], Type[BaseStep]]]:
    """Outer decorator function for the creation of a ZenML step.

    In order to be able to work with parameters such as `name`, it features a
    nested decorator structure.

    Args:
        _func: The decorated function.
        name: The name of the step. If left empty, the name of the decorated
            function will be used as a fallback.
        enable_cache: Specify whether caching is enabled for this step. If no
            value is passed, caching is enabled by default unless the step
            requires a `StepContext` (see
            `zenml.steps.step_context.StepContext` for more information).
        experiment_tracker: The experiment tracker to use for this step.
        step_operator: The step operator to use for this step.
        output_materializers: Output materializers for this step. If
            given as a dict, the keys must be a subset of the output names
            of this step. If a single value (type or string) is given, the
            materializer will be used for all outputs.
        output_artifacts: Output artifacts for this step. If
            given as a dict, the keys must be a subset of the output names
            of this step. If a single value (type or string) is given, the
            artifact class will be used for all outputs.
        settings: Settings for this step.
        extra: Extra configurations for this step.

    Returns:
        the inner decorator which creates the step class based on the
        ZenML BaseStep
    """

    def inner_decorator(func: F) -> Type[BaseStep]:
        """Inner decorator function for the creation of a ZenML Step.

        Args:
            func: types.FunctionType, this function will be used as the
                "process" method of the generated Step.

        Returns:
            The class of a newly generated ZenML Step.
        """
        return type(  # noqa
            func.__name__,
            (BaseStep,),
            {
                STEP_INNER_FUNC_NAME: staticmethod(func),
                INSTANCE_CONFIGURATION: {
                    PARAM_STEP_NAME: name,
                    PARAM_CREATED_BY_FUNCTIONAL_API: True,
                    PARAM_ENABLE_CACHE: enable_cache,
                    PARAM_EXPERIMENT_TRACKER: experiment_tracker,
                    PARAM_STEP_OPERATOR: step_operator,
                    PARAM_OUTPUT_ARTIFACTS: output_artifacts,
                    PARAM_OUTPUT_MATERIALIZERS: output_materializers,
                    PARAM_SETTINGS: settings,
                    PARAM_EXTRA_OPTIONS: extra,
                },
                "__module__": func.__module__,
                "__doc__": func.__doc__,
            },
        )

    if _func is None:
        return inner_decorator
    else:
        return inner_decorator(_func)
