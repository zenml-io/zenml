#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Utility functions for interacting with TFX contexts."""
import hashlib
import json
from typing import TYPE_CHECKING, Dict

from pydantic.json import pydantic_encoder
from tfx.proto.orchestration import pipeline_pb2

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import Step

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.stack import Stack


ZENML_MLMD_CONTEXT_TYPE = "zenml"
MLMD_CONTEXT_STACK_PROPERTY_NAME = "stack"
MLMD_CONTEXT_PIPELINE_CONFIG_PROPERTY_NAME = "pipeline_configuration"
MLMD_CONTEXT_STEP_CONFIG_PROPERTY_NAME = "step_configuration"
MLMD_CONTEXT_MODEL_IDS_PROPERTY_NAME = "model_ids"
MLMD_CONTEXT_NUM_STEPS_PROPERTY_NAME = "num_steps"


def add_pipeline_node_context(
    pipeline_node: pipeline_pb2.PipelineNode,
    type_: str,
    name: str,
    properties: Dict[str, str],
) -> None:
    """Adds a new context to a TFX protobuf pipeline node.

    Args:
        pipeline_node: A tfx protobuf pipeline node
        type_: The type name for the context to be added
        name: Unique key for the context
        properties: dictionary of strings as properties of the context
    """
    context: pipeline_pb2.ContextSpec = pipeline_node.contexts.contexts.add()
    context.type.name = type_
    context.name.field_value.string_value = name
    for key, value in properties.items():
        c_property = context.properties[key]
        c_property.field_value.string_value = value


def add_mlmd_contexts(
    pipeline_node: pipeline_pb2.PipelineNode,
    step: "Step",
    deployment: "PipelineDeployment",
    stack: "Stack",
) -> None:
    """Adds context to each pipeline node of a pb2_pipeline.

    Args:
        pipeline_node: The pipeline node to which the contexts should be
            added.
        step: The corresponding step for the pipeline node.
        deployment: The pipeline deployment to store in the contexts.
        stack: The stack the pipeline will run on.
    """
    from zenml.client import Client

    client = Client()

    model_ids = json.dumps(
        {
            "user_id": client.active_user.id,
            "project_id": client.active_project.id,
            "pipeline_id": deployment.pipeline_id,
            "stack_id": deployment.stack_id,
        },
        sort_keys=True,
        default=pydantic_encoder,
    )

    stack_json = json.dumps(stack.dict(), sort_keys=True)
    pipeline_config = deployment.pipeline.json(sort_keys=True)
    step_config = step.json(sort_keys=True)

    context_properties = {
        MLMD_CONTEXT_STACK_PROPERTY_NAME: stack_json,
        MLMD_CONTEXT_PIPELINE_CONFIG_PROPERTY_NAME: pipeline_config,
        MLMD_CONTEXT_STEP_CONFIG_PROPERTY_NAME: step_config,
        MLMD_CONTEXT_MODEL_IDS_PROPERTY_NAME: model_ids,
        MLMD_CONTEXT_NUM_STEPS_PROPERTY_NAME: str(len(deployment.steps)),
    }

    properties_json = json.dumps(context_properties, sort_keys=True)
    context_name = hashlib.md5(properties_json.encode()).hexdigest()

    add_pipeline_node_context(
        pipeline_node,
        type_=ZENML_MLMD_CONTEXT_TYPE,
        name=context_name,
        properties=context_properties,
    )


def get_step(
    pipeline_node: pipeline_pb2.PipelineNode,
) -> "Step":
    """Fetches the step from a PipelineNode context.

    Args:
        pipeline_node: Pipeline node info for a step.

    Returns:
        The step.

    Raises:
        RuntimeError: If no step was found.
    """
    for context in pipeline_node.contexts.contexts:
        if context.type.name == ZENML_MLMD_CONTEXT_TYPE:
            config_json = context.properties[
                MLMD_CONTEXT_STEP_CONFIG_PROPERTY_NAME
            ].field_value.string_value

            return Step.parse_raw(config_json)

    raise RuntimeError("Unable to find step.")


def get_pipeline_config(
    pipeline_node: pipeline_pb2.PipelineNode,
) -> "PipelineConfiguration":
    """Fetches the pipeline configuration from a PipelineNode context.

    Args:
        pipeline_node: Pipeline node info for a step.

    Returns:
        The pipeline config.

    Raises:
        RuntimeError: If no pipeline config was found.
    """
    for context in pipeline_node.contexts.contexts:
        if context.type.name == ZENML_MLMD_CONTEXT_TYPE:
            config_json = context.properties[
                MLMD_CONTEXT_PIPELINE_CONFIG_PROPERTY_NAME
            ].field_value.string_value

            return PipelineConfiguration.parse_raw(config_json)

    raise RuntimeError("Unable to find pipeline config.")
