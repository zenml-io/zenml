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

import time
from typing import TYPE_CHECKING, Optional

import tfx.orchestration.pipeline as tfx_pipeline
from tfx.orchestration.portable import data_types, launcher

from zenml.exceptions import DuplicateRunNameError
from zenml.logger import get_logger
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline

logger = get_logger(__name__)


def create_tfx_pipeline(
    zenml_pipeline: "BasePipeline",
) -> tfx_pipeline.Pipeline:
    """Creates a tfx pipeline from a ZenML pipeline."""
    # Connect the inputs/outputs of all steps in the pipeline
    zenml_pipeline.connect(**zenml_pipeline.steps)

    tfx_components = [step.component for step in zenml_pipeline.steps.values()]

    artifact_store = zenml_pipeline.stack.artifact_store
    metadata_store = zenml_pipeline.stack.metadata_store

    return tfx_pipeline.Pipeline(
        pipeline_name=zenml_pipeline.name,
        components=tfx_components,  # type: ignore[arg-type]
        pipeline_root=artifact_store.path,
        metadata_connection_config=metadata_store.get_tfx_metadata_config(),
        enable_cache=zenml_pipeline.enable_cache,
    )


def execute_step(
    tfx_launcher: launcher.Launcher,
) -> Optional[data_types.ExecutionInfo]:
    """Executes a tfx component.

    Args:
        tfx_launcher: A tfx launcher to execute the component.

    Returns:
        Optional execution info returned by the launcher.
    """
    step_name = tfx_launcher._pipeline_node.node_info.id  # type: ignore[attr-defined] # noqa
    start_time = time.time()
    logger.info(f"Step `{step_name}` has started.")
    try:
        execution_info = tfx_launcher.launch()
    except RuntimeError as e:
        if "execution has already succeeded" in str(e):
            # Hacky workaround to catch the error that a pipeline run with
            # this name already exists. Raise an error with a more descriptive
            # message instead.
            raise DuplicateRunNameError()
        else:
            raise

    run_duration = time.time() - start_time
    logger.info(
        "Step `%s` has finished in %s.",
        step_name,
        string_utils.get_human_readable_time(run_duration),
    )
    return execution_info
