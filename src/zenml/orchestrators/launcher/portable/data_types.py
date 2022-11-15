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
"""Data types shared for orchestration."""
from typing import Any, Dict, List, Optional

import attr
from tfx import types
from tfx.orchestration import data_types_utils
from tfx.proto.orchestration import execution_invocation_pb2
from tfx.proto.orchestration import pipeline_pb2


# TODO(b/150979622): We should introduce an id that is not changed across
# retires of the same component run and pass it to executor operators for
# human-readability purpose.
@attr.s(auto_attribs=True)
class ExecutionInfo:
  """A struct to store information for an execution."""
  # LINT.IfChange
  # The Execution id that is registered in MLMD.
  execution_id: Optional[int] = None
  # The input map to feed to execution
  input_dict: Dict[str, List[types.Artifact]] = attr.Factory(dict)
  # The output map to feed to execution
  output_dict: Dict[str, List[types.Artifact]] = attr.Factory(dict)
  # The exec_properties to feed to execution
  exec_properties: Dict[str, Any] = attr.Factory(dict)
  # The uri to execution result, note that the drivers or executors and
  # Launchers may not run in the same process, so they should use this uri to
  # "return" execution result to the launcher.
  execution_output_uri: Optional[str] = None
  # Stateful working dir will be deterministic given pipeline, node and run_id.
  # The typical usecase is to restore long running executor's state after
  # eviction. For examples, a Trainer can use this directory to store
  # checkpoints. This dir is undefined when Launcher.launch() is done.
  stateful_working_dir: Optional[str] = None
  # A tempory dir for executions and it is expected to be cleared up at the end
  # of executions in both success and failure cases. This dir is undefined when
  # Launcher.launch() is done.
  tmp_dir: Optional[str] = None
  # The config of this Node.
  pipeline_node: Optional[pipeline_pb2.PipelineNode] = None
  # The config of the pipeline that this node is running in.
  pipeline_info: Optional[pipeline_pb2.PipelineInfo] = None
  # The id of the pipeline run that this execution is in.
  pipeline_run_id: Optional[str] = None
  # LINT.ThenChange(../../proto/orchestration/execution_invocation.proto)

  def to_proto(self) -> execution_invocation_pb2.ExecutionInvocation:
    return execution_invocation_pb2.ExecutionInvocation(
        execution_id=self.execution_id,
        input_dict=data_types_utils.build_artifact_struct_dict(self.input_dict),
        output_dict=data_types_utils.build_artifact_struct_dict(
            self.output_dict),
        # TODO(b/171794016): Deprecate execution_properties once
        # execution_properties_with_schema is used to build execution
        # properties.
        execution_properties=data_types_utils.build_metadata_value_dict(
            self.exec_properties),
        execution_properties_with_schema=data_types_utils
        .build_pipeline_value_dict(self.exec_properties),
        output_metadata_uri=self.execution_output_uri,
        stateful_working_dir=self.stateful_working_dir,
        tmp_dir=self.tmp_dir,
        pipeline_node=self.pipeline_node,
        pipeline_info=self.pipeline_info,
        pipeline_run_id=self.pipeline_run_id)

  @classmethod
  def from_proto(
      cls, execution_invocation: execution_invocation_pb2.ExecutionInvocation
  ) -> 'ExecutionInfo':
    """Constructs ExecutionInfo from proto."""
    if execution_invocation.execution_properties_with_schema:
      parsed_exec_properties = data_types_utils.build_parsed_value_dict(
          execution_invocation.execution_properties_with_schema)
    else:
      parsed_exec_properties = data_types_utils.build_value_dict(
          execution_invocation.execution_properties)
    return cls(
        execution_id=execution_invocation.execution_id,
        input_dict=data_types_utils.build_artifact_dict(
            execution_invocation.input_dict),
        output_dict=data_types_utils.build_artifact_dict(
            execution_invocation.output_dict),
        exec_properties=parsed_exec_properties,
        execution_output_uri=execution_invocation.output_metadata_uri,
        stateful_working_dir=execution_invocation.stateful_working_dir,
        tmp_dir=execution_invocation.tmp_dir,
        pipeline_node=execution_invocation.pipeline_node,
        pipeline_info=execution_invocation.pipeline_info,
        pipeline_run_id=execution_invocation.pipeline_run_id)
