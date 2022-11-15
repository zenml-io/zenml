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

import abc

from tfx.orchestration import metadata
from tfx.orchestration.portable import data_types
from tfx.proto.orchestration import driver_output_pb2


class BaseDriver(abc.ABC):
  """The base class of all drivers."""

  def __init__(self, mlmd_connection: metadata.Metadata):
    """Constructor.

    Args:
      mlmd_connection: ML metadata connection.
    """
    self._mlmd_connection = mlmd_connection

  @abc.abstractmethod
  def run(
      self, execution_info: data_types.ExecutionInfo
  ) -> driver_output_pb2.DriverOutput:
    """Invokes the driver with inputs provided by the Launcher.

    Args:
      execution_info: a `data_types.ExecutionInfo` instance representing the
        execution info needed for the driver execution.

    Returns:
      An DriverOutput instance.
    """
    pass
