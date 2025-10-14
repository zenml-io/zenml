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
    Optional,
    TypeVar,
    Union,
)

from pydantic import ConfigDict, ValidationError

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
            self._run(*args, **kwargs)
        elif should_prevent_execution:
            logger.warning("Preventing execution of pipeline '%s'.", self.name)
        else:
            # Client-side, either execute locally or run with step operator
            from contextlib import nullcontext
            from uuid import uuid4

            from zenml.logging.step_logging import (
                PipelineLogsStorageContext,
                prepare_logs_uri,
            )
            from zenml.models import LogsRequest
            from zenml.pipelines.run_utils import create_placeholder_run

            stack = Client().active_stack
            logging_enabled = True

            logs_context = nullcontext()
            logs_model = None

            if logging_enabled:
                # Configure the logs
                logs_uri = prepare_logs_uri(
                    stack.artifact_store,
                )

                logs_context = PipelineLogsStorageContext(
                    logs_uri=logs_uri,
                    artifact_store=stack.artifact_store,
                    prepend_step_name=False,
                )  # type: ignore[assignment]

                logs_model = LogsRequest(
                    uri=logs_uri,
                    source="client",
                    artifact_store_id=stack.artifact_store.id,
                )

            with logs_context:
                snapshot = self._create_snapshot(**self._run_args)
                run = create_placeholder_run(
                    snapshot=snapshot,
                    orchestrator_run_id=str(uuid4()),
                    logs=logs_model,
                )
                stack = Client().active_stack

                if step_operator := stack.step_operator:
                    command = (
                        DynamicPipelineEntrypointConfiguration.get_entrypoint_command()
                        + DynamicPipelineEntrypointConfiguration.get_entrypoint_arguments(
                            snapshot_id=snapshot.id,
                            run_id=run.id,
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
                    initialize_runtime(
                        pipeline=self, snapshot=snapshot, run=run
                    )
                    self._run(*args, **kwargs)

    def _run(self, *args: Any, **kwargs: Any) -> None:
        from zenml.orchestrators.publish_utils import (
            publish_failed_pipeline_run,
            publish_successful_pipeline_run,
        )
        from zenml.pipelines.dynamic_pipeline_runtime import (
            get_pipeline_runtime,
        )

        runtime = get_pipeline_runtime()

        from contextlib import nullcontext

        from zenml.logging.step_logging import (
            PipelineLogsStorageContext,
            prepare_logs_uri,
        )
        from zenml.models import LogsRequest, PipelineRunUpdate

        stack = Client().active_stack
        logging_enabled = True

        logs_context = nullcontext()

        if logging_enabled:
            # Configure the logs
            logs_uri = prepare_logs_uri(
                stack.artifact_store,
            )

            logs_context = PipelineLogsStorageContext(
                logs_uri=logs_uri,
                artifact_store=stack.artifact_store,
                prepend_step_name=False,
            )  # type: ignore[assignment]

            logs_model = LogsRequest(
                uri=logs_uri,
                source="orchestrator",
                artifact_store_id=stack.artifact_store.id,
            )

            Client().zen_store.update_run(
                run_id=runtime.run.id,
                run_update=PipelineRunUpdate(
                    add_logs=[logs_model],
                ),
            )

        with logs_context:
            try:
                self._call_entrypoint(*args, **kwargs)
            except:
                publish_failed_pipeline_run(runtime.run.id)
                raise
            publish_successful_pipeline_run(runtime.run.id)

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
