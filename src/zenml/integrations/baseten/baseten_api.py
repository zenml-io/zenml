#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Minimal REST client for the Baseten Training API.

Job status and cancellation use the Baseten Training REST API directly rather
than shelling out to the ``truss`` CLI. Endpoints are scoped by training
project, so both the project id and the job id are required.
"""

from typing import Dict, Optional, cast

import requests

from zenml.logger import get_logger

logger = get_logger(__name__)

BASETEN_API_BASE_URL = "https://api.baseten.co"
_REQUEST_TIMEOUT = 30


class BasetenApiClient:
    """Thin client for the Baseten Training REST API."""

    def __init__(
        self, api_key: str, base_url: str = BASETEN_API_BASE_URL
    ) -> None:
        """Initialize the client.

        Args:
            api_key: Baseten API key used for authentication.
            base_url: Base URL of the Baseten API.
        """
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    @property
    def _headers(self) -> Dict[str, str]:
        """Authorization headers for Baseten API requests.

        Returns:
            The request headers.
        """
        return {"Authorization": f"Api-Key {self._api_key}"}

    def _job_url(self, project_id: str, job_id: str) -> str:
        """Build the URL for a training job.

        Args:
            project_id: The Baseten training project id.
            job_id: The Baseten training job id.

        Returns:
            The training job URL.
        """
        return (
            f"{self._base_url}/v1/training_projects/{project_id}/jobs/{job_id}"
        )

    def get_job_status(self, project_id: str, job_id: str) -> Optional[str]:
        """Get the current status of a training job.

        Args:
            project_id: The Baseten training project id.
            job_id: The Baseten training job id.

        Returns:
            The Baseten job status string, or None if the job no longer
            exists (HTTP 404).

        Raises:
            HTTPError: If the request fails for a reason other than 404.
        """
        response = requests.get(
            self._job_url(project_id, job_id),
            headers=self._headers,
            timeout=_REQUEST_TIMEOUT,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        # The response uses `current_status`; fall back to `status` defensively.
        state = data.get("current_status") or data.get("status")
        return cast(Optional[str], state)

    def stop_job(self, project_id: str, job_id: str) -> None:
        """Stop a running training job.

        Args:
            project_id: The Baseten training project id.
            job_id: The Baseten training job id.

        Raises:
            HTTPError: If the stop request fails.
        """
        response = requests.post(
            f"{self._job_url(project_id, job_id)}/stop",
            headers=self._headers,
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
