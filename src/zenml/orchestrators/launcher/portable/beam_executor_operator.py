# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Base class to define how to operator a Beam based executor."""

from typing import Any, Callable, Optional, cast

from tfx.dsl.components.base import base_beam_executor
from tfx.orchestration.portable import base_executor_operator
from tfx.orchestration.portable import data_types
from tfx.orchestration.portable import python_executor_operator
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration import execution_result_pb2
from tfx.utils import import_utils

from google.protobuf import message

try:
  from apache_beam import Pipeline as _BeamPipeline  # pylint: disable=g-import-not-at-top
except ModuleNotFoundError:
  _BeamPipeline = Any


class BeamExecutorOperator(base_executor_operator.BaseExecutorOperator):
  """BeamExecutorOperator handles Beam based executor's init and execution.

  Attributes:
    extra_flags: Extra flags that will pass to Beam executors. It come from
      two sources in the order:
      1. The `extra_flags` set in the executor spec.
      2. The flags passed in when starting the program by users or by other
         systems. The interpretation of these flags relying on the executor
         implementation.
    beam_pipeline_args: Beam specific arguments that will pass to Beam
      executors. It comes from `beam_pipeline_args` set in the Beam executor
      spec.
  """
  SUPPORTED_EXECUTOR_SPEC_TYPE = [executable_spec_pb2.BeamExecutableSpec]
  SUPPORTED_PLATFORM_CONFIG_TYPE = []

  def __init__(self,
               executor_spec: message.Message,
               platform_config: Optional[message.Message] = None):
    """Initializes a BeamExecutorOperator.

    Args:
      executor_spec: The specification of how to initialize the executor.
      platform_config: The specification of how to allocate resource for the
        executor.
    """
    del platform_config
    super().__init__(executor_spec)
    beam_executor_spec = cast(executable_spec_pb2.BeamExecutableSpec,
                              self._executor_spec)
    self._executor_cls = import_utils.import_class_by_path(
        beam_executor_spec.python_executor_spec.class_path)
    self.extra_flags = []
    self.extra_flags.extend(beam_executor_spec.python_executor_spec.extra_flags)
    self.beam_pipeline_args = []
    self.beam_pipeline_args.extend(beam_executor_spec.beam_pipeline_args)

  def run_executor(
      self,
      execution_info: data_types.ExecutionInfo,
      make_beam_pipeline_fn: Optional[Callable[[], _BeamPipeline]] = None,
  ) -> execution_result_pb2.ExecutorOutput:
    """Invokes executors given input from the Launcher.

    Args:
      execution_info: A wrapper of the details of this execution.
      make_beam_pipeline_fn: A custom method to create a Beam Pipeline object.

    Returns:
      The output from executor.
    """
    context = base_beam_executor.BaseBeamExecutor.Context(
        beam_pipeline_args=self.beam_pipeline_args,
        extra_flags=self.extra_flags,
        tmp_dir=execution_info.tmp_dir,
        unique_id=str(execution_info.execution_id),
        executor_output_uri=execution_info.execution_output_uri,
        stateful_working_dir=execution_info.stateful_working_dir,
        pipeline_node=execution_info.pipeline_node,
        pipeline_info=execution_info.pipeline_info,
        pipeline_run_id=execution_info.pipeline_run_id,
        make_beam_pipeline_fn=make_beam_pipeline_fn)
    executor = self._executor_cls(context=context)
    return python_executor_operator.run_with_executor(execution_info, executor)
