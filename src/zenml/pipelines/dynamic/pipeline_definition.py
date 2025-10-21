#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Definition of a ZenML pipeline."""

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    TypeVar,
    Union,
)

from pydantic import ConfigDict, ValidationError

from zenml import ExternalArtifact
from zenml.client import Client
from zenml.logger import get_logger
from zenml.logging.step_logging import setup_pipeline_logging
from zenml.models import ArtifactVersionResponse, PipelineRunResponse
from zenml.pipelines.pipeline_definition import Pipeline
from zenml.pipelines.run_utils import (
    create_placeholder_run,
    should_prevent_pipeline_execution,
)
from zenml.steps.step_invocation import StepInvocation
from zenml.utils import dict_utils, pydantic_utils

if TYPE_CHECKING:
    from zenml.steps import BaseStep
    from zenml.steps.entrypoint_function_utils import StepArtifact

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class DynamicPipeline(Pipeline):
    """ZenML pipeline class."""

    @property
    def depends_on(self) -> List["BaseStep"]:
        return []

    @property
    def is_dynamic(self) -> bool:
        """If the pipeline is dynamic.

        Returns:
            If the pipeline is dynamic.
        """
        return True

    @property
    def is_prepared(self) -> bool:
        """If the pipeline is prepared.

        Prepared means that the pipeline entrypoint has been called and the
        pipeline is fully defined.

        Returns:
            If the pipeline is prepared.
        """
        return False

    def prepare(self, *args: Any, **kwargs: Any) -> None:
        """Prepares the pipeline.

        Args:
            *args: Pipeline entrypoint input arguments.
            **kwargs: Pipeline entrypoint input keyword arguments.

        Raises:
            RuntimeError: If the pipeline has parameters configured differently in
                configuration file and code.
        """
        conflicting_parameters = {}
        parameters_ = (self.configuration.parameters or {}).copy()
        if from_file_ := self._from_config_file.get("parameters", None):
            parameters_ = dict_utils.recursive_update(parameters_, from_file_)
        if parameters_:
            for k, v_runtime in kwargs.items():
                if k in parameters_:
                    v_config = parameters_[k]
                    if v_config != v_runtime:
                        conflicting_parameters[k] = (v_config, v_runtime)
            if conflicting_parameters:
                is_plural = "s" if len(conflicting_parameters) > 1 else ""
                msg = f"Configured parameter{is_plural} for the pipeline `{self.name}` conflict{'' if not is_plural else 's'} with parameter{is_plural} passed in runtime:\n"
                for key, values in conflicting_parameters.items():
                    msg += f"`{key}`: config=`{values[0]}` | runtime=`{values[1]}`\n"
                msg += """This happens, if you define values for pipeline parameters in configuration file and pass same parameters from the code. Example:
```
# config.yaml
    parameters:
        param_name: value1
            
            
# pipeline.py
@pipeline
def pipeline_(param_name: str):
    step_name()

if __name__=="__main__":
    pipeline_.with_options(config_path="config.yaml")(param_name="value2")
```
To avoid this consider setting pipeline parameters only in one place (config or code).
"""
                raise RuntimeError(msg)
            for k, v_config in parameters_.items():
                if k not in kwargs:
                    kwargs[k] = v_config

        try:
            validated_args = pydantic_utils.validate_function_args(
                self.entrypoint,
                ConfigDict(arbitrary_types_allowed=False),
                *args,
                **kwargs,
            )
        except ValidationError as e:
            raise ValueError(
                "Invalid or missing pipeline function entrypoint arguments. "
                "Only JSON serializable inputs are allowed as pipeline inputs. "
                "Check out the pydantic error above for more details."
            ) from e

        self._parameters = validated_args
        self._invocations = {}

    def add_dynamic_invocation(
        self,
        step: "BaseStep",
        custom_id: Optional[str] = None,
        allow_id_suffix: bool = True,
        upstream_steps: Optional[Set[str]] = None,
        input_artifacts: Dict[str, "StepArtifact"] = {},
        external_artifacts: Dict[
            str, Union[ExternalArtifact, "ArtifactVersionResponse"]
        ] = {},
    ) -> str:
        invocation_id = self._compute_invocation_id(
            step=step, custom_id=custom_id, allow_suffix=allow_id_suffix
        )
        invocation = StepInvocation(
            id=invocation_id,
            step=step,
            input_artifacts=input_artifacts,
            external_artifacts=external_artifacts,
            model_artifacts_or_metadata={},
            client_lazy_loaders={},
            parameters={},
            default_parameters={},
            upstream_steps=upstream_steps or set(),
            pipeline=self,
        )
        self._invocations[invocation_id] = invocation
        return invocation_id

    def __call__(
        self, *args: Any, **kwargs: Any
    ) -> Optional[PipelineRunResponse]:
        if should_prevent_pipeline_execution():
            logger.info("Preventing execution of pipeline '%s'.", self.name)
            return

        stack = Client().active_stack

        if not stack.orchestrator.supports_dynamic_pipelines:
            raise RuntimeError(
                f"The {stack.orchestrator.__class__.__name__} does not support dynamic pipelines. "
            )

        self.prepare(*args, **kwargs)
        snapshot = self._create_snapshot(**self._run_args)

        with setup_pipeline_logging(
            source="client", snapshot=snapshot
        ) as logs_request:
            run = create_placeholder_run(
                snapshot=snapshot,
                logs=logs_request,
            )
            stack.orchestrator.run(
                snapshot=snapshot,
                stack=stack,
                placeholder_run=run,
            )
        return Client().get_pipeline_run(run.id)

    def _call_entrypoint(self, *args: Any, **kwargs: Any) -> None:
        """Calls the pipeline entrypoint function with the given arguments.

        Args:
            *args: Entrypoint function arguments.
            **kwargs: Entrypoint function keyword arguments.

        Raises:
            ValueError: If an input argument is missing or not JSON
                serializable.
        """
        try:
            validated_args = pydantic_utils.validate_function_args(
                self.entrypoint,
                ConfigDict(arbitrary_types_allowed=False),
                *args,
                **kwargs,
            )
        except ValidationError as e:
            raise ValueError(
                "Invalid or missing pipeline function entrypoint arguments. "
                "Only JSON serializable inputs are allowed as pipeline inputs. "
                "Check out the pydantic error above for more details."
            ) from e

        self.entrypoint(**validated_args)

    def _compute_output_schema(self) -> Optional[Dict[str, Any]]:
        """Computes the output schema for the pipeline.

        Returns:
            The output schema for the pipeline.
        """
        return None
