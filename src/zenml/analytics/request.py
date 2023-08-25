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

from zenml.analytics.utils import AnalyticsAPIError
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
    from zenml.analytics import source_context

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        source_context.name: source_context.get().value,
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
