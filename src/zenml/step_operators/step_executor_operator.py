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

"""Custom StepExecutorOperator which can be passed to the step operator."""

import json
import os
from typing import TYPE_CHECKING, Any, List, cast

from tfx.orchestration.portable import data_types
from tfx.orchestration.portable.base_executor_operator import (
    BaseExecutorOperator,
)
from tfx.proto.orchestration import executable_spec_pb2, execution_result_pb2

from zenml.client import Client
from zenml.config.step_run_info import StepRunInfo
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.step_operators.step_operator_entrypoint_configuration import (
    StepOperatorEntrypointConfiguration,
)
from zenml.steps.utils import (
    INTERNAL_EXECUTION_PARAMETER_PREFIX,
    PARAM_PIPELINE_PARAMETER_NAME,
)
from zenml.utils import proto_utils

if TYPE_CHECKING:
    from zenml.stack import Stack
    from zenml.step_operators import BaseStepOperator

logger = get_logger(__name__)


def _write_execution_info(
    execution_info: data_types.ExecutionInfo, path: str
) -> None:
    """Writes execution information to a given path.

    Args:
        execution_info: Execution information to write.
        path: Path to write the execution information to.
    """
    execution_info_bytes = execution_info.to_proto().SerializeToString()

    with fileio.open(path, "wb") as f:
        f.write(execution_info_bytes)

    logger.debug("Finished writing execution info to '%s'", path)


def _read_executor_output(
    output_path: str,
) -> execution_result_pb2.ExecutorOutput:
    """Reads executor output from the given path.

    Args:
        output_path: Path to read the executor output from.

    Returns:
        Executor output object.

    Raises:
        RuntimeError: If no output is written to the given path.
    """
    if fileio.exists(output_path):
        with fileio.open(output_path, "rb") as f:
            return execution_result_pb2.ExecutorOutput.FromString(f.read())
    else:
        raise RuntimeError(
            f"Unable to find executor output at path '{output_path}'."
        )


class StepExecutorOperator(BaseExecutorOperator):
    """StepExecutorOperator extends TFX's BaseExecutorOperator.

    This class can be passed as a custom executor operator during
    a pipeline run which will then be used to call the step's
    configured step operator to launch it in some environment.
    """

    SUPPORTED_EXECUTOR_SPEC_TYPE = [
        executable_spec_pb2.PythonClassExecutableSpec
    ]
    SUPPORTED_PLATFORM_CONFIG_TYPE: List[Any] = []

    @staticmethod
    def _get_step_operator(
        stack: "Stack", step_operator_name: str
    ) -> "BaseStepOperator":
        """Fetches the step operator specified in the execution info.

        Args:
            stack: Stack on which the step is being executed.
            step_operator_name: Name of the step operator to get.

        Returns:
            The step operator to run a step.

        Raises:
            RuntimeError: If no active step operator is found.
        """
        step_operator = stack.step_operator

        # the two following errors should never happen as the stack gets
        # validated before running the pipeline
        if not step_operator:
            raise RuntimeError(
                f"No step operator specified for active stack '{stack.name}'."
            )

        if step_operator_name != step_operator.name:
            raise RuntimeError(
                f"No step operator named '{step_operator_name}' in active "
                f"stack '{stack.name}'."
            )

        return step_operator

    @staticmethod
    def _get_step_name_in_pipeline(
        execution_info: data_types.ExecutionInfo,
    ) -> str:
        """Gets the name of a step inside its pipeline.

        Args:
            execution_info: The step execution info.

        Returns:
            The name of the step in the pipeline.
        """
        property_name = (
            INTERNAL_EXECUTION_PARAMETER_PREFIX + PARAM_PIPELINE_PARAMETER_NAME
        )
        return cast(
            str, json.loads(execution_info.exec_properties[property_name])
        )

    def run_executor(
        self,
        execution_info: data_types.ExecutionInfo,
    ) -> execution_result_pb2.ExecutorOutput:
        """Invokes the executor with inputs provided by the Launcher.

        Args:
            execution_info: Necessary information to run the executor.

        Returns:
            The executor output.
        """
        # Pretty sure these attributes will always be not None, assert here so
        # mypy doesn't complain
        assert execution_info.pipeline_node
        assert execution_info.pipeline_info
        assert execution_info.pipeline_run_id
        assert execution_info.tmp_dir
        assert execution_info.execution_output_uri

        step = proto_utils.get_step(pipeline_node=execution_info.pipeline_node)
        pipeline_config = proto_utils.get_pipeline_config(
            pipeline_node=execution_info.pipeline_node
        )
        assert step.config.step_operator

        stack = Client().active_stack
        step_operator = self._get_step_operator(
            stack=stack, step_operator_name=step.config.step_operator
        )

        # Write the execution info to a temporary directory inside the artifact
        # store so the step operator entrypoint can load it
        execution_info_path = os.path.join(
            execution_info.tmp_dir, "zenml_execution_info.pb"
        )
        _write_execution_info(execution_info, path=execution_info_path)

        step_name_in_pipeline = self._get_step_name_in_pipeline(execution_info)

        entrypoint_command = (
            StepOperatorEntrypointConfiguration.get_entrypoint_command()
            + StepOperatorEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name_in_pipeline,
                execution_info_path=execution_info_path,
            )
        )

        logger.info(
            "Using step operator `%s` to run step `%s`.",
            step_operator.name,
            step_name_in_pipeline,
        )
        step_run_info = StepRunInfo(
            config=step.config,
            pipeline=pipeline_config,
            run_name=execution_info.pipeline_run_id,
        )
        step_operator.launch(
            info=step_run_info,
            entrypoint_command=entrypoint_command,
        )

        return _read_executor_output(execution_info.execution_output_uri)
