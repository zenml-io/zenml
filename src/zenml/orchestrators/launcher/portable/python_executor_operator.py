# Copyright 2020 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Base class to define how to operator an executor."""
import copy
import sys
from typing import Optional, cast

from tfx.dsl.components.base import base_executor
from tfx.dsl.io import fileio
from tfx.orchestration.portable import base_executor_operator
from tfx.orchestration.portable import data_types
from tfx.orchestration.portable import outputs_utils
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration import execution_result_pb2
from tfx.types.value_artifact import ValueArtifact
from tfx.utils import import_utils

from google.protobuf import message

_STATEFUL_WORKING_DIR = 'stateful_working_dir'


def run_with_executor(
    execution_info: data_types.ExecutionInfo,
    executor: base_executor.BaseExecutor
) -> execution_result_pb2.ExecutorOutput:
  """Invokes executors given an executor instance and input from the Launcher.

  Args:
    execution_info: A wrapper of the details of this execution.
    executor: An executor instance.

  Returns:
    The output from executor.
  """
  # In cases where output directories are not empty due to a previous or
  # unrelated execution, clear the directories to ensure consistency.
  outputs_utils.clear_output_dirs(execution_info.output_dict)

  for _, artifact_list in execution_info.input_dict.items():
    for artifact in artifact_list:
      if isinstance(artifact, ValueArtifact):
        # Read ValueArtifact into memory.
        artifact.read()

  output_dict = copy.deepcopy(execution_info.output_dict)
  result = executor.Do(execution_info.input_dict, output_dict,
                       execution_info.exec_properties)
  if not result:
    # If result is not returned from the Do function, then try to
    # read from the executor_output_uri.
    if fileio.exists(execution_info.execution_output_uri):
      result = execution_result_pb2.ExecutorOutput.FromString(
          fileio.open(execution_info.execution_output_uri, 'rb').read())
    else:
      # Old style TFX executor doesn't return executor_output, but modify
      # output_dict and exec_properties in place. For backward compatibility,
      # we use their executor_output and exec_properties to construct
      # ExecutorOutput.
      result = execution_result_pb2.ExecutorOutput()
      outputs_utils.populate_output_artifact(result, output_dict)
      outputs_utils.populate_exec_properties(result,
                                             execution_info.exec_properties)
  return result


class PythonExecutorOperator(base_executor_operator.BaseExecutorOperator):
  """PythonExecutorOperator handles python class based executor's init and execution.

  Attributes:
    extra_flags: Extra flags that will pass to Python executors. It come from
      two sources in the order:
      1. The `extra_flags` set in the executor spec.
      2. The flags passed in when starting the program by users or by other
         systems.
      The interpretation of these flags relying on the executor implementation.
  """

  SUPPORTED_EXECUTOR_SPEC_TYPE = [executable_spec_pb2.PythonClassExecutableSpec]
  SUPPORTED_PLATFORM_CONFIG_TYPE = []

  def __init__(self,
               executor_spec: message.Message,
               platform_config: Optional[message.Message] = None):
    """Initializes a PythonExecutorOperator.

    Args:
      executor_spec: The specification of how to initialize the executor.
      platform_config: The specification of how to allocate resource for the
        executor.
    """
    # Python executors run locally, so platform_config is not used.
    del platform_config
    super().__init__(executor_spec)
    python_class_executor_spec = cast(
        executable_spec_pb2.PythonClassExecutableSpec, self._executor_spec)
    self._executor_cls = import_utils.import_class_by_path(
        python_class_executor_spec.class_path)
    self.extra_flags = []
    self.extra_flags.extend(python_class_executor_spec.extra_flags)
    self.extra_flags.extend(sys.argv[1:])

  def run_executor(
      self, execution_info: data_types.ExecutionInfo
  ) -> execution_result_pb2.ExecutorOutput:
    """Invokes executors given input from the Launcher.

    Args:
      execution_info: A wrapper of the details of this execution.

    Returns:
      The output from executor.
    """
    context = base_executor.BaseExecutor.Context(
        extra_flags=self.extra_flags,
        tmp_dir=execution_info.tmp_dir,
        unique_id=str(execution_info.execution_id),
        executor_output_uri=execution_info.execution_output_uri,
        stateful_working_dir=execution_info.stateful_working_dir,
        pipeline_node=execution_info.pipeline_node,
        pipeline_info=execution_info.pipeline_info,
        pipeline_run_id=execution_info.pipeline_run_id)
    executor = self._executor_cls(context=context)
    return run_with_executor(execution_info, executor)
