#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Utility functions for the orchestrator."""

from typing import TYPE_CHECKING, Dict, List, Optional

import tfx.orchestration.pipeline as tfx_pipeline
from tfx.orchestration.portable import data_types
from tfx.proto.orchestration.pipeline_pb2 import ContextSpec, PipelineNode

from zenml.logger import get_logger
from zenml.steps import BaseStep

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.stack import Stack


logger = get_logger(__name__)


def create_tfx_pipeline(
    zenml_pipeline: "BasePipeline", stack: "Stack"
) -> tfx_pipeline.Pipeline:
    """Creates a tfx pipeline from a ZenML pipeline.

    Args:
        zenml_pipeline: The ZenML pipeline.
        stack: The stack.

    Returns:
        The tfx pipeline.
    """
    # Connect the inputs/outputs of all steps in the pipeline
    zenml_pipeline.connect(**zenml_pipeline.steps)

    tfx_components = [step.component for step in zenml_pipeline.steps.values()]

    artifact_store = stack.artifact_store

    # We do not pass the metadata connection config here as it might not be
    # accessible. Instead it is queried from the active stack right before a
    # step is executed (see `BaseOrchestrator.run_step(...)`)
    return tfx_pipeline.Pipeline(
        pipeline_name=zenml_pipeline.name,
        components=tfx_components,  # type: ignore[arg-type]
        pipeline_root=artifact_store.path,
        enable_cache=zenml_pipeline.enable_cache,
    )


def get_step_for_node(node: PipelineNode, steps: List[BaseStep]) -> BaseStep:
    """Finds the matching step for a tfx pipeline node.

    Args:
        node: The tfx pipeline node.
        steps: The list of steps.

    Returns:
        The matching step.

    Raises:
        RuntimeError: If no matching step is found.
    """
    step_name = node.node_info.id
    try:
        return next(step for step in steps if step.name == step_name)
    except StopIteration:
        raise RuntimeError(f"Unable to find step with name '{step_name}'.")


def get_cache_status(
    execution_info: Optional[data_types.ExecutionInfo],
) -> bool:
    """Returns whether a cached execution was used or not.

    Args:
        execution_info: The execution info.

    Returns:
        `True` if the execution was cached, `False` otherwise.
    """
    # An execution output URI is only provided if the step needs to be
    # executed (= is not cached)
    if execution_info and execution_info.execution_output_uri is None:
        return True
    else:
        return False


def add_context_to_node(
    pipeline_node: PipelineNode,
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
    # Add a new context to the pipeline
    context: ContextSpec = pipeline_node.contexts.contexts.add()
    # Adding the type of context
    context.type.name = type_
    # Setting the name of the context
    context.name.field_value.string_value = name
    # Setting the properties of the context depending on attribute type
    for key, value in properties.items():
        c_property = context.properties[key]
        c_property.field_value.string_value = value
