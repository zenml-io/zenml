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
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, cast

from zenml.enums import StackComponentType
from zenml.models import LogsResponse
from zenml.stack import Flavor, StackComponent, StackComponentConfig
from zenml.utils.logging_utils import LogEntry

MAX_ENTRIES_PER_REQUEST = 20000


class BaseLogStoreConfig(StackComponentConfig):
    """Base configuration for all log stores."""


class BaseLogStoreOrigin:
    """Base class for all ZenML log store origins.

    The origin is the entry point for all log records to be sent to the log
    store for processing. The process of sending a log record is as follows:

    1. instantiate the log store or use the active log store
    2. register an origin by calling log_store.register_origin() and passing
    the log model and optional metadata to be attached to each log record
    3. emit the log record by calling log_store.emit() and passing the origin
    and log record
    4. deregister the origin when all logs have been emitted by calling
    log_store.deregister(origin)
    """

    def __init__(
        self,
        name: str,
        log_store: "BaseLogStore",
        log_model: LogsResponse,
        metadata: Dict[str, Any],
    ) -> None:
        """Initialize a log store origin.

        Args:
            name: The name of the origin.
            log_store: The log store to emit logs to.
            log_model: The log model associated with the origin.
            metadata: Additional metadata to attach to all log entries that will
                be emitted by this origin.
        """
        self.name = name
        self.log_store = log_store
        self.log_model = log_model
        self.metadata = metadata


class BaseLogStore(StackComponent, ABC):
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
        self._origins: Dict[str, BaseLogStoreOrigin] = {}
        self._lock = threading.RLock()

    @property
    def config(self) -> BaseLogStoreConfig:
        """Returns the configuration of the log store.

        Returns:
            The configuration.
        """
        return cast(BaseLogStoreConfig, self._config)

    @property
    def origin_class(self) -> Type[BaseLogStoreOrigin]:
        """Class of the origin.

        Returns:
            The class of the origin used with this log store.
        """
        return BaseLogStoreOrigin

    def register_origin(
        self, name: str, log_model: LogsResponse, metadata: Dict[str, Any]
    ) -> BaseLogStoreOrigin:
        """Register an origin for the log store.

        Args:
            name: The name of the origin.
            log_model: The log model associated with the origin.
            metadata: Additional metadata to attach to the log entry.

        Returns:
            The origin.
        """
        with self._lock:
            origin = self.origin_class(name, self, log_model, metadata)
            self._origins[name] = origin
            return origin

    def deregister_origin(
        self,
        origin: BaseLogStoreOrigin,
        blocking: bool = True,
    ) -> None:
        """Deregister an origin previously registered with the log store.

        If no other origins are left, the log store will be flushed. The
        `blocking` parameter determines whether to block until the flush is
        complete.

        Args:
            origin: The origin to deregister.
            blocking: Whether to block until the deregistration is complete
                and all logs are flushed if this is the last origin registered.
        """
        with self._lock:
            if origin.name not in self._origins:
                return
            self._release_origin(origin)
            del self._origins[origin.name]
            if len(self._origins) == 0:
                self.flush(blocking=blocking)

    @abstractmethod
    def emit(
        self,
        origin: BaseLogStoreOrigin,
        record: logging.LogRecord,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Process a log record from the logging system.

        Args:
            origin: The origin used to send the log record.
            record: The Python logging.LogRecord to process.
            metadata: Additional metadata to attach to the log entry.
        """

    @abstractmethod
    def _release_origin(
        self,
        origin: BaseLogStoreOrigin,
    ) -> None:
        """Finalize the stream of log records associated with an origin.

        This is used to announce the end of the stream of log records associated
        with an origin and that no more log records will be emitted.

        The implementation should ensure that all log records associated with
        the origin are flushed to the backend and any resources (clients,
        connections, file descriptors, etc.) are released.

        Args:
            origin: The origin to finalize.
        """

    @abstractmethod
    def flush(self, blocking: bool = True) -> None:
        """Flush the log store.

        This method is called to ensure that all logs are flushed to the backend.

        Args:
            blocking: Whether to block until the flush is complete.
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
