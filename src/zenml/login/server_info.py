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
"""ZenML server information retrieval."""

from typing import Optional

from zenml.logger import get_logger
from zenml.models import ServerModel
from zenml.zen_stores.rest_zen_store import (
    RestZenStore,
    RestZenStoreConfiguration,
)

logger = get_logger(__name__)


def get_server_info(url: str) -> Optional[ServerModel]:
    """Retrieve server information from a remote ZenML server.

    Args:
        url: The URL of the ZenML server.

    Returns:
        The server information or None if the server info could not be fetched.
    """
    # Here we try to leverage the existing RestZenStore support to fetch the
    # server info and only the server info, which doesn't actually need
    # any authentication.
    try:
        store = RestZenStore(
            config=RestZenStoreConfiguration(
                url=url,
            )
        )
        return store.server_info
    except Exception as e:
        logger.warning(
            f"Failed to fetch server info from the server running at {url}: {e}"
        )

    return None
