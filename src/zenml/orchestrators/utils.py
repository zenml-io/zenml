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

import json
from typing import TYPE_CHECKING, List, cast

import tfx.orchestration.pipeline as tfx_pipeline
from tfx.orchestration.portable import data_types
from tfx.proto.orchestration.pipeline_pb2 import PipelineNode

from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.steps import BaseStep
from zenml.steps.utils import (
    INTERNAL_EXECUTION_PARAMETER_PREFIX,
    PARAM_PIPELINE_PARAMETER_NAME,
)

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.stack import Stack

logger = get_logger(__name__)


def create_tfx_pipeline(
    zenml_pipeline: "BasePipeline", stack: "Stack"
) -> tfx_pipeline.Pipeline:
    """Creates a tfx pipeline from a ZenML pipeline."""
    # Connect the inputs/outputs of all steps in the pipeline
    zenml_pipeline.connect(**zenml_pipeline.steps)

    tfx_components = [step.component for step in zenml_pipeline.steps.values()]

    artifact_store = stack.artifact_store
    metadata_store = stack.metadata_store

    return tfx_pipeline.Pipeline(
        pipeline_name=zenml_pipeline.name,
        components=tfx_components,  # type: ignore[arg-type]
        pipeline_root=artifact_store.path,
        metadata_connection_config=metadata_store.get_tfx_metadata_config(),
        enable_cache=zenml_pipeline.enable_cache,
    )


def get_cache_status(
    execution_info: data_types.ExecutionInfo,
) -> bool:
    """Returns the caching status of a step.

    Args:
        execution_info: The execution info of a `tfx` step.

    Raises:
        AttributeError: If the execution info is `None`.
        KeyError: If no pipeline info is found in the `execution_info`.

    Returns:
        The caching status of a `tfx` step as a boolean value.
    """
    if execution_info is None:
        logger.warning("No execution info found when checking cache status.")
        return False

    status = False
    repository = Repository()
    # TODO [ENG-706]: Get the current running stack instead of just the active
    #   stack
    active_stack = repository.active_stack
    if not active_stack:
        raise RuntimeError(
            "No active stack is configured for the repository. Run "
            "`zenml stack set STACK_NAME` to update the active stack."
        )

    metadata_store = active_stack.metadata_store

    step_name_param = (
        INTERNAL_EXECUTION_PARAMETER_PREFIX + PARAM_PIPELINE_PARAMETER_NAME
    )
    step_name = json.loads(execution_info.exec_properties[step_name_param])
    if execution_info.pipeline_info:
        pipeline_name = execution_info.pipeline_info.id
    else:
        raise KeyError(f"No pipeline info found for step `{step_name}`.")
    pipeline_run_name = cast(str, execution_info.pipeline_run_id)
    pipeline = metadata_store.get_pipeline(pipeline_name)
    if pipeline is None:
        logger.error(f"Pipeline {pipeline_name} not found in Metadata Store.")
    else:
        status = (
            pipeline.get_run(pipeline_run_name).get_step(step_name).is_cached
        )
    return status


def get_step_for_node(node: PipelineNode, steps: List[BaseStep]) -> BaseStep:
    """Finds the matching step for a tfx pipeline node."""
    step_name = node.node_info.id
    try:
        return next(step for step in steps if step.name == step_name)
    except StopIteration:
        raise RuntimeError(f"Unable to find step with name '{step_name}'.")
