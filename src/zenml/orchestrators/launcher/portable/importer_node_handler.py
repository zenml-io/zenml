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
"""This module defines the handler for importer node."""

from typing import Any, Dict, List

from absl import logging
from tfx import types
from tfx.dsl.components.common import importer
from tfx.orchestration import data_types_utils
from tfx.orchestration import metadata
from tfx.orchestration.portable import data_types
from tfx.orchestration.portable import execution_publish_utils
from tfx.orchestration.portable import inputs_utils
from tfx.orchestration.portable import outputs_utils
from tfx.orchestration.portable import system_node_handler
from tfx.orchestration.portable.mlmd import context_lib
from tfx.proto.orchestration import pipeline_pb2


def _is_artifact_reimported(
    output_artifacts: Dict[str, List[types.Artifact]]) -> bool:
  # The artifacts are reimported only when there are artifacts in the output
  # dict and ids has been assign to them.
  return (bool(output_artifacts[importer.IMPORT_RESULT_KEY]) and all(
      (bool(a.id) for a in output_artifacts[importer.IMPORT_RESULT_KEY])))


class ImporterNodeHandler(system_node_handler.SystemNodeHandler):
  """The handler for the system Importer node."""

  def _extract_proto_map(
      self,
      # The actual type of proto message of map<str, pipeline_pb2.Value>.
      proto_map: Any
  ) -> Dict[str, Any]:
    extract_mlmd_value = lambda v: getattr(v, v.WhichOneof('value'))
    return {k: extract_mlmd_value(v.field_value) for k, v in proto_map.items()}

  def run(
      self, mlmd_connection: metadata.Metadata,
      pipeline_node: pipeline_pb2.PipelineNode,
      pipeline_info: pipeline_pb2.PipelineInfo,
      pipeline_runtime_spec: pipeline_pb2.PipelineRuntimeSpec
  ) -> data_types.ExecutionInfo:
    """Runs Importer specific logic.

    Args:
      mlmd_connection: ML metadata connection.
      pipeline_node: The specification of the node that this launcher lauches.
      pipeline_info: The information of the pipeline that this node runs in.
      pipeline_runtime_spec: The runtime information of the pipeline that this
        node runs in.

    Returns:
      The execution of the run.
    """
    logging.info('Running as an importer node.')
    with mlmd_connection as m:
      # 1.Prepares all contexts.
      contexts = context_lib.prepare_contexts(
          metadata_handler=m, node_contexts=pipeline_node.contexts)

      # 2. Resolves execution properties, please note that importers has no
      # input.
      exec_properties = data_types_utils.build_parsed_value_dict(
          inputs_utils.resolve_parameters_with_schema(
              node_parameters=pipeline_node.parameters))

      # 3. Registers execution in metadata.
      execution = execution_publish_utils.register_execution(
          metadata_handler=m,
          execution_type=pipeline_node.node_info.type,
          contexts=contexts,
          exec_properties=exec_properties)

      # 4. Generate output artifacts to represent the imported artifacts.
      output_spec = pipeline_node.outputs.outputs[importer.IMPORT_RESULT_KEY]
      properties = self._extract_proto_map(
          output_spec.artifact_spec.additional_properties)
      custom_properties = self._extract_proto_map(
          output_spec.artifact_spec.additional_custom_properties)
      output_artifact_class = types.Artifact(
          output_spec.artifact_spec.type).type
      output_artifacts = importer.generate_output_dict(
          metadata_handler=m,
          uri=str(exec_properties[importer.SOURCE_URI_KEY]),
          properties=properties,
          custom_properties=custom_properties,
          reimport=bool(exec_properties[importer.REIMPORT_OPTION_KEY]),
          output_artifact_class=output_artifact_class,
          mlmd_artifact_type=output_spec.artifact_spec.type)

      result = data_types.ExecutionInfo(
          execution_id=execution.id,
          input_dict={},
          output_dict=output_artifacts,
          exec_properties=exec_properties,
          pipeline_node=pipeline_node,
          pipeline_info=pipeline_info)

      # TODO(b/182316162): consider let the launcher level do the publish
      # for system nodes. So that the version taging logic doesn't need to be
      # handled per system node.
      outputs_utils.tag_output_artifacts_with_version(result.output_dict)

      # 5. Publish the output artifacts. If artifacts are reimported, the
      # execution is published as CACHED. Otherwise it is published as COMPLETE.
      if _is_artifact_reimported(output_artifacts):
        execution_publish_utils.publish_cached_execution(
            metadata_handler=m,
            contexts=contexts,
            execution_id=execution.id,
            output_artifacts=output_artifacts)

      else:
        execution_publish_utils.publish_succeeded_execution(
            metadata_handler=m,
            execution_id=execution.id,
            contexts=contexts,
            output_artifacts=output_artifacts)

      return result
