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

import collections
from typing import Any, Dict, List, Optional, cast

from absl import logging
from kubernetes import client
from tfx.dsl.compiler import placeholder_utils
from tfx.dsl.component.experimental import executor_specs
from tfx.orchestration.launcher import container_common
from tfx.orchestration.portable import base_executor_operator
from tfx.orchestration.portable import data_types
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration import execution_result_pb2
from tfx.utils import kube_utils

from google.protobuf import message


class KubernetesExecutorOperator(base_executor_operator.BaseExecutorOperator):
  """Responsible for launching a container executor on Kubernetes."""

  SUPPORTED_EXECUTOR_SPEC_TYPE = [executable_spec_pb2.ContainerExecutableSpec]
  SUPPORTED_PLATFORM_CONFIG_TYPE = []

  def __init__(self,
               executor_spec: message.Message,
               platform_config: Optional[message.Message] = None):
    super().__init__(executor_spec, platform_config)
    self._container_executor_spec = cast(
        executable_spec_pb2.ContainerExecutableSpec, self._executor_spec)

  def run_executor(
      self, execution_info: data_types.ExecutionInfo
  ) -> execution_result_pb2.ExecutorOutput:
    """Execute underlying component implementation.

    Runs executor container in a Kubernetes Pod and wait until it goes into
    `Succeeded` or `Failed` state.

    Args:
      execution_info: All the information that the launcher provides.

    Raises:
      RuntimeError: when the pod is in `Failed` state or unexpected failure from
      Kubernetes API.

    Returns:
      An ExecutorOutput instance

    """

    context = placeholder_utils.ResolutionContext(
        exec_info=execution_info,
        executor_spec=self._executor_spec,
        platform_config=self._platform_config)

    container_spec = executor_specs.TemplatedExecutorContainerSpec(
        image=self._container_executor_spec.image,
        command=[
            placeholder_utils.resolve_placeholder_expression(cmd, context)
            for cmd in self._container_executor_spec.commands
        ] or None,
        args=[
            placeholder_utils.resolve_placeholder_expression(arg, context)
            for arg in self._container_executor_spec.args
        ] or None,
    )

    pod_name = self._build_pod_name(execution_info)
    # TODO(hongyes): replace the default value from component config.
    try:
      namespace = kube_utils.get_kfp_namespace()
    except RuntimeError:
      namespace = 'kubeflow'

    pod_manifest = self._build_pod_manifest(pod_name, container_spec)
    core_api = kube_utils.make_core_v1_api()

    if kube_utils.is_inside_kfp():
      launcher_pod = kube_utils.get_current_kfp_pod(core_api)
      pod_manifest['spec']['serviceAccount'] = launcher_pod.spec.service_account
      pod_manifest['spec'][
          'serviceAccountName'] = launcher_pod.spec.service_account_name
      pod_manifest['metadata'][
          'ownerReferences'] = container_common.to_swagger_dict(
              launcher_pod.metadata.owner_references)
    else:
      pod_manifest['spec']['serviceAccount'] = kube_utils.TFX_SERVICE_ACCOUNT
      pod_manifest['spec'][
          'serviceAccountName'] = kube_utils.TFX_SERVICE_ACCOUNT

    logging.info('Looking for pod "%s:%s".', namespace, pod_name)
    resp = kube_utils.get_pod(core_api, pod_name, namespace)
    if not resp:
      logging.info('Pod "%s:%s" does not exist. Creating it...',
                   namespace, pod_name)
      logging.info('Pod manifest: %s', pod_manifest)
      try:
        resp = core_api.create_namespaced_pod(
            namespace=namespace, body=pod_manifest)
      except client.rest.ApiException as e:
        raise RuntimeError(
            'Failed to created container executor pod!\nReason: %s\nBody: %s' %
            (e.reason, e.body))

    # Wait up to 300 seconds for the pod to move from pending to another status.
    logging.info('Waiting for pod "%s:%s" to start.', namespace, pod_name)
    kube_utils.wait_pod(
        core_api,
        pod_name,
        namespace,
        exit_condition_lambda=kube_utils.pod_is_not_pending,
        condition_description='non-pending status',
        timeout_sec=300)

    logging.info('Start log streaming for pod "%s:%s".', namespace, pod_name)
    try:
      logs = core_api.read_namespaced_pod_log(
          name=pod_name,
          namespace=namespace,
          container=kube_utils.ARGO_MAIN_CONTAINER_NAME,
          follow=True,
          _preload_content=False).stream()
    except client.rest.ApiException as e:
      raise RuntimeError(
          'Failed to stream the logs from the pod!\nReason: %s\nBody: %s' %
          (e.reason, e.body))

    for log in logs:
      logging.info(log.decode().rstrip('\n'))

    # Wait indefinitely for the pod to complete.
    resp = kube_utils.wait_pod(
        core_api,
        pod_name,
        namespace,
        exit_condition_lambda=kube_utils.pod_is_done,
        condition_description='done state')

    if resp.status.phase == kube_utils.PodPhase.FAILED.value:
      raise RuntimeError('Pod "%s:%s" failed with status "%s".' %
                         (namespace, pod_name, resp.status))

    logging.info('Pod "%s:%s" is done.', namespace, pod_name)

    return execution_result_pb2.ExecutorOutput()

  def _build_pod_manifest(
      self, pod_name: str,
      container_spec: executor_specs.TemplatedExecutorContainerSpec
  ) -> Dict[str, Any]:
    """Build a pod spec.

    The function builds a pod spec by patching executor container spec into
    the pod spec from component config.

    Args:
      pod_name: The name of the pod.
      container_spec: The resolved executor container spec.

    Returns:
      The pod manifest in dictionary format.
    """
    pod_manifest = collections.defaultdict(dict)

    pod_manifest.update({
        'apiVersion': 'v1',
        'kind': 'Pod',
    })
    # TODO(hongyes): figure out a better way to figure out type hints for nested
    # dict.
    metadata = pod_manifest['metadata']
    metadata.update({'name': pod_name})
    spec = pod_manifest['spec']
    spec.update({'restartPolicy': 'Never'})
    containers = spec.setdefault('containers', [])  # type: List[Dict[str, Any]]
    container = None  # type: Optional[Dict[str, Any]]
    for c in containers:
      if c['name'] == kube_utils.ARGO_MAIN_CONTAINER_NAME:
        container = c
        break
    if not container:
      container = {'name': kube_utils.ARGO_MAIN_CONTAINER_NAME}
      containers.append(container)
    container.update({
        'image': container_spec.image,
        'command': container_spec.command,
        'args': container_spec.args,
    })
    return pod_manifest

  def _build_pod_name(self, execution_info: data_types.ExecutionInfo) -> str:
    pipeline_name = (
        execution_info.pipeline_info.id[:50] + '-' +
        execution_info.pipeline_run_id[:50])

    pod_name = '%s-%s-%s' % (pipeline_name,
                             execution_info.pipeline_node.node_info.id[:50],
                             execution_info.execution_id)
    return kube_utils.sanitize_pod_name(pod_name)
