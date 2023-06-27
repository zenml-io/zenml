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
from typing import TYPE_CHECKING, Optional

from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils.io_utils import is_remote

logger = get_logger(__name__)

if TYPE_CHECKING:
    pass


# How many seconds to wait before uploading logs to the artifact store
LOGS_HANDLER_INTERVAL_SECONDS: int = 5
# How many messages to buffer before uploading logs to the artifact store
LOGS_HANDLER_MAX_MESSAGES: int = 100


class ArtifactStoreLoggingHandler(TimedRotatingFileHandler):
    """Handler for logging to artifact stores."""

    def __init__(self, logs_uri: str):
        """Initializes the handler.

        Args:
            logs_uri: URI of the logs file.
        """
        self.logs_uri = logs_uri
        self.max_messages = LOGS_HANDLER_MAX_MESSAGES
        self.buffer = io.StringIO()
        self.message_count = 0
        self.last_upload_time = time.time()
        self.local_temp_file: Optional[str] = None

        # set local_logging_file to self.logs_uri if self.logs_uri is a local path
        # otherwise, set local_logging_file to a temporary file
        if is_remote(self.logs_uri):
            # We log to a temporary file first, because
            # TimedRotatingFileHandler does not support writing
            # to a remote file, but still needs a file to get going
            local_logging_file = f".zenml_tmp_logs_{int(time.time())}"
            self.local_temp_file = local_logging_file
        else:
            local_logging_file = self.logs_uri

        super().__init__(
            local_logging_file,
            when="s",
            interval=LOGS_HANDLER_INTERVAL_SECONDS,
        )

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
        try:
            with fileio.open(self.logs_uri, mode="wb") as log_file:
                log_file.write(self.buffer.getvalue().encode("utf-8"))
        except (OSError, IOError) as e:
            # This exception can be raised if there are issues with the underlying system calls,
            # such as reaching the maximum number of open files, permission issues, file corruption,
            # or other I/O errors
            logger.error(f"Error while trying to write logs: {e}")

        self.message_count = 0
        self.last_upload_time = time.time()

    def doRollover(self) -> None:
        """Flushes the buffer and performs a rollover."""
        self.flush()
        super().doRollover()

    def close(self) -> None:
        """Tidy up any resources used by the handler."""
        self.flush()
        super().close()
        if self.local_temp_file and fileio.exists(self.local_temp_file):
            fileio.remove(self.local_temp_file)
