# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Docker component launcher which launches a container in docker environment ."""

from typing import Any, Dict, Optional, cast

from absl import logging
import docker
from tfx.dsl.compiler import placeholder_utils
from tfx.dsl.component.experimental import executor_specs
from tfx.orchestration.portable import base_executor_operator
from tfx.orchestration.portable import data_types
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration import execution_result_pb2
from tfx.proto.orchestration import platform_config_pb2
from tfx.utils import proto_utils

from google.protobuf import message


class DockerExecutorOperator(base_executor_operator.BaseExecutorOperator):
  """Responsible for launching a container executor."""
  SUPPORTED_EXECUTOR_SPEC_TYPE = [executable_spec_pb2.ContainerExecutableSpec]
  SUPPORTED_PLATFORM_CONFIG_TYPE = [platform_config_pb2.DockerPlatformConfig]

  def __init__(self,
               executor_spec: message.Message,
               platform_config: Optional[message.Message] = None):
    super().__init__(executor_spec, platform_config)
    self._container_executor_spec = cast(
        executable_spec_pb2.ContainerExecutableSpec, self._executor_spec)
    if self._platform_config:
      self._docker_platform_config = cast(
          platform_config_pb2.DockerPlatformConfig, self._platform_config)
    else:
      self._docker_platform_config = platform_config_pb2.DockerPlatformConfig()

  def run_executor(
      self, execution_info: data_types.ExecutionInfo
  ) -> execution_result_pb2.ExecutorOutput:
    """Execute underlying component implementation."""

    context = placeholder_utils.ResolutionContext(
        exec_info=execution_info,
        executor_spec=self._executor_spec,
        platform_config=self._platform_config)

    component_executor_spec = (
        executor_specs.TemplatedExecutorContainerSpec(
            image=self._container_executor_spec.image,
            command=[
                placeholder_utils.resolve_placeholder_expression(cmd, context)
                for cmd in self._container_executor_spec.commands
            ]))

    logging.info('Container spec: %s', vars(component_executor_spec))
    logging.info('Docker platform config: %s',
                 proto_utils.proto_to_json(self._docker_platform_config))

    # Call client.containers.run and wait for completion.
    # ExecutorContainerSpec follows k8s container spec which has different
    # names to Docker's container spec. It's intended to set command to docker's
    # entrypoint and args to docker's command.
    if self._docker_platform_config.docker_server_url:
      client = docker.DockerClient(
          base_url=self._docker_platform_config.docker_server_url)
    else:
      client = docker.from_env()

    run_args = self._build_run_args(self._docker_platform_config)
    container = client.containers.run(
        image=component_executor_spec.image,
        command=component_executor_spec.command,
        detach=True,
        **run_args)

    # Streaming logs
    for log in container.logs(stream=True):
      logging.info('Docker: %s', log.decode('utf-8'))
    exit_code = container.wait()['StatusCode']
    if exit_code != 0:
      raise RuntimeError(
          'Container exited with error code "{}"'.format(exit_code))
    # TODO(b/141192583): Report data to publisher
    # - report container digest
    # - report replaced command line entrypoints
    # - report docker run args
    return execution_result_pb2.ExecutorOutput()

  def _build_run_args(
      self, docker_platform_config: platform_config_pb2.DockerPlatformConfig
  ) -> Dict[str, Any]:
    """Converts DockerPlatformConfig to args acceppted by the containers.run."""
    if docker_platform_config.additional_run_args:
      result = dict(docker_platform_config.additional_run_args)
    else:
      result = {}
    result.update(privileged=(docker_platform_config.privileged or False))
    if docker_platform_config.environment:
      result.update(environment=docker_platform_config.environment)
    if docker_platform_config.name:
      result.update(name=docker_platform_config.name)
    if docker_platform_config.user:
      if docker_platform_config.user.username:
        result.update(user=docker_platform_config.user.username)
      else:
        result.update(user=docker_platform_config.user.uid)
    if docker_platform_config.volumes:
      volumes = {}
      for volume_name in docker_platform_config.volumes:
        volume_mount_pb = docker_platform_config.volumes[volume_name]
        volumes[volume_name] = {
            'bind': volume_mount_pb.bind,
            'mode': volume_mount_pb.mode
        }
      result.update(volumes=volumes)
    return result
