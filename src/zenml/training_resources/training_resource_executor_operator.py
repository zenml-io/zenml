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

from tfx.orchestration.portable import data_types
from tfx.orchestration.portable.base_executor_operator import (
    BaseExecutorOperator,
)
from tfx.proto.orchestration import executable_spec_pb2, execution_result_pb2
from zenml.utils import source_utils
from typing import cast
import os
import sys
from zenml.repository import Repository
from zenml.io import fileio
from tfx.orchestration.portable import outputs_utils


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

        execution_info_proto = execution_info.to_proto().SerializeToString()
        execution_info_file_name = "zenml-execution-info"
        execution_info_path = os.path.join(Repository().root, execution_info_file_name)
        with open(execution_info_path, "wb") as f:
            f.write(execution_info_proto)

        main_module_file = cast(str, sys.modules["__main__"].__file__)
        main_module = source_utils.get_module_source_from_file_path(
            os.path.abspath(main_module_file)
        )

        step_module = execution_info.pipeline_node.node_info.type.name.split(".")[:-1]
        if step_module[0] == "__main__":
            step_module = main_module
        else:
            step_module = ".".join(step_module)

        step_function_name = execution_info.pipeline_node.node_info.id

        entrypoint_command = ["python", "-m", "zenml.training_resources.entrypoint", "--main_module", main_module, "--step_module", step_module, "--step_function_name", step_function_name, "--execution_info", execution_info_file_name]

        training_resource.launch(
            pipeline_name=execution_info.pipeline_info.id,
            run_name=execution_info.pipeline_run_id,
            entrypoint_command=entrypoint_command
        )

        if fileio.file_exists(execution_info.execution_output_uri):
            result = execution_result_pb2.ExecutorOutput.FromString(
                fileio.open(execution_info.execution_output_uri, 'rb').read())
        else:
            raise ValueError("missing file")

        return result
