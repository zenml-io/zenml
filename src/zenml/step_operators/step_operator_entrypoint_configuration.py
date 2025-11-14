#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Abstract base class for entrypoint configurations that run a single step."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from zenml.client import Client
from zenml.config.step_configurations import Step
from zenml.config.step_run_info import StepRunInfo
from zenml.entrypoints.step_entrypoint_configuration import (
    STEP_NAME_OPTION,
    StepEntrypointConfiguration,
)
from zenml.orchestrators import input_utils, output_utils
from zenml.orchestrators.step_runner import StepRunner

if TYPE_CHECKING:
    from zenml.models import PipelineSnapshotResponse, StepRunResponse

STEP_RUN_ID_OPTION = "step_run_id"


class StepOperatorEntrypointConfiguration(StepEntrypointConfiguration):
    """Base class for step operator entrypoint configurations."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the step operator entrypoint configuration.

        Args:
            *args: The arguments to pass to the superclass.
            **kwargs: The keyword arguments to pass to the superclass.
        """
        super().__init__(*args, **kwargs)
        self._step_run: Optional["StepRunResponse"] = None

    @classmethod
    def get_entrypoint_options(cls) -> Dict[str, bool]:
        """Gets all options required for running with this configuration.

        Returns:
            The superclass options as well as an option for the step run id.
        """
        return super().get_entrypoint_options() | {
            STEP_RUN_ID_OPTION: True,
        }

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            **kwargs: Kwargs, must include the step run id.

        Returns:
            The superclass arguments as well as arguments for the step run id.
        """
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{STEP_RUN_ID_OPTION}",
            kwargs[STEP_RUN_ID_OPTION],
        ]

    @property
    def step_run(self) -> "StepRunResponse":
        """The step run configured for this entrypoint configuration.

        Returns:
            The step run.
        """
        if self._step_run is None:
            step_run_id = UUID(self.entrypoint_args[STEP_RUN_ID_OPTION])
            self._step_run = Client().zen_store.get_run_step(step_run_id)
        return self._step_run

    @property
    def step(self) -> "Step":
        """The step configured for this entrypoint configuration.

        Returns:
            The step.
        """
        return Step(
            spec=self.step_run.spec,
            config=self.step_run.config,
            step_config_overrides=self.step_run.config,
        )

    def _run_step(
        self,
        step: "Step",
        snapshot: "PipelineSnapshotResponse",
    ) -> None:
        """Runs a single step.

        Args:
            step: The step to run.
            snapshot: The snapshot configuration.
        """
        step_run = self.step_run
        pipeline_run = Client().get_pipeline_run(step_run.pipeline_run_id)

        step_run_info = StepRunInfo(
            config=step.config,
            spec=step.spec,
            snapshot=snapshot,
            pipeline=snapshot.pipeline_configuration,
            run_name=pipeline_run.name,
            pipeline_step_name=self.entrypoint_args[STEP_NAME_OPTION],
            run_id=pipeline_run.id,
            step_run_id=step_run.id,
            force_write_logs=lambda: None,
        )

        stack = Client().active_stack
        # We need to call this here to include parameters from lazy
        # loaders in the step configuration.
        input_utils.resolve_step_inputs(step=step, pipeline_run=pipeline_run)
        output_artifact_uris = output_utils.prepare_output_artifact_uris(
            step_run=step_run, stack=stack, step=step
        )

        step_runner = StepRunner(step=step, stack=stack)
        step_runner.run(
            pipeline_run=pipeline_run,
            step_run=step_run,
            input_artifacts=step_run.inputs,
            output_artifact_uris=output_artifact_uris,
            step_run_info=step_run_info,
        )
