#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Dispatch boundary for prepared snapshot runs."""

from abc import ABC, abstractmethod
from uuid import UUID

from pydantic import BaseModel

from zenml.exceptions import MaxConcurrentTasksError


class SnapshotRunExecutionRequest(BaseModel):
    """Durable identifiers required to execute a prepared snapshot run."""

    run_id: UUID
    snapshot_id: UUID
    source_snapshot_id: UUID
    wait_for_completion: bool = True


class SnapshotRunQueueFullError(MaxConcurrentTasksError):
    """Raised when a dispatcher cannot accept more snapshot runs."""


class SnapshotRunDispatchError(Exception):
    """Raised when a dispatcher unexpectedly fails to accept a snapshot run."""


class SnapshotRunDispatcher(ABC):
    """Interface for accepting prepared snapshot runs for execution."""

    async def start(self) -> None:
        """Start dispatcher resources."""

    async def close(self) -> None:
        """Close dispatcher resources."""

    @abstractmethod
    def submit(self, request: SnapshotRunExecutionRequest) -> None:
        """Submit a prepared run and return after acceptance.

        Args:
            request: The prepared snapshot execution request.
        """


class LocalSnapshotRunDispatcher(SnapshotRunDispatcher):
    """Dispatch prepared runs through the server-local bounded executor."""

    def submit(self, request: SnapshotRunExecutionRequest) -> None:
        """Submit a prepared run to the local executor.

        Args:
            request: The prepared snapshot execution request.

        Raises:
            SnapshotRunQueueFullError: If local execution capacity is full.
        """
        from zenml.zen_server.pipeline_execution.utils import (
            execute_snapshot_run,
        )
        from zenml.zen_server.utils import snapshot_executor

        try:
            snapshot_executor().submit(execute_snapshot_run, request)
        except MaxConcurrentTasksError:
            raise SnapshotRunQueueFullError(
                "Maximum number of concurrent snapshot tasks reached."
            ) from None
