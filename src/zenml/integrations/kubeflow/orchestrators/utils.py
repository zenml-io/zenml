# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

# This file is copied in large parts from the tfx kubeflow entrypoint.

import json
import os
import textwrap
from typing import Callable, Dict, List, MutableMapping, Optional

from kfp import dsl
from kubernetes import client as k8s_client
from tfx.orchestration.portable import data_types
from tfx.proto.orchestration.pipeline_pb2 import (
    InputSpec,
    OutputSpec,
    PipelineNode,
)
from tfx.types import artifact, channel, standard_artifacts

from zenml.artifact_stores import LocalArtifactStore
from zenml.artifacts.model_artifact import ModelArtifact
from zenml.repository import Repository


def mount_config_map_op(
    config_map_name: str,
) -> Callable[[dsl.ContainerOp], None]:
    """Mounts all key-value pairs found in the named Kubernetes ConfigMap.
    All key-value pairs in the ConfigMap are mounted as environment variables.
    Args:
      config_map_name: The name of the ConfigMap resource.
    Returns:
      An OpFunc for mounting the ConfigMap.
    """

    def mount_config_map(container_op: dsl.ContainerOp) -> None:
        """Mounts all key-value pairs found in the Kubernetes ConfigMap."""
        config_map_ref = k8s_client.V1ConfigMapEnvSource(
            name=config_map_name, optional=True
        )
        container_op.container.add_env_from(
            k8s_client.V1EnvFromSource(config_map_ref=config_map_ref)
        )

    return mount_config_map


def _sanitize_underscore(name: str) -> Optional[str]:
    """Sanitize the underscore in pythonic name for markdown visualization."""
    if name:
        return str(name).replace("_", "\\_")
    else:
        return None


def _render_channel_as_mdstr(input_channel: channel.Channel) -> str:
    """Render a Channel as markdown string with the following format.

    **Type**: input_channel.type_name
    **Artifact: artifact1**
    **Properties**:
    **key1**: value1
    **key2**: value2
    ......

    Args:
      input_channel: the channel to be rendered.

    Returns:
      a md-formatted string representation of the channel.
    """

    md_str = "**Type**: {}\n\n".format(
        _sanitize_underscore(input_channel.type_name)
    )
    rendered_artifacts = []
    # List all artifacts in the channel.
    for single_artifact in input_channel.get():
        rendered_artifacts.append(_render_artifact_as_mdstr(single_artifact))

    return md_str + "\n\n".join(rendered_artifacts)


# TODO(b/147097443): clean up and consolidate rendering code.
def _render_artifact_as_mdstr(single_artifact: artifact.Artifact) -> str:
    """Render an artifact as markdown string with the following format.

    **Artifact: artifact1**
    **Properties**:
    **key1**: value1
    **key2**: value2
    ......

    Args:
      single_artifact: the artifact to be rendered.

    Returns:
      a md-formatted string representation of the artifact.
    """
    span_str = "None"
    split_names_str = "None"
    if single_artifact.PROPERTIES:
        if "span" in single_artifact.PROPERTIES:
            span_str = str(single_artifact.span)
        if "split_names" in single_artifact.PROPERTIES:
            split_names_str = str(single_artifact.split_names)
    return textwrap.dedent(
        """\
      **Artifact: {name}**

      **Properties**:

      **uri**: {uri}

      **id**: {id}

      **span**: {span}

      **type_id**: {type_id}

      **type_name**: {type_name}

      **state**: {state}

      **split_names**: {split_names}

      **producer_component**: {producer_component}

      """.format(
            name=_sanitize_underscore(single_artifact.name) or "None",
            uri=_sanitize_underscore(single_artifact.uri) or "None",
            id=str(single_artifact.id),
            span=_sanitize_underscore(span_str),
            type_id=str(single_artifact.type_id),
            type_name=_sanitize_underscore(single_artifact.type_name),
            state=_sanitize_underscore(single_artifact.state) or "None",
            split_names=_sanitize_underscore(split_names_str),
            producer_component=_sanitize_underscore(
                single_artifact.producer_component
            )
            or "None",
        )
    )


def dump_ui_metadata(
    node: PipelineNode,
    execution_info: data_types.ExecutionInfo,
    metadata_ui_path: str,
) -> None:
    """Dump KFP UI metadata json file for visualization purpose.

    For general components we just render a simple Markdown file for
      exec_properties/inputs/outputs.

    Args:
      node: associated TFX node.
      execution_info: runtime execution info for this component, including
        materialized inputs/outputs/execution properties and id.
      metadata_ui_path: path to dump ui metadata.
    """
    exec_properties_list = [
        "**{}**: {}".format(
            _sanitize_underscore(name), _sanitize_underscore(exec_property)
        )
        for name, exec_property in execution_info.exec_properties.items()
    ]
    src_str_exec_properties = "# Execution properties:\n{}".format(
        "\n\n".join(exec_properties_list) or "No execution property."
    )

    def _dump_input_populated_artifacts(
        node_inputs: MutableMapping[str, InputSpec],
        name_to_artifacts: Dict[str, List[artifact.Artifact]],
    ) -> List[str]:
        """Dump artifacts markdown string for inputs.

        Args:
          node_inputs: maps from input name to input sepc proto.
          name_to_artifacts: maps from input key to list of populated artifacts.

        Returns:
          A list of dumped markdown string, each of which represents a channel.
        """
        rendered_list = []
        for name, spec in node_inputs.items():
            # Need to look for materialized artifacts in the execution decision.
            rendered_artifacts = "".join(
                [
                    _render_artifact_as_mdstr(single_artifact)
                    for single_artifact in name_to_artifacts.get(name, [])
                ]
            )
            # There must be at least a channel in a input, and all channels in
            # a input share the same artifact type.
            artifact_type = spec.channels[0].artifact_query.type.name
            rendered_list.append(
                "## {name}\n\n**Type**: {channel_type}\n\n{artifacts}".format(
                    name=_sanitize_underscore(name),
                    channel_type=_sanitize_underscore(artifact_type),
                    artifacts=rendered_artifacts,
                )
            )

        return rendered_list

    def _dump_output_populated_artifacts(
        node_outputs: MutableMapping[str, OutputSpec],
        name_to_artifacts: Dict[str, List[artifact.Artifact]],
    ) -> List[str]:
        """Dump artifacts markdown string for outputs.

        Args:
          node_outputs: maps from output name to output sepc proto.
          name_to_artifacts: maps from output key to list of populated
          artifacts.

        Returns:
          A list of dumped markdown string, each of which represents a channel.
        """
        rendered_list = []
        for name, spec in node_outputs.items():
            # Need to look for materialized artifacts in the execution decision.
            rendered_artifacts = "".join(
                [
                    _render_artifact_as_mdstr(single_artifact)
                    for single_artifact in name_to_artifacts.get(name, [])
                ]
            )
            # There must be at least a channel in a input, and all channels
            # in a input share the same artifact type.
            artifact_type = spec.artifact_spec.type.name
            rendered_list.append(
                "## {name}\n\n**Type**: {channel_type}\n\n{artifacts}".format(
                    name=_sanitize_underscore(name),
                    channel_type=_sanitize_underscore(artifact_type),
                    artifacts=rendered_artifacts,
                )
            )

        return rendered_list

    src_str_inputs = "# Inputs:\n{}".format(
        "".join(
            _dump_input_populated_artifacts(
                node_inputs=node.inputs.inputs,
                name_to_artifacts=execution_info.input_dict or {},
            )
        )
        or "No input."
    )

    src_str_outputs = "# Outputs:\n{}".format(
        "".join(
            _dump_output_populated_artifacts(
                node_outputs=node.outputs.outputs,
                name_to_artifacts=execution_info.output_dict or {},
            )
        )
        or "No output."
    )

    outputs = [
        {
            "storage": "inline",
            "source": "{exec_properties}\n\n{inputs}\n\n{outputs}".format(
                exec_properties=src_str_exec_properties,
                inputs=src_str_inputs,
                outputs=src_str_outputs,
            ),
            "type": "markdown",
        }
    ]
    # Add Tensorboard view for ModelRun outputs.
    for name, spec in node.outputs.outputs.items():
        if (
            spec.artifact_spec.type.name
            == standard_artifacts.ModelRun.TYPE_NAME
            or spec.artifact_spec.type.name == ModelArtifact.TYPE_NAME
        ):
            output_model = execution_info.output_dict[name][0]
            source = output_model.uri

            # For local artifact repository, use a path that is relative to
            # the point where the local artifact folder is mounted as a volume
            artifact_store = Repository().active_stack.artifact_store
            if isinstance(artifact_store, LocalArtifactStore):
                source = os.path.relpath(source, artifact_store.path)
                source = f"volume://local-artifact-store/{source}"
            # Add Tensorboard view.
            tensorboard_output = {
                "type": "tensorboard",
                "source": source,
            }
            outputs.append(tensorboard_output)

    metadata_dict = {"outputs": outputs}

    with open(metadata_ui_path, "w") as f:
        json.dump(metadata_dict, f)
