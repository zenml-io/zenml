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
"""Logging handler for artifact stores."""

import io
import time
from logging import LogRecord
from logging.handlers import TimedRotatingFileHandler
from typing import TYPE_CHECKING, Any

from zenml.io import fileio
from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.artifact_stores.base_artifact_store import BaseArtifactStore


class ArtifactStoreLoggingHandler(TimedRotatingFileHandler):
    """Handler for logging to artifact stores."""

    def __init__(
        self,
        artifact_store: "BaseArtifactStore",
        logs_uri: str,
        max_messages: int = 20,
        *args: Any,
        **kwargs: Any
    ):
        """Initializes the handler.

        Args:
            artifact_store: Artifact store to log to.
            logs_uri: URI of the logs file.
            max_messages: Maximum number of messages to buffer before flushing.
            *args: Additional arguments to pass to the superclass.
            **kwargs: Additional keyword arguments to pass to the superclass.
        """
        self.logs_uri = logs_uri
        self.max_messages = max_messages
        self.buffer = io.StringIO()
        self.message_count = 0
        self.last_upload_time = time.time()
        super().__init__(self.logs_uri, *args, **kwargs)

    def emit(self, record: LogRecord) -> None:
        """Emits the log record.

        Args:
            record: Log record to emit.
        """
        msg = self.format(record)
        self.buffer.write(msg + "\n")
        self.message_count += 1

        current_time = time.time()
        time_elapsed = current_time - self.last_upload_time

        if (
            self.message_count >= self.max_messages
            or time_elapsed >= self.interval
        ):
            self.flush()

    def flush(self) -> None:
        """Flushes the buffer to the artifact store."""
        with fileio.open(self.logs_uri, mode="a") as log_file:
            log_file.write(self.buffer.getvalue())
        self.buffer.close()
        self.buffer = io.StringIO()
        self.message_count = 0
        self.last_upload_time = time.time()

    def doRollover(self) -> None:
        """Flushes the buffer and performs a rollover."""
        self.flush()
        super().doRollover()
