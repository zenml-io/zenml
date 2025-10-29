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
"""Default log store implementation."""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional, cast
from uuid import UUID

from zenml.client import Client
from zenml.log_stores.base_log_store import BaseLogStore, BaseLogStoreConfig
from zenml.logger import get_logger, logging_handlers

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.logging.step_logging import (
        ArtifactStoreHandler,
        LogEntry,
        PipelineLogsStorage,
    )
    from zenml.models import LogsResponse

logger = get_logger(__name__)


class DefaultLogStoreConfig(BaseLogStoreConfig):
    """Configuration for the default log store.

    This log store saves logs to the artifact store, which is the default
    and backward-compatible approach.
    """


class DefaultLogStore(BaseLogStore):
    """Log store that saves logs to the artifact store.

    This implementation uses the artifact store as the backend for log storage,
    maintaining backward compatibility with existing ZenML behavior. Logs are
    written to the artifact store using a background thread and queue for
    efficient batching.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the default log store.

        Args:
            *args: Positional arguments for the base class.
            **kwargs: Keyword arguments for the base class.
        """
        super().__init__(*args, **kwargs)
        self.storage: Optional["PipelineLogsStorage"] = None
        self.handler: Optional["ArtifactStoreHandler"] = None
        self._artifact_store: Optional["BaseArtifactStore"] = None
        self._original_root_level: Optional[int] = None

    @property
    def config(self) -> DefaultLogStoreConfig:
        """Returns the configuration of the default log store.

        Returns:
            The configuration.
        """
        return cast(DefaultLogStoreConfig, self._config)

    def activate(
        self,
        pipeline_run_id: UUID,
        step_id: Optional[UUID] = None,
        source: str = "step",
    ) -> None:
        """Activate log collection to the artifact store.

        Args:
            pipeline_run_id: The ID of the pipeline run.
            step_id: The ID of the step (if collecting step logs).
            source: The source of the logs (e.g., "step", "orchestrator").
        """
        from zenml.logging.step_logging import (
            ArtifactStoreHandler,
            PipelineLogsStorage,
            prepare_logs_uri,
        )

        # Get the artifact store from the active stack
        client = Client()
        self._artifact_store = client.active_stack.artifact_store

        # Prepare logs URI
        step_name = None
        if step_id:
            try:
                step_run = client.get_pipeline_run_step(step_id)
                step_name = step_run.name
            except Exception:
                pass

        logs_uri = prepare_logs_uri(
            artifact_store=self._artifact_store,
            step_name=step_name,
        )

        # Create storage and handler
        self.storage = PipelineLogsStorage(
            logs_uri=logs_uri,
            artifact_store=self._artifact_store,
        )
        self.handler = ArtifactStoreHandler(self.storage)

        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self.handler)

        # Set root logger level to minimum of all handlers
        self._original_root_level = root_logger.level
        handler_levels = [handler.level for handler in root_logger.handlers]
        min_level = min(handler_levels)
        if min_level < root_logger.level:
            root_logger.setLevel(min_level)

        # Add to context variables for print capture
        logging_handlers.add(self.handler)

        logger.debug(
            f"DefaultLogStore activated for {source} "
            f"(pipeline_run={pipeline_run_id}, step={step_id})"
        )

    def deactivate(self) -> None:
        """Deactivate log collection and flush remaining logs."""
        if not self.handler:
            return

        # Remove handler from root logger
        root_logger = logging.getLogger()
        if self.handler in root_logger.handlers:
            root_logger.removeHandler(self.handler)

        # Restore original root logger level
        if self._original_root_level is not None:
            root_logger.setLevel(self._original_root_level)

        # Remove from context variables
        logging_handlers.remove(self.handler)

        # Shutdown storage thread (flushes and merges logs)
        if self.storage:
            try:
                self.storage._shutdown_log_storage_thread()
            except Exception as e:
                logger.warning(f"Error shutting down log storage: {e}")

        logger.debug("DefaultLogStore deactivated")

    def fetch(
        self,
        logs_model: "LogsResponse",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20000,
    ) -> List["LogEntry"]:
        """Fetch logs from the artifact store.

        Args:
            logs_model: The logs model containing uri and artifact_store_id.
            start_time: Filter logs after this time.
            end_time: Filter logs before this time.
            limit: Maximum number of log entries to return.

        Returns:
            List of log entries from the artifact store.

        Raises:
            ValueError: If logs_model.uri is not provided.
        """
        from zenml.logging.step_logging import fetch_log_records

        if not logs_model.uri:
            raise ValueError(
                "logs_model.uri is required for DefaultLogStore.fetch()"
            )

        if not logs_model.artifact_store_id:
            raise ValueError(
                "logs_model.artifact_store_id is required for DefaultLogStore.fetch()"
            )

        client = Client()
        log_entries = fetch_log_records(
            zen_store=client.zen_store,
            artifact_store_id=logs_model.artifact_store_id,
            logs_uri=logs_model.uri,
        )

        if start_time or end_time:
            filtered_entries = []
            for entry in log_entries:
                if entry.timestamp:
                    if start_time and entry.timestamp < start_time:
                        continue
                    if end_time and entry.timestamp > end_time:
                        continue
                filtered_entries.append(entry)
            log_entries = filtered_entries

        return log_entries[:limit]
