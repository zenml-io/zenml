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
"""Minimal REST client for the Baseten Training API."""

from typing import Dict, Optional, cast

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from zenml.logger import get_logger

logger = get_logger(__name__)

BASETEN_API_BASE_URL = "https://api.baseten.co"
_REQUEST_TIMEOUT = 30


def _build_session() -> requests.Session:
    """Build a requests session that retries transient failures.

    Returns:
        A session with retries mounted for HTTPS requests.
    """
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


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
        self._session = _build_session()

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
            exists (HTTP 404). Raises ``requests.HTTPError`` if the request
            fails for any other reason.
        """
        response = self._session.get(
            self._job_url(project_id, job_id),
            headers=self._headers,
            timeout=_REQUEST_TIMEOUT,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        job = response.json().get("training_job", {})
        return cast(Optional[str], job.get("current_status"))

    def stop_job(self, project_id: str, job_id: str) -> None:
        """Stop a running training job.

        Raises ``requests.HTTPError`` if the stop request fails.

        Args:
            project_id: The Baseten training project id.
            job_id: The Baseten training job id.
        """
        response = self._session.post(
            f"{self._job_url(project_id, job_id)}/stop",
            headers=self._headers,
            json={},
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
