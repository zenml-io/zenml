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
"""Portable libraries for event related APIs."""

from typing import Optional, Tuple

from ml_metadata.proto import metadata_store_pb2


VALID_OUTPUT_EVENT_TYPES = frozenset([
    metadata_store_pb2.Event.OUTPUT, metadata_store_pb2.Event.INTERNAL_OUTPUT,
    metadata_store_pb2.Event.DECLARED_OUTPUT
])
_VALID_INPUT_EVENT_TYPES = frozenset([
    metadata_store_pb2.Event.INPUT, metadata_store_pb2.Event.INTERNAL_INPUT,
    metadata_store_pb2.Event.DECLARED_INPUT
])


def is_valid_output_event(event: metadata_store_pb2.Event,
                          expected_output_key: Optional[str] = None) -> bool:
  """Evaluates whether an event is an output event with the right output key.

  Args:
    event: The event to evaluate.
    expected_output_key: The expected output key.

  Returns:
    A bool value indicating result
  """
  if expected_output_key:
    return (len(event.path.steps) == 2 and  # Valid event should have 2 steps.
            event.path.steps[0].key == expected_output_key
            and event.type in VALID_OUTPUT_EVENT_TYPES)
  else:
    return event.type in VALID_OUTPUT_EVENT_TYPES


def is_valid_input_event(event: metadata_store_pb2.Event,
                         expected_input_key: Optional[str] = None) -> bool:
  """Evaluates whether an event is an input event with the right input key.

  Args:
    event: The event to evaluate.
    expected_input_key: The expected input key.

  Returns:
    A bool value indicating result
  """
  if expected_input_key:
    # Valid event should have even number of steps.
    if not (event.type in _VALID_INPUT_EVENT_TYPES and
            len(event.path.steps) % 2 == 0):
      return False
    keys = set(s.key for s in event.path.steps if s.HasField('key'))
    return expected_input_key in keys
  else:
    return event.type in _VALID_INPUT_EVENT_TYPES


def add_event_path(
    event: metadata_store_pb2.Event,
    key: str,
    index: int) -> None:
  """Adds event path to a given MLMD event."""
  # The order matters, we always use the first step to store key and the second
  # step to store index.
  event.path.steps.add().key = key
  event.path.steps.add().index = index


def generate_event(
    event_type: metadata_store_pb2.Event.Type,
    key: str,
    index: int,
    artifact_id: Optional[int] = None,
    execution_id: Optional[int] = None) -> metadata_store_pb2.Event:
  """Generates a MLMD event given type, key and index.

  Args:
    event_type: The type of the event. e.g., INPUT, OUTPUT, etc.
    key: The key of the input or output channel. Usually a key can uniquely
      identify a channel of a TFX node.
    index: The index of the artifact in a channel. For example, a trainer might
      take more than one Example artifacts in one of its input channels. We need
      to distinguish each artifact when creating events.
    artifact_id: Optional artifact id for the event.
    execution_id: Optional execution id for the event.

  Returns:
    A metadata_store_pb2.Event message.
  """
  event = metadata_store_pb2.Event()
  event.type = event_type
  # The order matters, we always use the first step to store key and the second
  # step to store index.
  event.path.steps.add().key = key
  event.path.steps.add().index = index
  if artifact_id:
    event.artifact_id = artifact_id
  if execution_id:
    event.execution_id = execution_id

  return event


def get_artifact_path(event: metadata_store_pb2.Event) -> Tuple[str, int]:
  """Gets the artifact path from the event.

  This is useful for reconstructing the artifact dict (mapping from key to an
  ordered list of artifacts) for an execution. The key and index of an artifact
  are expected to be stored in the event in two steps where the first step is
  the key and second is the index of the artifact within the list.

  Args:
    event: The event from which to extract path to the artifact.

  Returns:
    A tuple (<artifact key>, <artifact index>).

  Raises:
    ValueError: If there are not exactly 2 steps in the path corresponding to
      the key and index of the artifact.
  """
  if len(event.path.steps) != 2:
    raise ValueError(
        'Expected exactly two steps corresponding to key and index in event: {}'
        .format(event))
  return (event.path.steps[0].key, event.path.steps[1].index)
