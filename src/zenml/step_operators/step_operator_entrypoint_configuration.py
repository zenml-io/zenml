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

from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.io import fileio
from zenml.repository import Repository
from zenml.steps import utils as step_utils

if TYPE_CHECKING:
    from zenml.config.pipeline_configurations import PipelineDeployment
    from zenml.config.step_configurations import Step
EXECUTION_INFO_PATH_OPTION = "execution_info_path"


class StepOperatorEntrypointConfiguration(StepEntrypointConfiguration):
    """Base class for entrypoint configurations that run a single step.

    If an orchestrator needs to run steps in a separate process or environment
    (e.g. a docker container), you should create a custom entrypoint
    configuration class that inherits from this class and use it to implement
    your custom entrypoint logic.

    How to subclass:
    ----------------
    There is only one mandatory method `get_run_name(...)` that you need to
    implement in order to get a functioning entrypoint. Inside this method you
    need to return a string which **has** to be the same for all steps that are
    executed as part of the same pipeline run.

    Passing additional arguments to the entrypoint:
        If you need to pass additional arguments to the entrypoint, there are
        two methods that you need to implement:
            * `get_custom_entrypoint_options()`: This method should return all
                the additional options that you require in the entrypoint.

            * `get_custom_entrypoint_arguments(...)`: This method should return
                a list of arguments that should be passed to the entrypoint.
                The arguments need to provide values for all options defined
                in the `custom_entrypoint_options()` method mentioned above.

        You'll be able to access the argument values from `self.entrypoint_args`
        inside your `StepEntrypointConfiguration` subclass.

    Running custom code inside the entrypoint:
        If you need to run custom code in the entrypoint, you can overwrite
        the `setup(...)` and `post_run(...)` methods which allow you to run
        code before and after the step execution respectively.

    How to use:
    -----------
    After you created your `StepEntrypointConfiguration` subclass, you only
    have to run the entrypoint somewhere. To do this, you should execute the
    command returned by the `get_entrypoint_command()` method with the
    arguments returned by the `get_entrypoint_arguments(...)` method.

    Example:
    ```python
    class MyStepEntrypointConfiguration(StepEntrypointConfiguration):
        ...

    class MyOrchestrator(BaseOrchestrator):
        def prepare_or_run_pipeline(
            self,
            sorted_list_of_steps: List[BaseStep],
            pipeline: "BasePipeline",
            pb2_pipeline: Pb2Pipeline,
            stack: "Stack",
            runtime_configuration: "RuntimeConfiguration",
        ) -> Any:
            ...

            cmd = MyStepEntrypointConfiguration.get_entrypoint_command()
            for step in sorted_list_of_steps:
                ...

                args = MyStepEntrypointConfiguration.get_entrypoint_arguments(
                    step=step, pb2_pipeline=pb2_pipeline
                )
                # Run the command and pass it the arguments. Our example
                # orchestrator here executes the entrypoint in a separate
                # process, but in a real-world scenario you would probably run
                # it inside a docker container or a different environment.
                import subprocess
                subprocess.check_call(cmd + args)
    ```
    """

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running an entrypoint with this configuration.

        **Note**: Subclasses should implement the
            `get_custom_entrypoint_options()` class method instead of this
            one if they require custom options.

        Returns:
            A set of strings with all required options.
        """
        return super().get_entrypoint_options() | {EXECUTION_INFO_PATH_OPTION}

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        The argument list should be something that
        `argparse.ArgumentParser.parse_args(...)` can handle (e.g.
        `["--some_option", "some_value"]` or `["--some_option=some_value"]`).
        It needs to provide values for all options returned by the
        `get_entrypoint_options()` method of this class.

        **Note**: Subclasses should implement the
            `get_custom_entrypoint_arguments(...)` class method instead of
            this one if they require custom arguments.

        Args:
            **kwargs: Additional kwargs.

        Returns:
            A list of strings with the arguments.
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
        """Executes a step.

        Args:
            step: The step to execute.
            deployment: The pipeline deployment for the step.

        Raises:
            RuntimeError: If the step executor class does not exist.

        Returns:
            Step execution info.
        """
        # Make sure the artifact store is loaded before we load the execution
        # info
        stack = Repository().active_stack

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
        stack.prepare_step_run(step=step)
        run_with_executor(execution_info=execution_info, executor=executor)
        stack.cleanup_step_run(step=step)

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
