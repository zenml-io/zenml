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

from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from datetime import datetime
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Generator,
    Optional,
    Tuple,
    Type,
    Union,
)
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from zenml.client import Client
from zenml.constants import (
    ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE,
    handle_bool_env_var,
)
from zenml.enums import LoggingLevels
from zenml.logger import get_logger
from zenml.models import (
    LogsRequest,
    LogsResponse,
    PipelineRunUpdate,
    PipelineSnapshotResponse,
)
from zenml.utils.time_utils import utc_now

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.log_stores.base_log_store import BaseLogStore
    from zenml.models import LogsRequest, LogsResponse

# Maximum number of log entries to return in a single request
MAX_ENTRIES_PER_REQUEST = 20000
# Maximum size of a single log message in bytes (5KB)
DEFAULT_MESSAGE_SIZE = 5 * 1024

# Active log store and its associated log model
_active_log_context: ContextVar[
    Optional[Tuple["BaseLogStore", Union["LogsRequest", "LogsResponse"]]]
] = ContextVar("active_log_context", default=None)


def set_active_log_context(
    log_store: Optional["BaseLogStore"],
    log_model: Optional[Union["LogsRequest", "LogsResponse"]] = None,
) -> None:
    """Set active log store and model for current context.

    Args:
        log_store: Log store to activate, or None to deactivate.
        log_model: The log model associated with this context.
    """
    if log_store is None:
        _active_log_context.set(None)
    else:
        if log_model is None:
            raise ValueError(
                "log_model must be provided when log_store is set"
            )
        _active_log_context.set((log_store, log_model))


def get_active_log_context() -> Optional[
    Tuple["BaseLogStore", Union["LogsRequest", "LogsResponse"]]
]:
    """Get the active log store and model for the current context.

    Returns:
        Tuple of (log_store, log_model), or None if no context is active.
    """
    return _active_log_context.get()


def get_active_log_store() -> Optional["BaseLogStore"]:
    """Get the active log store for the current context.

    Returns:
        The active log store, or None if no log store is active.
    """
    context = _active_log_context.get()
    return context[0] if context else None


def get_active_log_model() -> Optional[Union["LogsRequest", "LogsResponse"]]:
    """Get the active log model for the current context.

    Returns:
        The active log model, or None if no context is active.
    """
    context = _active_log_context.get()
    return context[1] if context else None


class LogEntry(BaseModel):
    """A structured log entry with parsed information."""

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
        source: str,
        log_model: Optional[Union["LogsRequest", "LogsResponse"]] = None,
    ) -> None:
        """Initialize the logging context.

        Args:
            source: An identifier for the source of the logs
            (e.g., "step", "orchestrator")
            log_model: The log model to use for the logging context
        """
        if Client().active_stack.log_store:
            self.log_store = Client().active_stack.log_store
        else:
            from zenml.log_stores import (
                DefaultLogStore,
                DefaultLogStoreConfig,
                DefaultLogStoreFlavor,
            )

            default_log_store_flavor = DefaultLogStoreFlavor()

            self.log_store = DefaultLogStore(
                id=uuid4(),
                name="temporary_default",
                flavor=default_log_store_flavor.name,
                type=default_log_store_flavor.type,
                config=DefaultLogStoreConfig(),
                environment={},
                user=Client().active_user.id,
                created=utc_now(),
                updated=utc_now(),
                secrets=[],
            )

        self.source = source
        self.log_model = log_model or self.generate_log_request()

        self._previous_log_context: Optional[
            Tuple["BaseLogStore", Union["LogsRequest", "LogsResponse"]]
        ] = None
        self._is_outermost_context: bool = False

    def generate_log_request(self) -> "LogsRequest":
        """Create a log request model.

        Returns:
            The log request model.
        """
        from zenml.log_stores.default.default_log_store import (
            DefaultLogStore,
            prepare_logs_uri,
        )

        if isinstance(self.log_store, DefaultLogStore):
            log_id = uuid4()
            artifact_store = Client().active_stack.artifact_store

            return LogsRequest(
                id=log_id,
                source=self.source,
                uri=prepare_logs_uri(
                    artifact_store=artifact_store,
                    log_id=log_id,
                ),
                artifact_store_id=artifact_store.id,
            )
        else:
            return LogsRequest(
                id=uuid4(),
                source=self.source,
                log_store_id=self.log_store.id,
            )

    def __enter__(self) -> "LoggingContext":
        """Enter the context and activate log collection.

        Saves the current active context to restore it on exit,
        enabling nested logging contexts.

        Returns:
            self
        """
        self._previous_log_context = get_active_log_context()

        # Set the active context before activating the log store
        # so that activate() can access the log model from context
        set_active_log_context(self.log_store, self.log_model)
        self.log_store.activate()

        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit the context and deactivate log collection.

        Restores the previous active context to support nested contexts.

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

        self.log_store.deactivate()

        if self._previous_log_context:
            set_active_log_context(
                self._previous_log_context[0],
                self._previous_log_context[1],
            )
        else:
            set_active_log_context(None)


def setup_orchestrator_logging(
    run_id: UUID,
    snapshot: "PipelineSnapshotResponse",
) -> Any:
    """Set up logging for an orchestrator environment.

    This function can be reused by different orchestrators to set up
    consistent logging behavior.

    Args:
        run_id: The pipeline run ID.
        snapshot: The snapshot of the pipeline run.
        logs_response: The logs response to continue from.

    Returns:
        The logs context
    """
    # TODO: we need to establish the connection here again.
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

        return LoggingContext(source="orchestrator")
    except Exception as e:
        logger.error(
            f"Failed to setup orchestrator logging for run {run_id}: {e}"
        )
        return nullcontext()


# TODO: Double check this function
@contextmanager
def setup_pipeline_logging(
    source: str,
    snapshot: "PipelineSnapshotResponse",
    run_id: Optional[UUID] = None,
    logs_response: Optional[LogsResponse] = None,
) -> Generator[Optional[LogsRequest], None, None]:
    """Set up logging for a pipeline run.

    Args:
        source: The log source.
        snapshot: The snapshot of the pipeline run.
        run_id: The ID of the pipeline run.
        logs_response: The logs response to continue from.

    Raises:
        Exception: If updating the run with the logs request fails.

    Yields:
        The logs request.
    """
    logging_enabled = True

    if handle_bool_env_var(ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE, False):
        logging_enabled = False
    elif snapshot.pipeline_configuration.enable_pipeline_logs is not None:
        logging_enabled = snapshot.pipeline_configuration.enable_pipeline_logs

    if logging_enabled:
        client = Client()

        logs_model = None
        if logs_response:
            logs_model = logs_response

        logs_context = LoggingContext(source="client", log_model=logs_model)

        if run_id and logs_response is None:
            try:
                run_update = PipelineRunUpdate(
                    add_logs=[logs_context.log_model]
                )
                client.zen_store.update_run(
                    run_id=run_id, run_update=run_update
                )
            except Exception as e:
                logger.error(f"Failed to add logs to the run {run_id}: {e}")
                raise e

        with logs_context:
            yield logs_context.log_model
    else:
        yield None
