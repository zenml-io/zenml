#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Implementation of the post-execution pipeline."""

from typing import List, Optional

from zenml.client import Client
from zenml.logger import get_logger
from zenml.models import PipelineResponse

logger = get_logger(__name__)


def get_pipelines() -> List["PipelineResponse"]:
    """(Deprecated) Fetches all pipelines in the active workspace.

    Returns:
        A list of pipeline models.
    """
    logger.warning(
        "`zenml.post_execution.get_pipelines()` is deprecated and will be "
        "removed in a future release. Please use "
        "`zenml.client.Client().list_pipelines()` instead."
    )
    return Client().list_pipelines().items


def get_pipeline(
    pipeline: str,
    version: Optional[str] = None,
) -> Optional["PipelineResponse"]:
    """(Deprecated) Fetches a pipeline model.

    Args:
        pipeline: The name of the pipeline.
        version: Optional pipeline version. Specifies the version of the
            pipeline to return. If not given, returns the latest version.

    Returns:
        The pipeline model.
    """
    logger.warning(
        "`zenml.post_execution.get_pipeline()` is deprecated and will be "
        "removed in a future release. Please use "
        "`zenml.client.Client().get_pipeline()` instead."
    )
    return Client().get_pipeline(name_id_or_prefix=pipeline, version=version)
