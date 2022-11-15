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
"""The base class of all system node handlers."""

import abc

from tfx.orchestration import metadata
from tfx.proto.orchestration import pipeline_pb2

from ml_metadata.proto import metadata_store_pb2


class SystemNodeHandler(abc.ABC):
  """SystemNodeHandler is the base class of all system nodes' handler."""

  @abc.abstractmethod
  def run(
      self,
      mlmd_connection: metadata.Metadata,
      pipeline_node: pipeline_pb2.PipelineNode,
      pipeline_info: pipeline_pb2.PipelineInfo,
      pipeline_runtime_spec: pipeline_pb2.PipelineRuntimeSpec
  ) -> metadata_store_pb2.Execution:
    """Runs the system node and return the Execution.

    Args:
      mlmd_connection: ML metadata connection.
      pipeline_node: The specification of the node that this launcher lauches.
      pipeline_info: The information of the pipeline that this node runs in.
      pipeline_runtime_spec: The runtime information of the pipeline that this
        node runs in.

    Returns:
      The execution of the run.
    """
    pass
