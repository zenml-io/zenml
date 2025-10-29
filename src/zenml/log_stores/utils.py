#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Utility functions for working with log stores."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from zenml.logging.step_logging import LogEntry
    from zenml.models import LogsResponse
    from zenml.zen_stores.base_zen_store import BaseZenStore


def fetch_logs(
    logs: "LogsResponse",
    zen_store: "BaseZenStore",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 20000,
) -> List["LogEntry"]:
    """Fetch logs using the appropriate log store.

    This function determines which log store to use based on the log_store_id
    in the logs record. If log_store_id is present, it loads that log store.
    Otherwise, it falls back to DefaultLogStore.

    Args:
        logs: The logs model containing metadata and log_store_id.
        zen_store: The zen store to fetch log store component from.
        start_time: Filter logs after this time.
        end_time: Filter logs before this time.
        limit: Maximum number of log entries to return.

    Returns:
        List of log entries.
    """
    from zenml.enums import StackComponentType
    from zenml.stack import StackComponent

    if logs.log_store_id:
        log_store_model = zen_store.get_stack_component(logs.log_store_id)
        log_store = StackComponent.from_model(log_store_model)
    else:
        from zenml.log_stores.default_log_store import (
            DefaultLogStore,
            DefaultLogStoreConfig,
        )
        from zenml.utils.time_utils import utc_now

        if not logs.artifact_store_id:
            return []

        artifact_store_model = zen_store.get_stack_component(
            logs.artifact_store_id
        )

        log_store = DefaultLogStore(
            name="default_log_store_fallback",
            id=artifact_store_model.id,
            config=DefaultLogStoreConfig(),
            flavor="default",
            type=StackComponentType.LOG_STORE,
            user=artifact_store_model.user,
            workspace=artifact_store_model.workspace,
            created=utc_now(),
            updated=utc_now(),
        )

    return log_store.fetch(
        logs_model=logs,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
