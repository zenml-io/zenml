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
"""Base class for log stores."""

import logging
import threading
from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, cast

from zenml.enums import StackComponentType
from zenml.models import LogsResponse
from zenml.stack import Flavor, StackComponent, StackComponentConfig
from zenml.utils.logging_utils import LogEntry

MAX_ENTRIES_PER_REQUEST = 20000


class BaseLogStoreConfig(StackComponentConfig):
    """Base configuration for all log stores."""


class BaseLogStore(StackComponent):
    """Base class for all ZenML log stores.

    A log store is responsible for collecting, storing, and retrieving logs
    during pipeline and step execution. Different implementations may store
    logs in different backends (artifact store, OpenTelemetry, Datadog, etc.).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the log store.

        Args:
            *args: Positional arguments for the base class.
            **kwargs: Keyword arguments for the base class.
        """
        super().__init__(*args, **kwargs)
        self._emitter_counter = 0
        self._lock = threading.RLock()

    @property
    def config(self) -> BaseLogStoreConfig:
        """Returns the configuration of the log store.

        Returns:
            The configuration.
        """
        return cast(BaseLogStoreConfig, self._config)

    @abstractmethod
    def emit(
        self,
        record: logging.LogRecord,
        log_model: LogsResponse,
        metadata: Dict[str, Any],
    ) -> None:
        """Process a log record from the logging system.

        Args:
            record: The Python logging.LogRecord to process.
            log_model: The log model to emit the log record to.
            metadata: Additional metadata to attach to the log entry.
        """

    @abstractmethod
    def finalize(
        self,
        log_model: LogsResponse,
    ) -> None:
        """Finalize the stream of log records associated with a log model.

        This is used to announce the end of the stream of log records associated
        with a log model and that no more log records will be emitted.

        The implementation should ensure that all log records associated with
        the log model are flushed to the backend and any resources (clients,
        connections, file descriptors, etc.) are released.

        Args:
            log_model: The log model to finalize.
        """

    def register_emitter(self) -> None:
        """Register an emitter for the log store."""
        with self._lock:
            self._emitter_counter += 1

    def deregister_emitter(self) -> None:
        """Deregister an emitter for the log store."""
        with self._lock:
            self._emitter_counter -= 1
            if self._emitter_counter == 0:
                self.flush()

    @abstractmethod
    def flush(self) -> None:
        """Flush the log store.

        This method is called to ensure that all logs are flushed to the backend.
        """

    @abstractmethod
    def fetch(
        self,
        logs_model: LogsResponse,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = MAX_ENTRIES_PER_REQUEST,
    ) -> List[LogEntry]:
        """Fetch logs from the log store.

        This method is called from the server to retrieve logs for display
        on the dashboard or via API. The implementation should not require
        any integration-specific SDKs that aren't available on the server.

        Args:
            logs_model: The logs model containing metadata about the logs.
            start_time: Filter logs after this time.
            end_time: Filter logs before this time.
            limit: Maximum number of log entries to return.

        Returns:
            List of log entries matching the query.
        """


class BaseLogStoreFlavor(Flavor):
    """Base class for all ZenML log store flavors."""

    @property
    def type(self) -> StackComponentType:
        """Type of the flavor.

        Returns:
            The type of the flavor.
        """
        return StackComponentType.LOG_STORE

    @property
    def config_class(self) -> Type[BaseLogStoreConfig]:
        """Config class for the base log store flavor.

        Returns:
            The config class.
        """
        return BaseLogStoreConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type["BaseLogStore"]:
        """Implementation class for the base log store flavor.

        Returns:
            The implementation class.
        """
