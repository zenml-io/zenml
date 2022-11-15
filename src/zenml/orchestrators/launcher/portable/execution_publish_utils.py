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
"""Portable library for registering and publishing executions."""
import copy
import os
from typing import Mapping, Optional, Sequence
import uuid
from absl import logging

from tfx import types
from tfx.orchestration import metadata
from tfx.orchestration.portable.mlmd import execution_lib
from tfx.proto.orchestration import execution_result_pb2
from tfx.utils import typing_utils

from ml_metadata.proto import metadata_store_pb2


def _check_validity(new_artifact: metadata_store_pb2.Artifact,
                    original_artifact: types.Artifact,
                    has_multiple_artifacts: bool) -> None:
  """Check the validity of new artifact against the original artifact."""
  if new_artifact.type_id != original_artifact.type_id:
    raise RuntimeError('Executor output should not change artifact type.')

  if has_multiple_artifacts:
    # If there are multiple artifacts in the executor output, their URIs should
    # be a direct sub-dir of the system generated URI.
    if os.path.dirname(new_artifact.uri) != original_artifact.uri:
      raise RuntimeError(
          'When there are multiple artifacts to publish, their URIs '
          'should be direct sub-directories of the URI of the system generated '
          'artifact.')
  else:
    # If there is only one output artifact, its URI should not be changed
    if new_artifact.uri != original_artifact.uri:
      # TODO(b/175426744): Data Binder will modify the uri.
      logging.warning(
          'When there is one artifact to publish, the URI of it should be '
          'identical to the URI of system generated artifact.')


def publish_cached_execution(
    metadata_handler: metadata.Metadata,
    contexts: Sequence[metadata_store_pb2.Context],
    execution_id: int,
    output_artifacts: Optional[typing_utils.ArtifactMultiMap] = None,
) -> None:
  """Marks an existing execution as using cached outputs from a previous execution.

  Args:
    metadata_handler: A handler to access MLMD.
    contexts: MLMD contexts to associated with the execution.
    execution_id: The id of the execution.
    output_artifacts: Output artifacts of the execution. Each artifact will be
      linked with the execution through an event with type OUTPUT.
  """
  [execution] = metadata_handler.store.get_executions_by_id([execution_id])
  execution.last_known_state = metadata_store_pb2.Execution.CACHED

  execution_lib.put_execution(
      metadata_handler,
      execution,
      contexts,
      input_artifacts=None,
      output_artifacts=output_artifacts)


def _set_execution_result_if_not_empty(
    executor_output: Optional[execution_result_pb2.ExecutorOutput],
    execution: metadata_store_pb2.Execution) -> bool:
  """Sets execution result as a custom property of the execution."""
  if executor_output and (executor_output.execution_result.result_message or
                          executor_output.execution_result.metadata_details or
                          executor_output.execution_result.code):
    # TODO(b/190001754): Consider either switching to base64 encoding or using
    # a proto descriptor pool to circumvent TypeError which may be raised when
    # converting embedded `Any` protos.
    try:
      execution_lib.set_execution_result(executor_output.execution_result,
                                         execution)
    except TypeError:
      logging.exception(
          'Skipped setting execution_result as custom property of the '
          'execution due to error')


def publish_succeeded_execution(
    metadata_handler: metadata.Metadata,
    execution_id: int,
    contexts: Sequence[metadata_store_pb2.Context],
    output_artifacts: Optional[typing_utils.ArtifactMultiMap] = None,
    executor_output: Optional[execution_result_pb2.ExecutorOutput] = None
) -> Optional[typing_utils.ArtifactMultiMap]:
  """Marks an existing execution as success.

  Also publishes the output artifacts produced by the execution. This method
  will also merge the executor produced info into system generated output
  artifacts. The `last_know_state` of the execution will be changed to
  `COMPLETE` and the output artifacts will be marked as `LIVE`.

  Args:
    metadata_handler: A handler to access MLMD.
    execution_id: The id of the execution to mark successful.
    contexts: MLMD contexts to associated with the execution.
    output_artifacts: Output artifacts skeleton of the execution, generated by
      the system. Each artifact will be linked with the execution through an
      event with type OUTPUT.
    executor_output: Executor outputs. `executor_output.output_artifacts` will
      be used to update system-generated output artifacts passed in through
      `output_artifacts` arg. There are three contraints to the update: 1. The
        keys in `executor_output.output_artifacts` are expected to be a subset
        of the system-generated output artifacts dict. 2. An update to a certain
        key should contains all the artifacts under that key. 3. An update to an
        artifact should not change the type of the artifact.

  Returns:
    The maybe updated output_artifacts, note that only outputs whose key are in
    executor_output will be updated and others will be untouched. That said,
    it can be partially updated.
  Raises:
    RuntimeError: if the executor output to a output channel is partial.
  """
  if output_artifacts is not None:
    output_artifacts = {key: [copy.deepcopy(a) for a in artifacts]
                        for key, artifacts in output_artifacts.items()}
  else:
    output_artifacts = {}

  if executor_output:
    if not set(executor_output.output_artifacts.keys()).issubset(
        output_artifacts.keys()):
      raise RuntimeError(
          'Executor output %s contains more keys than output skeleton %s.' %
          (executor_output, output_artifacts))
    for key, artifact_list in output_artifacts.items():
      if key not in executor_output.output_artifacts:
        continue
      updated_artifact_list = executor_output.output_artifacts[key].artifacts

      # We assume the original output dict must include at least one output
      # artifact and all artifacts in the list share the same type.
      original_artifact = artifact_list[0]
      # Update the artifact list with what's in the executor output
      artifact_list.clear()
      # TODO(b/175426744): revisit this:
      # 1) Whether multiple output is needed or not after TFX componets
      #    are upgraded.
      # 2) If multiple output are needed and is a common practice, should we
      #    use driver instead to create the list of output artifact instead
      #    of letting executor to create them.
      for proto_artifact in updated_artifact_list:
        _check_validity(proto_artifact, original_artifact,
                        len(updated_artifact_list) > 1)
        python_artifact = types.Artifact(original_artifact.artifact_type)
        python_artifact.set_mlmd_artifact(proto_artifact)
        artifact_list.append(python_artifact)

  # Marks output artifacts as LIVE.
  for artifact_list in output_artifacts.values():
    for artifact in artifact_list:
      artifact.mlmd_artifact.state = metadata_store_pb2.Artifact.LIVE

  [execution] = metadata_handler.store.get_executions_by_id([execution_id])
  execution.last_known_state = metadata_store_pb2.Execution.COMPLETE
  if executor_output:
    for key, value in executor_output.execution_properties.items():
      execution.custom_properties[key].CopyFrom(value)
  _set_execution_result_if_not_empty(executor_output, execution)

  execution_lib.put_execution(
      metadata_handler, execution, contexts, output_artifacts=output_artifacts)

  return output_artifacts


def publish_failed_execution(
    metadata_handler: metadata.Metadata,
    contexts: Sequence[metadata_store_pb2.Context],
    execution_id: int,
    executor_output: Optional[execution_result_pb2.ExecutorOutput] = None
) -> None:
  """Marks an existing execution as failed.

  Args:
    metadata_handler: A handler to access MLMD.
    contexts: MLMD contexts to associated with the execution.
    execution_id: The id of the execution.
    executor_output: The output of executor.
  """
  [execution] = metadata_handler.store.get_executions_by_id([execution_id])
  execution.last_known_state = metadata_store_pb2.Execution.FAILED
  _set_execution_result_if_not_empty(executor_output, execution)

  execution_lib.put_execution(metadata_handler, execution, contexts)


def publish_internal_execution(
    metadata_handler: metadata.Metadata,
    contexts: Sequence[metadata_store_pb2.Context],
    execution_id: int,
    output_artifacts: Optional[typing_utils.ArtifactMultiMap] = None
) -> None:
  """Marks an exeisting execution as as success and links its output to an INTERNAL_OUTPUT event.

  Args:
    metadata_handler: A handler to access MLMD.
    contexts: MLMD contexts to associated with the execution.
    execution_id: The id of the execution.
    output_artifacts: Output artifacts of the execution. Each artifact will be
      linked with the execution through an event with type INTERNAL_OUTPUT.
  """
  [execution] = metadata_handler.store.get_executions_by_id([execution_id])
  execution.last_known_state = metadata_store_pb2.Execution.COMPLETE

  execution_lib.put_execution(
      metadata_handler,
      execution,
      contexts,
      output_artifacts=output_artifacts,
      output_event_type=metadata_store_pb2.Event.INTERNAL_OUTPUT)


def register_execution(
    metadata_handler: metadata.Metadata,
    execution_type: metadata_store_pb2.ExecutionType,
    contexts: Sequence[metadata_store_pb2.Context],
    input_artifacts: Optional[typing_utils.ArtifactMultiMap] = None,
    exec_properties: Optional[Mapping[str, types.ExecPropertyTypes]] = None,
    last_known_state: metadata_store_pb2.Execution.State = metadata_store_pb2
    .Execution.RUNNING
) -> metadata_store_pb2.Execution:
  """Registers a new execution in MLMD.

  Along with the execution:
  -  the input artifacts will be linked to the execution.
  -  the contexts will be linked to both the execution and its input artifacts.

  Args:
    metadata_handler: A handler to access MLMD.
    execution_type: The type of the execution.
    contexts: MLMD contexts to associated with the execution.
    input_artifacts: Input artifacts of the execution. Each artifact will be
      linked with the execution through an event.
    exec_properties: Execution properties. Will be attached to the execution.
    last_known_state: The last known state of the execution.

  Returns:
    An MLMD execution that is registered in MLMD, with id populated.
  """
  # Setting exec_name is required to make sure that only one execution is
  # registered in MLMD. If there is a RPC retry, AlreadyExistError will raise.
  # After this fix (b/221103319), AlreadyExistError may not raise. Instead,
  # execution may be updated again upon RPC retries.
  exec_name = str(uuid.uuid4())
  execution = execution_lib.prepare_execution(
      metadata_handler,
      execution_type,
      last_known_state,
      exec_properties,
      execution_name=exec_name)

  return execution_lib.put_execution(
      metadata_handler, execution, contexts, input_artifacts=input_artifacts)
