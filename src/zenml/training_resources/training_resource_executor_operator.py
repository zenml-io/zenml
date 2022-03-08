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

import os
import sys
from typing import cast

from tfx.orchestration.portable import data_types
from tfx.orchestration.portable.base_executor_operator import (
    BaseExecutorOperator,
)
from tfx.proto.orchestration import executable_spec_pb2, execution_result_pb2

from zenml.io import fileio
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.utils import source_utils

logger = get_logger(__name__)


def _write_execution_info(
    execution_info: data_types.ExecutionInfo, path: str
) -> None:
    """Writes execution information to a given path."""
    execution_info_bytes = execution_info.to_proto().SerializeToString()

    with fileio.open(path, "wb") as f:
        f.write(execution_info_bytes)

    logger.debug("Finished writing execution info to '%s'", path)


def _read_executor_output(
    output_path: str,
) -> execution_result_pb2.ExecutorOutput:
    """Reads executor output from the given path.

    Returns:
        Executor output object.

    Raises:
        RuntimeError: If no output is written to the given path.
    """
    if fileio.file_exists(output_path):
        with fileio.open(output_path, "rb") as f:
            return execution_result_pb2.ExecutorOutput.FromString(f.read())
    else:
        raise RuntimeError(
            f"Unable to find executor output at path '{output_path}'."
        )


class TrainingResourceExecutorOperator(BaseExecutorOperator):
    SUPPORTED_EXECUTOR_SPEC_TYPE = [
        executable_spec_pb2.PythonClassExecutableSpec
    ]
    SUPPORTED_PLATFORM_CONFIG_TYPE = []

    def run_executor(
        self,
        execution_info: data_types.ExecutionInfo,
    ) -> execution_result_pb2.ExecutorOutput:
        """Invokes the executor with inputs provided by the Launcher.

        Args:
          execution_info: A wrapper of the info needed by this execution.

        Returns:
          The output from executor.
        """
        stack = Repository().active_stack
        training_resource = stack.training_resource
        if not training_resource:
            raise RuntimeError(
                f"No training resource specified for active stack '{stack.name}'."
            )

        main_module_file = cast(str, sys.modules["__main__"].__file__)
        main_module = source_utils.get_module_source_from_file_path(
            os.path.abspath(main_module_file)
        )

        (
            step_module,
            step_class,
        ) = execution_info.pipeline_node.node_info.type.name.rsplit(
            ".", maxsplit=1
        )
        if step_module == "__main__":
            step_module = main_module

        step_source_path = f"{step_module}.{step_class}"

        # Write the execution info to a temporary directory inside the artifact
        # store so the training resource entrypoint can load it
        execution_info_path = os.path.join(
            execution_info.tmp_dir, "zenml_execution_info.pb"
        )
        _write_execution_info(execution_info, path=execution_info_path)

        entrypoint_command = [
            "python",
            "-m",
            "zenml.training_resources.entrypoint",
            "--main_module",
            main_module,
            "--step_source_path",
            step_source_path,
            "--execution_info_path",
            execution_info_path,
        ]

        requirements = stack.requirements()

        for context in execution_info.pipeline_node.contexts.contexts:
            if context.type.name == "pipeline_requirements":
                pipeline_requirements = set(
                    context.properties[
                        "pipeline_requirements"
                    ].field_value.string_value.split(" ")
                )
                requirements |= pipeline_requirements

        # TODO: Find a nice way to set this if the running version of ZenML is
        #  not an official release (e.g. on a development branch)
        requirements.add(
            "git+https://github.com/zenml-io/zenml.git@feature/ENG-640-training-resource"
        )

        training_resource.launch(
            pipeline_name=execution_info.pipeline_info.id,
            run_name=execution_info.pipeline_run_id,
            entrypoint_command=entrypoint_command,
            requirements=sorted(requirements),
        )

        return _read_executor_output(execution_info.execution_output_uri)
