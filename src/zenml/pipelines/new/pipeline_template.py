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
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Optional,
    Union,
)

from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.exceptions import PipelineInterfaceError
from zenml.logger import get_logger
from zenml.pipelines.new.pipeline import Pipeline
from zenml.steps import BaseStep

if TYPE_CHECKING:
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
PARAM_SETTINGS = "settings"
PARAM_EXTRA_OPTIONS = "extra"
PARAM_ON_FAILURE = "on_failure"
PARAM_ON_SUCCESS = "on_success"


class PipelineTemplate(Pipeline, ABC):
    _CLASS_CONFIGURATION: ClassVar[Optional[Dict[str, Any]]] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        config = self._CLASS_CONFIGURATION or {}

        super().__init__(
            name=config.pop(PARAM_PIPELINE_NAME, None)
            or self.__class__.__name__,
            **config,
        )

        steps = self._verify_steps(*args, **kwargs)

        with self:
            self.connect(**steps)

    @abstractmethod
    def connect(self, *args: BaseStep, **kwargs: BaseStep) -> None:
        raise NotImplementedError

    def _compute_invocation_id(
        self,
        step: "BaseStep",
        custom_id: Optional[str] = None,
        allow_suffix: bool = True,
    ) -> str:
        if not custom_id:
            custom_id = getattr(step, "_template_name", None)
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
            setattr(potential_step, "_template_name", key)

        return steps
