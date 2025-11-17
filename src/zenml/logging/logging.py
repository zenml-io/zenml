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
"""ZenML logging."""

import logging
import threading
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from types import TracebackType
from typing import (
    Any,
    Generator,
    Optional,
    Type,
)
from uuid import UUID, uuid4

from zenml.client import Client
from zenml.constants import (
    ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE,
    handle_bool_env_var,
)
from zenml.logger import get_logger
from zenml.models import (
    LogsRequest,
    LogsResponse,
    PipelineSnapshotResponse,
)

logger = get_logger(__name__)

# Active logging context
active_logging_context: ContextVar[Optional["LoggingContext"]] = ContextVar(
    "active_logging_context", default=None
)


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


class LoggingContext:
    """Context manager which collects logs using a LogStore."""

    def __init__(
        self,
        log_model: LogsResponse,
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


# TODO: Adjust the usage of this function
def setup_orchestrator_logging(
    run_id: UUID,
    snapshot: "PipelineSnapshotResponse",
    logs_response: LogsResponse,
) -> Any:
    """Set up logging for an orchestrator environment.

    This function can be reused by different orchestrators to set up
    consistent logging behavior.

    Args:
        run_id: The pipeline run ID.
        snapshot: The snapshot of the pipeline run.
        logs_response: The logs response for this orchestrator context.

    Returns:
        The logs context or nullcontext if logging is disabled.
    """
    try:
        logging_enabled = True

        if handle_bool_env_var(ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE, False):
            logging_enabled = False
        else:
            if (
                snapshot.pipeline_configuration.enable_pipeline_logs
                is not None
            ):
                logging_enabled = (
                    snapshot.pipeline_configuration.enable_pipeline_logs
                )

        if not logging_enabled:
            return nullcontext()

        return LoggingContext(log_model=logs_response)
    except Exception as e:
        logger.error(
            f"Failed to setup orchestrator logging for run {run_id}: {e}"
        )
        return nullcontext()


# TODO: Adjust the usage of this function
@contextmanager
def setup_pipeline_logging(
    snapshot: "PipelineSnapshotResponse",
    run_id: UUID,
    logs_response: LogsResponse,
) -> Generator[LogsResponse, None, None]:
    """Set up logging for a pipeline run.

    Args:
        snapshot: The snapshot of the pipeline run.
        run_id: The ID of the pipeline run.
        logs_response: The logs response for this pipeline context.

    Yields:
        The logs response.
    """
    logging_enabled = True

    if handle_bool_env_var(ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE, False):
        logging_enabled = False
    elif snapshot.pipeline_configuration.enable_pipeline_logs is not None:
        logging_enabled = snapshot.pipeline_configuration.enable_pipeline_logs

    if logging_enabled:
        with LoggingContext(log_model=logs_response):
            yield logs_response
    else:
        yield logs_response
