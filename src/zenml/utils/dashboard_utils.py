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

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration


def get_run_url(run_name: str, pipeline_id: Optional[str] = None) -> str:
    """Computes a dashboard url to directly view the run.

    Args:
        run_name: Name of the pipeline run.
        pipeline_id: Optional pipeline_id, to be sent when available.

    Returns:
        A direct url link to the pipeline run details page.
    """
    gc = GlobalConfiguration()

    # Connected to ZenML Server
    client = Client()

    # Get the runs from the zen_store
    runs = client.zen_store.list_runs(run_name=run_name)

    # We should only do the log if runs exist
    if runs:
        # For now, take the first index to get the latest run
        run = runs[0]
        url = gc.store.url
        # Add this for unlisted runs
        if pipeline_id:
            url += f"/pipelines/{pipeline_id}"
        url += f"/runs/{run.id}/dag"
