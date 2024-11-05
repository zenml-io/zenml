#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Utility functions to run ZenML pipelines."""

import contextlib
from typing import Dict, Optional, Union
from uuid import UUID

from zenml.client import Client
from zenml.enums import MetadataResourceTypes
from zenml.metadata.metadata_types import MetadataType
from zenml.steps.step_context import get_step_context


def log_metadata(
    metadata: Dict[str, MetadataType],
    run_name_id_or_prefix: Optional[Union[str, UUID]] = None,
) -> None:
    """Logs metadata.

    Args:
        metadata: The metadata to log.
        run_name_id_or_prefix: The name, ID or prefix of the run to log metadata
            for. Can be omitted when being called inside a step.

    Raises:
        ValueError: If no run identifier is provided and the function is not
            called from within a step.
    """
    step_context = None
    if not run_name_id_or_prefix:
        with contextlib.suppress(RuntimeError):
            step_context = get_step_context()
            run_name_id_or_prefix = step_context.pipeline_run.id

    if not run_name_id_or_prefix:
        raise ValueError(
            "No pipeline name or ID provided and you are not running "
            "within a step. Please provide a pipeline name or ID, or "
            "provide a run ID."
        )

    client = Client()
    if step_context is None and not isinstance(run_name_id_or_prefix, UUID):
        run_name_id_or_prefix = client.get_pipeline_run(
            name_id_or_prefix=run_name_id_or_prefix,
        ).id

    # TODO: Should we also create the corresponding step and model metadata
    #  as well?
    client.create_run_metadata(
        metadata=metadata,
        resource_id=run_name_id_or_prefix,
        resource_type=MetadataResourceTypes.PIPELINE_RUN,
    )
