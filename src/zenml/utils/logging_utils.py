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
"""Utility functions for logging."""

import logging
import threading
from contextlib import nullcontext
from contextvars import ContextVar
from datetime import datetime
from types import TracebackType
from typing import TYPE_CHECKING, Any, List, Optional, Type, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from zenml.client import Client
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.constants import (
    ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE,
    handle_bool_env_var,
)
from zenml.enums import LoggingLevels, StackComponentType
from zenml.exceptions import DoesNotExistException
from zenml.logger import get_logger
from zenml.models import (
    LogsRequest,
    LogsResponse,
    PipelineRunResponse,
    PipelineRunUpdate,
    PipelineSnapshotResponse,
)
from zenml.stack import StackComponent
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)


active_logging_context: ContextVar[Optional["LoggingContext"]] = ContextVar(
    "active_logging_context", default=None
)


class LogEntry(BaseModel):
    """A structured log entry with parsed information.

    This is used in two distinct ways:
        1. If we are using the artifact log store, we save the
        entries as JSON-serialized LogEntry's in the artifact store.
        2. When queried, the server returns logs as a list of LogEntry's.
    """

    message: str = Field(description="The log message content")
    name: Optional[str] = Field(
        default=None,
        description="The name of the logger",
    )
    level: Optional[LoggingLevels] = Field(
        default=None,
        description="The log level",
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="When the log was created",
    )
    module: Optional[str] = Field(
        default=None, description="The module that generated this log entry"
    )
    filename: Optional[str] = Field(
        default=None,
        description="The name of the file that generated this log entry",
    )
    lineno: Optional[int] = Field(
        default=None, description="The fileno that generated this log entry"
    )
    chunk_index: int = Field(
        default=0,
        description="The index of the chunk in the log entry",
    )
    total_chunks: int = Field(
        default=1,
        description="The total number of chunks in the log entry",
    )
    id: UUID = Field(
        default_factory=uuid4,
        description="The unique identifier of the log entry",
    )


class LoggingContext:
    """Context manager which collects logs using a LogStore."""

    def __init__(
        self,
        log_model: "LogsResponse",
    ) -> None:
        """Initialize the logging context.

        Args:
            log_model: The logs response model for this context.
        """
        self.log_model = log_model
        self._lock = threading.Lock()
        self._previous_context: Optional[LoggingContext] = None

    @classmethod
    def emit(cls, record: logging.LogRecord) -> None:
        """Emit a log record using the active logging context.

        This class method is called by stdout/stderr wrappers and logging
        handlers to route logs to the active log store.

        Args:
            record: The log record to emit.
        """
        try:
            if context := active_logging_context.get():
                message = record.getMessage()
                if message and message.strip():
                    Client().active_stack.log_store.emit(record, context)
        except Exception:
            pass

    def __enter__(self) -> "LoggingContext":
        """Enter the context and set as active.

        Returns:
            self
        """
        with self._lock:
            self._previous_context = active_logging_context.get()
            active_logging_context.set(self)

        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit the context and restore previous context.

        Args:
            exc_type: The class of the exception.
            exc_val: The instance of the exception.
            exc_tb: The traceback of the exception.
        """
        if exc_type is not None:
            logger.error(
                "An exception has occurred.",
                exc_info=(exc_type, exc_val, exc_tb) if exc_val else None,
            )

        with self._lock:
            active_logging_context.set(self._previous_context)


def generate_logs_request(source: str) -> LogsRequest:
    """Generate a LogsRequest for logging.

    Args:
        source: The source of the logs (e.g., "client", "orchestrator", "step").

    Returns:
        A LogsRequest object.
    """
    from zenml.log_stores.artifact.artifact_log_store import (
        ArtifactLogStore,
        prepare_logs_uri,
    )

    client = Client()
    log_store = client.active_stack.log_store
    log_id = uuid4()

    if isinstance(log_store, ArtifactLogStore):
        artifact_store = client.active_stack.artifact_store
        return LogsRequest(
            id=log_id,
            source=source,
            uri=prepare_logs_uri(
                artifact_store=artifact_store,
                log_id=log_id,
            ),
            artifact_store_id=artifact_store.id,
        )
    else:
        return LogsRequest(
            id=log_id,
            source=source,
            log_store_id=log_store.id if log_store else None,
        )


def is_logging_enabled(pipeline_configuration: PipelineConfiguration) -> bool:
    """Check if logging is enabled for a pipeline configuration.

    Args:
        pipeline_configuration: The pipeline configuration.

    Returns:
        True if logging is enabled, False if disabled.
    """
    if handle_bool_env_var(ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE, False):
        return False
    elif pipeline_configuration.enable_pipeline_logs is not None:
        return pipeline_configuration.enable_pipeline_logs
    else:
        return True


def search_logs_by_source(
    logs_collection: List[LogsResponse], source: str
) -> Optional[LogsResponse]:
    """Get the logs response for a given source.

    Args:
        logs_collection: The logs collection.
        source: The source of the logs.

    Returns:
        The logs response for the given source.
    """
    for log in logs_collection:
        if log.source == source:
            return log
    return None


def setup_orchestrator_logging(
    pipeline_run: "PipelineRunResponse",
    snapshot: "PipelineSnapshotResponse",
) -> Any:
    """Set up logging for an orchestrator environment.

    This function can be reused by different orchestrators to set up
    consistent logging behavior.

    Args:
        pipeline_run: The pipeline run.
        snapshot: The snapshot of the pipeline run.

    Returns:
        The logs context or nullcontext if logging is disabled.
    """
    logging_enabled = is_logging_enabled(snapshot.pipeline_configuration)

    if not logging_enabled:
        return nullcontext()

    if orchestrator_logs := search_logs_by_source(
        pipeline_run.log_collection, "orchestrator"
    ):
        return LoggingContext(log_model=orchestrator_logs)

    logs_request = generate_logs_request(source="orchestrator")
    try:
        client = Client()
        run_update = PipelineRunUpdate(add_logs=[logs_request])
        pipeline_run = client.zen_store.update_run(
            run_id=pipeline_run.id, run_update=run_update
        )
    except Exception as e:
        logger.error(f"Failed to add logs to the run {pipeline_run.id}: {e}")

    if orchestrator_logs := search_logs_by_source(
        pipeline_run.log_collection, "orchestrator"
    ):
        return LoggingContext(log_model=orchestrator_logs)

    return nullcontext()


def fetch_logs(
    logs: "LogsResponse",
    zen_store: "BaseZenStore",
    limit: int,
) -> List["LogEntry"]:
    """Fetch logs from the log store.

    This function is designed to be called from the server side where we can't
    always instantiate the full Stack object due to missing integration dependencies.
    Instead, it directly instantiates the appropriate log store based on the logs model.

    Args:
        logs: The logs response model containing metadata about the logs.
        zen_store: The zen store instance.
        limit: Maximum number of log entries to return.

    Returns:
        List of log entries.

    Raises:
        DoesNotExistException: If the log store doesn't exist or is not the right type.
        NotImplementedError: If the log store's dependencies are not installed.
    """
    from zenml.log_stores.base_log_store import BaseLogStore

    log_store: Optional[BaseLogStore] = None

    if logs.log_store_id:
        try:
            log_store_model = zen_store.get_stack_component(logs.log_store_id)
        except KeyError:
            raise DoesNotExistException(
                f"Log store '{logs.log_store_id}' does not exist."
            )

        if not log_store_model.type == StackComponentType.LOG_STORE:
            raise DoesNotExistException(
                f"Stack component '{logs.log_store_id}' is not a log store."
            )

        try:
            log_store = cast(
                BaseLogStore,
                StackComponent.from_model(log_store_model),
            )
        except ImportError:
            raise NotImplementedError(
                f"Log store '{log_store_model.name}' could not be "
                "instantiated."
            )
    else:
        from zenml.log_stores.artifact.artifact_log_store import (
            ArtifactLogStore,
        )
        from zenml.log_stores.artifact.artifact_log_store_flavor import (
            ArtifactLogStoreConfig,
        )

        current_time = utc_now()
        log_store = ArtifactLogStore(
            name="default_artifact_log_store",
            id=uuid4(),
            config=ArtifactLogStoreConfig(),
            flavor="artifact",
            type=StackComponentType.LOG_STORE,
            user=uuid4(),
            created=current_time,
            updated=current_time,
        )

    return log_store.fetch(logs_model=logs, limit=limit)
