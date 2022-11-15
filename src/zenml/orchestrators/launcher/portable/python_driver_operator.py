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
"""A class to define how to operator an python based driver."""

from typing import cast

from tfx.orchestration import metadata
from tfx.orchestration.portable import base_driver_operator
from tfx.orchestration.portable import data_types
from tfx.proto.orchestration import driver_output_pb2
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration import pipeline_pb2
from tfx.utils import import_utils

from google.protobuf import message


class PythonDriverOperator(base_driver_operator.BaseDriverOperator):
  """PythonDriverOperator handles python class based driver's init and execution."""

  SUPPORTED_EXECUTABLE_SPEC_TYPE = [
      executable_spec_pb2.PythonClassExecutableSpec
  ]

  def __init__(self, driver_spec: message.Message,
               mlmd_connection: metadata.Metadata):
    """Constructor.

    Args:
      driver_spec: The specification of how to initialize the driver.
      mlmd_connection: ML metadata connection.

    Raises:
      RuntimeError: if the driver_spec is not supported.
    """
    super().__init__(driver_spec, mlmd_connection)

    python_class_driver_spec = cast(
        pipeline_pb2.ExecutorSpec.PythonClassExecutorSpec, driver_spec)
    self._driver = import_utils.import_class_by_path(
        python_class_driver_spec.class_path)(
            self._mlmd_connection)

  def run_driver(
      self, execution_info: data_types.ExecutionInfo
  ) -> driver_output_pb2.DriverOutput:
    return self._driver.run(execution_info)
