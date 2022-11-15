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
"""This module defines a generic Launcher for all TFleX nodes."""

import sys
import traceback
from typing import Any, Dict, List, Mapping, Optional, Type, TypeVar

from absl import logging
import attr
import grpc
import portpicker
from tfx import types
from tfx.dsl.io import fileio
from tfx.orchestration import data_types_utils
from tfx.orchestration import metadata
from tfx.orchestration.portable import base_driver_operator
from tfx.orchestration.portable import base_executor_operator
from tfx.orchestration.portable import beam_executor_operator
from tfx.orchestration.portable import cache_utils
from tfx.orchestration.portable import data_types
from tfx.orchestration.portable import docker_executor_operator
from tfx.orchestration.portable import execution_publish_utils
from tfx.orchestration.portable import execution_watcher
from tfx.orchestration.portable import importer_node_handler
from tfx.orchestration.portable import inputs_utils
from tfx.orchestration.portable import outputs_utils
from tfx.orchestration.portable import python_driver_operator
from tfx.orchestration.portable import python_executor_operator
from tfx.orchestration.portable import resolver_node_handler
from tfx.orchestration.portable.input_resolution import exceptions
from tfx.orchestration.portable.mlmd import context_lib
from tfx.orchestration.portable.mlmd import execution_lib
from tfx.proto.orchestration import driver_output_pb2
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration import execution_result_pb2
from tfx.proto.orchestration import pipeline_pb2
from tfx.utils import typing_utils

from google.protobuf import message
from ml_metadata.proto import metadata_store_pb2

# Subclasses of BaseExecutorOperator
ExecutorOperator = TypeVar(
    'ExecutorOperator', bound=base_executor_operator.BaseExecutorOperator)

# Subclasses of BaseDriverOperator
DriverOperator = TypeVar(
    'DriverOperator', bound=base_driver_operator.BaseDriverOperator)

DEFAULT_EXECUTOR_OPERATORS = {
    executable_spec_pb2.PythonClassExecutableSpec:
        python_executor_operator.PythonExecutorOperator,
    executable_spec_pb2.BeamExecutableSpec:
        beam_executor_operator.BeamExecutorOperator,
    executable_spec_pb2.ContainerExecutableSpec:
        docker_executor_operator.DockerExecutorOperator
}

DEFAULT_DRIVER_OPERATORS = {
    executable_spec_pb2.PythonClassExecutableSpec:
        python_driver_operator.PythonDriverOperator
}

# LINT.IfChange
_SYSTEM_NODE_HANDLERS = {
    'tfx.dsl.components.common.importer.Importer':
        importer_node_handler.ImporterNodeHandler,
    'tfx.dsl.components.common.resolver.Resolver':
        resolver_node_handler.ResolverNodeHandler,
}
# LINT.ThenChange(Internal system node list)

_ERROR_CODE_UNIMPLEMENTED: int = grpc.StatusCode.UNIMPLEMENTED.value[0]


@attr.s(auto_attribs=True)
class _ExecutionPreparationResult:
  """A wrapper class using as the return value of _prepare_execution()."""

  # The information used by executor operators.
  execution_info: data_types.ExecutionInfo
  # The Execution registered in MLMD.
  execution_metadata: Optional[metadata_store_pb2.Execution] = None
  # Contexts of the execution, usually used by Publisher.
  contexts: List[metadata_store_pb2.Context] = attr.Factory(list)
  # TODO(b/156126088): Update the following documentation when this bug is
  # closed.
  # Whether an execution is needed. An execution is not needed when:
  # 1) Not all the required input are ready.
  # 2) The input value doesn't meet the driver's requirement.
  # 3) Cache result is used.
  is_execution_needed: bool = False


class _ExecutionFailedError(Exception):
  """An internal error to carry ExecutorOutput when it is raised."""

  def __init__(self, err_msg: str,
               executor_output: execution_result_pb2.ExecutorOutput):
    super().__init__(err_msg)
    self._executor_output = executor_output

  @property
  def executor_output(self):
    return self._executor_output


def _register_execution(
    metadata_handler: metadata.Metadata,
    execution_type: metadata_store_pb2.ExecutionType,
    contexts: List[metadata_store_pb2.Context],
    input_artifacts: Optional[typing_utils.ArtifactMultiMap] = None,
    exec_properties: Optional[Mapping[str, types.Property]] = None,
) -> metadata_store_pb2.Execution:
  """Registers an execution in MLMD."""
  return execution_publish_utils.register_execution(
      metadata_handler=metadata_handler,
      execution_type=execution_type,
      contexts=contexts,
      input_artifacts=input_artifacts,
      exec_properties=exec_properties)


class Launcher:
  """Launcher is the main entrance of nodes in TFleX.

     It handles TFX internal details like artifact resolving, execution
     triggering and result publishing.
  """

  def __init__(
      self,
      pipeline_node: pipeline_pb2.PipelineNode,
      mlmd_connection: metadata.Metadata,
      pipeline_info: pipeline_pb2.PipelineInfo,
      pipeline_runtime_spec: pipeline_pb2.PipelineRuntimeSpec,
      executor_spec: Optional[message.Message] = None,
      custom_driver_spec: Optional[message.Message] = None,
      platform_config: Optional[message.Message] = None,
      custom_executor_operators: Optional[Dict[Any,
                                               Type[ExecutorOperator]]] = None,
      custom_driver_operators: Optional[Dict[Any,
                                             Type[DriverOperator]]] = None):
    """Initializes a Launcher.

    Args:
      pipeline_node: The specification of the node that this launcher lauches.
      mlmd_connection: ML metadata connection.
      pipeline_info: The information of the pipeline that this node runs in.
      pipeline_runtime_spec: The runtime information of the pipeline that this
        node runs in.
      executor_spec: Specification for the executor of the node. This is
        expected for all components nodes. This will be used to determine the
        specific ExecutorOperator class to be used to execute and will be passed
        into ExecutorOperator.
      custom_driver_spec: Specification for custom driver. This is expected only
        for advanced use cases.
      platform_config: Platform config that will be used as auxiliary info of
        the node execution. This will be passed to ExecutorOperator along with
        the `executor_spec`.
      custom_executor_operators: a map of ExecutableSpec to its
        ExecutorOperation implementation.
      custom_driver_operators: a map of ExecutableSpec to its DriverOperator
        implementation.

    Raises:
      ValueError: when component and component_config are not launchable by the
      launcher.
    """
    self._pipeline_node = pipeline_node
    self._mlmd_connection = mlmd_connection
    self._pipeline_info = pipeline_info
    self._pipeline_runtime_spec = pipeline_runtime_spec
    self._executor_spec = executor_spec
    self._executor_operators = {}
    self._executor_operators.update(DEFAULT_EXECUTOR_OPERATORS)
    self._executor_operators.update(custom_executor_operators or {})
    self._driver_operators = {}
    self._driver_operators.update(DEFAULT_DRIVER_OPERATORS)
    self._driver_operators.update(custom_driver_operators or {})

    self._executor_operator = None
    if executor_spec:
      self._executor_operator = self._executor_operators[type(executor_spec)](
          executor_spec, platform_config)
    self._output_resolver = outputs_utils.OutputsResolver(
        pipeline_node=self._pipeline_node,
        pipeline_info=self._pipeline_info,
        pipeline_runtime_spec=self._pipeline_runtime_spec)

    self._driver_operator = None
    if custom_driver_spec:
      self._driver_operator = self._driver_operators[type(custom_driver_spec)](
          custom_driver_spec, self._mlmd_connection)

    system_node_handler_class = _SYSTEM_NODE_HANDLERS.get(
        self._pipeline_node.node_info.type.name)
    self._system_node_handler = None
    if system_node_handler_class:
      self._system_node_handler = system_node_handler_class()

    assert bool(self._executor_operator) or bool(
        self._system_node_handler
    ), 'A node must be system node or have an executor.'

  def _register_or_reuse_execution(
      self, metadata_handler: metadata.Metadata,
      contexts: List[metadata_store_pb2.Context],
      input_artifacts: Optional[typing_utils.ArtifactMultiMap] = None,
      exec_properties: Optional[Mapping[str, types.Property]] = None,
  ) -> metadata_store_pb2.Execution:
    """Registers or reuses an execution in MLMD."""
    executions = execution_lib.get_executions_associated_with_all_contexts(
        metadata_handler, contexts)
    if len(executions) > 1:
      raise RuntimeError('Expecting no more than one previous executions for'
                         'the associated contexts')
    elif executions:
      execution = executions.pop()
      if execution_lib.is_execution_successful(execution):
        logging.warning('This execution has already succeeded. Will exit '
                        'gracefully to avoid overwriting output artifacts.')
      elif not execution_lib.is_execution_active(execution):
        logging.warning(
            'Expected execution to be in state NEW or RUNNING. Actual state: '
            '%s. Output artifacts may be overwritten.',
            execution.last_known_state)
      return execution
    return _register_execution(
        metadata_handler=metadata_handler,
        execution_type=self._pipeline_node.node_info.type,
        contexts=contexts,
        input_artifacts=input_artifacts,
        exec_properties=exec_properties)

  def _prepare_execution(self) -> _ExecutionPreparationResult:
    """Prepares inputs, outputs and execution properties for actual execution."""
    with self._mlmd_connection as m:
      # 1.Prepares all contexts.
      contexts = context_lib.prepare_contexts(
          metadata_handler=m, node_contexts=self._pipeline_node.contexts)

      # 2. Resolves inputs and execution properties.
      exec_properties = data_types_utils.build_parsed_value_dict(
          inputs_utils.resolve_parameters_with_schema(
              node_parameters=self._pipeline_node.parameters))

      try:
        resolved_inputs = inputs_utils.resolve_input_artifacts(
            pipeline_node=self._pipeline_node,
            metadata_handler=m)
      except exceptions.InputResolutionError as e:
        execution = self._register_or_reuse_execution(
            metadata_handler=m,
            contexts=contexts,
            exec_properties=exec_properties)
        if not execution_lib.is_execution_successful(execution):
          self._publish_failed_execution(
              execution_id=execution.id,
              contexts=contexts,
              executor_output=self._build_error_output(code=e.grpc_code_value))
        return _ExecutionPreparationResult(
            execution_info=self._build_execution_info(
                execution_id=execution.id),
            contexts=contexts,
            is_execution_needed=False)

      # 3. If not all required inputs are met. Return ExecutionInfo with
      # is_execution_needed being false. No publish will happen so down stream
      # nodes won't be triggered.
      # TODO(b/197907821): Publish special execution for Skip?
      if isinstance(resolved_inputs, inputs_utils.Skip):
        logging.info('Skipping execution for %s',
                     self._pipeline_node.node_info.id)
        return _ExecutionPreparationResult(
            execution_info=self._build_execution_info(),
            contexts=contexts,
            is_execution_needed=False)

      # TODO(b/197741942): Support len > 1.
      if len(resolved_inputs) > 1:
        executor_output = self._build_error_output(
            _ERROR_CODE_UNIMPLEMENTED,
            'Handling more than one input dicts not implemented yet.')
        execution = self._register_or_reuse_execution(
            metadata_handler=m,
            contexts=contexts,
            exec_properties=exec_properties)
        if not execution_lib.is_execution_successful(execution):
          self._publish_failed_execution(
              execution_id=execution.id,
              contexts=contexts,
              executor_output=executor_output)
        return _ExecutionPreparationResult(
            execution_info=self._build_execution_info(
                execution_id=execution.id),
            contexts=contexts,
            is_execution_needed=False)

      input_artifacts = resolved_inputs[0]

      # 4. Registers execution in metadata.
      execution = self._register_or_reuse_execution(
          metadata_handler=m,
          contexts=contexts,
          input_artifacts=input_artifacts,
          exec_properties=exec_properties)
      if execution_lib.is_execution_successful(execution):
        return _ExecutionPreparationResult(
            execution_info=self._build_execution_info(
                execution_id=execution.id),
            contexts=contexts,
            is_execution_needed=False)

      # 5. Resolve output
      output_artifacts = self._output_resolver.generate_output_artifacts(
          execution.id)

    # If there is a custom driver, runs it.
    if self._driver_operator:
      driver_output = self._driver_operator.run_driver(
          self._build_execution_info(
              input_dict=input_artifacts,
              output_dict=output_artifacts,
              exec_properties=exec_properties,
              execution_output_uri=(
                  self._output_resolver.get_driver_output_uri())))
      self._update_with_driver_output(driver_output, exec_properties,
                                      output_artifacts)

    # We reconnect to MLMD here because the custom driver closes MLMD connection
    # on returning.
    with self._mlmd_connection as m:
      # 6. Check cached result
      cache_context = cache_utils.get_cache_context(
          metadata_handler=m,
          pipeline_node=self._pipeline_node,
          pipeline_info=self._pipeline_info,
          executor_spec=self._executor_spec,
          input_artifacts=input_artifacts,
          output_artifacts=output_artifacts,
          parameters=exec_properties)
      contexts.append(cache_context)

      # 7. Should cache be used?
      if self._pipeline_node.execution_options.caching_options.enable_cache:
        cached_outputs = cache_utils.get_cached_outputs(
            metadata_handler=m, cache_context=cache_context)
        if cached_outputs is not None:
          # Publishes cache result
          execution_publish_utils.publish_cached_execution(
              metadata_handler=m,
              contexts=contexts,
              execution_id=execution.id,
              output_artifacts=cached_outputs)
          logging.info('An cached execusion %d is used.', execution.id)
          return _ExecutionPreparationResult(
              execution_info=self._build_execution_info(
                  execution_id=execution.id,
                  input_dict=input_artifacts,
                  output_dict=output_artifacts,
                  exec_properties=exec_properties),
              execution_metadata=execution,
              contexts=contexts,
              is_execution_needed=False)

      # 8. Going to trigger executor.
      logging.info('Going to run a new execution %d', execution.id)
      return _ExecutionPreparationResult(
          execution_info=self._build_execution_info(
              execution_id=execution.id,
              input_dict=input_artifacts,
              output_dict=output_artifacts,
              exec_properties=exec_properties,
              execution_output_uri=(
                  self._output_resolver.get_executor_output_uri(execution.id)),
              stateful_working_dir=(
                  self._output_resolver.get_stateful_working_directory()),
              tmp_dir=self._output_resolver.make_tmp_dir(execution.id)),
          execution_metadata=execution,
          contexts=contexts,
          is_execution_needed=True)

  def _build_execution_info(self, **kwargs: Any) -> data_types.ExecutionInfo:
    # pytype: disable=wrong-arg-types
    kwargs.update(
        pipeline_node=self._pipeline_node,
        pipeline_info=self._pipeline_info,
        pipeline_run_id=(self._pipeline_runtime_spec.pipeline_run_id
                         .field_value.string_value))
    # pytype: enable=wrong-arg-types
    return data_types.ExecutionInfo(**kwargs)

  def _build_error_output(
      self, code: int, msg: Optional[str] = None
  ) -> execution_result_pb2.ExecutorOutput:
    if msg is None:
      msg = '\n'.join(traceback.format_exception(*sys.exc_info()))
    return execution_result_pb2.ExecutorOutput(
        execution_result=execution_result_pb2.ExecutionResult(
            code=code, result_message=msg))

  def _run_executor(
      self, execution_info: data_types.ExecutionInfo
  ) -> execution_result_pb2.ExecutorOutput:
    """Executes underlying component implementation."""

    logging.info('Going to run a new execution: %s', execution_info)

    outputs_utils.make_output_dirs(execution_info.output_dict)
    try:
      executor_output = self._executor_operator.run_executor(execution_info)
      code = executor_output.execution_result.code
      if code != 0:
        result_message = executor_output.execution_result.result_message
        err = (f'Execution {execution_info.execution_id} '
               f'failed with error code {code} and '
               f'error message {result_message}')
        logging.error(err)
        raise _ExecutionFailedError(err, executor_output)
      return executor_output
    except Exception:  # pylint: disable=broad-except
      outputs_utils.remove_output_dirs(execution_info.output_dict)
      raise

  def _publish_successful_execution(
      self, execution_id: int, contexts: List[metadata_store_pb2.Context],
      output_dict: typing_utils.ArtifactMultiMap,
      executor_output: execution_result_pb2.ExecutorOutput) -> None:
    """Publishes succeeded execution result to ml metadata."""
    with self._mlmd_connection as m:
      execution_publish_utils.publish_succeeded_execution(
          metadata_handler=m,
          execution_id=execution_id,
          contexts=contexts,
          output_artifacts=output_dict,
          executor_output=executor_output)

  def _publish_failed_execution(
      self,
      execution_id: int,
      contexts: List[metadata_store_pb2.Context],
      executor_output: Optional[execution_result_pb2.ExecutorOutput] = None
  ) -> None:
    """Publishes failed execution to ml metadata."""
    with self._mlmd_connection as m:
      execution_publish_utils.publish_failed_execution(
          metadata_handler=m,
          execution_id=execution_id,
          contexts=contexts,
          executor_output=executor_output)

  def _clean_up_stateless_execution_info(
      self, execution_info: data_types.ExecutionInfo):
    logging.info('Cleaning up stateless execution info.')
    # Clean up tmp dir
    try:
      fileio.rmtree(execution_info.tmp_dir)
    except fileio.NotFoundError:
      # TODO(b/182964682): investigate the root cause of why this is happening.
      logging.warning(
          'execution_info.tmp_dir %s is not found, it is likely that it has '
          'been deleted by the executor. This is the full execution_info: %s',
          execution_info.tmp_dir, execution_info.to_proto())

  def _clean_up_stateful_execution_info(
      self, execution_info: data_types.ExecutionInfo):
    """Post execution clean up."""
    logging.info('Cleaning up stateful execution info.')
    outputs_utils.remove_stateful_working_dir(
        execution_info.stateful_working_dir)

  def _update_with_driver_output(
      self,
      driver_output: driver_output_pb2.DriverOutput,
      exec_properties: Dict[str, Any],
      output_dict: typing_utils.ArtifactMutableMultiMap):
    """Updates output_dict with driver output."""
    for key, artifact_list in driver_output.output_artifacts.items():
      python_artifact_list = []
      assert output_dict[key], 'Output artifacts should not be empty.'
      artifact_cls = output_dict[key][0].type
      assert all(artifact_cls == a.type for a in output_dict[key][1:]
                ), 'All artifacts should have a same type.'

      for proto_artifact in artifact_list.artifacts:
        # Create specific artifact class instance for easier class
        # identification and property access.
        python_artifact = artifact_cls()
        python_artifact.set_mlmd_artifact(proto_artifact)
        python_artifact_list.append(python_artifact)
      output_dict[key] = python_artifact_list

    for key, value in driver_output.exec_properties.items():
      exec_properties[key] = getattr(value, value.WhichOneof('value'))

  def launch(self) -> Optional[data_types.ExecutionInfo]:
    """Executes the component, includes driver, executor and publisher.

    Returns:
      The metadata of this execution that is registered in MLMD. It can be None
      if the driver decides not to run the execution.

    Raises:
      Exception: If the executor fails.
    """
    logging.info('Running launcher for %s', self._pipeline_node)
    if self._system_node_handler:
      # If this is a system node, runs it and directly return.
      return self._system_node_handler.run(self._mlmd_connection,
                                           self._pipeline_node,
                                           self._pipeline_info,
                                           self._pipeline_runtime_spec)

    # Runs as a normal node.
    execution_preparation_result = self._prepare_execution()
    (execution_info, contexts,
     is_execution_needed) = (execution_preparation_result.execution_info,
                             execution_preparation_result.contexts,
                             execution_preparation_result.is_execution_needed)
    if is_execution_needed:
      executor_watcher = None
      try:
        if self._executor_operator:
          # Create an execution watcher and save an in memory copy of the
          # Execution object to execution to it. Launcher calls executor
          # operator in process, thus there won't be race condition between the
          # execution watcher and the launcher to write to MLMD.
          executor_watcher = execution_watcher.ExecutionWatcher(
              port=portpicker.pick_unused_port(),
              mlmd_connection=self._mlmd_connection,
              execution=execution_preparation_result.execution_metadata,
              creds=grpc.local_server_credentials())
          self._executor_operator.with_execution_watcher(
              executor_watcher.address)
          executor_watcher.start()
        executor_output = self._run_executor(execution_info)
      except Exception as e:  # pylint: disable=broad-except
        execution_output = (
            e.executor_output if isinstance(e, _ExecutionFailedError) else None)
        self._publish_failed_execution(execution_info.execution_id, contexts,
                                       execution_output)
        logging.error('Execution %d failed.', execution_info.execution_id)
        raise
      finally:
        self._clean_up_stateless_execution_info(execution_info)
        if executor_watcher:
          executor_watcher.stop()

      logging.info('Execution %d succeeded.', execution_info.execution_id)
      self._clean_up_stateful_execution_info(execution_info)

      # TODO(b/182316162): Unify publisher handing so that post-execution
      # artifact logic is more cleanly handled.
      # Note that currently both the ExecutionInfo and ExecutorOutput are
      # consulted in `execution_publish_utils.publish_succeeded_execution()`.
      outputs_utils.tag_executor_output_with_version(executor_output)
      outputs_utils.tag_output_artifacts_with_version(
          execution_info.output_dict)
      logging.info('Publishing output artifacts %s for execution %s',
                   execution_info.output_dict, execution_info.execution_id)
      self._publish_successful_execution(execution_info.execution_id, contexts,
                                         execution_info.output_dict,
                                         executor_output)
    return execution_info
