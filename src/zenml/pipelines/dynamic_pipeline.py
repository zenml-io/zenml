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
    ClassVar,
    Dict,
    Optional,
    TypeVar,
    Union,
)

from pydantic import ConfigDict, ValidationError
from typing_extensions import Self

from zenml import constants
from zenml.client import Client
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.logger import get_logger
from zenml.models import (
    PipelineRunResponse,
)
from zenml.pipelines.pipeline_definition import Pipeline
from zenml.utils import (
    pydantic_utils,
)

if TYPE_CHECKING:
    StepConfigurationUpdateOrDict = Union[
        Dict[str, Any], StepConfigurationUpdate
    ]

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class DynamicPipeline(Pipeline):
    """ZenML pipeline class."""

    # The active pipeline is the pipeline to which step invocations will be
    # added when a step is called. It is set using a context manager when a
    # pipeline is called (see Pipeline.__call__ for more context)
    ACTIVE_PIPELINE: ClassVar[Optional["DynamicPipeline"]] = None

    @property
    def is_prepared(self) -> bool:
        """If the pipeline is prepared.

        Prepared means that the pipeline entrypoint has been called and the
        pipeline is fully defined.

        Returns:
            If the pipeline is prepared.
        """
        return True

    def prepare(self, *args: Any, **kwargs: Any) -> None:
        """Prepares the pipeline.

        Args:
            *args: Pipeline entrypoint input arguments.
            **kwargs: Pipeline entrypoint input keyword arguments.

        Raises:
            RuntimeError: If the pipeline has parameters configured differently in
                configuration file and code.
        """

    def __enter__(self) -> Self:
        """Activate the pipeline context.

        Raises:
            RuntimeError: If a different pipeline is already active.

        Returns:
            The pipeline instance.
        """
        if DynamicPipeline.ACTIVE_PIPELINE:
            raise RuntimeError(
                "Unable to enter pipeline context. A different pipeline "
                f"{DynamicPipeline.ACTIVE_PIPELINE.name} is already active."
            )

        DynamicPipeline.ACTIVE_PIPELINE = self
        return self

    def __exit__(self, *args: Any) -> None:
        """Deactivates the pipeline context.

        Args:
            *args: The arguments passed to the context exit handler.
        """
        DynamicPipeline.ACTIVE_PIPELINE = None

    def __call__(
        self, *args: Any, **kwargs: Any
    ) -> Optional[PipelineRunResponse]:
        """Handle a call of the pipeline.

        This method does one of two things:
        * If there is an active pipeline context, it calls the pipeline
          entrypoint function within that context and the step invocations
          will be added to the active pipeline.
        * If no pipeline is active, it activates this pipeline before calling
          the entrypoint function.

        Args:
            *args: Entrypoint function arguments.
            **kwargs: Entrypoint function keyword arguments.

        Returns:
            If called within another pipeline, returns the outputs of the
            `entrypoint` method. Otherwise, returns the pipeline run or `None`
            if running with a schedule.
        """
        from zenml.pipelines.dynamic_pipeline_entrypoint_configuration import (
            DynamicPipelineEntrypointConfiguration,
        )
        from zenml.pipelines.dynamic_pipeline_runtime import (
            get_pipeline_runtime,
            initialize_runtime,
        )

        should_prevent_execution = constants.SHOULD_PREVENT_PIPELINE_EXECUTION
        runtime = get_pipeline_runtime()

        if runtime and runtime.pipeline is self:
            self._call_entrypoint(*args, **kwargs)
            # TODO: update run status to completed
        elif should_prevent_execution:
            logger.warning("Preventing execution of pipeline '%s'.", self.name)
        else:
            # Client-side, either execute locally or run with step operator
            snapshot = self._create_snapshot(**self._run_args)
            stack = Client().active_stack

            if step_operator := stack.step_operator:
                command = (
                    DynamicPipelineEntrypointConfiguration.get_entrypoint_command()
                    + DynamicPipelineEntrypointConfiguration.get_entrypoint_arguments(
                        snapshot_id=snapshot.id
                    )
                )
                from zenml.orchestrators.utils import (
                    get_config_environment_vars,
                )

                environment, secrets = get_config_environment_vars()
                environment.update(secrets)
                step_operator.run_dynamic_pipeline(
                    command=command,
                    snapshot=snapshot,
                    environment=environment,
                )
            else:
                initialize_runtime(pipeline=self, snapshot=snapshot)
                self._call_entrypoint(*args, **kwargs)
                # TODO: update run status to completed

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
