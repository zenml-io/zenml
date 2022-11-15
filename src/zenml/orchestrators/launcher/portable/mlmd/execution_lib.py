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
"""Portable libraries for execution related APIs."""

import collections
import itertools
import re
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from absl import logging
from tfx import types
from tfx.orchestration import data_types_utils
from tfx.orchestration import metadata
from tfx.orchestration.portable.mlmd import common_utils
from tfx.orchestration.portable.mlmd import event_lib
from tfx.proto.orchestration import execution_result_pb2
from tfx.proto.orchestration import pipeline_pb2
from tfx.types import artifact_utils
from tfx.utils import proto_utils
from tfx.utils import typing_utils

from google.protobuf import json_format
from ml_metadata.proto import metadata_store_pb2

_EXECUTION_RESULT = '__execution_result__'
_PROPERTY_SCHEMA_PREFIX = '__schema__'
_PROPERTY_SCHEMA_SUFFIX = '__'


def is_execution_successful(execution: metadata_store_pb2.Execution) -> bool:
  """Whether or not an execution is successful.

  Args:
    execution: An execution message.

  Returns:
    A bool value indicating whether or not the execution is successful.
  """
  return (execution.last_known_state == metadata_store_pb2.Execution.COMPLETE or
          execution.last_known_state == metadata_store_pb2.Execution.CACHED)


def is_execution_active(execution: metadata_store_pb2.Execution) -> bool:
  """Returns `True` if an execution is active.

  Args:
    execution: An execution message.

  Returns:
    A bool value indicating whether or not the execution is active.
  """
  return (execution.last_known_state == metadata_store_pb2.Execution.NEW or
          execution.last_known_state == metadata_store_pb2.Execution.RUNNING)


def is_execution_failed(execution: metadata_store_pb2.Execution) -> bool:
  """Whether or not an execution is failed.

  Args:
    execution: An execution message.

  Returns:
    A bool value indicating whether or not the execution is failed.
  """
  return not is_execution_successful(execution) and not is_execution_active(
      execution)


def is_internal_key(key: str) -> bool:
  """Returns `True` if the key is an internal-only execution property key."""
  return key.startswith('__')


def is_schema_key(key: str) -> bool:
  """Returns `True` if the input key corresponds to a schema stored in execution property."""
  return re.fullmatch(r'^__schema__.*__$', key) is not None


def get_schema_key(key: str) -> str:
  """Returns key for storing execution property schema."""
  return _PROPERTY_SCHEMA_PREFIX + key + _PROPERTY_SCHEMA_SUFFIX


def sort_executions_newest_to_oldest(
    executions: Iterable[metadata_store_pb2.Execution]
) -> List[metadata_store_pb2.Execution]:
  """Returns MLMD executions in sorted order, newest to oldest.

  Args:
    executions: An iterable of MLMD executions.

  Returns:
    Executions sorted newest to oldest (based on MLMD execution creation time).
  """
  return sorted(
      executions, key=lambda e: e.create_time_since_epoch, reverse=True)


def prepare_execution(
    metadata_handler: metadata.Metadata,
    execution_type: metadata_store_pb2.ExecutionType,
    state: metadata_store_pb2.Execution.State,
    exec_properties: Optional[Mapping[str, types.ExecPropertyTypes]] = None,
    execution_name: str = '',
) -> metadata_store_pb2.Execution:
  """Creates an execution proto based on the information provided.

  Args:
    metadata_handler: A handler to access MLMD store.
    execution_type: A metadata_pb2.ExecutionType message describing the type of
      the execution.
    state: The state of the execution.
    exec_properties: Execution properties that need to be attached.
    execution_name: Name of the execution.

  Returns:
    A metadata_store_pb2.Execution message.
  """
  execution = metadata_store_pb2.Execution()
  execution.last_known_state = state
  execution.type_id = common_utils.register_type_if_not_exist(
      metadata_handler, execution_type).id
  if execution_name:
    execution.name = execution_name

  exec_properties = exec_properties or {}
  # For every execution property, put it in execution.properties if its key is
  # in execution type schema. Otherwise, put it in execution.custom_properties.
  for k, v in exec_properties.items():
    value = pipeline_pb2.Value()
    value = data_types_utils.set_parameter_value(value, v)

    if value.HasField('schema'):
      # Stores schema in custom_properties for non-primitive types to allow
      # parsing in later stages.
      data_types_utils.set_metadata_value(
          execution.custom_properties[get_schema_key(k)],
          proto_utils.proto_to_json(value.schema))

    if (execution_type.properties.get(k) ==
        data_types_utils.get_metadata_value_type(v)):
      execution.properties[k].CopyFrom(value.field_value)
    else:
      execution.custom_properties[k].CopyFrom(value.field_value)
  logging.debug('Prepared EXECUTION:\n %s', execution)
  return execution


def _create_artifact_and_event_pairs(
    metadata_handler: metadata.Metadata,
    artifact_dict: typing_utils.ArtifactMultiMap,
    event_type: metadata_store_pb2.Event.Type,
) -> List[Tuple[metadata_store_pb2.Artifact, metadata_store_pb2.Event]]:
  """Creates a list of [Artifact, Event] tuples.

  The result of this function will be used in a MLMD put_execution() call.

  Args:
    metadata_handler: A handler to access MLMD store.
    artifact_dict: The source of artifacts to work on. For each unique artifact
      in the dict, creates a tuple for that. Note that all artifacts of the same
      key in the artifact_dict are expected to share the same artifact type. If
      the same artifact is used for multiple keys, several event paths will be
      generated for the same event.
    event_type: The event type of the event to be attached to the artifact

  Returns:
    A list of [Artifact, Event] tuples
  """
  result = []
  artifact_event_map = dict()
  for key, artifact_list in artifact_dict.items():
    artifact_type = None
    for index, artifact in enumerate(artifact_list):
      if (artifact.mlmd_artifact.HasField('id') and
          artifact.id in artifact_event_map):
        event_lib.add_event_path(
            artifact_event_map[artifact.id][1], key=key, index=index)
      else:
        # TODO(b/153904840): If artifact id is present, skip putting the
        # artifact into the pair when MLMD API is ready.
        event = event_lib.generate_event(
            event_type=event_type, key=key, index=index)
        # Reuses already registered type in the same list whenever possible as
        # the artifacts in the same list share the same artifact type.
        if artifact_type:
          assert artifact_type.name == artifact.artifact_type.name, (
              'Artifacts under the same key should share the same artifact '
              'type.')
        artifact_type = common_utils.register_type_if_not_exist(
            metadata_handler, artifact.artifact_type)
        artifact.set_mlmd_artifact_type(artifact_type)
        if artifact.mlmd_artifact.HasField('id'):
          artifact_event_map[artifact.id] = (artifact.mlmd_artifact, event)
        else:
          result.append((artifact.mlmd_artifact, event))
  result.extend(list(artifact_event_map.values()))
  return result


def put_execution(
    metadata_handler: metadata.Metadata,
    execution: metadata_store_pb2.Execution,
    contexts: Sequence[metadata_store_pb2.Context],
    input_artifacts: Optional[typing_utils.ArtifactMultiMap] = None,
    output_artifacts: Optional[typing_utils.ArtifactMultiMap] = None,
    input_event_type: metadata_store_pb2.Event.Type = metadata_store_pb2.Event
    .INPUT,
    output_event_type: metadata_store_pb2.Event.Type = metadata_store_pb2.Event
    .OUTPUT
) -> metadata_store_pb2.Execution:
  """Writes an execution-centric subgraph to MLMD.

  This function mainly leverages metadata.put_execution() method to write the
  execution centric subgraph to MLMD.

  Args:
    metadata_handler: A handler to access MLMD.
    execution: The execution to be written to MLMD.
    contexts: MLMD contexts to associated with the execution.
    input_artifacts: Input artifacts of the execution. Each artifact will be
      linked with the execution through an event with type input_event_type.
      Each artifact will also be linked with every context in the `contexts`
      argument.
    output_artifacts: Output artifacts of the execution. Each artifact will be
      linked with the execution through an event with type output_event_type.
      Each artifact will also be linked with every context in the `contexts`
      argument.
    input_event_type: The type of the input event, default to be INPUT.
    output_event_type: The type of the output event, default to be OUTPUT.

  Returns:
    An MLMD execution that is written to MLMD, with id pupulated.
  """
  artifact_and_events = []
  if input_artifacts:
    artifact_and_events.extend(
        _create_artifact_and_event_pairs(
            metadata_handler=metadata_handler,
            artifact_dict=input_artifacts,
            event_type=input_event_type))
  if output_artifacts:
    artifact_and_events.extend(
        _create_artifact_and_event_pairs(
            metadata_handler=metadata_handler,
            artifact_dict=output_artifacts,
            event_type=output_event_type))
  execution_id, artifact_ids, contexts_ids = (
      metadata_handler.store.put_execution(
          execution=execution,
          artifact_and_events=artifact_and_events,
          contexts=contexts,
          reuse_context_if_already_exist=True))
  execution.id = execution_id
  for artifact_and_event, a_id in zip(artifact_and_events, artifact_ids):
    artifact, _ = artifact_and_event
    artifact.id = a_id
  for context, c_id in zip(contexts, contexts_ids):
    context.id = c_id

  return execution


def get_executions_associated_with_all_contexts(
    metadata_handler: metadata.Metadata,
    contexts: Iterable[metadata_store_pb2.Context]
) -> List[metadata_store_pb2.Execution]:
  """Returns executions that are associated with all given contexts.

  Args:
    metadata_handler: A handler to access MLMD.
    contexts: MLMD contexts for which to fetch associated executions.

  Returns:
    A list of executions associated with all given contexts.
  """
  executions_dict = None
  for context in contexts:
    executions = metadata_handler.store.get_executions_by_context(context.id)
    if executions_dict is None:
      executions_dict = {e.id: e for e in executions}
    else:
      executions_dict = {e.id: e for e in executions if e.id in executions_dict}
  return list(executions_dict.values()) if executions_dict else []


def get_artifact_ids_by_event_type_for_execution_id(
    metadata_handler: metadata.Metadata,
    execution_id: int) -> Dict['metadata_store_pb2.Event.Type', Set[int]]:
  """Returns artifact ids corresponding to the execution id grouped by event type.

  Args:
    metadata_handler: A handler to access MLMD.
    execution_id: Id of the execution for which to get artifact ids.

  Returns:
    A `dict` mapping event type to `set` of artifact ids.
  """
  events = metadata_handler.store.get_events_by_execution_ids([execution_id])
  result = collections.defaultdict(set)
  for event in events:
    result[event.type].add(event.artifact_id)
  return result


def get_artifacts_dict(
    metadata_handler: metadata.Metadata, execution_id: int,
    event_types: 'List[metadata_store_pb2.Event.Type]'
) -> typing_utils.ArtifactMultiDict:
  """Returns a map from key to an ordered list of artifacts for the given execution id.

  The dict is constructed purely from information stored in MLMD for the
  execution given by `execution_id`. The "key" is the tag associated with the
  `InputSpec` or `OutputSpec` in the pipeline IR.

  Args:
    metadata_handler: A handler to access MLMD.
    execution_id: Id of the execution for which to get artifacts.
    event_types: Event types to filter by.

  Returns:
    A dict mapping key to an ordered list of artifacts.

  Raises:
    ValueError: If the events are badly formed and correct ordering of
      artifacts cannot be determined or if all the artifacts could not be
      fetched from MLMD.
  """
  events = metadata_handler.store.get_events_by_execution_ids([execution_id])

  # Create a map from "key" to list of (index, artifact_id)s.
  indexed_artifact_ids_dict = collections.defaultdict(list)
  for event in events:
    if event.type not in event_types:
      continue
    key, index = event_lib.get_artifact_path(event)
    artifact_id = event.artifact_id
    indexed_artifact_ids_dict[key].append((index, artifact_id))

  # Create a map from "key" to ordered list of artifact ids.
  artifact_ids_dict = {}
  for key, indexed_artifact_ids in indexed_artifact_ids_dict.items():
    ordered_artifact_ids = sorted(indexed_artifact_ids, key=lambda x: x[0])
    # There shouldn't be any missing or duplicate indices.
    indices = [idx for idx, _ in ordered_artifact_ids]
    if indices != list(range(0, len(indices))):
      raise ValueError(
          f'Cannot construct artifact ids dict due to missing or duplicate '
          f'indices: {indexed_artifact_ids_dict}')
    artifact_ids_dict[key] = [aid for _, aid in ordered_artifact_ids]

  # Fetch all the relevant artifacts.
  all_artifact_ids = list(itertools.chain(*artifact_ids_dict.values()))
  mlmd_artifacts = metadata_handler.store.get_artifacts_by_id(all_artifact_ids)
  if len(all_artifact_ids) != len(mlmd_artifacts):
    raise ValueError('Could not find all mlmd artifacts for ids: {}'.format(
        ', '.join(all_artifact_ids)))

  # Fetch artifact types and create a map keyed by artifact type id.
  artifact_type_ids = set(a.type_id for a in mlmd_artifacts)
  artifact_types = metadata_handler.store.get_artifact_types_by_id(
      artifact_type_ids)
  artifact_types_by_id = {a.id: a for a in artifact_types}

  # Set `type` field in the artifact proto which is not filled by MLMD.
  for artifact in mlmd_artifacts:
    artifact.type = artifact_types_by_id[artifact.type_id].name

  # Create a map from artifact id to `types.Artifact` instances.
  artifacts_by_id = {
      a.id: artifact_utils.deserialize_artifact(artifact_types_by_id[a.type_id],
                                                a) for a in mlmd_artifacts
  }

  # Create a map from "key" to ordered list of `types.Artifact` to be returned.
  # The ordering of artifacts is in accordance with their "index" derived from
  # the events above.
  result = collections.defaultdict(list)
  for key, artifact_ids in artifact_ids_dict.items():
    for artifact_id in artifact_ids:
      result[key].append(artifacts_by_id[artifact_id])

  return result


def set_execution_result(execution_result: execution_result_pb2.ExecutionResult,
                         execution: metadata_store_pb2.Execution):
  """Sets execution result as a custom property of execution.

  Args:
    execution_result: The result of execution. It is typically generated by
      executor.
    execution: The execution to set to.
  """
  execution.custom_properties[_EXECUTION_RESULT].string_value = (
      json_format.MessageToJson(execution_result))
