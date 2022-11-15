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
"""Utilities for TFX Runtime Parameters."""
from typing import Mapping, Optional, cast, Dict

from tfx import types
from tfx.orchestration import data_types_utils
from tfx.proto.orchestration import pipeline_pb2

from google.protobuf import descriptor
from google.protobuf import message


def _is_type_match(v_type, v):
  if isinstance(v, int):
    return v_type == pipeline_pb2.RuntimeParameter.INT
  elif isinstance(v, float):
    return v_type == pipeline_pb2.RuntimeParameter.DOUBLE
  elif isinstance(v, str):
    return v_type == pipeline_pb2.RuntimeParameter.STRING
  else:
    raise RuntimeError('Unexpected binding value type: %s' % type(v))


def _get_runtime_parameter_value(
    runtime_parameter: pipeline_pb2.RuntimeParameter,
    parameter_bindings: Mapping[str,
                                types.Property]) -> Optional[types.Property]:
  """Populates the value for a RuntimeParameter when possible.

  If external parameter bindings not found, try to use the default value.

  Args:
    runtime_parameter: RuntimeParameter as the template.
    parameter_bindings: Parameter bindings to substitute runtime parameter
      placeholders in the RuntimeParameter.

  Returns:
    Resolved value for the RuntimeParameter if available. Returns None if the
    RuntimeParameter cannot be resolved.

  Raises:
    RuntimeError: When the provided binding value type does not match the
      RuntimeParameter type requirement.
  """
  # If no external parameter bindings for this runtime parameter, try to use its
  # default value.
  if runtime_parameter.name not in parameter_bindings:
    if runtime_parameter.HasField('default_value'):
      default_value = getattr(
          runtime_parameter.default_value,
          runtime_parameter.default_value.WhichOneof('value'))
      if _is_type_match(runtime_parameter.type, default_value):
        return default_value
      else:
        raise RuntimeError('Runtime parameter type %s does not match with %s.' %
                           (type(default_value), runtime_parameter))
    else:
      return None

  # External parameter binding is found, try to use it.
  binding_value = parameter_bindings[runtime_parameter.name]
  if _is_type_match(runtime_parameter.type, binding_value):
    return binding_value
  else:
    raise RuntimeError('Runtime parameter type %s does not match with %s.' %
                       (type(binding_value), runtime_parameter))


def _get_structural_runtime_parameter_value(
    structural_runtime_parameter: pipeline_pb2.StructuralRuntimeParameter,
    parameter_bindings: Mapping[str, types.Property],
    populated_values: Dict[str, Optional[types.Property]]) -> Optional[str]:
  """Populates the value for a StructuralRuntimeParameter when possible.

  Only populates the value when all parts in the structural runtime parameter
  are resolved to values.

  Args:
    structural_runtime_parameter: The StructuralRuntimeParameter message as the
      template.
    parameter_bindings: Parameter bindings to substitute runtime parameter
      placeholders in the StructuralRuntimeParameter.
    populated_values: A dict of all runtime parameters to their populated
      values.

  Returns:
    A string if all parts are resolved. Returns None otherwise.
  """
  parts = []
  for part in structural_runtime_parameter.parts:
    if part.WhichOneof('value') == 'constant_value':
      parts.append(part.constant_value)
    else:
      part_value = _get_runtime_parameter_value(part.runtime_parameter,
                                                parameter_bindings)
      populated_values[part.runtime_parameter.name] = part_value
      if part_value is None:
        return None
      parts.append(part_value)

  # If we reach here, all parts are resolved to strings, concatenates them
  # together and use that as the final value.
  return ''.join(parts)


def substitute_runtime_parameter(
    msg: message.Message,
    parameter_bindings: Mapping[str, types.Property]
    ) -> Mapping[str, types.Property]:
  """Utility function to substitute runtime parameter placeholders with values.

  Args:
    msg: The original message to change. Only messages defined under
      pipeline_pb2 will be supported. Other types will result in no-op.
    parameter_bindings: A dict of parameter keys to parameter values that will
      be used to substitute the runtime parameter placeholder.

  Returns:
    A dict of all runtime parameters to their populated values
  """
  if not isinstance(msg, message.Message):
    return {}

  parameters = {}
  # If the message is a pipeline_pb2.Value instance, try to find an substitute
  # with runtime parameter bindings.
  if isinstance(msg, pipeline_pb2.Value):
    value = cast(pipeline_pb2.Value, msg)
    which = value.WhichOneof('value')
    if which == 'runtime_parameter':
      real_value = _get_runtime_parameter_value(value.runtime_parameter,
                                                parameter_bindings)
      parameters[value.runtime_parameter.name] = real_value
      if real_value is None:
        return parameters
      value.Clear()
      data_types_utils.set_metadata_value(
          metadata_value=value.field_value, value=real_value)
    if which == 'structural_runtime_parameter':
      real_value = _get_structural_runtime_parameter_value(
          value.structural_runtime_parameter, parameter_bindings, parameters)
      if real_value is None:
        return parameters
      value.Clear()
      data_types_utils.set_metadata_value(
          metadata_value=value.field_value, value=real_value)

    return parameters

  # For other cases, recursively call into sub-messages if any.
  for field, sub_message in msg.ListFields():
    # No-op for non-message types.
    if field.type != descriptor.FieldDescriptor.TYPE_MESSAGE:
      continue
    # Evaluates every map values in a map.
    elif (field.message_type.has_options and
          field.message_type.GetOptions().map_entry):
      for key in sub_message:
        parameters.update(
            substitute_runtime_parameter(sub_message[key], parameter_bindings))
    # Evaluates every entry in a list.
    elif field.label == descriptor.FieldDescriptor.LABEL_REPEATED:
      for element in sub_message:
        parameters.update(
            substitute_runtime_parameter(element, parameter_bindings))
    # Evaluates sub-message.
    else:
      parameters.update(
          substitute_runtime_parameter(sub_message, parameter_bindings))
  return parameters
