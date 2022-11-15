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
from typing import Optional

from tfx.orchestration.portable import data_types
from tfx.proto.orchestration import execution_result_pb2
from tfx.utils import abc_utils

from google.protobuf import message


class BaseExecutorOperator(abc.ABC):
  """The base class of all executor operators."""

  SUPPORTED_EXECUTOR_SPEC_TYPE = abc_utils.abstract_property()
  SUPPORTED_PLATFORM_CONFIG_TYPE = abc_utils.abstract_property()

  def __init__(self,
               executor_spec: message.Message,
               platform_config: Optional[message.Message] = None):
    """Constructor.

    Args:
      executor_spec: The specification of how to initialize the executor.
      platform_config: The specification of how to allocate resource for the
        executor.

    Raises:
      RuntimeError: if the executor_spec or platform_config is not supported.
    """
    if not isinstance(executor_spec,
                      tuple(t for t in self.SUPPORTED_EXECUTOR_SPEC_TYPE)):
      raise RuntimeError('Executor spec not supported: %s' % executor_spec)
    if platform_config and not isinstance(
        platform_config, tuple(t for t in self.SUPPORTED_PLATFORM_CONFIG_TYPE)):
      raise RuntimeError('Platform spec not supported: %s' % platform_config)
    self._executor_spec = executor_spec
    self._platform_config = platform_config
    self._execution_watcher_address = None

  @abc.abstractmethod
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
    pass

  def with_execution_watcher(
      self, execution_watcher_address: str) -> 'BaseExecutorOperator':
    """Attatch an execution watcher to the executor operator.

    Args:
      execution_watcher_address: The address to an executor watcher gRPC service
        which can be used to update execution properties.

    Returns:
      The executor operator itself.
    """
    self._execution_watcher_address = execution_watcher_address
    return self
