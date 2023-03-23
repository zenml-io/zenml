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
"""The 'analytics' module of ZenML.

This module is based on the 'analytics-python' package created by Segment.
The base functionalities are adapted to work with the ZenML analytics server.
"""

import logging
from typing import List

import requests

from zenml.constants import ANALYTICS_SERVER_URL

logger = logging.getLogger(__name__)


def post(batch: List[str], timeout: int = 15) -> requests.Response:
    """Post a batch of messages to the ZenML analytics server.

    Args:
        batch: The messages to send.
        timeout: Timeout in seconds.

    Returns:
        The response.

    Raises:
        AnalyticsAPIError: If the post request has failed.
    """
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
    }
    response = requests.post(
        url=ANALYTICS_SERVER_URL + "/batch",
        headers=headers,
        data=f"[{','.join(batch)}]",
        timeout=timeout,
    )

    if response.status_code == 200:
        logger.debug("data uploaded successfully")
        return response

    raise AnalyticsAPIError(response.status_code, response.text)


class AnalyticsAPIError(Exception):
    """Custom exception class for API-related errors."""

    def __init__(self, status: int, message: str) -> None:
        """Initialization.

        Args:
            status: The status code of the response.
            message: The text of the response.
        """
        self.message = message
        self.status = status

    def __str__(self) -> str:
        """Method to represent the instance as a string.

        Returns:
            A representation of the message and the status code.
        """
        msg = "[ZenML Analytics] {1}: {0}"
        return msg.format(self.message, self.status)
