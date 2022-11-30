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
"""Utility class to help with interacting with the dashboard."""

from typing import Optional
from uuid import UUID

from zenml.client import Client
from zenml.enums import StoreType
from zenml.logger import get_logger

logger = get_logger(__name__)


def get_run_url(
    run_name: str, pipeline_id: Optional[UUID] = None
) -> Optional[str]:
    """Computes a dashboard url to directly view the run.

    Args:
        run_name: Name of the pipeline run.
        pipeline_id: Optional pipeline_id, to be sent when available.

    Returns:
        A direct url link to the pipeline run details page. If run does not exist,
        returns None.
    """
    # Connected to ZenML Server
    client = Client()

    if client.zen_store.type != StoreType.REST:
        return ""

    url = client.zen_store.url
    runs = client.zen_store.list_runs(name=run_name)

    if pipeline_id:
        url += f"/pipelines/{str(pipeline_id)}/runs"
    elif runs:
        url += "/runs"
    else:
        url += "/pipelines/all-runs"

    if runs:
        url += f"/{runs[0].id}/dag"

    return url


def print_run_url(run_name: str, pipeline_id: Optional[UUID] = None) -> None:
    """Logs a dashboard url to directly view the run.

    Args:
        run_name: Name of the pipeline run.
        pipeline_id: Optional pipeline_id, to be sent when available.
    """
    client = Client()

    if client.zen_store.type == StoreType.REST:
        url = get_run_url(
            run_name,
            pipeline_id,
        )
        if url:
            logger.info(f"Dashboard URL: {url}")
    elif client.zen_store.type == StoreType.SQL:
        # Connected to SQL Store Type, we're local
        logger.info(
            "Pipeline visualization can be seen in the ZenML Dashboard. "
            "Run `zenml up` to see your pipeline!"
        )
