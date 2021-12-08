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
"""Main entrypoint for containers with Kubeflow TFX component executors."""

import argparse
import copy
import importlib
import json
import logging
import os
import sys
import textwrap
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
    cast,
)

from google.protobuf import json_format
from ml_metadata.proto import metadata_store_pb2
from tfx import types
from tfx.dsl.compiler import constants
from tfx.orchestration import metadata
from tfx.orchestration.local import runner_utils
from tfx.orchestration.portable import (
    data_types,
    execution_publish_utils,
    kubernetes_executor_operator,
    launcher,
    runtime_parameter_utils,
)
from tfx.proto.orchestration import executable_spec_pb2, pipeline_pb2
from tfx.types import artifact, channel, standard_artifacts

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.integrations.kubeflow import kubeflow_metadata_adapter
from zenml.integrations.registry import integration_registry
from zenml.steps.utils import generate_component_class

_KFP_POD_NAME_ENV_KEY = "KFP_POD_NAME"
_KFP_POD_NAME_PROPERTY_KEY = "kfp_pod_name"


def _register_execution(
    metadata_handler: metadata.Metadata,
    execution_type: metadata_store_pb2.ExecutionType,
    contexts: List[metadata_store_pb2.Context],
    input_artifacts: MutableMapping[str, Sequence[types.Artifact]],
    exec_properties: Mapping[str, types.Property],
) -> metadata_store_pb2.Execution:
    """Registers an execution in MLMD."""
    kfp_pod_name = os.environ.get(_KFP_POD_NAME_ENV_KEY)
    execution_properties_copy = copy.deepcopy(exec_properties)
    execution_properties_copy = cast(
        MutableMapping[str, types.Property], execution_properties_copy
    )
    if kfp_pod_name:
        logging.info("Adding KFP pod name %s to execution", kfp_pod_name)
        execution_properties_copy[_KFP_POD_NAME_PROPERTY_KEY] = kfp_pod_name
    return execution_publish_utils.register_execution(
        metadata_handler=metadata_handler,
        execution_type=execution_type,
        contexts=contexts,
        input_artifacts=input_artifacts,
        exec_properties=execution_properties_copy,
    )


def _get_grpc_metadata_connection_config(
    kubeflow_metadata_config: Dict[str, Any]
) -> metadata_store_pb2.MetadataStoreClientConfig:
    """Constructs a metadata grpc connection config.

    Args:
      kubeflow_metadata_config: Configuration parameters to use for constructing a
        valid metadata connection config in a Kubeflow cluster.

    Returns:
      A metadata_store_pb2.MetadataStoreClientConfig object.
    """
    grpc_config = kubeflow_metadata_config["grpc_config"]
    connection_config = metadata_store_pb2.MetadataStoreClientConfig()
    connection_config.host = os.getenv(
        grpc_config["grpc_service_host"]["environment_variable"]
    )
    connection_config.port = int(
        os.getenv(grpc_config["grpc_service_port"]["environment_variable"])
    )
    return connection_config


def _get_metadata_connection(
    connection_info: str,
) -> kubeflow_metadata_adapter.KubeflowMetadataAdapter:
    """Constructs a Kubeflow metadata adapter."""
    kubeflow_metadata_config = json.loads(connection_info)
    metadata_connection_config = _get_grpc_metadata_connection_config(
        kubeflow_metadata_config
    )
    return kubeflow_metadata_adapter.KubeflowMetadataAdapter(
        metadata_connection_config
    )


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


def _dump_ui_metadata(
    node: pipeline_pb2.PipelineNode,
    execution_info: data_types.ExecutionInfo,
    ui_metadata_path: str = "/mlpipeline-ui-metadata.json",
) -> None:
    """Dump KFP UI metadata json file for visualization purpose.

    For general components we just render a simple Markdown file for
      exec_properties/inputs/outputs.

    Args:
      node: associated TFX node.
      execution_info: runtime execution info for this component, including
        materialized inputs/outputs/execution properties and id.
      ui_metadata_path: path to dump ui metadata.
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
        node_inputs: MutableMapping[str, pipeline_pb2.InputSpec],
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
            # There must be at least a channel in a input, and all channels in a input
            # share the same artifact type.
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
        node_outputs: MutableMapping[str, pipeline_pb2.OutputSpec],
        name_to_artifacts: Dict[str, List[artifact.Artifact]],
    ) -> List[str]:
        """Dump artifacts markdown string for outputs.

        Args:
          node_outputs: maps from output name to output sepc proto.
          name_to_artifacts: maps from output key to list of populated artifacts.

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
            # There must be at least a channel in a input, and all channels in a input
            # share the same artifact type.
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
    # Add Tensorboard view for ModelRun outpus.
    for name, spec in node.outputs.outputs.items():
        if (
            spec.artifact_spec.type.name
            == standard_artifacts.ModelRun.TYPE_NAME
        ):
            output_model = execution_info.output_dict[name][0]

            # Add Tensorboard view.
            tensorboard_output = {
                "type": "tensorboard",
                "source": output_model.uri,
            }
            outputs.append(tensorboard_output)

    metadata_dict = {"outputs": outputs}

    with open(ui_metadata_path, "w") as f:
        json.dump(metadata_dict, f)


def _get_pipeline_node(pipeline: pipeline_pb2.Pipeline, node_id: str):
    """Gets node of a certain node_id from a pipeline."""
    result = None
    for node in pipeline.nodes:
        if (
            node.WhichOneof("node") == "pipeline_node"
            and node.pipeline_node.node_info.id == node_id
        ):
            result = node.pipeline_node
    if not result:
        logging.error("pipeline ir = %s\n", pipeline)
        raise RuntimeError(
            f"Cannot find node with id {node_id} in pipeline ir."
        )

    return result


def _parse_runtime_parameter_str(param: str) -> Tuple[str, types.Property]:
    """Parses runtime parameter string in command line argument."""
    # Runtime parameter format: "{name}=(INT|DOUBLE|STRING):{value}"
    name, value_and_type = param.split("=", 1)
    value_type, value = value_and_type.split(":", 1)
    if value_type == pipeline_pb2.RuntimeParameter.Type.Name(
        pipeline_pb2.RuntimeParameter.INT
    ):
        value = int(value)
    elif value_type == pipeline_pb2.RuntimeParameter.Type.Name(
        pipeline_pb2.RuntimeParameter.DOUBLE
    ):
        value = float(value)
    return (name, value)


def _resolve_runtime_parameters(
    tfx_ir: pipeline_pb2.Pipeline, parameters: Optional[List[str]]
) -> None:
    """Resolve runtime parameters in the pipeline proto inplace."""
    if parameters is None:
        return

    parameter_bindings = {
        # Substitute the runtime parameter to be a concrete run_id
        constants.PIPELINE_RUN_ID_PARAMETER_NAME: os.environ["WORKFLOW_ID"],
    }
    # Argo will fill runtime parameter values in the parameters.
    for param in parameters:
        name, value = _parse_runtime_parameter_str(param)
        parameter_bindings[name] = value

    runtime_parameter_utils.substitute_runtime_parameter(
        tfx_ir, parameter_bindings
    )


def _create_executor_class(
    step_source_module_name: str,
    step_function_name: str,
    executor_class_target_module_name: str,
) -> None:
    """Creates an executor class for a given step and adds it to the target
    module.

    Args:
        step_source_module_name: Name of the module in which the step function
            is defined.
        step_function_name: Name of the step function.
        executor_class_target_module_name: Name of the module to which the
            executor class should be added.
    """
    step_module = importlib.import_module(step_source_module_name)
    step_class = getattr(step_module, step_function_name)
    step_instance = step_class()

    # TODO [HIGH]: This needs to be refactored when our standard interface
    #  implementation is finished
    input_spec = {key: BaseArtifact for key in step_instance.INPUT_SIGNATURE}
    output_spec = {key: BaseArtifact for key in step_instance.OUTPUT_SIGNATURE}

    execution_parameters = {
        **step_instance.PARAM_SPEC,
        **step_instance._internal_execution_parameters,
    }

    materializers = step_instance.get_materializers(ensure_complete=True)

    generate_component_class(
        step_name=step_instance.step_name,
        step_module=executor_class_target_module_name,
        input_spec=input_spec,
        output_spec=output_spec,
        execution_parameter_names=set(execution_parameters),
        step_function=step_instance.process,
        materializers=materializers,
    )


def _parse_command_line_arguments() -> argparse.Namespace:
    """Parses the command line input arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline_root", type=str, required=True)
    parser.add_argument(
        "--metadata_ui_path",
        type=str,
        required=False,
        default="/mlpipeline-ui-metadata.json",
    )
    parser.add_argument("--kubeflow_metadata_config", type=str, required=True)
    parser.add_argument("--tfx_ir", type=str, required=True)
    parser.add_argument("--node_id", type=str, required=True)
    # There might be multiple runtime parameters.
    # `args.runtime_parameter` should become List[str] by using "append".
    parser.add_argument("--runtime_parameter", type=str, action="append")
    parser.add_argument("--step_module", type=str, required=True)
    parser.add_argument("--step_function_name", type=str, required=True)

    return parser.parse_args()


def main():
    """Runs a single step defined by the command line arguments."""
    # Log to the container's stdout so Kubeflow Pipelines UI can display logs to
    # the user.
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger().setLevel(logging.INFO)

    args = _parse_command_line_arguments()

    launcher._register_execution = _register_execution

    tfx_pipeline = pipeline_pb2.Pipeline()
    json_format.Parse(args.tfx_ir, tfx_pipeline)
    _resolve_runtime_parameters(tfx_pipeline, args.runtime_parameter)

    node_id = args.node_id
    pipeline_node = _get_pipeline_node(tfx_pipeline, node_id)

    metadata_connection = _get_metadata_connection(
        args.kubeflow_metadata_config
    )

    deployment_config = runner_utils.extract_local_deployment_config(
        tfx_pipeline
    )
    executor_spec = runner_utils.extract_executor_spec(
        deployment_config, node_id
    )
    custom_driver_spec = runner_utils.extract_custom_driver_spec(
        deployment_config, node_id
    )
    custom_executor_operators = {
        executable_spec_pb2.ContainerExecutableSpec: kubernetes_executor_operator.KubernetesExecutorOperator
    }

    # make sure all integrations are activated so all materializers etc. are
    # available
    integration_registry.activate_integrations()

    executor_module_parts = executor_spec.class_path.split(".")[:-1]
    executor_class_target_module_name = ".".join(executor_module_parts)
    _create_executor_class(
        step_source_module_name=args.step_module,
        step_function_name=args.step_function_name,
        executor_class_target_module_name=executor_class_target_module_name,
    )

    component_launcher = launcher.Launcher(
        pipeline_node=pipeline_node,
        mlmd_connection=metadata_connection,
        pipeline_info=tfx_pipeline.pipeline_info,
        pipeline_runtime_spec=tfx_pipeline.runtime_spec,
        executor_spec=executor_spec,
        custom_driver_spec=custom_driver_spec,
        custom_executor_operators=custom_executor_operators,
    )
    logging.info("Component %s is running.", node_id)
    execution_info = component_launcher.launch()
    logging.info("Component %s is finished.", node_id)

    # Dump the UI metadata.
    _dump_ui_metadata(pipeline_node, execution_info, args.metadata_ui_path)


if __name__ == "__main__":
    main()
