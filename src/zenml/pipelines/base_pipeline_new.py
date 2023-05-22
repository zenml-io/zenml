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
import inspect
from abc import ABC, abstractmethod
from types import FunctionType
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Mapping, Optional, Union
from uuid import UUID

from zenml.config.schedule import Schedule
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.exceptions import PipelineInterfaceError
from zenml.logger import get_logger
from zenml.new.pipelines.pipeline import Pipeline
from zenml.steps import BaseStep

if TYPE_CHECKING:
    from zenml.config.base_settings import SettingsOrDict
    from zenml.models.pipeline_build_models import (
        PipelineBuildBaseModel,
    )

    StepConfigurationUpdateOrDict = Union[
        Dict[str, Any], StepConfigurationUpdate
    ]
    HookSpecification = Union[str, FunctionType]

logger = get_logger(__name__)

PIPELINE_INNER_FUNC_NAME = "connect"
CLASS_CONFIGURATION = "_CLASS_CONFIGURATION"
PARAM_PIPELINE_NAME = "name"
PARAM_ENABLE_CACHE = "enable_cache"
PARAM_ENABLE_ARTIFACT_METADATA = "enable_artifact_metadata"
PARAM_ENABLE_ARTIFACT_VISUALIZATION = "enable_artifact_visualization"
PARAM_SETTINGS = "settings"
PARAM_EXTRA_OPTIONS = "extra"
PARAM_ON_FAILURE = "on_failure"
PARAM_ON_SUCCESS = "on_success"

TEMPLATE_NAME_ATTRIBUTE = "_template_name"


class BasePipeline(Pipeline, ABC):
    _CLASS_CONFIGURATION: ClassVar[Optional[Dict[str, Any]]] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        config = self._CLASS_CONFIGURATION or {}
        self._steps = self._verify_steps(*args, **kwargs)

        def entrypoint() -> None:
            self.connect(**self._steps)

        super().__init__(
            name=config.pop(PARAM_PIPELINE_NAME, None)
            or self.__class__.__name__,
            entrypoint=entrypoint,
            **config,
        )

    @property
    def steps(self) -> Dict[str, BaseStep]:
        """Returns the steps of the pipeline.

        Returns:
            The steps of the pipeline.
        """
        return self._steps

    @abstractmethod
    def connect(self, *args: BaseStep, **kwargs: BaseStep) -> None:
        raise NotImplementedError

    def run(
        self,
        *,
        run_name: Optional[str] = None,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        enable_artifact_visualization: Optional[bool] = None,
        schedule: Optional[Schedule] = None,
        build: Union[str, "UUID", "PipelineBuildBaseModel", None] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        step_configurations: Optional[
            Mapping[str, "StepConfigurationUpdateOrDict"]
        ] = None,
        extra: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
        unlisted: bool = False,
        prevent_build_reuse: bool = False,
    ) -> None:
        """Runs the pipeline on the active stack.

        Args:
            run_name: Name of the pipeline run.
            enable_cache: If caching should be enabled for this pipeline run.
            enable_artifact_metadata: If artifact metadata should be enabled
                for this pipeline run.
            enable_artifact_visualization: If artifact visualization should be
                enabled for this pipeline run.
            schedule: Optional schedule to use for the run.
            build: Optional build to use for the run.
            settings: Settings for this pipeline run.
            step_configurations: Configurations for steps of the pipeline.
            extra: Extra configurations for this pipeline run.
            config_path: Path to a yaml configuration file. This file will
                be parsed as a
                `zenml.config.pipeline_configurations.PipelineRunConfiguration`
                object. Options provided in this file will be overwritten by
                options provided in code using the other arguments of this
                method.
            unlisted: Whether the pipeline run should be unlisted (not assigned
                to any pipeline).
            prevent_build_reuse: Whether to prevent the reuse of a build.
        """
        pipeline_copy = self.with_options(
            run_name=run_name,
            enable_cache=enable_cache,
            enable_artifact_metadata=enable_artifact_metadata,
            enable_artifact_visualization=enable_artifact_visualization,
            schedule=schedule,
            build=build,
            settings=settings,
            step_configurations=step_configurations,
            extra=extra,
            config_path=config_path,
            unlisted=unlisted,
            prevent_build_reuse=prevent_build_reuse,
        )

        pipeline_copy()

    def _compute_invocation_id(
        self,
        step: "BaseStep",
        custom_id: Optional[str] = None,
        allow_suffix: bool = True,
    ) -> str:
        if not custom_id:
            custom_id = getattr(step, TEMPLATE_NAME_ATTRIBUTE, None)
            allow_suffix = True

        return super()._compute_invocation_id(
            step=step, custom_id=custom_id, allow_suffix=allow_suffix
        )

    def _verify_steps(
        self, *args: Any, **kwargs: Any
    ) -> Dict[str, "BaseStep"]:
        signature = inspect.signature(self.connect, follow_wrapped=True)

        try:
            bound_args = signature.bind(*args, **kwargs)
        except TypeError as e:
            raise PipelineInterfaceError(
                f"Wrong arguments when initializing pipeline '{self.name}': {e}"
            ) from e

        steps = {}

        for key, potential_step in bound_args.arguments.items():
            step_class = type(potential_step)

            if inspect.isclass(potential_step) and issubclass(
                potential_step, BaseStep
            ):
                raise PipelineInterfaceError(
                    f"Wrong argument type (`{step_class}`) for argument "
                    f"'{key}' of pipeline '{self.name}'. "
                    f"A `BaseStep` subclass was provided instead of an "
                    f"instance. "
                    f"This might have been caused due to missing brackets of "
                    f"your steps when creating a pipeline with `@step` "
                    f"decorated functions, "
                    f"for which the correct syntax is `pipeline(step=step())`."
                )

            if not isinstance(potential_step, BaseStep):
                raise PipelineInterfaceError(
                    f"Wrong argument type (`{step_class}`) for argument "
                    f"'{key}' of pipeline '{self.name}'. Only "
                    f"`@step` decorated functions or instances of `BaseStep` "
                    f"subclasses can be used as arguments when creating "
                    f"a pipeline."
                )

            steps[key] = potential_step
            setattr(potential_step, TEMPLATE_NAME_ATTRIBUTE, key)

        return steps
