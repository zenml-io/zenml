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

from typing import TYPE_CHECKING, Any, List, Optional, Set, Type

from tfx.dsl.components.base.base_executor import BaseExecutor
from tfx.orchestration.portable import data_types
from tfx.orchestration.portable.data_types import ExecutionInfo
from tfx.orchestration.portable.python_executor_operator import (
    run_with_executor,
)
from tfx.proto.orchestration.execution_invocation_pb2 import ExecutionInvocation

from zenml.client import Client
from zenml.config.step_run_info import StepRunInfo
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.io import fileio
from zenml.steps import utils as step_utils

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.config.step_configurations import Step

EXECUTION_INFO_PATH_OPTION = "execution_info_path"


class StepOperatorEntrypointConfiguration(StepEntrypointConfiguration):
    """Base class for step operator entrypoint configurations."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running with this configuration.

        Returns:
            The superclass options as well as an option for the path to the
            execution info.
        """
        return super().get_entrypoint_options() | {EXECUTION_INFO_PATH_OPTION}

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            **kwargs: Kwargs, must include the execution info path.

        Returns:
            The superclass arguments as well as arguments for the path to the
            execution info.
        """
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{EXECUTION_INFO_PATH_OPTION}",
            kwargs[EXECUTION_INFO_PATH_OPTION],
        ]

    def _run_step(
        self,
        step: "Step",
        deployment: "PipelineDeployment",
    ) -> Optional[data_types.ExecutionInfo]:
        """Runs a single step.

        Args:
            step: The step to run.
            deployment: The deployment configuration.

        Raises:
            RuntimeError: If the step executor class does not exist.

        Returns:
            Step execution info.
        """
        # Make sure the artifact store is loaded before we load the execution
        # info
        stack = Client().active_stack

        execution_info_path = self.entrypoint_args[EXECUTION_INFO_PATH_OPTION]
        execution_info = self._load_execution_info(execution_info_path)
        executor_class = step_utils.get_executor_class(step.config.name)
        if not executor_class:
            raise RuntimeError(
                f"Unable to find executor class for step {step.config.name}."
            )

        executor = self._configure_executor(
            executor_class=executor_class, execution_info=execution_info
        )

        stack.orchestrator._ensure_artifact_classes_loaded(step.config)
        step_run_info = StepRunInfo(
            config=step.config,
            pipeline=deployment.pipeline,
            run_name=execution_info.pipeline_run_id,
        )

        stack.prepare_step_run(info=step_run_info)
        try:
            run_with_executor(execution_info=execution_info, executor=executor)
        finally:
            stack.cleanup_step_run(info=step_run_info)

        return execution_info

    @staticmethod
    def _load_execution_info(execution_info_path: str) -> ExecutionInfo:
        """Loads the execution info from the given path.

        Args:
            execution_info_path: Path to the execution info file.

        Returns:
            Execution info.
        """
        with fileio.open(execution_info_path, "rb") as f:
            execution_info_proto = ExecutionInvocation.FromString(f.read())

        return ExecutionInfo.from_proto(execution_info_proto)

    @staticmethod
    def _configure_executor(
        executor_class: Type[BaseExecutor], execution_info: ExecutionInfo
    ) -> BaseExecutor:
        """Creates and configures an executor instance.

        Args:
            executor_class: The class of the executor instance.
            execution_info: Execution info for the executor.

        Returns:
            A configured executor instance.
        """
        context = BaseExecutor.Context(
            tmp_dir=execution_info.tmp_dir,
            unique_id=str(execution_info.execution_id),
            executor_output_uri=execution_info.execution_output_uri,
            stateful_working_dir=execution_info.stateful_working_dir,
            pipeline_node=execution_info.pipeline_node,
            pipeline_info=execution_info.pipeline_info,
            pipeline_run_id=execution_info.pipeline_run_id,
        )

        return executor_class(context=context)
