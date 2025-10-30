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
"""ZenML logging handler."""

import os
import re
from contextlib import nullcontext
from contextvars import ContextVar
from datetime import datetime
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Type,
)
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from zenml.client import Client
from zenml.constants import (
    ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE,
    handle_bool_env_var,
)
from zenml.enums import LoggingLevels
from zenml.logger import (
    get_logger,
)
from zenml.models import (
    LogsRequest,
    LogsResponse,
    PipelineSnapshotResponse,
)
from zenml.utils.io_utils import sanitize_remote_path
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore

logger = get_logger(__name__)

# Context variables
redirected: ContextVar[bool] = ContextVar("redirected", default=False)

ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

LOGS_EXTENSION = ".log"
PIPELINE_RUN_LOGS_FOLDER = "pipeline_runs"

# Maximum number of log entries to return in a single request
MAX_ENTRIES_PER_REQUEST = 20000
# Maximum size of a single log message in bytes (5KB)
DEFAULT_MESSAGE_SIZE = 5 * 1024


def prepare_logs_uri(
    artifact_store: "BaseArtifactStore",
    log_id: UUID,
) -> str:
    """Generates and prepares a URI for the log file or folder for a step.

    Args:
        artifact_store: The artifact store on which the artifact will be stored.
        log_id: The ID of the logs entity

    Returns:
        The URI of the log storage (file or folder).
    """
    logs_base_uri = os.path.join(artifact_store.path, "logs")

    if not artifact_store.exists(logs_base_uri):
        artifact_store.makedirs(logs_base_uri)

    if artifact_store.config.IS_IMMUTABLE_FILESYSTEM:
        logs_uri = os.path.join(logs_base_uri, log_id)
        if artifact_store.exists(logs_uri):
            logger.warning(
                f"Logs directory {logs_uri} already exists! Removing old log directory..."
            )
            artifact_store.rmtree(logs_uri)

        artifact_store.makedirs(logs_uri)
    else:
        logs_uri = os.path.join(logs_base_uri, f"{log_id}{LOGS_EXTENSION}")
        if artifact_store.exists(logs_uri):
            logger.warning(
                f"Logs file {logs_uri} already exists! Removing old log file..."
            )
            artifact_store.remove(logs_uri)

    return sanitize_remote_path(logs_uri)


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

    def __init__(self, source: str) -> None:
        """Initialize the logging context.

        Args:
            source: An identifier for the source of the logs (e.g., "step", "orchestrator")
        """
        # Create the log store first
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

        # Based on the source, generate the log request
        self.source = source
        self.log_request = self.generate_log_request()

    def generate_log_request(self) -> "LogsRequest":
        """Create a log request model.

        Returns:
            The log request model.
        """
        from zenml.log_stores.default.default_log_store import DefaultLogStore

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

        Returns:
            self
        """
        self.log_store.activate(log_request=self.log_request)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit the context and deactivate log collection.

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
