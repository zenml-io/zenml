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
import os
import threading
from contextlib import nullcontext
from contextvars import ContextVar
from datetime import datetime
from types import TracebackType
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from zenml.client import Client
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import StepConfiguration
from zenml.constants import (
    ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE,
    ENV_ZENML_DISABLE_STEP_LOGS_STORAGE,
    ENV_ZENML_SERVER,
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
    StepRunResponse,
    StepRunUpdate,
)

if TYPE_CHECKING:
    from zenml.log_stores.base_log_store import BaseLogStoreOrigin
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

    model_config = ConfigDict(
        # ignore extra attributes during model initialization
        extra="ignore",
    )


class LoggingContext:
    """Context manager which collects logs using a LogStore."""

    def __init__(
        self,
        name: str,
        log_model: "LogsResponse",
        block_on_exit: bool = True,
        **metadata: Any,
    ) -> None:
        """Initialize the logging context.

        Args:
            name: The name of the logging context.
            log_model: The logs response model for this context.
            block_on_exit: Whether to block until all logs are flushed when the
                context is exited, if there are no more logging contexts active.
            **metadata: Additional metadata to attach to the log entry.
        """
        self.log_model = log_model
        self._lock = threading.Lock()
        self._previous_context: Optional[LoggingContext] = None
        self._disabled = False
        self._log_store = Client().active_stack.log_store
        self._metadata = metadata
        self._origin: Optional["BaseLogStoreOrigin"] = None
        self._name = name
        self._block_on_exit = block_on_exit

    @property
    def name(self) -> str:
        """The name of the logging context.

        Returns:
            The name of the logging context.
        """
        return self._name

    @classmethod
    def emit(cls, record: logging.LogRecord) -> None:
        """Emit a log record using the active logging context.

        This class method is called by stdout/stderr wrappers and logging
        handlers to route logs to the active log store.

        Args:
            record: The log record to emit.
        """
        if context := active_logging_context.get():
            if context._disabled:
                return
            context._disabled = True
            try:
                message = record.getMessage()
                if message and message.strip():
                    if context._origin:
                        context._log_store.emit(
                            context._origin,
                            record,
                        )
            except Exception:
                logger.debug("Failed to emit log record", exc_info=True)
            finally:
                context._disabled = False

    def __enter__(self) -> "LoggingContext":
        """Enter the context and set as active.

        Returns:
            self
        """
        with self._lock:
            self._previous_context = active_logging_context.get()
            active_logging_context.set(self)
            self._origin = self._log_store.register_origin(
                name=self.name,
                log_model=self.log_model,
                metadata=self._metadata,
            )

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
            LoggingContext.emit(
                logging.LogRecord(
                    name="",
                    level=logging.ERROR,
                    msg="An exception has occurred.",
                    args=(),
                    exc_info=(exc_type, exc_val, exc_tb) if exc_val else None,
                    func=None,
                    pathname="",
                    lineno=0,
                )
            )

        with self._lock:
            active_logging_context.set(self._previous_context)
            if self._origin:
                self._log_store.deregister_origin(
                    self._origin, blocking=self._block_on_exit
                )
                self._origin = None


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


def is_pipeline_logging_enabled(
    pipeline_configuration: PipelineConfiguration,
) -> bool:
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


def is_step_logging_enabled(
    step_configuration: StepConfiguration,
    pipeline_configuration: PipelineConfiguration,
) -> bool:
    """Check if logging is enabled for a step configuration.

    Args:
        step_configuration: The step configuration.
        pipeline_configuration: The pipeline configuration.

    Returns:
        True if logging is enabled, False if disabled.
    """
    from zenml.orchestrators.utils import is_setting_enabled

    if handle_bool_env_var(ENV_ZENML_DISABLE_STEP_LOGS_STORAGE, False):
        return False
    else:
        is_enabled_on_step = step_configuration.enable_step_logs
        is_enabled_on_pipeline = pipeline_configuration.enable_step_logs
        return is_setting_enabled(is_enabled_on_step, is_enabled_on_pipeline)


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


def get_run_log_metadata(
    pipeline_run: "PipelineRunResponse",
) -> Dict[str, Any]:
    """Get the log metadata for a pipeline run.

    Args:
        pipeline_run: The pipeline run.

    Returns:
        The log metadata.
    """
    log_metadata = {
        "pipeline.run.id": str(pipeline_run.id),
        "pipeline.run.name": pipeline_run.name,
        "project.id": str(pipeline_run.project.id),
        "project.name": pipeline_run.project.name,
    }

    if pipeline_run.pipeline is not None:
        log_metadata.update(
            {
                "pipeline.id": str(pipeline_run.pipeline.id),
                "pipeline.name": pipeline_run.pipeline.name,
            }
        )

    if pipeline_run.stack is not None:
        log_metadata.update(
            {
                "stack.id": str(pipeline_run.stack.id),
                "stack.name": pipeline_run.stack.name,
            }
        )

    if pipeline_run.user is not None:
        log_metadata.update(
            {
                "user.id": str(pipeline_run.user.id),
                "user.name": pipeline_run.user.name,
            }
        )

    return log_metadata


def setup_run_logging(
    pipeline_run: "PipelineRunResponse",
    source: str,
    block_on_exit: bool = True,
) -> Any:
    """Set up logging for a pipeline run.

    Searches for existing logs by source, updates the run if needed.

    Args:
        pipeline_run: The pipeline run.
        source: The source of the logs.
        block_on_exit: Whether to block until all logs are flushed when the
            context is exited, if there are no more logging contexts active.

    Returns:
        The logs context.
    """
    log_metadata = get_run_log_metadata(pipeline_run)
    log_metadata.update(dict(source=source))
    name = f"zenml.pipeline_run.{pipeline_run.name}.{source}"

    if pipeline_run.log_collection is not None:
        if run_logs := search_logs_by_source(
            pipeline_run.log_collection, source
        ):
            return LoggingContext(
                name=name,
                log_model=run_logs,
                block_on_exit=block_on_exit,
                **log_metadata,
            )

    logs_request = generate_logs_request(source=source)
    try:
        client = Client()
        run_update = PipelineRunUpdate(add_logs=[logs_request])
        pipeline_run = client.zen_store.update_run(
            run_id=pipeline_run.id, run_update=run_update
        )
    except Exception as e:
        logger.error(f"Failed to add logs to the run {pipeline_run.id}: {e}")

    if pipeline_run.log_collection is not None:
        if run_logs := search_logs_by_source(
            pipeline_run.log_collection, source
        ):
            return LoggingContext(
                name=name,
                log_model=run_logs,
                block_on_exit=block_on_exit,
                **log_metadata,
            )

    return nullcontext()


def get_step_log_metadata(
    step_run: "StepRunResponse", pipeline_run: "PipelineRunResponse"
) -> Dict[str, Any]:
    """Get the log metadata for a step run.

    Args:
        step_run: The step run.
        pipeline_run: The pipeline run.

    Returns:
        The log metadata.
    """
    log_metadata = get_run_log_metadata(pipeline_run)
    log_metadata.update(
        {
            "step.run.id": str(step_run.id),
            "step.run.name": step_run.name,
        }
    )
    return log_metadata


def setup_step_logging(
    step_run: "StepRunResponse",
    pipeline_run: "PipelineRunResponse",
    source: str,
    block_on_exit: bool = True,
) -> Any:
    """Set up logging for a step run.

    Searches for existing logs by source, updates the step if needed.

    Args:
        step_run: The step run.
        pipeline_run: The pipeline run.
        source: The source of the logs.
        block_on_exit: Whether to block until all logs are flushed when the
            context is exited, if there are no more logging contexts active.

    Returns:
        The logs context.
    """
    log_metadata = get_step_log_metadata(step_run, pipeline_run)
    log_metadata.update(dict(source=source))
    name = (
        f"zenml.pipeline_run.{pipeline_run.name}.step.{step_run.name}.{source}"
    )

    if pipeline_run.log_collection is not None:
        if run_logs := search_logs_by_source(
            pipeline_run.log_collection, source
        ):
            return LoggingContext(
                name=name,
                log_model=run_logs,
                block_on_exit=block_on_exit,
                **log_metadata,
            )

    if step_run.log_collection is not None:
        if step_logs := search_logs_by_source(step_run.log_collection, source):
            return LoggingContext(
                name=name,
                log_model=step_logs,
                block_on_exit=block_on_exit,
                **log_metadata,
            )

    logs_request = generate_logs_request(source=source)
    try:
        client = Client()
        step_run_update = StepRunUpdate(add_logs=[logs_request])
        step_run = client.zen_store.update_run_step(
            step_run_id=step_run.id, step_run_update=step_run_update
        )
    except Exception as e:
        logger.error(f"Failed to add logs to the step run {step_run.id}: {e}")

    if step_run.log_collection is not None:
        if step_logs := search_logs_by_source(step_run.log_collection, source):
            return LoggingContext(
                name=name,
                log_model=step_logs,
                block_on_exit=block_on_exit,
                **log_metadata,
            )

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
        RuntimeError: If the function is called from the client environment.
    """
    from zenml.log_stores.base_log_store import BaseLogStore
    from zenml.stack import StackComponent
    from zenml.zen_server.rbac.endpoint_utils import (
        verify_permissions_and_get_entity,
    )

    if ENV_ZENML_SERVER not in os.environ:
        # This utility function should not be called from the client environment
        # because it would cause instantiating the active log store again.
        raise RuntimeError(
            "This utility function is only supported in the server "
            "environment. Use the log store directly instead."
        )

    log_store: Optional[BaseLogStore] = None

    if logs.log_store_id:
        try:
            log_store_model = verify_permissions_and_get_entity(
                id=logs.log_store_id,
                get_method=zen_store.get_stack_component,
            )
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
    elif logs.artifact_store_id:
        from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
        from zenml.log_stores.artifact.artifact_log_store import (
            ArtifactLogStore,
        )

        try:
            artifact_store_model = verify_permissions_and_get_entity(
                id=logs.artifact_store_id,
                get_method=zen_store.get_stack_component,
            )
        except KeyError:
            raise DoesNotExistException(
                f"Artifact store '{logs.artifact_store_id}' does not exist."
            )
        if not artifact_store_model.type == StackComponentType.ARTIFACT_STORE:
            raise DoesNotExistException(
                f"Stack component '{logs.artifact_store_id}' is not an artifact store."
            )
        artifact_store = cast(
            "BaseArtifactStore",
            StackComponent.from_model(artifact_store_model),
        )
        log_store = ArtifactLogStore.from_artifact_store(
            artifact_store=artifact_store
        )

    else:
        return []

    try:
        return log_store.fetch(logs_model=logs, limit=limit)
    finally:
        log_store.cleanup()
