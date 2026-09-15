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
"""Retrieval of runner logs from the workload manager."""

from typing import Optional

from zenml.constants import LOGS_MAX_ENTRIES_PER_REQUEST
from zenml.log_stores.artifact.artifact_log_store import parse_log_entry
from zenml.models import (
    LogsEntriesFilter,
    LogsEntriesResponse,
    LogsResponse,
    PipelineRunResponse,
)
from zenml.zen_server.utils import server_config, workload_manager


def fetch_runner_logs(
    run: PipelineRunResponse,
    logs: Optional[LogsResponse] = None,
    start: Optional[str] = None,
    limit: Optional[int] = None,
    before: Optional[str] = None,
    after: Optional[str] = None,
    filter_: Optional[LogsEntriesFilter] = None,
) -> LogsEntriesResponse:
    """Read runner logs using the workload that launched the run.

    Args:
        run: The authorized, hydrated pipeline run.
        logs: The runner log model, absent for runs created before 0.94.0.
        start: Only the oldest end is supported.
        limit: Maximum number of entries to return.
        before: Unsupported continuation cursor.
        after: Unsupported continuation cursor.
        filter_: Unsupported filters.

    Returns:
        One batch of runner log entries, without continuation cursors.

    Raises:
        ValueError: If runner logs are unavailable or parameters are unsupported.
    """
    if (
        start not in (None, "oldest")
        or before is not None
        or after is not None
        or (filter_ is not None and any(filter_.model_dump().values()))
    ):
        raise ValueError(
            "Runner logs are retrieved as one batch. Pagination and search, "
            "level, since, and until filters must be applied by the client."
        )
    if limit is not None and limit <= 0:
        raise ValueError("`limit` must be a positive integer.")
    limit = min(
        limit or LOGS_MAX_ENTRIES_PER_REQUEST, LOGS_MAX_ENTRIES_PER_REQUEST
    )
    snapshot = run.snapshot
    if not snapshot:
        raise ValueError(
            "Runner logs are unavailable: the run has no snapshot."
        )
    if not logs and not (
        (snapshot.template_id or snapshot.source_snapshot_id or run.trigger)
        and server_config().workload_manager_enabled
    ):
        raise ValueError("Runner logs are unavailable for this run.")

    if run.trigger:
        workload_id = run.id
    elif run.source_snapshot:
        # A resumed snapshot run still refers to the original runner workload.
        workload_id = snapshot.id
    else:
        workload_id = run.id
    workload_logs = workload_manager().get_logs(workload_id=workload_id)
    entries = []
    for line in workload_logs.split("\n"):
        if entry := parse_log_entry(line):
            entries.append(entry)
        if len(entries) >= limit:
            break
    return LogsEntriesResponse(items=entries)
